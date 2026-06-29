"""
Стили (QSS) для окна модулей автоматизации.
Определяет:

- Темную кибер-зеленую/синюю тему терминала
- Стили для выпадающих списков и кнопок запуска
- Кастомизацию чекбоксов выбора аккаунтов
"""

from src import styles

MODULES_STYLESHEET = ""


def load_theme():
    """Считывает текущие цвета из styles.py и пересобирает MODULES_STYLESHEET"""
    global MODULES_STYLESHEET
    
    # Generate the gradient background dynamically based on the current theme
    GRADIENT_BTN = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {styles.COLOR_PRIMARY}, stop:1 {styles.COLOR_PRIMARY_DARK})"
    GRADIENT_BTN_HOVER = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {styles.COLOR_PRIMARY_LIGHT}, stop:1 {styles.COLOR_PRIMARY})"
    GRADIENT_FRAME = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {styles.COLOR_ACCENT_BG}, stop:1 {styles.COLOR_BG})"

    MODULES_STYLESHEET = f"""
/* Основное окно модулей */
QWidget {{
    background-color: {styles.COLOR_BG};
    color: {styles.COLOR_TEXT_MAIN};
    font-family: '{styles.FONT_NAME}', 'Segoe UI', sans-serif;
}}

/* Стили для секций (рамок) */
QFrame#SectionFrame {{
    background-color: {GRADIENT_FRAME};
    border: 1px solid {styles.COLOR_BORDER};
    border-top: 1px solid {styles.COLOR_BORDER_LIGHT};
    border-radius: 14px;
}}

/* Заголовки */
QLabel#SectionTitle {{
    color: {styles.COLOR_PRIMARY};
    font-weight: bold;
    font-size: 14px;
    text-transform: uppercase;
    margin-bottom: 8px;
    letter-spacing: 2px;
}}

/* Выпадающий список */
QComboBox {{
    background-color: {styles.COLOR_CONSOLE_BG};
    border: 1px solid {styles.COLOR_BORDER};
    border-bottom: 2px solid {styles.COLOR_BORDER};
    border-radius: 8px;
    padding: 10px 14px;
    color: {styles.COLOR_TEXT_MAIN};
    font-weight: bold;
}}

QComboBox:hover {{
    border: 1px solid {styles.COLOR_BORDER_LIGHT};
    border-bottom: 2px solid {styles.COLOR_BORDER_LIGHT};
}}

QComboBox:focus {{
    border: 1px solid {styles.COLOR_PRIMARY};
    border-bottom: 2px solid {styles.COLOR_PRIMARY_LIGHT};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 35px;
    border-left: none;
}}

QComboBox::down-arrow {{
    image: url({styles.CHEVRON_DOWN});
    width: 14px;
    height: 14px;
}}

QComboBox QAbstractItemView {{
    background-color: {styles.COLOR_ACCENT_BG};
    border: 1px solid {styles.COLOR_BORDER};
    border-radius: 8px;
    selection-background-color: rgba(16, 185, 129, 0.15); /* Adjusts via code conceptually */
    selection-color: {styles.COLOR_PRIMARY_LIGHT};
    color: {styles.COLOR_TEXT_MAIN};
    outline: none;
    padding: 6px;
}}

/* Кнопка запуска */
QPushButton#RunModuleBtn {{
    background-color: {GRADIENT_BTN};
    border: 1px solid {styles.COLOR_PRIMARY_DARK};
    border-bottom: 3px solid #047857; /* Darker accent for bottom */
    color: #FFFFFF;
    font-size: 16px;
    font-weight: bold;
    border-radius: 10px;
    padding: 16px;
    text-transform: uppercase;
    letter-spacing: 1px;
}}

QPushButton#RunModuleBtn:hover {{
    background-color: {GRADIENT_BTN_HOVER};
    border: 1px solid {styles.COLOR_PRIMARY_LIGHT};
    border-bottom: 3px solid {styles.COLOR_PRIMARY_DARK};
}}

QPushButton#RunModuleBtn:pressed {{
    background-color: {styles.COLOR_PRIMARY_DARK};
    border: 1px solid #047857;
    border-top: 3px solid #047857;
    border-bottom: 1px solid #047857;
    color: {styles.COLOR_TEXT_MAIN};
    padding-top: 18px;
    padding-bottom: 14px;
}}

/* Терминальный лог */
QTextEdit#LogOutput {{
    background-color: {styles.COLOR_CONSOLE_BG};
    border: 1px solid {styles.COLOR_BORDER};
    border-bottom: 2px solid {styles.COLOR_BORDER_DARK};
    border-radius: 10px;
    color: {styles.COLOR_PRIMARY};
    font-family: '{styles.FONT_NAME}', monospace;
    font-size: 13px;
    padding: 16px;
    line-height: 1.5;
}}

/* Стилизация чекбоксов */
QCheckBox {{
    spacing: 12px;
    padding: 6px;
    color: {styles.COLOR_TEXT_MAIN};
    font-size: 14px;
}}

QCheckBox::indicator {{
    width: 20px;
    height: 20px;
    border: 2px solid {styles.COLOR_BORDER};
    border-bottom: 3px solid {styles.COLOR_BORDER};
    border-radius: 6px;
    background-color: {styles.COLOR_CONSOLE_BG};
}}

QCheckBox::indicator:hover {{
    border-color: {styles.COLOR_BORDER_LIGHT};
    border-bottom-color: {styles.COLOR_BORDER_LIGHT};
    background-color: {styles.COLOR_BG};
}}

QCheckBox::indicator:checked {{
    background-color: {styles.COLOR_PRIMARY_DARK};
    border: 2px solid {styles.COLOR_PRIMARY_DARK};
    border-bottom: 3px solid {styles.COLOR_PRIMARY_DARK};
    image: url({styles.CHEVRON_DOWN});
}}

QCheckBox::indicator:checked:hover {{
    background-color: {styles.COLOR_PRIMARY};
    border-color: {styles.COLOR_PRIMARY};
    border-bottom-color: {styles.COLOR_PRIMARY};
}}

/* Скроллбары (Тонкие) */
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 12px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {styles.COLOR_BORDER};
    border-radius: 6px;
    min-height: 40px;
}}
QScrollBar::handle:vertical:hover {{
    background: {styles.COLOR_BORDER_LIGHT};
}}
QScrollBar::handle:vertical:pressed {{
    background: {styles.COLOR_PRIMARY_DARK};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
"""


# Инициализируем при импорте
load_theme()