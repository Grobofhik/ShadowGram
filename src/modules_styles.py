"""
Стили (QSS) для окна модулей автоматизации.
Определяет:

- Темную кибер-зеленую тему терминала
- Стили для выпадающих списков и кнопок запуска
- Кастомизацию чекбоксов выбора аккаунтов
"""

from src.styles import FONT_NAME, CHEVRON_DOWN

MODULES_STYLESHEET = f"""
/* Основное окно модулей */
QWidget {{
    background-color: #080C08;
    color: #E0E0E0;
    font-family: '{FONT_NAME}', 'Segoe UI', sans-serif;
}}

/* Стили для секций (рамок) */
QFrame#SectionFrame {{
    background-color: #0D140D;
    border: 1px solid #1A2E1A;
    border-radius: 12px;
}}

/* Заголовки */
QLabel#SectionTitle {{
    color: #00E676;
    font-weight: bold;
    font-size: 13px;
    text-transform: uppercase;
    margin-bottom: 5px;
    letter-spacing: 1px;
}}

/* Выпадающий список */
QComboBox {{
    background-color: #040604;
    border: 1px solid #1A2E1A;
    border-radius: 6px;
    padding: 8px 12px;
    color: #00E676;
    font-weight: normal;
}}

QComboBox:hover {{
    border: 1px solid #00E676;
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 30px;
    border-left-width: 1px;
    border-left-color: #1A2E1A;
    border-left-style: solid;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}}

QComboBox::down-arrow {{
    image: url({CHEVRON_DOWN});
    width: 16px;
    height: 16px;
}}

QComboBox QAbstractItemView {{
    background-color: #040604;
    border: 1px solid #1A2E1A;
    selection-background-color: #1A2B1A;
    selection-color: #00E676;
    color: #E0E0E0;
    outline: none;
}}

/* Кнопка запуска */
QPushButton#RunModuleBtn {{
    background-color: #00C853;
    border: none;
    color: #000000;
    font-size: 15px;
    font-weight: bold;
    border-radius: 8px;
    padding: 15px;
}}

QPushButton#RunModuleBtn:hover {{
    background-color: #00E676;
}}

QPushButton#RunModuleBtn:pressed {{
    background-color: #00B248;
}}

/* Терминальный лог */
QTextEdit#LogOutput {{
    background-color: #040604;
    border: 1px solid #1A2E1A;
    border-radius: 8px;
    color: #00E676;
    font-family: '{FONT_NAME}', monospace;
    font-size: 12px;
    padding: 12px;
}}

/* Стилизация чекбоксов */
QCheckBox {{
    spacing: 10px;
    padding: 5px;
    color: #E0E0E0;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid #1A2E1A;
    border-radius: 5px;
    background-color: #040604;
}}

QCheckBox::indicator:hover {{
    border-color: #00E676;
}}

QCheckBox::indicator:checked {{
    background-color: #00C853;
    border: 1px solid #00C853;
    image: url({CHEVRON_DOWN});
}}

/* Скроллбары (Тонкие) */
QScrollBar:vertical {{
    border: none;
    background: #080C08;
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: #1A2E1A;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: #00E676;
}}
"""