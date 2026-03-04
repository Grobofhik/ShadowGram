import asyncio
from typing import Tuple, Optional
from src.modules import session_checker

"""
Синхронная обертка для асинхронных проверок аккаунтов.
Функции:

- run_check: запуск асинхронной проверки сессии в отдельном цикле событий (event loop)
"""


def run_check(
    workdir: str, api_id: str, api_hash: str, proxy_url: Optional[str] = None
) -> Tuple[str, str]:
    """Запуск асинхронной проверки сессии в отдельном цикле событий

    Args:
        workdir: Рабочая директория аккаунта
        api_id: Telegram API ID
        api_hash: Telegram API Hash
        proxy_url: URL прокси (опционально)

    Returns:
        Tuple[str, str]: (статус, сообщение)
    """
    try:
        if not api_id or not api_hash:
            return "ConfigError", "API ID или API Hash не установлены!"

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                session_checker.check_account(workdir, api_id, api_hash, proxy_url)
            )
            return result
        finally:
            loop.close()
            asyncio.set_event_loop(None)
    except Exception as e:
        return "Error", str(e)
