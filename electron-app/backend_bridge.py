#!/usr/bin/env python3
"""Small JSON-lines bridge used by Electron during the incremental migration."""
import json
import sys
import asyncio
import threading
import uuid
import csv
import shutil
import zipfile
import io
import contextlib
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.core.constants import CONFIG_FILE
from src.core.managers import account_manager, config_manager, process_manager, proxy_manager

processes = {}
scenario_tasks = {}
auth_tasks = {}
module_tasks = {}
mass_sender_tasks = {}
neuro_tasks = {}
scenario_lock = threading.Lock()


def accounts():
    result = []
    for account in config_manager.load_config(CONFIG_FILE):
        workdir = Path(account.get("workdir", ""))
        result.append({
            **account,
            "name": account.get("name", workdir.name),
            "workdir": str(workdir),
            "status": "Running" if process_manager.is_process_running(processes.get(str(workdir))) else "Stopped",
            "proxyStatus": "Configured" if account.get("proxy") or account.get("proxy_url") else "None",
        })
    return result


def _scenario_accounts(selected):
    configured = config_manager.load_config(CONFIG_FILE)
    wanted = {str(item.get("name", "")) for item in selected}
    wanted.update(str(item.get("workdir", "")) for item in selected)
    return [item for item in configured if str(item.get("name", "")) in wanted or str(item.get("workdir", "")) in wanted]


def _run_scenario(task_id, graph, selected):
    logs = scenario_tasks[task_id]["logs"]

    def log(message):
        with scenario_lock:
            logs.append(str(message))

    async def run_all():
        from src.core.managers.node_executor import NodeScenarioExecutor
        cfg = config_manager._read_config(Path(CONFIG_FILE))
        limit = int(cfg.get("settings", {}).get("max_concurrent_tasks", 10) or 10)
        semaphore = asyncio.Semaphore(max(1, limit))
        chosen = _scenario_accounts(selected)
        if not chosen:
            log("Ошибка: не найдено ни одного выбранного аккаунта в config.json")
            return

        async def run_account(account):
            async with semaphore:
                name = account.get("name") or Path(account.get("workdir", "")).name
                log(f"[{name}] 🚀 Запуск сценария на аккаунте...")
                executor = NodeScenarioExecutor(
                    account,
                    str(account.get("api_id", cfg.get("settings", {}).get("api_id", ""))),
                    str(account.get("api_hash", cfg.get("settings", {}).get("api_hash", ""))),
                    lambda message: log(f"[{name}] {message}"),
                    graph,
                )
                scenario_tasks[task_id]["instances"].append(executor)
                await executor.run()
                log(f"[{name}] ✅ Сценарий завершён")

        await asyncio.gather(*(run_account(account) for account in chosen))

    try:
        asyncio.run(run_all())
        with scenario_lock:
            scenario_tasks[task_id]["status"] = "completed"
            scenario_tasks[task_id]["logs"].append("Сессия визуальных сценариев полностью завершена.")
    except Exception as exc:
        with scenario_lock:
            scenario_tasks[task_id]["status"] = "failed"
            scenario_tasks[task_id]["logs"].append(f"Критическая ошибка сценария: {exc}")

def _auth_finished(task_id, status, message):
    with scenario_lock:
        task = auth_tasks.get(task_id)
        if task:
            task["status"] = status
            task["logs"].append(message)

def _run_auth(task_id, payload):
    try:
        from src.core.auth import AuthWorker
        worker = AuthWorker(phone=str(payload.get("phone", "")), api_id=int(payload.get("apiId", 0)), api_hash=str(payload.get("apiHash", "")), workdir=str(payload.get("workdir", "")), proxy_url=payload.get("proxy"), device_name=str(payload.get("device", "ShadowGram-PC")), session_name=str(payload.get("sessionName", "account")), output_dir=str(payload.get("outputDir", payload.get("workdir", ""))), use_telethon=bool(payload.get("useTelethon", False)))
        auth_tasks[task_id]["worker"] = worker
        worker.signal_log.connect(lambda message: auth_tasks[task_id]["logs"].append(str(message)))
        worker.signal_stage.connect(lambda stage: auth_tasks[task_id].__setitem__("stage", str(stage)))
        worker.signal_success.connect(lambda path: _auth_finished(task_id, "completed", f"Сессия создана: {path}"))
        worker.signal_error.connect(lambda error: _auth_finished(task_id, "failed", str(error)))
        worker.run()
        if auth_tasks[task_id]["status"] == "running":
            _auth_finished(task_id, "cancelled", "Авторизация завершена без создания сессии.")
    except Exception as exc:
        _auth_finished(task_id, "failed", f"Ошибка запуска авторизации: {exc}")


def _task_log(task_id, message):
    with scenario_lock:
        for registry in (scenario_tasks, auth_tasks, module_tasks, mass_sender_tasks, neuro_tasks):
            task = registry.get(task_id)
            if task is not None:
                task.setdefault("logs", []).append(str(message))
                return


def _finish_task(registry, task_id, status, message=None):
    with scenario_lock:
        task = registry.get(task_id)
        if task is not None:
            task["status"] = status
            if message:
                task.setdefault("logs", []).append(str(message))


def _run_module(task_id, payload):
    try:
        from src.core.module_manager import ModuleManager

        manager = ModuleManager()
        with contextlib.redirect_stdout(io.StringIO()):
            modules = manager.discover_modules()
        plugin_name = str(payload.get("module", ""))
        plugin_class = modules.get(plugin_name) or manager.get_module_class(plugin_name)
        if plugin_class is None:
            raise RuntimeError(f"Модуль не найден: {plugin_name}")
        chosen = _scenario_accounts(payload.get("accounts", []))
        if not chosen:
            raise RuntimeError("Не выбран ни один аккаунт")
        cfg = config_manager._read_config(Path(CONFIG_FILE))
        limit = int(cfg.get("settings", {}).get("max_concurrent_tasks", 10) or 10)
        semaphore = asyncio.Semaphore(max(1, limit))
        params = dict(payload.get("params", {}))

        async def run_account(account):
            async with semaphore:
                name = account.get("name") or Path(account.get("workdir", "")).name
                _task_log(task_id, f"[{name}] 🚀 Запуск {plugin_name}")
                instance = plugin_class(
                    account,
                    str(account.get("api_id", cfg.get("settings", {}).get("api_id", ""))),
                    str(account.get("api_hash", cfg.get("settings", {}).get("api_hash", ""))),
                    lambda message: _task_log(task_id, f"[{name}] {message}"),
                )
                with scenario_lock:
                    module_tasks[task_id].setdefault("instances", []).append(instance)
                try:
                    if await instance.init_client():
                        await instance.run(**params)
                        _task_log(task_id, f"[{name}] ✅ Завершено")
                    else:
                        _task_log(task_id, f"[{name}] ❌ Не удалось подключить сессию")
                finally:
                    await instance.cleanup()

        async def run_all():
            await asyncio.gather(*(run_account(account) for account in chosen))

        asyncio.run(run_all())
        _finish_task(module_tasks, task_id, "completed", "Выполнение модуля завершено.")
    except asyncio.CancelledError:
        _finish_task(module_tasks, task_id, "cancelled", "Выполнение модуля отменено.")
    except Exception as exc:
        _finish_task(module_tasks, task_id, "failed", f"Ошибка модуля: {exc}")


def _run_mass_sender(task_id, payload):
    try:
        from src.core.managers.mass_sender_engine import MassSenderWorker

        worker = MassSenderWorker(
            _scenario_accounts(payload.get("accounts", [])),
            payload.get("targets", []),
            str(payload.get("message", "")),
            int(payload.get("delayMin", 5)),
            int(payload.get("delayMax", 15)),
            int(payload.get("limitPerAccount", 20)),
        )
        with scenario_lock:
            mass_sender_tasks[task_id]["worker"] = worker
        worker.progress_signal.connect(lambda status, account, message: _task_log(task_id, f"[{status}] {account}: {message}"))
        worker.stat_signal.connect(lambda sent, failed, flood: _task_log(task_id, f"[stats] sent={sent} failed={failed} flood={flood}"))
        worker.finished_signal.connect(lambda: _finish_task(mass_sender_tasks, task_id, "completed", "Рассылка завершена."))
        worker.run()
        if mass_sender_tasks.get(task_id, {}).get("status") == "running":
            _finish_task(mass_sender_tasks, task_id, "cancelled", "Рассылка остановлена.")
    except Exception as exc:
        _finish_task(mass_sender_tasks, task_id, "failed", f"Ошибка рассылки: {exc}")


def _run_neuro(task_id, payload):
    try:
        from src.core.managers.neuro_engine import NeuroEngineThread

        config_path = Path(CONFIG_FILE)
        data = config_manager._read_config(config_path)
        settings = dict(data.get("settings", {}))
        neuro = dict(settings.get("neuro_v2", {}))
        neuro.update(payload.get("settings", {}))
        neuro["selected_accounts"] = list(payload.get("selectedAccounts", []))
        settings["neuro_v2"] = neuro
        data["settings"] = settings
        config_manager._write_config(config_path, data)
        engine = NeuroEngineThread(neuro["selected_accounts"])
        with scenario_lock:
            neuro_tasks[task_id]["worker"] = engine
        engine.status_updated.connect(lambda account, message: _task_log(task_id, f"[{account}] {message}"))
        engine.stopped.connect(lambda: _finish_task(neuro_tasks, task_id, "completed", "Neuro-комментинг завершён."))
        engine.run()
        if neuro_tasks.get(task_id, {}).get("status") == "running":
            _finish_task(neuro_tasks, task_id, "cancelled", "Neuro-комментинг остановлен.")
    except Exception as exc:
        _finish_task(neuro_tasks, task_id, "failed", f"Ошибка Neuro: {exc}")


def handle(action, payload):
    if action == "docs:list":
        docs_root = ROOT / "documentation"
        files = sorted(str(path.relative_to(ROOT)).replace("\\", "/") for path in docs_root.rglob("*.md")) if docs_root.exists() else []
        return {"files": files}
    if action == "docs:read":
        relative = str(payload.get("path", "")).replace("\\", "/")
        docs_root = (ROOT / "documentation").resolve()
        source = (ROOT / relative).resolve()
        if docs_root not in source.parents or source.suffix.lower() != ".md":
            raise ValueError("Invalid documentation path")
        if not source.exists():
            raise FileNotFoundError(relative)
        return {"path": relative, "content": source.read_text(encoding="utf-8")}
    if action == "server:ping":
        host = str(payload.get("host", "127.0.0.1")).strip()
        port = int(payload.get("port", 8765))
        token = str(payload.get("token", "")).strip()
        url = f"http://{host}:{port}/"
        request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"} if token else {})
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return {"ok": True, "status": response.status, "message": f"Server responded with HTTP {response.status}"}
        except urllib.error.HTTPError as exc:
            return {"ok": False, "status": exc.code, "message": f"Server responded with HTTP {exc.code}"}
        except Exception as exc:
            return {"ok": False, "message": str(exc)}
    if action == "schedules:list":
        data = config_manager._read_config(Path(CONFIG_FILE))
        return {"schedules": data.get("schedules", [])}
    if action == "schedules:save":
        config_path = Path(CONFIG_FILE)
        data = config_manager._read_config(config_path)
        schedules = list(data.get("schedules", []))
        schedule = dict(payload.get("schedule", {}))
        schedule["id"] = str(schedule.get("id") or f"schedule-{uuid.uuid4().hex[:10]}")
        schedules = [item for item in schedules if str(item.get("id")) != schedule["id"]]
        schedules.append(schedule)
        data["schedules"] = schedules
        config_manager._write_config(config_path, data)
        return {"ok": True, "schedule": schedule, "schedules": schedules}
    if action == "schedules:delete":
        config_path = Path(CONFIG_FILE)
        data = config_manager._read_config(config_path)
        schedule_id = str(payload.get("id", ""))
        schedules = [item for item in data.get("schedules", []) if str(item.get("id")) != schedule_id]
        data["schedules"] = schedules
        config_manager._write_config(config_path, data)
        return {"ok": True, "schedules": schedules}
    if action == "schedules:toggle":
        config_path = Path(CONFIG_FILE)
        data = config_manager._read_config(config_path)
        schedule_id = str(payload.get("id", ""))
        schedules = list(data.get("schedules", []))
        for item in schedules:
            if str(item.get("id")) == schedule_id:
                item["enabled"] = not bool(item.get("enabled", True))
        data["schedules"] = schedules
        config_manager._write_config(config_path, data)
        return {"ok": True, "schedules": schedules}
    if action == "tasks:list":
        with scenario_lock:
            all_tasks = {**scenario_tasks, **auth_tasks, **module_tasks, **mass_sender_tasks, **neuro_tasks}
            return {"tasks": [{"taskId": task_id, "name": task.get("name", "Task"), "status": task.get("status", "unknown"), "stage": task.get("stage", ""), "logs": list(task.get("logs", [])), "createdAt": task.get("createdAt", "")} for task_id, task in all_tasks.items()]}
    if action == "tasks:clear-finished":
        with scenario_lock:
            finished = {"completed", "failed", "stopped", "cancelled"}
            removed = []
            for registry in (scenario_tasks, auth_tasks, module_tasks, mass_sender_tasks, neuro_tasks):
                for task_id, task in list(registry.items()):
                    if task.get("status") in finished:
                        registry.pop(task_id, None)
                        removed.append(task_id)
        return {"ok": True, "removed": len(removed)}
    if action == "tasks:stop":
        task_id = str(payload.get("taskId", ""))
        with scenario_lock:
            task = next((registry.get(task_id) for registry in (scenario_tasks, auth_tasks, module_tasks, mass_sender_tasks, neuro_tasks) if registry.get(task_id)), None)
            if not task:
                return {"ok": False, "message": "Task not found"}
            for instance in task.get("instances", []):
                try:
                    instance.stop_requested = True
                except Exception:
                    pass
            task["status"] = "stopping"
            task.setdefault("logs", []).append("Запрошена остановка задачи.")
            if task_id in auth_tasks and task.get("worker"):
                task["worker"].cancel()
            if task_id in mass_sender_tasks and task.get("worker"):
                task["worker"].stop()
            if task_id in neuro_tasks and task.get("worker"):
                task["worker"].stop()
            for instance in task.get("instances", []):
                try:
                    instance.is_stopped = True
                except Exception:
                    pass
        return {"ok": True, "taskId": task_id, "message": "Task stop requested"}
    if action == "auth:start":
        task_id = f"auth-{uuid.uuid4().hex[:12]}"
        with scenario_lock:
            auth_tasks[task_id] = {"name": f"Session · {payload.get('phone', '')}", "status": "running", "stage": "starting", "logs": ["Запуск авторизации..."], "worker": None, "createdAt": uuid.uuid1().time}
        threading.Thread(target=_run_auth, args=(task_id, payload), daemon=True).start()
        return {"ok": True, "taskId": task_id, "message": "Auth flow started"}
    if action == "auth:input":
        task = auth_tasks.get(str(payload.get("taskId", "")))
        if not task or not task.get("worker"):
            return {"ok": False, "message": "Auth task is not ready for input"}
        task["worker"].provide_input(str(payload.get("value", "")))
        return {"ok": True, "message": "Input submitted"}
    if action == "auth:cancel":
        task = auth_tasks.get(str(payload.get("taskId", "")))
        if task and task.get("worker"):
            task["worker"].cancel()
            task["status"] = "stopping"
        return {"ok": True, "message": "Auth cancellation requested"}
    if action == "module:list":
        from src.core.module_manager import ModuleManager
        manager = ModuleManager()
        with contextlib.redirect_stdout(io.StringIO()):
            modules = manager.discover_modules()
        return {"modules": [{"name": name, "title": getattr(cls, "MODULE_NAME", name), "description": getattr(cls, "MODULE_DESC", ""), "params": getattr(cls, "PARAMS", [])} for name, cls in modules.items()]}
    if action == "module:run":
        task_id = f"module-{uuid.uuid4().hex[:12]}"
        with scenario_lock:
            module_tasks[task_id] = {"name": f"Module · {payload.get('module', '')}", "status": "running", "stage": "starting", "logs": ["Модуль принят и поставлен на выполнение."], "instances": [], "createdAt": uuid.uuid1().time}
        threading.Thread(target=_run_module, args=(task_id, payload), daemon=True).start()
        return {"ok": True, "taskId": task_id, "message": "Module execution started"}
    if action == "mass-sender:run":
        task_id = f"mass-sender-{uuid.uuid4().hex[:12]}"
        with scenario_lock:
            mass_sender_tasks[task_id] = {"name": "Mass Sender", "status": "running", "stage": "starting", "logs": ["Рассылка принята и поставлена на выполнение."], "worker": None, "createdAt": uuid.uuid1().time}
        threading.Thread(target=_run_mass_sender, args=(task_id, payload), daemon=True).start()
        return {"ok": True, "taskId": task_id, "message": "Mass sender started"}
    if action == "neuro:run":
        task_id = f"neuro-{uuid.uuid4().hex[:12]}"
        with scenario_lock:
            neuro_tasks[task_id] = {"name": "Neuro Commenting", "status": "running", "stage": "starting", "logs": ["Neuro-комментинг принят и поставлен на выполнение."], "worker": None, "createdAt": uuid.uuid1().time}
        threading.Thread(target=_run_neuro, args=(task_id, payload), daemon=True).start()
        return {"ok": True, "taskId": task_id, "message": "Neuro execution started"}
    if action == "node:specs":
        from src.ui.node_editor.node_specs import NODE_SPECS
        return {"specs": NODE_SPECS}
    if action == "accounts:list":
        return {"accounts": accounts()}
    if action == "account:get-profile":
        target = str(payload.get("workdir", ""))
        data = config_manager._read_config(Path(CONFIG_FILE))
        account = next((item for item in data.get("accounts", []) if str(item.get("workdir", "")) == target), None)
        if not account:
            raise ValueError("Account not found")
        account = dict(account)
        account["hardware_profile"] = account_manager.get_hardware_profile(CONFIG_FILE, target)
        return {"ok": True, "account": account}
    if action == "account:update-profile":
        target = str(payload.get("workdir", ""))
        data = config_manager._read_config(Path(CONFIG_FILE))
        account = next((item for item in data.get("accounts", []) if str(item.get("workdir", "")) == target), None)
        if not account:
            raise ValueError("Account not found")
        allowed = {"first_name", "last_name", "username", "phone", "email", "password", "bio", "notes", "ai_prompt", "channel_name", "channel_link", "bound_channel", "proxy_url", "device_name", "privacy_guard"}
        for key, value in payload.get("profile", {}).items():
            if key in allowed:
                account[key] = value
        if isinstance(payload.get("hardware_profile"), dict):
            account["hardware_profile"] = payload["hardware_profile"]
        if payload.get("api_id") is not None or payload.get("api_hash") is not None:
            account_manager.update_api_credentials(CONFIG_FILE, target, payload.get("api_id"), payload.get("api_hash"))
            data = config_manager._read_config(Path(CONFIG_FILE))
        config_manager._write_config(Path(CONFIG_FILE), data)
        return {"ok": True, "account": account, "accounts": accounts()}
    if action == "account:generate-bio":
        bios = ["Just living life", "Crypto enthusiast", "Music lover", "Traveler & Dreamer", "Tech geek", "Coffee addict", "Always learning", "Making things happen", "Future billionaire", "Software engineer", "Digital artist", "Fitness & Health"]
        bio = random.choice(bios)
        target = str(payload.get("workdir", ""))
        account_manager.update_account_profile_data(CONFIG_FILE, target, bio=bio)
        return {"ok": True, "bio": bio}
    if action == "account:generate-api":
        from src.core.managers.api_manager import get_dynamic_api_credentials
        creds = get_dynamic_api_credentials(str(uuid.uuid4()))
        return {"ok": True, "api_id": str(creds["api_id"]), "api_hash": creds["api_hash"]}
    if action == "account:set-avatar":
        target = Path(str(payload.get("workdir", "")))
        source = Path(str(payload.get("sourcePath", "")))
        if not source.exists():
            raise ValueError("Avatar file not found")
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target / "avatar.jpg")
        return {"ok": True, "path": str(target / "avatar.jpg")}
    if action == "account:set-channel-avatar":
        target = Path(str(payload.get("workdir", "")))
        source = Path(str(payload.get("sourcePath", "")))
        if not source.exists():
            raise ValueError("Channel avatar file not found")
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target / "channel_avatar.jpg")
        return {"ok": True, "path": str(target / "channel_avatar.jpg")}
    if action == "account:export-session":
        target = Path(str(payload.get("workdir", "")))
        output = Path(str(payload.get("outputPath", "")))
        if not target.exists():
            raise ValueError("Account workdir not found")
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for file_path in target.glob("*.session"):
                archive.write(file_path, file_path.name)
            for name in ("avatar.jpg", "channel_avatar.jpg"):
                file_path = target / name
                if file_path.exists():
                    archive.write(file_path, name)
        return {"ok": True, "path": str(output), "message": "Session archive exported"}
    if action == "phones:export":
        phones = [str(account.get("phone", "")).strip() for account in config_manager.load_config(CONFIG_FILE) if account.get("phone")]
        output = Path(payload["outputPath"])
        output.write_text("\n".join(phones) + ("\n" if phones else ""), encoding="utf-8")
        return {"ok": True, "message": f"Exported {len(phones)} phone numbers"}
    if action == "accounts:table":
        data = config_manager._read_config(Path(CONFIG_FILE))
        return {"accounts": data.get("accounts", [])}
    if action == "accounts:bulk-proxy":
        selected = payload.get("workdirs", [])
        value = str(payload.get("proxy", "")).strip()
        for workdir in selected:
            account_manager.update_proxy(CONFIG_FILE, workdir, value)
        return {"ok": True, "accounts": accounts(), "message": f"Proxy updated for {len(selected)} accounts"}
    if action == "accounts:bulk-api":
        from src.core.managers.api_manager import get_dynamic_api_credentials
        import random
        import time
        selected = payload.get("workdirs", [])
        for workdir in selected:
            creds = get_dynamic_api_credentials(str(time.time() + random.random()))
            account_manager.update_api_credentials(CONFIG_FILE, workdir, str(creds["api_id"]), creds["api_hash"])
        return {"ok": True, "accounts": accounts(), "message": f"Fallback API updated for {len(selected)} accounts"}
    if action in {"accounts:bulk-launch", "accounts:bulk-stop", "accounts:bulk-check-proxy", "accounts:bulk-clear-cache"}:
        selected = [str(value) for value in payload.get("workdirs", [])]
        results = []
        for target in selected:
            try:
                if action == "accounts:bulk-launch":
                    result = handle("account:launch", {"workdir": target})
                elif action == "accounts:bulk-stop":
                    result = handle("account:stop", {"workdir": target})
                elif action == "accounts:bulk-check-proxy":
                    result = handle("account:proxy-check", {"workdir": target})
                else:
                    result = handle("account:clear-cache", {"workdir": target})
                results.append({"workdir": target, "ok": bool(result.get("ok"))})
            except Exception as exc:
                results.append({"workdir": target, "ok": False, "error": str(exc)})
        return {"ok": all(item["ok"] for item in results) if results else False, "results": results, "accounts": accounts(), "message": f"Обработано аккаунтов: {len(results)}"}
    if action == "account:remove":
        target = str(payload.get("workdir", ""))
        ok = account_manager.remove_account(CONFIG_FILE, target)
        processes.pop(target, None)
        return {"ok": ok, "accounts": accounts(), "message": "Аккаунт удалён" if ok else "Аккаунт не найден"}
    if action == "account:move":
        target = str(payload.get("workdir", ""))
        direction = int(payload.get("direction", 0))
        ok = account_manager.move_account_in_list(CONFIG_FILE, target, direction)
        return {"ok": ok, "accounts": accounts(), "message": "Позиция аккаунта обновлена" if ok else "Невозможно изменить позицию"}
    if action == "account:update-meta":
        target = str(payload.get("workdir", ""))
        if "notes" in payload:
            account_manager.update_notes(CONFIG_FILE, target, payload.get("notes"))
        if "ai_prompt" in payload:
            account_manager.update_prompt(CONFIG_FILE, target, payload.get("ai_prompt"))
        if "device_name" in payload:
            account_manager.update_device_info(CONFIG_FILE, target, str(payload.get("device_name") or ""))
        return {"ok": True, "accounts": accounts()}
    if action == "accounts:export-csv":
        output = Path(payload["outputPath"])
        data = config_manager._read_config(Path(CONFIG_FILE)).get("accounts", [])
        fields = ["name", "phone", "privacy_guard", "api_id", "api_hash", "proxy_url", "device_name", "email", "password", "notes", "workdir"]
        with output.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, delimiter=";", extrasaction="ignore")
            writer.writeheader()
            writer.writerows(data)
        return {"ok": True, "path": str(output), "message": f"Exported {len(data)} accounts"}
    if action == "scenario:save":
        output = Path(payload["path"])
        output.write_text(json.dumps(payload.get("graph", {}), ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "path": str(output)}
    if action == "scenario:load":
        source = Path(payload["path"])
        return {"ok": True, "graph": json.loads(source.read_text(encoding="utf-8"))}
    if action == "farms:get":
        from src.core.managers import farm_manager
        farms_list = farm_manager.list_farms()
        active = farm_manager.get_active_farm_name()
        return {"farms": [{"name": f, "is_active": (f == active)} for f in farms_list], "active": active}
    if action == "farms:switch":
        from src.core.managers import farm_manager
        target_farm = str(payload.get("farm", ""))
        ok = farm_manager.switch_active_farm(target_farm)
        return {"ok": ok, "active": farm_manager.get_active_farm_name(), "message": f"Switched to farm {target_farm}" if ok else "Failed to switch farm"}
    if action == "farms:create":
        from src.core.managers import farm_manager
        name = str(payload.get("name", "")).strip()
        ok = farm_manager.create_new_farm(name)
        return {"ok": ok, "message": f"Farm {name} created" if ok else "Failed to create farm"}
    if action == "settings:get":
        data = config_manager._read_config(Path(CONFIG_FILE))
        return {"settings": data.get("settings", {})}
    if action == "settings:save":
        config_path = Path(CONFIG_FILE)
        data = config_manager._read_config(config_path)
        settings = dict(data.get("settings", {}))
        settings.update(payload.get("settings", {}))
        data["settings"] = settings
        config_manager._write_config(config_path, data)
        return {"ok": True, "settings": settings}
    if action == "scenario:run":
        graph = payload.get("graph", {})
        if not any(node.get("type") == "start" for node in graph.get("nodes", [])):
            return {"ok": False, "message": "Scenario requires a Start node"}
        task_id = f"scenario-{uuid.uuid4().hex[:12]}"
        with scenario_lock:
            scenario_tasks[task_id] = {"name": "Node scenario", "status": "running", "logs": ["Сценарий принят и поставлен на выполнение."], "instances": [], "createdAt": uuid.uuid1().time}
        threading.Thread(target=_run_scenario, args=(task_id, graph, payload.get("accounts", [])), daemon=True).start()
        return {"ok": True, "taskId": task_id, "message": "Scenario execution started"}
    if action == "scenario:status":
        task_id = str(payload.get("taskId", ""))
        with scenario_lock:
            task = scenario_tasks.get(task_id)
            if not task:
                return {"ok": False, "message": "Scenario task not found"}
            return {"ok": True, "taskId": task_id, "status": task["status"], "logs": list(task["logs"])}
    if action == "scenario:stop":
        task_id = str(payload.get("taskId", ""))
        with scenario_lock:
            task = scenario_tasks.get(task_id)
            if not task:
                return {"ok": False, "message": "Scenario task not found"}
            for instance in task["instances"]:
                try:
                    instance.stop_requested = True
                except Exception:
                    pass
            task["status"] = "stopping"
            task["logs"].append("Запрошена остановка сценария.")
        return {"ok": True, "taskId": task_id, "message": "Scenario stop requested"}
    if action == "accounts:create":
        ok = account_manager.add_account(CONFIG_FILE, payload["name"], payload["workdir"], payload.get("proxy"), payload.get("device"), payload.get("apiId"), payload.get("apiHash"))
        return {"ok": ok, "accounts": accounts()}
    acc = next((item for item in accounts() if item.get("name") == payload.get("name") or item.get("workdir") == payload.get("workdir")), None)
    if not acc:
        raise ValueError("Account not found")
    workdir = acc["workdir"]
    proxy = acc.get("proxy") or acc.get("proxy_url")
    if action == "account:launch":
        tg, gost = process_manager.start_telegram(workdir, proxy, acc.get("device_name"), acc.get("name"))
        processes[workdir] = tg
        return {"ok": tg is not None, "accounts": accounts()}
    if action == "account:stop":
        ok = process_manager.stop_telegram(processes.pop(workdir, None), workdir=workdir)
        return {"ok": ok, "accounts": accounts()}
    if action == "account:proxy-check":
        return {"ok": proxy_manager.check_proxy_validity(proxy), "accounts": accounts()}
    if action == "account:clear-cache":
        ok, message = process_manager.clear_cache(workdir)
        return {"ok": ok, "message": message, "accounts": accounts()}
    if action == "account:session-check":
        session = list(Path(workdir).glob("*.session")) if Path(workdir).exists() else []
        return {"ok": bool(session), "message": "Session found" if session else "Session not found", "accounts": accounts()}
    raise ValueError(f"Unknown action: {action}")


for line in sys.stdin:
    try:
        request = json.loads(line)
        response = {"id": request.get("id"), "ok": True, "data": handle(request["action"], request.get("payload", {}))}
    except Exception as exc:
        response = {"id": request.get("id") if "request" in locals() else None, "ok": False, "error": str(exc)}
    print(json.dumps(response, ensure_ascii=False), flush=True)
