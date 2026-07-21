from src.core.constants import *
import os
import threading
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox, QLineEdit, QScrollArea, QFrame, QFileDialog, QMessageBox, QDialog, QMenu
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QSize, QTimer
import json
from src.ui.icon_cache import get_icon

"""
Страница списка аккаунтов.
Функции:

- init_ui: инициализация основного интерфейса страницы
- run_creation_proxy_check: проверка прокси при добавлении нового аккаунта
- on_creation_proxy_check_finished: обработка результата проверки прокси для формы создания
- refresh_accounts: полная перерисовка списка аккаунтов из конфига
- _load_next_batch: инкрементальная загрузка строк аккаунтов для предотвращения зависаний
- handle_move_request: обработка запроса на изменение позиции аккаунта
- animate_swap: анимация перемещения двух строк в списке
- toggle_select_all: массовое выделение или снятие выделения с аккаунтов
- bulk_launch: массовый запуск выбранных профилей
- bulk_stop: массовая остановка выбранных профилей
- bulk_check_proxy: массовая проверка прокси выбранных профилей
- bulk_clear_cache: массовая очистка кэша выбранных профилей
- browse_directory: выбор папки через стандартный диалог ОС
- add_profile: создание и сохранение нового профиля
- filter_accounts: фильтрация списка по поисковому запросу
- toggle_all_proxies: переключение видимости всех прокси в списке
- open_create_profile_dialog: открытие диалога создания профиля
"""

from src.core.managers import proxy_manager, farm_manager, config_manager, hw_manager, process_manager, account_manager
from src import styles
from src.core.logger import logger
from src.ui.account_row import TelegramAccountRow
from src.core.constants import (
    CONFIG_FILE, ICON_PATH, LOGO_PATH, SUCCESS_ICON_PATH, 
    CANCEL_ICON_PATH, PROXY_ICON_PATH, SETTINGS_ICON_PATH, 
    CASH_ICON_PATH, VIEV_ICON_PATH, MODULS_ICON_PATH, 
    FOLDER_ICON_PATH, NEW_PROXY_ICON_PATH, SERVER_ICON_PATH,
    NOTE_ICON_PATH
)

class CreateProfileDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Создать новый профиль")
        self.setFixedSize(500, 450)
        self.setStyleSheet(parent.styleSheet() if parent else "")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        layout.addWidget(QLabel("Добавить новый профиль", styleSheet=f"font-weight: bold; color: {styles.COLOR_PRIMARY}; font-size: 16px;"))
        
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("Имя профиля")
        self.input_name.textChanged.connect(self.auto_fill_path)
        layout.addWidget(self.input_name)
        
        path_l = QHBoxLayout()
        self.input_path = QLineEdit()
        self.input_path.setPlaceholderText("Путь к папке (workdir)")
        path_l.addWidget(self.input_path)
        
        btn_br = QPushButton()
        btn_br.setFixedWidth(40)
        btn_br.setIcon(get_icon(FOLDER_ICON_PATH))
        btn_br.setIconSize(QSize(20, 20))
        btn_br.clicked.connect(self.browse_directory)
        path_l.addWidget(btn_br)
        layout.addLayout(path_l)
        
        proxy_l = QHBoxLayout()
        self.input_proxy = QLineEdit()
        self.input_proxy.setPlaceholderText("HTTP Proxy (http://user:pass@host:port)")
        proxy_l.addWidget(self.input_proxy)
        
        self.btn_check_creation_proxy = QPushButton()
        self.btn_check_creation_proxy.setIcon(get_icon(NEW_PROXY_ICON_PATH))
        self.btn_check_creation_proxy.setIconSize(QSize(22, 22))
        self.btn_check_creation_proxy.setObjectName("CheckBtn")
        self.btn_check_creation_proxy.setFixedWidth(40)
        self.btn_check_creation_proxy.clicked.connect(self.run_creation_proxy_check)
        proxy_l.addWidget(self.btn_check_creation_proxy)
        layout.addLayout(proxy_l)
        
        api_l = QHBoxLayout()
        self.input_api_id = QLineEdit()
        self.input_api_id.setPlaceholderText("API ID (опционально)")
        api_l.addWidget(self.input_api_id)
        
        self.input_api_hash = QLineEdit()
        self.input_api_hash.setPlaceholderText("API Hash (опционально)")
        api_l.addWidget(self.input_api_hash)
        layout.addLayout(api_l)

        btn_add = QPushButton("Создать")
        btn_add.setObjectName("LaunchBtn")
        btn_add.setFixedHeight(40)
        btn_add.clicked.connect(self.add_profile)
        layout.addWidget(btn_add)
        
        self.tyanka_label = QLabel()
        pix = QPixmap(str(ICON_PATH))
        if not pix.isNull(): 
            self.tyanka_label.setPixmap(pix.scaled(150, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(self.tyanka_label, alignment=Qt.AlignmentFlag.AlignCenter)

    def auto_fill_path(self, text):
        if not text:
            self.input_path.clear()
            return
        farm_dir = farm_manager.get_active_farm_dir()
        suggested_path = farm_dir / "accounts" / text
        self.input_path.setText(str(suggested_path))

    def browse_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Выберите папку для профиля")
        if dir_path: self.input_path.setText(dir_path)

    def run_creation_proxy_check(self):
        p_url = self.input_proxy.text().strip()
        if not p_url: return
        self.btn_check_creation_proxy.setProperty("status", "checking")
        self.btn_check_creation_proxy.style().unpolish(self.btn_check_creation_proxy)
        self.btn_check_creation_proxy.style().polish(self.btn_check_creation_proxy)
        self.btn_check_creation_proxy.setEnabled(False)
        threading.Thread(target=lambda: self.parent().creation_proxy_check_finished.emit(proxy_manager.check_proxy_validity(p_url)), daemon=True).start()

    def set_proxy_status(self, is_valid):
        self.btn_check_creation_proxy.setEnabled(True)
        self.btn_check_creation_proxy.setProperty("status", "success" if is_valid else "error")
        self.btn_check_creation_proxy.style().unpolish(self.btn_check_creation_proxy)
        self.btn_check_creation_proxy.style().polish(self.btn_check_creation_proxy)
        if is_valid: QMessageBox.information(self, "Прокси", "Прокси рабочий!")
        else: QMessageBox.critical(self, "Прокси", "Прокси не работает!")

    def add_profile(self):
        name = self.input_name.text().strip()
        path = self.input_path.text().strip()
        proxy = self.input_proxy.text().strip() or None
        api_id = self.input_api_id.text().strip() or None
        api_hash = self.input_api_hash.text().strip() or None
        
        if not name or not path:
            QMessageBox.warning(self, "Ошибка", "Заполните имя и путь!")
            return
        if account_manager.add_account(CONFIG_FILE, name, path, proxy, api_id=api_id, api_hash=api_hash):
            if hasattr(self.parent(), "refresh_accounts"):
                self.parent().refresh_accounts()
            self.input_name.clear()
            self.input_path.clear()
            self.input_proxy.clear()
            self.input_api_id.clear()
            self.input_api_hash.clear()
            self.btn_check_creation_proxy.setProperty("status", "default")
            self.btn_check_creation_proxy.style().unpolish(self.btn_check_creation_proxy)
            self.btn_check_creation_proxy.style().polish(self.btn_check_creation_proxy)
            self.accept()


class AccountListPage(QWidget):
    settings_requested = pyqtSignal()
    modules_requested = pyqtSignal()
    server_requested = pyqtSignal()
    docs_requested = pyqtSignal()
    creation_proxy_check_finished = pyqtSignal(bool)

    def __init__(self, parent):
        super().__init__()
        self.setObjectName("PageRoot")
        self.mgr = parent
        self.rows = []
        self.proxies_hidden = True
        self.is_animating = False
        self._accounts_to_load = []
        self._load_timer = None
        self.create_dialog = None
        self.is_compact_mode = False
        self.init_ui()
        self.creation_proxy_check_finished.connect(self.on_creation_proxy_check_finished)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        hero = QFrame()
        hero.setObjectName("PageHero")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(18, 18, 18, 18)
        hero_layout.setSpacing(16)

        hero_copy = QVBoxLayout()
        hero_copy.setSpacing(4)

        hero_eyebrow = QLabel("CONTROL CENTER")
        hero_eyebrow.setObjectName("PageEyebrow")
        hero_copy.addWidget(hero_eyebrow)

        hero_title = QLabel("Управление аккаунтами")
        hero_title.setObjectName("PageTitle")
        hero_copy.addWidget(hero_title)

        hero_subtitle = QLabel("Основной список профилей с быстрыми действиями, поиском, проверками и пакетным управлением.")
        hero_subtitle.setObjectName("PageSubtitle")
        hero_subtitle.setWordWrap(True)
        hero_copy.addWidget(hero_subtitle)

        hero_layout.addLayout(hero_copy, 1)

        hero_actions = QHBoxLayout()
        hero_actions.setSpacing(10)

        btn_create = QPushButton("Создать профиль")
        btn_create.setObjectName("PillBtn")
        btn_create.setIcon(get_icon(FOLDER_ICON_PATH))
        btn_create.setIconSize(QSize(18, 18))
        btn_create.clicked.connect(self.open_create_profile_dialog)
        hero_actions.addWidget(btn_create)

        btn_services = QPushButton("Сервисы")
        btn_services.setObjectName("GhostBtn")
        btn_services.setIcon(get_icon(MODULS_ICON_PATH))
        btn_services.setIconSize(QSize(18, 18))
        btn_services.clicked.connect(self.mgr.show_services)
        hero_actions.addWidget(btn_services)

        btn_docs = QPushButton("Документация")
        btn_docs.setObjectName("GhostBtn")
        btn_docs.setIcon(get_icon(NOTE_ICON_PATH))
        btn_docs.setIconSize(QSize(18, 18))
        btn_docs.clicked.connect(self.mgr.show_docs)
        hero_actions.addWidget(btn_docs)

        hero_layout.addLayout(hero_actions)
        layout.addWidget(hero)

        toolbar_card = QFrame()
        toolbar_card.setObjectName("ToolbarCard")
        toolbar_layout = QVBoxLayout(toolbar_card)
        toolbar_layout.setContentsMargins(14, 12, 14, 12)
        toolbar_layout.setSpacing(10)

        toolbar_top = QHBoxLayout()
        toolbar_top.setSpacing(8)
        self.select_all_cb = QCheckBox("Выбрать все")
        self.select_all_cb.stateChanged.connect(self.toggle_select_all)
        toolbar_top.addWidget(self.select_all_cb)
        toolbar_top.addStretch()

        self.bulk_buttons = []
        for text, slot, icon_path in [
            ("Запустить", self.bulk_launch, SUCCESS_ICON_PATH),
            ("Остановить", self.bulk_stop, CANCEL_ICON_PATH),
            ("Проверить", self.bulk_check_proxy, PROXY_ICON_PATH),
            ("Кэш", self.bulk_clear_cache, CASH_ICON_PATH),
        ]:
            btn = self._create_toolbar_button(text, icon_path, slot)
            self.bulk_buttons.append(btn)
            toolbar_top.addWidget(btn)

        self.btn_toggle_proxies = QPushButton("Прокси")
        self.btn_toggle_proxies.setObjectName("GhostBtn")
        self.btn_toggle_proxies.setIcon(get_icon(VIEV_ICON_PATH))
        self.btn_toggle_proxies.setIconSize(QSize(18, 18))
        self.btn_toggle_proxies.setToolTip("Показать или скрыть адреса прокси")
        self.btn_toggle_proxies.clicked.connect(self.toggle_all_proxies)
        toolbar_top.addWidget(self.btn_toggle_proxies)
        toolbar_layout.addLayout(toolbar_top)

        toolbar_bottom = QHBoxLayout()
        toolbar_bottom.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по имени, пути, прокси, устройству или заметкам...")
        self.search_input.textChanged.connect(self.filter_accounts)
        toolbar_bottom.addWidget(self.search_input, 1)

        btn_refresh = QPushButton("Обновить список")
        btn_refresh.setObjectName("GhostBtn")
        btn_refresh.clicked.connect(self.refresh_accounts)
        toolbar_bottom.addWidget(btn_refresh)

        toolbar_layout.addLayout(toolbar_bottom)
        layout.addWidget(toolbar_card)

        content_card = QFrame()
        content_card.setObjectName("PageCard")
        content_layout = QVBoxLayout(content_card)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("ScrollContent")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(2, 2, 2, 2)
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.scroll_content)
        self.scroll.verticalScrollBar().setSingleStep(25)
        content_layout.addWidget(self.scroll)

        self.empty_state = QFrame()
        self.empty_state.setObjectName("EmptyStateCard")
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setContentsMargins(24, 22, 24, 22)
        empty_layout.setSpacing(8)

        self.empty_text = QLabel("Создайте первый профиль или измените поисковый запрос, если список уже заполнен.")
        self.empty_text.setObjectName("EmptyStateText")
        self.empty_text.setWordWrap(True)
        self.empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_text)

        self.empty_btn = QPushButton("Создать профиль")
        self.empty_btn.setObjectName("PillBtn")
        self.empty_btn.clicked.connect(self.open_create_profile_dialog)
        empty_layout.addWidget(self.empty_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.scroll_layout.addWidget(self.empty_state)
        self.scroll_layout.addStretch()
        layout.addWidget(content_card, 1)

    def _create_toolbar_button(self, text, icon_path, slot):
        btn = QPushButton(text)
        btn.setObjectName("GhostBtn")
        btn.setIcon(get_icon(icon_path))
        btn.setIconSize(QSize(18, 18))
        btn.clicked.connect(slot)
        return btn

    def open_create_profile_dialog(self):
        if not self.create_dialog:
            self.create_dialog = CreateProfileDialog(self)
        self.create_dialog.show()
        self.create_dialog.raise_()
        self.create_dialog.activateWindow()

    def open_device_generator(self):
        from src.services.device_generator import DeviceNameGeneratorService
        service = DeviceNameGeneratorService(self)
        service.exec()

    def open_prompt_generator(self):
        from src.services.ai_prompt_generator import AIPromptGeneratorService
        service = AIPromptGeneratorService(self)
        service.exec()

    def on_creation_proxy_check_finished(self, is_valid):
        if self.create_dialog:
            self.create_dialog.set_proxy_status(is_valid)

    def refresh_accounts(self):
        if self._load_timer:
            self._load_timer.stop()
            
        for r in self.rows:
            self.scroll_layout.removeWidget(r)
            r.deleteLater()
        self.rows = []
        self.update_summary()
        self.update_empty_state()

        try:
            data = config_manager._read_config(CONFIG_FILE)
            self.is_compact_mode = data.get("settings", {}).get("compact_mode", False)
        except Exception:
            self.is_compact_mode = False
        
        self._accounts_to_load = config_manager.load_config(CONFIG_FILE)
        if self._accounts_to_load:
            self._load_timer = QTimer(self)
            self._load_timer.timeout.connect(self._load_next_batch)
            self._load_timer.start(10)
        else:
            self.update_empty_state()

    def _load_next_batch(self):
        batch_size = 5
        
        for _ in range(batch_size):
            if not self._accounts_to_load:
                self._load_timer.stop()
                return
                
            acc = self._accounts_to_load.pop(0)
            row = TelegramAccountRow(
                acc["name"], 
                acc["workdir"], 
                acc.get("proxy_url"), 
                acc.get("notes"),
                acc.get("device_name"),
                acc.get("ai_prompt")
            )
            row.apply_compact_mode(self.is_compact_mode)
            row.set_proxy_hidden(self.proxies_hidden)
            row.account_removed.connect(self.refresh_accounts)
            row.profile_data_changed.connect(self.on_profile_data_changed)
            row.move_requested.connect(self.handle_move_request)
            row.running_state_changed.connect(lambda _state: self.update_summary())
            row.checkbox.stateChanged.connect(lambda _state: self.update_summary())
            self.rows.append(row)
            self.scroll_layout.insertWidget(max(0, self.scroll_layout.count() - 1), row)
            
            query = self.search_input.text().lower().strip()
            if query:
                row.setVisible(self._match_row_query(row, query))
        self.update_summary()
        self.update_empty_state()

    def _match_row_query(self, row, query):
        haystacks = [
            row.name,
            row.workdir,
            row.proxy_url or "",
            row.device_name or "",
            row.notes or "",
            row.ai_prompt or "",
        ]
        query = query.lower().strip()
        return any(query in value.lower() for value in haystacks if value)

    def on_profile_data_changed(self):
        if hasattr(self.mgr, 'table_page'):
            self.mgr.table_page.refresh_data()
        self.filter_accounts(self.search_input.text())
        self.update_summary()
        self.update_empty_state()

    def handle_move_request(self, row_widget, direction):
        if self.is_animating: return
        
        try:
            data = config_manager._read_config(CONFIG_FILE)
            accounts = data.get("accounts", [])
            
            idx = -1
            for i, a in enumerate(accounts):
                if a["name"] == row_widget.name and a["workdir"] == row_widget.workdir:
                    idx = i
                    break
                    
            if idx == -1: return
            new_idx = idx + direction
            
            if 0 <= new_idx < len(accounts):
                accounts[idx], accounts[new_idx] = accounts[new_idx], accounts[idx]
                data["accounts"] = accounts
                config_manager._write_config(CONFIG_FILE, data)
                self.animate_swap(idx, new_idx)
                
        except Exception as e:
            logger.error(f"Ошибка перемещения: {e}")

    def animate_swap(self, idx1, idx2):
        self.is_animating = True
        row1 = self.rows[idx1]
        row2 = self.rows[idx2]
        
        pos1 = row1.pos()
        pos2 = row2.pos()
        
        anim1 = QPropertyAnimation(row1, b"pos")
        anim1.setDuration(300)
        anim1.setStartValue(pos1)
        anim1.setEndValue(pos2)
        anim1.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        anim2 = QPropertyAnimation(row2, b"pos")
        anim2.setDuration(300)
        anim2.setStartValue(pos2)
        anim2.setEndValue(pos1)
        anim2.setEasingCurve(QEasingCurve.Type.InOutQuad)
        
        self.anim_group = QParallelAnimationGroup()
        self.anim_group.addAnimation(anim1)
        self.anim_group.addAnimation(anim2)
        
        def on_finished():
            self.scroll_layout.removeWidget(row1)
            self.scroll_layout.removeWidget(row2)
            
            min_idx = min(idx1, idx2)
            max_idx = max(idx1, idx2)
            
            self.rows[idx1], self.rows[idx2] = self.rows[idx2], self.rows[idx1]
            
            self.scroll_layout.insertWidget(min_idx, self.rows[min_idx])
            self.scroll_layout.insertWidget(max_idx, self.rows[max_idx])
            self.is_animating = False
            
        self.anim_group.finished.connect(on_finished)
        self.anim_group.start()

    def filter_accounts(self, text):
        t = text.lower().strip()
        for r in self.rows:
            r.setVisible(self._match_row_query(r, t) if t else True)
        self.update_empty_state()
        self.update_summary()

    def toggle_all_proxies(self):
        self.proxies_hidden = not self.proxies_hidden
        for r in self.rows: r.set_proxy_hidden(self.proxies_hidden)

    def toggle_select_all(self, state):
        st = state == Qt.CheckState.Checked.value
        for r in self.rows: r.checkbox.setChecked(st)
        self.update_summary()

    def bulk_launch(self):
        try:
            with open(CONFIG_FILE, "r") as f: config = json.load(f)
            delay = config.get("settings", {}).get("launch_delay", 2)
        except:
            delay = 2

        self._launch_queue = [r for r in self.rows if r.checkbox.isChecked() and not process_manager.is_process_running(r.tg_process)]
        self._launch_delay = delay * 1000
        self._process_launch_queue()

    def _process_launch_queue(self):
        if not self._launch_queue: return
        row = self._launch_queue.pop(0)
        row.toggle_telegram()
        if self._launch_queue:
            QTimer.singleShot(self._launch_delay, self._process_launch_queue)

    def bulk_stop(self):
        for r in self.rows:
            if r.checkbox.isChecked() and process_manager.is_process_running(r.tg_process): r.toggle_telegram()
        self.update_summary()

    def bulk_check_proxy(self):
        for r in self.rows:
            if r.checkbox.isChecked() and r.proxy_url: r.run_proxy_check()

    def bulk_clear_cache(self):
        cleared = 0
        for r in self.rows:
            if r.checkbox.isChecked() and not process_manager.is_process_running(r.tg_process):
                process_manager.clear_cache(r.workdir)
                cleared += 1
        QMessageBox.information(self, "Очистка кэша", f"Очищен кэш у {cleared} аккаунтов.")

    def update_summary(self):
        return

    def update_empty_state(self):
        if not self.rows:
            self.empty_state.show()
            self.empty_text.setText("Создайте первый профиль, чтобы начать работу с фермой.")
            self.empty_btn.show()
            return

        self.empty_state.hide()
