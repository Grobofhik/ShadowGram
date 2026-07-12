from src.core.constants import *
from PyQt6.QtGui import QIcon
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

class AvatarLabel(ClickableLabel):
    image_dropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if getattr(self, 'is_editable', False):
            if event.mimeData().hasUrls():
                urls = event.mimeData().urls()
                if urls and urls[0].isLocalFile():
                    path = urls[0].toLocalFile().lower()
                    if path.endswith(('.png', '.jpg', '.jpeg')):
                        event.acceptProposedAction()
                        return
        event.ignore()

    def dragMoveEvent(self, event):
        if getattr(self, 'is_editable', False):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if getattr(self, 'is_editable', False):
            urls = event.mimeData().urls()
            if urls and urls[0].isLocalFile():
                file_path = urls[0].toLocalFile()
                self.image_dropped.emit(file_path)
                event.acceptProposedAction()

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
        self.btn_edit = QPushButton("Edit")
        self.btn_edit.setIcon(QIcon(str(NOTE_ICON_PATH)))
        self.btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_edit.setStyleSheet(f"background: transparent; border: none; color: {COLOR_PRIMARY}; font-weight: bold; font-size: 14px;")
        self.btn_edit.clicked.connect(self.toggle_edit_mode)
        edit_row.addWidget(self.btn_edit)
        header_layout.addLayout(edit_row)
        
        # Avatar
        self.avatar_label = AvatarLabel()
        self.avatar_label.setFixedSize(90, 90)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.avatar_label.setToolTip("Click or drag image to change avatar (only in Edit mode)")
        self.avatar_label.is_editable = False
        self.avatar_label.clicked.connect(self.change_main_avatar)
        self.avatar_label.image_dropped.connect(self.set_new_avatar)
        
        self.update_main_avatar_pixmap()
        
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
            self.btn_edit.setText("Save")
            self.btn_edit.setStyleSheet(f"background: transparent; border: none; color: {COLOR_PRIMARY}; font-weight: bold; font-size: 14px;")
        else:
            self.btn_edit.setText("Edit")
            self.btn_edit.setStyleSheet(f"background: transparent; border: none; color: {COLOR_PRIMARY}; font-weight: bold; font-size: 14px;")
            self.save_profile_data()
            
        self.f_first_name.set_edit_mode(self.is_editing)
        self.f_last_name.set_edit_mode(self.is_editing)
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
        self.avatar_label.is_editable = self.is_editing
        
        if hasattr(self, 'btn_generate_api'):
            self.btn_generate_api.setVisible(self.is_editing)
        
    def save_profile_data(self):
        workdir = self.account_data.get("workdir")
        if not workdir: return
        
        from src.core.constants import CONFIG_FILE
        from src.core.managers import account_manager
        
        # Save profile info
        account_manager.update_account_profile_data(
            CONFIG_FILE,
            workdir,
            first_name=self.f_first_name.input_field.text().strip() or None,
            last_name=self.f_last_name.input_field.text().strip() or None,
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
        
        self.f_first_name = LabeledInput("Имя (First Name)", "", read_only=True)
        self.f_last_name = LabeledInput("Фамилия (Last Name)", "", read_only=True)
        self.f_username = LabeledInput("Username (@)", "", read_only=True)
        self.f_bio = LabeledInput("Bio (Description)", "", multi_line=True, read_only=True)
        self.f_email = LabeledInput("Recovery Email (2FA)", "", read_only=True)
        self.f_password = LabeledInput("Cloud Password (2FA)", "", read_only=True)
        
        row_names = QHBoxLayout()
        row_names.addWidget(self.f_first_name)
        row_names.addWidget(self.f_last_name)
        
        row1 = QHBoxLayout()
        row1.addWidget(self.f_username)
        row1.addWidget(self.f_email)
        
        section.layout.addLayout(row_names)
        section.layout.addLayout(row1)
        section.layout.addWidget(self.f_password)
        section.layout.addWidget(self.f_bio)
        
        self.scroll_layout.addWidget(section)

    def setup_tech_security_section(self):
        section = SectionFrame("Tech & Security Data")
        
        self.f_api_id = LabeledInput("API ID (Telegram app)", "", read_only=True)
        self.f_api_hash = LabeledInput("API Hash (Telegram app)", "", read_only=True)
        
        self.btn_generate_api = QPushButton("Auto API")
        self.btn_generate_api.setIcon(QIcon(str(REFRESH_ICON_PATH)))
        self.btn_generate_api.setToolTip("Сгенерировать случайные ключи официального приложения")
        self.btn_generate_api.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_generate_api.setFixedHeight(35)
        self.btn_generate_api.setStyleSheet(f"background-color: {COLOR_BG}; border: 1px solid {COLOR_BORDER}; border-radius: 6px; font-weight: bold;")
        self.btn_generate_api.clicked.connect(self.generate_api_keys)
        self.btn_generate_api.setVisible(False)
        
        row_api = QHBoxLayout()
        row_api.addWidget(self.f_api_id)
        row_api.addWidget(self.f_api_hash)
        row_api.addWidget(self.btn_generate_api)
        
        self.f_proxy = LabeledInput("Proxy String (IP:PORT:USER:PASS)", "", read_only=True)
        self.f_privacy_guard = LabeledInput("Privacy Guard", "", read_only=True)
        
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
        
        row_proxy = QHBoxLayout()
        row_proxy.addWidget(self.f_proxy)
        row_proxy.addWidget(self.f_privacy_guard)
        section.layout.addLayout(row_proxy)
        
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

    def generate_api_keys(self):
        from src.core.managers.api_manager import get_dynamic_api_credentials
        import time
        seed = str(time.time())
        creds = get_dynamic_api_credentials(seed)
        self.f_api_id.input_field.setText(str(creds['api_id']))
        self.f_api_hash.input_field.setText(creds['api_hash'])

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

    def update_main_avatar_pixmap(self):
        workdir = self.account_data.get("workdir")
        pixmap = None
        if workdir:
            avatar_path = os.path.join(workdir, "avatar.jpg")
            if os.path.exists(avatar_path):
                pixmap = QPixmap(avatar_path)
        
        if not pixmap or pixmap.isNull():
            parent_row = self.parent()
            if parent_row and hasattr(parent_row, 'avatar_label'):
                original_pixmap = parent_row.avatar_label.pixmap()
                if original_pixmap and not original_pixmap.isNull():
                    pixmap = original_pixmap

        if not pixmap or pixmap.isNull():
            pixmap = QPixmap(90, 90)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor(COLOR_BORDER))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(0, 0, 90, 90)
            painter.end()
        else:
            scaled = pixmap.scaled(90, 90, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            pixmap = QPixmap(90, 90)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            path = QPainterPath()
            path.addEllipse(0, 0, 90, 90)
            painter.setClipPath(path)
            x = (90 - scaled.width()) // 2
            y = (90 - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            painter.end()
            
        self.avatar_label.setPixmap(pixmap)
        self.update_header_gradient(pixmap)
        
        parent_row = self.parent()
        if parent_row and hasattr(parent_row, 'update_avatar'):
            parent_row.update_avatar()

    def update_header_gradient(self, pixmap):
        if not hasattr(self, 'header_frame'):
            return
        if not pixmap or pixmap.isNull():
            gradient = f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {COLOR_ACCENT_BG}, stop:1 {COLOR_BG})"
        else:
            image = pixmap.toImage()
            if image.isNull():
                gradient = f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {COLOR_ACCENT_BG}, stop:1 {COLOR_BG})"
            else:
                scaled = image.scaled(2, 2, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                c1 = QColor(scaled.pixelColor(0, 0))
                c2 = QColor(scaled.pixelColor(1, 1))
                
                h1, s1, l1, _ = c1.getHsl()
                h2, s2, l2, _ = c2.getHsl()
                
                # Dark premium theme HSL constraints
                l1 = max(15, min(l1, 35))
                l2 = max(10, min(l2, 25))
                
                c1.setHsl(h1, s1, l1)
                c2.setHsl(h2, s2, l2)
                
                gradient = f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {c1.name()}, stop:1 {c2.name()})"
                
        self.header_frame.setStyleSheet(f"background-color: {gradient}; border-bottom: 1px solid {COLOR_BORDER};")

    def change_main_avatar(self):
        workdir = self.account_data.get("workdir")
        if not workdir: return
        file_path, _ = QFileDialog.getOpenFileName(self, "Выбрать аватар", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.set_new_avatar(file_path)

    def set_new_avatar(self, file_path):
        workdir = self.account_data.get("workdir")
        if not workdir: return
        dest_path = os.path.join(workdir, "avatar.jpg")
        try:
            shutil.copy2(file_path, dest_path)
            self.update_main_avatar_pixmap()
            
            # Start background upload
            from PyQt6.QtCore import QThread, pyqtSignal
            import asyncio
            from src.modules.plugins.set_avatar import SetAvatarPlugin
            
            class AvatarUploadThread(QThread):
                finished_signal = pyqtSignal(bool, str)
                
                def __init__(self, acc_data, photo_path):
                    super().__init__()
                    self.acc_data = acc_data
                    self.photo_path = photo_path
                    self.logs = []
                    
                def log_cb(self, msg):
                    self.logs.append(msg)
                    
                def run(self):
                    async def do_upload():
                        plugin = SetAvatarPlugin(
                            account_data=self.acc_data,
                            api_id=str(self.acc_data.get("api_id", "")),
                            api_hash=self.acc_data.get("api_hash", ""),
                            log_callback=self.log_cb
                        )
                        # We don't want global locks to delay avatar set from UI
                        await plugin.run(photo_path=self.photo_path)
                        
                    asyncio.run(do_upload())
                    success = any("успешно" in msg for msg in self.logs)
                    self.finished_signal.emit(success, "\\n".join(self.logs))
                    
            self.upload_thread = AvatarUploadThread(self.account_data, dest_path)
            self.status_label.setText("Status:  Установка аватарки в Telegram...")
            self.status_label.setStyleSheet(f"color: #fbc02d; font-size: 12px; font-weight: bold; font-family: '{FONT_NAME}'; background: transparent; border: none;")
            
            def on_finished(success, msgs):
                if success:
                    self.status_label.setText("Status:  Аватарка установлена!")
                    self.status_label.setStyleSheet(f"color: #00e676; font-size: 12px; font-weight: bold; font-family: '{FONT_NAME}'; background: transparent; border: none;")
                else:
                    self.status_label.setText("Status:  Ошибка установки")
                    self.status_label.setStyleSheet(f"color: #ff5252; font-size: 12px; font-weight: bold; font-family: '{FONT_NAME}'; background: transparent; border: none;")
                    
            self.upload_thread.finished_signal.connect(on_finished)
            self.upload_thread.start()
            
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
        self.btn_bio = ActionButton("Generate Random Bio")
        self.btn_export = ActionButton("Export Session (ZIP)")
        
        grid.addWidget(self.btn_start, 0, 0)
        grid.addWidget(self.btn_stop, 0, 1)
        grid.addWidget(self.btn_check, 1, 0, 1, 2)
        grid.addWidget(self.btn_clear, 2, 0)
        grid.addWidget(self.btn_export, 2, 1)
        grid.addWidget(self.btn_bio, 3, 0, 1, 2)
        
        # Connect buttons to parent (TelegramAccountRow) methods
        parent_row = self.parent()
        if parent_row:
            self.btn_start.clicked.connect(parent_row.toggle_telegram)
            self.btn_check.clicked.connect(parent_row.run_session_check)
            self.btn_clear.clicked.connect(parent_row.clear_account_cache)
            # Other buttons can be wired later as functionality is implemented
            
        self.btn_bio.clicked.connect(self.generate_random_bio)
        
        section.layout.addLayout(grid)
        self.scroll_layout.addWidget(section)

    def generate_random_bio(self):
        import random
        bios = [
            "Just living life", "Crypto enthusiast", "Music lover", 
            "Traveler & Dreamer", "Tech geek", "Coffee addict", 
            "Always learning", "Making things happen", "Future billionaire", 
            "Software engineer", "Digital artist", "Fitness & Health",
            "Exploring the world, one city at a time", "Invest in yourself",
            "Simplicity is the ultimate sophistication", "Stay hungry, stay foolish"
        ]
        
        chosen_bio = random.choice(bios)
        self.f_bio.input_field.setPlainText(chosen_bio)
        
        from src.core.managers import account_manager
        from src.core.constants import CONFIG_FILE
        account_manager.update_account_profile_data(CONFIG_FILE, self.account_data["workdir"], bio=chosen_bio)
        self._sync_to_telegram({"bio": chosen_bio})

    def _sync_to_telegram(self, fields):
        if "bio" in fields:
            bio_val = fields["bio"]
            from PyQt6.QtCore import QThread, pyqtSignal
            import asyncio
            from src.modules.plugins.set_bio import SetBioPlugin
            
            class BioUploadThread(QThread):
                finished_signal = pyqtSignal(bool, str)
                
                def __init__(self, acc_data, target_bio):
                    super().__init__()
                    self.acc_data = acc_data
                    self.target_bio = target_bio
                    self.logs = []
                    
                def log_cb(self, msg):
                    self.logs.append(msg)
                    
                def run(self):
                    async def do_sync():
                        plugin = SetBioPlugin(
                            account_data=self.acc_data,
                            api_id=str(self.acc_data.get("api_id", "")),
                            api_hash=self.acc_data.get("api_hash", ""),
                            log_callback=self.log_cb
                        )
                        # Pass workdir so the plugin knows which account is running
                        plugin.workdir = self.acc_data.get("workdir")
                        await plugin.run(bios_text=self.target_bio)
                        
                    asyncio.run(do_sync())
                    success = any("успешно" in msg.lower() for msg in self.logs)
                    self.finished_signal.emit(success, "\n".join(self.logs))
                    
            self.bio_sync_thread = BioUploadThread(self.account_data, bio_val)
            self.status_label.setText("Status:  Синхронизация био с Telegram...")
            self.status_label.setStyleSheet(f"color: #fbc02d; font-size: 12px; font-weight: bold; font-family: '{FONT_NAME}'; background: transparent; border: none;")
            
            def on_finished(success, msgs):
                if success:
                    self.status_label.setText("Status:  Био синхронизировано!")
                    self.status_label.setStyleSheet(f"color: #00e676; font-size: 12px; font-weight: bold; font-family: '{FONT_NAME}'; background: transparent; border: none;")
                else:
                    self.status_label.setText("Status:  Ошибка синхронизации био")
                    self.status_label.setStyleSheet(f"color: #ff5252; font-size: 12px; font-weight: bold; font-family: '{FONT_NAME}'; background: transparent; border: none;")
                    
            self.bio_sync_thread.finished_signal.connect(on_finished)
            self.bio_sync_thread.start()

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
        # API & Hardware
        acc = self.account_data
        self.f_api_id.input_field.setText(str(acc.get('api_id', '')))
        self.f_api_hash.input_field.setText(acc.get('api_hash', ''))
        self.f_proxy.input_field.setText(acc.get('proxy_url', ''))
        self.f_privacy_guard.input_field.setText("АКТИВЕН"if acc.get("privacy_guard") else "УЯЗВИМ")
        
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
        
        # Status
        workdir = self.account_data.get('workdir')
        from src.ui.account_row import TelegramAccountRow
        if workdir in TelegramAccountRow.status_cache:
            self.status_label.setText(f"Status: {TelegramAccountRow.status_cache[workdir]}")
        
        # New fields (Username, Bio, Email, 2FA) might not exist yet, set defaults if available
        self.f_first_name.input_field.setText(self.account_data.get('first_name', ''))
        self.f_last_name.input_field.setText(self.account_data.get('last_name', ''))
        self.f_username.input_field.setText(self.account_data.get('username', ''))
        self.f_email.input_field.setText(self.account_data.get('email', ''))
        self.f_password.input_field.setText(self.account_data.get('password', ''))
        self.f_bio.input_field.setPlainText(self.account_data.get('bio', ''))
        self.f_channel_name.input_field.setText(self.account_data.get('channel_name', ''))
        self.f_channel_link.input_field.setText(self.account_data.get('channel_link', ''))
