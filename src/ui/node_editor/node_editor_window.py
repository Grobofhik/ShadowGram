from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QSplitter, 
                             QMessageBox, QLineEdit, QTextEdit, QSpinBox, 
                             QFileDialog, QScrollArea, QMenu, QDialog)
from PyQt6.QtCore import Qt, QPointF, QMetaObject, Q_ARG, pyqtSlot
from PyQt6.QtGui import QIcon, QFont

import os
import json
from src import styles
from src.ui.node_editor.node_classes import NodeBlockItem, ConnectionItem
from src.ui.node_editor.node_canvas import NodeCanvasScene, NodeCanvasView
from src.ui.node_editor.node_specs import NODE_SPECS
from src.ui.node_editor.components import ConsolePanel, PropertiesDock
from src.ui.node_editor.components.accounts_panel import AccountsPanel

class NodeEditorWindow(QWidget):
    def __init__(self, selected_accounts=None, manager=None):
        super().__init__()
        self.selected_accounts = selected_accounts or []
        self.manager = manager
        
        self.setWindowTitle("ShadowGram Node Editor")
        self.resize(1100, 750)
        self.setStyleSheet(styles.STYLESHEET)
        
        # Component references
        self.properties_dock = None
        self.console_widget = None
        
        from src.ui.active_tasks_window import ActiveTasksWindow
        self.active_tasks_win = ActiveTasksWindow()
        self.active_tasks_win.stop_requested.connect(self.stop_running_task)
        self.running_tasks = {} # { task_id: (asyncio_task, loop) }
        self.local_tasks = {} # { task_id: { "loop": loop, "tasks": [], "instances": [] } }
        
        self.init_ui()

    def init_ui(self):
        # Photoshop style layout: Clean dark container
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Photoshop-like top toolbar for editing and adding nodes
        self.top_toolbar = QFrame()
        self.top_toolbar.setObjectName("TopToolbar")
        self.top_toolbar.setStyleSheet(f"""
            QFrame#TopToolbar {{
                background-color: {styles.COLOR_ACCENT_BG};
                border-bottom: 1px solid {styles.COLOR_BORDER};
            }}
            QPushButton {{
                background-color: {styles.COLOR_BG};
                color: {styles.COLOR_TEXT_MAIN};
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {styles.COLOR_HOVER_BG};
                border-color: {styles.COLOR_PRIMARY};
            }}
            QPushButton::menu-indicator {{
                image: none; /* Hide default native arrow for custom clean design */
            }}
            QMenu {{
                background-color: {styles.COLOR_ACCENT_BG};
                color: {styles.COLOR_TEXT_MAIN};
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 20px 6px 12px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {styles.COLOR_HOVER_BG};
                color: {styles.COLOR_PRIMARY};
            }}
        """)
        
        toolbar_layout = QHBoxLayout(self.top_toolbar)
        toolbar_layout.setContentsMargins(15, 8, 15, 8)
        toolbar_layout.setSpacing(12)
        
        # Toggle Accounts Panel Button
        btn_toggle_acc = QPushButton("Аккаунты")
        btn_toggle_acc.clicked.connect(self.toggle_accounts_panel)
        toolbar_layout.addWidget(btn_toggle_acc)
        
        # 1. Dropdown: Control Flow / Управление
        btn_flow = QPushButton("Сценарий ▼")
        menu_flow = QMenu(self)
        
        act_start = menu_flow.addAction("Старт")
        act_start.triggered.connect(lambda: self.add_node_by_type("start"))
        
        act_end = menu_flow.addAction("Конец")
        act_end.triggered.connect(lambda: self.add_node_by_type("end"))
        
        act_delay = menu_flow.addAction("Пауза")
        act_delay.triggered.connect(lambda: self.add_node_by_type("delay"))
        
        act_rand_delay = menu_flow.addAction("Случайная пауза")
        act_rand_delay.triggered.connect(lambda: self.add_node_by_type("random_delay"))
        
        act_if = menu_flow.addAction("Условие ЕСЛИ")
        act_if.triggered.connect(lambda: self.add_node_by_type("if_condition"))
        
        act_rand_branch = menu_flow.addAction("Случайный выбор пути")
        act_rand_branch.triggered.connect(lambda: self.add_node_by_type("random_branch"))
        act_loop = menu_flow.addAction("Цикл")
        act_loop.triggered.connect(lambda: self.add_node_by_type("loop"))
        
        btn_flow.setMenu(menu_flow)
        toolbar_layout.addWidget(btn_flow)
        
        # 2. Dropdown: Profile & Contacts / Профиль и Контакты
        btn_profile = QPushButton("Профиль ▼")
        menu_profile = QMenu(self)
        
        # Submenu: Данные аккаунта
        sub_profile_acc = menu_profile.addMenu("Данные аккаунта")
        act_getme = sub_profile_acc.addAction("Информация о себе")
        act_getme.triggered.connect(lambda: self.add_node_by_type("get_me"))
        act_bio = sub_profile_acc.addAction("Установить БИО")
        act_bio.triggered.connect(lambda: self.add_node_by_type("set_bio"))
        act_avatar = sub_profile_acc.addAction("Установить аватар")
        act_avatar.triggered.connect(lambda: self.add_node_by_type("set_avatar"))
        act_set_name = sub_profile_acc.addAction("Установить имя")
        act_set_name.triggered.connect(lambda: self.add_node_by_type("set_name"))
        act_set_username = sub_profile_acc.addAction("Установить юзернейм")
        act_set_username.triggered.connect(lambda: self.add_node_by_type("set_username"))
        act_common_chats = sub_profile_acc.addAction("Общие чаты")
        act_common_chats.triggered.connect(lambda: self.add_node_by_type("get_common_chats"))
        act_dl_avatar = sub_profile_acc.addAction("Скачать аватарку")
        act_dl_avatar.triggered.connect(lambda: self.add_node_by_type("download_profile_photos"))
        
        # Submenu: Безопасность
        sub_profile_sec = menu_profile.addMenu("Безопасность")
        act_set_privacy = sub_profile_sec.addAction("Настройки приватности")
        act_set_privacy.triggered.connect(lambda: self.add_node_by_type("set_privacy"))
        act_2fa = sub_profile_sec.addAction("Установить 2FA")
        act_2fa.triggered.connect(lambda: self.add_node_by_type("enable_2fa"))
        
        # Submenu: Контакты
        sub_profile_cnt = menu_profile.addMenu("Контакты")
        act_search = sub_profile_cnt.addAction("Поиск пользователей")
        act_search.triggered.connect(lambda: self.add_node_by_type("search_contacts"))
        act_import_contacts = sub_profile_cnt.addAction("Импорт контактов")
        act_import_contacts.triggered.connect(lambda: self.add_node_by_type("import_contacts"))
        act_contact = sub_profile_cnt.addAction("Добавить контакт")
        act_contact.triggered.connect(lambda: self.add_node_by_type("add_contact"))
        act_del_contacts = sub_profile_cnt.addAction("Удалить контакты")
        act_del_contacts.triggered.connect(lambda: self.add_node_by_type("delete_contacts"))
        act_block = sub_profile_cnt.addAction("Заблокировать юзера")
        act_block.triggered.connect(lambda: self.add_node_by_type("block_user"))
        act_unblock = sub_profile_cnt.addAction("Разблокировать юзера")
        act_unblock.triggered.connect(lambda: self.add_node_by_type("unblock_user"))
        
        # Root level info chat
        act_get_chat = menu_profile.addAction("Информация о чате")
        act_get_chat.triggered.connect(lambda: self.add_node_by_type("get_chat"))
        
        btn_profile.setMenu(menu_profile)
        toolbar_layout.addWidget(btn_profile)
        
        # 3. Dropdown: Sending Messages & Media / Отправка
        btn_sending = QPushButton("Отправка ▼")
        menu_sending = QMenu(self)
        
        # Submenu: Текст и сообщения
        sub_send_msg = menu_sending.addMenu("Текст и сообщения")
        act_msg = sub_send_msg.addAction("Отправить сообщение")
        act_msg.triggered.connect(lambda: self.add_node_by_type("send_message"))
        act_fwd = sub_send_msg.addAction("Переслать сообщения")
        act_fwd.triggered.connect(lambda: self.add_node_by_type("forward_messages"))
        act_edit = sub_send_msg.addAction("Редактировать сообщение")
        act_edit.triggered.connect(lambda: self.add_node_by_type("edit_message_text"))
        act_search_msg = sub_send_msg.addAction("Поиск сообщений")
        act_search_msg.triggered.connect(lambda: self.add_node_by_type("search_messages"))
        act_del_msg = sub_send_msg.addAction("Удалить сообщения")
        act_del_msg.triggered.connect(lambda: self.add_node_by_type("delete_messages"))
        act_draft = sub_send_msg.addAction("Сохранить черновик")
        act_draft.triggered.connect(lambda: self.add_node_by_type("save_draft"))
        act_send_post_comment = sub_send_msg.addAction("Отправить комментарий к посту")
        act_send_post_comment.triggered.connect(lambda: self.add_node_by_type("send_post_comment"))
        
        # Submenu: Медиафайлы
        sub_send_med = menu_sending.addMenu("Медиафайлы")
        act_photo = sub_send_med.addAction("Отправить фото")
        act_photo.triggered.connect(lambda: self.add_node_by_type("send_photo"))
        act_video = sub_send_med.addAction("Отправить видео")
        act_video.triggered.connect(lambda: self.add_node_by_type("send_video"))
        act_doc = sub_send_med.addAction("Отправить документ")
        act_doc.triggered.connect(lambda: self.add_node_by_type("send_document"))
        act_voice = sub_send_med.addAction("Отправить голосовое")
        act_voice.triggered.connect(lambda: self.add_node_by_type("send_voice"))
        act_audio = sub_send_med.addAction("Отправить аудио")
        act_audio.triggered.connect(lambda: self.add_node_by_type("send_audio"))
        act_gif = sub_send_med.addAction("Отправить GIF")
        act_gif.triggered.connect(lambda: self.add_node_by_type("send_gif"))
        act_story = sub_send_med.addAction("Опубликовать историю")
        act_story.triggered.connect(lambda: self.add_node_by_type("send_story"))
        
        # Submenu: Интерактив
        sub_send_int = menu_sending.addMenu("Интерактив")
        act_sticker = sub_send_int.addAction("Отправить стикер")
        act_sticker.triggered.connect(lambda: self.add_node_by_type("send_sticker"))
        act_reaction = sub_send_int.addAction("Поставить реакцию")
        act_reaction.triggered.connect(lambda: self.add_node_by_type("send_reaction"))
        act_loc = sub_send_int.addAction("Отправить локацию")
        act_loc.triggered.connect(lambda: self.add_node_by_type("send_location"))
        act_dice = sub_send_int.addAction("Отправить кости/игры")
        act_dice.triggered.connect(lambda: self.add_node_by_type("send_dice"))
        act_poll = sub_send_int.addAction("Отправить опрос")
        act_poll.triggered.connect(lambda: self.add_node_by_type("send_poll"))
        
        btn_sending.setMenu(menu_sending)
        toolbar_layout.addWidget(btn_sending)
        
        # 4. Dropdown: Chats and Admin / Управление чатами
        btn_chats = QPushButton("Чаты ▼")
        menu_chats = QMenu(self)
        
        # Submenu: Создание и инфо
        sub_chats_cre = menu_chats.addMenu("Создание и инфо")
        act_group = sub_chats_cre.addAction("Создать группу")
        act_group.triggered.connect(lambda: self.add_node_by_type("create_group"))
        act_channel = sub_chats_cre.addAction("Создать канал")
        act_channel.triggered.connect(lambda: self.add_node_by_type("create_channel"))
        act_chtitle = sub_chats_cre.addAction("Изменить название")
        act_chtitle.triggered.connect(lambda: self.add_node_by_type("set_chat_title"))
        act_chdesc = sub_chats_cre.addAction("Изменить описание")
        act_chdesc.triggered.connect(lambda: self.add_node_by_type("set_chat_description"))
        act_chusername = sub_chats_cre.addAction("Изменить юзернейм чата")
        act_chusername.triggered.connect(lambda: self.add_node_by_type("set_chat_username"))
        act_chphoto = sub_chats_cre.addAction("Изменить аватар чата")
        act_chphoto.triggered.connect(lambda: self.add_node_by_type("set_chat_photo"))
        act_delchphoto = sub_chats_cre.addAction("Удалить аватар чата")
        act_delchphoto.triggered.connect(lambda: self.add_node_by_type("delete_chat_photo"))
        act_invlink = sub_chats_cre.addAction("Создать инвайт-ссылку")
        act_invlink.triggered.connect(lambda: self.add_node_by_type("export_chat_invite_link"))
        
        # Submenu: Модерация участников
        sub_chats_mod = menu_chats.addMenu("Модерация участников")
        act_restrict = sub_chats_mod.addAction("Ограничить пользователя")
        act_restrict.triggered.connect(lambda: self.add_node_by_type("restrict_chat_member"))
        act_promote = sub_chats_mod.addAction("Назначить админом")
        act_promote.triggered.connect(lambda: self.add_node_by_type("promote_chat_member"))
        act_ban = sub_chats_mod.addAction("Забанить пользователя")
        act_ban.triggered.connect(lambda: self.add_node_by_type("ban_chat_member"))
        act_unban = sub_chats_mod.addAction("Разбанить пользователя")
        act_unban.triggered.connect(lambda: self.add_node_by_type("unban_chat_member"))
        
        # Submenu: Управление сообщениями
        sub_chats_msg = menu_chats.addMenu("Управление сообщениями")
        act_pin = sub_chats_msg.addAction("Закрепить сообщение")
        act_pin.triggered.connect(lambda: self.add_node_by_type("pin_chat_message"))
        act_unpin = sub_chats_msg.addAction("Открепить сообщение")
        act_unpin.triggered.connect(lambda: self.add_node_by_type("unpin_chat_message"))
        
        # Submenu: Настройки чата
        sub_chats_set = menu_chats.addMenu("Настройки чата")
        act_slow = sub_chats_set.addAction("Медленный режим")
        act_slow.triggered.connect(lambda: self.add_node_by_type("set_chat_slow_mode"))
        act_perms = sub_chats_set.addAction("Права чата")
        act_perms.triggered.connect(lambda: self.add_node_by_type("set_chat_permissions"))
        
        # Submenu: Каналы
        sub_chats_chan = menu_chats.addMenu("Каналы")
        act_posts = sub_chats_chan.addAction("Выгрузить посты")
        act_posts.triggered.connect(lambda: self.add_node_by_type("get_channel_posts"))
        act_approve = sub_chats_chan.addAction("Одобрить заявки")
        act_approve.triggered.connect(lambda: self.add_node_by_type("approve_join_requests"))
        act_edit_p = sub_chats_chan.addAction("Редактировать пост")
        act_edit_p.triggered.connect(lambda: self.add_node_by_type("edit_channel_post"))
        act_del_p = sub_chats_chan.addAction("Удалить пост")
        act_del_p.triggered.connect(lambda: self.add_node_by_type("delete_channel_post"))
        
        btn_chats.setMenu(menu_chats)
        toolbar_layout.addWidget(btn_chats)
        
        # 5. Dropdown: Activity / Активность
        btn_activity = QPushButton("Активность ▼")
        menu_activity = QMenu(self)
        
        # Submenu: Вступление и выход
        sub_act_join = menu_activity.addMenu("Вступление и выход")
        act_join = sub_act_join.addAction("Вступить в чат")
        act_join.triggered.connect(lambda: self.add_node_by_type("join_chat"))
        act_leave = sub_act_join.addAction("Выйти из чата")
        act_leave.triggered.connect(lambda: self.add_node_by_type("leave_chat"))
        act_mute = sub_act_join.addAction("Мьют уведомлений (Mute)")
        act_mute.triggered.connect(lambda: self.add_node_by_type("mute_chat"))
        
        # Submenu: Взаимодействие
        sub_act_int = menu_activity.addMenu("Взаимодействие")
        act_react = sub_act_int.addAction("Авто-Реакции")
        act_react.triggered.connect(lambda: self.add_node_by_type("auto_react"))
        act_aireply = sub_act_int.addAction("ИИ Автоответчик")
        act_aireply.triggered.connect(lambda: self.add_node_by_type("ai_reply"))
        act_read = sub_act_int.addAction("Прочитать сообщения")
        act_read.triggered.connect(lambda: self.add_node_by_type("read_chat_history"))
        act_scrape = sub_act_int.addAction("Сбор участников чата")
        act_scrape.triggered.connect(lambda: self.add_node_by_type("scrape_chat_members"))
        act_download = sub_act_int.addAction("Скачать медиа")
        act_download.triggered.connect(lambda: self.add_node_by_type("download_media"))
        act_stories = sub_act_int.addAction("Просмотреть истории")
        act_stories.triggered.connect(lambda: self.add_node_by_type("view_user_stories"))
        
        # Submenu: Активность в каналах
        sub_act_chan = menu_activity.addMenu("Активность в каналах")
        act_comment = sub_act_chan.addAction("Оставить комментарий")
        act_comment.triggered.connect(lambda: self.add_node_by_type("comment_channel_post"))
        act_get_last_comment = sub_act_chan.addAction("Прочитать последний комментарий")
        act_get_last_comment.triggered.connect(lambda: self.add_node_by_type("get_last_comment"))
        act_extract_num = sub_act_chan.addAction("Извлечь и увеличить число")
        act_extract_num.triggered.connect(lambda: self.add_node_by_type("extract_increment_number"))
        act_forward = sub_act_chan.addAction("Переслать пост")
        act_forward.triggered.connect(lambda: self.add_node_by_type("forward_channel_post"))
        act_post_react = sub_act_chan.addAction("Реакция на пост")
        act_post_react.triggered.connect(lambda: self.add_node_by_type("react_to_post"))
        act_post_link = sub_act_chan.addAction("Ссылка на пост")
        act_post_link.triggered.connect(lambda: self.add_node_by_type("share_post_link"))
        
        # Submenu: Список чатов
        sub_act_list = menu_activity.addMenu("Список чатов")
        act_arc = sub_act_list.addAction("Архивировать чат")
        act_arc.triggered.connect(lambda: self.add_node_by_type("archive_chats"))
        act_unarc = sub_act_list.addAction("Разархивировать чат")
        act_unarc.triggered.connect(lambda: self.add_node_by_type("unarchive_chats"))
        act_pin = sub_act_list.addAction("Закрепить чат")
        act_pin.triggered.connect(lambda: self.add_node_by_type("pin_chat"))
        act_unpin = sub_act_list.addAction("Открепить чат")
        act_unpin.triggered.connect(lambda: self.add_node_by_type("unpin_chat"))
        
        btn_activity.setMenu(menu_activity)
        toolbar_layout.addWidget(btn_activity)
        
        # 6. Dropdown: Bots / Боты
        btn_bots = QPushButton("Боты ▼")
        menu_bots = QMenu(self)
        
        act_bot_start = menu_bots.addAction("Запустить бота")
        act_bot_start.triggered.connect(lambda: self.add_node_by_type("bot_start"))
        act_bot_cmd = menu_bots.addAction("Отправить команду")
        act_bot_cmd.triggered.connect(lambda: self.add_node_by_type("bot_send_command"))
        act_bot_inline = menu_bots.addAction("Нажать inline-кнопку")
        act_bot_inline.triggered.connect(lambda: self.add_node_by_type("bot_click_inline"))
        act_bot_keyboard = menu_bots.addAction("Нажать кнопку меню")
        act_bot_keyboard.triggered.connect(lambda: self.add_node_by_type("bot_click_keyboard"))
        act_bot_webapp = menu_bots.addAction("Открыть Mini App")
        act_bot_webapp.triggered.connect(lambda: self.add_node_by_type("bot_open_web_app"))
        act_bot_inlineq = menu_bots.addAction("Инлайн-запрос")
        act_bot_inlineq.triggered.connect(lambda: self.add_node_by_type("bot_inline_query"))
        
        btn_bots.setMenu(menu_bots)
        toolbar_layout.addWidget(btn_bots)
        
        # 7. Dropdown: Premium / Премиум
        btn_premium = QPushButton("Премиум ▼")
        menu_premium = QMenu(self)
        
        act_prem_msg = menu_premium.addAction("Премиум сообщение")
        act_prem_msg.triggered.connect(lambda: self.add_node_by_type("send_premium_message"))
        act_prem_react = menu_premium.addAction("Премиум реакция")
        act_prem_react.triggered.connect(lambda: self.add_node_by_type("send_premium_reaction"))
        act_prem_status = menu_premium.addAction("Эмодзи-статус")
        act_prem_status.triggered.connect(lambda: self.add_node_by_type("set_emoji_status"))
        
        btn_premium.setMenu(menu_premium)
        toolbar_layout.addWidget(btn_premium)
        
        # 8. Dropdown: Utilities / Вспомогательные
        btn_utils = QPushButton("Утилиты ▼")
        menu_utils = QMenu(self)
        
        act_get_comments = menu_utils.addAction("Получить комментарии")
        act_get_comments.triggered.connect(lambda: self.add_node_by_type("get_post_comments"))
        act_ai_prompt = menu_utils.addAction("Запрос к ИИ")
        act_ai_prompt.triggered.connect(lambda: self.add_node_by_type("ai_prompt"))
        act_str_contains = menu_utils.addAction("Поиск текста")
        act_str_contains.triggered.connect(lambda: self.add_node_by_type("string_contains"))
        act_write_file = menu_utils.addAction("Записать в файл")
        act_write_file.triggered.connect(lambda: self.add_node_by_type("write_file"))
        act_read_file = menu_utils.addAction("Прочитать файл")
        act_read_file.triggered.connect(lambda: self.add_node_by_type("read_file"))
        act_history = menu_utils.addAction("История сообщений")
        act_history.triggered.connect(lambda: self.add_node_by_type("get_chat_history_messages"))
        act_unread_dialogs = menu_utils.addAction("Непрочитанные диалоги")
        act_unread_dialogs.triggered.connect(lambda: self.add_node_by_type("get_unread_dialogs"))
        act_read_line = menu_utils.addAction("Считать строку")
        act_read_line.triggered.connect(lambda: self.add_node_by_type("read_line"))
        act_folder_file = menu_utils.addAction("Файл из папки")
        act_folder_file.triggered.connect(lambda: self.add_node_by_type("get_file_from_folder"))
        
        btn_utils.setMenu(menu_utils)
        toolbar_layout.addWidget(btn_utils)
        
        # 9. Dropdown: Checks / Проверки
        btn_checks = QPushButton("Проверки ▼")
        menu_checks = QMenu(self)
        
        act_chk_avatar = menu_checks.addAction("Проверить аватар")
        act_chk_avatar.triggered.connect(lambda: self.add_node_by_type("check_avatar"))
        act_chk_user = menu_checks.addAction("Доступность юзернейма")
        act_chk_user.triggered.connect(lambda: self.add_node_by_type("check_username"))
        act_chk_status = menu_checks.addAction("Статус пользователя")
        act_chk_status.triggered.connect(lambda: self.add_node_by_type("check_user_status"))
        act_chk_member = menu_checks.addAction("Участие в группе")
        act_chk_member.triggered.connect(lambda: self.add_node_by_type("check_is_member"))
        act_chk_prem = menu_checks.addAction("Наличие Премиума")
        act_chk_prem.triggered.connect(lambda: self.add_node_by_type("check_is_premium"))
        act_chk_bio = menu_checks.addAction("Ссылка в описании")
        act_chk_bio.triggered.connect(lambda: self.add_node_by_type("check_bio_link"))
        act_chk_admin = menu_checks.addAction("Проверить админа")
        act_chk_admin.triggered.connect(lambda: self.add_node_by_type("check_is_admin"))
        act_chk_type = menu_checks.addAction("Тип чата")
        act_chk_type.triggered.connect(lambda: self.add_node_by_type("check_chat_type"))
        act_chk_restr = menu_checks.addAction("Наличие ограничений")
        act_chk_restr.triggered.connect(lambda: self.add_node_by_type("check_is_restricted"))
        act_chk_cont = menu_checks.addAction("В контактах")
        act_chk_cont.triggered.connect(lambda: self.add_node_by_type("check_is_contact"))
        act_chk_bot = menu_checks.addAction("Является ботом")
        act_chk_bot.triggered.connect(lambda: self.add_node_by_type("check_is_bot"))
        act_chk_msg = menu_checks.addAction("Содержимое сообщения")
        act_chk_msg.triggered.connect(lambda: self.add_node_by_type("check_message_contains"))
        act_chk_unread = menu_checks.addAction("Непрочитанные")
        act_chk_unread.triggered.connect(lambda: self.add_node_by_type("check_unread_count"))
        act_chk_members = menu_checks.addAction("Число участников")
        act_chk_members.triggered.connect(lambda: self.add_node_by_type("check_chat_members_count"))
        act_chk_pinned = menu_checks.addAction("Сообщение закреплено")
        act_chk_pinned.triggered.connect(lambda: self.add_node_by_type("check_is_pinned"))
        act_chk_pr_username = menu_checks.addAction("Наличие юзернейма")
        act_chk_pr_username.triggered.connect(lambda: self.add_node_by_type("check_profile_has_username"))
        act_chk_pr_phone = menu_checks.addAction("Видимость телефона")
        act_chk_pr_phone.triggered.connect(lambda: self.add_node_by_type("check_profile_phone_visible"))
        act_chk_pr_scam = menu_checks.addAction("Метка Scam/Fake")
        act_chk_pr_scam.triggered.connect(lambda: self.add_node_by_type("check_profile_is_scam"))
        act_chk_pr_stories = menu_checks.addAction("Активные истории")
        act_chk_pr_stories.triggered.connect(lambda: self.add_node_by_type("check_profile_stories_enabled"))
        act_chk_pr_mutual = menu_checks.addAction("Взаимный контакт")
        act_chk_pr_mutual.triggered.connect(lambda: self.add_node_by_type("check_profile_is_mutual"))
        act_chk_chan_sub = menu_checks.addAction("Подписка на канал")
        act_chk_chan_sub.triggered.connect(lambda: self.add_node_by_type("check_channel_subscription"))
        
        btn_checks.setMenu(menu_checks)
        toolbar_layout.addWidget(btn_checks)
        
        # 10. Dropdown: Plugins / Плагины
        btn_plugins = QPushButton("Плагины ▼")
        menu_plugins = QMenu(self)
        
        from src.core.managers import plugin_manager
        if plugin_manager.custom_specs:
            for action_name, action_spec in plugin_manager.custom_specs.items():
                title = action_spec.get("title", action_name)
                # Correctly bind the parameter to a lambda using default argument
                act = menu_plugins.addAction(title)
                act.triggered.connect(lambda checked=False, name=action_name: self.add_node_by_type(name))
        else:
            act_none = menu_plugins.addAction("Нет загруженных плагинов")
            act_none.setEnabled(False)
            
        btn_plugins.setMenu(menu_plugins)
        toolbar_layout.addWidget(btn_plugins)
        
        toolbar_layout.addStretch(1)
        
        # Utilities / File management (Photoshop actions)
        btn_load = QPushButton("Открыть")
        btn_load.clicked.connect(self.load_scenario)
        toolbar_layout.addWidget(btn_load)
        
        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self.save_scenario)
        toolbar_layout.addWidget(btn_save)
        
        btn_clear = QPushButton("Очистить")
        btn_clear.clicked.connect(self.clear_canvas)
        toolbar_layout.addWidget(btn_clear)
        
        btn_run = QPushButton("ЗАПУСТИТЬ")
        btn_run.setObjectName("PrimaryBtn")
        btn_run.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY_DARK}; color: #ffffff; font-weight: bold; border: none;")
        btn_run.clicked.connect(self.run_scenario)
        toolbar_layout.addWidget(btn_run)
        
        main_layout.addWidget(self.top_toolbar)
        
        # Canvas & Properties dock via Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #1e293b; width: 4px; }")
        
        # Left selected accounts panel (Slide-out drawer)
        self.accounts_panel = AccountsPanel(self)
        splitter.addWidget(self.accounts_panel)
        
        # Canvas workspace (80% width)
        self.scene = NodeCanvasScene(self)
        self.view = NodeCanvasView(self.scene, self)
        self.view.setStyleSheet("border: none; background-color: #0f172a;")
        splitter.addWidget(self.view)
        
        # Right properties dock (Photoshop-like dock, 20% width)
        self.properties_dock = PropertiesDock(self)
        splitter.addWidget(self.properties_dock)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        splitter.setStretchFactor(2, 1)
        
        # Bottom Console Panel (Photoshop/IDE style)
        self.console_widget = ConsolePanel(self)
        self.console_output = self.console_widget.output
        
        # Vertical Splitter
        self.v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.v_splitter.setStyleSheet("QSplitter::handle { background-color: #1e293b; height: 4px; }")
        
        self.v_splitter.addWidget(splitter)
        self.v_splitter.addWidget(self.console_widget)
        self.v_splitter.setStretchFactor(0, 4)
        self.v_splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(self.v_splitter, 1)
        
        # Wire canvas selection change
        self.scene.selectionChanged.connect(self.on_selection_changed)
        
        # Add default Start node at center
        self.create_node("start", QPointF(150, 200))
        self.view.centerOn(150, 200)

    def create_node(self, spec_key, pos, initial_params=None):
        spec = NODE_SPECS.get(spec_key)
        if not spec:
            return None
            
        node = NodeBlockItem(spec["title"], spec_key)
        
        # Add ports
        for name in spec["inputs"]:
            node.add_port(name, False)
        for name in spec["outputs"]:
            node.add_port(name, True)
            
        # Add to scene
        self.scene.addItem(node)
        node.setPos(pos)
        
        # Initialize parameters: default spec params overridden by initial_params
        for p_name, p_info in spec["params"].items():
            node.params[p_name] = p_info["default"]
        if initial_params:
            node.params.update(initial_params)
            
        return node

    def add_node_by_type(self, spec_key):
        # Spawn node at the center of the current visible viewport
        view_rect = self.view.viewport().rect()
        scene_center = self.view.mapToScene(view_rect.center())
        
        # Reroute slightly randomly so nodes don't spawn exactly on top of each other
        import random
        offset_pos = scene_center + QPointF(random.randint(-30, 30), random.randint(-30, 30))
        self.create_node(spec_key, offset_pos)

    def on_selection_changed(self):
        self.properties_dock.update_properties(self.scene)

    def clear_canvas(self):
        for item in list(self.scene.items()):
            if isinstance(item, ConnectionItem):
                item.delete()
            elif isinstance(item, NodeBlockItem):
                self.scene.removeItem(item)
        # Add default start
        self.create_node("start", QPointF(150, 200))
        self.view.centerOn(150, 200)

    def save_scenario(self):
        self.properties_dock.save_current_params()
        
        nodes_data = []
        connections_data = []
        
        nodes = [item for item in self.scene.items() if isinstance(item, NodeBlockItem)]
        for node in nodes:
            nodes_data.append({
                "id": node.id,
                "type": node.node_type,
                "title": node.title,
                "pos_x": node.scenePos().x(),
                "pos_y": node.scenePos().y(),
                "params": node.params,
                "outputs": [port.name for port in node.outputs]
            })
            
            for port in node.outputs:
                for conn in port.connections:
                    if conn.end_port:
                        connections_data.append({
                            "from_node": node.id,
                            "from_port": port.name,
                            "to_node": conn.end_port.parent_node.id,
                            "to_port": conn.end_port.name
                        })
                        
        graph = {
            "nodes": nodes_data,
            "connections": connections_data
        }
        
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить сценарий", os.getcwd(), "ShadowGram Nodes (*.sgn)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(graph, f, indent=4, ensure_ascii=False)
                QMessageBox.information(self, "Успех", "Сценарий сохранен!")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {e}")

    def load_scenario(self):
        path, _ = QFileDialog.getOpenFileName(self, "Открыть сценарий", os.getcwd(), "ShadowGram Nodes (*.sgn)")
        if not path:
            return
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                graph = json.load(f)
                
            self.clear_canvas()
            for item in list(self.scene.items()):
                if isinstance(item, NodeBlockItem):
                    self.scene.removeItem(item)
                    
            node_map = {}
            for n_data in graph.get("nodes", []):
                loaded_params = dict(n_data.get("params", {}))
                node = self.create_node(n_data["type"], QPointF(n_data["pos_x"], n_data["pos_y"]), initial_params=loaded_params)
                if node:
                    node.id = n_data["id"]
                    node.title = n_data["title"]
                    node.params = loaded_params
                    if "outputs" in n_data:
                        # Clear default outputs
                        for out_port in list(node.outputs):
                            node.remove_output_port(out_port.name)
                        # Add loaded outputs
                        for port_name in n_data["outputs"]:
                            node.add_port(port_name, is_output=True)
                    node_map[node.id] = node
                    
            for c_data in graph.get("connections", []):
                from_node = node_map.get(c_data["from_node"])
                to_node = node_map.get(c_data["to_node"])
                if from_node and to_node:
                    out_port = next((p for p in from_node.outputs if p.name == c_data["from_port"]), None)
                    in_port = next((p for p in to_node.inputs if p.name == c_data["to_port"]), None)
                    if out_port and in_port:
                        conn = ConnectionItem(out_port, in_port)
                        self.scene.addItem(conn)
                        
            QMessageBox.information(self, "Успех", "Сценарий успешно загружен!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось прочитать файл: {e}")

    def get_graph_data(self):
        # Чтение структуры графа с холста
        nodes_data = []
        connections_data = []
        
        nodes = [item for item in self.scene.items() if isinstance(item, NodeBlockItem)]
        for node in nodes:
            nodes_data.append({
                "id": node.id,
                "type": node.node_type,
                "title": node.title,
                "params": dict(node.params),
                "outputs": [port.name for port in node.outputs]
            })
            
            for port in node.outputs:
                for conn in port.connections:
                    if conn.end_port:
                        connections_data.append({
                            "from_node": node.id,
                            "from_port": port.name,
                            "to_node": conn.end_port.parent_node.id,
                            "to_port": conn.end_port.name
                        })
                        
        return {
            "nodes": nodes_data,
            "connections": connections_data
        }

    def run_scenario(self):
        self.properties_dock.save_current_params() # Сохраняем последние введенные поля
        
        graph_data = self.get_graph_data()
        
        # Проверка на наличие стартовой ноды
        start_node = next((n for n in graph_data["nodes"] if n["type"] == "start"), None)
        if not start_node:
            QMessageBox.warning(self, "Внимание", "На холсте отсутствует обязательный блок 'Старт'!")
            return
            
        if not self.selected_accounts:
            QMessageBox.warning(self, "Внимание", "Не выбрано ни одного аккаунта для запуска сценария!\nСначала отметьте нужные аккаунты на вкладке 'Аккаунты'.")
            return
            
        # 1. Поиск незаполненных (пустых) строковых полей/ссылок для быстрой подстановки перед стартом
        empty_params = []
        nodes_items = [item for item in self.scene.items() if isinstance(item, NodeBlockItem)]
        for node_item in nodes_items:
            spec = NODE_SPECS.get(node_item.node_type, {})
            for p_name, p_info in spec.get("params", {}).items():
                p_type = p_info.get("type", "str")
                if p_type in ["str", "textarea"]:
                    val = str(node_item.params.get(p_name, "")).strip()
                    if not val:
                        empty_params.append({
                            "node_item": node_item,
                            "param_name": p_name,
                            "param_info": p_info,
                            "current_value": val
                        })

        if empty_params:
            from src.ui.node_editor.dialogs.empty_params_dialog import EmptyParamsFillDialog
            dialog = EmptyParamsFillDialog(empty_params, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return # Пользователь отменил запуск

            # Пересобираем графовые данные после подстановки значений
            graph_data = self.get_graph_data()

        # Проверка отсутствующих необходимых файлов
        missing_files = []
        for n in graph_data["nodes"]:
            spec = NODE_SPECS.get(n["type"])
            if not spec:
                continue
            for p_name, p_info in spec.get("params", {}).items():
                if p_info.get("type") in ["file", "folder"]:
                    val = str(n.get("params", {}).get(p_name, p_info.get("default", ""))).strip()
                    if not val:
                        missing_files.append(f"• Блок '{spec.get('title', n['type'])}': параметр '{p_info.get('label')}' не задан.")
                    elif not os.path.exists(val):
                        missing_files.append(f"• Блок '{spec.get('title', n['type'])}': путь '{os.path.basename(val)}' отсутствует.")
                        
        if missing_files:
            msg = "⚠️ Обнаружены проблемы с локальными файлами:\n\n" + "\n".join(missing_files) + "\n\nВы действительно хотите запустить сценарий?"
            reply = QMessageBox.question(
                self, 
                "Предупреждение о файлах", 
                msg,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
                
        import uuid
        task_id = str(uuid.uuid4())
        
        # Показываем окно активных задач
        self.active_tasks_win.add_task_tab(task_id, f"Node Граф ({len(self.selected_accounts)} акк.)")
        self.active_tasks_win.show()
        
        self.local_tasks[task_id] = { "loop": None, "tasks": [], "instances": [] }
        
        import threading
        threading.Thread(
            target=self.run_node_batch, 
            args=(self.selected_accounts, graph_data, task_id), 
            daemon=True
        ).start()

    def run_node_batch(self, accounts, graph_data, task_id):
        import asyncio
        import random
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.local_tasks[task_id]["loop"] = loop
        
        try:
            from src.core.constants import CONFIG_FILE
            from src.core.managers.config_manager import _read_config
            cfg = _read_config(CONFIG_FILE)
            max_concurrent = cfg.get("settings", {}).get("max_concurrent_tasks", 10)
            
            async def run_all():
                tasks = []
                concurrency_limit = asyncio.Semaphore(max_concurrent)
                
                def log_f(msg, acc_name, tid=task_id):
                    # Безопасное логирование в интерфейс через invokeMethod
                    QMetaObject.invokeMethod(
                        self.active_tasks_win, 
                        "append_log", 
                        Qt.ConnectionType.QueuedConnection, 
                        Q_ARG(str, tid), 
                        Q_ARG(str, f"[{acc_name}] {msg}")
                    )
                    QMetaObject.invokeMethod(
                        self, 
                        "append_console_log", 
                        Qt.ConnectionType.QueuedConnection, 
                        Q_ARG(str, f"[{acc_name}] {msg}")
                    )
                    
                async def wrapped_run(acc_data, initial_delay):
                    try:
                        if initial_delay > 0:
                            log_f(f"⏳ Ожидание шахматного старта: {initial_delay:.2f} сек...", acc_data["name"])
                            await asyncio.sleep(initial_delay)
                            
                        async with concurrency_limit:
                            from src.core.managers.node_executor import NodeScenarioExecutor
                            
                            aid = acc_data.get("api_id", 0)
                            ah = acc_data.get("api_hash", "")
                            
                            log_f("🚀 Запуск сценария на аккаунте...", acc_data["name"])
                            
                            executor = NodeScenarioExecutor(
                                acc_data, 
                                str(aid), 
                                ah, 
                                lambda msg: log_f(msg, acc_data["name"]), 
                                graph_data
                            )
                            self.local_tasks[task_id]["instances"].append(executor)
                            
                            await executor.run()
                    except asyncio.CancelledError:
                        log_f("Сценарий отменен пользователем.", acc_data["name"])
                        raise
                    except Exception as e:
                        log_f(f"Критическая ошибка: {e}", acc_data["name"])
                        
                from src.core.base_module import BaseModule
                min_stagger, max_stagger = getattr(BaseModule, "START_DELAY", (5, 25))
                try:
                    min_stagger, max_stagger = float(min_stagger), float(max_stagger)
                except Exception:
                    min_stagger, max_stagger = 5.0, 25.0

                for idx, acc in enumerate(accounts):
                    acc_task = loop.create_task(wrapped_run(acc, 0.0))
                    self.local_tasks[task_id]["tasks"].append(acc_task)
                    await acc_task
                    
                    # После того как 1-й аккаунт ВСЁ сделал, ставим задержку перед запуском следующего
                    if idx < len(accounts) - 1:
                        delay_after = round(random.uniform(min_stagger, max_stagger), 2)
                        log_f(f"⏳ Аккаунт {acc.get('name', 'профиль')} завершил сценарий. Пауза {delay_after} сек. перед запуском следующего аккаунта...", "system")
                        await asyncio.sleep(delay_after)
                
            main_task = loop.create_task(run_all())
            self.running_tasks[task_id] = (main_task, loop)
            loop.run_until_complete(main_task)
            
            QMetaObject.invokeMethod(
                self.active_tasks_win,
                "append_log",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, task_id),
                Q_ARG(str, "<b>Сессия визуальных сценариев полностью завершена.</b>")
            )
            
        except asyncio.CancelledError:
            pass
        finally:
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
            try:
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.run_until_complete(loop.shutdown_default_executor())
            except Exception:
                pass
            loop.close()

    def stop_running_task(self, task_id):
        import asyncio
        if task_id in self.local_tasks:
            info = self.local_tasks[task_id]
            loop = info["loop"]
            for task in info["tasks"]:
                task.cancel()
            for inst in info["instances"]:
                if loop and loop.is_running():
                    try:
                        asyncio.run_coroutine_threadsafe(inst.cleanup(), loop)
                    except Exception:
                        pass
                    
            if task_id in self.active_tasks_win.tabs:
                self.active_tasks_win.tabs[task_id]["status"].setText("Статус: Остановлен")
                self.active_tasks_win.tabs[task_id]["status"].setStyleSheet("color: #ff5252; font-weight: bold;")
                self.active_tasks_win.tabs[task_id]["btn"].setEnabled(False)

    @pyqtSlot(str)
    def append_console_log(self, text):
        # Определение цвета строки на основе ключевых слов лога
        color = "#94a3b8"
        if "успешно" in text.lower() or "✅" in text:
            color = "#10b981" # Emerald green
        elif "ошибка" in text.lower() or "❌" in text or "критическая" in text.lower():
            color = "#f43f5e" # Rose red
        elif "предупреждение" in text.lower() or "⏳" in text or "ожидание" in text.lower() or "запуск через" in text.lower():
            color = "#f59e0b" # Amber yellow
        elif "шаг" in text.lower() or "блок" in text.lower():
            color = "#38bdf8" # Sky blue
            
        formatted = f"<span style='color: {color};'>{text}</span>"
        self.console_output.append(formatted)
        
        # Скролл вниз
        v_bar = self.console_output.verticalScrollBar()
        v_bar.setValue(v_bar.maximum())

    def toggle_accounts_panel(self):
        if not hasattr(self, "accounts_panel"):
            return
            
        from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
        
        # Check current visibility state based on maximumWidth
        is_expanded = self.accounts_panel.maximumWidth() > 0 and self.accounts_panel.isVisible()
        start_val = 280 if is_expanded else 0
        end_val = 0 if is_expanded else 280
        
        # Stop any running animation
        if hasattr(self, "accounts_anim") and self.accounts_anim is not None:
            self.accounts_anim.stop()
            
        self.accounts_anim = QPropertyAnimation(self.accounts_panel, b"maximumWidth")
        self.accounts_anim.setDuration(220)  # Smooth transition duration
        self.accounts_anim.setStartValue(start_val)
        self.accounts_anim.setEndValue(end_val)
        self.accounts_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        def on_anim_finished():
            if end_val == 0:
                self.accounts_panel.setVisible(False)
            else:
                self.accounts_panel.setFixedWidth(280)
                
        if end_val > 0:
            self.accounts_panel.setVisible(True)
            
        self.accounts_anim.finished.connect(on_anim_finished)
        self.accounts_anim.start()
