import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFrame, QScrollArea, QWidget, QGridLayout,
    QTextEdit, QGraphicsDropShadowEffect, QSizePolicy, QFileDialog
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon, QFont, QPainter, QPainterPath, QColor

from src.styles import (
    COLOR_BG, COLOR_ACCENT_BG, COLOR_PRIMARY, COLOR_BORDER, 
    COLOR_TEXT_MUTED, COLOR_HOVER_BG, FONT_NAME
)
from src.core.constants import ICON_PATH
import shutil

class ClickableLabel(QLabel):
    clicked = pyqtSignal()
    
    def mousePressEvent(self, event):
        if getattr(self, 'is_editable', False):
            self.clicked.emit()
        super().mousePressEvent(event)

class SectionFrame(QFrame):
    """Custom styled frame for sections."""
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("sectionFrame")
        self.setStyleSheet(f"""
            QFrame#sectionFrame {{
                background-color: {COLOR_ACCENT_BG};
                border: 1px solid {COLOR_BORDER};
                border-radius: 12px;
            }}
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        self.layout.setSpacing(12)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {COLOR_PRIMARY}; font-weight: bold; font-size: 14px; font-family: '{FONT_NAME}'; border: none; background: transparent;")
        self.layout.addWidget(title_label)
        
        # Shadow effect for depth
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

class LabeledInput(QWidget):
    """Reusable widget for a label and a text input."""
    def __init__(self, label_text, default_text="", read_only=False, multi_line=False, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(4)
        
        self.label = QLabel(label_text)
        self.label.setStyleSheet(f"color: {COLOR_TEXT_MUTED}; font-size: 11px; font-family: '{FONT_NAME}'; background: transparent; border: none;")
        self.layout.addWidget(self.label)
        
        self.input_style = f"""
            background-color: {COLOR_BG};
            border: 1px solid {COLOR_BORDER};
            border-radius: 6px;
            color: white;
            padding: 8px;
            font-family: '{FONT_NAME}';
        """
        
        self.readonly_style = f"""
            background-color: transparent;
            border: none;
            color: white;
            padding: 4px;
            font-family: '{FONT_NAME}';
            font-size: 14px;
        """
        
        self.is_multi = multi_line
        
        if multi_line:
            self.input_field = QTextEdit()
            self.input_field.setPlainText(default_text)
            self.input_field.setMaximumHeight(80)
        else:
            self.input_field = QLineEdit(default_text)
            
        self.layout.addWidget(self.input_field)
        self.set_edit_mode(not read_only)
        
    def set_edit_mode(self, is_editing):
        self.input_field.setReadOnly(not is_editing)
        cls_name = "QTextEdit" if self.is_multi else "QLineEdit"
        if is_editing:
            self.input_field.setStyleSheet(f"{cls_name} {{ {self.input_style} }} {cls_name}:focus {{ border: 1px solid {COLOR_PRIMARY}; }}")
        else:
            self.input_field.setStyleSheet(f"{cls_name} {{ {self.readonly_style} }}")

class ActionButton(QPushButton):
    """Styled button for quick actions."""
    def __init__(self, text, icon_name=None, primary=False, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(40)
        
        if icon_name:
            icon_path = os.path.join(ICON_PATH, f"{icon_name}.png")
            if os.path.exists(icon_path):
                self.setIcon(QIcon(icon_path))
                self.setIconSize(QSize(18, 18))
                
        bg_color = COLOR_PRIMARY if primary else COLOR_BG
        text_color = "#000000" if primary else "white"
        border_color = COLOR_PRIMARY if primary else COLOR_BORDER
        hover_bg = COLOR_PRIMARY if primary else COLOR_HOVER_BG
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 8px 12px;
                font-family: '{FONT_NAME}';
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                border: 1px solid {COLOR_PRIMARY};
                opacity: 0.8;
            }}
            QPushButton:pressed {{
                background-color: {COLOR_BG};
                color: {COLOR_PRIMARY};
            }}
        """)

class AccountProfileWindow(QDialog):
    def __init__(self, account_data, parent=None):
        super().__init__(parent)
        self.account_data = account_data
        self.setup_ui()
        self.populate_data()
        
    def setup_ui(self):
        self.setWindowTitle(f"Profile: {self.account_data.get('phone', 'Unknown')}")
        self.resize(550, 800)
        self.setStyleSheet(f"background-color: {COLOR_BG};")
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # 1. Header (Avatar + Name)
        self.setup_header()
        
        # 2. Scrollable Content Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        # Inherit scrollbar styles from main app if possible, or basic dark scrollbar
        self.scroll_area.setStyleSheet(f"""
            QScrollBar:vertical {{
                background: {COLOR_BG};
                width: 10px;
                margin: 0px 0px 0px 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLOR_BORDER};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {COLOR_PRIMARY};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        """)
        
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setContentsMargins(24, 24, 24, 24)
        self.scroll_layout.setSpacing(20)
        
        self.setup_public_info_section()
        self.setup_personal_channel_section()
        self.setup_tech_security_section()
        self.setup_quick_actions_section()
        
        self.scroll_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_widget)
        self.main_layout.addWidget(self.scroll_area)
        
    def setup_header(self):
        self.header_frame = QFrame()
        self.header_frame.setStyleSheet(f"background-color: {COLOR_ACCENT_BG}; border-bottom: 1px solid {COLOR_BORDER};")
        self.header_frame.setMinimumHeight(160)
        header_layout = QVBoxLayout(self.header_frame)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.setContentsMargins(20, 10, 20, 20)
        
        # Edit button row
        edit_row = QHBoxLayout()
        edit_row.addStretch()
        self.btn_edit = QPushButton("✏️ Edit")
        self.btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_edit.setStyleSheet(f"background: transparent; border: none; color: {COLOR_PRIMARY}; font-weight: bold; font-size: 14px;")
        self.btn_edit.clicked.connect(self.toggle_edit_mode)
        edit_row.addWidget(self.btn_edit)
        header_layout.addLayout(edit_row)
        
        # Avatar
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(90, 90)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.avatar_label.setToolTip("Click to change avatar")
        # Default avatar circle
        pixmap = QPixmap(90, 90)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(COLOR_BORDER))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, 90, 90)
        painter.end()
        # Set Avatar Pixmap
        parent_row = self.parent()
        if parent_row and hasattr(parent_row, 'avatar_label'):
            original_pixmap = parent_row.avatar_label.pixmap()
            if original_pixmap and not original_pixmap.isNull():
                self.avatar_label.setPixmap(original_pixmap.scaled(90, 90, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
            else:
                self.avatar_label.setPixmap(pixmap)
        else:
            self.avatar_label.setPixmap(pixmap)
        
        # Name
        self.name_label = QLabel("Unknown Account")
        self.name_label.setStyleSheet(f"color: white; font-size: 20px; font-weight: bold; font-family: '{FONT_NAME}'; background: transparent; border: none;")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Phone / Status
        self.status_label = QLabel("Status: Unknown")
        self.status_label.setStyleSheet(f"color: {COLOR_PRIMARY}; font-size: 12px; font-family: '{FONT_NAME}'; background: transparent; border: none;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header_layout.addWidget(self.avatar_label, alignment=Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.name_label, alignment=Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(self.header_frame)
        
    def toggle_edit_mode(self):
        self.is_editing = not getattr(self, 'is_editing', False)
        
        if self.is_editing:
            self.btn_edit.setText("✅ Save")
            self.btn_edit.setStyleSheet(f"background: transparent; border: none; color: {COLOR_PRIMARY}; font-weight: bold; font-size: 14px;")
        else:
            self.btn_edit.setText("✏️ Edit")
            self.btn_edit.setStyleSheet(f"background: transparent; border: none; color: {COLOR_PRIMARY}; font-weight: bold; font-size: 14px;")
            self.save_profile_data()
            
        self.f_username.set_edit_mode(self.is_editing)
        self.f_bio.set_edit_mode(self.is_editing)
        self.f_email.set_edit_mode(self.is_editing)
        self.f_password.set_edit_mode(self.is_editing)
        self.f_proxy.set_edit_mode(self.is_editing)
        self.f_device_model.set_edit_mode(self.is_editing)
        self.f_system_version.set_edit_mode(self.is_editing)
        self.f_app_version.set_edit_mode(self.is_editing)
        self.f_lang_code.set_edit_mode(self.is_editing)
        self.f_notes.set_edit_mode(self.is_editing)
        self.f_prompt.set_edit_mode(self.is_editing)
        self.f_api_id.set_edit_mode(self.is_editing)
        self.f_api_hash.set_edit_mode(self.is_editing)
        self.f_channel_name.set_edit_mode(self.is_editing)
        self.f_channel_link.set_edit_mode(self.is_editing)
        self.channel_avatar_label.is_editable = self.is_editing
        
    def save_profile_data(self):
        workdir = self.account_data.get("workdir")
        if not workdir: return
        
        from src.core.constants import CONFIG_FILE
        from src.core.managers import account_manager
        
        # Save profile info
        account_manager.update_account_profile_data(
            CONFIG_FILE,
            workdir,
            bio=self.f_bio.input_field.toPlainText().strip() or None,
            username=self.f_username.input_field.text().strip() or None,
            email=self.f_email.input_field.text().strip() or None,
            password=self.f_password.input_field.text().strip() or None,
            channel_name=self.f_channel_name.input_field.text().strip() or None,
            channel_link=self.f_channel_link.input_field.text().strip() or None
        )
        
        # Save tech info
        account_manager.update_proxy(CONFIG_FILE, workdir, self.f_proxy.input_field.text().strip() or None)
        
        # Save hardware profile
        hw_profile = {
            "device_model": self.f_device_model.input_field.text().strip(),
            "system_version": self.f_system_version.input_field.text().strip(),
            "app_version": self.f_app_version.input_field.text().strip(),
            "lang_code": self.f_lang_code.input_field.text().strip()
        }
        account_manager.update_hardware_profile(CONFIG_FILE, workdir, hw_profile)
        
        account_manager.update_notes(CONFIG_FILE, workdir, self.f_notes.input_field.toPlainText().strip() or None)
        account_manager.update_prompt(CONFIG_FILE, workdir, self.f_prompt.input_field.toPlainText().strip() or None)
        account_manager.update_api_credentials(
            CONFIG_FILE, 
            workdir, 
            self.f_api_id.input_field.text().strip() or None, 
            self.f_api_hash.input_field.text().strip() or None
        )

    def setup_public_info_section(self):
        section = SectionFrame("Public Profile Info")
        
        self.f_username = LabeledInput("Username (@)", "", read_only=True)
        self.f_bio = LabeledInput("Bio (Description)", "", multi_line=True, read_only=True)
        self.f_email = LabeledInput("Recovery Email (2FA)", "", read_only=True)
        self.f_password = LabeledInput("Cloud Password (2FA)", "", read_only=True)
        
        row1 = QHBoxLayout()
        row1.addWidget(self.f_username)
        row1.addWidget(self.f_email)
        
        section.layout.addLayout(row1)
        section.layout.addWidget(self.f_password)
        section.layout.addWidget(self.f_bio)
        
        self.scroll_layout.addWidget(section)

    def setup_tech_security_section(self):
        section = SectionFrame("Tech & Security Data")
        
        self.f_api_id = LabeledInput("API ID (Telegram app)", "", read_only=True)
        self.f_api_hash = LabeledInput("API Hash (Telegram app)", "", read_only=True)
        
        row_api = QHBoxLayout()
        row_api.addWidget(self.f_api_id)
        row_api.addWidget(self.f_api_hash)
        
        self.f_proxy = LabeledInput("Proxy String (IP:PORT:USER:PASS)", "", read_only=True)
        
        self.f_device_model = LabeledInput("Device Model", "", read_only=True)
        self.f_system_version = LabeledInput("OS Version", "", read_only=True)
        self.f_app_version = LabeledInput("App Version", "", read_only=True)
        self.f_lang_code = LabeledInput("Language", "", read_only=True)
        
        row_hw1 = QHBoxLayout()
        row_hw1.addWidget(self.f_device_model)
        row_hw1.addWidget(self.f_system_version)
        
        row_hw2 = QHBoxLayout()
        row_hw2.addWidget(self.f_app_version)
        row_hw2.addWidget(self.f_lang_code)
        
        self.f_notes = LabeledInput("Private Notes", "", multi_line=True, read_only=True)
        self.f_prompt = LabeledInput("AI Prompt for Auto-reply", "", multi_line=True, read_only=True)
        
        section.layout.addLayout(row_api)
        section.layout.addWidget(self.f_proxy)
        section.layout.addLayout(row_hw1)
        section.layout.addLayout(row_hw2)
        section.layout.addWidget(self.f_notes)
        section.layout.addWidget(self.f_prompt)
        
        self.scroll_layout.addWidget(section)

    def setup_personal_channel_section(self):
        section = SectionFrame("Личный канал")
        
        row = QHBoxLayout()
        
        # Channel Avatar
        self.channel_avatar_label = ClickableLabel()
        self.channel_avatar_label.setFixedSize(60, 60)
        self.channel_avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.channel_avatar_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.channel_avatar_label.setToolTip("Click to change channel avatar (only in Edit mode)")
        self.channel_avatar_label.is_editable = False
        self.channel_avatar_label.clicked.connect(self.change_channel_avatar)
        
        self.update_channel_avatar_pixmap()
        
        row.addWidget(self.channel_avatar_label)
        
        # Fields
        fields_layout = QVBoxLayout()
        self.f_channel_name = LabeledInput("Название канала", "", read_only=True)
        self.f_channel_link = LabeledInput("Ссылка", "", read_only=True)
        
        fields_layout.addWidget(self.f_channel_name)
        fields_layout.addWidget(self.f_channel_link)
        
        row.addLayout(fields_layout)
        section.layout.addLayout(row)
        
        self.scroll_layout.addWidget(section)

    def update_channel_avatar_pixmap(self):
        workdir = self.account_data.get("workdir")
        pixmap = None
        if workdir:
            avatar_path = os.path.join(workdir, "channel_avatar.jpg")
            if os.path.exists(avatar_path):
                pixmap = QPixmap(avatar_path)
        
        if not pixmap or pixmap.isNull():
            pixmap = QPixmap(60, 60)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor(COLOR_BORDER))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(0, 0, 60, 60)
            painter.end()
        else:
            scaled = pixmap.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            pixmap = QPixmap(60, 60)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            path = QPainterPath()
            path.addEllipse(0, 0, 60, 60)
            painter.setClipPath(path)
            x = (60 - scaled.width()) // 2
            y = (60 - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            painter.end()
            
        self.channel_avatar_label.setPixmap(pixmap)

    def change_channel_avatar(self):
        workdir = self.account_data.get("workdir")
        if not workdir: return
        file_path, _ = QFileDialog.getOpenFileName(self, "Выбрать аватар канала", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            dest_path = os.path.join(workdir, "channel_avatar.jpg")
            try:
                shutil.copy2(file_path, dest_path)
                self.update_channel_avatar_pixmap()
            except Exception as e:
                pass

    def setup_quick_actions_section(self):
        section = SectionFrame("Quick Actions Hub")
        
        grid = QGridLayout()
        grid.setSpacing(10)
        
        self.btn_start = ActionButton("Start Telegram", primary=True)
        self.btn_stop = ActionButton("Stop Telegram")
        self.btn_check = ActionButton("Check Session Validity")
        self.btn_clear = ActionButton("Clear Cache (tdata)")
        self.btn_avatar = ActionButton("Generate AI Avatar")
        self.btn_bio = ActionButton("Generate Random Bio")
        self.btn_export = ActionButton("Export Session (ZIP)")
        
        grid.addWidget(self.btn_start, 0, 0)
        grid.addWidget(self.btn_stop, 0, 1)
        grid.addWidget(self.btn_check, 1, 0, 1, 2)
        grid.addWidget(self.btn_clear, 2, 0)
        grid.addWidget(self.btn_export, 2, 1)
        grid.addWidget(self.btn_avatar, 3, 0)
        grid.addWidget(self.btn_bio, 3, 1)
        
        # Connect buttons to parent (TelegramAccountRow) methods
        parent_row = self.parent()
        if parent_row:
            self.btn_start.clicked.connect(parent_row.toggle_telegram)
            self.btn_check.clicked.connect(parent_row.run_session_check)
            self.btn_clear.clicked.connect(parent_row.clear_account_cache)
            # Other buttons can be wired later as functionality is implemented
        
        section.layout.addLayout(grid)
        self.scroll_layout.addWidget(section)

    def populate_data(self):
        # Basic fields
        first = self.account_data.get('first_name')
        last = self.account_data.get('last_name')
        if first or last:
            name_text = f"{first or ''} {last or ''}".strip()
        else:
            name_text = self.account_data.get('phone', 'Unknown')
        self.name_label.setText(name_text)
        
        # Proxy
        proxy = self.account_data.get('proxy_url', '')
        self.f_proxy.input_field.setText(proxy)
        
        # API credentials
        api_id = self.account_data.get('api_id', '')
        api_hash = self.account_data.get('api_hash', '')
        self.f_api_id.input_field.setText(str(api_id))
        self.f_api_hash.input_field.setText(api_hash)
        
        # Setup Hardware profile
        from src.core.constants import CONFIG_FILE
        from src.core.managers.account_manager import get_hardware_profile
        hw_profile = get_hardware_profile(CONFIG_FILE, self.account_data.get('workdir', ''))
        
        self.f_device_model.input_field.setText(hw_profile.get('device_model', 'PC 64bit'))
        self.f_system_version.input_field.setText(hw_profile.get('system_version', 'Windows 10'))
        self.f_app_version.input_field.setText(hw_profile.get('app_version', '4.8.4 x64'))
        self.f_lang_code.input_field.setText(hw_profile.get('lang_code', 'en'))

        # Notes
        self.f_notes.input_field.setPlainText(self.account_data.get('notes', ''))
        
        # Prompts
        self.f_prompt.input_field.setPlainText(self.account_data.get('ai_prompt', ''))
        
        # New fields (Username, Bio, Email, 2FA) might not exist yet, set defaults if available
        self.f_username.input_field.setText(self.account_data.get('username', ''))
        self.f_email.input_field.setText(self.account_data.get('email', ''))
        self.f_password.input_field.setText(self.account_data.get('password', ''))
        self.f_bio.input_field.setPlainText(self.account_data.get('bio', ''))
        self.f_channel_name.input_field.setText(self.account_data.get('channel_name', ''))
        self.f_channel_link.input_field.setText(self.account_data.get('channel_link', ''))
