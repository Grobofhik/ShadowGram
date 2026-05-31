import asyncio
import random
from src.core.base_module import BaseModule
from hydrogram.errors import FloodWait, RPCError

"""
Модуль «📥 Масс-Фолловер» (Follower).
Массово подписывает аккаунты на указанные каналы и чаты.
Поддерживает как публичные юзернеймы (@durov), так и приватные инвайт-ссылки (https://t.me/+...).
"""

class FollowerPlugin(BaseModule):
    MODULE_NAME = "📥 Масс-Фолловер"
    MODULE_DESC = "Массово подписывает аккаунты на каналы и чаты по списку ссылок. Поддерживает приватные инвайты."
    
    PARAMS = [
        {"name": "chat_links", "type": "textarea", "label": "Ссылки на каналы/чаты (по одной в строке)"},
        {"name": "min_delay", "type": "text", "label": "Мин. задержка между вступлениями (сек)"},
        {"name": "max_delay", "type": "text", "label": "Макс. задержка между вступлениями (сек)"}
    ]

    async def run(self, **kwargs):
        links_raw = kwargs.get("chat_links", "")
        links = [l.strip() for l in links_raw.split("\n") if l.strip()]
        
        if not links:
            self.log("Список ссылок пуст! Укажите хотя бы одну ссылку.", "warning")
            return
            
        try:
            d_min = int(kwargs.get("min_delay", 5))
            d_max = int(kwargs.get("max_delay", 15))
        except ValueError:
            self.log("Задержки указаны неверно, использую стандартные (5-15 сек).", "warning")
            d_min, d_max = 5, 15

        if not await self.init_client():
            return

        try:
            self.log(f"Найдено {len(links)} ссылок для вступления. Начинаю работу...", "info")

            for i, link in enumerate(links):
                try:
                    self.log(f"Пробую вступить: {link}", "info")
                    
                    # Очищаем ссылку от лишних символов, если юзер случайно их скопировал
                    clean_link = link.replace(" ", "")
                    
                    chat = await self.client.join_chat(clean_link)
                    self.log(f"✅ Успешно вступил в чат: {chat.title}", "success")
                    
                except FloodWait as e:
                    self.log(f"⚠️ Слишком много запросов (FloodWait). Жду {e.value} сек...", "warning")
                    await self.sleep(e.value)
                    
                    # Пробуем еще раз после ожидания
                    try:
                        chat = await self.client.join_chat(clean_link)
                        self.log(f"✅ Успешно вступил после ожидания: {chat.title}", "success")
                    except RPCError as ex:
                        if "INVITE_REQUEST_SENT" in str(ex):
                            self.log(f"✅ Заявка на вступление успешно отправлена (ожидает одобрения): {clean_link}", "success")
                        else:
                            self.log(f"❌ Не удалось вступить даже после ожидания: {ex}", "error")
                    except Exception as ex:
                        self.log(f"❌ Не удалось вступить даже после ожидания: {ex}", "error")
                        
                except RPCError as e:
                    # Типичные ошибки Telegram
                    if "USER_ALREADY_PARTICIPANT" in str(e):
                        self.log(f"ℹ️ Аккаунт уже состоит в этом чате: {clean_link}", "info")
                    elif "INVITE_HASH_EXPIRED" in str(e) or "INVITE_HASH_INVALID" in str(e):
                        self.log(f"❌ Приватная ссылка недействительна или истекла: {clean_link}", "error")
                    elif "USERNAME_INVALID" in str(e) or "USERNAME_NOT_OCCUPIED" in str(e):
                        self.log(f"❌ Неверный юзернейм или канал не существует: {clean_link}", "error")
                    elif "INVITE_REQUEST_SENT" in str(e):
                        self.log(f"✅ Заявка на вступление успешно отправлена (ожидает одобрения): {clean_link}", "success")
                    else:
                        self.log(f"❌ Ошибка Telegram API при вступлении в {clean_link}: {e}", "warning")
                        
                except Exception as e:
                    self.log(f"❌ Неизвестная ошибка: {e}", "error")

                # Задержка перед следующим вступлением (кроме последнего)
                if i < len(links) - 1:
                    wait_time = random.randint(d_min, d_max)
                    self.log(f"⏳ Пауза {wait_time} сек. перед следующим каналом...", "info")
                    await self.sleep(wait_time)

            self.log("🎯 Работа Масс-Фолловера завершена!", "success")
            
        finally:
            await self.cleanup()
