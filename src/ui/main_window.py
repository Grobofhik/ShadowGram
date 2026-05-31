import os
import subprocess
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QFrame, QLabel, QPushButton, QMenu
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import QTimer, QEvent, Qt, QSize

"""
Главный контроллер интерфейса приложения.
Функции:

- init_ui: настройка главного окна и стека страниц
- init_audio: инициализация системы воспроизведения звука
- show_settings: переключение на страницу настроек
- show_list: переключение на страницу списка аккаунтов
- show_modules: открытие окна модулей управления
- show_server: открытие окна управления сервером
- sync_status: периодическая синхронизация статусов всех аккаунтов
- eventFilter: перехват событий (в частности, кликов по логотипу для воспроизведения звука)
"""

from src.ui.list_page import AccountListPage
from src.ui.settings_page import SettingsPage
from src.core.constants import (
    SOUND_PATH, LOGO_PATH, FOLDER_ICON_PATH,
    SERVER_ICON_PATH, MODULS_ICON_PATH, 
    NOTE_ICON_PATH, SETTINGS_ICON_PATH
)

class TelegramManager(QWidget):
    def __init__(self):
        super().__init__()
        self.modules_win = None
        self.server_win = None
        self.init_ui()
        self.init_audio()
        self.timer = QTimer()
        self.timer.timeout.connect(self.sync_status)
        self.timer.start(1000)

    def init_ui(self):
        self.setWindowTitle("Shadowgram")
        self.resize(1000, 750)
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Боковая панель навигации (Sidebar)
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(270)
        self.sidebar.setStyleSheet("QFrame#Sidebar { background-color: #0D140D; border-right: 1px solid #1A2E1A; }")
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(15, 20, 15, 20)
        sidebar_layout.setSpacing(10)

        # Логотип и заголовок
        logo_layout = QHBoxLayout()
        logo_label = QLabel()
        logo_pix = QPixmap(str(LOGO_PATH))
        if not logo_pix.isNull():
            logo_label.setPixmap(logo_pix.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        logo_label.setStyleSheet("background-color: transparent;")
        logo_label.installEventFilter(self)
        logo_layout.addWidget(logo_label)

        title_label = QLabel("Shadowgram")
        title_label.setObjectName("Title")
        title_label.setStyleSheet("font-size: 24px; background-color: transparent;")
        logo_layout.addWidget(title_label)
        sidebar_layout.addLayout(logo_layout)
        
        sidebar_layout.addSpacing(10)

        # Навигационные кнопки
        self.btn_main = self.create_nav_button(" Главная", FOLDER_ICON_PATH)
        self.btn_main.clicked.connect(self.show_list)
        sidebar_layout.addWidget(self.btn_main)

        self.btn_create_profile = self.create_nav_button(" Создать профиль", FOLDER_ICON_PATH) # Можно заменить иконку
        self.btn_create_profile.clicked.connect(self.open_create_profile)
        sidebar_layout.addWidget(self.btn_create_profile)

        self.btn_server = self.create_nav_button(" Сервер", SERVER_ICON_PATH)
        self.btn_server.clicked.connect(self.show_server)
        sidebar_layout.addWidget(self.btn_server)

        self.btn_modules = self.create_nav_button(" Модули", MODULS_ICON_PATH)
        self.btn_modules.clicked.connect(self.show_modules)
        sidebar_layout.addWidget(self.btn_modules)

        # Меню доп сервисов
        self.btn_services = self.create_nav_button(" Доп сервисы", MODULS_ICON_PATH)
        services_menu = QMenu(self)
        services_menu.setStyleSheet("QMenu { background-color: #040604; color: #00E676; border: 1px solid #1A2E1A; } QMenu::item { padding: 8px 20px; } QMenu::item:selected { background-color: #1A2B1A; }")
        
        action_device_gen = services_menu.addAction("Генератор имён устройств")
        action_device_gen.triggered.connect(self.open_device_generator)

        action_prompt_gen = services_menu.addAction("Генератор AI Промптов")
        action_prompt_gen.triggered.connect(self.open_prompt_generator)
        
        self.btn_services.setMenu(services_menu)
        sidebar_layout.addWidget(self.btn_services)

        sidebar_layout.addStretch()

        # Кнопки внизу (Документация и Настройки)
        self.btn_docs = self.create_nav_button(" Документация", NOTE_ICON_PATH)
        self.btn_docs.clicked.connect(self.show_docs)
        sidebar_layout.addWidget(self.btn_docs)

        self.btn_settings = self.create_nav_button(" Настройки", SETTINGS_ICON_PATH)
        self.btn_settings.clicked.connect(self.show_settings)
        sidebar_layout.addWidget(self.btn_settings)

        main_layout.addWidget(self.sidebar)

        # Стек с основным контентом
        self.stack = QStackedWidget(self)
        
        self.acc_list_page = AccountListPage(self)
        self.settings_page = SettingsPage()

        self.settings_page.back_requested.connect(self.show_list)
        self.settings_page.settings_saved.connect(self.reload_all_windows)

        self.stack.addWidget(self.acc_list_page)
        self.stack.addWidget(self.settings_page)

        main_layout.addWidget(self.stack, 1) # 1 - растягивать контент

        self.acc_list_page.refresh_accounts()

    def create_nav_button(self, text, icon_path):
        btn = QPushButton(text)
        btn.setIcon(QIcon(str(icon_path)))
        btn.setIconSize(QSize(20, 20))
        btn.setFixedHeight(45)
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                text-align: left;
                padding-left: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #111A11;
                border: 1px solid #1A2E1A;
            }
            QPushButton::menu-indicator {
                image: none;
            }
        """)
        return btn

    def init_audio(self):
        self.sound_path = str(SOUND_PATH)

    def show_settings(self):
        self.settings_page.load_settings()
        self.stack.setCurrentWidget(self.settings_page)

    def show_list(self):
        self.stack.setCurrentWidget(self.acc_list_page)

    def reload_all_windows(self):
        self.acc_list_page.refresh_accounts()
        if self.modules_win is not None:
            self.modules_win.close()
            self.modules_win = None
        if self.server_win is not None:
            self.server_win.close()
            self.server_win = None

    def show_docs(self):
        self.settings_page.show_docs()

    def show_modules(self):
        if self.modules_win is None:
            from src.ui.modules_window import ModulesWindow
            self.modules_win = ModulesWindow()
        self.modules_win.show()
        self.modules_win.raise_()
        self.modules_win.activateWindow()

    def show_server(self):
        if self.server_win is None:
            from src.ui.server_window import ServerWindow
            self.server_win = ServerWindow()
        self.server_win.show()
        self.server_win.raise_()
        self.server_win.activateWindow()

    def open_create_profile(self):
        self.acc_list_page.open_create_profile_dialog()

    def open_device_generator(self):
        self.acc_list_page.open_device_generator()

    def open_prompt_generator(self):
        self.acc_list_page.open_prompt_generator()

    def sync_status(self):
        for r in self.acc_list_page.rows:
            if r.tg_process is not None:
                r.check_status()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            for cmd in ["mpv", "ffplay", "pw-play", "paplay"]:
                try:
                    args = [cmd, "--no-video", "--volume=100", self.sound_path] if cmd == "mpv" else [cmd, "-nodisp", "-autoexit", self.sound_path] if cmd == "ffplay" else [cmd, self.sound_path]
                    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True
                except:
                    continue
            return True
        return super().eventFilter(obj, event)