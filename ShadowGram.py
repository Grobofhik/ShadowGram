import sys
import json
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtCore import QObject, QEvent, Qt
from src.ui.main_window import TelegramManager
from src import styles
from src.core.constants import CONFIG_FILE, CONFIG_DIR, FONTS_DIR

"""
Точка входа в приложение ShadowGram.
Функции:

- load_fonts: загрузка кастомных шрифтов из директории ресурсов
- init_config: инициализация базового файла конфигурации при первом запуске
- ShiftScrollFilter: поддержка горизонтального скролла через Shift + Wheel
- Основной блок: настройка QApplication, стилей и запуск главного окна
"""


class ShiftScrollFilter(QObject):
    """Фильтр для поддержки горизонтального скролла через Shift + Wheel"""

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Обработка событий колесика мыши с модификатором Shift"""
        if event.type() == QEvent.Type.Wheel:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                return self._handle_horizontal_scroll(obj, event)
        return super().eventFilter(obj, event)

    def _handle_horizontal_scroll(self, obj: QObject, event: QEvent) -> bool:
        """Обработка горизонтального скролла"""
        target = obj
        while target:
            if hasattr(target, "horizontalScrollBar"):
                bar = target.horizontalScrollBar()
                if bar.maximum() > 0:  # Если скроллбар активен
                    delta = event.angleDelta().y()
                    bar.setValue(bar.value() - delta)
                    return True
            target = target.parent()
        return False


def _setup_python_path() -> None:
    """Настройка Python path для импортов"""
    base_dir = Path(__file__).parent
    if str(base_dir) not in sys.path:
        sys.path.insert(0, str(base_dir))


def load_fonts() -> None:
    """Загрузка кастомных шрифтов из директории ресурсов"""
    if not FONTS_DIR.exists():
        return

    font_files = [
        f
        for f in FONTS_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in (".ttf", ".otf")
    ]

    for font_file in font_files:
        font_id = QFontDatabase.addApplicationFont(str(font_file))
        if font_id != -1:
            families = QFontDatabase.applicationFontFamilies(font_id)
            print(f"[DEBUG] Loaded font: {font_file.name} as families: {families}")


def init_config() -> None:
    """Инициализация базового файла конфигурации при первом запуске"""
    if CONFIG_FILE.exists():
        return

    default_config = {"settings": {"api_id": 0, "api_hash": ""}, "accounts": []}

    # Убедимся что директория конфига существует
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(default_config, f, indent=4, ensure_ascii=False)


def main() -> None:
    """Основная функция запуска приложения"""
    _setup_python_path()
    init_config()

    app = QApplication(sys.argv)

    # Включаем горизонтальный скролл через Shift
    scroll_filter = ShiftScrollFilter()
    app.installEventFilter(scroll_filter)

    load_fonts()
    app.setStyleSheet(styles.STYLESHEET)

    window = TelegramManager()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
