"""
Глобальные стили (QSS) основного интерфейса ShadowGram.
Определяет:

- Цветовую палитру и шрифты (Зеленый Кибер-стиль или Синий стиль)
- Стили для кнопок, полей ввода и карточек аккаунтов
- Кастомизацию скроллбаров и чекбоксов
"""
import json
import base64
from pathlib import Path
from src.core.constants import CONFIG_FILE

# Настройки шрифта
FONT_NAME = "Monocraft"
TITLE_FONT_NAME = "alagard-12px-unicode"

# Глобальные переменные палитры (будут перезаписываться в load_theme)
COLOR_PRIMARY = "#00E676"
COLOR_PRIMARY_DARK = "#00C853"
COLOR_BG = "#080C08"
COLOR_ACCENT_BG = "#0D140D"
COLOR_BORDER = "#1A2E1A"
COLOR_BORDER_LIGHT = "#142114"
COLOR_BORDER_DARK = "#244024"
COLOR_TEXT_MUTED = "#8B9A8B"
COLOR_TEXT_DISABLED = "#4A5C4A"
COLOR_HOVER_BG = "#111A11"
COLOR_SELECT_BG = "#1A2B1A"
COLOR_CONSOLE_BG = "#040604"
COLOR_SCROLL_HANDLE = "#1A2E1A"

CHEVRON_RIGHT = ""
CHEVRON_DOWN = ""

STYLESHEET = ""
DOCS_STYLESHEET = ""


def get_svg_icon(points, color):
    """Генерация base64 SVG иконки шеврона с нужным цветом"""
    # Заменяем # на %23 во внутреннем SVG, но так как кодируем в base64, можно писать цвет напрямую
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="{points}"></polyline></svg>'
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode('utf-8')).decode('utf-8')


def load_theme(theme_name=None):
    """Считывает тему и пересобирает глобальные стили"""
    global COLOR_PRIMARY, COLOR_PRIMARY_DARK, COLOR_BG, COLOR_ACCENT_BG
    global COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_BORDER_DARK, COLOR_TEXT_MUTED
    global COLOR_TEXT_DISABLED, COLOR_HOVER_BG, COLOR_SELECT_BG, COLOR_CONSOLE_BG
    global COLOR_SCROLL_HANDLE, CHEVRON_RIGHT, CHEVRON_DOWN, STYLESHEET, DOCS_STYLESHEET
    
    if not theme_name:
        theme_name = "green"
        try:
            config_path = Path(CONFIG_FILE)
            if config_path.exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    theme_name = data.get("settings", {}).get("theme", "green")
        except Exception:
            pass
            
    # Update current theme in constants
    from src.core import constants
    constants.CURRENT_THEME = theme_name
            
    if theme_name == "blue":
        # Синяя тема с голубыми элементами
        COLOR_PRIMARY = "#00B0FF"
        COLOR_PRIMARY_DARK = "#0091EA"
        COLOR_BG = "#08080C"
        COLOR_ACCENT_BG = "#0D0D14"
        COLOR_BORDER = "#1A1A2E"
        COLOR_BORDER_LIGHT = "#141421"
        COLOR_BORDER_DARK = "#242440"
        COLOR_TEXT_MUTED = "#8B8B9A"
        COLOR_TEXT_DISABLED = "#4A4A5C"
        COLOR_HOVER_BG = "#11111A"
        COLOR_SELECT_BG = "#1A1A2B"
        COLOR_CONSOLE_BG = "#040406"
        COLOR_SCROLL_HANDLE = "#1A1A2E"
    else:
        # Зеленая кибер-тема по умолчанию
        COLOR_PRIMARY = "#00E676"
        COLOR_PRIMARY_DARK = "#00C853"
        COLOR_BG = "#080C08"
        COLOR_ACCENT_BG = "#0D140D"
        COLOR_BORDER = "#1A2E1A"
        COLOR_BORDER_LIGHT = "#142114"
        COLOR_BORDER_DARK = "#244024"
        COLOR_TEXT_MUTED = "#8B9A8B"
        COLOR_TEXT_DISABLED = "#4A5C4A"
        COLOR_HOVER_BG = "#111A11"
        COLOR_SELECT_BG = "#1A2B1A"
        COLOR_CONSOLE_BG = "#040604"
        COLOR_SCROLL_HANDLE = "#1A2E1A"

    CHEVRON_RIGHT = get_svg_icon("9 18 15 12 9 6", COLOR_PRIMARY)
    CHEVRON_DOWN = get_svg_icon("6 9 12 15 18 9", COLOR_PRIMARY)

    # Строим основной STYLESHEET
    STYLESHEET = f"""
QWidget {{
    background-color: {COLOR_BG};
    color: #E0E0E0;
    font-size: 13px;
    font-family: '{FONT_NAME}', 'Segoe UI', sans-serif;
}}

QToolTip {{
    background-color: {COLOR_ACCENT_BG};
    color: {COLOR_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 6px;
    font-size: 11px;
    font-family: '{FONT_NAME}';
}}

QScrollArea {{
    border: none;
    background-color: {COLOR_BG};
}}

QWidget#ScrollContent {{
    background-color: {COLOR_BG};
}}

QFrame#AccountRow {{
    background-color: {COLOR_ACCENT_BG};
    border: 1px solid {COLOR_BORDER};
    border-radius: 12px;
    margin: 4px 0px;
}}

QFrame#AccountRow:hover {{
    border: 1px solid {COLOR_PRIMARY};
    background-color: {COLOR_HOVER_BG};
}}

QPushButton {{
    background-color: {COLOR_HOVER_BG};
    color: {COLOR_PRIMARY};
    border: 1px solid {COLOR_BORDER_DARK};
    padding: 8px 16px;
    border-radius: 8px;
    font-weight: normal;
}}

QPushButton:hover {{
    background-color: {COLOR_SELECT_BG};
    border-color: {COLOR_PRIMARY};
    color: #FFFFFF;
}}

QPushButton:pressed {{
    background-color: {COLOR_BG};
    border-color: {COLOR_PRIMARY_DARK};
}}

QPushButton:disabled {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT_DISABLED};
    border: 1px solid {COLOR_BORDER_LIGHT};
}}

QPushButton#LaunchBtn {{
    background-color: {COLOR_PRIMARY_DARK};
    color: {f"#000000" if COLOR_PRIMARY == "#00E676" else "#FFFFFF"};
    border: none;
    border-radius: 8px;
    font-weight: normal;
}}

QPushButton#LaunchBtn:hover {{
    background-color: {COLOR_PRIMARY};
}}

QPushButton#ExplorerBtn {{ background-color: #0D2136; border-color: #153E6B; color: #58A6FF; }}
QPushButton#ExplorerBtn:hover {{ background-color: #153E6B; border-color: #58A6FF; color: #FFFFFF; }}

QPushButton#EditBtn, QPushButton#NotesBtn, QPushButton#CheckBtn {{ 
    background-color: {COLOR_HOVER_BG}; 
    border: 1px solid {COLOR_BORDER_DARK};
}}
QPushButton#EditBtn:hover, QPushButton#NotesBtn:hover, QPushButton#CheckBtn:hover {{ 
    background-color: {COLOR_SELECT_BG}; 
    border-color: {COLOR_PRIMARY};
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

QPushButton#CheckBtn[status="success"], QPushButton#SessionBtn[status="alive"] {{ 
    background-color: {"rgba(0, 230, 118, 0.1)" if COLOR_PRIMARY == "#00E676" else "rgba(0, 176, 255, 0.1)"}; 
    border-color: {COLOR_PRIMARY};
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

QPushButton#MoveBtn {{
    background-color: transparent;
    border: none;
    color: {COLOR_TEXT_DISABLED};
    font-size: 10px;
    padding: 2px;
}}
QPushButton#MoveBtn:hover {{
    color: {COLOR_PRIMARY};
}}

QTabWidget::pane {{
    border: 1px solid {COLOR_BORDER};
    background-color: {COLOR_ACCENT_BG};
    border-radius: 8px;
    top: -1px;
}}

QTabBar::tab {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT_MUTED};
    padding: 8px 18px;
    border: 1px solid transparent;
    border-bottom: 2px solid {COLOR_BORDER};
    font-weight: normal;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 2px;
}}

QTabBar::tab:hover {{
    background-color: {COLOR_HOVER_BG};
    color: #E0E0E0;
}}

QTabBar::tab:selected {{
    color: {COLOR_PRIMARY};
    background-color: {COLOR_ACCENT_BG};
    border: 1px solid {COLOR_BORDER};
    border-bottom: 2px solid {COLOR_PRIMARY};
}}

QLineEdit, QSpinBox, QTextEdit {{
    background-color: {COLOR_CONSOLE_BG};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 8px;
    color: {COLOR_PRIMARY};
    selection-background-color: {COLOR_BORDER_LIGHT};
}}

QLineEdit:focus, QSpinBox:focus, QTextEdit:focus {{
    border: 1px solid {COLOR_PRIMARY};
    background-color: {COLOR_HOVER_BG};
}}

QSpinBox::up-button, QSpinBox::down-button {{
    width: 0px;
}}

QComboBox {{
    background-color: {COLOR_CONSOLE_BG};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 6px 12px;
    color: #E0E0E0;
}}

QComboBox:hover, QComboBox:focus {{
    border: 1px solid {COLOR_PRIMARY};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 25px;
    border-left: none;
}}

QComboBox::down-arrow {{
    image: url({CHEVRON_DOWN});
    width: 10px;
    height: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLOR_ACCENT_BG};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    selection-background-color: {COLOR_SELECT_BG};
    selection-color: {COLOR_PRIMARY};
    color: #E0E0E0;
    outline: none;
}}

QLabel#Title {{
    color: {COLOR_PRIMARY};
    font-size: 26px;
    font-weight: normal;
    font-family: '{TITLE_FONT_NAME}';
    letter-spacing: 2px;
    text-shadow: {"0px 0px 10px rgba(0, 230, 118, 0.5)" if COLOR_PRIMARY == "#00E676" else "0px 0px 10px rgba(0, 176, 255, 0.5)"};
}}

QLabel#SettingLabel {{
    color: {COLOR_TEXT_MUTED};
    font-weight: normal;
    margin-top: 10px;
    font-size: 13px;
}}

QLabel#AvatarLabel {{
    background-color: transparent;
    border: 2px solid {COLOR_BORDER};
    border-radius: 25px;
}}

QLabel#AvatarLabel:hover {{
    border: 2px solid {COLOR_PRIMARY};
}}

QLabel#NotePopup {{
    background-color: {COLOR_ACCENT_BG};
    color: #E0E0E0;
    border: 1px solid {COLOR_PRIMARY};
    border-radius: 8px;
    padding: 12px;
    font-size: 12px;
    font-family: '{FONT_NAME}';
}}

QLabel#StatusRunning {{ 
    color: {f"#000000" if COLOR_PRIMARY == "#00E676" else "#FFFFFF"}; 
    font-weight: normal;
    font-size: 11px;
    background-color: {COLOR_PRIMARY};
    padding: 4px 10px;
    border-radius: 6px;
}}

QLabel#StatusStopped {{ 
    color: {COLOR_TEXT_MUTED}; 
    font-size: 11px;
    font-weight: normal;
    background-color: {COLOR_HOVER_BG};
    padding: 4px 10px;
    border-radius: 6px;
    border: 1px solid {COLOR_BORDER_DARK};
}}

QFrame#CreateSection {{
    background-color: {COLOR_ACCENT_BG};
    border: 1px solid {COLOR_BORDER};
    border-radius: 12px;
    padding: 20px;
    margin-top: 10px;
}}

QScrollBar:vertical {{
    border: none;
    background: {COLOR_BG};
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {COLOR_SCROLL_HANDLE};
    min-height: 30px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLOR_PRIMARY};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    border: none;
    background: {COLOR_BG};
    height: 8px;
    margin: 0px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {COLOR_SCROLL_HANDLE};
    min-width: 30px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {COLOR_PRIMARY};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

QCheckBox {{
    spacing: 8px;
    color: #E0E0E0;
    font-weight: normal;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {COLOR_BORDER};
    border-radius: 5px;
    background-color: {COLOR_CONSOLE_BG};
}}

QCheckBox::indicator:hover {{
    border-color: {COLOR_PRIMARY};
}}

QCheckBox::indicator:checked {{
    background-color: {COLOR_PRIMARY_DARK};
    border-color: {COLOR_PRIMARY_DARK};
    image: url({CHEVRON_DOWN});
}}

QProgressBar {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    background-color: {COLOR_CONSOLE_BG};
    text-align: center;
    color: white;
    font-weight: normal;
}}

QProgressBar::chunk {{
    background-color: {COLOR_PRIMARY};
    border-radius: 5px;
}}
"""

    # Строим DOCS_STYLESHEET
    DOCS_STYLESHEET = f"""
QWidget#DocsWindow {{
    background-color: {COLOR_BG};
    color: #E0E0E0;
}}

QFrame#DocsSidebar {{
    background-color: {COLOR_ACCENT_BG};
    border-right: 1px solid {COLOR_BORDER};
}}

QLabel#DocsSidebarTitle {{
    color: {COLOR_PRIMARY};
    font-weight: normal;
    font-size: 15px;
    letter-spacing: 1px;
    padding-bottom: 10px;
    border-bottom: 1px solid {COLOR_BORDER};
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
    background-color: {COLOR_HOVER_BG};
}}

QTreeWidget#DocsTree::item:selected {{
    background-color: {"rgba(0, 230, 118, 0.1)" if COLOR_PRIMARY == "#00E676" else "rgba(0, 176, 255, 0.1)"};
    color: {COLOR_PRIMARY};
    font-weight: normal;
    border: {"1px solid rgba(0, 230, 118, 0.3)" if COLOR_PRIMARY == "#00E676" else "1px solid rgba(0, 176, 255, 0.3)"};
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
    background-color: {COLOR_HOVER_BG};
    border: 1px solid {COLOR_BORDER};
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
    background-color: {COLOR_BG};
    color: #E0E0E0;
    font-size: 15px;
    border: none;
    padding: 40px;
    font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;
}}
"""


# Загружаем тему по умолчанию при импорте
load_theme()