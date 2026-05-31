import asyncio
import random
from typing import Any
from src.core.base_module import BaseModule
from src.modules.plugins.auto_reactor import AutoReactor
from src.modules.plugins.ai_commenter import AICommenter
from src.modules.plugins.channel_viewer import ChannelViewerPlugin

"""
Модуль «Channel Monitor» (Мониторинг канала 24/7).
Следит за выбранным каналом и при появлении нового поста автоматически 
запускает просмотры, реакции и нейрокомментинг.
"""

class ChannelMonitorPlugin(BaseModule):
    MODULE_NAME = "👁️ Мониторинг канала (24/7)"
    MODULE_DESC = "Непрерывно следит за каналом 24/7. При появлении нового поста автоматически накручивает просмотры, ставит реакции и пишет AI-комментарии."
    
    PARAMS = [
        {"name": "channel_url", "type": "text", "label": "Ссылка на канал (@username или https://t.me/...)"},
        {"name": "check_interval", "type": "text", "label": "Интервал проверки на новые посты (сек)"},
        
        {"name": "do_views", "type": "checkbox", "label": "Накручивать просмотры"},
        {"name": "do_reactions", "type": "checkbox", "label": "Ставить реакции"},
        {"name": "reaction_chance", "type": "text", "label": "Шанс реакции (0-100%)"},
        
        {"name": "do_comments", "type": "checkbox", "label": "Писать AI-комментарии"},
        {"name": "comment_chance", "type": "text", "label": "Шанс комментария (0-100%)"},
        
        {"name": "api_key", "type": "text", "label": "API Ключ (для нейросети)"},
        {"name": "api_base_url", "type": "text", "label": "API Base URL"},
        {"name": "model_name", "type": "text", "label": "Название AI модели"}
    ]
    
    IS_CYCLIC = False # Цикл реализуем внутри run() для полного контроля
    START_DELAY = (30, 120)

    async def run(self, **kwargs: Any) -> Any:
        channel_url = kwargs.get("channel_url", "").strip().replace("https://t.me/", "").replace("@", "")
        if not channel_url:
            self.log("Укажите ссылку на канал!", "error")
            return
            
        try:
            interval = int(kwargs.get("check_interval", "30"))
        except ValueError:
            interval = 30
        interval = max(5, interval) # Не менее 5 секунд, чтобы избежать флуда
        
        do_views = kwargs.get("do_views", False)
        do_reactions = kwargs.get("do_reactions", False)
        do_comments = kwargs.get("do_comments", False)
        
        r_chance = kwargs.get("reaction_chance", "100")
        c_chance = kwargs.get("comment_chance", "100")
        
        api_key = kwargs.get("api_key", "")
        api_base_url = kwargs.get("api_base_url", "")
        model_name = kwargs.get("model_name", "")
        
        try:
            chat = await self.client.get_chat(channel_url)
            self.log(f"Начинаю мониторинг канала: {chat.title} (24/7)", "success")
            
            # Получаем ID последнего сообщения
            last_msg_id = 0
            async for msg in self.client.get_chat_history(chat.id, limit=1):
                last_msg_id = msg.id
                
            self.log(f"Последний пост ID: {last_msg_id}. Ожидание новых...", "info")
            
            # Подготавливаем инстансы других модулей
            reactor = AutoReactor(self.acc, self.api_id, self.api_hash, self.log_callback)
            reactor.client = self.client
            reactor.gost_process = self.gost_process
            reactor.local_port = self.local_port
            
            commenter = AICommenter(self.acc, self.api_id, self.api_hash, self.log_callback)
            commenter.client = self.client
            commenter.gost_process = self.gost_process
            commenter.local_port = self.local_port
            
            viewer = ChannelViewerPlugin(self.acc, self.api_id, self.api_hash, self.log_callback)
            viewer.client = self.client
            viewer.gost_process = self.gost_process
            viewer.local_port = self.local_port
            
            while True:
                await self.sleep(interval)
                
                try:
                    new_msgs = []
                    async for msg in self.client.get_chat_history(chat.id, limit=5):
                        if msg.id > last_msg_id:
                            new_msgs.append(msg)
                        else:
                            break
                            
                    if new_msgs:
                        # Сортируем от старых к новым (чтобы обрабатывать по порядку)
                        new_msgs.reverse()
                        
                        for msg in new_msgs:
                            self.log(f"🔔 ОБНАРУЖЕН НОВЫЙ ПОСТ! ID: {msg.id}", "success")
                            last_msg_id = max(last_msg_id, msg.id)
                            
                            # Имитируем небольшую задержку реакции (реальные пользователи не читают мгновенно)
                            delay = random.uniform(5, 20)
                            self.log(f"Имитация реакции человека: жду {delay:.1f} сек...", "info")
                            await self.sleep(delay)
                            
                            if do_views:
                                self.log(f"👀 Накручиваю просмотр...", "info")
                                await viewer.run(channel_link=channel_url, post_limit="1")
                                
                            if do_reactions:
                                self.log(f"❤️ Ставлю реакцию...", "info")
                                await reactor.run(channel_url=channel_url, posts_count="1", reaction_chance=str(r_chance))
                                
                            if do_comments:
                                self.log(f"📝 Генерирую комментарий...", "info")
                                await commenter.run(
                                    channel_url=channel_url, 
                                    api_key=api_key, 
                                    api_base_url=api_base_url, 
                                    model_name=model_name, 
                                    posts_count="1", 
                                    comment_chance=str(c_chance)
                                )
                                
                        self.log("✅ Обработка новых постов завершена. Продолжаю мониторинг.", "success")
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    self.log(f"Ошибка при проверке обновлений: {e}", "warning")
                    
        except asyncio.CancelledError:
            self.log("Мониторинг канала остановлен.", "info")
            raise
        except Exception as e:
            self.log(f"Критическая ошибка мониторинга: {e}", "error")
