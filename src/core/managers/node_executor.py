import os
import asyncio
import random
from typing import Dict, Any, Callable
from src.core.base_module import BaseModule
from hydrogram.errors import FloodWait, RPCError

# Shared file-line rotation registry for all executor instances
FILE_LINES_LOCK = asyncio.Lock()
FILE_LINES_CACHE = {}  # { file_path: [lines] }
FILE_LINE_CURSORS = {}  # { file_path: current_index }

class NodeScenarioExecutor(BaseModule):
    MODULE_NAME = "Node Executor"
    MODULE_DESC = "Исполнитель визуальных графов сценариев"

    def __init__(
        self,
        account_data: Dict[str, Any],
        api_id: str,
        api_hash: str,
        log_callback: Callable[[str], None],
        graph_data: Dict[str, Any]
    ) -> None:
        super().__init__(account_data, api_id, api_hash, log_callback)
        self.graph = graph_data
        
        # Локальный контекст переменных для текущей сессии аккаунта
        self.variables = {
            "me_name": self.acc.get("name", ""),
            "me_workdir": str(self.workdir or ""),
            "me_proxy": self.proxy_url or ""
        }
        
        # Наследование параметров контекста
        self.last_bot_username = ""
        self.last_chat_id = ""
        self.last_message_id = None

    async def get_next_line_from_file(self, file_path: str) -> str:
        if not file_path:
            return ""
            
        global FILE_LINES_LOCK, FILE_LINES_CACHE, FILE_LINE_CURSORS
        
        async with FILE_LINES_LOCK:
            abs_path = os.path.abspath(file_path)
            if abs_path not in FILE_LINES_CACHE:
                if os.path.exists(abs_path):
                    try:
                        with open(abs_path, "r", encoding="utf-8") as f:
                            lines = [line.strip() for line in f if line.strip()]
                        FILE_LINES_CACHE[abs_path] = lines
                        FILE_LINE_CURSORS[abs_path] = 0
                        self.log(f"Файл ротации '{os.path.basename(abs_path)}' успешно загружен ({len(lines)} строк).", "success")
                    except Exception as e:
                        self.log(f"⚠️ Ошибка чтения файла '{abs_path}': {e}", "error")
                        FILE_LINES_CACHE[abs_path] = []
                        FILE_LINE_CURSORS[abs_path] = 0
                else:
                    self.log(f"⚠️ Файл для ротации '{abs_path}' не найден!", "warning")
                    FILE_LINES_CACHE[abs_path] = []
                    FILE_LINE_CURSORS[abs_path] = 0
                    
            lines = FILE_LINES_CACHE[abs_path]
            if not lines:
                return ""
                
            idx = FILE_LINE_CURSORS[abs_path]
            if idx < len(lines):
                val = lines[idx]
                FILE_LINE_CURSORS[abs_path] += 1
                return val
            else:
                # Wrap around and start from index 0 again
                val = lines[0]
                FILE_LINE_CURSORS[abs_path] = 1
                return val

    async def init_client(self) -> bool:
        success = await super().init_client()
        if success and self.client:
            def wrap_sender(method, method_name):
                async def wrapper(*args, **kwargs):
                    res = await method(*args, **kwargs)
                    if res:
                        if hasattr(res, "chat") and res.chat:
                            self.last_message_id = res.id
                            self.last_chat_id = str(res.chat.id)
                        elif hasattr(res, "id"):
                            if method_name in ["create_group", "create_channel"]:
                                self.last_chat_id = str(res.id)
                            else:
                                self.last_message_id = res.id
                    elif len(args) > 0 and isinstance(args[0], (str, int)):
                        self.last_chat_id = str(args[0])
                    return res
                return wrapper
                
            for name in ["send_message", "send_photo", "send_video", "send_document", 
                         "send_voice", "send_audio", "send_animation", "send_sticker", 
                         "send_location", "create_group", "create_channel", "send_dice"]:
                original = getattr(self.client, name, None)
                if original:
                    setattr(self.client, name, wrap_sender(original, name))
        return success

    def resolve_string(self, text: str) -> str:
        """Подставляет переменные {var_name} в строку и вычисляет spintax"""
        if not isinstance(text, str):
            return text
            
        import random
        # 1. Шаблонизация переменных (сначала локальные, затем глобальные)
        res = text
        for k, v in self.variables.items():
            res = res.replace(f"{{{k}}}", str(v))
            
        if hasattr(self.__class__, "GLOBAL_VARIABLES"):
            for k, v in self.__class__.GLOBAL_VARIABLES.items():
                res = res.replace(f"{{{k}}}", str(v))
                
        # 2. Обработка Spintax {выбор1|выбор2}
        if "{" in res and "|" in res:
            while "{" in res and "}" in res:
                start_idx = res.rfind("{")
                end_idx = res.find("}", start_idx)
                choices = res[start_idx+1:end_idx].split("|")
                res = res[:start_idx] + random.choice(choices) + res[end_idx+1:]
                
        return res

    async def keep_online(self):
        """Отправляет запрос обновления статуса, чтобы аккаунт выглядел Онлайн"""
        try:
            from hydrogram.raw.functions.account import UpdateStatus
            await self.client.invoke(UpdateStatus(offline=False))
        except Exception:
            pass

    async def sleep(self, seconds: float):
        # Перед паузой обновляем статус в сети
        await self.keep_online()
        await super().sleep(seconds)

    async def generate_ai_text(self, prompt: str, system_prompt: str = "Ответь вежливо.") -> str:
        """Запрос к OpenAI-совместимому API для ИИ-блоков"""
        from src.core.constants import CONFIG_FILE
        from src.core.managers.config_manager import _read_config
        import requests
        
        cfg = _read_config(CONFIG_FILE)
        settings = cfg.get("settings", {})
        
        api_key = settings.get("default_ai_api_key", "").strip()
        api_url = settings.get("default_ai_base_url", "https://api.groq.com/openai/v1").strip().rstrip("/")
        model_name = settings.get("default_ai_model", "llama-3.1-8b-instant").strip()
        
        if not api_key:
            self.log("Ошибка: В глобальных настройках отсутствует API-ключ ИИ!", "error")
            return ""
            
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 150,
            "temperature": 0.7
        }
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.post(f"{api_url}/chat/completions", headers=headers, json=payload, timeout=20)
            )
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content'].strip()
            else:
                self.log(f"Ошибка ИИ API {response.status_code}: {response.text}", "error")
        except Exception as e:
            self.log(f"Ошибка сети ИИ-запроса: {e}", "error")
            
        return ""

    async def run(self, **kwargs):
        # 1. Инициализация клиента (прокси, туннель, подключение)
        if not await self.init_client():
            self.log("Не удалось подключить Telegram-клиент для этого аккаунта.", "error")
            return

        try:
            self.log("Запуск выполнения визуального сценария графа...", "info")
            
            # Маппинг нод по ID
            self.nodes = {n["id"]: n for n in self.graph.get("nodes", [])}
            nodes = self.nodes
            
            # Маппинг соединений: (from_node_id, from_port_name) -> список to_node_id
            self.connections_list = self.graph.get("connections", [])
            connections = {}
            for conn in self.connections_list:
                key = (conn["from_node"], conn["from_port"])
                if key not in connections:
                    connections[key] = []
                connections[key].append(conn["to_node"])
                
            # Поиск стартовой ноды
            start_node = next((n for n in nodes.values() if n["type"] == "start"), None)
            if not start_node:
                self.log("Ошибка: На холсте не обнаружен блок 'Старт'!", "error")
                return

            # Шаги выполнения
            self.step_count = 0
            self.max_steps = 50000
            
            # Импортируем реестр обработчиков действий
            from src.core.node_actions import ACTION_HANDLERS
            import collections
            
            # Очередь активных задач
            self.queue = collections.deque([start_node["id"]])
            queue = self.queue
            
            # Стек блоков Try/Catch
            if not hasattr(self, "try_catch_stack"):
                self.try_catch_stack = []
            
            while queue:
                node_id = queue.popleft()
                
                self.step_count += 1
                if self.step_count >= self.max_steps:
                    self.log(f"Превышен лимит шагов ({self.max_steps}). Прерывание сценария.", "warning")
                    break
                    
                node = nodes.get(node_id)
                if not node:
                    continue
                self.current_node = node
                    
                node_type = node["type"]
                node_params = dict(node.get("params", {}))
                
                # Автоматическое наследование контекстных параметров
                if "bot_username" in node_params:
                    val = self.resolve_string(str(node_params["bot_username"])).strip()
                    if not val and self.last_bot_username:
                        node_params["bot_username"] = self.last_bot_username
                        self.log(f"[Контекст]: Унаследован bot_username: {self.last_bot_username}", "info")
                    elif val:
                        self.last_bot_username = val
                        
                if "chat_id" in node_params:
                    val = self.resolve_string(str(node_params["chat_id"])).strip()
                    if not val and self.last_chat_id:
                        node_params["chat_id"] = self.last_chat_id
                        self.log(f"[Контекст]: Унаследован chat_id: {self.last_chat_id}", "info")
                    elif val:
                        self.last_chat_id = val
                        
                if "to_chat_id" in node_params:
                    val = self.resolve_string(str(node_params["to_chat_id"])).strip()
                    if not val and self.last_chat_id:
                        node_params["to_chat_id"] = self.last_chat_id
                        self.log(f"[Контекст]: Унаследован to_chat_id: {self.last_chat_id}", "info")
                    elif val:
                        self.last_chat_id = val
                        
                if "message_id" in node_params:
                    val_raw = node_params.get("message_id")
                    val_str = self.resolve_string(str(val_raw)).strip() if val_raw is not None else ""
                    if (not val_str or val_str == "0" or val_str == "") and self.last_message_id is not None:
                        node_params["message_id"] = self.last_message_id
                        self.log(f"[Контекст]: Унаследован message_id: {self.last_message_id}", "info")
                    elif val_str and val_str.isdigit():
                        self.last_message_id = int(val_str)
                        
                if "chat_link" in node_params:
                    val = self.resolve_string(str(node_params["chat_link"])).strip()
                    if not val and getattr(self, "last_chat_link", None):
                        node_params["chat_link"] = self.last_chat_link
                        self.log(f"[Контекст]: Унаследована ссылка на канал/чат (chat_link): {self.last_chat_link}", "info")
                    elif val:
                        self.last_chat_link = val
                        self.last_channel_url = val
                        
                node_title = node.get("title", node_type)
                
                self.log(f"Шаг {self.step_count}: Блок '{node_title}' ({node_type})", "info")
                
                next_port = "next"
                try:
                    await self.keep_online()
                    handler = ACTION_HANDLERS.get(node_type)
                    if handler:
                        next_port = await handler(self, node_params)
                    else:
                        self.log(f"Ошибка: Не найден обработчик для блока '{node_type}'!", "error")
                        next_port = None
                except FloodWait as flood:
                    self.log(f"⚠️ Ограничение Telegram (FloodWait). Ждем {flood.value} сек...", "warning")
                    await self.sleep(flood.value)
                    # Повторяем шаг после паузы
                    self.step_count -= 1
                    queue.appendleft(node_id)
                    continue
                except RPCError as rpc:
                    self.log(f"Ошибка API Telegram: {rpc}", "error")
                    next_port = None
                except Exception as node_err:
                    self.log(f"Ошибка при обработке блока: {node_err}", "error")
                    next_port = None
                    
                if next_port:
                    next_nodes = connections.get((node_id, next_port), [])
                    for next_id in next_nodes:
                        queue.append(next_id)
                else:
                    # Попытка найти активный блок Try/Catch для перехвата ошибки
                    if getattr(self, "try_catch_stack", []):
                        catch_node_id = self.try_catch_stack.pop()
                        self.log(f"Перехват ошибки! Возврат к блоку Try/Catch...", "warning")
                        queue.clear()
                        catch_nodes = connections.get((catch_node_id, "error"), [])
                        for next_id in catch_nodes:
                            queue.append(next_id)
                    else:
                        self.log("Ветка сценария прервана из-за ошибки (Try/Catch не найден).", "error")

        except Exception as e:
            self.log(f"Критическая ошибка сценария: {e}", "error")
        finally:
            # Освобождаем зависшие мьютексы
            if hasattr(self, "acquired_locks") and hasattr(self.__class__, "GLOBAL_LOCKS"):
                for lock_name in list(self.acquired_locks):
                    l = self.__class__.GLOBAL_LOCKS.get(lock_name)
                    if l and l.locked():
                        try:
                            l.release()
                        except RuntimeError:
                            pass
                self.acquired_locks.clear()
                
            await self.cleanup()
            self.log("Очистка завершена. Процесс выполнения остановлен.", "info")
