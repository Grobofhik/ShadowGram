import os
import json
import uuid
import shutil
import urllib.request
import subprocess
import time
import zipfile
import string
import random
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
from src.core.constants import *
from src.core.utils import get_free_port
from src.core.managers.hw_manager import get_or_create_fake_hw
from src.core.managers.proxy_manager import normalize_proxy_url, parse_proxy_url, _configure_socks_proxy_commands, _setup_gost_proxy, _configure_proxy_commands
from src.core.logger import logger

def start_telegram(
    workdir: Union[str, Path],
    proxy_url: Optional[str] = None,
    device_name: Optional[str] = None,
    account_name: Optional[str] = None,
) -> Tuple[Optional[subprocess.Popen], Optional[subprocess.Popen]]:
    """Запуск процесса Telegram с привязкой к workdir и прокси"""
    workdir = Path(workdir)
    logger.error(f"\n[DEBUG] Запуск профиля: {workdir}")

    if not workdir.exists():
        workdir.mkdir(parents=True, exist_ok=True)

    # 1. Fetch/generate fake hardware and device_name
    fake_vendor, fake_model, device_name_from_hw = get_or_create_fake_hw(account_name)
    if device_name_from_hw:
        device_name = device_name_from_hw

    gost_process: Optional[subprocess.Popen] = None
    tg_bin = (
        shutil.which("telegram-desktop")
        or shutil.which("Telegram")
        or "telegram-desktop"
    )
    tg_cmd = [tg_bin, "-workdir", str(workdir)]

    local_port: Optional[int] = None
    if proxy_url:
        proxy_url = normalize_proxy_url(proxy_url)
        is_socks = proxy_url.startswith("socks5://") or proxy_url.startswith("socks4://")
        if is_socks:
            proxy_info = parse_proxy_url(proxy_url)
            if proxy_info:
                tg_cmd = _configure_socks_proxy_commands(tg_cmd, workdir, proxy_info)
        else:
            local_port = get_free_port()
            gost_process = _setup_gost_proxy(workdir, proxy_url, local_port)
            if gost_process:
                tg_cmd = _configure_proxy_commands(tg_cmd, workdir, local_port)

    env = os.environ.copy()
    if proxy_url:
        is_socks = proxy_url.startswith("socks5://") or proxy_url.startswith("socks4://")
        if is_socks:
            env["all_proxy"] = proxy_url
            env["ALL_PROXY"] = proxy_url
        elif local_port:
            proxy_str = f"socks5://127.0.0.1:{local_port}"
            env["all_proxy"] = proxy_str
            env["ALL_PROXY"] = proxy_str

    if device_name:
        env.update(
            {
                "HOSTNAME": device_name,
                "QT_QPA_PLATFORM": "xcb",
            }
        )

    err_log = workdir / "telegram_error.log"
    
    # bwrap pipes setup
    pipes_fds = None
    r1, w1, r2, w2 = None, None, None, None
    
    if fake_vendor and fake_model and shutil.which("bwrap"):
        try:
            r1, w1 = os.pipe()
            r2, w2 = os.pipe()
            pipes_fds = (r1, r2)
        except Exception as pipe_e:
            logger.warning(f"Не удалось создать pipes для bwrap: {pipe_e}")
            for fd in [r1, w1]:
                if fd is not None:
                    try:
                        os.close(fd)
                    except:
                        pass
            r1, w1, r2, w2 = None, None, None, None
            pipes_fds = None

    final_cmd = _build_final_command(tg_cmd, device_name, fake_vendor, fake_model, pipes_fds)

    try:
        with open(err_log, "w") as f_err:
            if pipes_fds:
                tg_process = subprocess.Popen(
                    final_cmd, 
                    stdout=subprocess.DEVNULL, 
                    stderr=f_err, 
                    env=env,
                    pass_fds=pipes_fds
                )
                # Write fake data and close write ends
                os.write(w1, f"{fake_vendor}\n".encode())
                os.close(w1)
                os.write(w2, f"{fake_model}\n".encode())
                os.close(w2)
                
                # Close read ends in parent
                os.close(r1)
                os.close(r2)
            else:
                tg_process = subprocess.Popen(
                    final_cmd, stdout=subprocess.DEVNULL, stderr=f_err, env=env
                )
        return tg_process, gost_process
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        if pipes_fds:
            for fd in [r1, r2, w1, w2]:
                try:
                    os.close(fd)
                except:
                    pass
        if gost_process:
            gost_process.terminate()
        return None, None


def stop_telegram(
    tg_process: Optional[subprocess.Popen],
    gost_process: Optional[subprocess.Popen] = None,
) -> bool:
    """Корректное завершение процессов Telegram и gost"""
    processes = [p for p in [tg_process, gost_process] if p is not None]
    for p in processes:
        try:
            p.terminate()
            p.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                p.kill()
            except Exception:
                pass
        except Exception:
            pass
    return True


def is_process_running(process: Optional[subprocess.Popen]) -> bool:
    """Проверка, активен ли процесс в данный момент"""
    return process is not None and process.poll() is None


def open_explorer(workdir: Union[str, Path]) -> bool:
    """Открытие папки аккаунта в файловом менеджере Thunar"""
    workdir = Path(workdir)
    if not workdir.exists():
        workdir.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.Popen(["thunar", str(workdir)])
        return True
    except Exception as e:
        logger.error(f"Ошибка открытия Thunar: {e}")
        return False


def clear_cache(workdir: Union[str, Path]) -> Tuple[bool, str]:
    """Очистка временных файлов и кэша в папке профиля"""
    workdir = Path(workdir)
    if not workdir.exists():
        return False, "Папка не существует"

    cache_dirs = ["cache", "media_cache", "thumbnails", "temp"]
    deleted_count = 0

    try:
        for cache_dir in cache_dirs:
            cache_path = workdir / cache_dir
            if cache_path.exists():
                shutil.rmtree(cache_path)
                deleted_count += 1
        return True, f"Успешно очищено {deleted_count} папок."
    except Exception as e:
        return False, str(e)


def _build_final_command(
    tg_cmd: List[str],
    device_name: Optional[str],
    fake_vendor: Optional[str] = None,
    fake_model: Optional[str] = None,
    pipes_fds: Optional[Tuple[int, int]] = None
) -> List[str]:
    """Построение финальной команды для запуска"""
    if fake_vendor and fake_model and pipes_fds and shutil.which("bwrap"):
        r1, r2 = pipes_fds
        bwrap_cmd = [
            "bwrap",
            "--dev-bind", "/", "/",
            "--ro-bind-data", str(r1), "/sys/devices/virtual/dmi/id/sys_vendor",
            "--ro-bind-data", str(r2), "/sys/devices/virtual/dmi/id/product_name"
        ]
        if device_name:
            bwrap_cmd.extend(["--unshare-uts", "--hostname", device_name])
        return bwrap_cmd + tg_cmd

    if device_name and shutil.which("firejail"):
        firejail_cmd = [
            "firejail",
            "--noprofile",
            "--quiet",
            f"--hostname={device_name}",
            "--nodbus",
            "--env=DBUS_SESSION_BUS_ADDRESS=",
            "--env=DBUS_SYSTEM_BUS_ADDRESS=",
        ]
        return firejail_cmd + tg_cmd
    elif device_name and shutil.which("unshare"):
        set_hostname_py = (
            "import ctypes, socket; "
            "try: "
            "  libc=ctypes.CDLL('libc.so.6'); "
            f" name=b'{device_name}'; "
            "  libc.sethostname(name, len(name)); "
            "except Exception: pass"
        )
        inner_cmd = " ".join(f'"{c}"' for c in tg_cmd)
        return [
            "unshare",
            "--uts",
            "--map-root-user",
            "sh",
            "-c",
            f'python3 -c "{set_hostname_py}" && exec {inner_cmd}',
        ]
    else:
        return tg_cmd


