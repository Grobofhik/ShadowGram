from src.core.base_module import BaseModule
from hydrogram import raw, enums
from src.core.managers.account_manager import update_privacy_guard

"""
Модуль «Privacy Guard» (Защита приватности).
Функции:

- run: автоматическая настройка приватности через низкоуровневые вызовы API (invoke)
"""

class PrivacyGuardPlugin(BaseModule):
    MODULE_NAME = "🛡️ Privacy Guard"
    MODULE_DESC = "Устанавливает жесткие настройки приватности: никто не видит номер, в группы — только контакты."
    
    async def run(self, **kwargs):
        if not await self.init_client():
            return

        try:
            self.log("Настраиваю приватность через API...", "info")
            
            # Настройки, которые мы будем применять
            # PrivacyValueNobody - никто
            # PrivacyValueAllowContacts - только контакты
            
            # 1. Скрываем номер телефона (Никто)
            self.log("Скрываю номер телефона...", "info")
            await self.client.invoke(
                raw.functions.account.SetPrivacy(
                    key=raw.types.InputPrivacyKeyPhoneNumber(),
                    rules=[raw.types.InputPrivacyValueDisallowAll()]
                )
            )

            # 2. Кто может добавлять в группы (Только контакты)
            self.log("Ограничиваю приглашения в группы...", "info")
            await self.client.invoke(
                raw.functions.account.SetPrivacy(
                    key=raw.types.InputPrivacyKeyChatInvite(),
                    rules=[raw.types.InputPrivacyValueAllowContacts()]
                )
            )

            # 3. Время последнего входа (Никто)
            self.log("Скрываю статус 'был в сети'...", "info")
            await self.client.invoke(
                raw.functions.account.SetPrivacy(
                    key=raw.types.InputPrivacyKeyStatusTimestamp(),
                    rules=[raw.types.InputPrivacyValueDisallowAll()]
                )
            )

            # 4. Кто может звонить (Только контакты)
            self.log("Ограничиваю звонки...", "info")
            await self.client.invoke(
                raw.functions.account.SetPrivacy(
                    key=raw.types.InputPrivacyKeyPhoneCall(),
                    rules=[raw.types.InputPrivacyValueAllowContacts()]
                )
            )
            
            update_privacy_guard(self.config_file, self.workdir, True)
            self.log("Приватность успешно настроена!", "success")
            
        except Exception as e:
            self.log(f"Ошибка настройки: {e}", "error")
        finally:
            await self.cleanup()