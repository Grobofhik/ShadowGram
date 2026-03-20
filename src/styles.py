"""
Глобальные стили (QSS) основного интерфейса ShadowGram.
Определяет:

- Цветовую палитру и шрифты (Зеленый Кибер-стиль)
- Стили для кнопок, полей ввода и карточек аккаунтов
- Кастомизацию скроллбаров и чекбоксов
"""

# Настройки шрифта
FONT_NAME = "Monocraft"
TITLE_FONT_NAME = "alagard-12px-unicode"

# Иконки для дерева документации (Base64 SVG)
CHEVRON_RIGHT = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMiIgaGVpZ2h0PSIxMiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiMwMGU2NzYiIHN0cm9rZS13aWR0aD0iMyIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cG9seWxpbmUgcG9pbnRzPSI5IDE4IDE1IDEyIDkgNiI+PC9wb2x5bGluZT48L3N2Zz4="
CHEVRON_DOWN = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMiIgaGVpZ2h0PSIxMiIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiMwMGU2NzYiIHN0cm9rZS13aWR0aD0iMyIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cG9seWxpbmUgcG9pbnRzPSI2IDkgMTIgMTUgMTggOSI+PC9wb2x5bGluZT48L3N2Zz4="

# Refined Shadowgram Stylesheet - Cyber Green
STYLESHEET = f"""
QWidget {{
    background-color: #080C08; /* Очень темный зеленый/черный фон */
    color: #E0E0E0;
    font-size: 13px;
    font-family: '{FONT_NAME}', 'Segoe UI', sans-serif;
}}

QToolTip {{
    background-color: #0D140D;
    color: #00E676;
    border: 1px solid #1B5E20;
    border-radius: 6px;
    padding: 6px;
    font-size: 11px;
    font-family: '{FONT_NAME}';
}}

/* Основная область списка */
QScrollArea {{
    border: none;
    background-color: #080C08;
}}

QWidget#ScrollContent {{
    background-color: #080C08;
}}

/* Карточка аккаунта */
QFrame#AccountRow {{
    background-color: #0D140D;
    border: 1px solid #1A2E1A;
    border-radius: 12px;
    margin: 4px 0px;
}}

QFrame#AccountRow:hover {{
    border: 1px solid #00E676;
    background-color: #121C12;
    /* Легкое зеленое свечение */
}}

/* Общий стиль кнопок */
QPushButton {{
    background-color: #111A11;
    color: #00E676;
    border: 1px solid #244024;
    padding: 8px 16px;
    border-radius: 8px;
    font-weight: normal;
}}

QPushButton:hover {{
    background-color: #1A2B1A;
    border-color: #00E676;
    color: #FFFFFF;
}}

QPushButton:pressed {{
    background-color: #0A120A;
    border-color: #00C853;
}}

QPushButton:disabled {{
    background-color: #080C08;
    color: #4A5C4A;
    border: 1px solid #142114;
}}

/* Главная кнопка Запустить/Закрыть */
QPushButton#LaunchBtn {{
    background-color: #00C853;
    color: #000000;
    border: none;
    border-radius: 8px;
    font-weight: normal;
}}

QPushButton#LaunchBtn:hover {{
    background-color: #00E676;
}}

/* Специфические кнопки-иконки */
QPushButton#ExplorerBtn {{ background-color: #0D2136; border-color: #153E6B; color: #58A6FF; }}
QPushButton#ExplorerBtn:hover {{ background-color: #153E6B; border-color: #58A6FF; color: #FFFFFF; }}

QPushButton#EditBtn, QPushButton#NotesBtn, QPushButton#CheckBtn {{ 
    background-color: #111A11; 
    border: 1px solid #244024;
}}
QPushButton#EditBtn:hover, QPushButton#NotesBtn:hover, QPushButton#CheckBtn:hover {{ 
    background-color: #1A2B1A; 
    border-color: #00E676;
}}

QPushButton#DeviceBtn {{ 
    background-color: #1A1A2E; 
    border: 1px solid #2D2D5E;
}}
QPushButton#DeviceBtn:hover {{ 
    background-color: #2D2D5E; 
    border-color: #8250DF;
}}

QPushButton#DeleteBtn {{ 
    background-color: #2E1111; 
    border: 1px solid #5E2424;
}}
QPushButton#DeleteBtn:hover {{ 
    background-color: #5E2424; 
    border-color: #FF5252;
}}

/* Состояния кнопки проверки прокси и сессии */
QPushButton#CheckBtn[status="success"], QPushButton#SessionBtn[status="alive"] {{ 
    background-color: rgba(0, 230, 118, 0.1); 
    border-color: #00E676;
}}
QPushButton#CheckBtn[status="error"], QPushButton#SessionBtn[status="banned"] {{ 
    background-color: rgba(255, 82, 82, 0.1); 
    border-color: #FF5252;
}}
QPushButton#CheckBtn[status="checking"] {{ 
    background-color: rgba(255, 193, 7, 0.1); 
    border-color: #FFC107;
}}

QPushButton#SessionBtn {{ 
    background-color: #1A1423; 
    border: 1px solid #3B2D4A; 
}}
QPushButton#SessionBtn:hover {{ 
    background-color: #3B2D4A; 
    border-color: #B388FF;
}}

/* Кнопки перемещения */
QPushButton#MoveBtn {{
    background-color: transparent;
    border: none;
    color: #4A5C4A;
    font-size: 10px;
    padding: 2px;
}}
QPushButton#MoveBtn:hover {{
    color: #00E676;
}}

/* Вкладки (Настройки) */
QTabWidget::pane {{
    border: 1px solid #1A2E1A;
    background-color: #0D140D;
    border-radius: 8px;
    top: -1px;
}}

QTabBar::tab {{
    background-color: #080C08;
    color: #8B9A8B;
    padding: 8px 18px;
    border: 1px solid transparent;
    border-bottom: 2px solid #1A2E1A;
    font-weight: normal;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
}}

QTabBar::tab:hover {{
    background-color: #111A11;
    color: #E0E0E0;
}}

QTabBar::tab:selected {{
    color: #00E676;
    background-color: #0D140D;
    border: 1px solid #1A2E1A;
    border-bottom: 2px solid #00E676;
}}

/* Поля ввода и текстовые области */
QLineEdit, QSpinBox, QTextEdit {{
    background-color: #040604;
    border: 1px solid #1A2E1A;
    border-radius: 6px;
    padding: 8px;
    color: #00E676;
    selection-background-color: #1B5E20;
}}

QLineEdit:focus, QSpinBox:focus, QTextEdit:focus {{
    border: 1px solid #00E676;
    background-color: #0A100A;
}}

QSpinBox::up-button, QSpinBox::down-button {{
    width: 0px;
}}

/* Заголовки и текст */
QLabel#Title {{
    color: #00E676;
    font-size: 26px;
    font-weight: normal;
    font-family: '{TITLE_FONT_NAME}';
    letter-spacing: 2px;
    text-shadow: 0px 0px 10px rgba(0, 230, 118, 0.5);
}}

QLabel#SettingLabel {{
    color: #8B9A8B;
    font-weight: normal;
    margin-top: 10px;
    font-size: 13px;
}}

/* Аватарка (без фона) */
QLabel#AvatarLabel {{
    background-color: transparent;
    border: 2px solid #1A2E1A;
    border-radius: 25px;
}}

QLabel#AvatarLabel:hover {{
    border: 2px solid #00E676;
}}

QLabel#NotePopup {{
    background-color: #0D140D;
    color: #E0E0E0;
    border: 1px solid #00E676;
    border-radius: 8px;
    padding: 12px;
    font-size: 12px;
    font-family: '{FONT_NAME}';
}}

QLabel#StatusRunning {{ 
    color: #000000; 
    font-weight: normal;
    font-size: 11px;
    background-color: #00E676;
    padding: 4px 10px;
    border-radius: 6px;
}}

QLabel#StatusStopped {{ 
    color: #8B9A8B; 
    font-size: 11px;
    font-weight: normal;
    background-color: #111A11;
    padding: 4px 10px;
    border-radius: 6px;
    border: 1px solid #244024;
}}

/* Секция создания */
QFrame#CreateSection {{
    background-color: #0D140D;
    border: 1px solid #1A2E1A;
    border-radius: 12px;
    padding: 20px;
    margin-top: 10px;
}}

/* Скроллбары */
QScrollBar:vertical {{
    border: none;
    background: #080C08;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: #1A2E1A;
    min-height: 30px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: #00E676;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    border: none;
    background: #080C08;
    height: 8px;
    margin: 0px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: #1A2E1A;
    min-width: 30px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal:hover {{
    background: #00E676;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

/* Чекбоксы */
QCheckBox {{
    spacing: 8px;
    color: #E0E0E0;
    font-weight: normal;
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
    border-color: #00C853;
    image: url({CHEVRON_DOWN});
}}

/* Прогрессбар */
QProgressBar {{
    border: 1px solid #1A2E1A;
    border-radius: 6px;
    background-color: #040604;
    text-align: center;
    color: white;
    font-weight: normal;
}}

QProgressBar::chunk {{
    background-color: #00E676;
    border-radius: 5px;
}}
"""

# Специальные стили для окна документации
DOCS_STYLESHEET = f"""
QWidget#DocsWindow {{
    background-color: #080C08;
    color: #E0E0E0;
}}

QFrame#DocsSidebar {{
    background-color: #0D140D;
    border-right: 1px solid #1A2E1A;
}}

QLabel#DocsSidebarTitle {{
    color: #00E676;
    font-weight: normal;
    font-size: 15px;
    letter-spacing: 1px;
    padding-bottom: 10px;
    border-bottom: 1px solid #1A2E1A;
}}

QTreeWidget#DocsTree {{
    background-color: transparent;
    border: none;
    outline: none;
    color: #E0E0E0;
    font-size: 13px;
}}

QTreeWidget#DocsTree::item {{
    padding: 8px 4px;
    border-radius: 6px;
    margin-bottom: 2px;
}}

QTreeWidget#DocsTree::item:hover {{
    background-color: #111A11;
}}

QTreeWidget#DocsTree::item:selected {{
    background-color: rgba(0, 230, 118, 0.1);
    color: #00E676;
    font-weight: normal;
    border: 1px solid rgba(0, 230, 118, 0.3);
}}

QTreeWidget#DocsTree::branch:has-children:!has-siblings:closed,
QTreeWidget#DocsTree::branch:closed:has-children:has-siblings {{
    image: url({CHEVRON_RIGHT});
}}

QTreeWidget#DocsTree::branch:open:has-children:!has-siblings,
QTreeWidget#DocsTree::branch:open:has-children:has-siblings {{
    image: url({CHEVRON_DOWN});
}}

QPushButton#DocsCloseBtn {{
    background-color: #111A11;
    border: 1px solid #1A2E1A;
    border-radius: 8px;
    color: #E0E0E0;
    font-weight: normal;
}}

QPushButton#DocsCloseBtn:hover {{
    background-color: #2E1111;
    border-color: #FF5252;
    color: #FF5252;
}}

QTextBrowser#DocsBrowser {{
    background-color: #080C08;
    color: #E0E0E0;
    font-size: 15px;
    border: none;
    padding: 40px;
    font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;
}}
"""