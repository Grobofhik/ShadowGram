"""
Стили (QSS) для окна модулей автоматизации.
Определяет:

- Темную кибер-зеленую тему терминала
- Стили для выпадающих списков и кнопок запуска
- Кастомизацию чекбоксов выбора аккаунтов
"""

from src import styles

MODULES_STYLESHEET = ""


def load_theme():
    """Считывает текущие цвета из styles.py и пересобирает MODULES_STYLESHEET"""
    global MODULES_STYLESHEET
    MODULES_STYLESHEET = f"""
/* Основное окно модулей */
QWidget {{
    background-color: {styles.COLOR_BG};
    color: #E0E0E0;
    font-family: '{styles.FONT_NAME}', 'Segoe UI', sans-serif;
}}

/* Стили для секций (рамок) */
QFrame#SectionFrame {{
    background-color: {styles.COLOR_ACCENT_BG};
    border: 1px solid {styles.COLOR_BORDER};
    border-radius: 12px;
}}

/* Заголовки */
QLabel#SectionTitle {{
    color: {styles.COLOR_PRIMARY};
    font-weight: bold;
    font-size: 13px;
    text-transform: uppercase;
    margin-bottom: 5px;
    letter-spacing: 1px;
}}

/* Выпадающий список */
QComboBox {{
    background-color: {styles.COLOR_CONSOLE_BG};
    border: 1px solid {styles.COLOR_BORDER};
    border-radius: 6px;
    padding: 8px 12px;
    color: {styles.COLOR_PRIMARY};
    font-weight: normal;
}}

QComboBox:hover {{
    border: 1px solid {styles.COLOR_PRIMARY};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 30px;
    border-left-width: 1px;
    border-left-color: {styles.COLOR_BORDER};
    border-left-style: solid;
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}}

QComboBox::down-arrow {{
    image: url({styles.CHEVRON_DOWN});
    width: 16px;
    height: 16px;
}}

QComboBox QAbstractItemView {{
    background-color: {styles.COLOR_CONSOLE_BG};
    border: 1px solid {styles.COLOR_BORDER};
    selection-background-color: {styles.COLOR_SELECT_BG};
    selection-color: {styles.COLOR_PRIMARY};
    color: #E0E0E0;
    outline: none;
}}

/* Кнопка запуска */
QPushButton#RunModuleBtn {{
    background-color: {styles.COLOR_PRIMARY_DARK};
    border: none;
    color: {"#000000" if styles.COLOR_PRIMARY == "#00E676" else "#FFFFFF"};
    font-size: 15px;
    font-weight: bold;
    border-radius: 8px;
    padding: 15px;
}}

QPushButton#RunModuleBtn:hover {{
    background-color: {styles.COLOR_PRIMARY};
}}

QPushButton#RunModuleBtn:pressed {{
    background-color: {styles.COLOR_PRIMARY_DARK};
}}

/* Терминальный лог */
QTextEdit#LogOutput {{
    background-color: {styles.COLOR_CONSOLE_BG};
    border: 1px solid {styles.COLOR_BORDER};
    border-radius: 8px;
    color: {styles.COLOR_PRIMARY};
    font-family: '{styles.FONT_NAME}', monospace;
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
    border: 2px solid {styles.COLOR_BORDER};
    border-radius: 5px;
    background-color: {styles.COLOR_CONSOLE_BG};
}}

QCheckBox::indicator:hover {{
    border-color: {styles.COLOR_PRIMARY};
}}

QCheckBox::indicator:checked {{
    background-color: {styles.COLOR_PRIMARY_DARK};
    border: 1px solid {styles.COLOR_PRIMARY_DARK};
    image: url({styles.CHEVRON_DOWN});
}}

/* Скроллбары (Тонкие) */
QScrollBar:vertical {{
    border: none;
    background: {styles.COLOR_BG};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {styles.COLOR_SCROLL_HANDLE};
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: {styles.COLOR_PRIMARY};
}}
"""


# Инициализируем при импорте
load_theme()