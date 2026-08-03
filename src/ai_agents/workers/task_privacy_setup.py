import asyncio
from hydrogram import Client, raw
from src.core.logger import logger
from src.core.managers.account_manager import update_privacy_guard
from src.core.constants import CONFIG_FILE

async def run(client: Client, params: dict, context: dict) -> bool:
    """
    Воркер: Устанавливает жесткие настройки приватности (скрывает номер и т.д.)
    """
    try:
        me = await client.get_me()
        logger.info(f"[{me.first_name}] Воркер task_privacy_setup запущен.")

        # 1. Скрываем номер телефона (Никто)
        await client.invoke(
            raw.functions.account.SetPrivacy(
                key=raw.types.InputPrivacyKeyPhoneNumber(),
                rules=[raw.types.InputPrivacyValueDisallowAll()]
            )
        )

        # 2. Кто может добавлять в группы (Только контакты)
        await client.invoke(
            raw.functions.account.SetPrivacy(
                key=raw.types.InputPrivacyKeyChatInvite(),
                rules=[raw.types.InputPrivacyValueAllowContacts()]
            )
        )

        # 3. Время последнего входа (Никто)
        await client.invoke(
            raw.functions.account.SetPrivacy(
                key=raw.types.InputPrivacyKeyStatusTimestamp(),
                rules=[raw.types.InputPrivacyValueDisallowAll()]
            )
        )

        # 4. Кто может звонить (Только контакты)
        await client.invoke(
            raw.functions.account.SetPrivacy(
                key=raw.types.InputPrivacyKeyPhoneCall(),
                rules=[raw.types.InputPrivacyValueAllowContacts()]
            )
        )
        
        logger.info(f"[{me.first_name}] ✅ Приватность успешно настроена!")
        
        # Обновляем БД
        update_privacy_guard(CONFIG_FILE, client.workdir, True)
        
        return True
        
    except Exception as e:
        logger.error(f"Ошибка в task_privacy_setup: {e}")
        return False
