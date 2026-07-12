import asyncio
import json
import random
import requests
import traceback
from typing import List, Dict

from PyQt6.QtCore import QThread, pyqtSignal
from hydrogram import Client
from hydrogram.errors import RPCError, PeerIdInvalid, ChannelPrivate

from src.core.constants import CONFIG_FILE

class NeuroEngineThread(QThread):
    # Сигналы для обновления UI
    # account_name, status_message
    status_updated = pyqtSignal(str, str)
    # Сигнал об ошибке или завершении
    stopped = pyqtSignal()

    def __init__(self, selected_accounts: List[str], parent=None):
        super().__init__(parent)
        self.selected_accounts = selected_accounts
        self.is_running = True
        self.loop = None
        self.tasks = []
        
        # Кэш истории (channel_id -> last_post_id) для каждого аккаунта
        # { 'acc1': { '@durov': 1234 } }
        self.history = {}

    def get_settings(self) -> Dict:
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception:
            return {}

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        settings = self.get_settings()
        neuro_settings = settings.get("settings", {}).get("neuro_v2", {})
        
        api_key = settings.get("settings", {}).get("default_ai_api_key", "")
        if not api_key:
            for acc in self.selected_accounts:
                self.status_updated.emit(acc, "Ошибка: Не указан API ключ ИИ (настройки)")
            self.stopped.emit()
            return

        self.loop.run_until_complete(self.run_all_accounts(neuro_settings, api_key, settings))
        self.loop.close()
        self.stopped.emit()

    def stop(self):
        self.is_running = False
        self.status_updated.emit("ALL", "Останавливаем процессы...")

    async def run_all_accounts(self, neuro_settings, api_key, full_settings):
        # Собираем данные об аккаунтах
        accounts_data = {acc.get("name"): acc for acc in full_settings.get("accounts", [])}
        
        for acc_name in self.selected_accounts:
            acc_info = accounts_data.get(acc_name)
            if not acc_info:
                self.status_updated.emit(acc_name, "Аккаунт не найден в конфиге")
                continue
                
            task = self.loop.create_task(self.account_worker(acc_name, acc_info, neuro_settings, api_key))
            self.tasks.append(task)
            
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)

    async def _generate_comment(self, post_text: str, prompt: str, api_key: str, context_comments: list = None) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        ctx_str = ""
        if context_comments:
            ctx_str = "\n\nРЕАКЦИЯ ТОЛПЫ (ПОСЛЕДНИЕ КОММЕНТАРИИ): \n- " + "\n- ".join(context_comments)
            ctx_str += "\nТвоя задача: гармонично влиться в дискуссию, учитывая мнение толпы."
            
        payload = {
            "contents": [{
                "parts": [{"text": f"SYSTEM PROMPT: {prompt}\n\nPOST TEXT:\n{post_text}{ctx_str}"}]
            }],
            "generationConfig": {
                "temperature": 0.8,
                "maxOutputTokens": 200,
            }
        }
        
        for attempt in range(3):
            loop = asyncio.get_running_loop()
            try:
                response = await loop.run_in_executor(None, lambda: requests.post(url, json=payload, timeout=15))
                if response.status_code == 503:
                    await asyncio.sleep(5)
                    continue
                response.raise_for_status()
                data = response.json()
                
                comment = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                return comment
            except Exception as e:
                print(f"[{attempt}] Ошибка генерации: {e}")
                await asyncio.sleep(2)
        return ""

    async def account_worker(self, account_name, acc_info, neuro_settings, api_key):
        self.status_updated.emit(account_name, "Инициализация сессии...")
        self.history[account_name] = {}
        
        channels = [c.strip() for c in neuro_settings.get("channels", "").split() if c.strip()]
        if not channels:
            self.status_updated.emit(account_name, "Ошибка: нет каналов для комментинга")
            return
            
        prompts = neuro_settings.get("account_prompts", {}).get(account_name, [])
        if not prompts:
            prompts = ["Ты обычный пользователь Telegram, прокомментируй пост коротко и по факту."]
            
        workdir = acc_info.get("workdir")
        if not workdir:
            self.status_updated.emit(account_name, "Ошибка: не найден workdir")
            return

        from src.core.managers.proxy_manager import parse_proxy_url
        from src.core.managers.account_manager import get_hardware_profile

        proxy_dict = None
        gost_process = None
        proxy_url = acc_info.get("proxy_url")
        if proxy_url:
            is_socks = proxy_url.startswith("socks5://") or proxy_url.startswith("socks4://")
            if is_socks:
                proxy_dict = parse_proxy_url(proxy_url)
            else:
                from src.modules.session_checker import _setup_proxy
                gost_process, proxy_dict = await _setup_proxy(proxy_url)

        from src.modules.session_checker import _find_session_file
        from pathlib import Path
        session_file = _find_session_file(Path(workdir))
        if not session_file:
            logger.error(f"Файл сессии не найден для {account_name}")
            if gost_process:
                gost_process.terminate()
                gost_process.wait()
            return
            
        hw = get_hardware_profile(CONFIG_FILE, workdir)

        client = Client(
            name=session_file.stem,
            workdir=str(session_file.parent),
            api_id=acc_info.get("api_id"),
            api_hash=acc_info.get("api_hash"),
            proxy=proxy_dict,
            app_version=hw.get("app_version", "1.0"),
            device_model=hw.get("device_model", acc_info.get("device_name", "PC")),
            system_version=hw.get("system_version", "Windows"),
            lang_code=hw.get("lang_code", "en"),
            no_updates=True
        )
        
        try:
            await client.start()
            self.status_updated.emit(account_name, "Успешный вход в сессию")
        except Exception as e:
            self.status_updated.emit(account_name, f"Ошибка входа: {e}")
            return
            
        try:
            while self.is_running:
                for target_channel in channels:
                    if not self.is_running:
                        break
                        
                    self.status_updated.emit(account_name, f"Проверка канала {target_channel}...")
                    
                    try:
                        # Получаем последний пост
                        async for msg in client.get_chat_history(target_channel, limit=1):
                            last_post = msg
                            break
                        else:
                            last_post = None
                            
                        if last_post:
                            last_id = self.history[account_name].get(target_channel, 0)
                            if last_post.id > last_id:
                                # Это новый пост!
                                self.status_updated.emit(account_name, "Найден новый пост! Анализируем...")
                                
                                post_text = last_post.text or last_post.caption or "[Медиа/Без текста]"
                                active_prompt = random.choice(prompts)
                                
                                # Задержка перед генерацией
                                sub_delay = neuro_settings.get("sub_delay", 30)
                                wait_time = random.randint(int(sub_delay * 0.8), int(sub_delay * 1.2))
                                self.status_updated.emit(account_name, f"Чтение поста... пауза {wait_time} сек")
                                await asyncio.sleep(wait_time)
                                
                                if not self.is_running: break
                                
                                self.status_updated.emit(account_name, "Генерация ИИ-комментария...")
                                
                                context_comments = []
                                discussion_msg = None
                                try:
                                    discussion_msg = await client.get_discussion_message(target_channel, last_post.id)
                                    if neuro_settings.get("read_history", True):
                                        async for reply in client.get_chat_history(discussion_msg.chat.id, reply_to_message_id=discussion_msg.id, limit=10):
                                            if reply.text:
                                                context_comments.append(reply.text)
                                        # Reverse to get chronological order
                                        context_comments = context_comments[::-1]
                                except Exception as e:
                                    print(f"Could not read discussion history: {e}")
                                
                                comment = await self._generate_comment(post_text, active_prompt, api_key, context_comments)
                                
                                if comment and discussion_msg:
                                    com_delay = neuro_settings.get("com_delay", 60)
                                    wait_time_com = random.randint(int(com_delay * 0.8), int(com_delay * 1.2))
                                    self.status_updated.emit(account_name, f"Набор текста... {wait_time_com} сек")
                                    
                                    from hydrogram.enums import ChatAction
                                    # Отправляем действие "Печатает..." несколько раз во время задержки
                                    for i in range(0, wait_time_com, 5):
                                        if not self.is_running: break
                                        try:
                                            await client.send_chat_action(discussion_msg.chat.id, ChatAction.TYPING)
                                        except Exception:
                                            pass
                                        await asyncio.sleep(min(5, wait_time_com - i))
                                    
                                    if not self.is_running: break
                                    
                                    self.status_updated.emit(account_name, "Отправка комментария...")
                                    try:
                                        await discussion_msg.reply(comment)
                                        self.status_updated.emit(account_name, f"✅ Комментарий отправлен")
                                    except Exception as e:
                                        self.status_updated.emit(account_name, f"❌ Ошибка отправки: Комментарии закрыты?")
                                else:
                                    self.status_updated.emit(account_name, "⚠️ ИИ не сгенерировал текст")
                                    
                                # Запоминаем пост
                                self.history[account_name][target_channel] = last_post.id
                            else:
                                self.status_updated.emit(account_name, f"Нет новых постов в {target_channel}")
                        
                    except Exception as e:
                        self.status_updated.emit(account_name, f"Ошибка с {target_channel}: {str(e)[:30]}")
                        
                    # Задержка между каналами
                    chan_min = neuro_settings.get("chan_delay_min", 60)
                    chan_max = neuro_settings.get("chan_delay_max", 120)
                    wait_chan = random.randint(chan_min, chan_max)
                    self.status_updated.emit(account_name, f"Ожидание {wait_chan} сек до след. канала...")
                    
                    for _ in range(wait_chan):
                        if not self.is_running: break
                        await asyncio.sleep(1)

                if self.is_running:
                    self.status_updated.emit(account_name, "Цикл завершён, пауза 30 сек...")
                    for _ in range(30):
                        if not self.is_running: break
                        await asyncio.sleep(1)
                        
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass
            if gost_process:
                try:
                    gost_process.terminate()
                    gost_process.wait()
                except:
                    pass
            self.status_updated.emit(account_name, "Остановлен")
