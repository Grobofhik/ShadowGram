from src.core.constants import *
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
                             QPushButton, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QCursor, QPixmap
import os
from src import styles
from src.core.constants import (
    TOOGLE_ICON_PATH, PHONE_ICON_PATH, KEY_ICON_PATH, 
    PEAPLE_ICON_PATH, REFRESH_ICON_PATH, REBOOT_ICON_PATH, 
    ROBOT_ICON_PATH, CALL_ICON_PATH
)

_ICON_CACHE = {}

class ServiceCard(QFrame):
    def __init__(self, title, description, icon, callback, parent=None):
        super().__init__(parent)
        self.callback = callback
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # Base styling for the card
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {styles.COLOR_CONSOLE_BG};
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 10px;
            }}
            QFrame:hover {{
                background-color: {styles.COLOR_HOVER_BG};
                border: 1px solid {styles.COLOR_PRIMARY};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        lbl_icon = QLabel()
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        if os.path.exists(icon):
            if icon not in _ICON_CACHE:
                _ICON_CACHE[icon] = QPixmap(icon).scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            lbl_icon.setPixmap(_ICON_CACHE[icon])
            lbl_icon.setStyleSheet("border: none; background: transparent;")
        else:
            lbl_icon.setText(icon)
            lbl_icon.setStyleSheet("font-size: 32px; border: none; background: transparent;")
            
        layout.addWidget(lbl_icon)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {styles.COLOR_PRIMARY}; border: none; background: transparent;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)
        
        lbl_desc = QLabel(description)
        lbl_desc.setStyleSheet(f"font-size: 13px; color: {styles.COLOR_TEXT_MUTED}; border: none; background: transparent;")
        lbl_desc.setWordWrap(True)
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_desc)
        
        self.setMinimumSize(250, 180)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.callback()

class ServicesPage(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header_layout = QHBoxLayout()
        header_icon = QLabel()
        icon_path = str(TOOGLE_ICON_PATH)
        
        if os.path.exists(icon_path):
            if icon_path not in _ICON_CACHE:
                _ICON_CACHE[icon_path] = QPixmap(icon_path).scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            header_icon.setPixmap(_ICON_CACHE[icon_path])
        else:
            header_icon.setText("🛠")
            header_icon.setStyleSheet("font-size: 24px;")
            
        header_title = QLabel("Дополнительные сервисы")
        header_title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {styles.COLOR_PRIMARY};")
        
        header_layout.addWidget(header_icon)
        header_layout.addWidget(header_title)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        subtitle = QLabel("Полезные утилиты для массовой работы с аккаунтами и генерации данных.")
        subtitle.setStyleSheet(f"font-size: 14px; color: {styles.COLOR_TEXT_MUTED};")
        layout.addWidget(subtitle)
        
        layout.addSpacing(20)
        
        # Grid area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        
        grid = QGridLayout(container)
        grid.setSpacing(25)
        grid.setContentsMargins(0, 0, 0, 0)
        
        # Define services
        services = [
            {
                "title": "Авторизация сессий",
                "desc": "Массовый вход в аккаунты по номеру телефона (через код) для создания файлов сессий (.session).",
                "icon": str(PHONE_ICON_PATH),
                "callback": self.main_window.open_session_manager
            },
            {
                "title": "Генератор API ID",
                "desc": "Автоматически регистрирует приложения на my.telegram.org и получает уникальные api_id / api_hash.",
                "icon": str(KEY_ICON_PATH),
                "callback": self.main_window.open_api_generator
            },
            {
                "title": "Масс-реггер профилей",
                "desc": "Пакетное создание профилей фермы (папки, конфиги, генерация данных) в 1 клик.",
                "icon": str(PEAPLE_ICON_PATH),
                "callback": self.main_window.open_mass_profile_creator
            },
            {
                "title": "Конвертер TData",
                "desc": "Конвертирует сессии формата TData (Telegram Desktop) в формат сессий для скриптов.",
                "icon": str(REFRESH_ICON_PATH),
                "callback": self.main_window.open_tdata_converter
            },
            {
                "title": "Конвертер Telethon",
                "desc": "Конвертирует сессии формата Telethon в формат Hydrogram (Pyrogram) для работы с фермой.",
                "icon": str(REBOOT_ICON_PATH),
                "callback": self.main_window.open_telethon_converter
            },
            {
                "title": "Имена устройств",
                "desc": "Рандомизирует названия устройств (Device Model) для сессий, чтобы они выглядели как разные телефоны.",
                "icon": str(PHONE_ICON_PATH),
                "callback": self.main_window.open_device_generator
            },
            {
                "title": "Генератор Промптов",
                "desc": "Умный конструктор запросов для ИИ-модулей.",
                "icon": str(ROBOT_ICON_PATH),
                "callback": self.main_window.open_prompt_generator
            },
            {
                "title": "Экспорт номеров",
                "desc": "Экспортирует номера телефонов всех аккаунтов фермы в отдельный текстовый файл.",
                "icon": str(CALL_ICON_PATH),
                "callback": self.main_window.export_phone_numbers
            }
        ]
        
        # Add to grid (e.g. 3 columns)
        row = 0
        col = 0
        for srv in services:
            card = ServiceCard(srv["title"], srv["desc"], srv["icon"], srv["callback"])
            grid.addWidget(card, row, col)
            col += 1
            if col > 2:
                col = 0
                row += 1
                
        # Fill remaining space
        grid.setRowStretch(row + 1, 1)
        
        scroll.setWidget(container)
        
        layout.addWidget(scroll)
