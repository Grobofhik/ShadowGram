from src.core.constants import *
from PyQt6.QtGui import QIcon
from src.ui.icon_cache import get_icon
import os
import shutil
import json
import asyncio
import random
from pathlib import Path
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QLineEdit, QTextEdit, 
                             QFrame, QFileDialog, QMessageBox, QScrollArea, QAbstractButton, QCheckBox, QSlider, QGridLayout, QDialog,
                             QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QPainterPath, QColor, QPen
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QSize, pyqtProperty, QEasingCurve, QPropertyAnimation
from src.core.managers import proxy_manager, farm_manager, config_manager, hw_manager, process_manager, account_manager
from src.core.constants import CONFIG_FILE, ROCKET_ICON_PATH, FOLDER_ICON_PATH, SUCCESS_ICON_PATH, CANCEL_ICON_PATH
from src.modules.plugins.smart_warmer import SmartWarmerPlugin
from src.modules.plugins.smart_commenter import SmartCommenterPlugin
from hydrogram import Client
from src import styles

def resolve_chat_id(bound_channel: str):
    if not bound_channel:
        return None
    val = bound_channel.strip()
    if val.startswith("id:"):
        val = val[3:]
    try:
        return int(val)
    except ValueError:
        pass
    
    if "t.me/+" in val or "t.me/joinchat/" in val:
        return val
        
    if "t.me/" in val:
        parts = val.split("t.me/")
        if len(parts) > 1:
            username = parts[1].strip().split("/")[0]
            if not username.startswith("@"):
                username = "@" + username
            return username

    if not val.startswith("@") and not val.startswith("+") and not val.startswith("https://"):
        val = "@" + val
        
    return val

class DragDropLabel(QLabel):
    fileDropped = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._default_style = ""
        self._is_drag_over = False

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    if path.lower().endswith(('.png', '.jpg', '.jpeg')):
                        event.acceptProposedAction()
                        self._is_drag_over = True
                        self.update_drag_style()
                        return
        event.ignore()

    def dragLeaveEvent(self, event):
        self._is_drag_over = False
        self.restore_style()
        event.accept()

    def dropEvent(self, event):
        self._is_drag_over = False
        self.restore_style()
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    if path.lower().endswith(('.png', '.jpg', '.jpeg')):
                        event.acceptProposedAction()
                        self.fileDropped.emit(path)
                        return
        event.ignore()

    def setStyleSheet(self, style):
        if not self._is_drag_over:
            self._default_style = style
        super().setStyleSheet(style)

    def update_drag_style(self):
        drag_style = f"border: 2px dashed {styles.COLOR_PRIMARY}; border-radius: 55px; background-color: {styles.COLOR_HOVER_BG};"
        super().setStyleSheet(drag_style)

    def restore_style(self):
        super().setStyleSheet(self._default_style)


class AvatarGalleryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Галерея аватаров проекта")
        self.setFixedSize(500, 420)
        self.selected_path = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        title = QLabel("Выберите аватарку из папки /avatars:")
        title.setStyleSheet("font-weight: bold; font-size: 13px; color: #FFFFFF;")
        layout.addWidget(title)

        # Scroll area for grid of images
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"QScrollArea {{ border: 1px solid {styles.COLOR_BORDER}; border-radius: 8px; background-color: {styles.COLOR_BG}; }}")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet(f"background-color: {styles.COLOR_BG};")
        scroll_layout = QGridLayout(scroll_content)
        scroll_layout.setSpacing(12)
        scroll_layout.setContentsMargins(12, 12, 12, 12)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Scan folder
        from src.core.constants import BASE_DIR
        avatars_dir = BASE_DIR / "avatars"
        avatars_dir.mkdir(parents=True, exist_ok=True)
        
        images = [
            f for f in avatars_dir.iterdir()
            if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg")
        ]

        # Populate grid
        self.buttons = []
        if not images:
            no_img_lbl = QLabel("В папке /avatars/ нет изображений.\nЗакиньте туда аватарки (.png, .jpg, .jpeg) в корне проекта.")
            no_img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_img_lbl.setStyleSheet("color: #888888; font-size: 12px;")
            scroll_layout.addWidget(no_img_lbl, 0, 0)
        else:
            row, col = 0, 0
            cols_limit = 4
            for img_path in images:
                btn = QPushButton()
                btn.setFixedSize(95, 95)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                
                # Load image
                pix = QPixmap(str(img_path))
                if not pix.isNull():
                    scaled_pix = pix.scaled(90, 90, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                    
                    # Rounding
                    render_size = 90
                    rounded_pix = QPixmap(render_size, render_size)
                    rounded_pix.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(rounded_pix)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    path = QPainterPath()
                    path.addEllipse(0, 0, render_size, render_size)
                    painter.setClipPath(path)
                    painter.drawPixmap(0, 0, scaled_pix)
                    painter.end()
                    
                    btn.setIcon(QIcon(rounded_pix))
                    btn.setIconSize(QSize(90, 90))
                
                # Style button
                btn.setStyleSheet(f"""
                    QPushButton {{
                        border: 2px solid {styles.COLOR_BORDER};
                        border-radius: 47px;
                        background-color: transparent;
                    }}
                    QPushButton:hover {{
                        border: 2px solid {styles.COLOR_PRIMARY};
                    }}
                """)
                
                btn.setProperty("image_path", str(img_path))
                btn.clicked.connect(self.on_image_selected)
                
                scroll_layout.addWidget(btn, row, col)
                self.buttons.append(btn)
                
                col += 1
                if col >= cols_limit:
                    col = 0
                    row += 1

        # Buttons layout
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.btn_select = QPushButton("Выбрать")
        self.btn_select.setEnabled(False)
        self.btn_select.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY}; color: black; font-weight: bold; padding: 6px 16px; border-radius: 4px;")
        self.btn_select.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_select)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.setStyleSheet(f"background-color: {styles.COLOR_HOVER_BG}; color: white; padding: 6px 16px; border-radius: 4px;")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

    def on_image_selected(self):
        sender = self.sender()
        path = sender.property("image_path")
        self.selected_path = path
        
        bg_rgba = "rgba(0, 230, 118, 0.1)" if styles.COLOR_PRIMARY == "#00E676" else "rgba(0, 176, 255, 0.1)"
        for btn in self.buttons:
            if btn.property("image_path") == path:
                btn.setStyleSheet(f"border: 2px solid {styles.COLOR_PRIMARY}; border-radius: 47px; background-color: {bg_rgba};")
            else:
                btn.setStyleSheet(f"border: 2px solid {styles.COLOR_BORDER}; border-radius: 47px; background-color: transparent;")
        
        self.btn_select.setEnabled(True)


class MassAvatarUpdateWorker(QThread):
    log_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal()

    def __init__(self, selected_accounts, api_id, api_hash, avatar_files):
        super().__init__()
        self.accounts = selected_accounts
        self.api_id = api_id
        self.api_hash = api_hash
        self.avatar_files = avatar_files
        self.loop = None

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        async def run_one(acc, photo_path):
            workdir = acc.get("workdir")
            proxy_url = acc.get("proxy_url")
            device_name = acc.get("device_name", "ShadowGram-PC")
            
            if not workdir or not os.path.exists(workdir):
                self.log_signal.emit(f"[{acc['name']}] Рабочая папка не найдена!", "error")
                return

            from src.modules.session_checker import _find_session_file
            session_file = _find_session_file(Path(workdir))
            if not session_file:
                self.log_signal.emit(f"[{acc['name']}] Файл сессии не найден!", "error")
                return

            self.log_signal.emit(f"[{acc['name']}] Запуск клиента для установки аватарки...", "info")
            
            gost_proc = None
            proxy_settings = None
            if proxy_url:
                is_socks = proxy_url.startswith("socks5://") or proxy_url.startswith("socks4://")
                if is_socks:
                    from src.core.managers.proxy_manager import parse_proxy_url
                    proxy_settings = parse_proxy_url(proxy_url)
                else:
                    from src.modules.session_checker import _setup_proxy
                    gost_proc, proxy_settings = await _setup_proxy(proxy_url)
                    if not gost_proc:
                        self.log_signal.emit(f"[{acc['name']}] Ошибка прокси-туннеля!", "error")
                        return

            from src.core.constants import CONFIG_FILE
            from src.core.managers.account_manager import get_hardware_profile
            hw_profile = get_hardware_profile(CONFIG_FILE, str(session_file.parent))

            client = Client(
                name=session_file.stem,
                api_id=int(acc.get("api_id", 0)),
                api_hash=acc.get("api_hash", ""),
                workdir=str(session_file.parent),
                proxy=proxy_settings,
                device_model=hw_profile.get("device_model", "PC 64bit"),
                system_version=hw_profile.get("system_version", "Windows 10"),
                app_version=hw_profile.get("app_version", "4.8.4 x64"),
                lang_code=hw_profile.get("lang_code", "en"),
            )
            
            try:
                await asyncio.wait_for(client.connect(), timeout=20.0)
                self.log_signal.emit(f"[{acc['name']}] Установка новой случайной аватарки: {os.path.basename(photo_path)}...", "info")
                await client.set_profile_photo(photo=photo_path)
                
                try:
                    shutil.copy2(photo_path, Path(workdir) / "avatar.jpg")
                except:
                    pass
                
                self.log_signal.emit(f"[{acc['name']}] Аватарка успешно установлена!", "success")
            except Exception as e:
                self.log_signal.emit(f"[{acc['name']}] Ошибка установки аватарки: {e}", "error")
            finally:
                try:
                    await client.disconnect()
                except:
                    pass
                if gost_proc:
                    try:
                        gost_proc.terminate()
                    except:
                        pass

        async def run_all():
            for acc in self.accounts:
                chosen_photo = random.choice(self.avatar_files)
                await run_one(acc, chosen_photo)
                await asyncio.sleep(2.0)

        try:
            self.loop.run_until_complete(run_all())
        except Exception as e:
            self.log_signal.emit(f"Ошибка массового обновления аватарок: {e}", "error")
        finally:
            self.loop.close()
            self.finished_signal.emit()


class SegmentedControl(QWidget):
    valueChanged = pyqtSignal(str)
    
    def __init__(self, options, default_value, parent=None):
        super().__init__(parent)
        self.options = options
        self.current_value = default_value
        self.buttons = {}
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        for opt in options:
            btn = QPushButton(opt)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, o=opt: self.set_value(o))
            self.buttons[opt] = btn
            layout.addWidget(btn)
            
        self.update_styles()
        
    def set_value(self, value):
        if self.current_value != value:
            self.current_value = value
            self.update_styles()
            self.valueChanged.emit(value)
            
    def value(self):
        return self.current_value
        
    def update_styles(self):
        for opt, btn in self.buttons.items():
            if opt == self.current_value:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {styles.COLOR_PRIMARY_DARK};
                        color: white;
                        border: 1px solid {styles.COLOR_PRIMARY_DARK};
                        border-radius: 6px;
                        padding: 6px 12px;
                        font-weight: bold;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {styles.COLOR_CONSOLE_BG};
                        color: {styles.COLOR_TEXT_MUTED};
                        border: 1px dashed {styles.COLOR_BORDER};
                        border-radius: 6px;
                        padding: 6px 12px;
                    }}
                    QPushButton:hover {{
                        border: 1px solid {styles.COLOR_PRIMARY};
                        color: {styles.COLOR_PRIMARY};
                    }}
                """)

class CommentingExecutionWorker(QThread):
    log_signal = pyqtSignal(str, str)     # account_name, msg
    status_signal = pyqtSignal(str, str)  # account_name, status
    finished_signal = pyqtSignal(int)     # block_index

    def __init__(self, block_index, selected_accounts=None, api_id=None, api_hash=None):
        super().__init__()
        if isinstance(block_index, list):
            self.block_index = 0
            self.accounts = block_index
            self.api_id = selected_accounts
            self.api_hash = api_id
        else:
            self.block_index = block_index
            self.accounts = selected_accounts
            self.api_id = api_id
            self.api_hash = api_hash
        self.instances = []
        self._is_paused = False
        self._is_stopped = False

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        concurrency_limit = asyncio.Semaphore(10)
        
        async def run_one(acc):
            async with concurrency_limit:
                acc_name = acc.get("name", "Unknown")
                def log_cb(msg):
                    self.log_signal.emit(acc_name, msg)
                
                self.status_signal.emit(acc_name, "Запуск...")
                plugin = SmartCommenterPlugin(acc, acc.get("api_id", 0), acc.get("api_hash", ""), log_cb)
                plugin.is_paused = self._is_paused
                
                def status_cb(status_str):
                    self.status_signal.emit(acc_name, status_str)
                
                plugin.status_callback = status_cb
                self.instances.append(plugin)
                
                try:
                    delay = random.randint(1, 8)
                    log_cb(f"<span style='color: #fbc02d;'>[{acc_name}] Запуск комментирования через {delay} сек...</span>")
                    await plugin.sleep(delay)
                    
                    self.status_signal.emit(acc_name, "Инициализация...")
                    await plugin.run()
                    self.status_signal.emit(acc_name, "Завершен")
                except asyncio.CancelledError:
                    self.status_signal.emit(acc_name, "Остановлен")
                    log_cb(f"<span style='color: #ff5252;'>[{acc_name}] Работа остановлена пользователем.</span>")
                except Exception as e:
                    self.status_signal.emit(acc_name, "Ошибка")
                    log_cb(f"<span style='color: #ff5252;'>[{acc_name}] Ошибка: {e}</span>")
                finally:
                    await plugin.cleanup()

        async def run_all():
            tasks = [run_one(acc) for acc in self.accounts]
            await asyncio.gather(*tasks)

        try:
            loop.run_until_complete(run_all())
        except Exception as e:
            self.log_signal.emit("SYSTEM", f"Ошибка выполнения автокомментирования в Блоке {self.block_index + 1}: {e}")
        finally:
            loop.close()
            self.finished_signal.emit(self.block_index)

    def pause(self):
        self._is_paused = True
        for instance in self.instances:
            instance.is_paused = True
            if hasattr(instance, "status_callback") and instance.status_callback:
                instance.status_callback("Пауза")

    def resume(self):
        self._is_paused = False
        for instance in self.instances:
            instance.is_paused = False
            if hasattr(instance, "status_callback") and instance.status_callback:
                instance.status_callback("Мониторинг...")

    def stop(self):
        self._is_stopped = True
        for instance in self.instances:
            instance.is_stopped = True
            instance.is_paused = False

class AccountLogDialog(QDialog):
    def __init__(self, parent, acc_name, initial_logs):
        super().__init__(parent)
        self.acc_name = acc_name
        self.setWindowTitle(f"Лог аккаунта — {acc_name}")
        self.resize(600, 400)
        self.setStyleSheet(f"background-color: {styles.COLOR_BG}; border: 1px solid {styles.COLOR_BORDER};")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet(f"""
            QTextEdit {{
                background-color: {styles.COLOR_CONSOLE_BG};
                color: #FFFFFF;
                border: 1px solid {styles.COLOR_BORDER};
                font-family: monospace;
            }}
        """)
        
        for log in initial_logs:
            self.log_area.append(log)
            
        layout.addWidget(self.log_area)
        
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        btn_close.setStyleSheet(f"background-color: {styles.COLOR_HOVER_BG}; color: {styles.COLOR_PRIMARY}; padding: 6px 12px; border-radius: 4px;")
        layout.addWidget(btn_close)

    def append_log(self, text):
        self.log_area.append(text)

class CommentingControlWindow(QDialog):
    def __init__(self, parent, blocks, api_id, api_hash):
        super().__init__(parent)
        self.parent = parent
        self.blocks = blocks
        self.api_id = api_id
        self.api_hash = api_hash
        
        self.setWindowTitle("Управление процессами нейрокомментирования")
        self.resize(900, 700)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowMinMaxButtonsHint)
        
        self.account_widgets = {}
        self.block_status_labels = {}
        self.account_logs = {}
        self.open_log_dialogs = {}
        self.workers = {}
        self.is_finished_called = False
        
        self.setup_ui()
        self.start_all_blocks()

    def setup_ui(self):
        accent_color = styles.COLOR_PRIMARY
        accent_dark = styles.COLOR_PRIMARY_DARK
        bg_color = styles.COLOR_BG
        accent_bg = styles.COLOR_ACCENT_BG
        border_color = styles.COLOR_BORDER
        console_bg = styles.COLOR_CONSOLE_BG
        hover_bg = styles.COLOR_HOVER_BG
        select_bg = styles.COLOR_SELECT_BG
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            QLabel {{
                color: #FFFFFF;
                font-family: '{styles.FONT_NAME}', sans-serif;
            }}
            QFrame#BlockCard {{
                background-color: {accent_bg};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 12px;
                margin-bottom: 12px;
            }}
            QLineEdit {{
                background-color: {console_bg};
                border: 1px solid {border_color};
                border-radius: 5px;
                padding: 6px;
                color: {accent_color};
                font-family: '{styles.FONT_NAME}', sans-serif;
            }}
            QLineEdit:focus {{
                border: 1px solid {accent_color};
                background-color: {hover_bg};
            }}
            QPushButton {{
                background-color: {hover_bg};
                color: {accent_color};
                border: 1px solid {styles.COLOR_BORDER_DARK};
                padding: 6px 12px;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {select_bg};
                border-color: {accent_color};
                color: #FFFFFF;
            }}
            QPushButton:pressed {{
                background-color: {bg_color};
            }}
            QTextEdit#GlobalLogs {{
                background-color: {console_bg};
                border: 1px solid {border_color};
                color: {accent_color};
                font-family: monospace;
                font-size: 12px;
                border-radius: 6px;
                padding: 8px;
            }}
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                border: none;
                background: {bg_color};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {styles.COLOR_SCROLL_HANDLE};
                min-height: 30px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {accent_color};
            }}
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)
        
        header_layout = QHBoxLayout()
        title_lbl = QLabel("💬 ПАНЕЛЬ УПРАВЛЕНИЯ НЕЙРОКОММЕНТИРОВАНИЕМ")
        title_lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {accent_color}; letter-spacing: 1px;")
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        self.blocks_layout = QVBoxLayout(scroll_content)
        self.blocks_layout.setContentsMargins(0, 0, 0, 0)
        self.blocks_layout.setSpacing(10)
        
        for idx, block_accounts in enumerate(self.blocks):
            card = self.create_block_card(idx, block_accounts)
            self.blocks_layout.addWidget(card)
            
        self.blocks_layout.addStretch()
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, stretch=2)
        
        logs_title_layout = QHBoxLayout()
        logs_lbl = QLabel("📜 ОБЩИЙ ЛОГ ОПЕРАЦИЙ")
        logs_lbl.setStyleSheet(f"font-weight: bold; color: {accent_color}; font-size: 12px;")
        logs_title_layout.addWidget(logs_lbl)
        logs_title_layout.addStretch()
        
        btn_clear_logs = QPushButton("Очистить")
        btn_clear_logs.clicked.connect(self.clear_logs)
        btn_clear_logs.setStyleSheet("padding: 3px 8px; font-size: 11px;")
        logs_title_layout.addWidget(btn_clear_logs)
        main_layout.addLayout(logs_title_layout)
        
        self.txt_global_logs = QTextEdit()
        self.txt_global_logs.setObjectName("GlobalLogs")
        self.txt_global_logs.setReadOnly(True)
        main_layout.addWidget(self.txt_global_logs, stretch=1)

    def create_block_card(self, idx, accounts):
        card = QFrame()
        card.setObjectName("BlockCard")
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        header = QHBoxLayout()
        block_title = QLabel(f"📦 Блок {idx + 1}")
        block_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF;")
        header.addWidget(block_title)
        
        status_lbl = QLabel("🟢 Активен")
        status_lbl.setStyleSheet(f"color: {styles.COLOR_PRIMARY}; font-weight: bold; font-size: 12px;")
        self.block_status_labels[idx] = status_lbl
        header.addWidget(status_lbl)
        
        header.addStretch()
        
        btn_play = QPushButton("Запустить")
        btn_play.setIcon(QIcon(str(START_ICON_PATH)))
        btn_play.clicked.connect(lambda _, i=idx: self.on_play_block(i))
        btn_play.setStyleSheet(f"color: {styles.COLOR_PRIMARY}; border-color: {styles.COLOR_BORDER}; font-size: 11px; padding: 4px 8px;")
        header.addWidget(btn_play)
        
        btn_pause = QPushButton("Пауза")
        btn_pause.setIcon(QIcon(str(CANCEL_ICON_PATH)))
        btn_pause.clicked.connect(lambda _, i=idx: self.on_pause_block(i))
        btn_pause.setStyleSheet("color: #FF9800; border-color: #5E3C00; font-size: 11px; padding: 4px 8px;")
        header.addWidget(btn_pause)
        
        btn_stop = QPushButton("Стоп")
        btn_stop.setIcon(QIcon(str(CANCEL_ICON_PATH)))
        btn_stop.clicked.connect(lambda _, i=idx: self.on_stop_block(i))
        btn_stop.setStyleSheet("color: #FF5252; border-color: #5E1F1F; font-size: 11px; padding: 4px 8px;")
        header.addWidget(btn_stop)
        
        layout.addLayout(header)
        
        accounts_layout = QVBoxLayout()
        accounts_layout.setSpacing(6)
        
        for acc in accounts:
            acc_row = QHBoxLayout()
            acc_row.setSpacing(10)
            
            acc_name_lbl = QLabel(acc["name"])
            acc_name_lbl.setMinimumWidth(120)
            acc_name_lbl.setStyleSheet("font-weight: bold; color: #E0E0E0;")
            acc_row.addWidget(acc_name_lbl)
            
            acc_status = QLabel("Запуск...")
            acc_status.setStyleSheet("color: #FFC107; font-size: 11px;")
            acc_status.setMinimumWidth(100)
            acc_row.addWidget(acc_status)
            
            channels_val = acc.get("commenting_settings", {}).get("channels", "").strip()
            display_channels = ", ".join(c.strip() for c in channels_val.split("\n") if c.strip())
            
            channels_input = QLineEdit()
            channels_input.setText(display_channels)
            channels_input.setPlaceholderText("Каналы через запятую...")
            acc_row.addWidget(channels_input, stretch=1)
            
            btn_save = QPushButton("")
            btn_save.setIcon(QIcon(str(SAVE_ICON_PATH)))
            btn_save.setToolTip("Сохранить и применить настройки на лету")
            btn_save.setFixedWidth(32)
            btn_save.clicked.connect(lambda _, n=acc["name"]: self.on_save_channels(n))
            acc_row.addWidget(btn_save)
            
            btn_log = QPushButton("")
            btn_log.setIcon(QIcon(str(NOTE_ICON_PATH)))
            btn_log.setToolTip("Посмотреть логи аккаунта")
            btn_log.setFixedWidth(32)
            btn_log.clicked.connect(lambda _, n=acc["name"]: self.on_open_logs(n))
            acc_row.addWidget(btn_log)
            
            accounts_layout.addLayout(acc_row)
            
            self.account_widgets[acc["name"]] = {
                "status_lbl": acc_status,
                "channels_input": channels_input,
                "save_btn": btn_save,
                "log_btn": btn_log
            }
            self.account_logs[acc["name"]] = []
            
        layout.addLayout(accounts_layout)
        return card

    def start_all_blocks(self):
        for idx, block_accounts in enumerate(self.blocks):
            worker = CommentingExecutionWorker(idx, block_accounts, self.api_id, self.api_hash)
            worker.log_signal.connect(self.handle_log)
            worker.status_signal.connect(self.handle_status)
            worker.finished_signal.connect(self.handle_finished)
            self.workers[idx] = worker
            worker.start()

    def handle_log(self, acc_name, msg):
        self.txt_global_logs.append(msg)
        if acc_name in self.account_logs:
            self.account_logs[acc_name].append(msg)
        if acc_name in self.open_log_dialogs:
            self.open_log_dialogs[acc_name].append_log(msg)

    def handle_status(self, acc_name, status):
        if acc_name in self.account_widgets:
            status_lbl = self.account_widgets[acc_name]["status_lbl"]
            status_lbl.setText(status)
            
            if status in ["Запуск...", "Вход...", "Инициализация..."]:
                status_lbl.setStyleSheet("color: #FFC107; font-size: 11px;")
            elif status in ["Мониторинг...", "Успех 💬", "Слежение..."]:
                status_lbl.setStyleSheet(f"color: {styles.COLOR_PRIMARY}; font-size: 11px; font-weight: bold;")
            elif status == "Ожидание...":
                status_lbl.setStyleSheet("color: #00B0FF; font-size: 11px;")
            elif status == "Пауза":
                status_lbl.setStyleSheet("color: #FF9800; font-size: 11px; font-weight: bold;")
            elif status == "Ошибка":
                status_lbl.setStyleSheet("color: #FF5252; font-size: 11px; font-weight: bold;")
            elif status in ["Завершен", "Остановлен"]:
                status_lbl.setStyleSheet("color: #888888; font-size: 11px;")

    def handle_finished(self, block_index):
        if block_index in self.block_status_labels:
            lbl = self.block_status_labels[block_index]
            lbl.setText("🔴 Завершен")
            lbl.setStyleSheet("color: #FF5252; font-weight: bold; font-size: 12px;")
            
        all_finished = True
        for worker in self.workers.values():
            if worker.isRunning():
                all_finished = False
                break
                
        if all_finished:
            self.txt_global_logs.append("<span style='color: #00e676;'>[SYSTEM] Все блоки автокомментирования завершили работу.</span>")
            if hasattr(self.parent, "on_commenting_finished"):
                self.parent.on_commenting_finished()

    def on_play_block(self, block_index):
        if block_index in self.workers:
            self.workers[block_index].resume()
            if block_index in self.block_status_labels:
                lbl = self.block_status_labels[block_index]
                lbl.setText("🟢 Активен")
                lbl.setStyleSheet(f"color: {styles.COLOR_PRIMARY}; font-weight: bold; font-size: 12px;")

    def on_pause_block(self, block_index):
        if block_index in self.workers:
            self.workers[block_index].pause()
            if block_index in self.block_status_labels:
                lbl = self.block_status_labels[block_index]
                lbl.setText("Пауза")
                lbl.setStyleSheet("color: #FF9800; font-weight: bold; font-size: 12px;")

    def on_stop_block(self, block_index):
        if block_index in self.workers:
            self.workers[block_index].stop()

    def on_save_channels(self, acc_name):
        if acc_name not in self.account_widgets:
            return
            
        input_widget = self.account_widgets[acc_name]["channels_input"]
        btn_save = self.account_widgets[acc_name]["save_btn"]
        text = input_widget.text().strip()
        
        new_channels_list = [c.strip() for c in text.split(",") if c.strip()]
        new_channels_text = "\n".join(new_channels_list)
        
        self.update_account_channels(acc_name, new_channels_text)
        
        updated_running = False
        for worker in self.workers.values():
            for instance in worker.instances:
                if instance.acc.get("name") == acc_name:
                    instance.active_channels = list(new_channels_list)
                    updated_running = True
                    break
            if updated_running:
                break
                
        status_msg = "и применены на лету!" if updated_running else "(сохранены, аккаунт не запущен)"
        self.txt_global_logs.append(f"<span style='color: #00e676;'>[SYSTEM] Настройки каналов для {acc_name} успешно сохранены {status_msg}</span>")
        
        btn_save.setStyleSheet("background-color: #00E676; color: black;")
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: btn_save.setStyleSheet(""))

    def update_account_channels(self, acc_name, new_channels_text):
        if hasattr(self.parent, "accounts_map") and acc_name in self.parent.accounts_map:
            acc = self.parent.accounts_map[acc_name]
            if "commenting_settings" not in acc:
                acc["commenting_settings"] = {}
            acc["commenting_settings"]["channels"] = new_channels_text
            
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for acc in data.get("accounts", []):
                if acc["name"] == acc_name:
                    if "commenting_settings" not in acc:
                        acc["commenting_settings"] = {}
                    acc["commenting_settings"]["channels"] = new_channels_text
                    break
                    
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
            farm_manager.save_active_farm_config()
            
            if hasattr(self.parent, "refresh_accounts"):
                self.parent.refresh_accounts()
                
        except Exception as e:
            self.txt_global_logs.append(f"<span style='color: #ff5252;'>[SYSTEM] Ошибка сохранения настроек {acc_name}: {e}</span>")

    def on_open_logs(self, acc_name):
        if acc_name in self.open_log_dialogs:
            dialog = self.open_log_dialogs[acc_name]
            dialog.raise_()
            dialog.activateWindow()
            return
            
        initial_logs = self.account_logs.get(acc_name, [])
        dialog = AccountLogDialog(self, acc_name, initial_logs)
        self.open_log_dialogs[acc_name] = dialog
        dialog.finished.connect(lambda: self.open_log_dialogs.pop(acc_name, None))
        dialog.show()

    def clear_logs(self):
        self.txt_global_logs.clear()

    def closeEvent(self, event):
        for worker in self.workers.values():
            if worker.isRunning():
                worker.stop()
                
        for worker in self.workers.values():
            if worker.isRunning():
                worker.wait()
                
        for dialog in list(self.open_log_dialogs.values()):
            dialog.close()
            
        if hasattr(self.parent, "on_commenting_finished"):
            self.parent.on_commenting_finished()
            
        event.accept()

class ProfileOperationWorker(QThread):
    log_signal = pyqtSignal(str, str) # message, status
    info_fetched = pyqtSignal(dict)   # first_name, last_name, bio, avatar_path, and optionally channel_info
    operation_finished = pyqtSignal(bool, str) # success, message

    def __init__(self, action, account_data, api_id, api_hash, params=None):
        super().__init__()
        self.action = action # "fetch", "update_profile", "update_avatar", "create_channel", "update_channel_profile", "update_channel_avatar", "publish_channel_post"
        self.acc = account_data
        self.api_id = api_id
        self.api_hash = api_hash
        self.params = params or {}
        self.loop = None
        self.client = None
        self.gost_process = None

    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self.execute())
        except Exception as e:
            self.log_signal.emit(f"Критическая ошибка выполнения: {e}", "error")
            self.operation_finished.emit(False, str(e))
        finally:
            self.loop.close()

    async def execute(self):
        proxy_url = self.acc.get("proxy_url")
        device_name = self.acc.get("device_name", "ShadowGram-PC")
        workdir = self.acc.get("workdir")
        
        if not workdir or not os.path.exists(workdir):
            self.log_signal.emit("Рабочая папка аккаунта не найдена!", "error")
            self.operation_finished.emit(False, "Workdir not found")
            return

        from src.modules.session_checker import _find_session_file
        session_file = _find_session_file(Path(workdir))
        if not session_file:
            self.log_signal.emit("Файл сессии .session не найден в папке профиля!", "error")
            self.operation_finished.emit(False, "No session file")
            return

        proxy_settings = None
        if proxy_url:
            self.log_signal.emit("Настройка прокси...", "info")
            is_socks = proxy_url.startswith("socks5://") or proxy_url.startswith("socks4://")
            if is_socks:
                from src.core.managers.proxy_manager import parse_proxy_url
                proxy_settings = parse_proxy_url(proxy_url)
            else:
                from src.modules.session_checker import _setup_proxy
                self.gost_process, proxy_settings = await _setup_proxy(proxy_url)
                if not self.gost_process:
                    self.log_signal.emit("Не удалось настроить Gost-туннель для прокси!", "error")
                    self.operation_finished.emit(False, "Gost tunnel failure")
                    return

        self.log_signal.emit("Подключение к Telegram через Hydrogram...", "info")
        from src.core.constants import CONFIG_FILE
        from src.core.managers.account_manager import get_hardware_profile
        hw_profile = get_hardware_profile(CONFIG_FILE, str(session_file.parent))

        self.client = Client(
            name=session_file.stem,
            api_id=int(self.acc.get("api_id", 0)),
            api_hash=self.acc.get("api_hash", ""),
            workdir=str(session_file.parent),
            proxy=proxy_settings,
            device_model=hw_profile.get("device_model", "PC 64bit"),
            system_version=hw_profile.get("system_version", "Windows 10"),
            app_version=hw_profile.get("app_version", "4.8.4 x64"),
            lang_code=hw_profile.get("lang_code", "en"),
        )
        
        try:
            try:
                await asyncio.wait_for(self.client.connect(), timeout=20.0)
            except asyncio.TimeoutError:
                raise Exception("Превышено время ожидания подключения (проверьте прокси или сеть)")
            self.client.me = await self.client.get_me()
            self.log_signal.emit("Подключение успешно установлено!", "success")
            
            if self.action == "fetch":
                self.log_signal.emit("Запрос данных профиля с серверов Telegram...", "info")
                me = self.client.me
                
                bio = ""
                try:
                    chat = await self.client.get_chat("me")
                    bio = chat.bio or ""
                except Exception as e:
                    self.log_signal.emit(f"Не удалось получить Био профиля: {e}", "warning")
                
                avatar_path = None
                if me.photo:
                    avatar_dest = Path(workdir) / "avatar.jpg"
                    try:
                        self.log_signal.emit("Загрузка текущей аватарки профиля...", "info")
                        await self.client.download_media(me.photo.big_file_id, file_name=str(avatar_dest))
                        avatar_path = str(avatar_dest)
                    except Exception as e:
                        self.log_signal.emit(f"Не удалось скачать аватарку: {e}", "warning")
                
                channel_info = None
                bound_channel = self.acc.get("bound_channel")
                if bound_channel:
                    try:
                        self.log_signal.emit(f"Запрос данных канала {bound_channel}...", "info")
                        resolved = resolve_chat_id(bound_channel)
                        chat = await self.client.get_chat(resolved)
                        chan_avatar_path = None
                        if chat.photo:
                            chan_avatar_dest = Path(workdir) / "channel_avatar.jpg"
                            try:
                                self.log_signal.emit("Загрузка аватарки канала...", "info")
                                await self.client.download_media(chat.photo.big_file_id, file_name=str(chan_avatar_dest))
                                chan_avatar_path = str(chan_avatar_dest)
                            except Exception as e:
                                self.log_signal.emit(f"Не удалось скачать аватарку канала: {e}", "warning")
                        
                        channel_info = {
                            "title": chat.title or "",
                            "description": chat.description or "",
                            "avatar_path": chan_avatar_path or (str(Path(workdir) / "channel_avatar.jpg") if (Path(workdir) / "channel_avatar.jpg").exists() else None)
                        }
                    except Exception as e:
                        self.log_signal.emit(f"Не удалось получить данные привязанного канала {bound_channel}: {e}", "warning")

                info = {
                    "first_name": me.first_name or "",
                    "last_name": me.last_name or "",
                    "bio": bio,
                    "avatar_path": avatar_path or (str(Path(workdir) / "avatar.jpg") if (Path(workdir) / "avatar.jpg").exists() else None),
                    "channel_info": channel_info
                }
                self.info_fetched.emit(info)
                self.operation_finished.emit(True, "Данные профиля загружены")

            elif self.action == "update_profile":
                first_name = self.params.get("first_name")
                last_name = self.params.get("last_name")
                bio = self.params.get("bio")
                
                self.log_signal.emit(f"Обновление полей профиля в Telegram (Имя: {first_name}, Фамилия: {last_name})...", "info")
                await self.client.update_profile(first_name=first_name, last_name=last_name, bio=bio)
                self.log_signal.emit("Данные профиля успешно изменены в Telegram!", "success")
                self.operation_finished.emit(True, "Профиль обновлен")

            elif self.action == "update_avatar":
                photo_path = self.params.get("photo_path")
                self.log_signal.emit(f"Установка новой аватарки: {os.path.basename(photo_path)}...", "info")
                await self.client.set_profile_photo(photo=photo_path)
                
                # Copy to local avatar.jpg
                try:
                    shutil.copy2(photo_path, Path(workdir) / "avatar.jpg")
                except Exception as ce:
                    self.log_signal.emit(f"Не удалось обновить локальный кэш аватарки: {ce}", "warning")
                
                self.log_signal.emit("Аватарка успешно установлена в Telegram!", "success")
                self.operation_finished.emit(True, "Аватарка обновлена")

            elif self.action == "create_channel":
                title = self.params.get("title")
                description = self.params.get("description")
                username = self.params.get("username")
                
                self.log_signal.emit(f"Создание нового канала '{title}'...", "info")
                chat = await self.client.create_channel(title=title, description=description)
                self.log_signal.emit(f"Канал создан! ID: {chat.id}", "success")
                
                channel_link = ""
                if username:
                    username = username.strip().replace("https://t.me/", "").replace("t.me/", "").replace("@", "")
                    self.log_signal.emit(f"Установка публичного юзернейма @{username}...", "info")
                    try:
                        await self.client.set_chat_username(chat.id, username)
                        channel_link = f"@{username}"
                        self.log_signal.emit(f"Юзернейм @{username} успешно привязан!", "success")
                    except Exception as ue:
                        self.log_signal.emit(f"Не удалось установить юзернейм @{username} (возможно, занят): {ue}", "error")
                        try:
                            invite_link = await self.client.export_chat_invite_link(chat.id)
                            channel_link = invite_link
                        except:
                            channel_link = f"id:{chat.id}"
                else:
                    try:
                        invite_link = await self.client.export_chat_invite_link(chat.id)
                        channel_link = invite_link
                        self.log_signal.emit(f"Ссылка на приватный канал: {invite_link}", "success")
                    except Exception as ie:
                        channel_link = f"id:{chat.id}"
                        self.log_signal.emit(f"Не удалось сгенерировать инвайт-ссылку: {ie}", "warning")
                        
                self.operation_finished.emit(True, channel_link)

            elif self.action == "update_channel_profile":
                bound_channel = self.acc.get("bound_channel")
                if not bound_channel:
                    self.log_signal.emit("Канал не привязан к аккаунту!", "error")
                    self.operation_finished.emit(False, "Channel not bound")
                    return
                title = self.params.get("title")
                description = self.params.get("description")
                
                self.log_signal.emit(f"Получение информации о канале {bound_channel}...", "info")
                resolved = resolve_chat_id(bound_channel)
                chat = await self.client.get_chat(resolved)
                
                self.log_signal.emit(f"Обновление названия канала на '{title}'...", "info")
                await self.client.set_chat_title(chat.id, title)
                self.log_signal.emit("Название канала успешно обновлено!", "success")
                
                self.log_signal.emit("Обновление описания канала...", "info")
                await self.client.set_chat_description(chat.id, description or "")
                self.log_signal.emit("Описание канала успешно обновлено!", "success")
                
                self.operation_finished.emit(True, "Данные канала обновлены")

            elif self.action == "update_channel_avatar":
                bound_channel = self.acc.get("bound_channel")
                if not bound_channel:
                    self.log_signal.emit("Канал не привязан к аккаунту!", "error")
                    self.operation_finished.emit(False, "Channel not bound")
                    return
                photo_path = self.params.get("photo_path")
                self.log_signal.emit(f"Установка новой аватарки канала: {os.path.basename(photo_path)}...", "info")
                resolved = resolve_chat_id(bound_channel)
                chat = await self.client.get_chat(resolved)
                
                await self.client.set_chat_photo(chat.id, photo=photo_path)
                
                try:
                    shutil.copy2(photo_path, Path(workdir) / "channel_avatar.jpg")
                except Exception as ce:
                    self.log_signal.emit(f"Не удалось обновить локальный кэш аватарки канала: {ce}", "warning")
                
                self.log_signal.emit("Аватарка канала успешно установлена в Telegram!", "success")
                self.operation_finished.emit(True, "Аватарка канала обновлена")

            elif self.action == "publish_channel_post":
                bound_channel = self.acc.get("bound_channel")
                if not bound_channel:
                    self.log_signal.emit("Канал не привязан к аккаунту!", "error")
                    self.operation_finished.emit(False, "Channel not bound")
                    return
                text = self.params.get("text", "")
                photo_path = self.params.get("photo_path")
                
                resolved = resolve_chat_id(bound_channel)
                chat = await self.client.get_chat(resolved)
                
                if photo_path and os.path.exists(photo_path):
                    self.log_signal.emit(f"Отправка поста с фото в канал {chat.title}...", "info")
                    await self.client.send_photo(chat.id, photo=photo_path, caption=text)
                else:
                    self.log_signal.emit(f"Отправка текстового поста в канал {chat.title}...", "info")
                    await self.client.send_message(chat.id, text=text)
                
                self.log_signal.emit("Пост успешно опубликован в канале!", "success")
                self.operation_finished.emit(True, "Пост опубликован")

        except Exception as e:
            self.log_signal.emit(f"Ошибка при работе с Telegram API: {e}", "error")
            self.operation_finished.emit(False, str(e))
        finally:
            self.log_signal.emit("Отключение от Telegram и очистка ресурсов...", "info")
            try:
                await self.client.disconnect()
            except:
                pass
            if self.gost_process:
                self.gost_process.terminate()
                self.gost_process.wait()


class WarmerExecutionWorker(QThread):
    log_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal()

    def __init__(self, selected_accounts, api_id, api_hash, params):
        super().__init__()
        self.accounts = selected_accounts
        self.api_id = api_id
        self.api_hash = api_hash
        self.params = params
        self.instances = []

    def stop(self):
        for plugin in self.instances:
            plugin.is_stopped = True

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        concurrency_limit = asyncio.Semaphore(5) # Лимит 5 одновременных сессий прогрева
        
        async def run_one(acc):
            async with concurrency_limit:
                def log_cb(msg):
                    # Отправляем логи в общий UI с пометкой аккаунта
                    self.log_signal.emit(msg, "info")
                
                plugin = SmartWarmerPlugin(acc, acc.get("api_id", 0), acc.get("api_hash", ""), log_cb)
                plugin.selected_accounts = self.accounts
                self.instances.append(plugin)
                try:
                    # Staggered Start (случайная задержка 1-8 сек)
                    delay = random.randint(1, 8)
                    log_cb(f"<span style='color: #fbc02d;'>[{acc['name']}] Запуск прогрева через {delay} сек...</span>")
                    for _ in range(int(delay * 5)):
                        if getattr(plugin, "is_stopped", False):
                            raise asyncio.CancelledError("Модуль остановлен пользователем")
                        await asyncio.sleep(0.2)
                    
                    await plugin.run(**self.params)
                except Exception as e:
                    log_cb(f"<span style='color: #ff5252;'>[{acc['name']}] Ошибка: {e}</span>")
                finally:
                    await plugin.cleanup()

        async def run_all():
            tasks = [run_one(acc) for acc in self.accounts]
            await asyncio.gather(*tasks)

        try:
            loop.run_until_complete(run_all())
        except Exception as e:
            self.log_signal.emit(f"Ошибка сессии автопрогрева: {e}", "error")
        finally:
            loop.close()
            self.finished_signal.emit()


class Switch(QAbstractButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(46, 24)
        self._thumb_position = 3.0
        self._animation = QPropertyAnimation(self, b"thumb_position", self)
        self._animation.setDuration(120)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

    @pyqtProperty(float)
    def thumb_position(self):
        return self._thumb_position

    @thumb_position.setter
    def thumb_position(self, pos):
        self._thumb_position = pos
        self.update()

    def setChecked(self, checked):
        super().setChecked(checked)
        self._thumb_position = 25.0 if checked else 3.0
        self.update()

    def nextCheckState(self):
        super().nextCheckState()
        self._animation.setStartValue(self._thumb_position)
        self._animation.setEndValue(25.0 if self.isChecked() else 3.0)
        self._animation.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        bg_color = QColor(styles.COLOR_PRIMARY_DARK) if self.isChecked() else QColor(styles.COLOR_HOVER_BG)
        border_color = QColor(styles.COLOR_PRIMARY) if self.isChecked() else QColor(styles.COLOR_BORDER_DARK)
        painter.setBrush(bg_color)
        painter.setPen(QPen(border_color, 1))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        
        thumb_color = QColor("#000000") if self.isChecked() else QColor("#E0E0E0")
        painter.setBrush(thumb_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(self._thumb_position), 3, 18, 18)
        painter.end()


class ProtectionPresetCard(QFrame):
    clicked = pyqtSignal(str)
    
    def __init__(self, key, icon, title, subtitle, parent=None):
        super().__init__(parent)
        self.key = key
        self.setObjectName("PresetCardInactive")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)
        
        # Icon
        self.icon_lbl = QLabel(icon)
        self.icon_lbl.setFixedSize(28, 28)
        
        if key == "conservative":
            bg = styles.COLOR_PRIMARY_DARK
            fg = "#000000" if styles.COLOR_PRIMARY == "#00E676" else "#FFFFFF"
            self.icon_lbl.setStyleSheet(f"background-color: {bg}; color: {fg}; border-radius: 6px; font-size: 14px; qproperty-alignment: AlignCenter;")
        elif key == "balanced":
            bg = styles.COLOR_PRIMARY
            fg = "#000000" if styles.COLOR_PRIMARY == "#00E676" else "#FFFFFF"
            self.icon_lbl.setStyleSheet(f"background-color: {bg}; color: {fg}; border-radius: 6px; font-size: 14px; qproperty-alignment: AlignCenter;")
        else: # aggressive
            self.icon_lbl.setStyleSheet("background-color: #ff8f00; color: white; border-radius: 6px; font-size: 14px; qproperty-alignment: AlignCenter;")
            
        layout.addWidget(self.icon_lbl)
        
        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("font-weight: bold; color: white; font-size: 11px; border: none; background: transparent;")
        self.sub_lbl = QLabel(subtitle)
        self.sub_lbl.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 9px; border: none; background: transparent;")
        text_layout.addWidget(self.title_lbl)
        text_layout.addWidget(self.sub_lbl)
        
        layout.addLayout(text_layout, 1)
        
    def set_active(self, active):
        if active:
            self.setObjectName("PresetCardActive")
            bg_rgba = "rgba(0, 230, 118, 0.1)" if styles.COLOR_PRIMARY == "#00E676" else "rgba(0, 176, 255, 0.1)"
            self.setStyleSheet(f"""
                QFrame#PresetCardActive {{
                    background-color: {bg_rgba};
                    border: 1px solid {styles.COLOR_PRIMARY};
                    border-radius: 8px;
                }}
            """)
        else:
            self.setObjectName("PresetCardInactive")
            self.setStyleSheet(f"""
                QFrame#PresetCardInactive {{
                    background-color: {styles.COLOR_BG};
                    border: 1px dashed {styles.COLOR_BORDER};
                    border-radius: 8px;
                }}
                QFrame#PresetCardInactive:hover {{
                    border: 1px solid {styles.COLOR_PRIMARY};
                }}
            """)
        self.style().unpolish(self)
        self.style().polish(self)
        
    def set_enabled_preset(self, enabled):
        self.setEnabled(enabled)
        if enabled:
            self.setGraphicsEffect(None)
        else:
            from PyQt6.QtWidgets import QGraphicsOpacityEffect
            eff = QGraphicsOpacityEffect()
            eff.setOpacity(0.3)
            self.setGraphicsEffect(eff)
        
    def mousePressEvent(self, event):
        if self.isEnabled() and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)
        super().mousePressEvent(event)


class PromptEditDialog(QDialog):
    def __init__(self, title, name="", text="", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(380, 260)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {styles.COLOR_BG};
                border: 1px solid {styles.COLOR_BORDER};
            }}
            QLabel {{
                color: {styles.COLOR_TEXT_MUTED};
                font-weight: bold;
                font-size: 11px;
            }}
            QLineEdit, QTextEdit {{
                background-color: {styles.COLOR_CONSOLE_BG};
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 6px;
                padding: 6px;
                color: #E0E0E0;
            }}
            QPushButton {{
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        layout.addWidget(QLabel("Название промпта:"))
        self.name_edit = QLineEdit(self)
        self.name_edit.setPlaceholderText("Например: хейтер, психолог...")
        self.name_edit.setText(name)
        layout.addWidget(self.name_edit)
        
        layout.addWidget(QLabel("Текст промпта (инструкция для ИИ):"))
        self.text_edit = QTextEdit(self)
        self.text_edit.setPlaceholderText("Напиши короткий, эмоциональный комментарий...")
        self.text_edit.setText(text)
        layout.addWidget(self.text_edit)
        
        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()
        
        self.btn_cancel = QPushButton("Отмена", self)
        self.btn_cancel.setStyleSheet("background-color: #2E1111; color: #FF5252; border: 1px solid #5E2424;")
        self.btn_cancel.clicked.connect(self.reject)
        btns.addWidget(self.btn_cancel)
        
        self.btn_save = QPushButton("Сохранить", self)
        self.btn_save.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY_DARK}; color: {'#000000' if styles.COLOR_PRIMARY == '#00E676' else '#FFFFFF'}; font-weight: bold;")
        self.btn_save.clicked.connect(self.accept)
        btns.addWidget(self.btn_save)
        
        layout.addLayout(btns)
        
    def get_data(self):
        return self.name_edit.text().strip(), self.text_edit.toPlainText().strip()


class PromptCard(QFrame):
    view_clicked = pyqtSignal(str)
    use_clicked = pyqtSignal(str)
    edit_clicked = pyqtSignal(str)
    delete_clicked = pyqtSignal(str)
    
    def __init__(self, key, title, prompt_text, is_system=True, is_starred=False, parent=None):
        super().__init__(parent)
        self.key = key
        self.title = title
        self.prompt_text = prompt_text
        self.is_system = is_system
        self.is_starred = is_starred
        self.is_active = False
        
        self.setObjectName("PromptCardInactive")
        self.setFixedHeight(46)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(10, 4, 10, 4)
        self.main_layout.setSpacing(10)
        
        # 1. Left Icon/Badge
        self.badge_lbl = QLabel()
        self.badge_lbl.setFixedSize(16, 16)
        self.badge_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self.is_system and self.is_starred:
            self.badge_lbl.setText("⭐")
            self.badge_lbl.setStyleSheet("color: #ff8f00; font-size: 11px; background: transparent; border: none;")
        else:
            self.badge_lbl.setStyleSheet("background: transparent; border: none;")
        self.main_layout.addWidget(self.badge_lbl)
        
        # 2. Middle Info (Title + Text preview)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(1)
        info_layout.setContentsMargins(0, 0, 0, 0)
        
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("font-weight: bold; color: white; font-size: 11px; background: transparent; border: none;")
        info_layout.addWidget(self.title_lbl)
        
        # Preview text (first line or truncated text)
        clean_text = " ".join(prompt_text.split())
        preview = clean_text[:80] + "..." if len(clean_text) > 80 else clean_text
        self.preview_lbl = QLabel(preview)
        self.preview_lbl.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 9px; background: transparent; border: none;")
        info_layout.addWidget(self.preview_lbl)
        
        self.main_layout.addLayout(info_layout, 1)
        
        # 3. Action Buttons
        btns_h = QHBoxLayout()
        btns_h.setSpacing(6)
        btns_h.setContentsMargins(0, 0, 0, 0)
        
        btn_style = f"""
            QPushButton {{
                background-color: {styles.COLOR_HOVER_BG};
                color: {styles.COLOR_TEXT_MUTED};
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 4px;
                font-size: 10px;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                border: 1px solid {styles.COLOR_PRIMARY};
                color: {styles.COLOR_PRIMARY};
            }}
        """
        
        self.btn_view = QPushButton("")
        self.btn_view.setIcon(QIcon(str(VIEW_ICON_PATH)))
        self.btn_view.setToolTip("Просмотреть промпт")
        self.btn_view.setStyleSheet(btn_style)
        self.btn_view.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_view.clicked.connect(lambda: self.view_clicked.emit(self.key))
        btns_h.addWidget(self.btn_view)
        
        self.btn_use = QPushButton("")
        self.btn_use.setIcon(QIcon(str(START_ICON_PATH)))
        self.btn_use.setToolTip("Использовать этот промпт")
        self.btn_use.setStyleSheet(btn_style)
        self.btn_use.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_use.clicked.connect(lambda: self.use_clicked.emit(self.key))
        btns_h.addWidget(self.btn_use)
        
        if not self.is_system:
            self.btn_edit = QPushButton("")
            self.btn_edit.setIcon(QIcon(str(NOTE_ICON_PATH)))
            self.btn_edit.setToolTip("Редактировать промпт")
            self.btn_edit.setStyleSheet(btn_style)
            self.btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_edit.clicked.connect(lambda: self.edit_clicked.emit(self.key))
            btns_h.addWidget(self.btn_edit)
            
            self.btn_delete = QPushButton("")
            self.btn_delete.setIcon(QIcon(str(DELETE_ICON_PATH)))
            self.btn_delete.setToolTip("Удалить промпт")
            self.btn_delete.setStyleSheet(btn_style)
            self.btn_delete.setCursor(Qt.CursorShape.PointingHandCursor)
            self.btn_delete.clicked.connect(lambda: self.delete_clicked.emit(self.key))
            btns_h.addWidget(self.btn_delete)
            
        self.main_layout.addLayout(btns_h)
        self.set_active(False)
        
    def set_active(self, active):
        self.is_active = active
        if active:
            self.setObjectName("PromptCardActive")
            bg_rgba = "rgba(0, 230, 118, 0.12)" if styles.COLOR_PRIMARY == "#00E676" else "rgba(0, 176, 255, 0.12)"
            self.setStyleSheet(f"""
                QFrame#PromptCardActive {{
                    background-color: {bg_rgba};
                    border: 2px solid {styles.COLOR_PRIMARY};
                    border-radius: 6px;
                }}
            """)
            if not (self.is_system and self.is_starred):
                self.badge_lbl.setText("")
                self.badge_lbl.setStyleSheet(f"color: {styles.COLOR_PRIMARY}; font-size: 11px; font-weight: bold; background: transparent; border: none;")
        else:
            self.setObjectName("PromptCardInactive")
            self.setStyleSheet(f"""
                QFrame#PromptCardInactive {{
                    background-color: {styles.COLOR_BG};
                    border: 1px solid {styles.COLOR_BORDER_LIGHT};
                    border-radius: 6px;
                }}
                QFrame#PromptCardInactive:hover {{
                    border: 1px solid {styles.COLOR_PRIMARY};
                }}
            """)
            if self.is_system and self.is_starred:
                self.badge_lbl.setText("⭐")
                self.badge_lbl.setStyleSheet("color: #ff8f00; font-size: 11px; background: transparent; border: none;")
            else:
                self.badge_lbl.setText("")
                
        self.style().unpolish(self)
        self.style().polish(self)


class CreatePromptRow(QFrame):
    clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CreateRow")
        self.setFixedHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame#CreateRow {{
                background-color: {styles.COLOR_BG};
                border: 1px dashed {styles.COLOR_BORDER_LIGHT};
                border-radius: 6px;
            }}
            QFrame#CreateRow:hover {{
                border: 1px solid {styles.COLOR_PRIMARY};
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(6)
        
        plus_lbl = QLabel("+")
        plus_lbl.setStyleSheet(f"color: {styles.COLOR_PRIMARY}; font-size: 18px; font-weight: bold; background: transparent; border: none;")
        layout.addWidget(plus_lbl)
        
        text_lbl = QLabel("Создать новый промпт")
        text_lbl.setStyleSheet(f"color: {styles.COLOR_PRIMARY}; font-size: 11px; font-weight: bold; background: transparent; border: none;")
        layout.addWidget(text_lbl)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class WorkModePresetCard(QFrame):
    clicked = pyqtSignal(str)
    
    def __init__(self, key, icon, title, subtitle, parent=None):
        super().__init__(parent)
        self.key = key
        self.setObjectName("WorkModeCardInactive")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        
        # Icon
        self.icon_lbl = QLabel(icon)
        self.icon_lbl.setFixedSize(36, 36)
        self.icon_lbl.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY_DARK}; border-radius: 8px; font-size: 16px; qproperty-alignment: AlignCenter; color: {'#000000' if styles.COLOR_PRIMARY == '#00E676' else '#FFFFFF'};")
        layout.addWidget(self.icon_lbl)
        
        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet("font-weight: bold; color: white; font-size: 12px; border: none; background: transparent;")
        self.sub_lbl = QLabel(subtitle)
        self.sub_lbl.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 10px; border: none; background: transparent;")
        text_layout.addWidget(self.title_lbl)
        text_layout.addWidget(self.sub_lbl)
        
        layout.addLayout(text_layout, 1)
        
    def set_active(self, active):
        if active:
            self.setObjectName("WorkModeCardActive")
            bg_rgba = "rgba(0, 230, 118, 0.15)" if styles.COLOR_PRIMARY == "#00E676" else "rgba(0, 176, 255, 0.15)"
            self.setStyleSheet(f"""
                QFrame#WorkModeCardActive {{
                    background-color: {bg_rgba};
                    border: 2px solid {styles.COLOR_PRIMARY};
                    border-radius: 10px;
                }}
            """)
        else:
            self.setObjectName("WorkModeCardInactive")
            self.setStyleSheet(f"""
                QFrame#WorkModeCardInactive {{
                    background-color: {styles.COLOR_BG};
                    border: 1px dashed {styles.COLOR_BORDER};
                    border-radius: 10px;
                }}
                QFrame#WorkModeCardInactive:hover {{
                    border: 1px solid {styles.COLOR_PRIMARY};
                }}
            """)
        self.style().unpolish(self)
        self.style().polish(self)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)
        super().mousePressEvent(event)


class EditAccountChannelsDialog(QDialog):
    def __init__(self, acc_name, initial_channels, initial_prompt, parent=None):
        super().__init__(parent)
        self.acc_name = acc_name
        self.setWindowTitle(f"Настройки: {acc_name}")
        self.resize(550, 450)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMinMaxButtonsHint)
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {styles.COLOR_BG};
                border: 1px solid {styles.COLOR_BORDER};
            }}
            QLabel {{
                color: #FFFFFF;
                font-family: '{styles.FONT_NAME}', sans-serif;
            }}
            QPushButton {{
                background-color: {styles.COLOR_HOVER_BG};
                color: {styles.COLOR_PRIMARY};
                border: 1px solid {styles.COLOR_BORDER_DARK};
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                font-family: '{styles.FONT_NAME}', sans-serif;
            }}
            QPushButton:hover {{
                background-color: {styles.COLOR_SELECT_BG};
                border-color: {styles.COLOR_PRIMARY};
                color: #FFFFFF;
            }}
            QTextEdit {{
                background-color: {styles.COLOR_CONSOLE_BG};
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 6px;
                padding: 6px;
                color: #E0E0E0;
                font-family: monospace;
            }}
            QTextEdit:focus {{
                border: 1px solid {styles.COLOR_PRIMARY};
                background-color: {styles.COLOR_HOVER_BG};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        header_lbl = QLabel(f"Тонкая настройка аккаунта: {acc_name}")
        header_lbl.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {styles.COLOR_PRIMARY};")
        layout.addWidget(header_lbl)
        
        layout.addWidget(QLabel("Целевые каналы для этого аккаунта (по одному на строку):", styleSheet="font-weight: bold; color: #B0B0B0; font-size: 11px;"))
        self.txt_channels = QTextEdit()
        self.txt_channels.setPlaceholderText("@channel_username\\nhttps://t.me/channel_link")
        self.txt_channels.setPlainText(initial_channels)
        layout.addWidget(self.txt_channels, stretch=3)
        
        layout.addWidget(QLabel("Индивидуальный системный промпт ИИ (оставьте пустым для промпта по умолчанию):", styleSheet="font-weight: bold; color: #B0B0B0; font-size: 11px;"))
        self.txt_prompt = QTextEdit()
        self.txt_prompt.setPlaceholderText("Например: Отвечай с юмором, пиши очень кратко...")
        self.txt_prompt.setPlainText(initial_prompt)
        layout.addWidget(self.txt_prompt, stretch=2)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        btn_cancel = QPushButton("Отмена")
        btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancel)
        
        self.btn_save = QPushButton("💾 Применить")
        self.btn_save.setObjectName("ApplyBtn")
        self.btn_save.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY_DARK}; color: #000000;")
        self.btn_save.clicked.connect(self.accept)
        buttons_layout.addWidget(self.btn_save)
        
        layout.addLayout(buttons_layout)
        
    def get_data(self) -> tuple:
        return self.txt_channels.toPlainText().strip(), self.txt_prompt.toPlainText().strip()


class AccountDistributionCard(QFrame):
    channelsChanged = pyqtSignal(str, str)
    promptChanged = pyqtSignal(str, str)
    
    def __init__(self, acc, initial_channels, initial_prompt="", parent=None):
        super().__init__(parent)
        self.acc = acc
        self.acc_name = acc["name"]
        self.setObjectName("DistCard")
        from src import styles
        self.setStyleSheet(f"""
            QFrame#DistCard {{
                background-color: {styles.COLOR_BG};
                border: 1px solid {styles.COLOR_BORDER_LIGHT};
                border-radius: 8px;
            }}
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(6)
        
        # Header row
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)
        
        # Avatar icon or placeholder
        avatar_lbl = QLabel("👤")
        avatar_lbl.setFixedSize(24, 24)
        avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        av_bg = "rgba(0, 230, 118, 0.15)" if styles.COLOR_PRIMARY == "#00E676" else "rgba(0, 176, 255, 0.15)"
        avatar_lbl.setStyleSheet(f"background-color: {av_bg}; color: {styles.COLOR_PRIMARY}; border-radius: 12px; font-size: 11px;")
        header_layout.addWidget(avatar_lbl)
        
        # Name & Phone
        name_phone_layout = QVBoxLayout()
        name_phone_layout.setSpacing(0)
        self.name_lbl = QLabel(self.acc_name)
        self.name_lbl.setStyleSheet("font-weight: bold; color: white; font-size: 11px;")
        name_phone_layout.addWidget(self.name_lbl)
        
        # Deterministic phone/id
        dummy_phone = str(916000000000 + abs(hash(self.acc_name)) % 1000000000)
        self.phone_lbl = QLabel(dummy_phone)
        self.phone_lbl.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 9px;")
        name_phone_layout.addWidget(self.phone_lbl)
        header_layout.addLayout(name_phone_layout, 1)
        
        # Chevron button
        self.btn_chevron = QPushButton("∨")
        self.btn_chevron.setFixedSize(20, 20)
        self.btn_chevron.setStyleSheet(f"background: transparent; color: {styles.COLOR_TEXT_MUTED}; border: none; font-size: 12px; font-weight: bold;")
        self.btn_chevron.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_chevron.clicked.connect(self.toggle_expanded)
        header_layout.addWidget(self.btn_chevron)
        
        self.main_layout.addLayout(header_layout)
        
        # Counter row
        counter_layout = QHBoxLayout()
        self.counter_lbl = QLabel("# 0 кан.")
        self.counter_lbl.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 10px; font-weight: bold;")
        counter_layout.addWidget(self.counter_lbl)
        counter_layout.addStretch()
        
        # Prompt Status Badge
        self.prompt_status_lbl = QLabel("Свой промпт"if initial_prompt else "Дефолт")
        self.prompt_status_lbl.setStyleSheet(f"color: {styles.COLOR_PRIMARY}; font-size: 10px; font-weight: bold;")
        counter_layout.addWidget(self.prompt_status_lbl)
        
        self.main_layout.addLayout(counter_layout)
        
        # Expandable TextEdit for Channels
        self.txt_channels = QTextEdit()
        self.txt_channels.setFixedHeight(80)
        self.txt_channels.setPlaceholderText("Каналы (по одному на строку)...")
        self.txt_channels.setStyleSheet(f"""
            QTextEdit {{
                background-color: {styles.COLOR_CONSOLE_BG};
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 6px;
                padding: 4px;
                color: #E0E0E0;
                font-size: 10px;
            }}
        """)
        self.txt_channels.setPlainText(initial_channels)
        self.txt_channels.textChanged.connect(self.on_text_changed)
        self.main_layout.addWidget(self.txt_channels)
        
        # Expandable TextEdit for Prompt
        self.txt_prompt = QTextEdit()
        self.txt_prompt.setFixedHeight(50)
        self.txt_prompt.setPlaceholderText("Системный промпт для этого аккаунта...")
        self.txt_prompt.setStyleSheet(f"""
            QTextEdit {{
                background-color: {styles.COLOR_CONSOLE_BG};
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 6px;
                padding: 4px;
                color: #A0E0FF;
                font-size: 10px;
            }}
        """)
        self.txt_prompt.setPlainText(initial_prompt)
        self.txt_prompt.textChanged.connect(self.on_prompt_text_changed)
        self.main_layout.addWidget(self.txt_prompt)
        
        self.txt_channels.setVisible(False)
        self.txt_prompt.setVisible(False)
        self.is_expanded = False
        self.update_counter(initial_channels)
        
    def toggle_expanded(self):
        self.is_expanded = not self.is_expanded
        self.txt_channels.setVisible(self.is_expanded)
        self.txt_prompt.setVisible(self.is_expanded)
        self.btn_chevron.setText("∧" if self.is_expanded else "∨")
        
    def set_expanded(self, expanded):
        self.is_expanded = expanded
        self.txt_channels.setVisible(expanded)
        self.txt_prompt.setVisible(expanded)
        self.btn_chevron.setText("∧" if expanded else "∨")
        
    def on_text_changed(self):
        text = self.txt_channels.toPlainText()
        self.update_counter(text)
        self.channelsChanged.emit(self.acc_name, text)

    def on_prompt_text_changed(self):
        text = self.txt_prompt.toPlainText().strip()
        if text:
            self.prompt_status_lbl.setText("Свой промпт")
        else:
            self.prompt_status_lbl.setText("Дефолт")
        self.promptChanged.emit(self.acc_name, text)
        
    def update_counter(self, text):
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        count = len(lines)
        has_folder = any("addlist" in line or "joinchat" in line for line in lines)
        
        if has_folder:
            self.counter_lbl.setText(f"# {count} папок")
        else:
            self.counter_lbl.setText(f"# {count} кан.")


class ApiTestWorker(QThread):
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, provider, api_key, base_url, model_name, parent=None):
        super().__init__(parent)
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model_name

    def run(self):
        import requests
        url = self.base_url.strip()
        if not url:
            if self.provider == "Google Gemini":
                url = "https://generativelanguage.googleapis.com/v1beta/openai"
            else:
                url = "https://api.openai.com/v1"
        if url.endswith("/"):
            url = url[:-1]
                
        model = self.model_name.strip()
        if not model:
            if self.provider == "Google Gemini":
                model = "gemini-2.5-flash"
            else:
                model = "gpt-4o-mini"
                
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "max_tokens": 5
        }
        
        try:
            response = requests.post(f"{url}/chat/completions", headers=headers, json=payload, timeout=12)
            if response.status_code == 200:
                self.finished_signal.emit(True, "Подключение успешно установлено!")
            else:
                try:
                    err = response.json().get("error", {}).get("message", response.text)
                except Exception:
                    err = response.text
                self.finished_signal.emit(False, f"Ошибка API ({response.status_code}): {err}")
        except Exception as e:
            self.finished_signal.emit(False, f"Ошибка подключения: {e}")


class NewModulesPage(QWidget):
    api_test_signal = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_test_signal.connect(self.append_log)
        self.mgr = parent
        self.worker = None
        self.warmer_worker = None
        self.current_avatar_path = None
        self.switches = {}
        self.current_module = "warmup"
        
        # Данные для двухпанельного выбора
        self.all_accounts = []
        self.selected_accounts = []
        
        # Данные для распределения каналов в Нейрокомментинге
        self.selected_work_mode = "multithreaded"
        self.distribution_cards = []
        self.auto_distributed_channels = {}
        
        # Системные промпты (словарь)
        self.system_prompts = {
            "positive": {
                "title": "Позитивный комментарий",
                "text": "Напиши короткий, позитивный и дружелюбный комментарий к публикации. Поддержи автора, вырази одобрение или согласие в простой разговорной манере без использования хэштегов.",
                "starred": True
            },
            "intimate": {
                "title": "Интимный",
                "text": "Напиши кокетливый, интригующий и слегка загадочный комментарий к посту. Пиши легко, непринужденно, проявляя дружеский или романтический интерес, но оставаясь в рамках приличия.",
                "starred": False
            },
            "emotional": {
                "title": "Эмоциональный отклик",
                "text": "Напиши эмоциональный и живой комментарий. Вырази яркие эмоции (восторг, удивление или искреннее сочувствие в зависимости от темы поста), пиши естественно.",
                "starred": False
            },
            "question": {
                "title": "Вопрос автору",
                "text": "Напиши вовлекающий комментарий в виде вопроса автору. Задай один интересный или уточняющий вопрос по теме поста, чтобы завязать беседу.",
                "starred": False
            },
            "short": {
                "title": "Краткий отзыв",
                "text": "Напиши очень краткий, емкий отзыв на пост. Буквально 3-5 слов, выражающих суть твоего мнения в разговорном стиле.",
                "starred": False
            },
            "analytical": {
                "title": "Аналитический подход",
                "text": "Напиши вдумчивый, конструктивный и серьезный комментарий к посту. Поделись кратким аргументом или аналитическим выводом по теме.",
                "starred": False
            }
        }
        
        # Пользовательские промпты (список словарей)
        self.custom_prompts = [
            {"name": "психолог", "text": "Ответь на пост с позиции понимающего, эмпатичного психолога. Поддержи автора, предложи посмотреть на ситуацию глубже."},
            {"name": "хейтер", "text": "Напиши саркастический, слегка критический, но забавный комментарий. Подвергни сомнению слова автора, используя тонкую иронию."},
            {"name": "дейтинг", "text": "Напиши общительный, открытый комментарий для привлечения внимания. Сделай комплимент или предложи пообщаться в легкой игровой форме."},
            {"name": "31", "text": "Напиши оригинальный комментарий с использованием числовых фактов или короткого житейского наблюдения."}
        ]
        
        # Имя активного промпта
        self.active_prompt_name = "Позитивный комментарий"
        self.prompt_cards = {}
        
        self.setStyleSheet(self.get_custom_stylesheet())
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # 1. Левая панель - список новых модулей
        left_frame = QFrame()
        left_frame.setObjectName("LeftSectionFrame")
        left_frame.setFixedWidth(280)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(10, 15, 10, 15)
        left_layout.setSpacing(10)

        left_layout.addWidget(QLabel("Каталог модулей", objectName="SectionTitle"))

        # Scroll area for modules list
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_content.setObjectName("ScrollContent")
        self.scroll_layout = QVBoxLayout(scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_area.setWidget(scroll_content)
        left_layout.addWidget(scroll_area)

        main_layout.addWidget(left_frame)

        # 2. Правая панель с прокруткой - рабочая область
        self.right_scroll = QScrollArea()
        self.right_scroll.setWidgetResizable(True)
        self.right_scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {styles.COLOR_BG}; }}")
        
        self.right_widget = QWidget()
        self.right_widget.setObjectName("RightWidget")
        self.right_layout = QVBoxLayout(self.right_widget)
        self.right_layout.setContentsMargins(10, 0, 10, 0)
        self.right_layout.setSpacing(20)
        
        self.right_scroll.setWidget(self.right_widget)
        main_layout.addWidget(self.right_scroll, 1)

        self.setup_modules_list()
        self.show_warmup_steroids_module()

    def setup_modules_list(self):
        self.btn_warmup = QPushButton("Прогрев (Стероиды)")
        self.btn_warmup.setIcon(QIcon(str(ROCKET_ICON_PATH)))
        self.btn_warmup.setObjectName("ModuleListBtnActive")
        self.btn_warmup.clicked.connect(self.on_warmup_clicked)
        self.scroll_layout.addWidget(self.btn_warmup)

        self.btn_commenting = QPushButton("💬 Нейрокомментинг (Стероиды)")
        self.btn_commenting.setObjectName("ModuleListBtnInactive")
        self.btn_commenting.clicked.connect(self.on_commenting_clicked)
        self.scroll_layout.addWidget(self.btn_commenting)

        btn_bot = QPushButton("AI Автоответчик v2\n(Скоро)")
        btn_bot.setIcon(QIcon(str(ROBOT_ICON_PATH)))
        btn_bot.setObjectName("ModuleListBtnDisabled")
        btn_bot.setEnabled(False)
        self.scroll_layout.addWidget(btn_bot)

        btn_inviter = QPushButton("Умный Инвайтер v2\n(Скоро)")
        btn_inviter.setIcon(QIcon(str(ROCKET_ICON_PATH)))
        btn_inviter.setObjectName("ModuleListBtnDisabled")
        btn_inviter.setEnabled(False)
        self.scroll_layout.addWidget(btn_inviter)

    def update_module_list_selection(self, active_btn):
        for btn in [self.btn_warmup, self.btn_commenting]:
            if btn == active_btn:
                btn.setObjectName("ModuleListBtnActive")
            else:
                btn.setObjectName("ModuleListBtnInactive")
            btn.setStyle(btn.style())

    def on_warmup_clicked(self):
        self.current_module = "warmup"
        self.update_module_list_selection(self.btn_warmup)
        self.show_warmup_steroids_module()

    def on_commenting_clicked(self):
        self.current_module = "commenting"
        self.update_module_list_selection(self.btn_commenting)
        self.show_neurocommenting_module()

    def _clear_right_layout(self):
        self.distribution_cards.clear()
        self.prompt_cards.clear()
        while self.right_layout.count():
            item = self.right_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    self._clear_layout(item.layout())

    def show_warmup_steroids_module(self):
        self._clear_right_layout()
        self.switches.clear()

        # Шапка
        title_layout = QHBoxLayout()
        module_title = QLabel("Прогрев и Управление Профилем (Стероиды)")
        module_title.setObjectName("ModuleWorkTitle")
        title_layout.addWidget(module_title)
        title_layout.addStretch()
        
        title_layout.addWidget(QLabel("Аккаунт (Редактор):"))
        self.acc_combo = QComboBox()
        self.acc_combo.setFixedWidth(160)
        self.acc_combo.currentTextChanged.connect(self.on_account_changed)
        title_layout.addWidget(self.acc_combo)

        btn_refresh = QPushButton()
        btn_refresh.setIcon(get_icon(FOLDER_ICON_PATH))
        btn_refresh.setIconSize(QSize(16, 16))
        btn_refresh.setFixedSize(30, 30)
        btn_refresh.clicked.connect(self.refresh_accounts)
        title_layout.addWidget(btn_refresh)
        self.right_layout.addLayout(title_layout)

        # ----------------------------------------------------
        # БЛОК 1: Настройка профиля
        # ----------------------------------------------------
        profile_frame = QFrame()
        profile_frame.setObjectName("ContentSectionFrame")
        profile_layout = QVBoxLayout(profile_frame)
        profile_layout.setContentsMargins(15, 15, 15, 15)
        
        profile_section_title = QLabel("Настройка профиля Telegram")
        profile_section_title.setObjectName("SectionSubTitle")
        profile_layout.addWidget(profile_section_title)

        profile_container = QHBoxLayout()
        profile_container.setSpacing(20)

        # Аватар
        avatar_layout = QVBoxLayout()
        avatar_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter)
        self.avatar_label = DragDropLabel()
        self.avatar_label.setObjectName("TelegramAvatarLabel")
        self.avatar_label.setFixedSize(110, 110)
        self.avatar_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.installEventFilter(self)
        self.avatar_label.fileDropped.connect(self.handle_avatar_drop)
        avatar_layout.addWidget(self.avatar_label)
        
        avatar_sub = QLabel("Нажмите для смены")
        avatar_sub.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 10px; margin-top: 5px;")
        avatar_layout.addWidget(avatar_sub, alignment=Qt.AlignmentFlag.AlignCenter)

        self.btn_avatar_gallery = QPushButton("🖼️ Выбрать из папки")
        self.btn_avatar_gallery.setStyleSheet("font-size: 10px; padding: 3px 6px; margin-top: 4px;")
        self.btn_avatar_gallery.clicked.connect(self.show_avatar_gallery_dialog)
        avatar_layout.addWidget(self.btn_avatar_gallery, alignment=Qt.AlignmentFlag.AlignCenter)

        profile_container.addLayout(avatar_layout)

        # Форма
        form_layout = QVBoxLayout()
        form_layout.setSpacing(8)

        name_h = QHBoxLayout()
        name_h.addWidget(QLabel("Имя:     ", styleSheet=f"font-weight: bold; color: {styles.COLOR_TEXT_MUTED};"))
        self.input_first_name = QLineEdit()
        self.input_first_name.setPlaceholderText("Имя в Telegram")
        name_h.addWidget(self.input_first_name)
        form_layout.addLayout(name_h)

        lname_h = QHBoxLayout()
        lname_h.addWidget(QLabel("Фамилия: ", styleSheet=f"font-weight: bold; color: {styles.COLOR_TEXT_MUTED};"))
        self.input_last_name = QLineEdit()
        self.input_last_name.setPlaceholderText("Фамилия (опционально)")
        lname_h.addWidget(self.input_last_name)
        form_layout.addLayout(lname_h)

        bio_h = QHBoxLayout()
        bio_h.addWidget(QLabel("О себе:  ", styleSheet=f"font-weight: bold; color: {styles.COLOR_TEXT_MUTED};"))
        self.input_bio = QLineEdit()
        self.input_bio.setPlaceholderText("Описание профиля (макс. 70 символов)")
        self.input_bio.setMaxLength(70)
        self.input_bio.textChanged.connect(self.update_bio_counter)
        bio_h.addWidget(self.input_bio)
        form_layout.addLayout(bio_h)

        self.bio_counter = QLabel("0 / 70")
        self.bio_counter.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 11px;")
        self.bio_counter.setAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.addWidget(self.bio_counter)

        channel_h = QHBoxLayout()
        channel_h.addWidget(QLabel("Канал:   ", styleSheet=f"font-weight: bold; color: {styles.COLOR_TEXT_MUTED};"))
        self.input_bound_channel = QLineEdit()
        self.input_bound_channel.setPlaceholderText("@channel_username или ссылка")
        channel_h.addWidget(self.input_bound_channel)
        form_layout.addLayout(channel_h)

        profile_container.addLayout(form_layout, 1)
        profile_layout.addLayout(profile_container)
        
        prof_btns = QHBoxLayout()
        prof_btns.addStretch()
        self.btn_load_tg = QPushButton("Загрузить из TG")
        self.btn_load_tg.setIcon(QIcon(str(REFRESH_ICON_PATH)))
        self.btn_load_tg.clicked.connect(self.load_data_from_telegram)
        prof_btns.addWidget(self.btn_load_tg)
        
        self.btn_save_profile = QPushButton("💾 Применить профиль")
        self.btn_save_profile.setObjectName("ApplyBtn")
        self.btn_save_profile.clicked.connect(self.save_profile_changes)
        prof_btns.addWidget(self.btn_save_profile)
        profile_layout.addLayout(prof_btns)

        self.right_layout.addWidget(profile_frame)

        # ----------------------------------------------------
        # БЛОК 2: Управление промо-каналом
        # ----------------------------------------------------
        channel_frame = QFrame()
        channel_frame.setObjectName("ContentSectionFrame")
        channel_layout = QVBoxLayout(channel_frame)
        channel_layout.setContentsMargins(15, 15, 15, 15)
        channel_layout.setSpacing(12)

        self.channel_section_title = QLabel("Управление промо-каналом")
        self.channel_section_title.setObjectName("SectionSubTitle")
        channel_layout.addWidget(self.channel_section_title)

        # Контейнер профиля (аватарка и поля)
        chan_container = QHBoxLayout()
        chan_container.setSpacing(20)

        # Аватар
        chan_avatar_layout = QVBoxLayout()
        chan_avatar_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignCenter)
        self.chan_avatar_label = DragDropLabel()
        self.chan_avatar_label.setObjectName("TelegramAvatarLabel")
        self.chan_avatar_label.setFixedSize(110, 110)
        self.chan_avatar_label.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chan_avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chan_avatar_label.installEventFilter(self)
        self.chan_avatar_label.fileDropped.connect(self.handle_channel_avatar_drop)
        chan_avatar_layout.addWidget(self.chan_avatar_label)
        
        self.chan_avatar_sub = QLabel("Нажмите для смены")
        self.chan_avatar_sub.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 10px; margin-top: 5px;")
        chan_avatar_layout.addWidget(self.chan_avatar_sub, alignment=Qt.AlignmentFlag.AlignCenter)

        self.btn_chan_avatar_gallery = QPushButton("🖼️ Выбрать из папки")
        self.btn_chan_avatar_gallery.setStyleSheet("font-size: 10px; padding: 3px 6px; margin-top: 4px;")
        self.btn_chan_avatar_gallery.clicked.connect(self.show_channel_avatar_gallery_dialog)
        chan_avatar_layout.addWidget(self.btn_chan_avatar_gallery, alignment=Qt.AlignmentFlag.AlignCenter)

        chan_container.addLayout(chan_avatar_layout)

        # Форма полей канала
        chan_form_layout = QVBoxLayout()
        chan_form_layout.setSpacing(8)

        # Название
        chan_title_h = QHBoxLayout()
        chan_title_h.addWidget(QLabel("Название:", styleSheet=f"font-weight: bold; color: {styles.COLOR_TEXT_MUTED}; min-width: 70px;"))
        self.input_chan_title = QLineEdit()
        self.input_chan_title.setPlaceholderText("Название канала")
        chan_title_h.addWidget(self.input_chan_title)
        chan_form_layout.addLayout(chan_title_h)

        # Описание
        chan_desc_h = QHBoxLayout()
        chan_desc_h.addWidget(QLabel("Описание:", styleSheet=f"font-weight: bold; color: {styles.COLOR_TEXT_MUTED}; min-width: 70px;"))
        self.input_chan_desc = QLineEdit()
        self.input_chan_desc.setPlaceholderText("Описание канала")
        chan_desc_h.addWidget(self.input_chan_desc)
        chan_form_layout.addLayout(chan_desc_h)

        # Юзернейм (используется при создании)
        chan_user_h = QHBoxLayout()
        self.chan_user_lbl = QLabel("Юзернейм:", styleSheet=f"font-weight: bold; color: {styles.COLOR_TEXT_MUTED}; min-width: 70px;")
        chan_user_h.addWidget(self.chan_user_lbl)
        self.input_chan_user = QLineEdit()
        self.input_chan_user.setPlaceholderText("@username (для создания публичного)")
        chan_user_h.addWidget(self.input_chan_user)
        chan_form_layout.addLayout(chan_user_h)

        # Кнопка действия канала (Создать или Сохранить)
        chan_btn_h = QHBoxLayout()
        chan_btn_h.addStretch()
        self.btn_channel_action = QPushButton("✨ Создать канал")
        self.btn_channel_action.setObjectName("ApplyBtn")
        self.btn_channel_action.clicked.connect(self.on_channel_action_clicked)
        chan_btn_h.addWidget(self.btn_channel_action)
        chan_form_layout.addLayout(chan_btn_h)

        chan_container.addLayout(chan_form_layout, 1)
        channel_layout.addLayout(chan_container)

        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setStyleSheet(f"background-color: {styles.COLOR_BORDER}; max-height: 1px; border: none;")
        channel_layout.addWidget(separator)

        # Секция постинга
        post_title = QLabel("Создать новый пост")
        post_title.setStyleSheet(f"color: {styles.COLOR_PRIMARY}; font-weight: bold; font-size: 11px;")
        channel_layout.addWidget(post_title)

        post_fields_layout = QVBoxLayout()
        post_fields_layout.setSpacing(6)

        # Текст поста
        self.input_post_text = QTextEdit()
        self.input_post_text.setPlaceholderText("Введите текст поста...")
        self.input_post_text.setFixedHeight(80)
        self.input_post_text.setStyleSheet(f"background-color: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 6px; padding: 4px; color: #E0E0E0;")
        post_fields_layout.addWidget(self.input_post_text)

        # Фото (опционально)
        photo_h = QHBoxLayout()
        photo_h.addWidget(QLabel("Фото:", styleSheet=f"font-weight: bold; color: {styles.COLOR_TEXT_MUTED};"))
        self.input_post_photo = QLineEdit()
        self.input_post_photo.setPlaceholderText("Путь к изображению (не выбрано)")
        self.input_post_photo.setReadOnly(True)
        photo_h.addWidget(self.input_post_photo, 1)

        self.btn_browse_post_photo = QPushButton("Обзор...")
        self.btn_browse_post_photo.setStyleSheet(f"background-color: {styles.COLOR_HOVER_BG}; color: {styles.COLOR_PRIMARY}; border: 1px solid {styles.COLOR_BORDER_DARK}; border-radius: 4px; padding: 4px 8px;")
        self.btn_browse_post_photo.clicked.connect(self.choose_post_photo)
        photo_h.addWidget(self.btn_browse_post_photo)

        self.btn_clear_post_photo = QPushButton("Сбросить")
        self.btn_clear_post_photo.setStyleSheet("background-color: #2E1111; color: #FF5252; border: 1px solid #5E2424; border-radius: 4px; padding: 4px 8px;")
        self.btn_clear_post_photo.clicked.connect(self.clear_post_photo)
        photo_h.addWidget(self.btn_clear_post_photo)

        post_fields_layout.addLayout(photo_h)

        # Кнопка отправки поста
        post_btn_h = QHBoxLayout()
        post_btn_h.addStretch()
        self.btn_publish_post = QPushButton("📢 Опубликовать пост")
        self.btn_publish_post.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY_DARK}; color: white; font-weight: bold; padding: 6px 12px;")
        self.btn_publish_post.clicked.connect(self.publish_channel_post)
        post_btn_h.addWidget(self.btn_publish_post)
        post_fields_layout.addLayout(post_btn_h)

        channel_layout.addLayout(post_fields_layout)
        self.right_layout.addWidget(channel_frame)

        # ----------------------------------------------------
        # БЛОК 2.5: Двухпанельный Выбор Аккаунтов (NEW)
        # ----------------------------------------------------
        selector_frame = QFrame()
        selector_frame.setObjectName("ContentSectionFrame")
        selector_layout = QVBoxLayout(selector_frame)
        selector_layout.setContentsMargins(15, 15, 15, 15)
        selector_layout.setSpacing(10)

        # Шапка выбора
        selector_header = QHBoxLayout()
        selector_title_layout = QVBoxLayout()
        selector_title = QLabel("Выбор аккаунтов")
        selector_title.setObjectName("SectionSubTitle")
        selector_title_layout.addWidget(selector_title)
        selector_header.addLayout(selector_title_layout)
        selector_header.addStretch()
        
        self.lbl_selected_count = QLabel("0 выбрано")
        bg_rgba = "rgba(0, 230, 118, 0.1)" if styles.COLOR_PRIMARY == "#00E676" else "rgba(0, 176, 255, 0.1)"
        border_rgba = "rgba(0, 230, 118, 0.3)" if styles.COLOR_PRIMARY == "#00E676" else "rgba(0, 176, 255, 0.3)"
        self.lbl_selected_count.setStyleSheet(f"color: {styles.COLOR_PRIMARY}; font-weight: bold; background-color: {bg_rgba}; padding: 4px 10px; border-radius: 6px; border: 1px solid {border_rgba};")
        selector_header.addWidget(self.lbl_selected_count)
        selector_layout.addLayout(selector_header)

        # Две панели рядом
        panels_h = QHBoxLayout()
        panels_h.setSpacing(15)

        # Левая панель - Доступные
        avail_panel = QFrame()
        avail_panel.setObjectName("SelectionCard")
        avail_layout = QVBoxLayout(avail_panel)
        avail_layout.setContentsMargins(10, 10, 10, 10)
        avail_layout.setSpacing(8)

        avail_header = QHBoxLayout()
        avail_title_lbl = QLabel("Доступные аккаунты")
        avail_title_lbl.setStyleSheet(f"font-weight: bold; color: {styles.COLOR_PRIMARY};")
        avail_header.addWidget(avail_title_lbl)
        avail_header.addStretch()
        self.lbl_avail_count = QLabel("Всего: 0")
        self.lbl_avail_count.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 11px;")
        avail_header.addWidget(self.lbl_avail_count)
        avail_layout.addLayout(avail_header)

        # Поиск
        self.search_selector = QLineEdit()
        self.search_selector.setPlaceholderText("🔍 Поиск по имени...")
        self.search_selector.textChanged.connect(self.update_selector_ui)
        avail_layout.addWidget(self.search_selector)

        # Фильтры
        filters_layout = QHBoxLayout()
        self.cb_only_proxy = QCheckBox("Рабочие прокси")
        self.cb_only_proxy.stateChanged.connect(self.update_selector_ui)
        filters_layout.addWidget(self.cb_only_proxy)

        self.cb_hide_running = QCheckBox("Скрыть в работе")
        self.cb_hide_running.stateChanged.connect(self.update_selector_ui)
        filters_layout.addWidget(self.cb_hide_running)
        avail_layout.addLayout(filters_layout)

        # Добавить все
        btn_add_all = QPushButton(">> Добавить все")
        bg_btn = "rgba(0, 200, 83, 0.15)" if styles.COLOR_PRIMARY == "#00E676" else "rgba(0, 145, 234, 0.15)"
        btn_add_all.setStyleSheet(f"background-color: {bg_btn}; color: {styles.COLOR_PRIMARY}; border: 1px solid {styles.COLOR_PRIMARY}; font-size: 11px; padding: 4px;")
        btn_add_all.clicked.connect(self.add_all_filtered_to_selected)
        avail_layout.addWidget(btn_add_all)

        # Скролл доступных
        self.avail_scroll = QScrollArea()
        self.avail_scroll.setWidgetResizable(True)
        self.avail_scroll.setFixedHeight(220)
        self.avail_scroll.setStyleSheet(f"QScrollArea {{ background-color: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER_LIGHT}; border-radius: 6px; }}")
        self.avail_scroll_widget = QWidget()
        self.avail_scroll_layout = QVBoxLayout(self.avail_scroll_widget)
        self.avail_scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.avail_scroll_layout.setSpacing(5)
        self.avail_scroll_layout.setContentsMargins(5, 5, 5, 5)
        self.avail_scroll.setWidget(self.avail_scroll_widget)
        avail_layout.addWidget(self.avail_scroll)
        panels_h.addWidget(avail_panel, 1)

        # Правая панель - Выбранные
        select_panel = QFrame()
        select_panel.setObjectName("SelectionCard")
        select_layout = QVBoxLayout(select_panel)
        select_layout.setContentsMargins(10, 10, 10, 10)
        select_layout.setSpacing(8)

        select_header = QHBoxLayout()
        select_title_lbl = QLabel("Выбрано для прогрева")
        select_title_lbl.setStyleSheet(f"font-weight: bold; color: {styles.COLOR_PRIMARY};")
        select_header.addWidget(select_title_lbl)
        select_header.addStretch()
        select_layout.addLayout(select_header)

        # Кнопки действий над выбранными
        select_actions_h = QHBoxLayout()
        select_actions_h.setSpacing(6)
        
        btn_remove_all = QPushButton("<< Удалить все")
        btn_remove_all.setStyleSheet("background-color: rgba(198, 40, 40, 0.15); color: #FF5252; border: 1px solid #FF5252; font-size: 11px; padding: 4px;")
        btn_remove_all.clicked.connect(self.remove_all_from_selected)
        select_actions_h.addWidget(btn_remove_all, 1)
        
        self.btn_random_avatars = QPushButton("🎲 Случайные аватарки")
        bg_rand = "rgba(0, 230, 118, 0.15)" if styles.COLOR_PRIMARY == "#00E676" else "rgba(0, 176, 255, 0.15)"
        self.btn_random_avatars.setStyleSheet(f"background-color: {bg_rand}; color: {styles.COLOR_PRIMARY}; border: 1px solid {styles.COLOR_PRIMARY}; font-size: 11px; padding: 4px;")
        self.btn_random_avatars.clicked.connect(self.randomize_selected_avatars)
        select_actions_h.addWidget(self.btn_random_avatars, 1)
        
        select_layout.addLayout(select_actions_h)

        # Скролл выбранных
        self.selected_scroll = QScrollArea()
        self.selected_scroll.setWidgetResizable(True)
        self.selected_scroll.setFixedHeight(260) # на один уровень с левой панелью
        self.selected_scroll.setStyleSheet(f"QScrollArea {{ background-color: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER_LIGHT}; border-radius: 6px; }}")
        self.selected_scroll_widget = QWidget()
        self.selected_scroll_layout = QVBoxLayout(self.selected_scroll_widget)
        self.selected_scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.selected_scroll_layout.setSpacing(5)
        self.selected_scroll_layout.setContentsMargins(5, 5, 5, 5)
        self.selected_scroll.setWidget(self.selected_scroll_widget)
        select_layout.addWidget(self.selected_scroll)
        panels_h.addWidget(select_panel, 1)

        selector_layout.addLayout(panels_h)
        self.right_layout.addWidget(selector_frame)

        # ----------------------------------------------------
        # БЛОК 3: Тонкая настройка действий прогрева
        # ----------------------------------------------------
        settings_frame = QFrame()
        settings_frame.setObjectName("ContentSectionFrame")
        settings_layout = QVBoxLayout(settings_frame)
        settings_layout.setContentsMargins(15, 15, 15, 15)
        settings_layout.setSpacing(12)

        # Шапка блока с кнопками выбора режима
        sett_header = QHBoxLayout()
        sett_title_layout = QVBoxLayout()
        sett_title = QLabel("Тонкая настройка действий")
        sett_title.setObjectName("SectionSubTitle")
        sett_desc = QLabel("Включайте или отключайте отдельные действия прогрева")
        sett_desc.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 11px;")
        sett_title_layout.addWidget(sett_title)
        sett_title_layout.addWidget(sett_desc)
        sett_header.addLayout(sett_title_layout)
        sett_header.addStretch()

        btn_eco = QPushButton("⚡ Экономный режим")
        btn_eco.clicked.connect(self.apply_economy_mode)
        sett_header.addWidget(btn_eco)

        btn_all_on = QPushButton("☑ Включить все")
        btn_all_on.clicked.connect(self.enable_all_switches)
        sett_header.addWidget(btn_all_on)

        btn_all_off = QPushButton("☐ Выключить все")
        btn_all_off.clicked.connect(self.disable_all_switches)
        sett_header.addWidget(btn_all_off)
        settings_layout.addLayout(sett_header)

        # Сетка категорий (3 колонки)
        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(15)

        col1_layout = QVBoxLayout(); col1_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        col2_layout = QVBoxLayout(); col2_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        col3_layout = QVBoxLayout(); col3_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 1. Чтение
        col1_layout.addWidget(self.create_category_card("📖 Чтение", [
            ("read_dialogs", "Просмотр диалогов", False),
            ("scroll_channels", "Прокрутка каналов", True),
            ("mark_as_read", "Отметить как прочитано", False),
            ("search_messages", "Поиск сообщений", False),
        ]))

        # 2. Социальные
        col1_layout.addWidget(self.create_category_card("Социальные", [
            ("forward_messages", "Пересылка сообщений", False),
            ("notes_saved", "Заметки в Избранном", False),
            ("sync_contacts", "Синхронизация контактов", False),
        ]))

        # 3. Активность
        col2_layout.addWidget(self.create_category_card("👍 Активность", [
            ("vote_polls", "Голосование в опросах", False),
            ("watch_video", "Просмотр видео", True),
            ("listen_voice", "Прослушивание голосовых", True),
        ]))

        # 4. Группы
        col2_layout.addWidget(self.create_category_card("Группы", [
            ("archive_chats", "Архивирование чатов", False),
            ("mute_chats", "Отключение звука в чатах", False),
        ]))

        # 5. Развлечения (с тегом "трафик" в заголовке)
        col3_layout.addWidget(self.create_category_card("🎉 Развлечения", [
            ("search_gif", "Поиск GIF", True),
            ("view_stickers", "Просмотр стикер-паков", True),
            ("inline_bots", "Инлайн-боты", False),
            ("preview_links", "Предпросмотр ссылок", True),
        ], header_traffic=True))

        # 6. Профиль и настройки
        col3_layout.addWidget(self.create_category_card("⚙ Профиль и настройки", [
            ("simulate_typing", "Симуляция печати", False),
            ("view_profiles", "Просмотр профилей", False),
            ("check_settings", "Проверка настроек", False),
            ("gradual_update", "Постепенное обновление пр...", False),
            ("emoji_status", "Эмодзи-статус", False),
            ("drafts", "Черновики", False),
            ("configure_notifications", "Настройка уведомлений", False),
            ("scheduled_messages", "Отложенные сообщения", False),
        ]))

        grid_layout.addLayout(col1_layout, 1)
        grid_layout.addLayout(col2_layout, 1)
        grid_layout.addLayout(col3_layout, 1)
        settings_layout.addLayout(grid_layout)

        # Текстовое поле ввода чатов для прогрева
        settings_layout.addWidget(QLabel("Группы/Чаты для прогрева (по одной ссылке на строку):", styleSheet=f"color: {styles.COLOR_TEXT_MUTED}; font-weight: bold; margin-top: 10px;"))
        self.input_warmup_chats = QTextEdit()
        self.input_warmup_chats.setFixedHeight(80)
        self.input_warmup_chats.setPlaceholderText("https://t.me/chat1\nhttps://t.me/chat2")
        settings_layout.addWidget(self.input_warmup_chats)

        # Блок задержек и длительности прогрева
        delays_layout = QHBoxLayout()
        delays_layout.setSpacing(15)
        delays_layout.setContentsMargins(0, 5, 0, 5)
        
        min_del_h = QHBoxLayout()
        min_del_h.addWidget(QLabel("Мин. задержка (сек):", styleSheet=f"color: {styles.COLOR_TEXT_MUTED}; font-size: 11px; font-weight: bold;"))
        self.input_min_delay = QLineEdit()
        self.input_min_delay.setFixedWidth(60)
        self.input_min_delay.setPlaceholderText("4")
        min_del_h.addWidget(self.input_min_delay)
        delays_layout.addLayout(min_del_h)
        
        max_del_h = QHBoxLayout()
        max_del_h.addWidget(QLabel("Макс. задержка (сек):", styleSheet=f"color: {styles.COLOR_TEXT_MUTED}; font-size: 11px; font-weight: bold;"))
        self.input_max_delay = QLineEdit()
        self.input_max_delay.setFixedWidth(60)
        self.input_max_delay.setPlaceholderText("10")
        max_del_h.addWidget(self.input_max_delay)
        delays_layout.addLayout(max_del_h)
        
        dur_h = QHBoxLayout()
        dur_h.addWidget(QLabel("Длительность (минут):", styleSheet=f"color: {styles.COLOR_TEXT_MUTED}; font-size: 11px; font-weight: bold;"))
        self.input_warmup_duration = QLineEdit()
        self.input_warmup_duration.setFixedWidth(60)
        self.input_warmup_duration.setPlaceholderText("30")
        dur_h.addWidget(self.input_warmup_duration)
        delays_layout.addLayout(dur_h)
        
        delays_layout.addStretch()
        settings_layout.addLayout(delays_layout)

        # Кнопки сохранения и запуска
        warmup_control_layout = QHBoxLayout()
        warmup_control_layout.addStretch()

        self.btn_save_warmup = QPushButton("💾 Сохранить настройки")
        self.btn_save_warmup.clicked.connect(self.save_warmup_only)
        warmup_control_layout.addWidget(self.btn_save_warmup)

        self.btn_run_warmup = QPushButton("Запустить авто-прогрев")
        self.btn_run_warmup.setIcon(QIcon(str(ROCKET_ICON_PATH)))
        self.btn_run_warmup.setObjectName("ApplyBtn")
        self.btn_run_warmup.clicked.connect(self.start_automatic_warmup)
        warmup_control_layout.addWidget(self.btn_run_warmup)
        
        self.btn_schedule_warmup = QPushButton("⏰ Запланировать")
        self.btn_schedule_warmup.clicked.connect(self.schedule_warmup)
        warmup_control_layout.addWidget(self.btn_schedule_warmup)
        
        self.btn_stop_warmup = QPushButton("Остановить прогрев")
        self.btn_stop_warmup.setIcon(QIcon(str(CANCEL_ICON_PATH)))
        self.btn_stop_warmup.clicked.connect(self.stop_automatic_warmup)
        warmup_control_layout.addWidget(self.btn_stop_warmup)
        settings_layout.addLayout(warmup_control_layout)
        self.right_layout.addWidget(settings_frame)

        # ----------------------------------------------------
        # БЛОК 3.2: Настройка Нейро-Диалогов (Cross-Talk AI)
        # ----------------------------------------------------
        dialogues_frame = QFrame()
        dialogues_frame.setObjectName("ContentSectionFrame")
        dialogues_layout = QVBoxLayout(dialogues_frame)
        dialogues_layout.setContentsMargins(15, 15, 15, 15)
        dialogues_layout.setSpacing(12)

        dialogues_title_layout = QVBoxLayout()
        dialogues_title = QLabel("💬 Настройка Нейро-Диалогов (Cross-Talk AI)")
        dialogues_title.setObjectName("SectionSubTitle")
        dialogues_desc = QLabel("Позволяет вашим аккаунтам вести реалистичный диалог друг с другом с использованием ИИ")
        dialogues_desc.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 11px;")
        dialogues_title_layout.addWidget(dialogues_title)
        dialogues_title_layout.addWidget(dialogues_desc)

        dialogues_header_layout = QHBoxLayout()
        dialogues_header_layout.addLayout(dialogues_title_layout)
        dialogues_header_layout.addStretch()

        self.switch_enable_dialogues = Switch()
        self.switch_enable_dialogues.toggled.connect(self.update_dialogues_panel_state)
        dialogues_header_layout.addWidget(self.switch_enable_dialogues)
        dialogues_layout.addLayout(dialogues_header_layout)

        # Контейнер настроек диалогов
        self.dialogues_settings_widget = QWidget()
        self.dialogues_settings_widget.setEnabled(False)
        dialogues_settings_layout = QVBoxLayout(self.dialogues_settings_widget)
        dialogues_settings_layout.setContentsMargins(0, 0, 0, 0)
        dialogues_settings_layout.setSpacing(10)

        # Режим диалога (Группа / Чат vs Личные сообщения)
        mode_h = QHBoxLayout()
        mode_h.addWidget(QLabel("Режим диалога:", styleSheet=f"font-weight: bold; color: {styles.COLOR_TEXT_MUTED}; min-width: 120px;"))
        self.combo_dialogue_mode = QComboBox()
        self.combo_dialogue_mode.addItems(["Группа / Чат", "Личные сообщения (ЛС)"])
        self.combo_dialogue_mode.currentTextChanged.connect(self.on_dialogue_mode_changed)
        mode_h.addWidget(self.combo_dialogue_mode)
        dialogues_settings_layout.addLayout(mode_h)

        # Ссылка на чат (для Группа / Чат)
        chat_h = QHBoxLayout()
        self.dialogue_chat_label = QLabel("Ссылка на чат:", styleSheet=f"font-weight: bold; color: {styles.COLOR_TEXT_MUTED}; min-width: 120px;")
        chat_h.addWidget(self.dialogue_chat_label)
        self.input_dialogue_chat = QLineEdit()
        self.input_dialogue_chat.setPlaceholderText("https://t.me/joinchat/... или @group_username")
        chat_h.addWidget(self.input_dialogue_chat)
        dialogues_settings_layout.addLayout(chat_h)

        # Промпт диалога
        prompt_v = QVBoxLayout()
        prompt_v.setSpacing(4)
        prompt_v.addWidget(QLabel("Контекст / Тема обсуждения ИИ:", styleSheet=f"font-weight: bold; color: {styles.COLOR_TEXT_MUTED};"))
        self.input_dialogue_prompt = QTextEdit()
        self.input_dialogue_prompt.setFixedHeight(60)
        self.input_dialogue_prompt.setPlaceholderText("О чем должны общаться аккаунты...")
        self.input_dialogue_prompt.setStyleSheet(f"background-color: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 6px; padding: 4px; color: #E0E0E0;")
        prompt_v.addWidget(self.input_dialogue_prompt)
        dialogues_settings_layout.addLayout(prompt_v)

        # Количество сообщений
        count_h = QHBoxLayout()
        count_h.addWidget(QLabel("Глубина диалога (сообщений):", styleSheet=f"font-weight: bold; color: {styles.COLOR_TEXT_MUTED};"))
        count_h.addStretch()
        
        count_h.addWidget(QLabel("Мин:", styleSheet=f"color: {styles.COLOR_TEXT_MUTED}; font-size: 11px;"))
        self.input_dialogue_min_msgs = QLineEdit()
        self.input_dialogue_min_msgs.setFixedWidth(50)
        self.input_dialogue_min_msgs.setPlaceholderText("3")
        count_h.addWidget(self.input_dialogue_min_msgs)

        count_h.addWidget(QLabel("Макс:", styleSheet=f"color: {styles.COLOR_TEXT_MUTED}; font-size: 11px; margin-left: 10px;"))
        self.input_dialogue_max_msgs = QLineEdit()
        self.input_dialogue_max_msgs.setFixedWidth(50)
        self.input_dialogue_max_msgs.setPlaceholderText("7")
        count_h.addWidget(self.input_dialogue_max_msgs)
        dialogues_settings_layout.addLayout(count_h)

        dialogues_layout.addWidget(self.dialogues_settings_widget)
        self.right_layout.addWidget(dialogues_frame)

    def show_neurocommenting_module(self):
        self._clear_right_layout()
        self.switches.clear()
        self.selected_preset = "balanced"
        
        # 1. Шапка
        title_layout = QHBoxLayout()
        module_title = QLabel("💬 Нейрокомментинг (Стероиды)")
        module_title.setObjectName("ModuleWorkTitle")
        title_layout.addWidget(module_title)
        title_layout.addStretch()
        
        title_layout.addWidget(QLabel("Аккаунт (Редактор):"))
        self.acc_combo = QComboBox()
        self.acc_combo.setFixedWidth(160)
        self.acc_combo.currentTextChanged.connect(self.on_account_changed)
        title_layout.addWidget(self.acc_combo)

        btn_refresh = QPushButton()
        btn_refresh.setIcon(get_icon(FOLDER_ICON_PATH))
        btn_refresh.setIconSize(QSize(16, 16))
        btn_refresh.setFixedSize(30, 30)
        btn_refresh.clicked.connect(self.refresh_accounts)
        title_layout.addWidget(btn_refresh)
        self.right_layout.addLayout(title_layout)

        # 2. Создание Tab Widget
        self.commenting_tabs = QTabWidget()
        self.commenting_tabs.setObjectName("CommentingTabs")
        self.right_layout.addWidget(self.commenting_tabs)

        # ==========================================
        # Вкладка 1:  Запуск (Launch)
        # ==========================================
        tab_launch = QWidget()
        layout_launch = QVBoxLayout(tab_launch)
        layout_launch.setContentsMargins(10, 10, 10, 10)
        layout_launch.setSpacing(12)

        # Выбор аккаунтов
        selector_frame = QFrame()
        selector_frame.setObjectName("ContentSectionFrame")
        selector_layout = QVBoxLayout(selector_frame)
        selector_layout.setContentsMargins(10, 10, 10, 10)
        selector_layout.setSpacing(8)

        selector_header = QHBoxLayout()
        selector_title = QLabel("Выбор аккаунтов для запуска")
        selector_title.setObjectName("SectionSubTitle")
        selector_header.addWidget(selector_title)
        selector_header.addStretch()
        
        self.lbl_selected_count = QLabel("0 выбрано")
        bg_rgba = "rgba(0, 230, 118, 0.1)" if styles.COLOR_PRIMARY == "#00E676" else "rgba(0, 176, 255, 0.1)"
        border_rgba = "rgba(0, 230, 118, 0.3)" if styles.COLOR_PRIMARY == "#00E676" else "rgba(0, 176, 255, 0.3)"
        self.lbl_selected_count.setStyleSheet(f"color: {styles.COLOR_PRIMARY}; font-weight: bold; background-color: {bg_rgba}; padding: 4px 10px; border-radius: 6px; border: 1px solid {border_rgba};")
        selector_header.addWidget(self.lbl_selected_count)
        selector_layout.addLayout(selector_header)

        panels_h = QHBoxLayout()
        panels_h.setSpacing(10)

        # Левая - Доступные
        avail_panel = QFrame()
        avail_panel.setObjectName("SelectionCard")
        avail_layout = QVBoxLayout(avail_panel)
        avail_layout.setContentsMargins(6, 6, 6, 6)
        avail_layout.setSpacing(5)

        avail_header = QHBoxLayout()
        avail_title_lbl = QLabel("Доступные")
        avail_title_lbl.setStyleSheet(f"font-weight: bold; color: {styles.COLOR_PRIMARY};")
        avail_header.addWidget(avail_title_lbl)
        avail_header.addStretch()
        self.lbl_avail_count = QLabel("Всего: 0")
        self.lbl_avail_count.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 11px;")
        avail_header.addWidget(self.lbl_avail_count)
        avail_layout.addLayout(avail_header)

        self.search_selector = QLineEdit()
        self.search_selector.setPlaceholderText("🔍 Поиск аккаунта...")
        self.search_selector.textChanged.connect(self.update_selector_ui)
        avail_layout.addWidget(self.search_selector)

        filters_layout = QHBoxLayout()
        self.cb_only_proxy = QCheckBox("С прокси")
        self.cb_only_proxy.stateChanged.connect(self.update_selector_ui)
        filters_layout.addWidget(self.cb_only_proxy)

        self.cb_hide_running = QCheckBox("Скрыть активные")
        self.cb_hide_running.stateChanged.connect(self.update_selector_ui)
        filters_layout.addWidget(self.cb_hide_running)
        avail_layout.addLayout(filters_layout)

        btn_add_all = QPushButton(">> Добавить все")
        bg_btn = "rgba(0, 200, 83, 0.15)" if styles.COLOR_PRIMARY == "#00E676" else "rgba(0, 145, 234, 0.15)"
        btn_add_all.setStyleSheet(f"background-color: {bg_btn}; color: {styles.COLOR_PRIMARY}; border: 1px solid {styles.COLOR_PRIMARY}; font-size: 11px; padding: 4px;")
        btn_add_all.clicked.connect(self.add_all_filtered_to_selected)
        avail_layout.addWidget(btn_add_all)

        self.avail_scroll = QScrollArea()
        self.avail_scroll.setWidgetResizable(True)
        self.avail_scroll.setFixedHeight(160)
        self.avail_scroll.setStyleSheet(f"QScrollArea {{ background-color: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER_LIGHT}; border-radius: 6px; }}")
        self.avail_scroll_widget = QWidget()
        self.avail_scroll_layout = QVBoxLayout(self.avail_scroll_widget)
        self.avail_scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.avail_scroll_layout.setSpacing(4)
        self.avail_scroll_layout.setContentsMargins(4, 4, 4, 4)
        self.avail_scroll.setWidget(self.avail_scroll_widget)
        avail_layout.addWidget(self.avail_scroll)
        panels_h.addWidget(avail_panel, 1)

        # Правая - Выбранные
        select_panel = QFrame()
        select_panel.setObjectName("SelectionCard")
        select_layout = QVBoxLayout(select_panel)
        select_layout.setContentsMargins(6, 6, 6, 6)
        select_layout.setSpacing(5)

        select_header = QHBoxLayout()
        select_title_lbl = QLabel("Выбранные для работы")
        select_title_lbl.setStyleSheet(f"font-weight: bold; color: {styles.COLOR_PRIMARY};")
        select_header.addWidget(select_title_lbl)
        select_header.addStretch()
        select_layout.addLayout(select_header)

        btn_remove_all = QPushButton("<< Удалить все")
        btn_remove_all.setStyleSheet("background-color: rgba(198, 40, 40, 0.15); color: #FF5252; border: 1px solid #FF5252; font-size: 11px; padding: 4px;")
        btn_remove_all.clicked.connect(self.remove_all_from_selected)
        select_layout.addWidget(btn_remove_all)

        self.selected_scroll = QScrollArea()
        self.selected_scroll.setWidgetResizable(True)
        self.selected_scroll.setFixedHeight(200)
        self.selected_scroll.setStyleSheet(f"QScrollArea {{ background-color: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER_LIGHT}; border-radius: 6px; }}")
        self.selected_scroll_widget = QWidget()
        self.selected_scroll_layout = QVBoxLayout(self.selected_scroll_widget)
        self.selected_scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.selected_scroll_layout.setSpacing(4)
        self.selected_scroll_layout.setContentsMargins(4, 4, 4, 4)
        self.selected_scroll.setWidget(self.selected_scroll_widget)
        select_layout.addWidget(self.selected_scroll)
        panels_h.addWidget(select_panel, 1)

        selector_layout.addLayout(panels_h)
        layout_launch.addWidget(selector_frame)

        # Целевые каналы
        chan_frame = QFrame()
        chan_frame.setObjectName("ContentSectionFrame")
        chan_layout = QVBoxLayout(chan_frame)
        chan_layout.setContentsMargins(10, 10, 10, 10)
        chan_layout.setSpacing(6)

        chan_title_badge = QHBoxLayout()
        chan_title_badge.addWidget(QLabel("Целевые каналы для комментирования (по одной ссылке на строку):", styleSheet="font-weight: bold; color: #E0E0E0;"))
        self.badge_channels = QLabel("0 каналов")
        bc_bg = "rgba(0, 230, 118, 0.15)" if styles.COLOR_PRIMARY == "#00E676" else "rgba(0, 176, 255, 0.15)"
        bc_border = "rgba(0, 230, 118, 0.3)" if styles.COLOR_PRIMARY == "#00E676" else "rgba(0, 176, 255, 0.3)"
        self.badge_channels.setStyleSheet(f"background-color: {bc_bg}; color: {styles.COLOR_PRIMARY}; font-size: 10px; border: 1px solid {bc_border}; border-radius: 10px; padding: 2px 8px; font-weight: bold;")
        chan_title_badge.addWidget(self.badge_channels)
        chan_title_badge.addStretch()
        chan_layout.addLayout(chan_title_badge)

        self.input_channels = QTextEdit()
        self.input_channels.setPlaceholderText("https://t.me/durov\n@telegram")
        self.input_channels.setFixedHeight(80)
        self.input_channels.setStyleSheet(f"background-color: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 6px; padding: 4px; color: #E0E0E0;")
        self.input_channels.textChanged.connect(self.update_channels_count_badge)
        chan_layout.addWidget(self.input_channels)
        layout_launch.addWidget(chan_frame)

        # Кнопки запуска
        control_layout = QHBoxLayout()
        control_layout.addStretch()

        self.btn_save_commenting = QPushButton("💾 Сохранить настройки")
        self.btn_save_commenting.clicked.connect(self.save_commenting_only)
        control_layout.addWidget(self.btn_save_commenting)

        self.btn_run_commenting = QPushButton("💬 Запустить нейрокомментинг")
        self.btn_run_commenting.setObjectName("ApplyBtn")
        self.btn_run_commenting.clicked.connect(self.start_neurocommenting)
        control_layout.addWidget(self.btn_run_commenting)
        
        self.btn_schedule_commenting = QPushButton("⏰ Запланировать")
        self.btn_schedule_commenting.clicked.connect(self.schedule_neurocommenting)
        control_layout.addWidget(self.btn_schedule_commenting)
        
        layout_launch.addLayout(control_layout)

        # Консоль
        console_frame = QFrame()
        console_frame.setObjectName("ContentSectionFrame")
        console_layout = QVBoxLayout(console_frame)
        console_layout.setContentsMargins(10, 10, 10, 10)
        console_layout.setSpacing(6)

        console_title_h = QHBoxLayout()
        console_title_h.addWidget(QLabel("Мониторинг выполнения и Логи", objectName="ConsoleTitle"))
        console_title_h.addStretch()
        
        btn_clear_log = QPushButton("Очистить логи")
        btn_clear_log.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        btn_clear_log.clicked.connect(lambda: self.console_output.clear())
        console_title_h.addWidget(btn_clear_log)
        console_layout.addLayout(console_title_h)

        self.console_output = QTextEdit()
        self.console_output.setObjectName("ConsoleLog")
        self.console_output.setReadOnly(True)
        self.console_output.setFixedHeight(120)
        console_layout.addWidget(self.console_output)
        layout_launch.addWidget(console_frame)

        self.commenting_tabs.addTab(tab_launch, "Запуск")

        # ==========================================
        # Вкладка 2: 🧠 Интеллект ИИ (AI settings)
        # ==========================================
        tab_ai = QWidget()
        layout_ai = QVBoxLayout(tab_ai)
        layout_ai.setContentsMargins(10, 10, 10, 10)
        layout_ai.setSpacing(10)

        ai_frame = QFrame()
        ai_frame.setObjectName("ContentSectionFrame")
        ai_layout = QVBoxLayout(ai_frame)
        ai_layout.setContentsMargins(10, 10, 10, 10)
        ai_layout.setSpacing(8)

        ai_section_title = QLabel("Настройка API Ключей и Стилей ИИ")
        ai_section_title.setObjectName("SectionSubTitle")
        ai_layout.addWidget(ai_section_title)

        form_layout = QVBoxLayout()
        form_layout.setSpacing(8)

        # Провайдер
        prov_h = QHBoxLayout()
        prov_h.addWidget(QLabel("ИИ Провайдер:", styleSheet=f"font-weight: bold; color: {styles.COLOR_TEXT_MUTED}; min-width: 90px;"))
        self.combo_provider = QComboBox()
        self.combo_provider.addItems(["OpenAI-совместимый", "Google Gemini"])
        self.combo_provider.currentTextChanged.connect(self.on_provider_changed)
        prov_h.addWidget(self.combo_provider)
        form_layout.addLayout(prov_h)

        # Стиль
        style_h = QHBoxLayout()
        style_h.addWidget(QLabel("Стиль ИИ:   ", styleSheet=f"font-weight: bold; color: {styles.COLOR_TEXT_MUTED}; min-width: 90px;"))
        self.combo_ai_style = QComboBox()
        self.combo_ai_style.addItems([
            "Обычный пользователь (Естественный)",
            "Крипто-эксперт (Сленг)",
            "Интеллектуал (Умный)",
            "Юморист (Сарказм/Ирония)",
            "Краткий критик (Хейтер)",
            "Свой промпт (из склада ниже)"
        ])
        self.combo_ai_style.currentTextChanged.connect(self.on_ai_style_changed)
        style_h.addWidget(self.combo_ai_style)
        form_layout.addLayout(style_h)

        # API Ключ
        key_h = QHBoxLayout()
        key_h.addWidget(QLabel("API Ключ:   ", styleSheet=f"font-weight: bold; color: {styles.COLOR_TEXT_MUTED}; min-width: 90px;"))
        self.input_api_key = QLineEdit()
        self.input_api_key.setPlaceholderText("gsk_...")
        self.input_api_key.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        key_h.addWidget(self.input_api_key)
        
        btn_test_api = QPushButton("⚡ Проверить")
        btn_test_api.setToolTip("Выполнить тестовый запрос к ИИ")
        btn_test_api.clicked.connect(self.test_api_connection)
        btn_test_api.setStyleSheet(f"background-color: {styles.COLOR_HOVER_BG}; font-size: 11px; padding: 4px 10px;")
        key_h.addWidget(btn_test_api)
        form_layout.addLayout(key_h)

        # Base URL
        url_h = QHBoxLayout()
        url_h.addWidget(QLabel("Base URL:   ", styleSheet=f"font-weight: bold; color: {styles.COLOR_TEXT_MUTED}; min-width: 90px;"))
        self.input_api_base_url = QLineEdit()
        self.input_api_base_url.setPlaceholderText("https://api.openai.com/v1")
        url_h.addWidget(self.input_api_base_url)
        form_layout.addLayout(url_h)

        # Модель
        model_h = QHBoxLayout()
        model_h.addWidget(QLabel("Модель:     ", styleSheet=f"font-weight: bold; color: {styles.COLOR_TEXT_MUTED}; min-width: 90px;"))
        self.input_model_name = QLineEdit()
        self.input_model_name.setPlaceholderText("gpt-4o-mini")
        model_h.addWidget(self.input_model_name)
        form_layout.addLayout(model_h)

        # Кастомный промпт
        self.prompt_input_container = QWidget()
        prompt_v = QVBoxLayout(self.prompt_input_container)
        prompt_v.setContentsMargins(0, 0, 0, 0)
        prompt_v.addWidget(QLabel("Индивидуальный системный промпт ИИ:", styleSheet=f"font-weight: bold; color: {styles.COLOR_TEXT_MUTED};"))
        self.input_prompt = QTextEdit()
        self.input_prompt.setPlaceholderText("Инструкция для генерации комментариев...")
        self.input_prompt.setFixedHeight(50)
        self.input_prompt.setStyleSheet(f"background-color: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 6px; padding: 4px; color: #E0E0E0;")
        prompt_v.addWidget(self.input_prompt)
        form_layout.addWidget(self.prompt_input_container)

        ai_layout.addLayout(form_layout)
        layout_ai.addWidget(ai_frame)

        # Склад промптов
        msg_frame = QFrame()
        msg_frame.setObjectName("ContentSectionFrame")
        msg_layout = QVBoxLayout(msg_frame)
        msg_layout.setContentsMargins(10, 10, 10, 10)
        msg_layout.setSpacing(8)
        
        msg_header = QHBoxLayout()
        msg_title = QLabel("Склад промптов ИИ")
        msg_title.setObjectName("SectionSubTitle")
        msg_header.addWidget(msg_title)
        msg_header.addStretch()
        
        msg_header.addWidget(QLabel("Использовать склад", styleSheet=f"color: {styles.COLOR_TEXT_MUTED}; font-size: 11px;"))
        self.switch_use_ai_prompt = Switch()
        self.switch_use_ai_prompt.toggled.connect(self.on_use_ai_prompt_toggled)
        msg_header.addWidget(self.switch_use_ai_prompt)

        msg_header.addWidget(QLabel("Ротация промптов", styleSheet=f"color: {styles.COLOR_TEXT_MUTED}; font-size: 11px; margin-left: 12px;"))
        self.switch_rotate_prompts = Switch()
        msg_header.addWidget(self.switch_rotate_prompts)
        
        msg_layout.addLayout(msg_header)
        
        self.prompts_gallery_container = QWidget()
        gallery_layout = QVBoxLayout(self.prompts_gallery_container)
        gallery_layout.setContentsMargins(0, 0, 0, 0)
        gallery_layout.setSpacing(6)
        
        # Системные
        sys_section = QWidget()
        sys_sect_layout = QVBoxLayout(sys_section)
        sys_sect_layout.setContentsMargins(0, 0, 0, 0)
        sys_sect_layout.setSpacing(4)
        
        sys_header = QHBoxLayout()
        sys_title = QLabel("Системные промпты")
        sys_title.setStyleSheet("font-weight: bold; color: white; font-size: 11px;")
        sys_header.addWidget(sys_title)
        self.lbl_sys_count = QLabel("(6)")
        self.lbl_sys_count.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 11px;")
        sys_header.addWidget(self.lbl_sys_count)
        sys_header.addStretch()
        
        self.btn_toggle_sys = QPushButton("▲")
        self.btn_toggle_sys.setFixedSize(20, 20)
        self.btn_toggle_sys.setStyleSheet(f"background: transparent; color: {styles.COLOR_TEXT_MUTED}; border: none; font-size: 12px; font-weight: bold;")
        self.btn_toggle_sys.clicked.connect(self.toggle_sys_prompts_visibility)
        sys_header.addWidget(self.btn_toggle_sys)
        sys_sect_layout.addLayout(sys_header)
        
        self.sys_prompts_scroll = QScrollArea()
        self.sys_prompts_scroll.setWidgetResizable(True)
        self.sys_prompts_scroll.setFixedHeight(100)
        self.sys_prompts_scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        self.sys_prompts_widget = QWidget()
        self.sys_prompts_widget.setObjectName("SysPromptsWidget")
        self.sys_prompts_widget.setStyleSheet("QWidget#SysPromptsWidget { background-color: transparent; }")
        self.sys_prompts_layout = QVBoxLayout(self.sys_prompts_widget)
        self.sys_prompts_layout.setContentsMargins(0, 0, 0, 0)
        self.sys_prompts_layout.setSpacing(4)
        self.sys_prompts_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.sys_prompts_scroll.setWidget(self.sys_prompts_widget)
        sys_sect_layout.addWidget(self.sys_prompts_scroll)
        gallery_layout.addWidget(sys_section)
        
        # Пользовательские
        custom_section = QWidget()
        custom_sect_layout = QVBoxLayout(custom_section)
        custom_sect_layout.setContentsMargins(0, 0, 0, 0)
        custom_sect_layout.setSpacing(4)
        
        custom_header = QHBoxLayout()
        custom_title = QLabel("👤 Мои промпты")
        custom_title.setStyleSheet("font-weight: bold; color: white; font-size: 11px;")
        custom_header.addWidget(custom_title)
        self.lbl_custom_count = QLabel("(4)")
        self.lbl_custom_count.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 11px;")
        custom_header.addWidget(self.lbl_custom_count)
        custom_header.addStretch()
        
        self.btn_toggle_custom = QPushButton("▲")
        self.btn_toggle_custom.setFixedSize(20, 20)
        self.btn_toggle_custom.setStyleSheet(f"background: transparent; color: {styles.COLOR_TEXT_MUTED}; border: none; font-size: 12px; font-weight: bold;")
        self.btn_toggle_custom.clicked.connect(self.toggle_custom_prompts_visibility)
        custom_header.addWidget(self.btn_toggle_custom)
        custom_sect_layout.addLayout(custom_header)
        
        self.custom_prompts_scroll = QScrollArea()
        self.custom_prompts_scroll.setWidgetResizable(True)
        self.custom_prompts_scroll.setFixedHeight(100)
        self.custom_prompts_scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        self.custom_prompts_widget = QWidget()
        self.custom_prompts_widget.setObjectName("CustomPromptsWidget")
        self.custom_prompts_widget.setStyleSheet("QWidget#CustomPromptsWidget { background-color: transparent; }")
        self.custom_prompts_layout = QVBoxLayout(self.custom_prompts_widget)
        self.custom_prompts_layout.setContentsMargins(0, 0, 0, 0)
        self.custom_prompts_layout.setSpacing(4)
        self.custom_prompts_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.custom_prompts_scroll.setWidget(self.custom_prompts_widget)
        custom_sect_layout.addWidget(self.custom_prompts_scroll)
        gallery_layout.addWidget(custom_section)
        
        msg_layout.addWidget(self.prompts_gallery_container)
        
        # Язык
        lang_h = QHBoxLayout()
        lang_h.setContentsMargins(0, 5, 0, 0)
        lang_title = QLabel("🌐 Авто-определение языка (пишет комментарий на языке поста)")
        lang_title.setStyleSheet("font-weight: bold; color: white; font-size: 11px;")
        lang_h.addWidget(lang_title)
        lang_h.addStretch()
        lang_h.addWidget(QLabel("Авто", styleSheet=f"color: {styles.COLOR_TEXT_MUTED}; font-size: 11px;"))
        self.switch_auto_lang = Switch()
        lang_h.addWidget(self.switch_auto_lang)
        msg_layout.addLayout(lang_h)
        
        layout_ai.addWidget(msg_frame)
        self.commenting_tabs.addTab(tab_ai, "🧠 Интеллект ИИ")

        # ==========================================
        # Вкладка 3:  Алгоритм и Лимиты
        # ==========================================
        tab_limits = QWidget()
        layout_limits = QVBoxLayout(tab_limits)
        layout_limits.setContentsMargins(10, 10, 10, 10)
        layout_limits.setSpacing(10)

        settings_frame = QFrame()
        settings_frame.setObjectName("ContentSectionFrame")
        settings_layout = QVBoxLayout(settings_frame)
        settings_layout.setContentsMargins(10, 10, 10, 10)
        settings_layout.setSpacing(10)

        # AI Защита
        protection_frame = QFrame()
        protection_frame.setStyleSheet(f"background-color: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 8px; padding: 6px;")
        protection_layout = QVBoxLayout(protection_frame)
        protection_layout.setSpacing(8)

        row1_layout = QHBoxLayout()
        shield_lbl = QLabel("")
        shield_lbl.setFixedSize(22, 22)
        shield_lbl.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY_DARK}; border-radius: 6px; font-size: 12px; qproperty-alignment: AlignCenter; color: #000;")
        row1_layout.addWidget(shield_lbl)

        info_layout = QVBoxLayout()
        shield_title = QLabel("AI Защита аккаунтов от блокировок")
        shield_title.setStyleSheet("font-weight: bold; color: white; font-size: 11px;")
        info_layout.addWidget(shield_title)
        desc_lbl = QLabel("Умные задержки на основе длины публикаций и сгенерированных текстов.")
        desc_lbl.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 10px;")
        info_layout.addWidget(desc_lbl)
        row1_layout.addLayout(info_layout, 1)

        self.switch_ai_protection = Switch()
        self.switch_ai_protection.toggled.connect(self.on_protection_toggled)
        row1_layout.addWidget(self.switch_ai_protection)
        protection_layout.addLayout(row1_layout)

        # Пресеты
        self.preset_layout = QHBoxLayout()
        self.preset_layout.setSpacing(6)
        self.card_conservative = ProtectionPresetCard("conservative", "", "Максимум", "Медленно, безопасно")
        self.card_balanced = ProtectionPresetCard("balanced", "", "Баланс", "Оптимальный режим")
        self.card_aggressive = ProtectionPresetCard("aggressive", "⚡", "Агрессивно", "Высокая скорость")
        for card in [self.card_conservative, self.card_balanced, self.card_aggressive]:
            card.clicked.connect(self.on_preset_clicked)
            self.preset_layout.addWidget(card, 1)
        protection_layout.addLayout(self.preset_layout)
        settings_layout.addWidget(protection_frame)

        # Две колонки
        grid_layout = QHBoxLayout()
        grid_layout.setSpacing(10)

        # Колонки
        col1_frame = QFrame()
        col1_frame.setObjectName("CategoryCard")
        col1_layout = QVBoxLayout(col1_frame)
        col1_layout.setSpacing(6)

        col1_title_lbl = QLabel("Режим комментирования:")
        col1_title_lbl.setStyleSheet("font-weight: bold; color: #E0E0E0; font-size: 11px;")
        col1_layout.addWidget(col1_title_lbl)

        self.comment_mode_control = SegmentedControl(["Случайный", "Ключевые слова", "Все посты", "ИИ-Фильтр"], "Случайный")
        self.comment_mode_control.valueChanged.connect(self.on_comment_mode_changed)
        col1_layout.addWidget(self.comment_mode_control)

        # Chance slider
        self.widget_chance = QWidget()
        chance_layout = QVBoxLayout(self.widget_chance)
        chance_layout.setContentsMargins(0, 0, 0, 0)
        chance_lbl_layout = QHBoxLayout()
        chance_title_lbl = QLabel("Вероятность:")
        chance_title_lbl.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 11px;")
        chance_lbl_layout.addWidget(chance_title_lbl)
        self.chance_val_lbl = QLabel("50%")
        self.chance_val_lbl.setStyleSheet(f"color: {styles.COLOR_PRIMARY}; font-weight: bold; font-size: 11px;")
        chance_lbl_layout.addWidget(self.chance_val_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        chance_layout.addLayout(chance_lbl_layout)

        self.slider_chance = QSlider(Qt.Orientation.Horizontal)
        self.slider_chance.setRange(1, 100)
        self.slider_chance.setValue(50)
        self.slider_chance.setStyleSheet("QSlider::groove:horizontal { height: 4px; background: #222; border-radius: 2px; } QSlider::handle:horizontal { background: #00E676; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }")
        self.slider_chance.valueChanged.connect(self.on_chance_slider_changed)
        chance_layout.addWidget(self.slider_chance)
        col1_layout.addWidget(self.widget_chance)

        # Keywords list widget
        self.widget_keywords = QWidget()
        kw_layout = QVBoxLayout(self.widget_keywords)
        kw_layout.setContentsMargins(0, 0, 0, 0)
        input_btn_h = QHBoxLayout()
        self.input_keywords_raw = QLineEdit()
        self.input_keywords_raw.setPlaceholderText("Слова через запятую...")
        input_btn_h.addWidget(self.input_keywords_raw, 1)
        btn_add_kw = QPushButton("+")
        btn_add_kw.setFixedSize(26, 26)
        btn_add_kw.clicked.connect(self.on_add_kw_clicked)
        input_btn_h.addWidget(btn_add_kw)
        kw_layout.addLayout(input_btn_h)
        col1_layout.addWidget(self.widget_keywords)

        self.widget_all_posts = QLabel("Пишет комментарии под каждым постом.")
        self.widget_all_posts.setStyleSheet("color: gray; font-size: 10px; font-style: italic;")
        col1_layout.addWidget(self.widget_all_posts)

        self.widget_ai_filter = QLabel("ИИ пропускает только полезные публикации.")
        self.widget_ai_filter.setStyleSheet("color: gray; font-size: 10px; font-style: italic;")
        col1_layout.addWidget(self.widget_ai_filter)

        grid_layout.addWidget(col1_frame, 1)

        # Колонка 2
        col2_frame = QFrame()
        col2_frame.setObjectName("CategoryCard")
        col2_layout = QVBoxLayout(col2_frame)
        col2_layout.setSpacing(6)

        col2_title_lbl = QLabel("Режим лимитов:")
        col2_title_lbl.setStyleSheet("font-weight: bold; color: #E0E0E0; font-size: 11px;")
        col2_layout.addWidget(col2_title_lbl)

        self.limit_mode_control = SegmentedControl(["По количеству", "По времени"], "По количеству")
        self.limit_mode_control.valueChanged.connect(self.on_limit_mode_changed)
        col2_layout.addWidget(self.limit_mode_control)

        limit_lbl_layout = QHBoxLayout()
        self.limit_title = QLabel("Макс. комментариев:")
        self.limit_title.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 11px;")
        limit_lbl_layout.addWidget(self.limit_title)
        self.limit_val_lbl = QLabel("500")
        self.limit_val_lbl.setStyleSheet(f"color: {styles.COLOR_PRIMARY}; font-weight: bold; font-size: 11px;")
        limit_lbl_layout.addWidget(self.limit_val_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        col2_layout.addLayout(limit_lbl_layout)

        self.slider_limit = QSlider(Qt.Orientation.Horizontal)
        self.slider_limit.setRange(1, 1000)
        self.slider_limit.setValue(500)
        self.slider_limit.setStyleSheet("QSlider::groove:horizontal { height: 4px; background: #222; border-radius: 2px; } QSlider::handle:horizontal { background: #00E676; width: 12px; height: 12px; margin: -4px 0; border-radius: 6px; }")
        self.slider_limit.valueChanged.connect(self.on_limit_slider_changed)
        col2_layout.addWidget(self.slider_limit)

        grid_layout.addWidget(col2_frame, 1)
        settings_layout.addLayout(grid_layout)

        # Второй круг
        followup_frame = QFrame()
        followup_frame.setStyleSheet(f"background-color: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 8px; padding: 6px;")
        followup_layout = QVBoxLayout(followup_frame)
        followup_layout.setSpacing(4)

        f_row1 = QHBoxLayout()
        f_icon = QLabel("💬")
        f_icon.setFixedSize(22, 22)
        f_icon.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY_DARK}; border-radius: 6px; font-size: 12px; qproperty-alignment: AlignCenter; color: #000;")
        f_row1.addWidget(f_icon)

        f_info = QVBoxLayout()
        f_title_lbl = QLabel("Второй круг (Ответы на чужие комментарии)")
        f_title_lbl.setStyleSheet("font-weight: bold; color: white; font-size: 11px;")
        f_info.addWidget(f_title_lbl)
        f_desc_lbl = QLabel("Бот будет отвечать на комментарии других людей под ваш комментарий.")
        f_desc_lbl.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 10px;")
        f_info.addWidget(f_desc_lbl)
        f_row1.addLayout(f_info, 1)

        self.switch_followup = Switch()
        self.switch_followup.toggled.connect(self.on_followup_toggled)
        f_row1.addWidget(self.switch_followup)
        followup_layout.addLayout(f_row1)

        self.followup_settings_widget = QWidget()
        f_settings_layout = QHBoxLayout(self.followup_settings_widget)
        f_settings_layout.setContentsMargins(0, 0, 0, 0)
        f_settings_layout.setSpacing(12)

        delay_vbox = QVBoxLayout()
        delay_title_h = QHBoxLayout()
        delay_lbl = QLabel("Период (часов):")
        delay_lbl.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 11px;")
        delay_title_h.addWidget(delay_lbl)
        self.lbl_followup_hours = QLabel("3 ч")
        self.lbl_followup_hours.setStyleSheet(f"color: {styles.COLOR_PRIMARY}; font-weight: bold; font-size: 11px;")
        delay_title_h.addWidget(self.lbl_followup_hours, alignment=Qt.AlignmentFlag.AlignRight)
        delay_vbox.addLayout(delay_title_h)
        self.slider_followup_hours = QSlider(Qt.Orientation.Horizontal)
        self.slider_followup_hours.setRange(1, 24)
        self.slider_followup_hours.setValue(3)
        self.slider_followup_hours.valueChanged.connect(self.on_followup_hours_changed)
        delay_vbox.addWidget(self.slider_followup_hours)
        f_settings_layout.addLayout(delay_vbox, 1)

        chance_vbox = QVBoxLayout()
        chance_title_h = QHBoxLayout()
        chance_lbl = QLabel("Вероятность ответа:")
        chance_lbl.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 11px;")
        chance_title_h.addWidget(chance_lbl)
        self.lbl_followup_chance = QLabel("30%")
        self.lbl_followup_chance.setStyleSheet(f"color: {styles.COLOR_PRIMARY}; font-weight: bold; font-size: 11px;")
        chance_title_h.addWidget(self.lbl_followup_chance, alignment=Qt.AlignmentFlag.AlignRight)
        chance_vbox.addLayout(chance_title_h)
        self.slider_followup_chance = QSlider(Qt.Orientation.Horizontal)
        self.slider_followup_chance.setRange(5, 100)
        self.slider_followup_chance.setValue(30)
        self.slider_followup_chance.valueChanged.connect(self.on_followup_chance_changed)
        chance_vbox.addWidget(self.slider_followup_chance)
        f_settings_layout.addLayout(chance_vbox, 1)

        followup_layout.addWidget(self.followup_settings_widget)
        self.followup_settings_widget.setVisible(False)
        settings_layout.addWidget(followup_frame)

        layout_limits.addWidget(settings_frame)
        self.commenting_tabs.addTab(tab_limits, "Алгоритм и Лимиты")

        # ==========================================
        # Вкладка 4:  Распределение (Distribution)
        # ==========================================
        tab_dist = QWidget()
        layout_dist = QVBoxLayout(tab_dist)
        layout_dist.setContentsMargins(10, 10, 10, 10)
        layout_dist.setSpacing(10)

        dist_frame = QFrame()
        dist_frame.setObjectName("ContentSectionFrame")
        dist_layout = QVBoxLayout(dist_frame)
        dist_layout.setContentsMargins(10, 10, 10, 10)
        dist_layout.setSpacing(8)

        dist_section_title = QLabel("Режим распределения целей")
        dist_section_title.setObjectName("SectionSubTitle")
        dist_layout.addWidget(dist_section_title)

        work_presets_h = QHBoxLayout()
        self.card_work_multithread = WorkModePresetCard("multithreaded", "", "Многопоточный", "Каналы делятся между аккаунтами")
        self.card_work_standard = WorkModePresetCard("standard", "", "Стандартный", "Все аккаунты мониторят все каналы")
        self.card_work_multithread.clicked.connect(self.on_work_mode_changed)
        self.card_work_standard.clicked.connect(self.on_work_mode_changed)
        work_presets_h.addWidget(self.card_work_multithread, 1)
        work_presets_h.addWidget(self.card_work_standard, 1)
        dist_layout.addLayout(work_presets_h)

        self.lbl_ratio_badge = QLabel("0 папок / 0 акк. = ~0/акк")
        self.lbl_ratio_badge.setStyleSheet(f"background-color: {bc_bg}; color: {styles.COLOR_PRIMARY}; font-size: 11px; border: 1px solid {bc_border}; border-radius: 12px; padding: 4px 12px; font-weight: bold;")
        ratio_h = QHBoxLayout()
        ratio_h.addWidget(self.lbl_ratio_badge)
        ratio_h.addStretch()
        dist_layout.addLayout(ratio_h)

        # Контейнер деталей
        self.distribution_details_widget = QWidget()
        details_layout = QVBoxLayout(self.distribution_details_widget)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(6)

        badges_h = QHBoxLayout()
        self.lbl_badge_targets = QLabel("0 целей")
        self.lbl_badge_targets.setStyleSheet(f"background-color: {styles.COLOR_HOVER_BG}; color: {styles.COLOR_TEXT_MUTED}; font-size: 10px; border: 1px solid {styles.COLOR_BORDER}; border-radius: 4px; padding: 2px 6px; font-weight: bold;")
        badges_h.addWidget(self.lbl_badge_targets)
        self.lbl_badge_manual = QLabel("0 ручн.")
        self.lbl_badge_manual.setStyleSheet(f"background-color: {bc_bg}; color: {styles.COLOR_PRIMARY}; font-size: 10px; border: 1px solid {bc_border}; border-radius: 4px; padding: 2px 6px; font-weight: bold;")
        badges_h.addWidget(self.lbl_badge_manual)
        badges_h.addStretch()
        details_layout.addLayout(badges_h)

        btn_green_style = f"background-color: {styles.COLOR_HOVER_BG}; color: {styles.COLOR_PRIMARY}; border: 1px solid {styles.COLOR_BORDER_DARK}; border-radius: 4px; font-size: 10px; padding: 3px 8px;"
        btns_h1 = QHBoxLayout()
        btn_green_style = f"background-color: {styles.COLOR_HOVER_BG}; color: {styles.COLOR_PRIMARY}; border: 1px solid {styles.COLOR_BORDER_DARK}; border-radius: 4px; font-size: 10px; padding: 0 10px;"
        btn_muted_style = f"background-color: {styles.COLOR_HOVER_BG}; color: {styles.COLOR_TEXT_MUTED}; border: 1px solid {styles.COLOR_BORDER_DARK}; border-radius: 4px; font-size: 10px; padding: 0 10px;"
        
        btn_recalc = QPushButton("Пересчитать / Обновить")
        btn_recalc.setIcon(QIcon(str(REFRESH_ICON_PATH)))
        btn_recalc.setMinimumWidth(180)
        btn_recalc.setFixedHeight(26)
        btn_recalc.setStyleSheet(btn_green_style)
        btn_recalc.clicked.connect(self.recalculate_distribution)
        btns_h1.addWidget(btn_recalc)
        
        btns_h1.addStretch()
        details_layout.addLayout(btns_h1)

        btns_h2 = QHBoxLayout()
        btns_h2.setSpacing(8)
        
        btn_export = QPushButton("↓ Экспорт JSON")
        btn_export.setMinimumWidth(110)
        btn_export.setFixedHeight(26)
        btn_export.setStyleSheet(btn_green_style)
        btn_export.clicked.connect(self.export_distribution_json)
        btns_h2.addWidget(btn_export)
        
        btn_import = QPushButton("↑ Импорт JSON")
        btn_import.setMinimumWidth(110)
        btn_import.setFixedHeight(26)
        btn_import.setStyleSheet(btn_green_style)
        btn_import.clicked.connect(self.import_distribution_json)
        btns_h2.addWidget(btn_import)
        
        btns_h2.addStretch()
        details_layout.addLayout(btns_h2)
        
        # Strict Pinning Row
        pin_h = QHBoxLayout()
        pin_info_l = QVBoxLayout()
        pin_info_l.setSpacing(2)
        pin_title = QLabel("Жесткое закрепление целей")
        pin_title.setStyleSheet("font-weight: bold; color: white; font-size: 11px;")
        pin_desc = QLabel("Автораспределение остаётся базой, а ручные изменения сохраняются как явная схема запуска.")
        pin_desc.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 9px;")
        pin_info_l.addWidget(pin_title)
        pin_info_l.addWidget(pin_desc)
        pin_h.addLayout(pin_info_l, 1)
        
        self.switch_strict_pinning = Switch()
        pin_h.addWidget(self.switch_strict_pinning)
        details_layout.addLayout(pin_h)
        
        # ОБЩЕЕ ПОЛЕ РАСПРЕДЕЛЕНИЯ Section
        gen_lbl = QLabel("ОБЩЕЕ ПОЛЕ РАСПРЕДЕЛЕНИЯ")
        gen_lbl.setStyleSheet(f"color: {styles.COLOR_PRIMARY}; font-weight: bold; font-size: 11px; text-transform: uppercase;")
        details_layout.addWidget(gen_lbl)
        
        gen_sub = QLabel("Вставьте сюда общий список каналов и папок, чтобы быстро разложить их по аккаунтам. Потом можно точно подправить карточки ниже.")
        gen_sub.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 10px;")
        details_layout.addWidget(gen_sub)
        
        self.txt_general_distribution = QTextEdit()
        self.txt_general_distribution.setPlaceholderText("@channel_one\n@channel_two\nhttps://t.me/addlist/...")
        self.txt_general_distribution.setFixedHeight(100)
        self.txt_general_distribution.setStyleSheet(f"background-color: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 8px; padding: 6px; color: #E0E0E0; font-size: 11px;")
        self.txt_general_distribution.textChanged.connect(self.update_ratio_badge)
        self.txt_general_distribution.textChanged.connect(self.update_scheme_badges)
        details_layout.addWidget(self.txt_general_distribution)
        
        # Distribute Button Row
        dist_btn_h = QHBoxLayout()
        dist_btn_h.addWidget(QLabel("Пул промптов для распределения:", styleSheet=f"font-weight: bold; color: {styles.COLOR_TEXT_MUTED}; font-size: 11px;"))
        self.combo_distribute_prompts = QComboBox()
        self.combo_distribute_prompts.addItems([
            "Из склада промптов (Случайно)",
            "Пресеты стилей (Случайно)",
            "Не распределять"
        ])
        self.combo_distribute_prompts.setStyleSheet(f"background-color: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 6px; padding: 4px; color: #E0E0E0; font-size: 11px; min-width: 170px;")
        dist_btn_h.addWidget(self.combo_distribute_prompts)
        
        dist_btn_h.addStretch()
        btn_distribute = QPushButton("Распределить")
        btn_distribute.setIcon(QIcon(str(ROCKET_ICON_PATH)))
        dist_fg = "#000000" if styles.COLOR_PRIMARY == "#00E676" else "#FFFFFF"
        btn_distribute.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.COLOR_PRIMARY};
                color: {dist_fg};
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 16px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {styles.COLOR_PRIMARY_DARK};
            }}
        """)
        btn_distribute.clicked.connect(self.distribute_channels_evenly)
        dist_btn_h.addWidget(btn_distribute)
        details_layout.addLayout(dist_btn_h)
        
        # Таблица распределения целей по аккаунтам
        grid_desc = QLabel("Текущая схема будет сохранена локально и отправлена в задачу как явное закрепление цели за аккаунтом.")
        grid_desc.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 10px; font-style: italic;")
        details_layout.addWidget(grid_desc)
        
        self.distribution_table = QTableWidget()
        self.distribution_table.setColumnCount(4)
        self.distribution_table.setHorizontalHeaderLabels(["Аккаунт", "Кол-во каналов", "Стиль промпта", "Действия"])
        self.distribution_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.distribution_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.distribution_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.distribution_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.distribution_table.setMinimumHeight(150)
        self.distribution_table.setMaximumHeight(350)
        self.distribution_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.distribution_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.distribution_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {styles.COLOR_CONSOLE_BG};
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 8px;
                gridline-color: {styles.COLOR_BORDER_LIGHT};
                color: #FFFFFF;
            }}
            QTableWidget::item {{
                padding: 6px;
            }}
            QHeaderView::section {{
                background-color: {styles.COLOR_HOVER_BG};
                color: {styles.COLOR_PRIMARY};
                font-weight: bold;
                border: 1px solid {styles.COLOR_BORDER_LIGHT};
                padding: 4px;
            }}
        """)
        details_layout.addWidget(self.distribution_table)
        
        dist_layout.addWidget(self.distribution_details_widget)
        self.right_layout.addWidget(dist_frame)

        # Кнопки сохранения и запуска
        control_layout = QHBoxLayout()
        control_layout.addStretch()

        self.btn_save_commenting = QPushButton("💾 Сохранить настройки")
        self.btn_save_commenting.clicked.connect(self.save_commenting_only)
        control_layout.addWidget(self.btn_save_commenting)

        self.btn_run_commenting = QPushButton("💬 Запустить нейрокомментинг")
        self.btn_run_commenting.setObjectName("ApplyBtn")
        self.btn_run_commenting.clicked.connect(self.start_neurocommenting)
        control_layout.addWidget(self.btn_run_commenting)

        self.right_layout.addLayout(control_layout)

        # ----------------------------------------------------
        # БЛОК 4: Интерактивная консоль/лог
        # ----------------------------------------------------
        console_frame = QFrame()
        console_frame.setObjectName("ContentSectionFrame")
        console_layout = QVBoxLayout(console_frame)
        console_layout.setContentsMargins(15, 15, 15, 15)
        console_layout.setSpacing(8)

        console_title_h = QHBoxLayout()
        console_title_h.addWidget(QLabel("Мониторинг выполнения и Логи", objectName="ConsoleTitle"))
        console_title_h.addStretch()
        
        btn_clear_log = QPushButton("Очистить логи")
        btn_clear_log.setStyleSheet("padding: 2px 8px; font-size: 11px;")
        btn_clear_log.clicked.connect(lambda: self.console_output.clear())
        console_title_h.addWidget(btn_clear_log)
        console_layout.addLayout(console_title_h)

        self.console_output = QTextEdit()
        self.console_output.setObjectName("ConsoleLog")
        self.console_output.setReadOnly(True)
        self.console_output.setFixedHeight(150)
        console_layout.addWidget(self.console_output)

        self.right_layout.addWidget(console_frame)

        self.on_comment_mode_changed("Случайный")
        self.on_protection_toggled(False)
        self.on_work_mode_changed("multithreaded")
        self.switch_use_ai_prompt.setChecked(True)
        self.on_use_ai_prompt_toggled(True)
        self.switch_rotate_prompts.setChecked(False)
        self.update_prompts_grids()
        self.refresh_accounts()

    def on_chance_slider_changed(self, value):
        self.chance_val_lbl.setText(f"{value}%")

    def on_limit_slider_changed(self, value):
        self.limit_val_lbl.setText(str(value))

    def on_limit_mode_changed(self, mode):
        if mode == "По количеству":
            self.limit_title.setText("Макс. комментариев")
            self.slider_limit.setRange(1, 1000)
        else:
            self.limit_title.setText("Макс. время (минут)")
            self.slider_limit.setRange(1, 600)

    def update_channels_count_badge(self):
        try:
            text = self.input_channels.toPlainText().strip()
            lines = [line for line in text.split("\n") if line.strip()]
            count = len(lines)
            
            if count % 10 == 1 and count % 100 != 11:
                suffix = "канал"
            elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
                suffix = "канала"
            else:
                suffix = "каналов"
                
            self.badge_channels.setText(f"{count} {suffix}")
        except Exception:
            pass

    def on_protection_toggled(self, checked):
        self.card_conservative.set_enabled_preset(checked)
        self.card_balanced.set_enabled_preset(checked)
        self.card_aggressive.set_enabled_preset(checked)

    def on_followup_toggled(self, checked):
        self.followup_settings_widget.setVisible(checked)

    def on_followup_hours_changed(self, value):
        self.lbl_followup_hours.setText(f"{value} ч")

    def on_followup_chance_changed(self, value):
        self.lbl_followup_chance.setText(f"{value}%")

    def on_preset_clicked(self, key):
        self.selected_preset = key
        self.card_conservative.set_active(key == "conservative")
        self.card_balanced.set_active(key == "balanced")
        self.card_aggressive.set_active(key == "aggressive")

    def on_provider_changed(self, provider_text):
        if provider_text == "Google Gemini":
            # Prefill Gemini OpenAI Base URL and Model Name, change placeholders
            if not self.input_api_base_url.text().strip() or self.input_api_base_url.text().strip() == "https://api.openai.com/v1":
                self.input_api_base_url.setText("https://generativelanguage.googleapis.com/v1beta/openai")
            self.input_api_base_url.setPlaceholderText("https://generativelanguage.googleapis.com/v1beta/openai")
            self.input_api_key.setPlaceholderText("AIzaSy...")
            if not self.input_model_name.text().strip() or self.input_model_name.text().strip() == "gpt-4o-mini":
                self.input_model_name.setText("gemini-2.5-flash")
            self.input_model_name.setPlaceholderText("gemini-2.5-flash")
        else: # OpenAI-compatible
            if self.input_api_base_url.text().strip() == "https://generativelanguage.googleapis.com/v1beta/openai":
                self.input_api_base_url.clear()
            self.input_api_base_url.setPlaceholderText("https://api.openai.com/v1")
            self.input_api_key.setPlaceholderText("gsk_...")
            if self.input_model_name.text().strip() == "gemini-2.5-flash":
                self.input_model_name.clear()
            self.input_model_name.setPlaceholderText("gpt-4o-mini")

    def on_ai_style_changed(self, style_text):
        is_custom = (style_text in ["Свой промпт (из галереи ниже)", "Свой промпт (из склада ниже)"])
        self.prompt_input_container.setVisible(is_custom)

    def on_comment_mode_changed(self, mode):
        self.widget_chance.setVisible(mode == "Случайный")
        self.widget_keywords.setVisible(mode == "По ключевым словам")
        self.widget_all_posts.setVisible(mode == "Все посты")
        self.widget_ai_filter.setVisible(mode == "ИИ-Фильтр постов")

    def on_add_kw_clicked(self):
        from PyQt6.QtWidgets import QInputDialog
        word, ok = QInputDialog.getText(self, "Добавить ключевое слово", "Введите слово:")
        if ok and word.strip():
            current = self.input_keywords_raw.text().strip()
            if current:
                if not current.endswith(","):
                    current += ", "
                self.input_keywords_raw.setText(current + word.strip())
            else:
                self.input_keywords_raw.setText(word.strip())

    def on_paste_kw_clicked(self):
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            current = self.input_keywords_raw.text().strip()
            if current:
                if not current.endswith(","):
                    current += ", "
                self.input_keywords_raw.setText(current + text)
            else:
                self.input_keywords_raw.setText(text)

    def on_clear_kw_clicked(self):
        self.input_keywords_raw.clear()

    def save_commenting_settings_locally(self):
        acc_name = self.acc_combo.currentText()
        if not acc_name or acc_name not in self.accounts_map:
            return
            
        acc_data = self.accounts_map[acc_name]
        
        # Determine active prompt text
        active_text = ""
        if self.switch_use_ai_prompt.isChecked():
            # Search in system prompts
            for p_key, p_val in self.system_prompts.items():
                if p_val["title"] == self.active_prompt_name:
                    active_text = p_val["text"]
                    break
            # Search in custom prompts
            if not active_text:
                for cp in self.custom_prompts:
                    if cp["name"] == self.active_prompt_name:
                        active_text = cp["text"]
                        break
        
        if not active_text:
            active_text = self.input_prompt.toPlainText().strip()
            
        settings_dict = {
            "api_key": self.input_api_key.text().strip(),
            "api_base_url": self.input_api_base_url.text().strip(),
            "model_name": self.input_model_name.text().strip(),
            "provider": self.combo_provider.currentText(),
            "ai_style": self.combo_ai_style.currentText(),
            "prompt": active_text,
            "selected_prompt_name": self.active_prompt_name,
            "use_ai_prompt": self.switch_use_ai_prompt.isChecked(),
            "rotate_prompts": self.switch_rotate_prompts.isChecked(),
            "channels": self.input_channels.toPlainText().strip(),
            "keywords": self.input_keywords_raw.text().strip(),
            "ai_protection": self.switch_ai_protection.isChecked(),
            "protection_preset": getattr(self, "selected_preset", "balanced"),
            "mode": self.comment_mode_control.value(),
            "chance": self.slider_chance.value(),
            "limit_mode": self.limit_mode_control.value(),
            "max_comments": self.slider_limit.value(),
            "auto_language": self.switch_auto_lang.isChecked(),
            "followup_enabled": self.switch_followup.isChecked(),
            "followup_hours": self.slider_followup_hours.value(),
            "followup_chance": self.slider_followup_chance.value()
        }
        
        acc_data["commenting_settings"] = settings_dict
        
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Save current account settings
            for acc in data.get("accounts", []):
                if acc["name"] == acc_name:
                    acc["commenting_settings"] = settings_dict
                    break
                    
            # Save global commenting distribution configuration
            if "settings" not in data:
                data["settings"] = {}
            data["settings"]["commenting_work_mode"] = self.selected_work_mode
            data["settings"]["commenting_strict_pinning"] = self.switch_strict_pinning.isChecked()
            data["settings"]["commenting_general_distribution"] = self.txt_general_distribution.toPlainText().strip()
            data["settings"]["commenting_auto_language"] = self.switch_auto_lang.isChecked()
            data["settings"]["commenting_custom_prompts"] = self.custom_prompts
            
            # Save unique channels from selected accounts commenting_settings (if multithreaded)
            if self.selected_work_mode == "multithreaded":
                for acc in data.get("accounts", []):
                    name = acc["name"]
                    # Find in selected_accounts
                    match_acc = next((a for a in self.selected_accounts if a["name"] == name), None)
                    if match_acc:
                        c_sett = match_acc.get("commenting_settings", {})
                        if "commenting_settings" not in acc:
                            acc["commenting_settings"] = {}
                        acc["commenting_settings"]["channels"] = c_sett.get("channels", "").strip()
                        if c_sett.get("prompt", "").strip():
                            acc["commenting_settings"]["prompt"] = c_sett["prompt"].strip()
                            acc["commenting_settings"]["ai_style"] = "Свой промпт (из склада ниже)"
            else:
                # If standard, save general distribution list to all selected accounts
                standard_channels = self.txt_general_distribution.toPlainText().strip()
                for acc in data.get("accounts", []):
                    if acc["name"] in [a["name"] for a in self.selected_accounts]:
                        if "commenting_settings" not in acc:
                            acc["commenting_settings"] = {}
                        acc["commenting_settings"]["channels"] = standard_channels
                    
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            farm_manager.save_active_farm_config()
            self.refresh_accounts()
            self.append_log("Все настройки нейрокомментирования сохранены в конфигурацию.", "success")
        except Exception as e:
            self.append_log(f"Не удалось записать настройки в файл: {e}", "error")

    def save_commenting_only(self):
        self.save_commenting_settings_locally()
        QMessageBox.information(self, "Успех", "Настройки комментирования успешно сохранены!")

    def schedule_warmup(self):
        from src.ui.schedule_dialog import ScheduleDialog
        from src.core.scheduler import global_scheduler
        
        dialog = ScheduleDialog("Авто-прогрев", self)
        if dialog.exec():
            # Запускаем один раз сразу и добавляем в расписание
            self.start_automatic_warmup()
            
            job_id = global_scheduler.add_job(
                func=self.start_automatic_warmup,
                trigger='interval',
                minutes=dialog.interval_minutes,
                id='warmup_job',
                replace_existing=True
            )
            if job_id:
                QMessageBox.information(self, "Успех", f"Авто-прогрев добавлен в расписание (каждые {dialog.interval_minutes} мин).")

    def schedule_neurocommenting(self):
        from src.ui.schedule_dialog import ScheduleDialog
        from src.core.scheduler import global_scheduler
        
        dialog = ScheduleDialog("Нейрокомментинг", self)
        if dialog.exec():
            self.start_neurocommenting()
            job_id = global_scheduler.add_job(
                func=self.start_neurocommenting,
                trigger='interval',
                minutes=dialog.interval_minutes,
                id='commenting_job',
                replace_existing=True
            )
            if job_id:
                QMessageBox.information(self, "Успех", f"Нейрокомментинг добавлен в расписание (каждые {dialog.interval_minutes} мин).")

    def start_neurocommenting(self):
        if not self.selected_accounts:
            QMessageBox.warning(self, "Внимание", "Выберите хотя бы один аккаунт в списке справа для запуска нейрокомментирования!")
            return
            
        # Если выключено жесткое закрепление, автоматически распределяем и сохраняем перед запуском
        if self.selected_work_mode == "multithreaded" and not self.switch_strict_pinning.isChecked():
            self.distribute_channels_evenly()
            self.save_commenting_settings_locally()
            
        missing_apis = [acc.get("name") for acc in block_accounts if not acc.get("api_id") or not acc.get("api_hash")]
        if missing_apis:
            QMessageBox.critical(self, "Ошибка", f"У следующих аккаунтов не заполнены API ID/Hash:\n{', '.join(missing_apis)}")
            return
            
        # Загрузим глобальные дефолтные настройки для проверки валидности
        global_api_key = ""
        global_api_base_url = ""
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                s = data.get("settings", {})
                global_api_key = s.get("default_ai_api_key", "").strip()
                global_api_base_url = s.get("default_ai_base_url", "").strip()
        except:
            pass
            
        for acc in self.selected_accounts:
            c_sett = acc.get("commenting_settings", {})
            api_key = c_sett.get("api_key", "").strip() or global_api_key
            api_base_url = c_sett.get("api_base_url", "").strip() or global_api_base_url
            channels = c_sett.get("channels", "").strip()
            
            if not api_key or not api_base_url or not channels:
                QMessageBox.warning(self, "Внимание", f"У аккаунта {acc['name']} не заполнены API ключ, Base URL или список каналов!")
                return
                
        self.btn_run_commenting.setEnabled(False)
        self.btn_run_commenting.setText("⌛ Выполняется комментирование...")
        self.btn_schedule_commenting.setEnabled(False)
        
        selected_names_str = ", ".join(a["name"] for a in self.selected_accounts)
        self.append_log(f"Запуск сессии нейрокомментирования для аккаунтов: {selected_names_str}...", "warning")
        
        blocks = [self.selected_accounts[i:i+10] for i in range(0, len(self.selected_accounts), 10)]
        self.commenting_control_window = CommentingControlWindow(self, blocks, api_id, api_hash)
        self.commenting_control_window.show()

    def on_commenting_finished(self):
        self.btn_run_commenting.setEnabled(True)
        self.btn_run_commenting.setText("💬 Запустить нейрокомментинг")
        self.btn_schedule_commenting.setEnabled(True)
        self.append_log("Сессия автоматического нейрокомментирования завершена.", "success")
        QMessageBox.information(self, "Успех", "Сессия нейрокомментирования выбранных аккаунтов успешно завершена!")

    def create_category_card(self, title, items, header_traffic=False):
        card = QFrame()
        card.setObjectName("CategoryCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        header_l = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-weight: bold; color: {styles.COLOR_PRIMARY}; font-size: 12px;")
        header_l.addWidget(title_lbl)
        
        if header_traffic:
            badge = QLabel("трафик")
            badge.setStyleSheet("background-color: rgba(230, 81, 0, 0.15); color: #FF9800; font-size: 9px; border: 1px solid #FF9800; border-radius: 4px; padding: 1px 3px; font-weight: bold;")
            header_l.addWidget(badge)
        header_l.addStretch()
        layout.addLayout(header_l)

        for key, name, has_traffic in items:
            item_l = QHBoxLayout()
            item_l.setSpacing(6)
            
            switch = Switch()
            self.switches[key] = switch
            item_l.addWidget(switch)
            
            lbl = QLabel(name)
            lbl.setStyleSheet("font-size: 11px; color: #E0E0E0;")
            item_l.addWidget(lbl)
            
            if has_traffic:
                badge = QLabel("трафик")
                badge.setStyleSheet("background-color: rgba(230, 81, 0, 0.12); color: #FF9800; font-size: 8px; border: 1px solid rgba(230, 81, 0, 0.3); border-radius: 3px; padding: 1px 2px;")
                item_l.addWidget(badge)
            
            item_l.addStretch()
            layout.addLayout(item_l)

        return card

    def refresh_accounts(self):
        self.acc_combo.blockSignals(True)
        self.acc_combo.clear()
        
        self.all_accounts = config_manager.load_config(CONFIG_FILE)
        self.accounts_map = {acc["name"]: acc for acc in self.all_accounts}
        
        self.acc_combo.addItems(list(self.accounts_map.keys()))
        self.acc_combo.blockSignals(False)
        
        # Сбросим выбранные аккаунты, если их больше нет в конфиге
        valid_names = set(acc["name"] for acc in self.all_accounts)
        self.selected_accounts = [self.accounts_map[acc["name"]] for acc in self.selected_accounts if acc["name"] in valid_names]
        
        if self.all_accounts:
            self.on_account_changed(self.acc_combo.currentText())
            
        self.update_selector_ui()

    def on_account_changed(self, acc_name):
        if not acc_name or acc_name not in self.accounts_map:
            return
        
        acc_data = self.accounts_map[acc_name]
        
        if self.current_module == "warmup":
            # Обновим поля профиля
            self.input_bound_channel.setText(acc_data.get("bound_channel", ""))
            self.input_first_name.setText(acc_data.get("first_name", ""))
            self.input_last_name.setText(acc_data.get("last_name", ""))
            self.input_bio.setText(acc_data.get("bio", ""))
            
            # Обновим чаты прогрева
            chats_list = acc_data.get("warmup_chat_links", "")
            self.input_warmup_chats.setPlainText(chats_list)
            
            # Обновим задержки и длительность
            min_delay = acc_data.get("warmup_min_delay", "4")
            max_delay = acc_data.get("warmup_max_delay", "10")
            warmup_duration = acc_data.get("warmup_duration", "30")
            
            self.input_min_delay.setText(str(min_delay))
            self.input_max_delay.setText(str(max_delay))
            self.input_warmup_duration.setText(str(warmup_duration))
            
            # Загрузка переключателей
            warmup_settings = acc_data.get("warmup_settings", {})
            for key, switch in self.switches.items():
                switch.setChecked(warmup_settings.get(key, True))

            self.combo_dialogue_mode.setCurrentText(acc_data.get("warmup_dialogue_mode", "Группа / Чат"))
            self.switch_enable_dialogues.setChecked(acc_data.get("warmup_enable_dialogues", False))
            self.input_dialogue_chat.setText(acc_data.get("warmup_dialogue_chat", ""))
            self.input_dialogue_prompt.setPlainText(acc_data.get("warmup_dialogue_prompt", "Обсуждение технологий, стартапов, ИИ и будущего интернета. Общайтесь как обычные люди, спорьте или соглашайтесь друг с другом."))
            self.input_dialogue_min_msgs.setText(str(acc_data.get("warmup_dialogue_min_msgs", "3")))
            self.input_dialogue_max_msgs.setText(str(acc_data.get("warmup_dialogue_max_msgs", "7")))
            
            # Make sure panel state updates visually
            self.update_dialogues_panel_state()
                
            # Загрузка локального аватара
            workdir = acc_data.get("workdir")
            local_avatar = os.path.join(workdir, "avatar.jpg") if workdir else None
            if local_avatar and os.path.exists(local_avatar):
                self.load_avatar(local_avatar)
            else:
                self.load_avatar(None)
                
            # Очистим секцию постинга при переключении
            if hasattr(self, 'input_post_text'):
                self.input_post_text.clear()
            if hasattr(self, 'input_post_photo'):
                self.input_post_photo.clear()
                
            # Обновим секцию канала
            self.update_channel_section_visibility()
                
            self.append_log(f"Выбран профиль редактора '{acc_name}'. Вы можете просмотреть или изменить его настройки.", "info")
            
        elif self.current_module == "commenting":
            c_sett = acc_data.get("commenting_settings", {})
            self.combo_provider.setCurrentText(c_sett.get("provider", "OpenAI-совместимый"))
            self.combo_ai_style.setCurrentText(c_sett.get("ai_style", "Обычный пользователь (Естественный)"))
            self.input_api_key.setText(c_sett.get("api_key", ""))
            self.input_api_base_url.setText(c_sett.get("api_base_url", ""))
            self.input_model_name.setText(c_sett.get("model_name", ""))
            self.input_prompt.setPlainText(c_sett.get("prompt", "Напиши короткий, естественный комментарий к посту. Пиши как обычный пользователь соцсетей, просто и живо. Без смайликов, без хештегов."))
            self.input_channels.setPlainText(c_sett.get("channels", ""))
            self.input_keywords_raw.setText(c_sett.get("keywords", ""))
            
            # Switch and controls
            protection_active = c_sett.get("ai_protection", False)
            self.switch_ai_protection.setChecked(protection_active)
            self.on_protection_toggled(protection_active)
            
            preset = c_sett.get("protection_preset", "balanced")
            self.on_preset_clicked(preset)

            followup_active = c_sett.get("followup_enabled", False)
            self.switch_followup.setChecked(followup_active)
            self.followup_settings_widget.setVisible(followup_active)
            
            followup_hours = c_sett.get("followup_hours", 3)
            self.slider_followup_hours.setValue(followup_hours)
            self.lbl_followup_hours.setText(f"{followup_hours} ч")
            
            followup_chance = c_sett.get("followup_chance", 30)
            self.slider_followup_chance.setValue(followup_chance)
            self.lbl_followup_chance.setText(f"{followup_chance}%")
            
            mode = c_sett.get("mode", "Случайный")
            self.comment_mode_control.set_value(mode)
            self.on_comment_mode_changed(mode)
            
            chance = c_sett.get("chance", 26)
            self.slider_chance.setValue(chance)
            self.chance_val_lbl.setText(f"{chance}%")
            
            limit_mode = c_sett.get("limit_mode", "По количеству")
            self.limit_mode_control.set_value(limit_mode)
            
            max_comments = c_sett.get("max_comments", 500)
            self.slider_limit.setValue(max_comments)
            self.limit_val_lbl.setText(str(max_comments))
            
            self.update_channels_count_badge()
            self.on_limit_mode_changed(limit_mode)
            
            # Load global distribution and prompt configs
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                global_settings = data.get("settings", {})
                
                work_mode = global_settings.get("commenting_work_mode", "multithreaded")
                self.selected_work_mode = work_mode
                self.card_work_multithread.set_active(work_mode == "multithreaded")
                self.card_work_standard.set_active(work_mode == "standard")
                self.distribution_details_widget.setVisible(work_mode == "multithreaded")
                
                strict_pinning = global_settings.get("commenting_strict_pinning", False)
                self.switch_strict_pinning.setChecked(strict_pinning)
                
                gen_dist = global_settings.get("commenting_general_distribution", "@channel_one\n@channel_two\nhttps://t.me/addlist/...")
                self.txt_general_distribution.setPlainText(gen_dist)
                
                # Load custom prompts
                self.custom_prompts = global_settings.get("commenting_custom_prompts", self.custom_prompts)
                
                # Load active language detection
                auto_lang = global_settings.get("commenting_auto_language", False)
                self.switch_auto_lang.setChecked(auto_lang)
            except Exception:
                pass
                
            # Load active prompt name
            self.active_prompt_name = c_sett.get("selected_prompt_name", "Позитивный комментарий")
            
            # Load switch_use_ai_prompt state
            use_ai_prompt = c_sett.get("use_ai_prompt", True)
            self.switch_use_ai_prompt.setChecked(use_ai_prompt)
            self.on_use_ai_prompt_toggled(use_ai_prompt)
            
            # Load switch_rotate_prompts state
            rotate_prompts = c_sett.get("rotate_prompts", False)
            self.switch_rotate_prompts.setChecked(rotate_prompts)
            
            self.update_prompts_grids()
            
            self.append_log(f"Выбран профиль '{acc_name}' для комментирования. Настройки загружены.", "info")

    def append_log(self, text, status="info"):
        if not hasattr(self, 'console_output') or self.console_output is None:
            return
        try:
            # Touch document to ensure C++ object isn't deleted
            self.console_output.document()
        except RuntimeError:
            return

        if "<span" in text:
            self.console_output.append(text)
        else:
            prefix = "[sys]"
            color_map = {
                "success": "#00e676",
                "error": "#ff5252",
                "warning": "#fbc02d",
                "info": f"{styles.COLOR_TEXT_MUTED}",
            }
            color = color_map.get(status, "white")
            formatted = f"<span style='color: {color};'>{prefix} {text}</span>"
            self.console_output.append(formatted)
        
        try:
            self.console_output.verticalScrollBar().setValue(self.console_output.verticalScrollBar().maximum())
        except RuntimeError:
            pass

    def update_selector_ui(self):
        # 1. Очистка списков виджетов
        self._clear_layout(self.avail_scroll_layout)
        self._clear_layout(self.selected_scroll_layout)

        # 2. Фильтрация доступных аккаунтов
        search_txt = self.search_selector.text().lower().strip()
        only_proxy = self.cb_only_proxy.isChecked()
        hide_running = self.cb_hide_running.isChecked()

        selected_names = set(acc["name"] for acc in self.selected_accounts)
        available_list = []

        for acc in self.all_accounts:
            if acc["name"] in selected_names:
                continue
                
            # Прокси-фильтр
            if only_proxy and not acc.get("proxy_url"):
                continue

            # Фильтр запущенных
            # Мы ищем соответствующие строки из списка AccountListPage, чтобы проверить, запущен ли процесс
            is_running = False
            for row in getattr(self.mgr.acc_list_page, "rows", []):
                if row.name == acc["name"] and row.workdir == acc["workdir"]:
                    if process_manager.is_process_running(row.tg_process):
                        is_running = True
                    break
            
            if hide_running and is_running:
                continue

            # Текстовый фильтр
            if search_txt and search_txt not in acc["name"].lower():
                continue

            available_list.append((acc, is_running))

        # Отрисовка левой панели
        self.lbl_avail_count.setText(f"Отфильтровано: {len(available_list)} / Всего: {len(self.all_accounts)}")
        for acc, is_running in available_list:
            item_frame = self.create_selector_item_row(acc, is_running, to_selected=True)
            self.avail_scroll_layout.addWidget(item_frame)

        # Отрисовка правой панели
        self.lbl_selected_count.setText(f"{len(self.selected_accounts)} выбрано")
        for acc in self.selected_accounts:
            # Проверим, запущен ли выбранный аккаунт
            is_running = False
            for row in getattr(self.mgr.acc_list_page, "rows", []):
                if row.name == acc["name"] and row.workdir == acc["workdir"]:
                    if process_manager.is_process_running(row.tg_process):
                        is_running = True
                    break
            item_frame = self.create_selector_item_row(acc, is_running, to_selected=False)
            self.selected_scroll_layout.addWidget(item_frame)

        if self.current_module == "commenting":
            self.update_distribution_grid()

    def create_selector_item_row(self, acc, is_running, to_selected):
        frame = QFrame()
        frame.setObjectName("SelectorItemRow")
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(8)

        # Аватарка (мини)
        avatar = QLabel()
        avatar.setFixedSize(28, 28)
        avatar_path = os.path.join(acc["workdir"], "avatar.jpg")
        if os.path.exists(avatar_path):
            original = QPixmap(avatar_path)
            if not original.isNull():
                render_size = 28
                rounded = QPixmap(render_size, render_size)
                rounded.fill(Qt.GlobalColor.transparent)
                painter = QPainter(rounded)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                path = QPainterPath()
                path.addEllipse(0, 0, render_size, render_size)
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, original.scaled(render_size, render_size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
                painter.end()
                avatar.setPixmap(rounded)
        if avatar.pixmap() is None:
            avatar.setText("👤")
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar.setStyleSheet(f"font-size: 13px; color: {styles.COLOR_PRIMARY}; background-color: {styles.COLOR_CONSOLE_BG}; border-radius: 14px; border: 1px solid {styles.COLOR_BORDER_DARK};")
        
        layout.addWidget(avatar)

        # Имя и прокси
        info_l = QVBoxLayout()
        info_l.setSpacing(0)
        
        name_lbl = QLabel(acc["name"])
        name_lbl.setStyleSheet("font-weight: bold; font-size: 12px; color: #E0E0E0;")
        info_l.addWidget(name_lbl)
        
        proxy_info = "Без прокси"
        if acc.get("proxy_url"):
            # Короткий вывод хоста
            url = acc.get("proxy_url")
            if "@" in url:
                proxy_info = "🌐 " + url.split("@")[-1]
            else:
                proxy_info = "🌐 " + url.replace("http://", "").replace("socks5://", "")
        proxy_lbl = QLabel(proxy_info)
        proxy_lbl.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 9px;")
        info_l.addWidget(proxy_lbl)
        layout.addLayout(info_l, 1)

        # Статусные баджи
        if is_running:
            run_badge = QLabel("В работе")
            run_badge.setStyleSheet("background-color: rgba(244, 67, 54, 0.15); color: #FF5252; font-size: 9px; border: 1px solid #FF5252; border-radius: 3px; padding: 1px 3px;")
            layout.addWidget(run_badge)
        elif acc.get("proxy_url"):
            proxy_badge = QLabel("Прокси OK")
            bg_badge = "rgba(0, 230, 118, 0.1)" if styles.COLOR_PRIMARY == "#00E676" else "rgba(0, 176, 255, 0.1)"
            border_badge = "rgba(0, 230, 118, 0.3)" if styles.COLOR_PRIMARY == "#00E676" else "rgba(0, 176, 255, 0.3)"
            proxy_badge.setStyleSheet(f"background-color: {bg_badge}; color: {styles.COLOR_PRIMARY}; font-size: 9px; border: 1px solid {border_badge}; border-radius: 3px; padding: 1px 3px;")
            layout.addWidget(proxy_badge)

        # Кнопка перемещения
        btn_action = QPushButton(">>" if to_selected else "<<")
        btn_action.setFixedSize(28, 24)
        if to_selected:
            btn_action.setStyleSheet(f"background-color: {styles.COLOR_HOVER_BG}; color: {styles.COLOR_PRIMARY}; border: 1px solid {styles.COLOR_BORDER_DARK}; border-radius: 4px; font-weight: bold;")
            btn_action.clicked.connect(lambda: self.move_to_selected(acc))
        else:
            btn_action.setStyleSheet("background-color: #2E1111; color: #FF5252; border: 1px solid #5E2424; border-radius: 4px; font-weight: bold;")
            btn_action.clicked.connect(lambda: self.move_to_available(acc))
        layout.addWidget(btn_action)

        return frame

    def move_to_selected(self, acc):
        if acc not in self.selected_accounts:
            self.selected_accounts.append(acc)
            self.update_selector_ui()

    def move_to_available(self, acc):
        self.selected_accounts = [a for a in self.selected_accounts if a["name"] != acc["name"]]
        self.update_selector_ui()

    def add_all_filtered_to_selected(self):
        search_txt = self.search_selector.text().lower().strip()
        only_proxy = self.cb_only_proxy.isChecked()
        hide_running = self.cb_hide_running.isChecked()

        selected_names = set(acc["name"] for acc in self.selected_accounts)

        for acc in self.all_accounts:
            if acc["name"] in selected_names:
                continue
            if only_proxy and not acc.get("proxy_url"):
                continue
            
            is_running = False
            for row in getattr(self.mgr.acc_list_page, "rows", []):
                if row.name == acc["name"] and row.workdir == acc["workdir"]:
                    if process_manager.is_process_running(row.tg_process):
                        is_running = True
                    break
            
            if hide_running and is_running:
                continue
            if search_txt and search_txt not in acc["name"].lower():
                continue

            self.selected_accounts.append(acc)
            
        self.update_selector_ui()

    def remove_all_from_selected(self):
        self.selected_accounts.clear()
        self.update_selector_ui()

    def load_avatar(self, avatar_path=None):
        self.current_avatar_path = avatar_path
        if avatar_path and os.path.exists(avatar_path):
            original_pixmap = QPixmap(avatar_path)
            if not original_pixmap.isNull():
                render_size = 110
                rounded_pixmap = QPixmap(render_size, render_size)
                rounded_pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(rounded_pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                path = QPainterPath()
                path.addEllipse(0, 0, render_size, render_size)
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, original_pixmap.scaled(render_size, render_size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
                painter.end()
                self.avatar_label.setPixmap(rounded_pixmap)
                self.avatar_label.setStyleSheet(f"border: 2px solid {styles.COLOR_PRIMARY}; border-radius: 55px;")
                return
        
        self.avatar_label.setText("👤")
        self.avatar_label.setStyleSheet(f"""
            QLabel#TelegramAvatarLabel {{
                font-size: 50px; 
                color: {styles.COLOR_PRIMARY}; 
                background-color: {styles.COLOR_CONSOLE_BG}; 
                border-radius: 55px; 
                border: 2px solid {styles.COLOR_BORDER};
            }}
            QLabel#TelegramAvatarLabel:hover {{
                border: 2px solid {styles.COLOR_PRIMARY};
            }}
        """)

    def load_channel_avatar(self, avatar_path=None):
        self.current_channel_avatar_path = avatar_path
        if avatar_path and os.path.exists(avatar_path):
            original_pixmap = QPixmap(avatar_path)
            if not original_pixmap.isNull():
                render_size = 110
                rounded_pixmap = QPixmap(render_size, render_size)
                rounded_pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(rounded_pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                path = QPainterPath()
                path.addEllipse(0, 0, render_size, render_size)
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, original_pixmap.scaled(render_size, render_size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
                painter.end()
                self.chan_avatar_label.setPixmap(rounded_pixmap)
                self.chan_avatar_label.setStyleSheet(f"border: 2px solid {styles.COLOR_PRIMARY}; border-radius: 55px;")
                return
        
        self.chan_avatar_label.setText("📢")
        self.chan_avatar_label.setStyleSheet(f"""
            QLabel#TelegramAvatarLabel {{
                font-size: 50px; 
                color: {styles.COLOR_PRIMARY}; 
                background-color: {styles.COLOR_CONSOLE_BG}; 
                border-radius: 55px; 
                border: 2px solid {styles.COLOR_BORDER};
            }}
            QLabel#TelegramAvatarLabel:hover {{
                border: 2px solid {styles.COLOR_PRIMARY};
            }}
        """)

    def eventFilter(self, obj, event):
        if obj == self.avatar_label and event.type() == event.Type.MouseButtonPress:
            self.choose_and_upload_avatar()
            return True
        elif hasattr(self, 'chan_avatar_label') and obj == self.chan_avatar_label and event.type() == event.Type.MouseButtonPress:
            self.choose_and_upload_channel_avatar()
            return True
        return super().eventFilter(obj, event)

    def get_api_credentials(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                s = data.get("settings", {})
                return s.get("api_id"), s.get("api_hash")
        except:
            return None, None
    def start_worker(self, action, params=None):
        acc_name = self.acc_combo.currentText()
        if not acc_name or acc_name not in self.accounts_map:
            QMessageBox.warning(self, "Внимание", "Аккаунт не выбран!")
            return
        
        api_id, api_hash = acc_data.get("api_id"), acc_data.get("api_hash")
        if not api_id or not api_hash:
            QMessageBox.critical(self, "Ошибка", f"В профиле аккаунта {acc_name} не заполнены API ID или API Hash!")
            return
            
        acc_data = self.accounts_map[acc_name]
        
        self.btn_load_tg.setEnabled(False)
        self.btn_save_profile.setEnabled(False)
        if hasattr(self, 'btn_channel_action'):
            self.btn_channel_action.setEnabled(False)
        if hasattr(self, 'btn_publish_post'):
            self.btn_publish_post.setEnabled(False)
        
        self.worker = ProfileOperationWorker(action, acc_data, api_id, api_hash, params)
        self.worker.log_signal.connect(self.append_log)
        self.worker.operation_finished.connect(self.on_worker_finished)
        
        if action == "fetch":
            self.worker.info_fetched.connect(self.on_info_fetched)
            
        self.worker.start()

    def on_worker_finished(self, success, message):
        self.btn_load_tg.setEnabled(True)
        self.btn_save_profile.setEnabled(True)
        if hasattr(self, 'btn_channel_action'):
            self.btn_channel_action.setEnabled(True)
        if hasattr(self, 'btn_publish_post'):
            self.btn_publish_post.setEnabled(True)
        
        if success:
            self.append_log(f"Операция завершена успешно: {message}", "success")
            if self.worker and self.worker.action == "create_channel":
                self.input_bound_channel.setText(message)
                acc_name = self.acc_combo.currentText()
                if acc_name in self.accounts_map:
                    acc_data = self.accounts_map[acc_name]
                    account_manager.update_bound_channel(CONFIG_FILE, acc_data["workdir"], message)
                    acc_data["bound_channel"] = message
                    self.append_log(f"Канал {message} успешно создан и привязан к текущему профилю аккаунта.", "success")
                    self.update_channel_section_visibility()
            elif self.worker and self.worker.action == "update_channel_profile":
                self.append_log("Изменения названия и описания канала успешно сохранены.", "success")
            elif self.worker and self.worker.action == "update_channel_avatar":
                self.append_log("Аватарка канала успешно сохранена.", "success")
                acc_name = self.acc_combo.currentText()
                if acc_name in self.accounts_map:
                    acc_data = self.accounts_map[acc_name]
                    self.update_channel_section_visibility()
            elif self.worker and self.worker.action == "publish_channel_post":
                self.append_log("Пост успешно опубликован в вашем канале.", "success")
                self.input_post_text.clear()
                self.clear_post_photo()
        else:
            self.append_log(f"Ошибка операции: {message}", "error")
            QMessageBox.critical(self, "Ошибка", f"Не удалось выполнить операцию: {message}")

    def on_info_fetched(self, info):
        self.input_first_name.setText(info.get("first_name", ""))
        self.input_last_name.setText(info.get("last_name", ""))
        self.input_bio.setText(info.get("bio", ""))
        
        avatar_path = info.get("avatar_path")
        if avatar_path:
            self.load_avatar(avatar_path)
            
        # Загрузка полей промо-канала
        chan_info = info.get("channel_info")
        if chan_info:
            self.input_chan_title.setText(chan_info.get("title", ""))
            self.input_chan_desc.setText(chan_info.get("description", ""))
            chan_avatar = chan_info.get("avatar_path")
            if chan_avatar:
                self.load_channel_avatar(chan_avatar)
            else:
                self.load_channel_avatar(None)
            self.append_log("Данные профиля и привязанного канала успешно загружены и отображены в интерфейсе!", "success")
        else:
            self.append_log("Данные профиля успешно загружены и отображены в интерфейсе!", "success")

        # Сохранение данных в локальную базу данных (config.json)
        acc_name = self.acc_combo.currentText()
        if acc_name in self.accounts_map:
            acc_data = self.accounts_map[acc_name]
            first_name = info.get("first_name", "")
            last_name = info.get("last_name", "")
            bio = info.get("bio", "")
            bound_channel = acc_data.get("bound_channel", "")
            
            # Обновление в локальной памяти
            acc_data["first_name"] = first_name
            acc_data["last_name"] = last_name
            acc_data["bio"] = bio
            
            # Обновление в config.json
            account_manager.update_account_profile_data(
                CONFIG_FILE,
                acc_data["workdir"],
                first_name,
                last_name,
                bio,
                bound_channel
            )
            self.append_log("Загруженные данные профиля сохранены в локальную базу данных (config.json)!", "success")

    def load_data_from_telegram(self):
        self.start_worker("fetch")

    def handle_avatar_drop(self, fp):
        acc_name = self.acc_combo.currentText()
        if not acc_name:
            return
        self.append_log(f"Загрузка перетащенного аватара: {fp}", "info")
        self.start_worker("update_avatar", {"photo_path": fp})

    def handle_channel_avatar_drop(self, fp):
        acc_name = self.acc_combo.currentText()
        if not acc_name:
            return
        self.append_log(f"Загрузка перетащенного аватара канала: {fp}", "info")
        self.start_worker("update_channel_avatar", {"photo_path": fp})

    def show_avatar_gallery_dialog(self):
        acc_name = self.acc_combo.currentText()
        if not acc_name:
            QMessageBox.warning(self, "Внимание", "Аккаунт не выбран!")
            return

        dlg = AvatarGalleryDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected_path = dlg.selected_path
            if selected_path:
                self.append_log(f"Выбран аватар из галереи проекта: {os.path.basename(selected_path)}", "info")
                self.start_worker("update_avatar", {"photo_path": selected_path})

    def show_channel_avatar_gallery_dialog(self):
        acc_name = self.acc_combo.currentText()
        if not acc_name:
            QMessageBox.warning(self, "Внимание", "Аккаунт не выбран!")
            return

        dlg = AvatarGalleryDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected_path = dlg.selected_path
            if selected_path:
                self.append_log(f"Выбран аватар канала из галереи проекта: {os.path.basename(selected_path)}", "info")
                self.start_worker("update_channel_avatar", {"photo_path": selected_path})

    def randomize_selected_avatars(self):
        if not self.selected_accounts:
            QMessageBox.warning(self, "Внимание", "Не выбрано ни одного аккаунта для установки аватарок!")
            return

        missing_apis = [acc.get("name") for acc in self.selected_accounts if not acc.get("api_id") or not acc.get("api_hash")]
        if missing_apis:
            QMessageBox.critical(self, "Ошибка", f"У следующих аккаунтов не заполнены API ID/Hash:\n{', '.join(missing_apis)}")
            return
            
        api_id, api_hash = 0, ""

        from src.core.constants import BASE_DIR
        avatars_dir = BASE_DIR / "avatars"
        if not avatars_dir.exists() or not any(avatars_dir.iterdir()):
            QMessageBox.warning(self, "Внимание", f"Папка '{avatars_dir.name}' пуста или не существует в корне проекта!\nПожалуйста, закиньте туда аватарки (.png, .jpg, .jpeg).")
            return

        avatar_files = [
            str(f) for f in avatars_dir.iterdir()
            if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg")
        ]

        if not avatar_files:
            QMessageBox.warning(self, "Внимание", "В папке avatars не найдено подходящих изображений (.png, .jpg, .jpeg)!")
            return

        self.btn_run_warmup.setEnabled(False)
        self.btn_save_warmup.setEnabled(False)
        self.btn_schedule_warmup.setEnabled(False)
        
        self.append_log(f"Начало массовой установки случайных аватарок для {len(self.selected_accounts)} аккаунтов...", "info")
        
        self.mass_avatar_worker = MassAvatarUpdateWorker(self.selected_accounts, api_id, api_hash, avatar_files)
        self.mass_avatar_worker.log_signal.connect(self.append_log)
        
        def on_finished():
            self.btn_run_warmup.setEnabled(True)
            self.btn_save_warmup.setEnabled(True)
            self.btn_schedule_warmup.setEnabled(True)
            self.append_log("Массовая установка аватарок успешно завершена!", "success")
            QMessageBox.information(self, "Успех", "Массовая установка аватарок завершена!")
            
        self.mass_avatar_worker.finished_signal.connect(on_finished)
        self.mass_avatar_worker.start()

    def choose_and_upload_avatar(self):
        acc_name = self.acc_combo.currentText()
        if not acc_name:
            return
            
        fp, _ = QFileDialog.getOpenFileName(self, "Выбрать фото профиля", "", "Images (*.png *.jpg *.jpeg)")
        if not fp:
            return
            
        self.start_worker("update_avatar", {"photo_path": fp})

    def update_bio_counter(self, text):
        self.bio_counter.setText(f"{len(text)} / 70")

    def save_profile_changes(self):
        acc_name = self.acc_combo.currentText()
        if not acc_name or acc_name not in self.accounts_map:
            return
            
        acc_data = self.accounts_map[acc_name]
        
        # 1. Считаем данные из интерфейса
        first_name = self.input_first_name.text().strip()
        last_name = self.input_last_name.text().strip() or ""
        bio = self.input_bio.text().strip()
        channel = self.input_bound_channel.text().strip() or None
        
        if not first_name:
            QMessageBox.warning(self, "Внимание", "Поле имени в Telegram не может быть пустым!")
            return

        # 2. Сохраним профиль и канал локально в память и config.json
        acc_data["first_name"] = first_name
        acc_data["last_name"] = last_name
        acc_data["bio"] = bio
        acc_data["bound_channel"] = channel
        
        account_manager.update_account_profile_data(CONFIG_FILE, acc_data["workdir"], first_name, last_name, bio, channel)
        self.update_channel_section_visibility()
        
        # 3. Сохраним тумблеры и ссылки на чаты
        self.save_warmup_settings_locally()
        self.append_log("Все локальные настройки профиля и прогрева сохранены.", "success")
        
        # 4. Отправим изменения в Telegram
        self.start_worker("update_profile", {
            "first_name": first_name,
            "last_name": last_name,
            "bio": bio
        })

    def update_channel_section_visibility(self):
        acc_name = self.acc_combo.currentText()
        if not acc_name or acc_name not in self.accounts_map:
            return
            
        acc_data = self.accounts_map[acc_name]
        bound_channel = acc_data.get("bound_channel")
        
        if bound_channel:
            self.channel_section_title.setText(f"Управление промо-каналом: {bound_channel}")
            self.input_chan_user.setText(bound_channel)
            self.input_chan_user.setPlaceholderText("Привязанный канал")
            self.input_chan_user.setReadOnly(True)
            self.chan_user_lbl.setText("Привязан:")
            
            # Action button is for updating profile
            self.btn_channel_action.setText("💾 Применить изменения канала")
            ac_fg = "#000000" if styles.COLOR_PRIMARY == "#00E676" else "#FFFFFF"
            self.btn_channel_action.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY_DARK}; color: {ac_fg}; font-weight: bold;")
            
            # Enable posting
            self.input_post_text.setEnabled(True)
            self.input_post_text.setPlaceholderText("Введите текст поста...")
            self.btn_browse_post_photo.setEnabled(True)
            self.btn_clear_post_photo.setEnabled(True)
            self.btn_publish_post.setEnabled(True)
            self.chan_avatar_sub.setText("Нажмите для смены")
            if hasattr(self, 'btn_chan_avatar_gallery'):
                self.btn_chan_avatar_gallery.setEnabled(True)
            
            # Попробуем загрузить локальный аватар
            workdir = acc_data.get("workdir")
            local_chan_avatar = os.path.join(workdir, "channel_avatar.jpg") if workdir else None
            if local_chan_avatar and os.path.exists(local_chan_avatar):
                self.load_channel_avatar(local_chan_avatar)
            else:
                self.load_channel_avatar(None)
        else:
            self.channel_section_title.setText("Управление промо-каналом (Канал не привязан)")
            self.input_chan_title.clear()
            self.input_chan_desc.clear()
            self.input_chan_user.clear()
            self.input_chan_user.setPlaceholderText("@username (для создания публичного)")
            self.input_chan_user.setReadOnly(False)
            self.chan_user_lbl.setText("Юзернейм:")
            
            # Action button is for creating a new channel
            self.btn_channel_action.setText("✨ Создать канал")
            ac_fg = "#000000" if styles.COLOR_PRIMARY == "#00E676" else "#FFFFFF"
            self.btn_channel_action.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY}; color: {ac_fg}; font-weight: bold;")
            
            # Disable posting
            self.input_post_text.clear()
            self.input_post_text.setEnabled(False)
            self.input_post_text.setPlaceholderText("Сначала привяжите канал в профиле или создайте новый!")
            self.btn_browse_post_photo.setEnabled(False)
            self.btn_clear_post_photo.setEnabled(False)
            self.btn_publish_post.setEnabled(False)
            self.chan_avatar_sub.setText("Смена невозможна")
            if hasattr(self, 'btn_chan_avatar_gallery'):
                self.btn_chan_avatar_gallery.setEnabled(False)
            
            self.load_channel_avatar(None)

    def on_channel_action_clicked(self):
        acc_name = self.acc_combo.currentText()
        if not acc_name or acc_name not in self.accounts_map:
            return
            
        acc_data = self.accounts_map[acc_name]
        bound_channel = acc_data.get("bound_channel")
        
        if bound_channel:
            self.save_channel_changes()
        else:
            title = self.input_chan_title.text().strip()
            desc = self.input_chan_desc.text().strip()
            user = self.input_chan_user.text().strip()
            
            if not title:
                QMessageBox.warning(self, "Внимание", "Название канала не может быть пустым!")
                return
                
            self.start_worker("create_channel", {
                "title": title,
                "description": desc,
                "username": user
            })

    def choose_and_upload_channel_avatar(self):
        acc_name = self.acc_combo.currentText()
        if not acc_name:
            return
            
        fp, _ = QFileDialog.getOpenFileName(self, "Выбрать фото канала", "", "Images (*.png *.jpg *.jpeg)")
        if not fp:
            return
            
        self.start_worker("update_channel_avatar", {"photo_path": fp})

    def save_channel_changes(self):
        title = self.input_chan_title.text().strip()
        desc = self.input_chan_desc.text().strip()
        
        if not title:
            QMessageBox.warning(self, "Внимание", "Название канала не может быть пустым!")
            return
            
        self.start_worker("update_channel_profile", {
            "title": title,
            "description": desc
        })

    def choose_post_photo(self):
        fp, _ = QFileDialog.getOpenFileName(self, "Выбрать фото для поста", "", "Images (*.png *.jpg *.jpeg)")
        if fp:
            self.input_post_photo.setText(fp)

    def clear_post_photo(self):
        self.input_post_photo.clear()

    def publish_channel_post(self):
        text = self.input_post_text.toPlainText().strip()
        photo = self.input_post_photo.text().strip()
        
        if not text and not photo:
            QMessageBox.warning(self, "Внимание", "Нельзя отправить пустой пост! Введите текст или выберите фото.")
            return
            
        self.start_worker("publish_channel_post", {
            "text": text,
            "photo_path": photo if photo else None
        })

    def save_warmup_settings_locally(self):
        acc_name = self.acc_combo.currentText()
        if not acc_name or acc_name not in self.accounts_map:
            return
            
        acc_data = self.accounts_map[acc_name]
        
        settings_dict = {}
        for key, switch in self.switches.items():
            settings_dict[key] = switch.isChecked()
            
        acc_data["warmup_settings"] = settings_dict
        acc_data["warmup_chat_links"] = self.input_warmup_chats.toPlainText().strip()
        acc_data["warmup_min_delay"] = self.input_min_delay.text().strip() or "4"
        acc_data["warmup_max_delay"] = self.input_max_delay.text().strip() or "10"
        acc_data["warmup_duration"] = self.input_warmup_duration.text().strip() or "30"
        acc_data["warmup_dialogue_mode"] = self.combo_dialogue_mode.currentText()
        acc_data["warmup_dialogue_chat"] = self.input_dialogue_chat.text().strip()
        acc_data["warmup_dialogue_prompt"] = self.input_dialogue_prompt.toPlainText().strip()
        acc_data["warmup_dialogue_min_msgs"] = self.input_dialogue_min_msgs.text().strip() or "3"
        acc_data["warmup_dialogue_max_msgs"] = self.input_dialogue_max_msgs.text().strip() or "7"
        acc_data["warmup_enable_dialogues"] = self.switch_enable_dialogues.isChecked()
        
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for acc in data.get("accounts", []):
                if acc["name"] == acc_name:
                    acc["warmup_settings"] = settings_dict
                    acc["warmup_chat_links"] = self.input_warmup_chats.toPlainText().strip()
                    acc["warmup_min_delay"] = self.input_min_delay.text().strip() or "4"
                    acc["warmup_max_delay"] = self.input_max_delay.text().strip() or "10"
                    acc["warmup_duration"] = self.input_warmup_duration.text().strip() or "30"
                    acc["warmup_dialogue_mode"] = self.combo_dialogue_mode.currentText()
                    acc["warmup_dialogue_chat"] = self.input_dialogue_chat.text().strip()
                    acc["warmup_dialogue_prompt"] = self.input_dialogue_prompt.toPlainText().strip()
                    acc["warmup_dialogue_min_msgs"] = self.input_dialogue_min_msgs.text().strip() or "3"
                    acc["warmup_dialogue_max_msgs"] = self.input_dialogue_max_msgs.text().strip() or "7"
                    acc["warmup_enable_dialogues"] = self.switch_enable_dialogues.isChecked()
                    acc["bound_channel"] = acc_data.get("bound_channel")
                    break
                    
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            farm_manager.save_active_farm_config()
            self.refresh_accounts()
        except Exception as e:
            self.append_log(f"Не удалось записать настройки в файл: {e}", "error")

    def save_warmup_only(self):
        self.save_warmup_settings_locally()
        self.append_log("Настройки прогрева и список чатов сохранены в конфигурацию.", "success")
        QMessageBox.information(self, "Успех", "Настройки прогрева успешно сохранены!")

    def enable_all_switches(self):
        for switch in self.switches.values():
            switch.setChecked(True)
        self.append_log("Все тумблеры прогрева активированы.", "info")

    def disable_all_switches(self):
        for switch in self.switches.values():
            switch.setChecked(False)
        self.append_log("Все тумблеры прогрева отключены.", "info")

    def apply_economy_mode(self):
        traffic_keys = {"scroll_channels", "watch_video", "listen_voice", "search_gif", "view_stickers", "preview_links"}
        for key, switch in self.switches.items():
            if key in traffic_keys:
                switch.setChecked(False)
            else:
                switch.setChecked(True)
        self.append_log("Включен экономный режим: действия с высоким расходом трафика отключены.", "warning")

    def start_automatic_warmup(self):
        if not self.selected_accounts:
            QMessageBox.warning(self, "Внимание", "Выберите хотя бы один аккаунт в списке справа для запуска прогрева!")
            return
            
        missing_apis = [acc.get("name") for acc in self.selected_accounts if not acc.get("api_id") or not acc.get("api_hash")]
        if missing_apis:
            QMessageBox.critical(self, "Ошибка", f"У следующих аккаунтов не заполнены API ID/Hash:\n{', '.join(missing_apis)}")
            return
            
        api_id, api_hash = 0, ""
            
        chat_links = self.input_warmup_chats.toPlainText().strip()
        if not chat_links:
            QMessageBox.warning(self, "Внимание", "Введите хотя бы одну ссылку на чат для прогрева!")
            return
            
        # Сбор параметров
        params = {
            "chat_links": chat_links,
            "use_bots": self.switches.get("inline_bots").isChecked(),
            "enable_neuro_dialogues": self.switch_enable_dialogues.isChecked(),
            "neuro_dialogue_mode": self.combo_dialogue_mode.currentText(),
            "neuro_dialogue_chat": self.input_dialogue_chat.text().strip(),
            "neuro_dialogue_prompt": self.input_dialogue_prompt.toPlainText().strip(),
            "neuro_dialogue_min_msgs": self.input_dialogue_min_msgs.text().strip() or "3",
            "neuro_dialogue_max_msgs": self.input_dialogue_max_msgs.text().strip() or "7",
        }
        
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                s = cfg.get("settings", {})
                
                # Читаем параметры задержек и длительности из UI
                min_del = self.input_min_delay.text().strip() or "4"
                max_del = self.input_max_delay.text().strip() or "10"
                w_dur = self.input_warmup_duration.text().strip() or "30"
                
                params.update({
                    "api_key": s.get("default_ai_api_key", ""),
                    "api_base_url": s.get("default_ai_base_url", ""),
                    "model_name": s.get("default_ai_model_name", ""),
                    "reactions_chance": "20",
                    "write_chance": "10",
                    "min_delay": min_del,
                    "max_delay": max_del,
                    "warmup_duration": w_dur
                })
        except:
            pass
            
        self.btn_run_warmup.setEnabled(False)
        self.btn_run_warmup.setText("⌛ Прогрев выполняется...")
        self.btn_stop_warmup.setEnabled(True)
        self.btn_stop_warmup.setText("Остановить прогрев")
        self.warmer_cancelled = False
        
        selected_names_str = ", ".join(a["name"] for a in self.selected_accounts)
        self.append_log(f"Запуск сессии автопрогрева для аккаунтов: {selected_names_str}...", "warning")
        
        # Запуск параллельного воркера
        self.warmer_worker = WarmerExecutionWorker(self.selected_accounts, api_id, api_hash, params)
        self.warmer_worker.log_signal.connect(self.append_log)
        self.warmer_worker.finished_signal.connect(self.on_warmer_finished)
        self.warmer_worker.start()

    def stop_automatic_warmup(self):
        if not hasattr(self, "warmer_worker") or not self.warmer_worker.isRunning():
            return
        self.btn_stop_warmup.setEnabled(False)
        self.btn_stop_warmup.setText("⌛ Остановка...")
        self.append_log("Запрос на остановку прогрева отправлен. Ожидайте завершения процессов...", "warning")
        self.warmer_cancelled = True
        self.warmer_worker.stop()

    def update_dialogues_panel_state(self):
        is_on = self.switch_enable_dialogues.isChecked()
        self.dialogues_settings_widget.setEnabled(is_on)

    def on_dialogue_mode_changed(self, mode):
        is_group = (mode == "Группа / Чат")
        self.dialogue_chat_label.setVisible(is_group)
        self.input_dialogue_chat.setVisible(is_group)

    def on_warmer_finished(self):
        self.btn_run_warmup.setEnabled(True)
        self.btn_run_warmup.setText("Запустить авто-прогрев")
        self.btn_stop_warmup.setEnabled(False)
        self.btn_stop_warmup.setText("Остановить прогрев")
        self.append_log("Параллельная сессия автоматического прогрева завершена.", "success")
        if getattr(self, "warmer_cancelled", False):
            self.warmer_cancelled = False
            QMessageBox.information(self, "Информация", "Сессия автоматического прогрева остановлена пользователем!")
        else:
            QMessageBox.information(self, "Успех", "Сессия автоматического прогрева выбранных аккаунтов успешно завершена!")

    def on_work_mode_changed(self, mode):
        self.selected_work_mode = mode
        self.card_work_multithread.set_active(mode == "multithreaded")
        self.card_work_standard.set_active(mode == "standard")
        
        # standard mode must collapse/hide details
        self.distribution_details_widget.setVisible(mode == "multithreaded")
        self.update_ratio_badge()
        self.update_scheme_badges()

    def test_api_connection(self):
        api_key = self.input_api_key.text().strip()
        if not api_key:
            QMessageBox.warning(self, "Внимание", "Пожалуйста, введите API Ключ!")
            return
            
        provider = self.combo_provider.currentText()
        base_url = self.input_api_base_url.text().strip()
        model_name = self.input_model_name.text().strip()
        
        self.append_log(f"Проверка подключения к {provider}... Ожидание ответа...", "info")
        
        self.api_test_worker = ApiTestWorker(provider, api_key, base_url, model_name, self)
        self.api_test_worker.finished_signal.connect(self.on_api_test_finished)
        self.api_test_worker.start()

    def on_api_test_finished(self, success, message):
        if success:
            QMessageBox.information(self, "Успех", message)
            self.append_log(message, "success")
        else:
            QMessageBox.critical(self, "Ошибка", message)
            self.append_log(message, "error")

    def update_distribution_grid(self):
        # 1. Clear old table contents
        self.distribution_table.setRowCount(0)
        
        # 2. Re-create rows for all selected accounts
        for i, acc in enumerate(self.selected_accounts):
            acc_name = acc["name"]
            c_sett = acc.setdefault("commenting_settings", {})
            channels_text = c_sett.get("channels", "")
            prompt_text = c_sett.get("prompt", "")
            
            # Count channels
            channels_count = len([line.strip() for line in channels_text.split("\n") if line.strip()])
            
            # Row setup
            self.distribution_table.insertRow(i)
            
            # Item 0: Account Name
            name_item = QTableWidgetItem(acc_name)
            name_item.setForeground(QColor("#FFFFFF"))
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.distribution_table.setItem(i, 0, name_item)
            
            # Item 1: Channels count
            count_item = QTableWidgetItem(f"{channels_count} каналов")
            count_item.setForeground(QColor(styles.COLOR_PRIMARY))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.distribution_table.setItem(i, 1, count_item)
            
            # Item 2: Prompt Style
            prompt_summary = "Индивидуальный" if prompt_text.strip() else "По умолчанию"
            prompt_item = QTableWidgetItem(prompt_summary)
            prompt_item.setForeground(QColor("#8B9A8B" if not prompt_text.strip() else styles.COLOR_PRIMARY))
            prompt_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.distribution_table.setItem(i, 2, prompt_item)
            
            # Item 3: Actions (Edit / Reset buttons)
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(6)
            
            btn_edit = QPushButton("Изменить")
            btn_edit.setIcon(QIcon(str(NOTE_ICON_PATH)))
            btn_edit.setStyleSheet(f"padding: 2px 8px; font-size: 11px; background-color: rgba(0, 230, 118, 0.1) if styles.COLOR_PRIMARY == '#00E676' else rgba(0, 176, 255, 0.1); border: 1px solid {styles.COLOR_PRIMARY}; color: {styles.COLOR_PRIMARY};")
            btn_edit.clicked.connect(lambda checked, name=acc_name: self.edit_single_account_channels(name))
            
            btn_clear = QPushButton("Сбросить")
            btn_clear.setIcon(QIcon(str(DELETE_ICON_PATH)))
            btn_clear.setStyleSheet("padding: 2px 8px; font-size: 11px; background-color: rgba(255, 82, 82, 0.1); border: 1px solid rgba(255, 82, 82, 0.3); color: #FF5252;")
            btn_clear.clicked.connect(lambda checked, name=acc_name: self.clear_single_account_channels(name))
            
            actions_layout.addWidget(btn_edit)
            actions_layout.addWidget(btn_clear)
            actions_widget.setLayout(actions_layout)
            self.distribution_table.setCellWidget(i, 3, actions_widget)
            
        self.update_ratio_badge()
        self.update_scheme_badges()

    def edit_single_account_channels(self, acc_name):
        target_acc = None
        for acc in self.selected_accounts:
            if acc["name"] == acc_name:
                target_acc = acc
                break
                
        if not target_acc:
            return
            
        c_sett = target_acc.setdefault("commenting_settings", {})
        channels_text = c_sett.get("channels", "")
        prompt_text = c_sett.get("prompt", "")
        
        dialog = EditAccountChannelsDialog(acc_name, channels_text, prompt_text, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_channels, new_prompt = dialog.get_data()
            c_sett["channels"] = new_channels
            c_sett["prompt"] = new_prompt
            
            self.save_commenting_settings_locally()
            self.update_distribution_grid()
            self.append_log(f"Настройки аккаунта {acc_name} успешно обновлены.", "success")
            
    def clear_single_account_channels(self, acc_name):
        target_acc = None
        for acc in self.selected_accounts:
            if acc["name"] == acc_name:
                target_acc = acc
                break
                
        if not target_acc:
            return
            
        c_sett = target_acc.setdefault("commenting_settings", {})
        c_sett["channels"] = ""
        c_sett["prompt"] = ""
            
        self.save_commenting_settings_locally()
        self.update_distribution_grid()
        self.append_log(f"Настройки распределения для {acc_name} сброшены.", "info")

    def distribute_channels_evenly(self):
        text = self.txt_general_distribution.toPlainText().strip()
        channels = [line.strip() for line in text.split("\n") if line.strip()]
        if not channels:
            QMessageBox.warning(self, "Внимание", "Общее поле распределения не содержит каналов!")
            return
            
        if not self.selected_accounts:
            QMessageBox.warning(self, "Внимание", "Не выбрано ни одного аккаунта для распределения!")
            return
            
        self.auto_distributed_channels.clear()
        
        # 1. Сбор пула промптов
        prompt_mode = self.combo_distribute_prompts.currentText()
        prompts_pool = []
        if prompt_mode in ["Из склада промптов (Случайно)", "Из галереи (Случайно)"]:
            for p in self.system_prompts.values():
                prompts_pool.append(p["text"])
            for p in self.custom_prompts:
                prompts_pool.append(p["text"])
        elif prompt_mode == "Пресеты стилей (Случайно)":
            prompts_pool = [
                "Ты — опытный админ крипто-канала, общающийся со своей аудиторией на равных. Пиши короткие, живые комменты (от 3 до 10 слов), используя крипто-сленг (гем, ворк, лайфчейндж, скипаем, заносим, смарт-мув, бритва). Будь уверенным, дерзким, но дружелюбным. Без приветствий, без хэштегов.",
                "Ты — эксперт с высоким уровнем IQ. Оставляй короткие (до 10 слов), содержательные, хорошо структурированные и умные комментарии к посту. Используй точные формулировки. Без приветствий, без смайликов.",
                "Оставляй короткие, ироничные или саркастические комментарии к постам. Пошути или мягко подстебни тему поста. Пиши как обычный пользователь соцсетей, очень живо и весело. Не пиши банальностей.",
                "Оставляй короткие (2-6 слов), скептические или критические комментарии. Сомневайся в полезности поста, но делай это смешно и естественно. Будь краток.",
                "Напиши короткий, естественный комментарий к посту. Пиши как обычный пользователь соцсетей, просто и живо. Без смайликов, без хештегов."
            ]
        
        if self.selected_work_mode == "multithreaded":
            accounts_count = len(self.selected_accounts)
            distributed = {acc["name"]: [] for acc in self.selected_accounts}
            for idx, chan in enumerate(channels):
                acc_name = self.selected_accounts[idx % accounts_count]["name"]
                distributed[acc_name].append(chan)
                
            for acc in self.selected_accounts:
                assigned = distributed.get(acc["name"], [])
                assigned_text = "\n".join(assigned)
                c_sett = acc.setdefault("commenting_settings", {})
                c_sett["channels"] = assigned_text
                self.auto_distributed_channels[acc["name"]] = assigned_text
                
                # Распределить случайный промпт
                if prompts_pool:
                    rand_prompt = random.choice(prompts_pool)
                    c_sett["prompt"] = rand_prompt
                    c_sett["ai_style"] = "Свой промпт (из склада ниже)"
                
        else: # standard
            full_text = "\n".join(channels)
            for acc in self.selected_accounts:
                c_sett = acc.setdefault("commenting_settings", {})
                c_sett["channels"] = full_text
                self.auto_distributed_channels[acc["name"]] = full_text
                
                # Распределить случайный промпт
                if prompts_pool:
                    rand_prompt = random.choice(prompts_pool)
                    c_sett["prompt"] = rand_prompt
                    c_sett["ai_style"] = "Свой промпт (из склада ниже)"
                
        self.save_commenting_settings_locally()
        self.update_distribution_grid()
        self.append_log("Каналы и промпты успешно распределены по аккаунтам.", "success")

    def update_ratio_badge(self):
        text = self.txt_general_distribution.toPlainText().strip()
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        lines_count = len(lines)
        accs_count = len(self.selected_accounts)
        
        import math
        ratio = math.ceil(lines_count / accs_count) if accs_count > 0 else 0
        
        if lines_count % 10 == 1 and lines_count % 100 != 11:
            suffix = "папка"
        elif 2 <= lines_count % 10 <= 4 and (lines_count % 100 < 10 or lines_count % 100 >= 20):
            suffix = "папки"
        else:
            suffix = "папок"
            
        self.lbl_ratio_badge.setText(f"{lines_count} {suffix} / {accs_count} акк. = ~{ratio}/акк")

    def update_scheme_badges(self):
        text = self.txt_general_distribution.toPlainText().strip()
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        targets_count = len(lines)
        accs_count = len(self.selected_accounts)
        
        if targets_count % 10 == 1 and targets_count % 100 != 11:
            tgt_suffix = "цель"
        elif 2 <= targets_count % 10 <= 4 and (targets_count % 100 < 10 or targets_count % 100 >= 20):
            tgt_suffix = "цели"
        else:
            tgt_suffix = "целей"
            
        self.lbl_badge_targets.setText(f"{targets_count} {tgt_suffix}")
        
        manual_count = 0
        if targets_count > 0 and accs_count > 0:
            if self.selected_work_mode == "multithreaded":
                distributed = {acc["name"]: [] for acc in self.selected_accounts}
                for idx, chan in enumerate(lines):
                    acc_name = self.selected_accounts[idx % accs_count]["name"]
                    distributed[acc_name].append(chan)
            else:
                distributed = {acc["name"]: lines for acc in self.selected_accounts}
                
            for acc in self.selected_accounts:
                expected = "\n".join(distributed.get(acc["name"], []))
                c_sett = acc.get("commenting_settings", {})
                actual = c_sett.get("channels", "").strip()
                if actual != expected:
                    manual_count += 1
        else:
            for acc in self.selected_accounts:
                c_sett = acc.get("commenting_settings", {})
                if c_sett.get("channels", "").strip():
                    manual_count += 1
                    
        self.lbl_badge_manual.setText(f"{manual_count} ручн.")

    def recalculate_distribution(self):
        self.update_ratio_badge()
        self.update_scheme_badges()
        self.update_distribution_grid()

    def export_distribution_json(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Экспорт схемы распределения", "", "JSON Files (*.json)")
        if file_path:
            mapping = {}
            for acc in self.selected_accounts:
                c_sett = acc.get("commenting_settings", {})
                mapping[acc["name"]] = [line.strip() for line in c_sett.get("channels", "").split("\n") if line.strip()]
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(mapping, f, indent=4, ensure_ascii=False)
                self.append_log(f"Схема распределения экспортирована в {os.path.basename(file_path)}", "success")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось экспортировать схему: {e}")

    def import_distribution_json(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Импорт схемы распределения", "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    mapping = json.load(f)
                
                for acc in self.selected_accounts:
                    if acc["name"] in mapping:
                        c_sett = acc.setdefault("commenting_settings", {})
                        c_sett["channels"] = "\n".join(mapping[acc["name"]])
                
                self.save_commenting_settings_locally()
                self.update_distribution_grid()
                self.append_log(f"Схема распределения импортирована из {os.path.basename(file_path)}", "success")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось импортировать схему: {e}")

    def on_use_ai_prompt_toggled(self, checked):
        self.prompts_gallery_container.setVisible(checked)
        self.prompt_input_container.setVisible(not checked)

    def toggle_sys_prompts_visibility(self):
        visible = self.sys_prompts_scroll.isVisible()
        self.sys_prompts_scroll.setVisible(not visible)
        self.btn_toggle_sys.setText("▼" if visible else "▲")

    def toggle_custom_prompts_visibility(self):
        visible = self.custom_prompts_scroll.isVisible()
        self.custom_prompts_scroll.setVisible(not visible)
        self.btn_toggle_custom.setText("▼" if visible else "▲")

    def update_prompts_grids(self):
        self._clear_layout(self.sys_prompts_layout)
        self._clear_layout(self.custom_prompts_layout)
        self.prompt_cards.clear()
        
        # Render System Prompts
        for idx, (key, val) in enumerate(self.system_prompts.items()):
            card = PromptCard(key, val["title"], val["text"], is_system=True, is_starred=val["starred"])
            card.view_clicked.connect(self.view_prompt)
            card.use_clicked.connect(self.select_prompt)
            self.prompt_cards[val["title"]] = card
            self.sys_prompts_layout.addWidget(card)
            
        self.lbl_sys_count.setText(f"({len(self.system_prompts)})")
            
        # Render Custom Prompts
        for cp in self.custom_prompts:
            card = PromptCard(cp["name"], cp["name"], cp["text"], is_system=False)
            card.view_clicked.connect(self.view_prompt)
            card.use_clicked.connect(self.select_prompt)
            card.edit_clicked.connect(self.edit_prompt)
            card.delete_clicked.connect(self.delete_prompt)
            self.prompt_cards[cp["name"]] = card
            self.custom_prompts_layout.addWidget(card)
            
        # Add "+ Создать" Row
        create_card = CreatePromptRow()
        create_card.clicked.connect(self.create_prompt)
        self.custom_prompts_layout.addWidget(create_card)
        
        self.lbl_custom_count.setText(f"({len(self.custom_prompts)})")
        
        # Highlight active card
        for title, card in self.prompt_cards.items():
            card.set_active(title == self.active_prompt_name)

    def select_prompt(self, key_or_name):
        title = key_or_name
        if key_or_name in self.system_prompts:
            title = self.system_prompts[key_or_name]["title"]
            
        self.active_prompt_name = title
        
        for t, card in self.prompt_cards.items():
            card.set_active(t == title)
            
        active_text = ""
        if key_or_name in self.system_prompts:
            active_text = self.system_prompts[key_or_name]["text"]
        else:
            for cp in self.custom_prompts:
                if cp["name"] == key_or_name:
                    active_text = cp["text"]
                    break
        if active_text:
            self.input_prompt.setPlainText(active_text)
            
        self.append_log(f"Выбран активный промпт: '{title}'", "info")

    def view_prompt(self, key_or_name):
        title = key_or_name
        text = ""
        if key_or_name in self.system_prompts:
            title = self.system_prompts[key_or_name]["title"]
            text = self.system_prompts[key_or_name]["text"]
        else:
            for cp in self.custom_prompts:
                if cp["name"] == key_or_name:
                    text = cp["text"]
                    break
        QMessageBox.information(self, f"Просмотр промпта: {title}", text)

    def create_prompt(self):
        dialog = PromptEditDialog("Создание промпта ИИ", parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name, text = dialog.get_data()
            if not name or not text:
                QMessageBox.warning(self, "Внимание", "Название и текст промпта не могут быть пустыми!")
                return
                
            if name in self.system_prompts or any(cp["name"] == name for cp in self.custom_prompts):
                QMessageBox.warning(self, "Внимание", f"Промпт с названием '{name}' уже существует!")
                return
                
            self.custom_prompts.append({"name": name, "text": text})
            self.update_prompts_grids()
            self.save_commenting_settings_locally()
            self.append_log(f"Создан новый промпт: '{name}'", "success")

    def edit_prompt(self, name):
        prompt_item = None
        for cp in self.custom_prompts:
            if cp["name"] == name:
                prompt_item = cp
                break
        if not prompt_item:
            return
            
        dialog = PromptEditDialog("Редактирование промпта ИИ", name=prompt_item["name"], text=prompt_item["text"], parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_name, new_text = dialog.get_data()
            if not new_name or not new_text:
                QMessageBox.warning(self, "Внимание", "Название и текст промпта не могут быть пустыми!")
                return
                
            if new_name != name and (new_name in self.system_prompts or any(cp["name"] == new_name for cp in self.custom_prompts)):
                QMessageBox.warning(self, "Внимание", f"Промпт с названием '{new_name}' уже существует!")
                return
                
            prompt_item["name"] = new_name
            prompt_item["text"] = new_text
            
            if self.active_prompt_name == name:
                self.active_prompt_name = new_name
                
            self.update_prompts_grids()
            self.save_commenting_settings_locally()
            self.append_log(f"Изменен промпт: '{new_name}'", "success")

    def delete_prompt(self, name):
        reply = QMessageBox.question(
            self, "Подтверждение удаления", 
            f"Вы уверены, что хотите удалить промпт '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.custom_prompts = [cp for cp in self.custom_prompts if cp["name"] != name]
            
            if self.active_prompt_name == name:
                self.active_prompt_name = "Позитивный комментарий"
                
            self.update_prompts_grids()
            self.save_commenting_settings_locally()
            self.append_log(f"Удален промпт: '{name}'", "warning")

    def get_custom_stylesheet(self):
        from src import styles
        return f"""
        QFrame#LeftSectionFrame, QFrame#RightSectionFrame {{
            background-color: {styles.COLOR_ACCENT_BG};
            border: 1px solid {styles.COLOR_BORDER};
            border-radius: 12px;
        }}

        QFrame#ContentSectionFrame {{
            background-color: {styles.COLOR_ACCENT_BG};
            border: 1px solid {styles.COLOR_BORDER};
            border-radius: 10px;
            padding: 10px;
        }}

        QFrame#CategoryCard, QFrame#SelectionCard {{
            background-color: {styles.COLOR_BG};
            border: 1px solid {styles.COLOR_BORDER_LIGHT};
            border-radius: 8px;
            padding: 8px;
        }}

        QFrame#SelectorItemRow {{
            background-color: {styles.COLOR_ACCENT_BG};
            border: 1px solid {styles.COLOR_BORDER};
            border-radius: 6px;
        }}
        
        QFrame#SelectorItemRow:hover {{
            border: 1px solid {styles.COLOR_PRIMARY};
            background-color: {styles.COLOR_HOVER_BG};
        }}

        QLabel#SectionTitle {{
            color: {styles.COLOR_PRIMARY};
            font-weight: bold;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding-bottom: 5px;
            border-bottom: 1px solid {styles.COLOR_BORDER};
        }}

        QLabel#SectionSubTitle {{
            color: {styles.COLOR_PRIMARY};
            font-weight: bold;
            font-size: 13px;
        }}

        QLabel#ModuleWorkTitle {{
            color: {styles.COLOR_PRIMARY};
            font-size: 15px;
            font-weight: bold;
        }}

        QLabel#ConsoleTitle {{
            color: {styles.COLOR_PRIMARY};
            font-weight: bold;
            font-size: 12px;
        }}

        QPushButton#ModuleListBtnActive {{
            background-color: {"rgba(0, 230, 118, 0.1)" if styles.COLOR_PRIMARY == "#00E676" else "rgba(0, 176, 255, 0.1)"};
            color: {styles.COLOR_PRIMARY};
            border: 1px solid {styles.COLOR_PRIMARY};
            border-radius: 8px;
            padding: 12px;
            text-align: left;
            font-weight: bold;
        }}

        QPushButton#ModuleListBtnActive:hover {{
            background-color: {"rgba(0, 230, 118, 0.15)" if styles.COLOR_PRIMARY == "#00E676" else "rgba(0, 176, 255, 0.15)"};
        }}

        QPushButton#ModuleListBtnInactive {{
            background-color: {styles.COLOR_ACCENT_BG};
            color: {styles.COLOR_TEXT_MUTED};
            border: 1px solid {styles.COLOR_BORDER};
            border-radius: 8px;
            padding: 12px;
            text-align: left;
        }}

        QPushButton#ModuleListBtnInactive:hover {{
            border: 1px solid {styles.COLOR_PRIMARY};
            color: {styles.COLOR_PRIMARY};
            background-color: {styles.COLOR_HOVER_BG};
        }}

        QPushButton#ModuleListBtnDisabled {{
            background-color: {styles.COLOR_BG};
            color: {styles.COLOR_TEXT_DISABLED};
            border: 1px solid {styles.COLOR_BORDER_LIGHT};
            border-radius: 8px;
            padding: 12px;
            text-align: left;
        }}

        QPushButton#ApplyBtn {{
            background-color: {styles.COLOR_PRIMARY_DARK};
            color: #000000;
            font-weight: bold;
        }}

        QPushButton#ApplyBtn:hover {{
            background-color: {styles.COLOR_PRIMARY};
            color: #000000;
        }}

        QPushButton#StopBtn {{
            background-color: transparent;
            color: #ff5252;
            border: 1px solid #ff5252;
            font-weight: bold;
        }}

        QPushButton#StopBtn:hover {{
            background-color: rgba(255, 82, 82, 0.1);
        }}

        QPushButton#StopBtn:disabled {{
            border: 1px solid {styles.COLOR_BORDER_LIGHT};
            color: {styles.COLOR_TEXT_DISABLED};
            background-color: transparent;
        }}

        QTextEdit#ConsoleLog {{
            background-color: {styles.COLOR_CONSOLE_BG};
            border: 1px solid {styles.COLOR_BORDER};
            border-radius: 8px;
            font-family: monospace;
            font-size: 11px;
            padding: 8px;
        }}

        QComboBox {{
            background-color: {styles.COLOR_CONSOLE_BG};
            border: 1px solid {styles.COLOR_BORDER};
            border-radius: 6px;
            padding: 4px 8px;
            color: {styles.COLOR_PRIMARY};
        }}
        
        QCheckBox {{
            color: #E0E0E0;
            font-size: 11px;
        }}
        """
