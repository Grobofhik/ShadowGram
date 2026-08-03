# Спецификация поддерживаемых блоков сценария для визуального Node-редактора
NODE_SPECS = {
    # ==========================================
    # 1. УПРАВЛЕНИЕ (Flow Control)
    # ==========================================
    "start": {
        "title": "Старт",
        "category": "Управление",
        "inputs": [],
        "outputs": ["next"],
        "params": {}
    },
    "end": {
        "title": "Конец",
        "category": "Управление",
        "inputs": ["prev"],
        "outputs": [],
        "params": {}
    },
    "delay": {
        "title": "Пауза",
        "category": "Управление",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "seconds": {"label": "Задержка (сек)", "type": "int", "default": 10}
        }
    },
    "random_delay": {
        "title": "Случайная пауза",
        "category": "Управление",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "min_seconds": {"label": "Минимум (сек)", "type": "int", "default": 5},
            "max_seconds": {"label": "Максимум (сек)", "type": "int", "default": 15}
        }
    },
    "if_condition": {
        "title": "Условие ЕСЛИ",
        "category": "Управление",
        "inputs": ["prev", "condition"],
        "outputs": ["true", "false"],
        "params": {
            "condition": {"label": "Условие (если не подключен порт 'Условие')", "type": "str", "default": ""}
        }
    },
    "random_branch": {
        "title": "Рандом",
        "category": "Управление",
        "inputs": ["prev"],
        "outputs": ["path_a", "path_b"],
        "params": {}
    },
    "loop": {
        "title": "Цикл",
        "category": "Управление",
        "inputs": ["prev"],
        "outputs": ["loop_body", "next"],
        "params": {
            "loop_type": {
                "label": "Тип цикла",
                "type": "select",
                "options": [
                    {"value": "infinite", "label": "Бесконечно"},
                    {"value": "count", "label": "Количество повторений"}
                ],
                "default": "infinite"
            },
            "iterations": {"label": "Количество итераций", "type": "int", "default": 10}
        }
    },
    "try_catch": {
        "title": "Перехват ошибки",
        "category": "Управление",
        "inputs": ["prev"],
        "outputs": ["next", "error"],
        "params": {}
    },
    "lock": {
        "title": "Захватить ресурс (Lock)",
        "category": "Управление",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "lock_name": {"label": "Имя ресурса (мьютекса)", "type": "str", "default": "global_lock"}
        }
    },
    "unlock": {
        "title": "Освободить ресурс (Unlock)",
        "category": "Управление",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "lock_name": {"label": "Имя ресурса (мьютекса)", "type": "str", "default": "global_lock"}
        }
    },

    # ==========================================
    # 2. ПРОФИЛЬ И КОНТАКТЫ (Profile & Contacts)
    # ==========================================
    "get_me": {
        "title": "Информация о себе",
        "category": "Профиль",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {}
    },
    "set_bio": {
        "title": "Установить БИО",
        "category": "Профиль",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "bio_text": {"label": "Текст БИО (статич.)", "type": "str", "default": ""},
            "file_path": {"label": "Путь к файлу БИО (.txt)", "type": "file", "default": ""}
        }
    },
    "set_avatar": {
        "title": "Установить аватар",
        "category": "Профиль",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "avatars_dir": {"label": "Путь к папке с фото", "type": "folder", "default": "avatars"}
        }
    },
    "set_name": {
        "title": "Установить имя",
        "category": "Профиль",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "first_name": {"label": "Имя (статич.)", "type": "str", "default": ""},
            "last_name": {"label": "Фамилия (статич.)", "type": "str", "default": ""},
            "file_path": {"label": "Файл имен (Имя,Фамилия) (.txt)", "type": "file", "default": ""}
        }
    },
    "set_username": {
        "title": "Установить юзернейм",
        "category": "Профиль",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "username": {"label": "Новый юзернейм (статич.)", "type": "str", "default": ""},
            "file_path": {"label": "Файл юзернеймов (.txt)", "type": "file", "default": ""}
        }
    },
    "set_privacy": {
        "title": "Настройки приватности",
        "category": "Профиль",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "phone_number": {"label": "Кто видит номер (1-все, 2-контакты, 3-никто)", "type": "int", "default": 3},
            "chat_invite": {"label": "Кто приглашает в группы (1-все, 2-контакты)", "type": "int", "default": 2},
            "status_timestamp": {"label": "Кто видит статус входа (1-все, 2-контакты, 3-никто)", "type": "int", "default": 3},
            "phone_call": {"label": "Кто может звонить (1-все, 2-контакты, 3-никто)", "type": "int", "default": 2}
        }
    },
    "enable_2fa": {
        "title": "Установить 2FA",
        "category": "Профиль",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "password": {"label": "Облачный пароль", "type": "str", "default": "MySecretPassword123"}
        }
    },
    "search_contacts": {
        "title": "Поиск пользователей",
        "category": "Профиль",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "query": {"label": "Поисковый запрос", "type": "str", "default": "durov"},
            "limit": {"label": "Лимит результатов", "type": "int", "default": 5}
        }
    },
    "import_contacts": {
        "title": "Импорт контактов",
        "category": "Профиль",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "contacts_list": {"label": "Список (телефон, имя; телефон, имя)", "type": "textarea", "default": "+79991112233, Иван; +79994445566, Петр"}
        }
    },
    "get_common_chats": {
        "title": "Общие чаты",
        "category": "Профиль",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "user_id": {"label": "ID или юзернейм пользователя", "type": "str", "default": ""}
        }
    },

    "add_contact": {
        "title": "Добавить контакт",
        "category": "Профиль",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "phone": {"label": "Номер телефона", "type": "str", "default": ""},
            "first_name": {"label": "Имя контакта", "type": "str", "default": ""}
        }
    },
    "delete_contacts": {
        "title": "Удалить контакты",
        "category": "Профиль",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "user_ids": {"label": "ID пользователей (через запятую)", "type": "str", "default": ""}
        }
    },
    "block_user": {
        "title": "Заблокировать юзера",
        "category": "Профиль",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "user_id": {"label": "ID или юзернейм пользователя", "type": "str", "default": ""}
        }
    },
    "unblock_user": {
        "title": "Разблокировать юзера",
        "category": "Профиль",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "user_id": {"label": "ID или юзернейм пользователя", "type": "str", "default": ""}
        }
    },

    # ==========================================
    # 3. ОТПРАВКА СООБЩЕНИЙ И МЕДИА (Sending)
    # ==========================================
    "send_message": {
        "title": "Отправить сообщение",
        "category": "Отправка",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "Юзернейм или ID чата", "type": "str", "default": ""},
            "text": {"label": "Текст сообщения (статич.)", "type": "textarea", "default": "Привет из ShadowGram!"},
            "file_path": {"label": "Файл с текстами сообщений (.txt)", "type": "file", "default": ""}
        }
    },
    "send_photo": {
        "title": "Отправить фото",
        "category": "Отправка",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "Юзернейм или ID чата", "type": "str", "default": ""},
            "photo_path": {"label": "Путь к файлу изображения", "type": "str", "default": ""},
            "caption": {"label": "Описание (подпись)", "type": "str", "default": ""}
        }
    },
    "send_video": {
        "title": "Отправить видео",
        "category": "Отправка",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "Юзернейм или ID чата", "type": "str", "default": ""},
            "video_path": {"label": "Путь к файлу видео", "type": "str", "default": ""},
            "caption": {"label": "Описание (подпись)", "type": "str", "default": ""}
        }
    },
    "send_document": {
        "title": "Отправить документ",
        "category": "Отправка",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "Юзернейм или ID чата", "type": "str", "default": ""},
            "file_path": {"label": "Путь к файлу документа", "type": "str", "default": ""},
            "caption": {"label": "Описание (подпись)", "type": "str", "default": ""}
        }
    },
    "send_voice": {
        "title": "Отправить голосовое",
        "category": "Отправка",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "Юзернейм или ID чата", "type": "str", "default": ""},
            "voice_path": {"label": "Путь к файлу голоса (.ogg)", "type": "str", "default": ""}
        }
    },
    "send_audio": {
        "title": "Отправить аудио",
        "category": "Отправка",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "Юзернейм или ID чата", "type": "str", "default": ""},
            "audio_path": {"label": "Путь к аудиофайлу", "type": "str", "default": ""},
            "caption": {"label": "Описание (подпись)", "type": "str", "default": ""}
        }
    },
    "send_gif": {
        "title": "Отправить GIF",
        "category": "Отправка",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "Юзернейм или ID чата", "type": "str", "default": ""},
            "gif_path": {"label": "Путь к GIF-файлу (.gif или .mp4)", "type": "str", "default": ""},
            "caption": {"label": "Описание (подпись)", "type": "str", "default": ""}
        }
    },
    "send_location": {
        "title": "Отправить локацию",
        "category": "Отправка",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "Юзернейм или ID чата", "type": "str", "default": ""},
            "latitude": {"label": "Широта (например: 55.7558)", "type": "str", "default": "55.7558"},
            "longitude": {"label": "Долгота (например: 37.6173)", "type": "str", "default": "37.6173"}
        }
    },
    "send_dice": {
        "title": "Отправить кости",
        "category": "Отправка",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "Юзернейм или ID чата", "type": "str", "default": ""},
            "emoji": {"label": "Игра (🎲, 🎯, 🏀, ⚽, 🎰, 🎳)", "type": "str", "default": "🎲"}
        }
    },
    "forward_messages": {
        "title": "Переслать сообщения",
        "category": "Отправка",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "from_chat_id": {"label": "Откуда (ID/юзернейм)", "type": "str", "default": ""},
            "to_chat_id": {"label": "Куда (ID/юзернейм)", "type": "str", "default": ""},
            "message_ids": {"label": "ID сообщений (через запятую)", "type": "str", "default": ""}
        }
    },
    "search_messages": {
        "title": "Поиск сообщений",
        "category": "Отправка",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "Юзернейм или ID чата", "type": "str", "default": ""},
            "query": {"label": "Поисковый запрос", "type": "str", "default": "привет"},
            "limit": {"label": "Лимит результатов", "type": "int", "default": 5}
        }
    },
    "edit_message_text": {
        "title": "Редактировать сообщение",
        "category": "Отправка",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID или юзернейм чата", "type": "str", "default": ""},
            "message_id": {"label": "ID сообщения", "type": "int", "default": 0},
            "new_text": {"label": "Новый текст сообщения", "type": "textarea", "default": ""}
        }
    },
    "delete_messages": {
        "title": "Удалить сообщения",
        "category": "Отправка",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID или юзернейм чата", "type": "str", "default": ""},
            "message_ids": {"label": "ID сообщений (через запятую)", "type": "str", "default": ""}
        }
    },

    # ==========================================
    # 4. УПРАВЛЕНИЕ ЧАТАМИ И АДМИНИСТРИРОВАНИЕ (Chat Admin)
    # ==========================================
    "create_group": {
        "title": "Создать группу",
        "category": "Администрирование",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "title": {"label": "Название группы", "type": "str", "default": "Новая группа"},
            "users": {"label": "Участники (через запятую)", "type": "str", "default": ""}
        }
    },
    "create_channel": {
        "title": "Создать канал",
        "category": "Администрирование",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "title": {"label": "Название канала", "type": "str", "default": "Новый канал"},
            "description": {"label": "Описание канала", "type": "str", "default": ""}
        }
    },
    "set_chat_title": {
        "title": "Изменить название чата",
        "category": "Администрирование",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID или юзернейм чата", "type": "str", "default": ""},
            "title": {"label": "Новое название", "type": "str", "default": ""}
        }
    },
    "set_chat_description": {
        "title": "Изменить описание чата",
        "category": "Администрирование",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID или юзернейм чата", "type": "str", "default": ""},
            "description": {"label": "Новое описание", "type": "str", "default": ""}
        }
    },
    "set_chat_username": {
        "title": "Юзернейм чата",
        "category": "Администрирование",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID группы или канала", "type": "str", "default": ""},
            "username": {"label": "Новый юзернейм чата", "type": "str", "default": ""}
        }
    },
    "set_chat_photo": {
        "title": "Изменить аватар чата",
        "category": "Администрирование",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID или юзернейм чата", "type": "str", "default": ""},
            "photo_path": {"label": "Путь к изображению", "type": "str", "default": ""}
        }
    },
    "delete_chat_photo": {
        "title": "Удалить аватар чата",
        "category": "Администрирование",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID или юзернейм чата", "type": "str", "default": ""}
        }
    },
    "pin_chat_message": {
        "title": "Закрепить сообщение",
        "category": "Администрирование",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID или юзернейм чата", "type": "str", "default": ""},
            "message_id": {"label": "ID сообщения", "type": "int", "default": 0},
            "silent": {"label": "Тихое закрепление (1 - да, 0 - нет)", "type": "int", "default": 1}
        }
    },
    "unpin_chat_message": {
        "title": "Открепить сообщение",
        "category": "Администрирование",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID или юзернейм чата", "type": "str", "default": ""},
            "message_id": {"label": "ID сообщения (0 - открепить все)", "type": "int", "default": 0}
        }
    },
    "restrict_chat_member": {
        "title": "Ограничить пользователя",
        "category": "Администрирование",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID или юзернейм чата", "type": "str", "default": ""},
            "user_id": {"label": "ID или юзернейм пользователя", "type": "str", "default": ""},
            "until_date_sec": {"label": "Срок бана в сек (0 - навсегда)", "type": "int", "default": 0}
        }
    },
    "promote_chat_member": {
        "title": "Назначить админом",
        "category": "Администрирование",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID или юзернейм чата", "type": "str", "default": ""},
            "user_id": {"label": "ID или юзернейм пользователя", "type": "str", "default": ""}
        }
    },
    "ban_chat_member": {
        "title": "Забанить пользователя",
        "category": "Администрирование",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID или юзернейм чата", "type": "str", "default": ""},
            "user_id": {"label": "ID или юзернейм пользователя", "type": "str", "default": ""}
        }
    },
    "unban_chat_member": {
        "title": "Разбанить пользователя",
        "category": "Администрирование",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID или юзернейм чата", "type": "str", "default": ""},
            "user_id": {"label": "ID или юзернейм пользователя", "type": "str", "default": ""}
        }
    },
    "export_chat_invite_link": {
        "title": "Создать инвайт-ссылку",
        "category": "Администрирование",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID или юзернейм чата", "type": "str", "default": ""}
        } # Запишет ссылку в переменную {invite_link}
    },

    # ==========================================
    # 5. ОБЩАЯ АКТИВНОСТЬ (Telegram Interactions)
    # ==========================================
    "join_chat": {
        "title": "Вступить в чат",
        "category": "Активность",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_link": {"label": "Ссылка на канал/чат", "type": "str", "default": ""}
        }
    },
    "leave_chat": {
        "title": "Выйти из чата",
        "category": "Активность",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "Юзернейм или ID чата", "type": "str", "default": ""}
        }
    },
    "mute_chat": {
        "title": "Мьют уведомлений (Mute)",
        "category": "Активность",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "Ссылка на канал или Юзернейм/ID", "type": "str", "default": ""}
        }
    },
    "auto_react": {
        "title": "Авто-Реакции",
        "category": "Активность",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "channel_url": {"label": "Ссылка на канал", "type": "str", "default": ""},
            "posts_count": {"label": "Количество постов", "type": "int", "default": 5},
            "reaction_chance": {"label": "Шанс реакции (0-100%)", "type": "int", "default": 100}
        }
    },
    "ai_reply": {
        "title": "ИИ Автоответчик",
        "category": "Активность",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID диалога", "type": "str", "default": ""},
            "prompt": {"label": "Промпт для ИИ-личности", "type": "textarea", "default": "Ответь вежливо и кратко."}
        }
    },
    "read_chat_history": {
        "title": "Прочитать сообщения",
        "category": "Активность",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID или юзернейм чата", "type": "str", "default": ""}
        }
    },
    "archive_chats": {
        "title": "Архивировать чат",
        "category": "Активность",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_ids": {"label": "ID чатов (через запятую)", "type": "str", "default": ""}
        }
    },
    "unarchive_chats": {
        "title": "Разархивировать чат",
        "category": "Активность",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_ids": {"label": "ID чатов (через запятую)", "type": "str", "default": ""}
        }
    },
    
    # Дополнительные новые блоки
    "send_sticker": {
        "title": "Отправить стикер",
        "category": "Отправка",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID или юзернейм чата", "type": "str", "default": ""},
            "sticker": {"label": "ID или путь к стикеру", "type": "str", "default": ""}
        }
    },
    "send_reaction": {
        "title": "Поставить реакцию",
        "category": "Отправка",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID или юзернейм чата", "type": "str", "default": ""},
            "message_id": {"label": "ID сообщения", "type": "int", "default": 0},
            "reaction": {"label": "Эмодзи реакции (например, 🔥)", "type": "str", "default": "👍"}
        }
    },
    "send_story": {
        "title": "Опубликовать историю",
        "category": "Отправка",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "media_path": {"label": "Путь к медиа (фото/видео)", "type": "str", "default": ""},
            "caption": {"label": "Подпись к истории", "type": "str", "default": ""}
        }
    },
    "set_chat_slow_mode": {
        "title": "Медленный режим",
        "category": "Администрирование",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID или юзернейм чата", "type": "str", "default": ""},
            "seconds": {"label": "Интервал медленного режима (сек)", "type": "int", "default": 10}
        }
    },
    "set_chat_permissions": {
        "title": "Права чата",
        "category": "Администрирование",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID или юзернейм чата", "type": "str", "default": ""},
            "send_messages": {"label": "Отправка сообщений (1 - да, 0 - нет)", "type": "int", "default": 1},
            "send_media": {"label": "Отправка медиа (1 - да, 0 - нет)", "type": "int", "default": 1}
        }
    },
    "get_chat": {
        "title": "Информация о чате",
        "category": "Профиль",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID или юзернейм чата", "type": "str", "default": ""}
        } # Запишет в переменные {chat_title}, {chat_members_count}
    },
    "scrape_chat_members": {
        "title": "Сбор участников чата",
        "category": "Активность",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID или юзернейм чата", "type": "str", "default": ""},
            "output_file": {"label": "Путь к файлу результатов (.txt)", "type": "str", "default": "scraped_users.txt"}
        }
    },
    "pin_chat": {
        "title": "Закрепить чат",
        "category": "Активность",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID или юзернейм чата", "type": "str", "default": ""}
        }
    },
    "unpin_chat": {
        "title": "Открепить чат",
        "category": "Активность",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID или юзернейм чата", "type": "str", "default": ""}
        }
    },
    "bot_start": {
        "title": "Запустить бота",
        "category": "Боты",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "bot_username": {"label": "Юзернейм бота", "type": "str", "default": ""},
            "payload": {"label": "Стартовый параметр (необязательно)", "type": "str", "default": ""}
        }
    },
    "bot_send_command": {
        "title": "Отправить команду",
        "category": "Боты",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "bot_username": {"label": "Юзернейм бота", "type": "str", "default": ""},
            "command": {"label": "Команда (например: /help)", "type": "str", "default": ""}
        }
    },
    "bot_click_inline": {
        "title": "Нажать inline-кнопку",
        "category": "Боты",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "post_url": {"label": "Ссылка на пост или Юзернейм/ID бота", "type": "str", "default": ""},
            "button_target": {"label": "Номер кнопки (1, 2...) или Текст", "type": "str", "default": "1"},
            "timeout": {"label": "Ожидание появления (сек)", "type": "int", "default": 15}
        }
    },
    "bot_click_keyboard": {
        "title": "Нажать кнопку меню",
        "category": "Боты",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "bot_username": {"label": "Юзернейм бота", "type": "str", "default": ""},
            "button_text": {"label": "Текст кнопки", "type": "str", "default": ""}
        }
    },
    "bot_open_web_app": {
        "title": "Открыть Mini App",
        "category": "Боты",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "bot_username": {"label": "Юзернейм бота", "type": "str", "default": ""},
            "short_name": {"label": "Короткое имя приложения (app_name)", "type": "str", "default": ""}
        }
    },
    "bot_inline_query": {
        "title": "Инлайн-запрос",
        "category": "Боты",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "bot_username": {"label": "Юзернейм инлайн-бота (например: @gif)", "type": "str", "default": ""},
            "query": {"label": "Поисковый запрос (например: cat)", "type": "str", "default": ""},
            "chat_id": {"label": "Куда отправить результат", "type": "str", "default": ""}
        }
    },
    "send_premium_message": {
        "title": "Премиум сообщение",
        "category": "Премиум",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "Юзернейм или ID чата", "type": "str", "default": ""},
            "text": {"label": "Текст (эмодзи в формате :ID_эмодзи:)", "type": "textarea", "default": "Привет :5343807270271166453:!"}
        }
    },
    "send_premium_reaction": {
        "title": "Премиум реакция",
        "category": "Премиум",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "Юзернейм или ID чата", "type": "str", "default": ""},
            "message_id": {"label": "ID сообщения", "type": "int", "default": 0},
            "reactions": {"label": "Эмодзи или ID (через запятую, до 3 шт)", "type": "str", "default": "👍, 🔥, ❤️"}
        }
    },
    "set_emoji_status": {
        "title": "Эмодзи-статус",
        "category": "Премиум",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "custom_emoji_id": {"label": "ID эмодзи (пусто для удаления)", "type": "str", "default": ""}
        }
    },
    "get_post_comments": {
        "title": "Получить комментарии",
        "category": "Утилиты",
        "inputs": ["prev"],
        "outputs": ["has_comments", "no_comments"],
        "params": {
            "chat_id": {"label": "Юзернейм или ID канала", "type": "str", "default": ""},
            "message_id": {"label": "ID поста", "type": "int", "default": 0},
            "limit": {"label": "Лимит комментариев", "type": "int", "default": 10}
        }
    },
    "ai_prompt": {
        "title": "Запрос к ИИ",
        "category": "Утилиты",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "prompt": {"label": "Запрос к ИИ (поддерживает {переменные})", "type": "textarea", "default": "Сделай краткую выжимку комментариев: {comments_text}"},
            "system_prompt": {"label": "Системный промпт", "type": "str", "default": "Ты полезный ИИ-помощник."}
        }
    },
    "string_contains": {
        "title": "Поиск текста",
        "category": "Утилиты",
        "inputs": ["prev"],
        "outputs": ["true", "false"],
        "params": {
            "text": {"label": "Исходный текст", "type": "textarea", "default": "{comments_text}"},
            "substring": {"label": "Искомая фраза", "type": "str", "default": "скам"}
        }
    },
    "write_file": {
        "title": "Записать в файл",
        "category": "Утилиты",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "file_path": {"label": "Путь к файлу", "type": "str", "default": "comments_log.txt"},
            "content": {"label": "Содержимое", "type": "textarea", "default": "{comments_text}\n---"},
            "mode": {
                "label": "Режим записи",
                "type": "select",
                "options": [
                    {"value": "append", "label": "Дописать в конец"},
                    {"value": "overwrite", "label": "Перезаписать"}
                ],
                "default": "append"
            }
        }
    },
    "read_file": {
        "title": "Прочитать файл",
        "category": "Утилиты",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "file_path": {"label": "Путь к файлу", "type": "str", "default": "input_data.txt"}
        }
    },
    "check_avatar": {
        "title": "Проверить аватар",
        "category": "Проверки",
        "inputs": ["prev"],
        "outputs": ["has_avatar", "no_avatar"],
        "params": {
            "chat_id": {"label": "Юзернейм или ID чата (пусто для себя)", "type": "str", "default": ""}
        }
    },
    "check_username": {
        "title": "Доступность юзернейма",
        "category": "Проверки",
        "inputs": ["prev"],
        "outputs": ["available", "taken"],
        "params": {
            "username": {"label": "Проверяемый юзернейм", "type": "str", "default": "shadowgram_test"}
        }
    },
    "check_user_status": {
        "title": "Статус пользователя",
        "category": "Проверки",
        "inputs": ["prev"],
        "outputs": ["online", "offline"],
        "params": {
            "chat_id": {"label": "Юзернейм или ID пользователя", "type": "str", "default": ""}
        }
    },
    "check_is_member": {
        "title": "Участие в группе",
        "category": "Проверки",
        "inputs": ["prev"],
        "outputs": ["member", "not_member"],
        "params": {
            "chat_id": {"label": "ID группы/канала", "type": "str", "default": ""},
            "user_id": {"label": "ID пользователя (пусто для себя)", "type": "str", "default": ""}
        }
    },
    "check_is_premium": {
        "title": "Наличие Премиума",
        "category": "Проверки",
        "inputs": ["prev"],
        "outputs": ["premium", "not_premium"],
        "params": {
            "chat_id": {"label": "ID пользователя (пусто для себя)", "type": "str", "default": ""}
        }
    },
    "check_bio_link": {
        "title": "Ссылка в описании",
        "category": "Проверки",
        "inputs": ["prev"],
        "outputs": ["has_link", "no_link"],
        "params": {
            "chat_id": {"label": "ID пользователя (пусто для себя)", "type": "str", "default": ""}
        }
    },
    "check_is_admin": {
        "title": "Проверить админа",
        "category": "Проверки",
        "inputs": ["prev"],
        "outputs": ["admin", "not_admin"],
        "params": {
            "chat_id": {"label": "ID группы/канала", "type": "str", "default": ""},
            "user_id": {"label": "ID пользователя (пусто для себя)", "type": "str", "default": ""}
        }
    },
    "check_chat_type": {
        "title": "Тип чата",
        "category": "Проверки",
        "inputs": ["prev"],
        "outputs": ["private", "group", "channel"],
        "params": {
            "chat_id": {"label": "ID чата", "type": "str", "default": ""}
        }
    },
    "check_is_restricted": {
        "title": "Наличие ограничений",
        "category": "Проверки",
        "inputs": ["prev"],
        "outputs": ["restricted", "normal"],
        "params": {
            "chat_id": {"label": "ID группы/канала", "type": "str", "default": ""},
            "user_id": {"label": "ID пользователя (пусто для себя)", "type": "str", "default": ""}
        }
    },
    "check_is_contact": {
        "title": "В контактах",
        "category": "Проверки",
        "inputs": ["prev"],
        "outputs": ["contact", "not_contact"],
        "params": {
            "user_id": {"label": "ID пользователя", "type": "str", "default": ""}
        }
    },
    "get_chat_history_messages": {
        "title": "История сообщений",
        "category": "Утилиты",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "Юзернейм или ID чата", "type": "str", "default": ""},
            "limit": {"label": "Лимит сообщений", "type": "int", "default": 20}
        }
    },
    "send_poll": {
        "title": "Отправить опрос",
        "category": "Отправка",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "Юзернейм или ID чата", "type": "str", "default": ""},
            "question": {"label": "Вопрос опроса", "type": "str", "default": "Вам нравится ShadowGram?"},
            "options": {"label": "Варианты (через запятую)", "type": "str", "default": "Да, Нет, Очень!"},
            "is_anonymous": {
                "label": "Анонимно",
                "type": "select",
                "options": [
                    {"value": "true", "label": "Да"},
                    {"value": "false", "label": "Нет"}
                ],
                "default": "true"
            }
        }
    },
    "download_media": {
        "title": "Скачать медиа",
        "category": "Активность",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "Юзернейм или ID чата", "type": "str", "default": ""},
            "message_id": {"label": "ID сообщения (0 для последнего)", "type": "int", "default": 0},
            "download_dir": {"label": "Папка скачивания", "type": "str", "default": "downloads"}
        }
    },
    "check_is_bot": {
        "title": "Является ботом",
        "category": "Проверки",
        "inputs": ["prev"],
        "outputs": ["bot", "user"],
        "params": {
            "chat_id": {"label": "ID пользователя", "type": "str", "default": ""}
        }
    },
    "check_message_contains": {
        "title": "Содержимое сообщения",
        "category": "Проверки",
        "inputs": ["prev"],
        "outputs": ["true", "false"],
        "params": {
            "chat_id": {"label": "ID чата", "type": "str", "default": ""},
            "message_id": {"label": "ID сообщения (0 для последнего)", "type": "int", "default": 0},
            "keyword": {"label": "Искомая фраза", "type": "str", "default": "привет"}
        }
    },
    "check_unread_count": {
        "title": "Непрочитанные",
        "category": "Проверки",
        "inputs": ["prev"],
        "outputs": ["has_unread", "no_unread"],
        "params": {
            "chat_id": {"label": "ID чата", "type": "str", "default": ""}
        }
    },
    "check_chat_members_count": {
        "title": "Число участников",
        "category": "Проверки",
        "inputs": ["prev"],
        "outputs": ["more", "less"],
        "params": {
            "chat_id": {"label": "ID группы/канала", "type": "str", "default": ""},
            "threshold": {"label": "Порог участников", "type": "int", "default": 100}
        }
    },
    "check_is_pinned": {
        "title": "Сообщение закреплено",
        "category": "Проверки",
        "inputs": ["prev"],
        "outputs": ["pinned", "not_pinned"],
        "params": {
            "chat_id": {"label": "ID чата", "type": "str", "default": ""},
            "message_id": {"label": "ID сообщения (0 для последнего)", "type": "int", "default": 0}
        }
    },
    "check_profile_has_username": {
        "title": "Наличие юзернейма",
        "category": "Проверки",
        "inputs": ["prev"],
        "outputs": ["has_username", "no_username"],
        "params": {
            "chat_id": {"label": "ID пользователя (пусто для себя)", "type": "str", "default": ""}
        }
    },
    "check_profile_phone_visible": {
        "title": "Видимость телефона",
        "category": "Проверки",
        "inputs": ["prev"],
        "outputs": ["visible", "hidden"],
        "params": {
            "chat_id": {"label": "ID пользователя (пусто для себя)", "type": "str", "default": ""}
        }
    },
    "check_profile_is_scam": {
        "title": "Метка Scam/Fake",
        "category": "Проверки",
        "inputs": ["prev"],
        "outputs": ["scam_or_fake", "clean"],
        "params": {
            "chat_id": {"label": "ID пользователя (пусто для себя)", "type": "str", "default": ""}
        }
    },
    "check_profile_stories_enabled": {
        "title": "Активные истории",
        "category": "Проверки",
        "inputs": ["prev"],
        "outputs": ["has_stories", "no_stories"],
        "params": {
            "chat_id": {"label": "ID пользователя (пусто для себя)", "type": "str", "default": ""}
        }
    },
    "check_profile_is_mutual": {
        "title": "Взаимный контакт",
        "category": "Проверки",
        "inputs": ["prev"],
        "outputs": ["mutual", "not_mutual"],
        "params": {
            "chat_id": {"label": "ID пользователя", "type": "str", "default": ""}
        }
    },
    "check_channel_subscription": {
        "title": "Подписка на канал",
        "category": "Проверки",
        "inputs": ["prev"],
        "outputs": ["subscribed", "not_subscribed"],
        "params": {
            "chat_id": {"label": "ID канала", "type": "str", "default": ""},
            "user_id": {"label": "ID пользователя (пусто для себя)", "type": "str", "default": ""}
        }
    },
    "get_channel_posts": {
        "title": "Выгрузить посты",
        "category": "Чаты",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID канала", "type": "str", "default": ""},
            "limit": {"label": "Количество постов", "type": "int", "default": 5}
        }
    },
    "approve_join_requests": {
        "title": "Одобрить заявки",
        "category": "Чаты",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID канала/группы", "type": "str", "default": ""},
            "user_id": {"label": "ID пользователя (пусто для всех)", "type": "str", "default": ""}
        }
    },
    "edit_channel_post": {
        "title": "Редактировать пост",
        "category": "Чаты",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID канала", "type": "str", "default": ""},
            "message_id": {"label": "ID поста", "type": "int", "default": 0},
            "new_text": {"label": "Новый текст поста", "type": "str", "default": ""}
        }
    },
    "delete_channel_post": {
        "title": "Удалить пост",
        "category": "Чаты",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID канала", "type": "str", "default": ""},
            "message_id": {"label": "ID поста", "type": "int", "default": 0}
        }
    },
    "comment_channel_post": {
        "title": "Оставить комментарий",
        "category": "Активность",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID канала", "type": "str", "default": ""},
            "message_id": {"label": "ID поста", "type": "int", "default": 0},
            "text": {"label": "Текст комментария", "type": "str", "default": "Отличный пост!"}
        }
    },
    "forward_channel_post": {
        "title": "Переслать пост",
        "category": "Активность",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID канала (откуда)", "type": "str", "default": ""},
            "message_id": {"label": "ID сообщения/поста", "type": "int", "default": 0},
            "to_chat_id": {"label": "Куда переслать", "type": "str", "default": ""}
        }
    },
    "react_to_post": {
        "title": "Реакция на пост",
        "category": "Активность",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID канала", "type": "str", "default": ""},
            "message_id": {"label": "ID сообщения/поста", "type": "int", "default": 0},
            "emoji": {"label": "Эмодзи (например, 👍)", "type": "str", "default": "👍"}
        }
    },
    "share_post_link": {
        "title": "Ссылка на пост",
        "category": "Активность",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "Юзернейм или ID канала", "type": "str", "default": ""},
            "message_id": {"label": "ID сообщения/поста", "type": "int", "default": 0}
        }
    },
    "save_draft": {
        "title": "Сохранить черновик",
        "category": "Отправка",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "Юзернейм или ID чата", "type": "str", "default": ""},
            "text": {"label": "Текст черновика", "type": "str", "default": ""}
        }
    },
    "view_user_stories": {
        "title": "Просмотреть истории",
        "category": "Активность",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID пользователя", "type": "str", "default": ""}
        }
    },
    "download_profile_photos": {
        "title": "Скачать аватарку",
        "category": "Профиль",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "chat_id": {"label": "ID пользователя", "type": "str", "default": ""},
            "download_dir": {"label": "Папка скачивания", "type": "str", "default": "downloads/avatars"}
        }
    },
    "get_unread_dialogs": {
        "title": "Непрочитанные диалоги",
        "category": "Утилиты",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "limit": {"label": "Макс. диалогов", "type": "int", "default": 20}
        }
    },
    "read_line": {
        "title": "Считать строку",
        "category": "Утилиты",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "file_path": {"label": "Путь к файлу (.txt)", "type": "file", "default": ""},
            "var_name": {"label": "Имя переменной", "type": "str", "default": "username_var"}
        }
    },
    "get_file_from_folder": {
        "title": "Файл из папки",
        "category": "Утилиты",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "folder_path": {"label": "Путь к папке", "type": "folder", "default": ""},
            "selection_mode": {"label": "Выбор (1-Случайный, 2-По очереди)", "type": "int", "default": 1},
            "var_name": {"label": "Имя переменной", "type": "str", "default": "media_path"}
        }
    },

    # ==========================================
    # 9. СЕТЬ И ДАННЫЕ (Network & Global Data)
    # ==========================================
    "http_request": {
        "title": "HTTP Запрос",
        "category": "Сеть",
        "inputs": ["prev"],
        "outputs": ["next", "error"],
        "params": {
            "method": {
                "label": "Метод",
                "type": "select",
                "options": [
                    {"value": "GET", "label": "GET"},
                    {"value": "POST", "label": "POST"}
                ],
                "default": "GET"
            },
            "url": {"label": "URL (поддерживает {переменные})", "type": "str", "default": "https://api.example.com/data"},
            "headers": {"label": "Заголовки (JSON)", "type": "textarea", "default": "{}"},
            "body": {"label": "Тело (для POST)", "type": "textarea", "default": ""},
            "var_name": {"label": "Сохранить ответ в", "type": "str", "default": "http_response"}
        }
    },
    "set_global_var": {
        "title": "Установить глоб. переменную",
        "category": "Данные",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "var_name": {"label": "Имя переменной", "type": "str", "default": "counter"},
            "var_value": {"label": "Значение", "type": "str", "default": "1"}
        }
    },
    "increase_global_counter": {
        "title": "Увеличить счетчик",
        "category": "Данные",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "var_name": {"label": "Имя счетчика", "type": "str", "default": "total_sent"},
            "step": {"label": "Шаг", "type": "int", "default": 1}
        }
    },
    "get_from_resource": {
        "title": "Получить из Ресурса",
        "category": "Данные",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "resource_id": {"label": "ID ресурса (имя)", "type": "str", "default": "names_list"},
            "file_path": {"label": "Путь к файлу (если ресурс еще не создан)", "type": "file", "default": ""},
            "mode": {
                "label": "Режим",
                "type": "select",
                "options": [
                    {"value": "sequential", "label": "По очереди (зациклено)"},
                    {"value": "random", "label": "Случайно"},
                    {"value": "delete", "label": "Взять и удалить"}
                ],
                "default": "sequential"
            },
            "var_name": {"label": "Сохранить в переменную", "type": "str", "default": "resource_val"}
        }
    },
    "parse_json": {
        "title": "Распарсить JSON",
        "category": "Данные",
        "inputs": ["prev"],
        "outputs": ["next"],
        "params": {
            "json_string": {"label": "JSON строка", "type": "str", "default": "{http_response}"},
            "key_path": {"label": "Путь к ключу (напр. user.id или 0.name)", "type": "str", "default": "data.id"},
            "var_name": {"label": "Сохранить в переменную", "type": "str", "default": "parsed_val"}
        }
    },
    "regex_extract": {
        "title": "Регулярное выражение (Regex)",
        "category": "Данные",
        "inputs": ["prev"],
        "outputs": ["found", "not_found"],
        "params": {
            "text": {"label": "Исходный текст", "type": "str", "default": "{file_content}"},
            "pattern": {"label": "Regex шаблон (c группой ())", "type": "str", "default": r"code: (\d+)"},
            "var_name": {"label": "Сохранить результат в", "type": "str", "default": "extracted_val"}
        }
    },
    "wait_for_message": {
        "title": "Ожидать сообщение",
        "category": "Активность",
        "inputs": ["prev"],
        "outputs": ["received", "timeout"],
        "params": {
            "chat_id": {"label": "Юзернейм или ID чата", "type": "str", "default": ""},
            "timeout": {"label": "Таймаут ожидания (сек)", "type": "int", "default": 30},
            "var_name": {"label": "Сохранить сообщение в", "type": "str", "default": "incoming_message"}
        }
    },
    "execute_sub_scenario": {
        "title": "Выполнить подсценарий",
        "category": "Управление",
        "inputs": ["prev"],
        "outputs": ["next", "error"],
        "params": {
            "scenario_path": {"label": "Путь к файлу сценария (.sgn)", "type": "file", "default": ""}
        }
    }
}

# Dynamically merge custom nodes specifications
try:
    from src.core.managers import plugin_manager
    NODE_SPECS.update(plugin_manager.custom_specs)
except Exception as e:
    print(f"Error merging custom node specs: {e}")
