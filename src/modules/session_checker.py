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
        from src.core.managers.proxy_manager import normalize_proxy_url
        import json
        import os
        normalized_url = normalize_proxy_url(proxy_url)
        # Create config file in a temporary location since session checker might run outside specific workdirs, or we can use /tmp
        import tempfile
        fd, config_path = tempfile.mkstemp(suffix=".json", prefix="gost_")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({
                "ServeNodes": [f"socks5://127.0.0.1:{local_port}"],
                "ChainNodes": [normalized_url]
            }, f)
            
        gost_process = subprocess.Popen(
            ["gost", "-L", f"socks5://127.0.0.1:{local_port}", "-F", normalized_url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
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


async def _check_spamblock(client: Any) -> str:
    """Проверка наличия спамблока через официального бота @SpamBot"""
    try:
        # Отправляем /start боту @SpamBot
        sent_msg = await client.send_message("SpamBot", "/start")
        
        # Ждем ответа от бота в течение максимум 5 секунд (10 итераций по 0.5 сек)
        for _ in range(10):
            await asyncio.sleep(0.5)
            async for message in client.get_chat_history("SpamBot", limit=5):
                if (message.from_user and 
                    message.from_user.username == "SpamBot" and 
                    message.id > sent_msg.id):
                    text = message.text or ""
                    text_lower = text.lower()
                    
                    if ("no limits" in text_lower or 
                        "свободен от каких-либо ограничений" in text_lower or 
                        "абсолютно свободен" in text_lower or 
                        "ограничения не наложены" in text_lower or
                        "каких-либо ограничений" in text_lower):
                        return "Отсутствует"
                    else:
                        # Попробуем вытащить первую значимую строчку
                        lines = [line.strip() for line in text.split("\n") if line.strip()]
                        for line in lines:
                            if "ограничен" in line.lower() or "limit" in line.lower() or "блокиров" in line.lower():
                                return "SPAM BLOCK"
                        return "SPAM BLOCK"
        
        # Если новое сообщение не пришло, проверим последнее сообщение в истории
        async for message in client.get_chat_history("SpamBot", limit=3):
            if message.from_user and message.from_user.username == "SpamBot":
                text = message.text or ""
                text_lower = text.lower()
                if ("no limits" in text_lower or 
                    "свободен от каких-либо ограничений" in text_lower or 
                    "абсолютно свободен" in text_lower or 
                    "каких-либо ограничений" in text_lower):
                    return "Отсутствует"
                return "SPAM BLOCK"
        
        return "Нет ответа от @SpamBot"
    except Exception as e:
        return "Ошибка проверки"


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
                from src.core.managers.proxy_manager import parse_proxy_url
                proxy_settings = parse_proxy_url(proxy_url)
            else:
                gost_process, proxy_settings = await _setup_proxy(proxy_url)

        from src.core.constants import CONFIG_FILE
        from src.core.managers.account_manager import get_hardware_profile
        from src.core.managers.runtime_hw_manager import apply_runtime_hw_overrides

        hw_profile = apply_runtime_hw_overrides(get_hardware_profile(CONFIG_FILE, workdir))

        client = Client(
            name=session_file.stem,
            api_id=int(api_id),
            api_hash=api_hash,
            workdir=str(session_file.parent),
            proxy=proxy_settings,
            device_model=hw_profile.get("device_model", "PC 64bit"),
            system_version=hw_profile.get("system_version", "Windows 10"),
            app_version=hw_profile.get("app_version", "4.8.4 x64"),
            lang_code=hw_profile.get("lang_code", "en"),
        )

        try:
            await asyncio.wait_for(client.connect(), timeout=15.0)
        except asyncio.TimeoutError:
            return "Error", "Превышено время ожидания подключения (проверьте прокси или сеть)"
        me = await client.get_me()
        client.me = me
        
        # Загружаем аватар если есть
        await _download_avatar(client, me, workdir)
        
        # Получаем полные данные (Bio, Username и т.д.)
        bio = ""
        try:
            full_me = await client.get_chat("me")
            if hasattr(full_me, "bio") and full_me.bio:
                bio = full_me.bio
        except Exception:
            pass
            
        channel_name = None
        channel_link = None
        
        try:
            from hydrogram.raw.functions.users import GetFullUser
            from hydrogram.raw.types import InputUserSelf
            
            full_user_req = await client.invoke(GetFullUser(id=InputUserSelf()))
            personal_channel_id = getattr(full_user_req.full_user, "personal_channel_id", None)
            
            if personal_channel_id:
                chat_id = int(f"-100{personal_channel_id}")
                channel = await client.get_chat(chat_id)
                channel_name = channel.title
                if channel.username:
                    channel_link = f"https://t.me/{channel.username}"
                elif getattr(channel, "invite_link", None):
                    channel_link = channel.invite_link
                
                if channel.photo:
                    avatar_path = Path(workdir) / "channel_avatar.jpg"
                    if not avatar_path.exists():
                        await client.download_media(channel.photo.big_file_id, file_name=str(avatar_path))
        except Exception as e:
            logger.debug(f"Failed to fetch personal channel info: {e}")
            
        from src.core.constants import CONFIG_FILE
        from src.core.managers.account_manager import update_account_profile_data
        
        update_account_profile_data(
            config_file=CONFIG_FILE,
            workdir=workdir,
            first_name=me.first_name or "",
            last_name=me.last_name or "",
            bio=bio or "",
            bound_channel=None,
            username=me.username or "",
            phone=me.phone_number or "",
            channel_name=channel_name or "",
            channel_link=channel_link or ""
        )
        
        # Проверяем наличие спамблока через @SpamBot
        spamblock_status = await _check_spamblock(client)
            
        await client.disconnect()
        return "Alive", f"Активен (@{me.username or me.id}) | {spamblock_status}"
        
    except UserDeactivated: 
        return "Banned", "Аккаунт в БАНЕ"
    except (AuthKeyUnregistered, Unauthorized): 
        return "Unauthorized", "Сессия вылетела"
    except Exception as e: 
        return "Error", str(e)
    finally:
        await _cleanup_resources(client, gost_process)
