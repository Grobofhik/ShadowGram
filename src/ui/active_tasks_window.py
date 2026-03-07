from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QTextEdit, QPushButton, QHBoxLayout, QLabel
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QIcon
from src.modules_styles import MODULES_STYLESHEET
from src.core.constants import CANCEL_ICON_PATH

"""
Окно активных задач автоматизации.
Добавлена возможность принудительной остановки задач.
Функции:

- stop_requested: сигнал для ядра об остановке задачи
- add_task_tab: создание вкладки с кнопкой остановки
"""

class ActiveTasksWindow(QWidget):
    stop_requested = pyqtSignal(str) # Передает task_id

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ShadowGram - Active Tasks")
        self.resize(800, 600)
        self.setStyleSheet(MODULES_STYLESHEET)
        
        self.tabs = {} # { task_id: { "log": QTextEdit, "btn": QPushButton } }
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        header = QHBoxLayout()
        header.addWidget(QLabel("Мониторинг запущенных модулей", objectName="SectionTitle"))
        header.addStretch()
        
        btn_clear = QPushButton("Очистить закрытые")
        btn_clear.setFixedWidth(180)
        btn_clear.clicked.connect(self.clear_finished_tabs)
        header.addWidget(btn_clear)
        layout.addLayout(header)

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        layout.addWidget(self.tab_widget)

    def add_task_tab(self, task_id, name):
        """Создает новую вкладку для задачи с кнопкой остановки"""
        if task_id not in self.tabs:
            container = QWidget()
            tab_layout = QVBoxLayout(container)
            
            # Контрольная панель вкладки
            controls = QHBoxLayout()
            status_label = QLabel(f"Статус: Выполняется")
            status_label.setStyleSheet("color: #00e676; font-weight: bold;")
            controls.addWidget(status_label)
            controls.addStretch()
            
            btn_stop = QPushButton(" ОСТАНОВИТЬ")
            btn_stop.setIcon(QIcon(str(CANCEL_ICON_PATH)))
            btn_stop.setIconSize(QSize(20, 20))
            btn_stop.setObjectName("DeleteBtn") # Используем красный стиль
            btn_stop.setFixedWidth(160)
            btn_stop.clicked.connect(lambda: self.stop_requested.emit(task_id))
            controls.addWidget(btn_stop)
            tab_layout.addLayout(controls)
            
            log_output = QTextEdit()
            log_output.setObjectName("LogOutput")
            log_output.setReadOnly(True)
            tab_layout.addWidget(log_output)
            
            index = self.tab_widget.addTab(container, name)
            self.tabs[task_id] = {"log": log_output, "btn": btn_stop, "status": status_label}
            self.tab_widget.setCurrentIndex(index)
        return self.tabs[task_id]["log"]

    def append_log(self, task_id, text):
        if task_id in self.tabs:
            self.tabs[task_id]["log"].append(text)
            v_bar = self.tabs[task_id]["log"].verticalScrollBar()
            v_bar.setValue(v_bar.maximum())
            
            if "Задача завершена" in text or "Критическая ошибка" in text or "остановлена" in text or "Сессия задач завершена." in text or "Все задачи завершены!" in text:
                self.tabs[task_id]["status"].setText("Статус: Завершено")
                self.tabs[task_id]["status"].setStyleSheet("color: #888;")
                self.tabs[task_id]["btn"].setEnabled(False)

    def close_tab(self, index):
        widget = self.tab_widget.widget(index)
        for tid, data in list(self.tabs.items()):
            if data["log"].parent() == widget or data["log"].parentWidget() == widget:
                # Если задача еще работает, просим остановить перед закрытием вкладки
                self.stop_requested.emit(tid)
                del self.tabs[tid]
                break
        self.tab_widget.removeTab(index)

    def clear_finished_tabs(self):
        for i in range(self.tab_widget.count() - 1, -1, -1):
            widget = self.tab_widget.widget(i)
            is_active = False
            for tid, data in self.tabs.items():
                if (data["log"].parent() == widget or data["log"].parentWidget() == widget) and data["btn"].isEnabled():
                    is_active = True
                    break
            if not is_active:
                self.close_tab(i)