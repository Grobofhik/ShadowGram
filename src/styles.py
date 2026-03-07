"""
Глобальные стили (QSS) основного интерфейса ShadowGram.
Определяет:

- Цветовую палитру и шрифты
- Стили для кнопок, полей ввода и карточек аккаунтов
- Кастомизацию скроллбаров и чекбоксов
"""

# Настройки шрифта
FONT_NAME = "Monocraft"
TITLE_FONT_NAME = "alagard-12px-unicode"

# Refined Shadowgram Stylesheet
STYLESHEET = f"""
QWidget {{
    background-color: #1a1f1a;
    color: #e0e0e0;
    font-family: '{FONT_NAME}', sans-serif;
}}

QToolTip {{
    background-color: #242b24;
    color: #00e676;
    border: 1px solid #4caf50;
    border-radius: 4px;
    padding: 6px;
    font-size: 11px;
    font-family: '{FONT_NAME}';
}}

/* Основная область списка */
QScrollArea {{
    border: none;
    background-color: #1a1f1a;
}}

QWidget#ScrollContent {{
    background-color: #1a1f1a;
}}

/* Карточка аккаунта */
QFrame#AccountRow {{
    background-color: #1e241e;
    border: 1px solid #2d382d;
    border-radius: 12px;
    margin: 2px;
}}

QFrame#AccountRow:hover {{
    border: 1px solid #4caf50;
    background-color: #262e26;
}}

/* Общий стиль кнопок */
QPushButton {{
    background-color: #2e7d32;
    color: #ffffff;
    border: 1px solid #1b5e20;
    padding: 8px 12px;
    border-radius: 6px;
    font-weight: bold;
}}

QPushButton:hover {{
    background-color: #388e3c;
    border: 1px solid #4caf50;
}}

QPushButton:pressed {{
    background-color: #1b5e20;
    padding-top: 10px;
    padding-bottom: 6px;
}}

/* Специфические кнопки-иконки */
QPushButton#ExplorerBtn {{ background-color: #0277bd; border-color: #01579b; }}
QPushButton#ExplorerBtn:hover {{ background-color: #0288d1; }}

QPushButton#EditBtn, QPushButton#NotesBtn, QPushButton#CheckBtn {{ 
    background-color: #37474f; 
    border-color: #263238; 
}}
QPushButton#EditBtn:hover, QPushButton#NotesBtn:hover, QPushButton#CheckBtn:hover {{ 
    background-color: #455a64; 
}}

QPushButton#DeviceBtn {{ 
    background-color: #1565c0; 
    border-color: #0d47a1; 
}}
QPushButton#DeviceBtn:hover {{ 
    background-color: #1976d2; 
}}

QPushButton#DeleteBtn {{ 
    background-color: #b71c1c; 
    border-color: #7f0000; 
}}
QPushButton#DeleteBtn:hover {{ 
    background-color: #c62828; 
}}

/* Состояния кнопки проверки прокси и сессии */
QPushButton#CheckBtn[status="success"], QPushButton#SessionBtn[status="alive"] {{ 
    background-color: #2e7d32; 
    border-color: #00e676;
}}
QPushButton#CheckBtn[status="error"], QPushButton#SessionBtn[status="banned"] {{ 
    background-color: #c62828; 
    border-color: #ff5252;
}}
QPushButton#CheckBtn[status="checking"] {{ 
    background-color: #fbc02d; 
    border-color: #f9a825;
}}

QPushButton#SessionBtn {{ 
    background-color: #4527a0; 
    border-color: #311b92; 
}}
QPushButton#SessionBtn:hover {{ 
    background-color: #512da8; 
}}

/* Кнопки перемещения */
QPushButton#MoveBtn {{
    background-color: #1a1f1a;
    border: 1px solid #2d382d;
    color: #888;
    font-size: 10px;
    padding: 0px;
}}
QPushButton#MoveBtn:hover {{
    color: #4caf50;
    border-color: #4caf50;
}}

/* Поля ввода */
QLineEdit {{
    background-color: #0d110d;
    border: 1px solid #2d382d;
    border-radius: 8px;
    padding: 10px;
    color: #ffffff;
    selection-background-color: #2e7d32;
}}

QLineEdit:focus {{
    border: 1px solid #4caf50;
    background-color: #121612;
}}

/* Заголовки и текст */
QLabel#Title {{
    color: #4caf50;
    font-size: 32px;
    font-weight: normal;
    font-family: '{TITLE_FONT_NAME}';
    letter-spacing: 2px;
}}

/* Аватарка (без фона) */
QLabel#AvatarLabel {{
    background-color: transparent;
    border: 2px solid #2d382d;
    border-radius: 25px;
}}

QLabel#AvatarLabel:hover {{
    border: 2px solid #4caf50;
}}

QLabel#NotePopup {{
    background-color: #2e3b2e;
    color: #e0e0e0;
    border: 1px solid #4caf50;
    border-radius: 5px;
    padding: 10px;
    font-size: 12px;
    font-family: '{FONT_NAME}';
}}

QLabel#StatusRunning {{ 
    color: #00e676; 
    font-weight: bold;
    background-color: #1b331b;
    padding: 2px 8px;
    border-radius: 4px;
}}

QLabel#StatusStopped {{ 
    color: #757575; 
    background-color: #1e241e;
    padding: 2px 8px;
    border-radius: 4px;
}}

/* Секция создания */
QFrame#CreateSection {{
    background-color: #1e241e;
    border-top: 2px solid #2d382d;
    border-bottom-left-radius: 15px;
    border-bottom-right-radius: 15px;
    padding: 15px;
}}

/* Скроллбары */
QScrollBar:vertical {{
    border: none;
    background: #1a1f1a;
    width: 10px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: #2d382d;
    min-height: 30px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{
    background: #4caf50;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    border: none;
    background: #1a1f1a;
    height: 10px;
    margin: 0px;
}}
QScrollBar::handle:horizontal {{
    background: #2d382d;
    min-width: 30px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #4caf50;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Чекбоксы */
QCheckBox::indicator {{
    width: 20px;
    height: 20px;
    border: 2px solid #2d382d;
    border-radius: 6px;
    background-color: #0d110d;
}}
QCheckBox::indicator:checked {{
    background-color: #2e7d32;
    border-color: #4caf50;
}}
"""