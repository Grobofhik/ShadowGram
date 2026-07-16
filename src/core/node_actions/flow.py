import random

async def start(executor, params):
    return "next"

async def delay(executor, params):
    seconds = int(params.get("seconds", 10))
    executor.log(f"Ожидание {seconds} секунд...", "info")
    await executor.sleep(seconds)
    return "next"

async def random_delay(executor, params):
    min_sec = float(params.get("min_seconds", 5))
    max_sec = float(params.get("max_seconds", 15))
    if min_sec > max_sec:
        min_sec, max_sec = max_sec, min_sec
    seconds = round(random.uniform(min_sec, max_sec), 2)
    executor.log(f"Ожидание случайного интервала {seconds} сек. (диапазон {min_sec}-{max_sec})...", "info")
    await executor.sleep(seconds)
    return "next"

async def if_condition(executor, params):
    # 1. Проверяем, подключен ли проверяющий блок к входному порту "condition"
    current_node = getattr(executor, "current_node", {})
    current_node_id = current_node.get("id")
    
    conn = next((c for c in getattr(executor, "connections_list", []) 
                 if c["to_node"] == current_node_id and c["to_port"] == "condition"), None)
                 
    if conn:
        upstream_node_id = conn["from_node"]
        upstream_port = conn["from_port"]
        upstream_node = getattr(executor, "nodes", {}).get(upstream_node_id)
        if upstream_node:
            upstream_type = upstream_node["type"]
            upstream_params = upstream_node.get("params", {})
            
            # Разрешаем наследование контекста для суб-блока
            resolved_params = dict(upstream_params)
            if "bot_username" in resolved_params:
                v = executor.resolve_string(str(resolved_params["bot_username"])).strip()
                if not v and executor.last_bot_username:
                    resolved_params["bot_username"] = executor.last_bot_username
            if "chat_id" in resolved_params:
                v = executor.resolve_string(str(resolved_params["chat_id"])).strip()
                if not v and executor.last_chat_id:
                    resolved_params["chat_id"] = executor.last_chat_id
            if "to_chat_id" in resolved_params:
                v = executor.resolve_string(str(resolved_params["to_chat_id"])).strip()
                if not v and executor.last_chat_id:
                    resolved_params["to_chat_id"] = executor.last_chat_id
            if "message_id" in resolved_params:
                v_raw = resolved_params.get("message_id")
                v_str = executor.resolve_string(str(v_raw)).strip() if v_raw is not None else ""
                if (not v_str or v_str == "0" or v_str == "") and executor.last_message_id is not None:
                    resolved_params["message_id"] = executor.last_message_id
            
            from src.core.node_actions import ACTION_HANDLERS
            handler = ACTION_HANDLERS.get(upstream_type)
            if handler:
                executor.log(f"ЕСЛИ: Вызов проверяющего блока '{upstream_node.get('title', upstream_type)}'...", "info")
                result_port = await handler(executor, resolved_params)
                eval_result = (result_port == upstream_port)
                next_port = "true" if eval_result else "false"
                executor.log(f"ЕСЛИ: Блок '{upstream_node.get('title', upstream_type)}' вернул '{result_port}'. Ожидалось '{upstream_port}'. Результат: {eval_result}. Путь: '{next_port}'", "info")
                return next_port
            else:
                executor.log(f"Ошибка ЕСЛИ: Не найден обработчик для '{upstream_type}'", "error")
                
    # 2. Если порт не подключен, вычисляем текстовое условие (обратная совместимость)
    condition = executor.resolve_string(params.get("condition", "")).strip()
    eval_result = True
    if condition:
        try:
            eval_result = bool(eval(condition, {"__builtins__": None}, {}))
        except Exception:
            eval_result = (condition.lower() not in ["false", "0", "no", ""])
            
    next_port = "true" if eval_result else "false"
    executor.log(f"Результат текстового условия ЕСЛИ: {eval_result}. Идем по порту '{next_port}'", "info")
    return next_port



async def random_branch(executor, params):
    node = getattr(executor, "current_node", {})
    outputs = node.get("outputs", ["path_a", "path_b"])
    if not outputs:
        return None
    next_port = random.choice(outputs)
    executor.log(f"Рандом: из вариантов {outputs} случайно выбран '{next_port}'", "info")
    return next_port

async def loop(executor, params):
    loop_type = params.get("loop_type", "infinite")
    iterations_str = executor.resolve_string(params.get("iterations", "10")).strip()
    
    if not hasattr(executor, "loop_counters"):
        executor.loop_counters = {}
        
    node_id = executor.current_node["id"]
    current_count = executor.loop_counters.get(node_id, 0)
    
    if loop_type == "count":
        try:
            max_iterations = int(iterations_str)
        except ValueError:
            max_iterations = 10
            
        if current_count < max_iterations:
            executor.loop_counters[node_id] = current_count + 1
            executor.log(f"Цикл (итерация {current_count + 1} из {max_iterations}): переход в тело цикла 'loop_body'", "info")
            return "loop_body"
        else:
            executor.loop_counters[node_id] = 0
            executor.log(f"Цикл завершен ({max_iterations} итераций). Переход по выходу 'next'", "success")
            return "next"
    else:
        executor.loop_counters[node_id] = current_count + 1
        executor.log(f"Цикл (итерация {current_count + 1}, бесконечный): переход в тело цикла 'loop_body'", "info")
        return "loop_body"

async def end(executor, params):
    if hasattr(executor, "queue"):
        executor.queue.clear()
    executor.log("Достигнут блок 'Конец'. Выполнение сценария успешно завершено.", "success")
    return None

async def try_catch(executor, params):
    if not hasattr(executor, "try_catch_stack"):
        executor.try_catch_stack = []
    current_node_id = getattr(executor, "current_node", {}).get("id")
    executor.try_catch_stack.append(current_node_id)
    return "next"

async def lock(executor, params):
    lock_name = executor.resolve_string(params.get("lock_name", "global_lock")).strip()
    if not hasattr(executor.__class__, "GLOBAL_LOCKS"):
        executor.__class__.GLOBAL_LOCKS = {}
    if lock_name not in executor.__class__.GLOBAL_LOCKS:
        executor.__class__.GLOBAL_LOCKS[lock_name] = asyncio.Lock()
    
    executor.log(f"Ожидание захвата ресурса (мьютекса) '{lock_name}'...", "info")
    await executor.__class__.GLOBAL_LOCKS[lock_name].acquire()
    executor.log(f"Ресурс '{lock_name}' захвачен.", "success")
    
    if not hasattr(executor, "acquired_locks"):
        executor.acquired_locks = set()
    executor.acquired_locks.add(lock_name)
    return "next"

async def unlock(executor, params):
    lock_name = executor.resolve_string(params.get("lock_name", "global_lock")).strip()
    if hasattr(executor.__class__, "GLOBAL_LOCKS") and lock_name in executor.__class__.GLOBAL_LOCKS:
        l = executor.__class__.GLOBAL_LOCKS[lock_name]
        if l.locked():
            try:
                l.release()
                executor.log(f"Ресурс '{lock_name}' освобожден.", "success")
            except RuntimeError:
                pass
    if hasattr(executor, "acquired_locks") and lock_name in executor.acquired_locks:
        executor.acquired_locks.remove(lock_name)
    return "next"
