import os
import asyncio

async def get_post_comments(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    message_id_val = params.get("message_id", 0)
    limit = int(params.get("limit", 10))
    
    if isinstance(message_id_val, str):
        message_id_str = executor.resolve_string(message_id_val).strip()
        message_id = int(message_id_str) if message_id_str.isdigit() else 0
    else:
        message_id = int(message_id_val)
        
    if not chat_id or not message_id:
        executor.log("Пропуск: не заполнен chat_id или message_id.", "warning")
        executor.variables["comments_text"] = ""
        return "no_comments"
        
    try:
        comments = []
        async for msg in executor.client.get_discussion_replies(chat_id, message_id, limit=limit):
            if msg.text:
                comments.append(msg.text)
                
        if comments:
            comments_text = "\n".join(comments)
            executor.variables["comments_text"] = comments_text
            executor.log(f"Успешно выгружено {len(comments)} комментариев из поста {message_id}.", "success")
            return "has_comments"
        else:
            executor.variables["comments_text"] = ""
            executor.log(f"Комментарии под постом {message_id} отсутствуют.", "info")
            return "no_comments"
    except Exception as e:
        executor.log(f"Ошибка получения комментариев: {e}", "error")
        executor.variables["comments_text"] = ""
        return "no_comments"

async def ai_prompt(executor, params):
    prompt = executor.resolve_string(params.get("prompt", "")).strip()
    system_prompt = executor.resolve_string(params.get("system_prompt", "Ты полезный ИИ-помощник.")).strip()
    
    if not prompt:
        executor.log("Пропуск: пустой промпт ИИ.", "warning")
        executor.variables["ai_response"] = ""
        return "next"
        
    try:
        res = await executor.generate_ai_text(prompt, system_prompt)
        executor.variables["ai_response"] = res
        executor.log("Запрос к ИИ успешно выполнен и сохранен в {ai_response}.", "success")
    except Exception as e:
        executor.log(f"Ошибка запроса к ИИ: {e}", "error")
        executor.variables["ai_response"] = ""
    return "next"

async def string_contains(executor, params):
    text = executor.resolve_string(params.get("text", "")).strip()
    substring = executor.resolve_string(params.get("substring", "")).strip()
    
    if substring.lower() in text.lower():
        executor.log(f"Текст содержит фразу '{substring}'.", "success")
        return "true"
    else:
        executor.log(f"Текст НЕ содержит фразу '{substring}'.", "info")
        return "false"

async def write_file(executor, params):
    file_path = executor.resolve_string(params.get("file_path", "")).strip()
    content = executor.resolve_string(params.get("content", ""))
    mode = params.get("mode", "append")
    
    if not file_path:
        executor.log("Пропуск: не указан путь к файлу.", "warning")
        return "next"
        
    try:
        write_mode = "a" if mode == "append" else "w"
        dir_name = os.path.dirname(file_path)
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
            
        with open(file_path, write_mode, encoding="utf-8") as f:
            f.write(content)
        executor.log(f"Данные успешно записаны в файл '{file_path}' (режим: {mode}).", "success")
    except Exception as e:
        executor.log(f"Ошибка записи в файл: {e}", "error")
    return "next"

async def read_file(executor, params):
    file_path = executor.resolve_string(params.get("file_path", "")).strip()
    if not file_path or not os.path.exists(file_path):
        executor.log(f"Пропуск: файл '{file_path}' не найден.", "warning")
        executor.variables["file_content"] = ""
        return "next"
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        executor.variables["file_content"] = content
        executor.log(f"Файл '{file_path}' успешно прочитан в {file_content}.", "success")
    except Exception as e:
        executor.log(f"Ошибка чтения файла: {e}", "error")
        executor.variables["file_content"] = ""
    return "next"

async def get_chat_history_messages(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    limit = int(params.get("limit", 20))
    if not chat_id:
        executor.log("Пропуск: не указан chat_id для выгрузки истории.", "warning")
        executor.variables["chat_history_text"] = ""
        return "next"
    try:
        messages = []
        async for msg in executor.client.get_chat_history(chat_id, limit=limit):
            if msg.text:
                messages.append(f"{msg.from_user.first_name if msg.from_user else 'User'}: {msg.text}")
        if messages:
            chat_history_text = "\n".join(messages)
            executor.variables["chat_history_text"] = chat_history_text
            executor.log(f"Успешно выгружено {len(messages)} сообщений из истории {chat_id}.", "success")
        else:
            executor.variables["chat_history_text"] = ""
            executor.log("Сообщения в истории не найдены.", "info")
    except Exception as e:
        executor.log(f"Ошибка выгрузки истории сообщений: {e}", "error")
        executor.variables["chat_history_text"] = ""
    return "next"

async def get_unread_dialogs(executor, params):
    limit = int(params.get("limit", 20))
    try:
        unread_chats = []
        async for dialog in executor.client.get_dialogs(limit=limit):
            if dialog.unread_messages_count and dialog.unread_messages_count > 0:
                # Store either username or ID
                chat = dialog.chat
                identifier = f"@{chat.username}" if chat.username else str(chat.id)
                unread_chats.append(identifier)
                
        if unread_chats:
            executor.variables["unread_chats_list"] = ",".join(unread_chats)
            executor.log(f"Найдено {len(unread_chats)} непрочитанных диалогов: {executor.variables['unread_chats_list']}", "success")
        else:
            executor.variables["unread_chats_list"] = ""
            executor.log("Непрочитанные диалоги не найдены.", "info")
    except Exception as e:
        executor.variables["unread_chats_list"] = ""
        executor.log(f"Ошибка получения списка непрочитанных диалогов: {e}", "error")
    return "next"

async def read_line(executor, params):
    file_path = executor.resolve_string(params.get("file_path", "")).strip()
    var_name = executor.resolve_string(params.get("var_name", "username_var")).strip()
    
    if not file_path or not var_name:
        executor.log("Пропуск: не указан файл или имя переменной для записи.", "warning")
        return "next"
        
    try:
        val = await executor.get_next_line_from_file(file_path)
        executor.variables[var_name] = val
        executor.log(f"Считана строка из файла: '{val}' -> сохранена в переменную {{{var_name}}}", "success")
    except Exception as e:
        executor.variables[var_name] = ""
        executor.log(f"Ошибка считывания строки в переменную {{{var_name}}}: {e}", "error")
    return "next"

# Global state for folder files rotation
FOLDER_FILES_LOCK = asyncio.Lock()
FOLDER_FILE_CURSORS = {}

async def get_file_from_folder(executor, params):
    folder_path = executor.resolve_string(params.get("folder_path", "")).strip()
    selection_mode = int(params.get("selection_mode", 1))
    var_name = executor.resolve_string(params.get("var_name", "media_path")).strip()
    
    if not folder_path or not var_name:
        executor.log("Пропуск: не указана папка или имя переменной.", "warning")
        return "next"
        
    abs_folder = os.path.abspath(folder_path)
    if not os.path.exists(abs_folder) or not os.path.isdir(abs_folder):
        executor.log(f"⚠️ Папка '{abs_folder}' не найдена или не является директорией!", "error")
        executor.variables[var_name] = ""
        return "next"
        
    try:
        global FOLDER_FILES_LOCK, FOLDER_FILE_CURSORS
        
        # Scan folder for files
        files = [
            os.path.join(abs_folder, f)
            for f in os.listdir(abs_folder)
            if os.path.isfile(os.path.join(abs_folder, f))
        ]
        files.sort()  # Sort to guarantee consistent ordering in sequential mode
        
        if not files:
            executor.log(f"⚠️ В папке '{abs_folder}' не найдено файлов!", "warning")
            executor.variables[var_name] = ""
            return "next"
            
        if selection_mode == 1:
            # Random selection
            selected_file = random.choice(files)
        else:
            # Sequential rotation selection
            async with FOLDER_FILES_LOCK:
                if abs_folder not in FOLDER_FILE_CURSORS:
                    FOLDER_FILE_CURSORS[abs_folder] = 0
                idx = FOLDER_FILE_CURSORS[abs_folder]
                if idx >= len(files):
                    idx = 0  # Wrap around
                selected_file = files[idx]
                FOLDER_FILE_CURSORS[abs_folder] = idx + 1
                
        executor.variables[var_name] = selected_file
        executor.log(f"Выбран файл из папки: '{os.path.basename(selected_file)}' -> сохранен в переменную {{{var_name}}}", "success")
    except Exception as e:
        executor.variables[var_name] = ""
        executor.log(f"Ошибка выбора файла из папки '{abs_folder}': {e}", "error")
        
    return "next"

import requests
import json
import asyncio

async def http_request(executor, params):
    method = params.get("method", "GET")
    url = executor.resolve_string(params.get("url", "")).strip()
    headers_str = executor.resolve_string(params.get("headers", "{}")).strip()
    body = executor.resolve_string(params.get("body", "")).strip()
    var_name = executor.resolve_string(params.get("var_name", "http_response")).strip()
    
    try:
        headers = json.loads(headers_str) if headers_str else {}
    except Exception:
        executor.log("Ошибка парсинга заголовков (неверный JSON), используются пустые.", "warning")
        headers = {}
        
    executor.log(f"HTTP {method} запрос к {url}...", "info")
    
    loop = asyncio.get_event_loop()
    def do_request():
        kwargs = {"headers": headers, "timeout": 30}
        if method.upper() in ["POST", "PUT", "PATCH"] and body:
            kwargs["data"] = body.encode("utf-8")
        return requests.request(method, url, **kwargs)
        
    try:
        resp = await loop.run_in_executor(None, do_request)
        resp_text = resp.text
        status = resp.status_code
        executor.log(f"HTTP запрос завершен со статусом {status}", "success" if status < 400 else "warning")
        if var_name:
            executor.variables[var_name] = resp_text
            executor.variables[f"{var_name}_status"] = status
    except Exception as e:
        executor.log(f"Ошибка выполнения HTTP запроса: {e}", "error")
        if var_name:
            executor.variables[var_name] = ""
            executor.variables[f"{var_name}_status"] = 0
            
    return "next"

async def set_global_var(executor, params):
    var_name = executor.resolve_string(params.get("var_name", "")).strip()
    var_value = executor.resolve_string(params.get("var_value", "")).strip()
    if not hasattr(executor.__class__, "GLOBAL_VARIABLES"):
        executor.__class__.GLOBAL_VARIABLES = {}
    if var_name:
        executor.__class__.GLOBAL_VARIABLES[var_name] = var_value
        executor.log(f"Глобальная переменная '{var_name}' установлена в '{var_value}'", "info")
    return "next"

async def increase_global_counter(executor, params):
    var_name = executor.resolve_string(params.get("var_name", "")).strip()
    step_str = executor.resolve_string(params.get("step", "1")).strip()
    try:
        step = int(step_str)
    except ValueError:
        step = 1
        
    if not hasattr(executor.__class__, "GLOBAL_VARIABLES"):
        executor.__class__.GLOBAL_VARIABLES = {}
        
    if var_name:
        current = executor.__class__.GLOBAL_VARIABLES.get(var_name, 0)
        try:
            current = int(current)
        except ValueError:
            current = 0
        new_val = current + step
        executor.__class__.GLOBAL_VARIABLES[var_name] = new_val
        executor.log(f"Глобальный счетчик '{var_name}' увеличен на {step} (стало: {new_val})", "info")
    return "next"

async def get_from_resource(executor, params):
    resource_id = executor.resolve_string(params.get("resource_id", "names_list")).strip()
    file_path = executor.resolve_string(params.get("file_path", "")).strip()
    mode = params.get("mode", "sequential")
    var_name = executor.resolve_string(params.get("var_name", "resource_val")).strip()
    
    from src.core.managers.resource_manager import resource_manager
    
    if file_path:
        await resource_manager.init_file_resource(resource_id, file_path, mode)
        
    val = await resource_manager.get_value(resource_id)
    if var_name:
        executor.variables[var_name] = val
        executor.log(f"Взято из ресурса '{resource_id}': '{val}' -> сохранено в {{{var_name}}}", "info" if val else "warning")
        
    return "next"

async def parse_json(executor, params):
    json_str = executor.resolve_string(params.get("json_string", "")).strip()
    path = executor.resolve_string(params.get("key_path", "")).strip()
    var_name = executor.resolve_string(params.get("var_name", "json_val")).strip()
    
    try:
        data = json.loads(json_str)
        curr = data
        if path:
            for key in path.split("."):
                if isinstance(curr, dict) and key in curr:
                    curr = curr[key]
                elif isinstance(curr, list) and key.isdigit():
                    curr = curr[int(key)]
                else:
                    curr = ""
                    break
        executor.variables[var_name] = str(curr) if curr is not None else ""
        executor.log(f"JSON распарсен: {var_name} = '{executor.variables[var_name]}'", "success")
    except Exception as e:
        executor.variables[var_name] = ""
        executor.log(f"Ошибка парсинга JSON: {e}", "error")
    return "next"

async def regex_extract(executor, params):
    text = executor.resolve_string(params.get("text", "")).strip()
    pattern = executor.resolve_string(params.get("pattern", "")).strip()
    var_name = executor.resolve_string(params.get("var_name", "extracted_val")).strip()
    
    import re
    try:
        match = re.search(pattern, text)
        if match:
            val = match.group(1) if match.groups() else match.group(0)
            executor.variables[var_name] = val
            executor.log(f"Regex нашёл: '{val}' -> {{{var_name}}}", "success")
            return "found"
        else:
            executor.variables[var_name] = ""
            executor.log(f"Regex не прошёл по шаблону '{pattern}'", "info")
            return "not_found"
    except Exception as e:
        executor.variables[var_name] = ""
        executor.log(f"Ошибка Regex: {e}", "error")
        return "not_found"

async def wait_for_message(executor, params):
    chat_id = executor.resolve_string(params.get("chat_id", "")).strip()
    timeout = int(params.get("timeout", 30))
    var_name = executor.resolve_string(params.get("var_name", "incoming_message")).strip()
    
    executor.log(f"Ожидание входящего сообщения из {chat_id} (таймаут {timeout}с)...", "info")
    start_time = asyncio.get_event_loop().time()
    
    last_msg_id = getattr(executor, "last_message_id", 0) or 0
    while (asyncio.get_event_loop().time() - start_time) < timeout:
        try:
            async for msg in executor.client.get_chat_history(chat_id, limit=1):
                if msg.id > last_msg_id and msg.text:
                    executor.variables[var_name] = msg.text
                    executor.last_message_id = msg.id
                    executor.log(f"Получено новое сообщение: '{msg.text[:30]}...'", "success")
                    return "received"
        except Exception:
            pass
        await asyncio.sleep(2)
        
    executor.log("Превышено время ожидания сообщения.", "warning")
    executor.variables[var_name] = ""
    return "timeout"

async def execute_sub_scenario(executor, params):
    scenario_path = executor.resolve_string(params.get("scenario_path", "")).strip()
    if not scenario_path or not os.path.exists(scenario_path):
        executor.log(f"Подсценарий '{scenario_path}' не найден!", "error")
        return "error"
        
    try:
        with open(scenario_path, "r", encoding="utf-8") as f:
            sub_graph = json.load(f)
            
        sub_executor = executor.__class__(
            account_data=executor.acc,
            api_id=executor.api_id,
            api_hash=executor.api_hash,
            log_callback=executor.log_callback,
            graph_data=sub_graph
        )
        sub_executor.client = executor.client
        sub_executor.variables.update(executor.variables)
        
        executor.log(f"Запуск подсценария из '{os.path.basename(scenario_path)}'...", "info")
        await sub_executor.run()
        executor.variables.update(sub_executor.variables)
        executor.log(f"Подсценарий '{os.path.basename(scenario_path)}' завершен.", "success")
        return "next"
    except Exception as e:
        executor.log(f"Ошибка выполнения подсценария: {e}", "error")
        return "error"

async def get_last_comment(executor, params):
    post_url = executor.resolve_string(params.get("post_url", "")).strip()
    fallback_number = int(params.get("default_number", 0))

    if not post_url:
        executor.log("Пропуск: не указана ссылка на пост.", "warning")
        executor.variables["last_comment_text"] = ""
        executor.variables["last_comment_number"] = fallback_number
        return "next"

    clean_target = post_url
    if "t.me/" in clean_target:
        clean_target = clean_target.split("t.me/")[-1]

    parts = clean_target.strip("/").split("/")
    if len(parts) < 2:
        executor.log(f"Некорректная ссылка на пост: {post_url}", "error")
        executor.variables["last_comment_text"] = ""
        executor.variables["last_comment_number"] = fallback_number
        return "next"

    channel_ref = parts[0]
    if channel_ref == "c" and len(parts) >= 3:
        channel_ref = int("-100" + parts[1])
        msg_id = int(parts[2])
    else:
        msg_id = int(parts[-1])

    try:
        last_comment = None
        async for reply_msg in executor.client.get_discussion_replies(channel_ref, msg_id, limit=1):
            last_comment = reply_msg
            break

        if last_comment and last_comment.text:
            text = last_comment.text.strip()
            executor.variables["last_comment_text"] = text
            executor.log(f"Успешно считан последний комментарий: '{text}'", "success")
        else:
            executor.variables["last_comment_text"] = ""
            executor.log(f"Комментарии под постом пока отсутствуют (используем дефолтное число {fallback_number}).", "info")
    except Exception as e:
        executor.log(f"Ошибка получения последнего комментария: {e}", "error")
        executor.variables["last_comment_text"] = ""

    return "next"

async def extract_increment_number(executor, params):
    input_text = executor.resolve_string(params.get("text", "")).strip()
    increment = int(params.get("increment", 1))
    default_number = int(params.get("default_number", 1))
    format_template = params.get("template", "{result}")

    import re
    numbers = re.findall(r'\d+', input_text)
    if numbers:
        last_num = int(numbers[-1])
        calculated = last_num + increment
        executor.log(f"Найдено число {last_num}, расчитано новое значение: {calculated}", "info")
    else:
        calculated = default_number
        executor.log(f"Числа не найдены в тексте '{input_text}', используется стартовое значение: {calculated}", "info")

    result_str = format_template.replace("{result}", str(calculated))
    executor.variables["next_number"] = calculated
    executor.variables["calculated_text"] = result_str
    executor.log(f"Сформирован итоговый текст: '{result_str}'", "success")
    return "next"

async def send_post_comment(executor, params):
    post_url = executor.resolve_string(params.get("post_url", "")).strip()
    text = executor.resolve_string(params.get("text", "")).strip()

    if not post_url or not text:
        executor.log("Пропуск: не заполнен post_url или текст комментария.", "warning")
        return "next"

    clean_target = post_url
    if "t.me/" in clean_target:
        clean_target = clean_target.split("t.me/")[-1]

    parts = clean_target.strip("/").split("/")
    if len(parts) < 2:
        executor.log(f"Некорректная ссылка на пост: {post_url}", "error")
        return "next"

    channel_ref = parts[0]
    if channel_ref == "c" and len(parts) >= 3:
        channel_ref = int("-100" + parts[1])
        msg_id = int(parts[2])
    else:
        msg_id = int(parts[-1])

    try:
        sent_msg = await executor.client.send_message(
            chat_id=channel_ref,
            text=text,
            reply_to_message_id=msg_id
        )
        executor.variables["sent_comment_id"] = sent_msg.id
        executor.log(f"Комментарий '{text}' успешно отправлен к посту!", "success")
    except Exception as e:
        executor.log(f"Ошибка отправки комментария к посту {post_url}: {e}", "error")

    return "next"

