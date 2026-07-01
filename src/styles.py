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

# Глобальные переменные палитры
COLOR_PRIMARY = "#10B981"
COLOR_PRIMARY_DARK = "#059669"
COLOR_PRIMARY_LIGHT = "#34D399"
COLOR_BG = "#060906"
COLOR_ACCENT_BG = "#0E140E"
COLOR_BORDER = "#1E2B1E"
COLOR_BORDER_LIGHT = "#2A3C2A"
COLOR_BORDER_DARK = "#121A12"
COLOR_TEXT_MAIN = "#F8FAFC"
COLOR_TEXT_MUTED = "#94A3B8"
COLOR_TEXT_DISABLED = "#475569"
COLOR_HOVER_BG = "#151F15"
COLOR_SELECT_BG = "#1A261A"
COLOR_CONSOLE_BG = "#040604"
COLOR_SCROLL_HANDLE = "#1E2B1E"

# Акценты статусов
COLOR_SUCCESS = "#10B981"
COLOR_WARNING = "#F59E0B"
COLOR_DANGER = "#EF4444"
COLOR_INFO = "#3B82F6"

CHEVRON_RIGHT = ""
CHEVRON_DOWN = ""

STYLESHEET = ""
DOCS_STYLESHEET = ""


def get_svg_icon(points, color):
    """Генерация base64 SVG иконки шеврона с нужным цветом"""
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="{points}"></polyline></svg>'
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode('utf-8')).decode('utf-8')


def load_theme(theme_name=None):
    """Считывает тему и пересобирает глобальные стили"""
    global COLOR_PRIMARY, COLOR_PRIMARY_DARK, COLOR_PRIMARY_LIGHT, COLOR_BG, COLOR_ACCENT_BG
    global COLOR_BORDER, COLOR_BORDER_LIGHT, COLOR_BORDER_DARK, COLOR_TEXT_MAIN, COLOR_TEXT_MUTED
    global COLOR_TEXT_DISABLED, COLOR_HOVER_BG, COLOR_SELECT_BG, COLOR_CONSOLE_BG
    global COLOR_SCROLL_HANDLE, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER, COLOR_INFO
    global CHEVRON_RIGHT, CHEVRON_DOWN, STYLESHEET, DOCS_STYLESHEET
    
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
            
    from src.core import constants
    constants.CURRENT_THEME = theme_name
            
    if theme_name == "blue":
        # Blue Theme (Ultra Modern Premium)
        COLOR_PRIMARY = "#3B82F6"
        COLOR_PRIMARY_DARK = "#2563EB"
        COLOR_PRIMARY_LIGHT = "#60A5FA"
        COLOR_BG = "#05080E"
        COLOR_ACCENT_BG = "#0B111D"
        COLOR_HOVER_BG = "#111A2C"
        COLOR_SELECT_BG = "#17233B"
        COLOR_CONSOLE_BG = "#030509"
        COLOR_BORDER = "#1E293B"
        COLOR_BORDER_LIGHT = "#334155"
        COLOR_BORDER_DARK = "#0F172A"
        COLOR_TEXT_MAIN = "#F8FAFC"
        COLOR_TEXT_MUTED = "#94A3B8"
        COLOR_TEXT_DISABLED = "#475569"
        COLOR_SCROLL_HANDLE = "#1E293B"
    else:
        # Green Theme (Ultra Modern Premium)
        COLOR_PRIMARY = "#10B981"
        COLOR_PRIMARY_DARK = "#059669"
        COLOR_PRIMARY_LIGHT = "#34D399"
        COLOR_BG = "#060906"
        COLOR_ACCENT_BG = "#0E140E"
        COLOR_HOVER_BG = "#151F15"
        COLOR_SELECT_BG = "#1A261A"
        COLOR_CONSOLE_BG = "#040604"
        COLOR_BORDER = "#1E2B1E"
        COLOR_BORDER_LIGHT = "#2A3C2A"
        COLOR_BORDER_DARK = "#121A12"
        COLOR_TEXT_MAIN = "#F8FAFC"
        COLOR_TEXT_MUTED = "#94A3B8"
        COLOR_TEXT_DISABLED = "#475569"
        COLOR_SCROLL_HANDLE = "#1E2B1E"

    # Status Colors 
    COLOR_SUCCESS = "#10B981"
    COLOR_WARNING = "#F59E0B"
    COLOR_DANGER = "#EF4444"
    COLOR_INFO = "#3B82F6"

    CHEVRON_RIGHT = get_svg_icon("9 18 15 12 9 6", COLOR_PRIMARY)
    CHEVRON_DOWN = get_svg_icon("6 9 12 15 18 9", COLOR_PRIMARY)

    def hex_to_rgba(hex_code, alpha):
        hex_code = hex_code.lstrip('#')
        r = int(hex_code[0:2], 16)
        g = int(hex_code[2:4], 16)
        b = int(hex_code[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha})"

    BTN_DANGER_BG = hex_to_rgba(COLOR_DANGER, 0.08)
    BTN_DANGER_HOVER = hex_to_rgba(COLOR_DANGER, 0.15)
    BTN_DANGER_PRESSED = hex_to_rgba(COLOR_DANGER, 0.25)
    
    BTN_WARNING_BG = hex_to_rgba(COLOR_WARNING, 0.08)
    BTN_SUCCESS_BG = hex_to_rgba(COLOR_PRIMARY, 0.08)

    # QSS doesn't support shadows on generic widgets well, but we simulate depth with top/bottom border nuances
    # Very subtle linear gradients create a "glass" or "premium" feel.
    GRADIENT_BG = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {COLOR_BG}, stop:1 {COLOR_CONSOLE_BG})"
    GRADIENT_ACCENT = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {COLOR_ACCENT_BG}, stop:1 {COLOR_BG})"
    GRADIENT_BTN = f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {COLOR_HOVER_BG}, stop:1 {COLOR_ACCENT_BG})"

    STYLESHEET = f"""
QWidget {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT_MAIN};
    font-size: 13px;
    font-family: '{FONT_NAME}', 'Segoe UI', sans-serif;
}}

QToolTip {{
    background-color: {COLOR_ACCENT_BG};
    color: {COLOR_PRIMARY_LIGHT};
    border: 1px solid {COLOR_PRIMARY_DARK};
    border-radius: 6px;
    padding: 8px 10px;
    font-size: 12px;
    font-family: '{FONT_NAME}';
}}

QScrollArea {{
    border: none;
    background-color: transparent;
}}

QWidget#ScrollContent {{
    background-color: transparent;
}}

/* Account Cards */
QFrame#AccountRow {{
    background-color: {GRADIENT_ACCENT};
    border: 1px solid {COLOR_BORDER};
    border-top: 1px solid {COLOR_BORDER_LIGHT};
    border-radius: 10px;
    margin: 6px 2px;
}}

QFrame#AccountRow:hover {{
    border: 1px solid {COLOR_BORDER_LIGHT};
    border-left: 3px solid {COLOR_PRIMARY};
    background-color: {COLOR_HOVER_BG};
}}

/* General Buttons (Tactile and Premium) */
QPushButton {{
    background-color: {GRADIENT_BTN};
    color: {COLOR_TEXT_MAIN};
    border: 1px solid {COLOR_BORDER};
    border-bottom: 2px solid {COLOR_BORDER_DARK};
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: bold;
    outline: none;
}}

QPushButton:hover {{
    background-color: {COLOR_HOVER_BG};
    border: 1px solid {COLOR_BORDER_LIGHT};
    border-bottom: 2px solid {COLOR_BORDER};
    color: {COLOR_PRIMARY_LIGHT};
}}

QPushButton:pressed {{
    background-color: {COLOR_SELECT_BG};
    border: 1px solid {COLOR_BORDER_DARK};
    border-top: 2px solid {COLOR_BORDER_DARK};
    color: {COLOR_PRIMARY};
    padding-top: 9px;
    padding-bottom: 7px;
}}

QPushButton:disabled {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT_DISABLED};
    border: 1px solid {COLOR_BORDER_DARK};
    border-bottom: 1px solid {COLOR_BORDER_DARK};
}}

/* Primary Buttons (Launch) */
QPushButton#LaunchBtn {{
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {COLOR_PRIMARY}, stop:1 {COLOR_PRIMARY_DARK});
    color: #FFFFFF;
    border: 1px solid {COLOR_PRIMARY_DARK};
    border-bottom: 2px solid #047857;
    border-radius: 6px;
    font-weight: bold;
}}

QPushButton#LaunchBtn:hover {{
    background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {COLOR_PRIMARY_LIGHT}, stop:1 {COLOR_PRIMARY});
    border: 1px solid {COLOR_PRIMARY_LIGHT};
    border-bottom: 2px solid {COLOR_PRIMARY_DARK};
}}

QPushButton#LaunchBtn:pressed {{
    background-color: {COLOR_PRIMARY_DARK};
    border: 1px solid #047857;
    border-top: 2px solid #047857;
    color: {COLOR_TEXT_MAIN};
    padding-top: 9px;
    padding-bottom: 7px;
}}

/* Secondary Buttons */
QPushButton#ExplorerBtn {{ 
    background-color: {hex_to_rgba(COLOR_INFO, 0.08)}; 
    border: 1px solid {hex_to_rgba(COLOR_INFO, 0.3)}; 
    border-bottom: 2px solid {hex_to_rgba(COLOR_INFO, 0.5)};
    color: {COLOR_PRIMARY_LIGHT if theme_name == "blue" else "#93C5FD"}; 
}}
QPushButton#ExplorerBtn:hover {{ 
    background-color: {hex_to_rgba(COLOR_INFO, 0.15)}; 
    border-color: {COLOR_INFO}; 
    color: #FFFFFF;
}}
QPushButton#ExplorerBtn:pressed {{ 
    background-color: {hex_to_rgba(COLOR_INFO, 0.25)}; 
    border-top: 2px solid {hex_to_rgba(COLOR_INFO, 0.5)};
    border-bottom: 1px solid {hex_to_rgba(COLOR_INFO, 0.3)};
    padding-top: 9px; padding-bottom: 7px;
}}

QPushButton#DeviceBtn {{ 
    background-color: {hex_to_rgba("#A855F7", 0.08)}; 
    border: 1px solid {hex_to_rgba("#A855F7", 0.3)}; 
    border-bottom: 2px solid {hex_to_rgba("#A855F7", 0.5)};
    color: #D8B4FE;
}}
QPushButton#DeviceBtn:hover {{ 
    background-color: {hex_to_rgba("#A855F7", 0.15)}; 
    border-color: #A855F7;
    color: #FFFFFF;
}}
QPushButton#DeviceBtn:pressed {{ 
    background-color: {hex_to_rgba("#A855F7", 0.25)}; 
    border-top: 2px solid {hex_to_rgba("#A855F7", 0.5)};
    border-bottom: 1px solid {hex_to_rgba("#A855F7", 0.3)};
    padding-top: 9px; padding-bottom: 7px;
}}

/* Danger Buttons */
QPushButton#DeleteBtn {{ 
    background-color: {BTN_DANGER_BG}; 
    border: 1px solid {hex_to_rgba(COLOR_DANGER, 0.3)};
    border-bottom: 2px solid {hex_to_rgba(COLOR_DANGER, 0.5)};
    color: {COLOR_DANGER};
}}
QPushButton#DeleteBtn:hover {{ 
    background-color: {BTN_DANGER_HOVER}; 
    border-color: {COLOR_DANGER}; 
    color: #FFFFFF;
}}
QPushButton#DeleteBtn:pressed {{ 
    background-color: {BTN_DANGER_PRESSED}; 
    border-top: 2px solid {hex_to_rgba(COLOR_DANGER, 0.5)};
    border-bottom: 1px solid {hex_to_rgba(COLOR_DANGER, 0.3)};
    padding-top: 9px; padding-bottom: 7px;
}}

/* Status Indicator Buttons */
QPushButton#CheckBtn[status="success"], QPushButton#SessionBtn[status="alive"] {{ 
    background-color: {BTN_SUCCESS_BG}; 
    border: 1px solid {hex_to_rgba(COLOR_PRIMARY, 0.4)};
    border-bottom: 2px solid {hex_to_rgba(COLOR_PRIMARY, 0.6)};
    color: {COLOR_PRIMARY_LIGHT};
}}
QPushButton#CheckBtn[status="error"], QPushButton#SessionBtn[status="banned"] {{ 
    background-color: {BTN_DANGER_BG}; 
    border: 1px solid {hex_to_rgba(COLOR_DANGER, 0.4)};
    border-bottom: 2px solid {hex_to_rgba(COLOR_DANGER, 0.6)};
    color: {COLOR_DANGER};
}}
QPushButton#CheckBtn[status="checking"] {{ 
    background-color: {BTN_WARNING_BG}; 
    border: 1px solid {hex_to_rgba(COLOR_WARNING, 0.4)};
    border-bottom: 2px solid {hex_to_rgba(COLOR_WARNING, 0.6)};
    color: {COLOR_WARNING};
}}

/* Session Button Default */
QPushButton#SessionBtn {{ 
    background-color: {COLOR_ACCENT_BG}; 
    border: 1px solid {COLOR_BORDER}; 
    border-bottom: 2px solid {COLOR_BORDER_DARK};
}}
QPushButton#SessionBtn:hover {{ 
    background-color: {COLOR_HOVER_BG}; 
    border-color: {COLOR_BORDER_LIGHT};
}}
QPushButton#SessionBtn:pressed {{ 
    padding-top: 9px; padding-bottom: 7px;
    border-top: 2px solid {COLOR_BORDER_DARK};
    border-bottom: 1px solid {COLOR_BORDER};
}}

/* Icon Only Buttons (Move) */
QPushButton#MoveBtn {{
    background-color: transparent;
    border: none;
    color: {COLOR_TEXT_DISABLED};
    font-size: 14px;
    padding: 4px;
}}
QPushButton#MoveBtn:hover {{
    color: {COLOR_PRIMARY_LIGHT};
    background-color: {hex_to_rgba(COLOR_PRIMARY, 0.1)};
    border-radius: 4px;
}}
QPushButton#MoveBtn:pressed {{
    color: {COLOR_PRIMARY_DARK};
    background-color: {hex_to_rgba(COLOR_PRIMARY, 0.2)};
    padding-top: 5px; padding-bottom: 3px;
}}

/* Tab Widget & Bar (Segmented Control Style) */
QTabWidget::pane {{
    border: 1px solid {COLOR_BORDER};
    background-color: {COLOR_ACCENT_BG};
    border-radius: 12px;
    top: -1px;
    padding: 10px;
}}

QTabBar::tab {{
    background-color: transparent;
    color: {COLOR_TEXT_MUTED};
    padding: 8px 24px;
    border: 1px solid transparent;
    font-weight: bold;
    border-radius: 20px; 
    margin: 4px;
}}

QTabBar::tab:hover {{
    background-color: {COLOR_HOVER_BG};
    color: {COLOR_TEXT_MAIN};
}}

QTabBar::tab:selected {{
    color: #FFFFFF;
    background-color: {hex_to_rgba(COLOR_PRIMARY, 0.15)};
    border: 1px solid {hex_to_rgba(COLOR_PRIMARY, 0.4)};
}}

/* Inputs */
QLineEdit, QSpinBox, QTextEdit {{
    background-color: {COLOR_CONSOLE_BG};
    border: 1px solid {COLOR_BORDER};
    border-bottom: 2px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 10px 14px;
    color: {COLOR_TEXT_MAIN};
    selection-background-color: {COLOR_PRIMARY_DARK};
    selection-color: #FFFFFF;
}}

QLineEdit:hover, QSpinBox:hover, QTextEdit:hover {{
    border: 1px solid {COLOR_BORDER_LIGHT};
    border-bottom: 2px solid {COLOR_BORDER_LIGHT};
}}

QLineEdit:focus, QSpinBox:focus, QTextEdit:focus {{
    border: 1px solid {COLOR_PRIMARY};
    border-bottom: 2px solid {COLOR_PRIMARY_LIGHT};
    background-color: {COLOR_BG};
}}

QLineEdit:disabled, QTextEdit:disabled {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT_DISABLED};
    border: 1px solid {COLOR_BORDER_DARK};
    border-bottom: 1px solid {COLOR_BORDER_DARK};
}}

QSpinBox::up-button, QSpinBox::down-button {{
    width: 0px;
}}

/* ComboBox */
QComboBox {{
    background-color: {COLOR_CONSOLE_BG};
    border: 1px solid {COLOR_BORDER};
    border-bottom: 2px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 10px 14px;
    color: {COLOR_TEXT_MAIN};
}}

QComboBox:hover {{
    border: 1px solid {COLOR_BORDER_LIGHT};
    border-bottom: 2px solid {COLOR_BORDER_LIGHT};
}}

QComboBox:focus {{
    border: 1px solid {COLOR_PRIMARY};
    border-bottom: 2px solid {COLOR_PRIMARY_LIGHT};
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 35px;
    border-left: none;
}}

QComboBox::down-arrow {{
    image: url({CHEVRON_DOWN});
    width: 14px;
    height: 14px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLOR_ACCENT_BG};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    selection-background-color: {hex_to_rgba(COLOR_PRIMARY, 0.15)};
    selection-color: {COLOR_PRIMARY_LIGHT};
    color: {COLOR_TEXT_MAIN};
    outline: none;
    padding: 6px;
}}

/* Typography */
QLabel#Title {{
    color: {COLOR_PRIMARY};
    font-size: 28px;
    font-weight: bold;
    font-family: '{TITLE_FONT_NAME}';
    letter-spacing: 3px;
}}

QLabel#SettingLabel {{
    color: {COLOR_TEXT_MUTED};
    font-weight: bold;
    margin-top: 14px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
}}

/* Images & Avatars */
QLabel#AvatarLabel {{
    background-color: {COLOR_CONSOLE_BG};
    border: 2px solid {COLOR_BORDER};
    border-radius: 25px;
}}

QLabel#AvatarLabel:hover {{
    border: 2px solid {COLOR_PRIMARY_LIGHT};
    background-color: {COLOR_ACCENT_BG};
}}

/* Badges */
QLabel#StatusRunning {{ 
    color: #FFFFFF;
    font-weight: bold;
    font-size: 11px;
    background-color: {COLOR_PRIMARY_DARK};
    padding: 5px 14px;
    border-radius: 12px;
}}

QLabel#StatusStopped {{ 
    color: {COLOR_TEXT_MUTED}; 
    font-size: 11px;
    font-weight: bold;
    background-color: {COLOR_BG};
    padding: 5px 14px;
    border-radius: 12px;
    border: 1px solid {COLOR_BORDER};
}}

/* Containers */
QFrame#CreateSection {{
    background-color: {GRADIENT_ACCENT};
    border: 1px solid {COLOR_BORDER};
    border-top: 1px solid {COLOR_BORDER_LIGHT};
    border-radius: 14px;
    padding: 28px;
    margin-top: 16px;
}}

/* Scrollbars */
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 12px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {COLOR_BORDER};
    border-radius: 6px;
    min-height: 40px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLOR_BORDER_LIGHT};
}}
QScrollBar::handle:vertical:pressed {{
    background: {COLOR_PRIMARY_DARK};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

QScrollBar:horizontal {{
    border: none;
    background: transparent;
    height: 12px;
    margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: {COLOR_BORDER};
    min-width: 40px;
    border-radius: 6px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {COLOR_BORDER_LIGHT};
}}
QScrollBar::handle:horizontal:pressed {{
    background: {COLOR_PRIMARY_DARK};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}

/* Checkboxes */
QCheckBox {{
    spacing: 12px;
    color: {COLOR_TEXT_MAIN};
    font-weight: normal;
    font-size: 14px;
}}

QCheckBox::indicator {{
    width: 20px;
    height: 20px;
    border: 2px solid {COLOR_BORDER};
    border-bottom: 3px solid {COLOR_BORDER};
    border-radius: 6px;
    background-color: {COLOR_CONSOLE_BG};
}}

QCheckBox::indicator:hover {{
    border-color: {COLOR_PRIMARY_DARK};
    border-bottom-color: {COLOR_PRIMARY_DARK};
    background-color: {COLOR_BG};
}}

QCheckBox::indicator:checked {{
    background-color: {COLOR_PRIMARY_DARK};
    border: 2px solid {COLOR_PRIMARY_DARK};
    border-bottom: 3px solid {COLOR_PRIMARY_DARK};
    image: url({CHEVRON_DOWN});
}}

QCheckBox::indicator:checked:hover {{
    background-color: {COLOR_PRIMARY};
    border-color: {COLOR_PRIMARY};
    border-bottom-color: {COLOR_PRIMARY};
}}

/* Progress Bar */
QProgressBar {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    background-color: {COLOR_CONSOLE_BG};
    text-align: center;
    color: {COLOR_TEXT_MAIN};
    font-weight: bold;
    height: 16px;
}}

QProgressBar::chunk {{
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLOR_PRIMARY_DARK}, stop:1 {COLOR_PRIMARY_LIGHT});
    border-radius: 6px;
}}
"""

    DOCS_STYLESHEET = f"""
QWidget#DocsPage {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT_MAIN};
}}

QFrame#DocsSidebar {{
    background-color: {COLOR_ACCENT_BG};
    border-right: 1px solid {COLOR_BORDER};
}}

QLabel#DocsSidebarTitle {{
    color: {COLOR_PRIMARY};
    font-weight: bold;
    font-size: 15px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    padding-bottom: 16px;
    border-bottom: 1px solid {COLOR_BORDER};
}}

QTreeWidget#DocsTree {{
    background-color: transparent;
    border: none;
    outline: none;
    color: {COLOR_TEXT_MAIN};
    font-size: 14px;
}}

QTreeWidget#DocsTree::item {{
    padding: 10px 8px;
    border-radius: 8px;
    margin-bottom: 4px;
}}

QTreeWidget#DocsTree::item:hover {{
    background-color: {COLOR_HOVER_BG};
    color: {COLOR_PRIMARY_LIGHT};
}}

QTreeWidget#DocsTree::item:selected {{
    background-color: {hex_to_rgba(COLOR_PRIMARY, 0.1)};
    color: {COLOR_PRIMARY};
    font-weight: bold;
    border-left: 3px solid {COLOR_PRIMARY};
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
    background-color: {COLOR_ACCENT_BG};
    border: 1px solid {COLOR_BORDER};
    border-bottom: 2px solid {COLOR_BORDER_DARK};
    border-radius: 8px;
    color: {COLOR_TEXT_MAIN};
    font-weight: bold;
    padding: 10px;
}}

QPushButton#DocsCloseBtn:hover {{
    background-color: {BTN_DANGER_BG};
    border-color: {COLOR_DANGER};
    border-bottom-color: {COLOR_DANGER};
    color: {COLOR_DANGER};
}}
QPushButton#DocsCloseBtn:pressed {{
    background-color: {BTN_DANGER_PRESSED};
    border-top: 2px solid {COLOR_DANGER};
    border-bottom: 1px solid {COLOR_DANGER};
    padding-top: 11px; padding-bottom: 9px;
}}

QTextBrowser#DocsBrowser {{
    background-color: {COLOR_BG};
    color: {COLOR_TEXT_MAIN};
    font-size: 16px;
    border: none;
    padding: 50px;
    font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;
    line-height: 1.8;
}}
"""

load_theme()