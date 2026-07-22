import os
import sys
import asyncio
import importlib
from pathlib import Path

# Добавляем корень проекта в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from hydrogram import Client
from src.core.logger import logger
from src.core.managers import config_manager
from src.core.constants import CONFIG_FILE

from src.ai_agents.scouts.file_scout import FileScout
from src.ai_agents.scouts.tg_scout import TelegramScout
from src.ai_agents.brain.orchestrator import AIOrchestrator

class AIRunner:
    """
    ГЛАВНЫЙ ОРКЕСТРАТОР (Связующее звено).
    Объединяет Фазу 1 (Скауты), Фазу 2 (Мозг) и Фазу 3 (Воркеры).
    """
    def __init__(self, api_key: str, api_base_url: str = None, model_name: str = None):
        self.api_key = api_key
        self.api_base_url = api_base_url
        self.model_name = model_name
        self.config_data = config_manager._read_config(Path(CONFIG_FILE))
        # Кэш состояния фермы, чтобы не сканировать при каждом сообщении
        self.cached_farm_state = None
        
    async def get_farm_state(self, force_refresh=False):
        if not self.cached_farm_state or force_refresh:
            logger.info("🤖 [Фаза 1.1] Запуск File Scout (Быстрый аудит диска)...")
            f_scout = FileScout()
            base_state = f_scout.run_audit()
            
            logger.info("🤖 [Фаза 1.2] Запуск Telegram Scout (Глубокий аудит активных аккаунтов)...")
            t_scout = TelegramScout(base_state)
            self.cached_farm_state = await t_scout.run_audit()
        return self.cached_farm_state

    async def chat_async(self, user_message: str):
        """
        Отправляет сообщение пользователя и состояние фермы в ИИ-Мозг.
        Возвращает ответ ИИ и сгенерированный план.
        """
        logger.info("🤖 === АНАЛИЗ ФЕРМЫ И ОБЩЕНИЕ С ИИ ===")
        farm_state = await self.get_farm_state()
        
        logger.info("🤖 [Фаза 2] Запрос к ИИ-Оркестратору (Генерация ответа и плана)...")
        orchestrator = AIOrchestrator(
            api_key=self.api_key, 
            api_base_url=self.api_base_url, 
            model_name=self.model_name
        )
        
        bot_msg, plan, mutations = orchestrator.chat_with_agent(user_message, farm_state)
        
        if plan or mutations:
            logger.info(f"🤖 Получен план (задач: {len(plan)}, мутаций конфига: {len(mutations)}).")
            
        return bot_msg, plan, mutations, farm_state

    async def execute_plan_async(self, plan: list, mutations: list = None):
        """
        Фаза 3: Выполнение ранее сгенерированного плана и мутаций конфига.
        """
        if not plan and not mutations:
            logger.warning("🤖 План пуст, нечего выполнять.")
            return
            
        logger.info("🤖 === ЗАПУСК ИИ-АВТОМАТИЗАЦИИ (ФАЗА 3) ===")
        
        if mutations:
            logger.info("🤖 Применяем прямые изменения в config.json и Telegram...")
            await self._execute_mutations(mutations)
            
        if plan:
            await self._execute_plan(plan)
            
        logger.info("🤖 === ИИ-СИСТЕМА УСПЕШНО ЗАВЕРШИЛА РАБОТУ ===")
        # Сбрасываем кэш, так как состояние фермы изменилось
        self.cached_farm_state = None

    async def _execute_mutations(self, mutations: list):
        """Прямое изменение параметров в config.json и Telegram по требованию ИИ"""
        changed = False
        for mut in mutations:
            workdirs = mut.get("workdirs", [])
            changes = mut.get("changes", {})
            if not changes or not workdirs:
                continue
                
            for acc in self.config_data.get("accounts", []):
                acc_dir_name = Path(acc["workdir"]).name
                if "all" in workdirs or acc["workdir"] in workdirs or acc_dir_name in workdirs:
                    tg_updates = {}
                    for k, v in changes.items():
                        # Для пароля обновляем cloud_password в папке аккаунта (если нужно)
                        if k == "password":
                            cfg_path = Path(acc["workdir"]) / "config.json"
                            if cfg_path.exists():
                                try:
                                    import json
                                    with open(cfg_path, "r", encoding="utf-8") as f:
                                        data = json.load(f)
                                    data["cloud_password"] = v
                                    with open(cfg_path, "w", encoding="utf-8") as f:
                                        json.dump(data, f, indent=4)
                                except:
                                    pass
                        # И обновляем в главном config.json
                        acc[k] = v
                        if k in ["first_name", "last_name", "bio", "username"]:
                            tg_updates[k] = v
                            
                    changed = True
                    logger.info(f"🤖 [Config] Обновлены параметры для {acc.get('name', 'Unknown')}: {list(changes.keys())}")
                    
                    if tg_updates:
                        logger.info(f"🤖 Применяем изменения профиля {acc.get('name', 'Unknown')} в Telegram...")
                        try:
                            from src.core.managers import proxy_manager
                            from src.core.managers.account_manager import get_hardware_profile
                            from src.core.constants import CONFIG_FILE
                            
                            proxy_dict = None
                            gost_process = None
                            proxy_url = acc.get("proxy_url")
                            if proxy_url:
                                is_socks = proxy_url.startswith("socks5://") or proxy_url.startswith("socks4://")
                                if is_socks:
                                    proxy_dict = proxy_manager.parse_proxy_url(proxy_url)
                                else:
                                    from src.modules.session_checker import _setup_proxy
                                    gost_process, proxy_dict = await _setup_proxy(proxy_url)
                                
                            from src.modules.session_checker import _find_session_file
                            
                            workdir_path = Path(acc["workdir"])
                            session_file = _find_session_file(workdir_path)
                            
                            if not session_file:
                                logger.error(f"Файл сессии не найден для {acc['workdir']}")
                                continue
                                
                            from src.core.managers.runtime_hw_manager import apply_runtime_hw_overrides

                            hw_profile = apply_runtime_hw_overrides(
                                get_hardware_profile(CONFIG_FILE, acc["workdir"])
                            )
                                
                            client = Client(
                                name=session_file.stem,
                                workdir=str(session_file.parent),
                                api_id=acc.get("api_id"),
                                api_hash=acc.get("api_hash"),
                                proxy=proxy_dict,
                                device_model=hw_profile.get("device_model", "PC 64bit"),
                                system_version=hw_profile.get("system_version", "Windows 10"),
                                app_version=hw_profile.get("app_version", "4.8.4 x64"),
                                lang_code=hw_profile.get("lang_code", "en"),
                                sleep_threshold=60,
                                max_concurrent_transmissions=1
                            )
                            await client.connect()
                            
                            # Обновляем first_name, last_name, bio
                            profile_kwargs = {}
                            if "first_name" in tg_updates: profile_kwargs["first_name"] = tg_updates["first_name"]
                            if "last_name" in tg_updates: profile_kwargs["last_name"] = tg_updates["last_name"]
                            if "bio" in tg_updates: profile_kwargs["bio"] = tg_updates["bio"]
                            
                            if profile_kwargs:
                                await client.update_profile(**profile_kwargs)
                                
                            # Обновляем username
                            if "username" in tg_updates:
                                un = tg_updates["username"]
                                if un:
                                    await client.set_username(un.replace('@', ''))
                                else:
                                    await client.set_username(None)
                                    
                            await client.disconnect()
                            logger.info(f"🤖 Успешно обновлен профиль Telegram для {acc.get('name', 'Unknown')}")
                        except Exception as e:
                            logger.error(f"🤖 Ошибка применения профиля Telegram для {acc.get('name', 'Unknown')}: {e}")
                        finally:
                            try:
                                await client.disconnect()
                            except:
                                pass
                            if gost_process:
                                try:
                                    gost_process.terminate()
                                except:
                                    pass
                    
        if changed:
            config_manager._write_config(Path(CONFIG_FILE), self.config_data)
            logger.info("🤖 config.json успешно обновлен!")

    async def _execute_plan(self, plan: list):
        for acc_schedule in plan:
            workdir = acc_schedule.get("workdir")
            schedule = acc_schedule.get("schedule", [])
            
            if not workdir or not schedule:
                continue
                
            acc_config = next((a for a in self.config_data.get("accounts", []) if a["workdir"] == workdir or Path(a["workdir"]).name == Path(workdir).name), None)
            if not acc_config:
                logger.error(f"❌ Не найден конфиг для {workdir}")
                continue
                
            acc_name = acc_config.get("name", "Unknown")
            # Update workdir to the absolute path for execution to succeed
            workdir = acc_config["workdir"]
            logger.info(f"\n🤖 --- [Аккаунт: {acc_name}] Начало работы ---")
            
            from src.core.managers import proxy_manager
            
            proxy_dict = None
            gost_process = None
            proxy_url = acc_config.get("proxy_url")
            if proxy_url:
                is_socks = proxy_url.startswith("socks5://") or proxy_url.startswith("socks4://")
                if is_socks:
                    proxy_dict = proxy_manager.parse_proxy_url(proxy_url)
                else:
                    from src.modules.session_checker import _setup_proxy
                    gost_process, proxy_dict = await _setup_proxy(proxy_url)
            
            from src.modules.session_checker import _find_session_file
            
            workdir_path = Path(workdir)
            session_file = _find_session_file(workdir_path)
            
            if not session_file:
                logger.error(f"Файл сессии не найден для {workdir}")
                continue
                
            from src.core.managers.runtime_hw_manager import apply_runtime_hw_overrides

            hw = apply_runtime_hw_overrides(acc_config.get("hardware_profile", {}))
            
            client = Client(
                name=session_file.stem,
                workdir=str(session_file.parent),
                api_id=acc_config.get("api_id"),
                api_hash=acc_config.get("api_hash"),
                proxy=proxy_dict,
                app_version=hw.get("app_version", "1.0"),
                device_model=hw.get("device_model", acc_config.get("device_name", "PC")),
                system_version=hw.get("system_version", "Windows"),
                lang_code=hw.get("lang_code", "en"),
                no_updates=True
            )
            
            try:
                await client.connect()
                
                context = {
                    "api_key": self.api_key,
                    "api_base_url": self.api_base_url,
                    "model_name": self.model_name
                }
                
                for task in schedule:
                    action = task.get("action")
                    delay = task.get("delay_after_sec", 0)
                    params = task.get("params", {})
                    
                    if action == "DELAY":
                        logger.info(f"[{acc_name}] ⏳ ИИ запросил паузу. Спим {delay} секунд...")
                        await asyncio.sleep(delay)
                        continue
                        
                    try:
                        worker_module = importlib.import_module(f"src.ai_agents.workers.{action}")
                        logger.info(f"[{acc_name}] ⚙️ Запуск воркера: {action}...")
                        
                        success = await worker_module.run(client, params, context)
                        if success:
                            logger.info(f"[{acc_name}] ✅ {action} выполнен успешно.")
                        else:
                            logger.error(f"[{acc_name}] ❌ {action} вернул ошибку.")
                            
                    except ModuleNotFoundError:
                        logger.warning(f"[{acc_name}] ⚠️ Воркер '{action}' не найден.")
                    except Exception as e:
                        logger.error(f"[{acc_name}] ❌ Ошибка при выполнении {action}: {e}")
                    
                    if delay > 0:
                        logger.info(f"[{acc_name}] ⏳ Задержка после задачи: {delay} сек...")
                        await asyncio.sleep(delay)
                        
            except Exception as e:
                err_str = str(e).lower()
                if "0x03" in err_str or "unreachable" in err_str or "proxy" in err_str or "timed out" in err_str:
                    logger.error(f"[{acc_name}] ❌ Ошибка подключения. Прокси-сервер не работает или истек (Сбой сети).")
                else:
                    logger.error(f"[{acc_name}] ❌ Не удалось подключиться: {e}")
            finally:
                if client.is_connected:
                    await client.disconnect()
                if gost_process:
                    try:
                        gost_process.terminate()
                        try:
                            import subprocess
                            gost_process.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            gost_process.kill()
                    except:
                        pass
                logger.info(f"--- [Аккаунт: {acc_name}] Завершил работу ---")
