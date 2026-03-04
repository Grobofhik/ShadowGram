from pathlib import Path
from typing import Final

"""
Глобальные константы и пути проекта.
Определяет:

- BASE_DIR: корневая директория проекта
- CONFIG_FILE: путь к файлу конфигурации JSON
- RESOURCE_DIR: путь к ресурсам (иконки, звуки, шрифты) с поддержкой системных путей
- ICON_PATHр, SOUND_PATH, FONTS_DIR: пямые пути к медиа-ресурсам
"""

BASE_DIR: Final[Path] = Path(__file__).parent.parent.parent.absolute()

CONFIG_DIR: Final[Path] = BASE_DIR
CONFIG_FILE: Final[Path] = BASE_DIR / "config.json"

SYSTEM_RESOURCE_DIR: Final[Path] = Path("/usr/share/shadowgram/resources")
LOCAL_RESOURCE_DIR: Final[Path] = BASE_DIR / "resources"

RESOURCE_DIR: Final[Path] = (
    LOCAL_RESOURCE_DIR if LOCAL_RESOURCE_DIR.exists() else SYSTEM_RESOURCE_DIR
)

# Иконки
ICON_PATH: Final[Path] = RESOURCE_DIR / "icons" / "GrobTyanka.png"
LOGO_PATH: Final[Path] = RESOURCE_DIR / "icons" / "GrobTyan_logo.png"
SUCCESS_ICON_PATH: Final[Path] = RESOURCE_DIR / "icons" / "succure_icon.png"
CANCEL_ICON_PATH: Final[Path] = RESOURCE_DIR / "icons" / "cancel_icon.png"
PROXY_ICON_PATH: Final[Path] = RESOURCE_DIR / "icons" / "proxy_icon.png"
SETTINGS_ICON_PATH: Final[Path] = RESOURCE_DIR / "icons" / "settings_icon.png"
CASH_ICON_PATH: Final[Path] = RESOURCE_DIR / "icons" / "cash_icon.png"
VIEV_ICON_PATH: Final[Path] = RESOURCE_DIR / "icons" / "view_icon.png"
MODULS_ICON_PATH: Final[Path] = RESOURCE_DIR / "icons" / "moduls_icon.png"
FOLDER_ICON_PATH: Final[Path] = RESOURCE_DIR / "icons" / "folder_icon.png"
SEARCH_ICON_PATH: Final[Path] = RESOURCE_DIR / "icons" / "search_icon.png"
DELETE_ICON_PATH: Final[Path] = RESOURCE_DIR / "icons" / "delete_icon.png"
NOTE_ICON_PATH: Final[Path] = RESOURCE_DIR / "icons" / "note_icon.png"
NEW_PROXY_ICON_PATH: Final[Path] = RESOURCE_DIR / "icons" / "new_proxy_icon.png"
DEVICE_ICON_PATH: Final[Path] = RESOURCE_DIR / "icons" / "device_icon.png"
START_ICON_PATH: Final[Path] = RESOURCE_DIR / "icons" / "start_icon.png"

# Другие ресурсы
SOUND_PATH: Final[Path] = RESOURCE_DIR / "sounds" / "Nuya.mp3"
FONTS_DIR: Final[Path] = RESOURCE_DIR / "fonts"
