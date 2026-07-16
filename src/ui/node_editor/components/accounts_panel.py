from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QLabel, QWidget
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath
import json
import os
from src import styles
from src.core.constants import CONFIG_FILE

def get_circular_pixmap(image_path, size=36):
    src = QPixmap(image_path)
    if src.isNull():
        return None
        
    target = QPixmap(size, size)
    target.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(target)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    
    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.setClipPath(path)
    
    scaled = src.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
    painter.drawPixmap(0, 0, scaled)
    painter.end()
    return target

class AccountItemWidget(QWidget):
    def __init__(self, acc_data, parent_panel, checked=False, parent=None):
        super().__init__(parent)
        self.acc_data = acc_data
        self.parent_panel = parent_panel
        self.selected = checked
        self.setFixedHeight(58)  # Optimal height without checkbox
        self.setObjectName("AccountCard")
        
        name = acc_data.get("name", "Без имени")
        phone = acc_data.get("phone", "Нет номера")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(12)
        
        # Avatar
        self.avatar = QLabel()
        self.avatar.setFixedSize(36, 36)
        self.avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Try to load real avatar
        workdir_path = acc_data.get("workdir", "")
        avatar_path = None
        if workdir_path:
            possible_jpg = os.path.join(workdir_path, "avatar.jpg")
            if os.path.exists(possible_jpg):
                avatar_path = possible_jpg
            elif os.path.isdir(workdir_path):
                for f in os.listdir(workdir_path):
                    if (f.startswith("avatar") or f.startswith("profile")) and f.lower().endswith((".jpg", ".png")):
                        avatar_path = os.path.join(workdir_path, f)
                        break
        
        pixmap = None
        if avatar_path:
            try:
                pixmap = get_circular_pixmap(avatar_path, 36)
            except Exception:
                pixmap = None
                
        if pixmap:
            self.avatar.setPixmap(pixmap)
            self.avatar.setStyleSheet("""
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 18px;
            """)
        else:
            first_char = name[0].upper() if name else "?"
            self.avatar.setText(first_char)
            colors = ["#3b82f6", "#10b981", "#8b5cf6", "#f59e0b", "#ec4899", "#14b8a6"]
            color_idx = abs(hash(name)) % len(colors)
            self.avatar.setStyleSheet(f"""
                background-color: {colors[color_idx]};
                color: #ffffff;
                font-weight: bold;
                font-size: 14px;
                border-radius: 18px;
                border: 1px solid rgba(255, 255, 255, 0.15);
            """)
            
        layout.addWidget(self.avatar)
        
        # Text details
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(0, 2, 0, 2)
        
        self.name_label = QLabel(name)
        self.name_label.setStyleSheet(f"color: {styles.COLOR_TEXT_MAIN}; font-size: 12px; font-weight: bold; background: transparent; border: none;")
        self.name_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        
        self.phone_label = QLabel(phone)
        self.phone_label.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 11px; background: transparent; border: none;")
        self.phone_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        
        text_layout.addWidget(self.name_label)
        text_layout.addWidget(self.phone_label)
        
        layout.addLayout(text_layout, 1)
        
        self.update_style()

    def update_style(self):
        # Selected color highlighting depending on Cyber Green or Modern Blue theme
        if self.selected:
            self.setStyleSheet(f"""
                QWidget#AccountCard {{
                    background-color: {styles.COLOR_PRIMARY}26; /* 15% opacity primary */
                    border: 1.5px solid {styles.COLOR_PRIMARY};
                    border-radius: 8px;
                }}
                QWidget#AccountCard:hover {{
                    background-color: {styles.COLOR_PRIMARY}3B; /* 23% opacity primary */
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QWidget#AccountCard {{
                    background-color: {styles.COLOR_BG};
                    border: 1px solid {styles.COLOR_BORDER};
                    border-radius: 8px;
                }}
                QWidget#AccountCard:hover {{
                    background-color: {styles.COLOR_HOVER_BG};
                    border-color: {styles.COLOR_BORDER_LIGHT};
                }}
            """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected = not self.selected
            self.update_style()
            self.parent_panel.on_card_clicked(self)
            event.accept()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event):
        from PyQt6.QtWidgets import QStyle, QStyleOption
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, p, self)

class AccountsPanel(QFrame):
    def __init__(self, parent_window, parent=None):
        super().__init__(parent)
        self.parent_window = parent_window
        self.setObjectName("AccountsPanel")
        self.setFixedWidth(280)  
        self.card_widgets = []
        self.setStyleSheet(f"""
            QFrame#AccountsPanel {{
                background-color: {styles.COLOR_ACCENT_BG};
                border-right: 1px solid {styles.COLOR_BORDER};
            }}
            QLabel#PanelTitle {{
                color: {styles.COLOR_TEXT_MAIN};
                font-size: 13px;
                font-weight: bold;
                padding-bottom: 6px;
            }}
            QLineEdit {{
                background-color: {styles.COLOR_BG};
                color: {styles.COLOR_TEXT_MAIN};
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 11px;
            }}
            QLineEdit:focus {{
                border-color: {styles.COLOR_PRIMARY};
            }}
            QListWidget {{
                background-color: transparent;
                border: none;
                padding: 0px;
            }}
            QListWidget::item {{
                background-color: transparent;
                border: none;
                margin-bottom: 8px;
                padding: 0px;
            }}
            QListWidget::item:hover, QListWidget::item:selected {{
                background-color: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 4px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {styles.COLOR_BORDER_LIGHT};
                min-height: 20px;
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {styles.COLOR_PRIMARY};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
            }}
            QPushButton {{
                background-color: {styles.COLOR_BG};
                color: {styles.COLOR_TEXT_MAIN};
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 6px;
                padding: 6px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {styles.COLOR_HOVER_BG};
                color: #ffffff;
                border-color: {styles.COLOR_PRIMARY};
            }}
        """)
        self.init_ui()
        self.load_accounts()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header Title
        self.title_label = QLabel("👥 Выберите аккаунты")
        self.title_label.setObjectName("PanelTitle")
        layout.addWidget(self.title_label)

        # Search box
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Поиск аккаунта...")
        self.search_box.textChanged.connect(self.filter_accounts)
        layout.addWidget(self.search_box)

        # Accounts List widget
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        layout.addWidget(self.list_widget, 1)

        # Select all / Deselect all buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        self.btn_select_all = QPushButton("Выбрать все")
        self.btn_select_all.clicked.connect(self.select_all)
        self.btn_deselect_all = QPushButton("Снять все")
        self.btn_deselect_all.clicked.connect(self.deselect_all)
        btn_layout.addWidget(self.btn_select_all)
        btn_layout.addWidget(self.btn_deselect_all)
        layout.addLayout(btn_layout)

    def load_accounts(self):
        self.list_widget.clear()
        self.card_widgets = []

        accounts = []
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                accounts = config.get("accounts", [])
        except Exception as e:
            self.parent_window.append_console_log(f"⚠️ Ошибка загрузки аккаунтов из конфигурации: {e}")

        selected_phones = {acc.get("phone") for acc in self.parent_window.selected_accounts if acc.get("phone")}

        for acc in accounts:
            phone = acc.get("phone", "")
            item = QListWidgetItem(self.list_widget)
            
            is_checked = phone in selected_phones
            widget = AccountItemWidget(acc, self, checked=is_checked)
            self.card_widgets.append(widget)
            
            item.setSizeHint(QSize(250, 58))
            self.list_widget.setItemWidget(item, widget)
            
        self.update_selected_accounts()

    def on_card_clicked(self, card_widget):
        self.update_selected_accounts()

    def update_selected_accounts(self):
        selected = []
        for card in self.card_widgets:
            if card.selected:
                selected.append(card.acc_data)
        self.parent_window.selected_accounts = selected
        self.title_label.setText(f"👥 Выбрано: {len(selected)} акк.")

    def select_all(self):
        for card in self.card_widgets:
            card.selected = True
            card.update_style()
        self.update_selected_accounts()

    def deselect_all(self):
        for card in self.card_widgets:
            card.selected = False
            card.update_style()
        self.update_selected_accounts()

    def filter_accounts(self, text):
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if widget:
                name_match = text.lower() in widget.name_label.text().lower()
                phone_match = text.lower() in widget.phone_label.text().lower()
                item.setHidden(not (name_match or phone_match))
