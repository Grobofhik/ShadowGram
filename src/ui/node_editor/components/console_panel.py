from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit
from src import styles

class ConsolePanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ConsoleWidget")
        self.setStyleSheet(f"""
            QFrame#ConsoleWidget {{
                background-color: {styles.COLOR_ACCENT_BG};
                border-top: 1px solid {styles.COLOR_BORDER};
            }}
        """)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 8, 15, 8)
        layout.setSpacing(5)
        
        # Заголовок
        header = QHBoxLayout()
        title = QLabel("КОНСОЛЬ ВЫПОЛНЕНИЯ")
        title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        header.addWidget(title)
        
        header.addStretch(1)
        
        btn_clear = QPushButton("Очистить консоль")
        btn_clear.setFixedSize(120, 22)
        btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #94a3b8;
                border: 1px solid #334155;
                border-radius: 3px;
                font-size: 10px;
                font-weight: bold;
                padding: 2px 6px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #ffffff;
            }
        """)
        btn_clear.clicked.connect(lambda: self.output.clear())
        header.addWidget(btn_clear)
        layout.addLayout(header)
        
        # Поле вывода терминального стиля
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet("""
            QTextEdit {
                background-color: #020617;
                color: #38bdf8;
                border: 1px solid #1e293b;
                border-radius: 4px;
                font-family: "DejaVu Sans Mono", "Courier New", monospace;
                font-size: 11px;
                line-height: 1.4;
            }
        """)
        layout.addWidget(self.output, 1)
        
    def append_log(self, text):
        # Автоматическая раскраска строк по ключевым словам
        color = "#94a3b8"
        if "успешно" in text.lower() or "✅" in text:
            color = "#10b981" # Emerald green
        elif "ошибка" in text.lower() or "❌" in text or "критическая" in text.lower():
            color = "#f43f5e" # Rose red
        elif "предупреждение" in text.lower() or "⏳" in text or "ожидание" in text.lower() or "запуск через" in text.lower():
            color = "#f59e0b" # Amber yellow
        elif "шаг" in text.lower() or "блок" in text.lower():
            color = "#38bdf8" # Sky blue
            
        formatted = f"<span style='color: {color};'>{text}</span>"
        self.output.append(formatted)
        
        # Прокрутка вниз
        v_bar = self.output.verticalScrollBar()
        v_bar.setValue(v_bar.maximum())
