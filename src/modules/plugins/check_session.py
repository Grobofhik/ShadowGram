from typing import Any
from pathlib import Path
from src.core.base_module import BaseModule
from hydrogram.errors import UserDeactivated, AuthKeyUnregistered, Unauthorized
from hydrogram import raw
from src.core.managers.account_manager import update_privacy_guard

"""
Модуль проверки работоспособности сессий.
Функции:

- run: проверка авторизации сессии, детектирование бана и загрузка аватара
"""

class SessionCheckPlugin(BaseModule):
    MODULE_NAME: str = "🔍 Проверка сессии"
    MODULE_DESC: str = "Проверяет статус сессии, наличие бана и загружает аватарку."

    async def run(self, **kwargs: Any) -> None:
        """Проверка авторизации сессии, детектирование бана и загрузка аватара"""
        # 1. Инициализируем клиента (база сама найдет .session и поднимет прокси)
        if not await self.init_client():
            return

        try:
            self.log("Подключение установлено, запрашиваю данные профиля...", "info")
            me = await self.client.get_me()
            
            # Если есть фото — качаем его
            await self._download_avatar(me)
            
            # Проверяем спамблок
            self.log("Проверяю ограничения через @SpamBot...", "info")
            from src.modules.session_checker import _check_spamblock
            spamblock_status = await _check_spamblock(self.client)
                
            if spamblock_status == "SPAM BLOCK":
                self.log(f"Статус: АКТИВЕН (@{me.username or me.id}) | SPAM BLOCK", "warning")
            else:
                self.log(f"Статус: АКТИВЕН (@{me.username or me.id}) | Без ограничений", "success")
                
            # Проверяем настройки приватности (Privacy Guard)
            self.log("Проверяю статус Privacy Guard...", "info")
            try:
                privacy = await self.client.invoke(raw.functions.account.GetPrivacy(
                    key=raw.types.InputPrivacyKeyPhoneNumber()
                ))
                is_guarded = False
                for rule in privacy.rules:
                    if isinstance(rule, raw.types.PrivacyValueDisallowAll):
                        is_guarded = True
                        break
                
                update_privacy_guard(self.config_file, self.workdir, is_guarded)
                
                if is_guarded:
                    self.log("🛡️ Privacy Guard: АКТИВИРОВАН (Номер скрыт)", "success")
                else:
                    self.log("⚠️ Privacy Guard: НЕ АКТИВЕН (Уязвимость!)", "warning")
            except Exception as e:
                self.log(f"Не удалось проверить приватность: {e}", "warning")
            
            
        except UserDeactivated:
            self.log("Аккаунт в БАНЕ (Deactivated)", "error")
        except (AuthKeyUnregistered, Unauthorized):
            self.log("Сессия невалидна (Unauthorized)", "error")
        except Exception as e:
            self.log(f"Ошибка выполнения: {e}", "error")
        finally:
            # Всегда чистим за собой
            await self.cleanup()
    
    async def _download_avatar(self, me: Any) -> None:
        """Загружает аватар пользователя если есть"""
        if me.photo and self.workdir:
            avatar_dest = Path(self.workdir) / "avatar.jpg"
            try:
                await self.client.download_media(me.photo.big_file_id, file_name=str(avatar_dest))
                self.log("Аватарка успешно обновлена!", "success")
            except Exception:
                pass
