import asyncio
import socket
import subprocess
from typing import Tuple, Optional, Dict, Any, Union
from pathlib import Path

"""
Модуль проверки статуса сессий Telegram.
Функции:

- get_free_port: получение свободного порта для прокси-туннеля
- check_account: асинхронная проверка работоспособности сессии и загрузка аватара
"""


def get_free_port() -> int:
    """Получает свободный порт для прокси-туннеля"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _find_session_file(workdir: Path) -> Optional[Path]:
    search_paths = [
        workdir,
        workdir / "tdata",
        workdir / "tdata" / "user_data",
    ]

    for path in search_paths:
        if path.exists():
            for f in path.iterdir():
                if f.is_file() and f.suffix == ".session":
                    return f.with_suffix("")
    return None


async def _setup_proxy(proxy_url: str) -> Tuple[Optional[subprocess.Popen], Optional[Dict[str, Any]]]:
    local_port = get_free_port()
    try:
        gost_process = subprocess.Popen(
            ["gost", "-L", f"socks5://127.0.0.1:{local_port}", "-F", proxy_url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proxy_settings = {
            "scheme": "socks5",
            "hostname": "127.0.0.1",
            "port": local_port,
        }
        await asyncio.sleep(1.5)
        return gost_process, proxy_settings
    except:  # noqa: E722
        return None, None


async def _download_avatar(client: Any, me: Any, workdir: Path) -> None:
    if me.photo:
        avatar_dest = workdir / "avatar.jpg"
        if avatar_dest.exists():
            return
        try:
            await client.download_media(me.photo.big_file_id, file_name=str(avatar_dest))
        except:  # noqa: E722
            pass


async def _cleanup_resources(client: Any, gost_process: Optional[subprocess.Popen]) -> None:
    try:
        await client.disconnect()
    except:  # noqa: E722
        pass
    if gost_process:
        gost_process.terminate()
        gost_process.wait()


async def check_account(
    workdir: Union[str, Path], 
    api_id: str, 
    api_hash: str, 
    proxy_url: Optional[str] = None, 
    device_name: str = "ShadowGram-PC"
) -> Tuple[str, str]:
    """Асинхронная проверка работоспособности сессии и загрузка аватара
    
    Args:
        workdir: Рабочая директория аккаунта
        api_id: Telegram API ID
        api_hash: Telegram API Hash
        proxy_url: URL прокси (опционально)
        device_name: Имя устройства
        
    Returns:
        Tuple[str, str]: (статус, сообщение)
    """
    
    from hydrogram import Client
    from hydrogram.errors import UserDeactivated, AuthKeyUnregistered, Unauthorized
    
    workdir = Path(workdir)
    session_file = _find_session_file(workdir)
    
    if not session_file:
        return "NoSession", "Файл .session не найден"

    gost_process: Optional[subprocess.Popen] = None
    proxy_settings: Optional[Dict[str, Any]] = None
    
    if proxy_url:
        gost_process, proxy_settings = await _setup_proxy(proxy_url)

    client = Client(
        name=session_file.stem,
        api_id=int(api_id),
        api_hash=api_hash,
        workdir=str(session_file.parent),
        proxy=proxy_settings,
        device_model=device_name or "PC",
        system_version="Arch Linux"
    )

    try:
        await client.connect()
        me = await client.get_me()
        
        # Загружаем аватар если есть
        await _download_avatar(client, me, workdir)
            
        await client.disconnect()
        return "Alive", f"Активен (@{me.username or me.id})"
        
    except UserDeactivated: 
        return "Banned", "Аккаунт в БАНЕ"
    except (AuthKeyUnregistered, Unauthorized): 
        return "Unauthorized", "Сессия вылетела"
    except Exception as e: 
        return "Error", str(e)
    finally:
        await _cleanup_resources(client, gost_process)
