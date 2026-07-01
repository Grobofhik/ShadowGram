import sys
import json
from pathlib import Path
import asyncio

# Custom Event Loop Policy to suppress database closure errors from background update tasks in Hydrogram/Pyrogram
class SilencedEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    def new_event_loop(self):
        loop = super().new_event_loop()
        def handle_exception(loop, context):
            exception = context.get("exception")
            if exception and ("closed database" in str(exception) or "Cannot operate on a closed database" in str(exception)):
                # Silence background updates sqlite db close errors
                return
            loop.default_exception_handler(context)
        loop.set_exception_handler(handle_exception)
        return loop

asyncio.set_event_loop_policy(SilencedEventLoopPolicy())

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtCore import QObject, QEvent, Qt

from src.core.constants import CONFIG_FILE, CONFIG_DIR, FONTS_DIR


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
    from src.core.managers.farm_manager import init_farms
    from src import styles

    init_farms()
    init_config()

    app = QApplication(sys.argv)

    # Включаем горизонтальный скролл через Shift
    scroll_filter = ShiftScrollFilter()
    app.installEventFilter(scroll_filter)

    load_fonts()

    # Загружаем тему и применяем глобальный stylesheet
    styles.load_theme()
    app.setStyleSheet(styles.STYLESHEET)

    from src.ui.main_window import TelegramManager
    
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            s = data.get("settings", {})
            if s.get("enable_pin", False):
                stored_pin = s.get("app_pin", "")
                from PyQt6.QtWidgets import QInputDialog, QLineEdit, QMessageBox
                # Ask for PIN
                pin, ok = QInputDialog.getText(None, "Авторизация", "Введите ПИН-код:", QLineEdit.EchoMode.Password)
                if not ok or pin != stored_pin:
                    QMessageBox.critical(None, "Ошибка", "Неверный ПИН-код!")
                    sys.exit(0)
    except Exception:
        pass
        
    window = TelegramManager()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
