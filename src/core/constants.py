from pathlib import Path
from typing import Final
import json

"""
Глобальные константы и пути проекта.
Определяет:

- BASE_DIR: корневая директория проекта
- CONFIG_FILE: путь к файлу конфигурации JSON
- RESOURCE_DIR: путь к ресурсам (иконки, звуки, шрифты) с поддержкой системных путей
- ICON_PATHр, SOUND_PATH, FONTS_DIR: пямые пути к медиа-ресурсам
"""

import sys
import os

# Check if application is frozen (PyInstaller/AppImage)
IS_FROZEN: Final[bool] = getattr(sys, 'frozen', False)

if IS_FROZEN:
    # Bundle directory where resources/ is located
    if hasattr(sys, '_MEIPASS'):
        BUNDLE_DIR = Path(sys._MEIPASS).absolute()
    else:
        BUNDLE_DIR = Path(sys.executable).parent.absolute()
    
    # Check if we are running as an AppImage
    if 'APPIMAGE' in os.environ:
        # Writable data directory next to the AppImage executable
        BASE_DIR = Path(os.environ['APPIMAGE']).parent.absolute()
    else:
        # Writable data directory next to the executable
        BASE_DIR = Path(sys.executable).parent.absolute()
        
    LOCAL_RESOURCE_DIR = BUNDLE_DIR / "resources"
else:
    BASE_DIR = Path(__file__).parent.parent.parent.absolute()
    LOCAL_RESOURCE_DIR = BASE_DIR / "resources"

CONFIG_DIR: Final[Path] = BASE_DIR
CONFIG_FILE: Final[Path] = BASE_DIR / "config.json"
FARMS_DIR: Final[Path] = BASE_DIR / "farms"
ACTIVE_FARM_FILE: Final[Path] = BASE_DIR / "active_farm.txt"
AVATARS_DIR: Final[Path] = BASE_DIR / "avatars"

SYSTEM_RESOURCE_DIR: Final[Path] = Path("/usr/share/shadowgram/resources")
RESOURCE_DIR: Final[Path] = (
    LOCAL_RESOURCE_DIR if LOCAL_RESOURCE_DIR.exists() else SYSTEM_RESOURCE_DIR
)

CURRENT_THEME = "green"
try:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            CURRENT_THEME = data.get("settings", {}).get("theme", "green")
except Exception:
    pass


class ThemeIconPath:
    def __init__(self, filename: str):
        self.filename = filename

    @property
    def resolved_path(self) -> Path:
        theme_dir = RESOURCE_DIR / "icons" / CURRENT_THEME
        if not theme_dir.exists():
            return RESOURCE_DIR / "icons" / "green" / self.filename
        return theme_dir / self.filename

    def __str__(self) -> str:
        return str(self.resolved_path)

    def __fspath__(self) -> str:
        return str(self.resolved_path)

    def __repr__(self) -> str:
        return repr(self.resolved_path)

    def exists(self) -> bool:
        return self.resolved_path.exists()

    def is_file(self) -> bool:
        return self.resolved_path.is_file()

    def is_dir(self) -> bool:
        return self.resolved_path.is_dir()

    def __truediv__(self, other) -> Path:
        return self.resolved_path / other


# Иконки
ICON_PATH: Final = ThemeIconPath("GrobTyanka.png")
LOGO_PATH: Final = ThemeIconPath("GrobTyan_logo.png")
SUCCESS_ICON_PATH: Final = ThemeIconPath("succure_icon.png")
CANCEL_ICON_PATH: Final = ThemeIconPath("cancel_icon.png")
PROXY_ICON_PATH: Final = ThemeIconPath("proxy_icon.png")
SETTINGS_ICON_PATH: Final = ThemeIconPath("settings_icon.png")
CASH_ICON_PATH: Final = ThemeIconPath("cash_icon.png")
VIEV_ICON_PATH: Final = ThemeIconPath("view_icon.png")
MODULS_ICON_PATH: Final = ThemeIconPath("moduls_icon.png")
FOLDER_ICON_PATH: Final = ThemeIconPath("folder_icon.png")
SEARCH_ICON_PATH: Final = ThemeIconPath("search_icon.png")
DELETE_ICON_PATH: Final = ThemeIconPath("delete_icon.png")
NOTE_ICON_PATH: Final = ThemeIconPath("note_icon.png")
NEW_PROXY_ICON_PATH: Final = ThemeIconPath("new_proxy_icon.png")
DEVICE_ICON_PATH: Final = ThemeIconPath("device_icon.png")
START_ICON_PATH: Final = ThemeIconPath("start_icon.png")
SERVER_ICON_PATH: Final = ThemeIconPath("server_icon.png")

# Новые иконки для ServerGram UI
PING_ICON_PATH: Final = ThemeIconPath("ping_icon.png")
RELOAD_ICON_PATH: Final = ThemeIconPath("reload_icon.png")
ROCKET_ICON_PATH: Final = ThemeIconPath("rocket_icon.png")
SAVE_ICON_PATH: Final = ThemeIconPath("save_icon.png")
USERS_ICON_PATH: Final = ThemeIconPath("folder_icon.png")

# Другие ресурсы
SOUND_PATH: Final[Path] = RESOURCE_DIR / "sounds" / "Nuya.mp3"
FONTS_DIR: Final[Path] = RESOURCE_DIR / "fonts"

