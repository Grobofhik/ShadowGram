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

def get_proxy_geo_info(proxy_url: str) -> Tuple[Optional[str], Optional[str]]:
    """Выполняет запрос через прокси к ip-api.com для получения timezone и countryCode"""
    import urllib.request
    import urllib.error
    from urllib.parse import urlparse
    import json
    
    if not proxy_url:
        return None, None
        
    try:
        normalized = normalize_proxy_url(proxy_url)
        parsed = urlparse(normalized)
        
        # Если это SOCKS прокси, используем PySocks для прямого HTTP запроса
        if parsed.scheme and parsed.scheme.startswith("socks"):
            try:
                import socks
                proxy_type = socks.SOCKS5 if parsed.scheme == "socks5" else socks.SOCKS4
                s = socks.socksocket()
                s.set_proxy(
                    proxy_type, 
                    parsed.hostname, 
                    parsed.port, 
                    username=parsed.username, 
                    password=parsed.password
                )
                s.settimeout(3.0)
                s.connect(("ip-api.com", 80))
                
                request = b"GET /json HTTP/1.1\r\nHost: ip-api.com\r\nUser-Agent: Mozilla/5.0\r\nConnection: close\r\n\r\n"
                s.sendall(request)
                
                response = b""
                while True:
                    chunk = s.recv(1024)
                    if not chunk:
                        break
                    response += chunk
                s.close()
                
                # Извлекаем тело HTTP ответа
                parts = response.split(b"\r\n\r\n", 1)
                if len(parts) == 2:
                    body = parts[1]
                    data = json.loads(body.decode('utf-8', errors='ignore'))
                    if data.get("status") == "success":
                        return data.get("timezone"), data.get("countryCode")
            except Exception as socks_e:
                logger.warning(f"Ошибка Geo-IP через SOCKS прокси {proxy_url}: {socks_e}")
        else:
            # Для HTTP/HTTPS прокси используем стандартный urllib
            proxy_handler = urllib.request.ProxyHandler({
                'http': normalized,
                'https': normalized
            })
            opener = urllib.request.build_opener(proxy_handler)
            opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
            
            with opener.open("http://ip-api.com/json", timeout=3.0) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data.get("status") == "success":
                    return data.get("timezone"), data.get("countryCode")
    except Exception as e:
        logger.warning(f"Не удалось определить гео-данные прокси {proxy_url}: {e}")
        
    return None, None


def map_country_code_to_locale(country_code: str) -> str:
    """Отображает код страны в подходящую локаль"""
    if not country_code:
        return "en_US.UTF-8"
        
    cc = country_code.upper()
    mapping = {
        "RU": "ru_RU.UTF-8",
        "UA": "uk_UA.UTF-8",
        "BY": "be_BY.UTF-8",
        "KZ": "kk_KZ.UTF-8",
        "DE": "de_DE.UTF-8",
        "FR": "fr_FR.UTF-8",
        "GB": "en_GB.UTF-8",
        "US": "en_US.UTF-8",
        "IT": "it_IT.UTF-8",
        "ES": "es_ES.UTF-8",
        "PL": "pl_PL.UTF-8",
        "TR": "tr_TR.UTF-8",
        "BR": "pt_BR.UTF-8",
        "CN": "zh_CN.UTF-8",
        "NL": "nl_NL.UTF-8",
    }
    return mapping.get(cc, f"{cc.lower()}_{cc}.UTF-8")


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

    logger.error(f"[DEBUG] fake_vendor={fake_vendor}, fake_model={fake_model}, device_name={device_name}")

    gost_process: Optional[subprocess.Popen] = None
    tg_bin = (
        shutil.which("telegram-desktop")
        or shutil.which("Telegram")
        or "telegram-desktop"
    )
    logger.error(f"[DEBUG] Telegram binary: {tg_bin} (exists={Path(tg_bin).exists() if '/' in tg_bin else 'which-fallback'})")
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

    # Определение таймзоны и локали по прокси (Geo-IP)
    timezone, country_code = None, None
    if proxy_url:
        timezone, country_code = get_proxy_geo_info(proxy_url)

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

    if timezone:
        env["TZ"] = timezone
        logger.info(f"[STEALTH] Подмена часового пояса на: {timezone}")
    if country_code:
        locale_str = map_country_code_to_locale(country_code)
        env["LANG"] = locale_str
        env["LC_ALL"] = locale_str
        logger.info(f"[STEALTH] Подмена локали на: {locale_str}")

    if device_name:
        env["HOSTNAME"] = device_name
            
    # Ensure DISPLAY and XAUTHORITY are inherited for Qt XCB GUI
    if "DISPLAY" in os.environ:
        env["DISPLAY"] = os.environ["DISPLAY"]
    if "XAUTHORITY" in os.environ:
        env["XAUTHORITY"] = os.environ["XAUTHORITY"]
    if "WAYLAND_DISPLAY" in os.environ:
        env["WAYLAND_DISPLAY"] = os.environ["WAYLAND_DISPLAY"]
    if "XDG_RUNTIME_DIR" in os.environ:
        env["XDG_RUNTIME_DIR"] = os.environ["XDG_RUNTIME_DIR"]

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
            for fd in [r1, w1, r2, w2]:
                if fd is not None:
                    try:
                        os.close(fd)
                    except:
                        pass
            r1, w1, r2, w2 = None, None, None, None
            pipes_fds = None

    final_cmd = _build_final_command(tg_cmd, device_name, fake_vendor, fake_model, pipes_fds, timezone)
    logger.error(f"[DEBUG] Final command: {' '.join(str(c) for c in final_cmd)}")
    logger.error(f"[DEBUG] pipes_fds={pipes_fds}")

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

        logger.error(f"[DEBUG] Telegram process started: pid={tg_process.pid}, alive={tg_process.poll() is None}")
        
        # Check if process died immediately
        import time
        time.sleep(1.0)
        exit_code = tg_process.poll()
        if exit_code is not None:
            logger.error(f"[DEBUG] Telegram process DIED immediately! exit_code={exit_code}")
            try:
                with open(err_log, "r") as f:
                    err_content = f.read().strip()
                if err_content:
                    logger.error(f"[DEBUG] stderr: {err_content[:1000]}")
            except Exception:
                pass
        else:
            logger.error(f"[DEBUG] Telegram process alive after 1s, pid={tg_process.pid}")

        return tg_process, gost_process
    except Exception as e:
        logger.error(f"[DEBUG] Критическая ошибка при запуске Telegram: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"[DEBUG] Traceback:\n{traceback.format_exc()}")
        if pipes_fds:
            for fd in [r1, r2, w1, w2]:
                if fd is not None:
                    try:
                        os.close(fd)
                    except:
                        pass
        if gost_process:
            gost_process.terminate()
        return None, None


def kill_processes_by_workdir(workdir: Union[str, Path]) -> None:
    """Поиск и принудительное завершение всех процессов, запущенных с указанным -workdir"""
    import signal
    
    try:
        workdir_path = Path(workdir).resolve()
        workdir_str = str(workdir_path)
    except Exception:
        workdir_str = str(workdir)
        
    workdir_raw = str(workdir)
    matched_pids = []
    
    try:
        # Сбор всех подходящих PID
        for pid_dir in os.listdir('/proc'):
            if not pid_dir.isdigit():
                continue
            try:
                pid = int(pid_dir)
                if pid == os.getpid():
                    continue
                cmdline_path = os.path.join('/proc', pid_dir, 'cmdline')
                if not os.path.exists(cmdline_path):
                    continue
                with open(cmdline_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                args = [a for a in content.split('\x00') if a]
                
                has_workdir = False
                for i, arg in enumerate(args):
                    if arg == '-workdir' and i + 1 < len(args):
                        val = args[i + 1]
                        try:
                            val_abs = str(Path(val).resolve())
                        except Exception:
                            val_abs = val
                        if val_abs == workdir_str or val == workdir_raw:
                            has_workdir = True
                            break
                
                if has_workdir:
                    matched_pids.append(pid)
            except Exception:
                continue
    except Exception as e:
        logger.error(f"Ошибка при поиске процессов по workdir: {e}")
        return

    if not matched_pids:
        return

    logger.warning(f"[DEBUG] Найдено {len(matched_pids)} процессов для workdir {workdir_str}. Завершаем PIDs: {matched_pids}")
    
    # Отправляем SIGTERM
    for pid in matched_pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except Exception as e:
            logger.error(f"Не удалось отправить SIGTERM процессу {pid}: {e}")

    # Ждем завершения процессов (до 1 секунды)
    start_time = time.time()
    while time.time() - start_time < 1.0:
        still_running = []
        for pid in matched_pids:
            if os.path.exists(f"/proc/{pid}"):
                still_running.append(pid)
        if not still_running:
            break
        time.sleep(0.1)

    # Если кто-то выжил, отправляем SIGKILL
    for pid in matched_pids:
        if os.path.exists(f"/proc/{pid}"):
            try:
                os.kill(pid, signal.SIGKILL)
                logger.warning(f"[DEBUG] Процесс {pid} принудительно убит через SIGKILL")
            except ProcessLookupError:
                pass
            except Exception as e:
                logger.error(f"Не удалось отправить SIGKILL процессу {pid}: {e}")


def stop_telegram(
    tg_process: Optional[subprocess.Popen],
    gost_process: Optional[subprocess.Popen] = None,
    workdir: Optional[Union[str, Path]] = None,
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

    if workdir:
        kill_processes_by_workdir(workdir)

    return True


def is_process_running(process: Optional[subprocess.Popen]) -> bool:
    """Проверка, активен ли процесс в данный момент"""
    return process is not None and process.poll() is None


def open_explorer(workdir: Union[str, Path]) -> bool:
    """Открытие папки аккаунта в файловом менеджере"""
    workdir = Path(workdir)
    if not workdir.exists():
        workdir.mkdir(parents=True, exist_ok=True)
        
    file_managers = ["thunar", "nautilus", "dolphin", "nemo", "xdg-open", "explorer.exe"]
    
    for fm in file_managers:
        if shutil.which(fm):
            try:
                subprocess.Popen([fm, str(workdir)])
                return True
            except Exception as e:
                logger.error(f"Ошибка открытия {fm}: {e}")
                continue
                
    logger.error("Не найден ни один из поддерживаемых файловых менеджеров.")
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
    pipes_fds: Optional[Tuple[int, ...]] = None,
    timezone: Optional[str] = None
) -> List[str]:
    """Построение финальной команды для запуска"""
    if fake_vendor and fake_model and pipes_fds and shutil.which("bwrap"):
        r1, r2 = pipes_fds[0], pipes_fds[1]
        bwrap_cmd = [
            "bwrap",
            "--dev-bind", "/", "/",
            "--ro-bind-data", str(r1), "/sys/devices/virtual/dmi/id/sys_vendor",
            "--ro-bind-data", str(r2), "/sys/devices/virtual/dmi/id/product_name"
        ]
        
        # Ensure X11 socket is available inside bwrap if present
        if Path("/tmp/.X11-unix").exists():
            bwrap_cmd.extend(["--bind", "/tmp/.X11-unix", "/tmp/.X11-unix"])
            
        # Подмена таймзоны внутри контейнера bwrap
        if timezone:
            host_zoneinfo = Path("/usr/share/zoneinfo") / timezone
            if host_zoneinfo.exists():
                bwrap_cmd.extend(["--ro-bind", str(host_zoneinfo), "/etc/localtime"])

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
        if timezone:
            firejail_cmd.append(f"--env=TZ={timezone}")
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


