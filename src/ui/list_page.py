import os
import threading
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox, QLineEdit, QScrollArea, QFrame, QFileDialog, QMessageBox
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QSize
import json

"""
Страница списка аккаунтов.
Функции:

- init_ui: инициализация основного интерфейса страницы
- run_creation_proxy_check: проверка прокси при добавлении нового аккаунта
- on_creation_proxy_check_finished: обработка результата проверки прокси для формы создания
- refresh_accounts: полная перерисовка списка аккаунтов из конфига
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
"""

from src.core import logic
from src.ui.account_row import TelegramAccountRow
from src.core.constants import (
    CONFIG_FILE, ICON_PATH, LOGO_PATH, SUCCESS_ICON_PATH, 
    CANCEL_ICON_PATH, PROXY_ICON_PATH, SETTINGS_ICON_PATH, 
    CASH_ICON_PATH, VIEV_ICON_PATH, MODULS_ICON_PATH, 
    FOLDER_ICON_PATH, NEW_PROXY_ICON_PATH, SERVER_ICON_PATH
)

class AccountListPage(QWidget):
    settings_requested = pyqtSignal()
    modules_requested = pyqtSignal()
    server_requested = pyqtSignal()
    creation_proxy_check_finished = pyqtSignal(bool)

    def __init__(self, parent):
        super().__init__()
        self.mgr = parent
        self.rows = []
        self.proxies_hidden = True
        self.is_animating = False
        self.init_ui()
        self.creation_proxy_check_finished.connect(self.on_creation_proxy_check_finished)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title_layout = QHBoxLayout()
        title_layout.setSpacing(10)
        
        logo_label = QLabel()
        logo_pix = QPixmap(str(LOGO_PATH))
        if not logo_pix.isNull():
            logo_label.setPixmap(logo_pix.scaled(90, 90, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        logo_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        title_layout.addWidget(logo_label)

        title_label = QLabel("Shadowgram")
        title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        title_label.setObjectName("Title")
        title_label.setContentsMargins(0, 0, 0, 10) # 10px отступа снизу поднимут текст выше
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        self.btn_server = QPushButton(" Сервер")
        # Reuse MODULS_ICON_PATH or another icon for server
        self.btn_server.setIcon(QIcon(str(SERVER_ICON_PATH)))
        self.btn_server.setIconSize(QSize(20, 20))
        self.btn_server.setFixedWidth(120)
        self.btn_server.setToolTip("Управление ServerGram")
        self.btn_server.clicked.connect(self.server_requested.emit)
        title_layout.addWidget(self.btn_server)

        self.btn_modules = QPushButton(" Модули")
        self.btn_modules.setIcon(QIcon(str(MODULS_ICON_PATH)))
        self.btn_modules.setIconSize(QSize(20, 20))
        self.btn_modules.setFixedWidth(120)
        self.btn_modules.setToolTip("Запуск модулей автоматизации")
        self.btn_modules.clicked.connect(self.modules_requested.emit)
        title_layout.addWidget(self.btn_modules)

        self.btn_settings = QPushButton()
        self.btn_settings.setIcon(QIcon(str(SETTINGS_ICON_PATH)))
        self.btn_settings.setIconSize(QSize(24, 24))
        self.btn_settings.setFixedWidth(45)
        self.btn_settings.clicked.connect(self.settings_requested.emit)
        title_layout.addWidget(self.btn_settings)
        layout.addLayout(title_layout)

        toolbar = QHBoxLayout()
        self.select_all_cb = QCheckBox("Выбрать все")
        self.select_all_cb.stateChanged.connect(self.toggle_select_all)
        toolbar.addWidget(self.select_all_cb)
        toolbar.addStretch()

        for btn_text, slot in [(" Запустить", self.bulk_launch), (" Остановить", self.bulk_stop), (" Проверить", self.bulk_check_proxy), (" Кэш", self.bulk_clear_cache)]:
            btn = QPushButton(btn_text)
            if btn_text == " Запустить":
                btn.setIcon(QIcon(str(SUCCESS_ICON_PATH)))
                btn.setIconSize(QSize(20, 20))
            elif btn_text == " Остановить":
                btn.setIcon(QIcon(str(CANCEL_ICON_PATH)))
                btn.setIconSize(QSize(20, 20))
            elif btn_text == " Проверить":
                btn.setIcon(QIcon(str(PROXY_ICON_PATH)))
                btn.setIconSize(QSize(20, 20))
            elif btn_text == " Кэш":
                btn.setIcon(QIcon(str(CASH_ICON_PATH)))
                btn.setIconSize(QSize(22, 22))
            btn.clicked.connect(slot)
            toolbar.addWidget(btn)
            
        self.btn_toggle_proxies = QPushButton()
        self.btn_toggle_proxies.setIcon(QIcon(str(VIEV_ICON_PATH)))
        self.btn_toggle_proxies.setIconSize(QSize(24, 24))
        self.btn_toggle_proxies.setFixedWidth(45)
        self.btn_toggle_proxies.setToolTip("Показать/Скрыть все прокси")
        self.btn_toggle_proxies.clicked.connect(self.toggle_all_proxies)
        toolbar.addWidget(self.btn_toggle_proxies)
        layout.addLayout(toolbar)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(" Поиск по имени или заметкам...")
        layout.addWidget(self.search_input)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("ScrollContent")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(10)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self.scroll_content)
        self.scroll.verticalScrollBar().setSingleStep(25)  # Делаем скролл мышью более плавным и быстрым
        layout.addWidget(self.scroll)

        btn_ref = QPushButton("Обновить список")
        btn_ref.setFixedHeight(40)
        btn_ref.clicked.connect(self.refresh_accounts)
        layout.addWidget(btn_ref)

        self.create_frame = QFrame(); self.create_frame.setObjectName("CreateSection")
        create_layout = QHBoxLayout(self.create_frame)
        inputs = QVBoxLayout()
        inputs.addWidget(QLabel("Добавить новый профиль", styleSheet="font-weight: bold; color: #4caf50;"))
        self.input_name = QLineEdit(); self.input_name.setPlaceholderText("Имя профиля"); inputs.addWidget(self.input_name)
        
        path_l = QHBoxLayout()
        self.input_path = QLineEdit(); self.input_path.setPlaceholderText("Путь к папке (workdir)"); path_l.addWidget(self.input_path)
        btn_br = QPushButton(); btn_br.setFixedWidth(40)
        btn_br.setIcon(QIcon(str(FOLDER_ICON_PATH)))
        btn_br.setIconSize(QSize(20, 20))
        btn_br.clicked.connect(self.browse_directory); path_l.addWidget(btn_br)
        inputs.addLayout(path_l)
        
        proxy_l = QHBoxLayout()
        self.input_proxy = QLineEdit(); self.input_proxy.setPlaceholderText("HTTP Proxy (http://user:pass@host:port)"); proxy_l.addWidget(self.input_proxy)
        self.btn_check_creation_proxy = QPushButton()
        self.btn_check_creation_proxy.setIcon(QIcon(str(NEW_PROXY_ICON_PATH)))
        self.btn_check_creation_proxy.setIconSize(QSize(22, 22))
        self.btn_check_creation_proxy.setObjectName("CheckBtn")
        self.btn_check_creation_proxy.setFixedWidth(40)
        self.btn_check_creation_proxy.clicked.connect(self.run_creation_proxy_check)
        proxy_l.addWidget(self.btn_check_creation_proxy)
        inputs.addLayout(proxy_l)

        btn_add = QPushButton("Создать"); btn_add.setFixedHeight(35); btn_add.clicked.connect(self.add_profile); inputs.addWidget(btn_add)
        create_layout.addLayout(inputs)

        self.tyanka_label = QLabel()
        self.tyanka_label.installEventFilter(self.mgr)
        pix = QPixmap(str(ICON_PATH))
        if not pix.isNull(): self.tyanka_label.setPixmap(pix.scaled(180, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        create_layout.addWidget(self.tyanka_label, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.create_frame)

    def run_creation_proxy_check(self):
        p_url = self.input_proxy.text().strip()
        if not p_url: return
        self.btn_check_creation_proxy.setProperty("status", "checking")
        self.mgr.refresh_btn_style(self.btn_check_creation_proxy)
        self.btn_check_creation_proxy.setEnabled(False)
        threading.Thread(target=lambda: self.creation_proxy_check_finished.emit(logic.check_proxy_validity(p_url)), daemon=True).start()

    def on_creation_proxy_check_finished(self, is_valid):
        self.btn_check_creation_proxy.setEnabled(True)
        self.btn_check_creation_proxy.setProperty("status", "success" if is_valid else "error")
        self.mgr.refresh_btn_style(self.btn_check_creation_proxy)
        if is_valid: QMessageBox.information(self, "Прокси", "Прокси рабочий!")
        else: QMessageBox.critical(self, "Прокси", "Прокси не работает!")

    def refresh_accounts(self):
        for r in self.rows: self.scroll_layout.removeWidget(r); r.deleteLater()
        self.rows = []
        for acc in logic.load_config(CONFIG_FILE):
            row = TelegramAccountRow(acc["name"], acc["workdir"], acc.get("proxy_url"), acc.get("notes"), acc.get("device_name"))
            row.account_removed.connect(self.refresh_accounts)
            row.move_requested.connect(self.handle_move_request)
            row.set_proxy_hidden(self.proxies_hidden)
            self.scroll_layout.addWidget(row); self.rows.append(row)

    def handle_move_request(self, row_widget, direction):
        if self.is_animating: return
        idx = self.rows.index(row_widget)
        new_idx = idx + direction
        if 0 <= new_idx < len(self.rows):
            self.animate_swap(row_widget, self.rows[new_idx], idx, new_idx)

    def animate_swap(self, w1, w2, idx1, idx2):
        self.is_animating = True
        pos1, pos2 = w1.pos(), w2.pos()
        self.anim1 = QPropertyAnimation(w1, b"pos"); self.anim1.setDuration(300); self.anim1.setStartValue(pos1); self.anim1.setEndValue(pos2); self.anim1.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.anim2 = QPropertyAnimation(w2, b"pos"); self.anim2.setDuration(300); self.anim2.setStartValue(pos2); self.anim2.setEndValue(pos1); self.anim2.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.anim_group = QParallelAnimationGroup()
        self.anim_group.addAnimation(self.anim1); self.anim_group.addAnimation(self.anim2)
        def finish():
            logic.move_account_in_list(CONFIG_FILE, w1.workdir, idx2 - idx1)
            self.is_animating = False; self.refresh_accounts()
        self.anim_group.finished.connect(finish); self.anim_group.start()

    def toggle_select_all(self, state):
        for r in self.rows: r.checkbox.setChecked(state == Qt.CheckState.Checked.value)

    def bulk_launch(self):
        for r in self.rows:
            if r.checkbox.isChecked() and not logic.is_process_running(r.tg_process): r.toggle_telegram()

    def bulk_stop(self):
        for r in self.rows:
            if r.checkbox.isChecked() and logic.is_process_running(r.tg_process): r.toggle_telegram()

    def bulk_check_proxy(self):
        for r in self.rows:
            if r.checkbox.isChecked() and r.proxy_url: r.run_proxy_check()

    def bulk_clear_cache(self):
        sel = [r for r in self.rows if r.checkbox.isChecked()]
        if not sel: return
        if QMessageBox.question(self, "Кэш", f"Очистить кэш {len(sel)} аккаунтов?") == QMessageBox.StandardButton.Yes:
            for r in sel: logic.clear_cache(r.workdir)
            QMessageBox.information(self, "Результат", "Кэш очищен.")

    def browse_directory(self):
        path = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if path: self.input_path.setText(path)

    def add_profile(self):
        n, p, pr = self.input_name.text().strip(), self.input_path.text().strip(), self.input_proxy.text().strip()
        if n and p and logic.add_account(CONFIG_FILE, n, p, pr if pr else None):
            self.input_name.clear(); self.input_path.clear(); self.input_proxy.clear(); self.refresh_accounts()

    def filter_accounts(self, text):
        query = text.lower().strip()
        for row in self.rows:
            row.setVisible(query in row.name.lower() or query in (row.notes.lower() if row.notes else ""))

    def toggle_all_proxies(self):
        self.proxies_hidden = not self.proxies_hidden
        for row in self.rows: row.set_proxy_hidden(self.proxies_hidden)