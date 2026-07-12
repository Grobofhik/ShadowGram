from src.core.constants import *
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox, QPushButton, QMessageBox
from PyQt6.QtCore import Qt
from src import styles
from src.core.scheduler import global_scheduler

class ScheduleDialog(QDialog):
    def __init__(self, task_name, parent=None):
        super().__init__(parent)
        self.task_name = task_name
        self.interval_minutes = 0
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Расписание: {self.task_name}")
        self.setStyleSheet(f"background-color: {styles.COLOR_BG}; color: {styles.COLOR_TEXT_MAIN};")
        self.resize(300, 150)
        
        layout = QVBoxLayout(self)
        
        lbl = QLabel(f"Настройте интервал запуска:")
        layout.addWidget(lbl)
        
        h_layout = QHBoxLayout()
        self.spin_val = QSpinBox()
        self.spin_val.setRange(1, 1000)
        self.spin_val.setValue(1)
        
        self.combo_type = QComboBox()
        self.combo_type.addItems(["Минут", "Часов", "Дней"])
        
        h_layout.addWidget(self.spin_val)
        h_layout.addWidget(self.combo_type)
        layout.addLayout(h_layout)
        
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("Запланировать")
        self.btn_ok.setStyleSheet(styles.STYLE_BUTTON_PRIMARY)
        self.btn_ok.clicked.connect(self.on_ok)
        
        self.btn_cancel = QPushButton("Отмена")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

    def on_ok(self):
        val = self.spin_val.value()
        t = self.combo_type.currentText()
        if t == "Минут":
            self.interval_minutes = val
        elif t == "Часов":
            self.interval_minutes = val * 60
        elif t == "Дней":
            self.interval_minutes = val * 1440
            
        self.accept()
