import logging
import sys
from pathlib import Path
from src.core.constants import BASE_DIR

LOG_FILE = BASE_DIR / "shadowgram.log"

class AILogHandler(logging.Handler):
    """
    Перехватывает логи, связанные с ИИ, и отправляет их в GUI через EventBus.
    """
    def emit(self, record):
        msg = self.format(record)
        # Отфильтровываем только те логи, которые интересны для отображения ИИ в интерфейсе
        if "🤖" in msg or "⚙️" in msg or "✅" in msg or "❌" in msg or "⏳" in msg or "[Фаза" in msg or "=== ИИ-СИСТЕМА" in msg or "=== ЗАПУСК" in msg:
            try:
                # Импортируем только во время выполнения, чтобы избежать циклических импортов
                # и проблем при запуске без GUI (PyQt6).
                import PyQt6.QtCore
                if PyQt6.QtCore.QCoreApplication.instance():
                    from src.core.events import get_event_bus
                    # Убираем стандартные префиксы логгера для вывода в чат
                    clean_msg = record.getMessage()
                    get_event_bus().ai_log_message.emit(clean_msg)
            except Exception:
                pass # Игнорируем ошибки при работе без GUI

def setup_logger():
    logger = logging.getLogger("ShadowGram")
    
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    ai_handler = AILogHandler()
    ai_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Для ИИ-чат хендлера не задаем форматер, так как мы берем clean_msg внутри

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.addHandler(ai_handler)

    return logger

logger = setup_logger()

# Отключаем спам от hydrogram при обрывах связи (Connection failed! Trying again...)
logging.getLogger("hydrogram").setLevel(logging.ERROR)
