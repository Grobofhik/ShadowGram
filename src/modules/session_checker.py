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


from src.core.utils import get_free_port

def _find_session_file(workdir: Path) -> Optional[Path]:
    from src.core.utils import find_session_file
    path_str = find_session_file(str(workdir))
    return Path(path_str) if path_str else None


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
        if client:
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
    
    client: Optional[Client] = None
    gost_process: Optional[subprocess.Popen] = None
    
    if not api_id or not str(api_id).isdigit():
        return "Error", "Некорректный API ID в настройках"
    if not api_hash:
        return "Error", "Некорректный API Hash в настройках"
        
    workdir = Path(workdir)
    session_file = _find_session_file(workdir)
    
    if not session_file:
        return "NoSession", "Файл .session не найден"

    proxy_settings: Optional[Dict[str, Any]] = None
    
    try:
        if proxy_url:
            is_socks = proxy_url.startswith("socks5://") or proxy_url.startswith("socks4://")
            if is_socks:
                from src.core.logic import parse_proxy_url
                proxy_settings = parse_proxy_url(proxy_url)
            else:
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
            await asyncio.wait_for(client.connect(), timeout=15.0)
        except asyncio.TimeoutError:
            return "Error", "Превышено время ожидания подключения (проверьте прокси или сеть)"
        me = await client.get_me()
        client.me = me
        
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
