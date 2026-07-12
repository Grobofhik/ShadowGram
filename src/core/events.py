from PyQt6.QtCore import QObject, pyqtSignal

class EventBus(QObject):
    """
    Глобальная шина событий для связи между потоками (в том числе asyncio) и GUI.
    """
    ai_log_message = pyqtSignal(str)
    
_event_bus = EventBus()

def get_event_bus():
    return _event_bus
