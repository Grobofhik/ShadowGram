from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QTextEdit, QPushButton, QFrame, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt
from src import styles
from src.ui.node_editor.node_specs import NODE_SPECS

class EmptyParamsFillDialog(QDialog):
    """
    Интерактивный диалог заполнения пустых входных параметров (ссылок, текстов) 
    перед непосредственным запуском сценария на аккаунтах.
    """

    def __init__(self, empty_params_list, parent=None):
        super().__init__(parent)
        self.empty_params_list = empty_params_list # List of dicts: {node_item, param_name, param_info, current_value}
        self.inputs = {} # Maps (node_id, param_name) -> QLineEdit / QTextEdit
        
        self.setWindowTitle("⚡ Быстрое заполнение параметров сценария")
        self.setMinimumWidth(550)
        self.setMaximumHeight(650)
        self.setStyleSheet(styles.STYLESHEET)
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header info
        header_frame = QFrame()
        header_frame.setStyleSheet(f"background-color: {styles.COLOR_ACCENT_BG}; border-radius: 8px; padding: 12px;")
        h_layout = QVBoxLayout(header_frame)
        h_layout.setContentsMargins(10, 10, 10, 10)
        
        title_lbl = QLabel("🎯 Заполнение пустых полей в сценарии")
        title_lbl.setStyleSheet(f"color: {styles.COLOR_PRIMARY}; font-size: 15px; font-weight: bold;")
        h_layout.addWidget(title_lbl)

        desc_lbl = QLabel("Ниже перечислены блоки, в которых не были указаны ссылки или тексты.\nЗаполните их один раз для массового запуска по всем аккаунтам:")
        desc_lbl.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 12px;")
        desc_lbl.setWordWrap(True)
        h_layout.addWidget(desc_lbl)

        layout.addWidget(header_frame)

        # Scroll area with empty input fields
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 5, 0, 5)
        scroll_layout.setSpacing(12)

        for item in self.empty_params_list:
            node_item = item["node_item"]
            param_name = item["param_name"]
            param_info = item["param_info"]
            
            node_title = node_item.title or NODE_SPECS.get(node_item.node_type, {}).get("title", node_item.node_type)
            param_label = param_info.get("label", param_name)
            param_type = param_info.get("type", "str")

            block_frame = QFrame()
            block_frame.setStyleSheet(f"background-color: {styles.COLOR_ACCENT_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 8px; padding: 12px;")
            b_layout = QVBoxLayout(block_frame)
            b_layout.setSpacing(6)

            # Node & Parameter Title
            lbl_title = QLabel(f"<b>{node_title}</b> — <span style='color: {styles.COLOR_PRIMARY};'>{param_label}</span>")
            lbl_title.setStyleSheet(f"color: {styles.COLOR_TEXT_MAIN}; font-size: 13px;")
            b_layout.addWidget(lbl_title)

            # Input control based on type
            if param_type == "textarea":
                inp = QTextEdit()
                inp.setPlaceholderText("Введите текст...")
                inp.setMaximumHeight(80)
                inp.setStyleSheet(f"background-color: {styles.COLOR_BG}; color: {styles.COLOR_TEXT_MAIN}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 4px; padding: 6px;")
            else:
                inp = QLineEdit()
                inp.setPlaceholderText("Вставьте ссылку или значение...")
                inp.setStyleSheet(f"background-color: {styles.COLOR_BG}; color: {styles.COLOR_TEXT_MAIN}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 4px; padding: 8px;")

            b_layout.addWidget(inp)
            scroll_layout.addWidget(block_frame)
            
            self.inputs[(node_item.id, param_name)] = (inp, param_type, node_item)

        scroll_layout.addStretch(1)
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.setStyleSheet(f"background-color: {styles.COLOR_BG}; color: {styles.COLOR_TEXT_MAIN}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 6px; padding: 8px 16px;")
        btn_cancel.clicked.connect(self.reject)

        btn_apply = QPushButton("🚀 Подтвердить и запустить")
        btn_apply.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY_DARK}; color: white; font-weight: bold; border-radius: 6px; padding: 8px 18px;")
        btn_apply.clicked.connect(self.apply_values)

        btn_layout.addStretch(1)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_apply)

        layout.addLayout(btn_layout)

    def apply_values(self):
        """Сохранение заполненных в окне значений прямо в ноды холста"""
        for (node_id, param_name), (inp_control, param_type, node_item) in self.inputs.items():
            if param_type == "textarea":
                val = inp_control.toPlainText().strip()
            else:
                val = inp_control.text().strip()

            if val:
                node_item.params[param_name] = val

        self.accept()
