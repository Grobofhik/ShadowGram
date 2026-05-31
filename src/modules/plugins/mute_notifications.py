import asyncio
from src.core.base_module import BaseModule
from hydrogram import raw

"""
Модуль «🔕 Mute All» (Отключение уведомлений).
Функции:
- Отключение глобальных уведомлений для личных сообщений, групп и каналов.
- Массовое отключение уведомлений во всех текущих диалогах пользователя.
"""

class MuteNotificationsPlugin(BaseModule):
    MODULE_NAME = "🔕 Mute All"
    MODULE_DESC = "Выключает уведомления во всех чатах, группах и каналах (навсегда)."
    
    # Параметры не требуются, модуль работает со всеми чатами сразу
    PARAMS = []

    async def run(self, **kwargs):
        # 1. Инициализация клиента
        if not await self.init_client():
            return

        try:
            self.log("Начинаю массовое отключение уведомлений...", "info")
            
            # Настройки: отключаем звук (silent=True) и ставим mute_until на максимум (навсегда)
            # 2147483647 — это максимальное значение int32, которое Telegram интерпретирует как "навсегда"
            mute_settings = raw.types.InputPeerNotifySettings(
                mute_until=2147483647,
                silent=True
            )
            
            # 2. Глобальные настройки (для новых контактов/чатов)
            self.log("Применяю глобальные настройки (Личные сообщения, Группы, Каналы)...", "info")
            
            # Для личных сообщений
            await self.client.invoke(
                raw.functions.account.UpdateNotifySettings(
                    peer=raw.types.InputNotifyUsers(),
                    settings=mute_settings
                )
            )
            
            # Для обычных групп
            await self.client.invoke(
                raw.functions.account.UpdateNotifySettings(
                    peer=raw.types.InputNotifyChats(),
                    settings=mute_settings
                )
            )
            
            # Для каналов и супергрупп
            await self.client.invoke(
                raw.functions.account.UpdateNotifySettings(
                    peer=raw.types.InputNotifyBroadcasts(),
                    settings=mute_settings
                )
            )
            
            self.log("Глобальные настройки обновлены.", "success")

            # 3. Обработка текущих диалогов
            self.log("Начинаю сканирование текущих диалогов...", "info")
            
            muted_count = 0
            async for dialog in self.client.get_dialogs():
                try:
                    # Разрешаем peer для низкоуровневого вызова
                    target_peer = await self.client.resolve_peer(dialog.chat.id)
                    
                    await self.client.invoke(
                        raw.functions.account.UpdateNotifySettings(
                            peer=raw.types.InputNotifyPeer(peer=target_peer),
                            settings=mute_settings
                        )
                    )
                    
                    muted_count += 1
                    if muted_count % 10 == 0:
                        self.log(f"Обработано диалогов: {muted_count}...", "info")
                        
                    # Небольшая пауза, чтобы не поймать FloodWait
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    chat_name = dialog.chat.title or dialog.chat.first_name or str(dialog.chat.id)
                    self.log(f"Не удалось заглушить '{chat_name}': {e}", "warning")

            self.log(f"Готово! Все уведомления отключены ({muted_count} активных диалогов).", "success")
            
        except Exception as e:
            self.log(f"Критическая ошибка в работе модуля: {e}", "error")
        finally:
            # 4. Всегда закрываем клиент и очищаем ресурсы
            await self.cleanup()
