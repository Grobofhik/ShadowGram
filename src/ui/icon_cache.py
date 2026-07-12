from src.core.constants import *
from PyQt6.QtGui import QIcon

_CACHE = {}

def get_icon(path_str):
    path_str = str(path_str)
    if path_str not in _CACHE:
        _CACHE[path_str] = QIcon(path_str)
    return _CACHE[path_str]
