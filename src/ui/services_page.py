from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
                             QPushButton, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QCursor
from src import styles

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
        
        lbl_icon = QLabel(icon)
        lbl_icon.setStyleSheet("font-size: 32px; border: none; background: transparent;")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
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
        header = QLabel("🛠 Дополнительные сервисы")
        header.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {styles.COLOR_PRIMARY};")
        layout.addWidget(header)
        
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
                "title": "Генератор API ID",
                "desc": "Раздает официальные API ID от Android, iOS и Desktop аккаунтам, чтобы избежать банов.",
                "icon": "🔑",
                "callback": self.main_window.open_api_generator
            },
            {
                "title": "Масс-регер профилей",
                "desc": "Быстро создает множество пустых профилей в базе для последующей заливки сессий.",
                "icon": "👥",
                "callback": self.main_window.open_mass_profile_creator
            },
            {
                "title": "Конвертер TData",
                "desc": "Переводит папки tdata от Telegram Desktop в формат .session для работы фермы.",
                "icon": "🔄",
                "callback": self.main_window.open_tdata_converter
            },
            {
                "title": "Имена устройств",
                "desc": "Рандомизирует названия устройств (Device Model) для сессий, чтобы они выглядели как разные телефоны.",
                "icon": "📱",
                "callback": self.main_window.open_device_generator
            },
            {
                "title": "Генератор Промптов",
                "desc": "Умный конструктор запросов для ИИ-модулей.",
                "icon": "🤖",
                "callback": self.main_window.open_prompt_generator
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
