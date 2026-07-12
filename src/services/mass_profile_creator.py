import os
import random
import string
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QSpinBox, QTextEdit, QCheckBox, QFileDialog, QMessageBox, QFrame, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt
from src.core.managers import proxy_manager, farm_manager, config_manager, hw_manager, process_manager, account_manager
from src.core.constants import CONFIG_FILE
from src import styles

class MassProfileCreatorService(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Массовое создание профилей")
        self.setStyleSheet(f"background-color: {styles.COLOR_BG}; color: {styles.COLOR_TEXT_MAIN};")
        self.init_ui()

    def create_card(self, title):
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background-color: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 10px; }}")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(15, 15, 15, 15)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {styles.COLOR_PRIMARY}; border: none;")
        card_layout.addWidget(lbl_title)
        return card, card_layout

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(container)
        layout.setSpacing(15)

        info_label = QLabel("Создайте множество профилей за пару кликов. Программа автоматически сгенерирует для них имена, раскидает прокси и создаст уникальные названия устройств.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 14px;")
        layout.addWidget(info_label)

        # 1. Шаблон имени
        card_name, name_layout = self.create_card("📝 Шаблон имени")
        from PyQt6.QtWidgets import QFormLayout
        form_name = QFormLayout()
        form_name.setSpacing(15)
        form_name.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        self.input_prefix = QLineEdit("acc")
        self.input_prefix.setStyleSheet(f"background-color: {styles.COLOR_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 6px; padding: 5px;")
        form_name.addRow(QLabel("Префикс:"), self.input_prefix)

        self.spin_start = QSpinBox()
        self.spin_start.setStyleSheet(f"background-color: {styles.COLOR_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 6px; padding: 5px;")
        self.spin_start.setRange(1, 9999)
        self.spin_start.setValue(1)
        form_name.addRow(QLabel("Старт:"), self.spin_start)

        self.spin_end = QSpinBox()
        self.spin_end.setStyleSheet(f"background-color: {styles.COLOR_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 6px; padding: 5px;")
        self.spin_end.setRange(1, 9999)
        self.spin_end.setValue(10)
        form_name.addRow(QLabel("Конец:"), self.spin_end)

        self.spin_padding = QSpinBox()
        self.spin_padding.setStyleSheet(f"background-color: {styles.COLOR_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 6px; padding: 5px;")
        self.spin_padding.setRange(1, 10)
        self.spin_padding.setValue(1)
        form_name.addRow(QLabel("Длина (нулей):"), self.spin_padding)
        
        name_layout.addLayout(form_name)
        layout.addWidget(card_name)

        # 2. Директория
        card_dir, dir_layout = self.create_card("📁 Директория (workdir)")
        dir_hbox = QHBoxLayout()
        self.input_path = QLineEdit()
        self.input_path.setStyleSheet(f"background-color: {styles.COLOR_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 6px; padding: 5px;")
        farm_dir = farm_manager.get_active_farm_dir()
        self.input_path.setText(str(farm_dir / "accounts"))
        dir_hbox.addWidget(self.input_path)
        
        btn_browse = QPushButton("Обзор")
        btn_browse.setStyleSheet(f"background-color: {styles.COLOR_HOVER_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 6px; padding: 5px 15px;")
        btn_browse.clicked.connect(self.browse_directory)
        dir_hbox.addWidget(btn_browse)
        dir_layout.addLayout(dir_hbox)
        layout.addWidget(card_dir)

        # 3. Настройки прокси и железа
        card_adv, adv_layout = self.create_card("⚙ Дополнительно")
        adv_layout.setContentsMargins(10, 10, 10, 10)
        adv_layout.setSpacing(5)
        
        # 2FA Password
        from PyQt6.QtWidgets import QFormLayout
        form_2fa = QFormLayout()
        form_2fa.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.input_2fa = QLineEdit()
        self.input_2fa.setPlaceholderText("Общий облачный пароль (оставьте пустым если нет)")
        self.input_2fa.setStyleSheet(f"background-color: {styles.COLOR_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 6px; padding: 5px;")
        form_2fa.addRow(QLabel("2FA пароль:"), self.input_2fa)
        adv_layout.addLayout(form_2fa)
        
        opt_hbox = QHBoxLayout()
        self.check_random_devices = QCheckBox("Генерация отпечатков устройства")
        self.check_random_devices.setChecked(True)
        self.check_random_devices.setStyleSheet("border: none; background: transparent;")
        opt_hbox.addWidget(self.check_random_devices)
        
        self.btn_load_proxies = QPushButton("Загрузить из Proxy Pool")
        self.btn_load_proxies.setStyleSheet(f"background-color: {styles.COLOR_HOVER_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 6px; padding: 4px 10px;")
        self.btn_load_proxies.clicked.connect(self.load_proxy_pool)
        opt_hbox.addWidget(self.btn_load_proxies)
        
        adv_layout.addLayout(opt_hbox)

        proxy_lbl = QLabel("Список прокси (по одному на строку):")
        proxy_lbl.setStyleSheet("border: none;")
        adv_layout.addWidget(proxy_lbl)
        
        self.input_proxies = QTextEdit()
        self.input_proxies.setStyleSheet(f"""
            QTextEdit {{
                background-color: {styles.COLOR_BG}; 
                border: 1px solid {styles.COLOR_BORDER}; 
                border-radius: 6px; 
                padding: 5px;
                font-family: monospace;
            }}
        """)
        self.input_proxies.setPlaceholderText("http://user:pass@host:port\nsocks5://user:pass@host:port")
        self.input_proxies.setFixedHeight(70)
        adv_layout.addWidget(self.input_proxies)
        
        layout.addWidget(card_adv)

        # Кнопка создания
        self.btn_create = QPushButton("✨ Создать профили")
        self.btn_create.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.COLOR_PRIMARY};
                color: #000000;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: {styles.COLOR_PRIMARY_LIGHT};
            }}
        """)
        self.btn_create.clicked.connect(self.create_profiles)
        layout.addWidget(self.btn_create)
        
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def load_proxy_pool(self):
        farm_name = farm_manager.get_active_farm_name()
        if not farm_name: return
        from src.core.constants import FARMS_DIR
        config_path = FARMS_DIR / farm_name / "config.json"
        config = config_manager._read_config(config_path)
        pool = config.get("settings", {}).get("proxy_pool", [])
        if pool:
            proxy_texts = []
            for p in pool:
                if isinstance(p, dict):
                    proxy_texts.append(p.get("url", ""))
                else:
                    proxy_texts.append(str(p))
            self.input_proxies.setText("\n".join(proxy_texts))
            QMessageBox.information(self, "Успех", f"Загружено {len(pool)} прокси из пула.")
        else:
            QMessageBox.warning(self, "Пусто", "Прокси пул пуст.")

    def browse_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Выберите базовую папку")
        if dir_path:
            self.input_path.setText(dir_path)

    def generate_random_device_name(self):
        return hw_manager.generate_random_device_name()

    def create_profiles(self):
        prefix = self.input_prefix.text().strip()
        start_idx = self.spin_start.value()
        end_idx = self.spin_end.value()
        padding = self.spin_padding.value()
        base_dir_str = self.input_path.text().strip()

        if end_idx < start_idx:
            QMessageBox.warning(self, "Ошибка", "Конечный индекс не может быть меньше стартового!")
            return

        if not base_dir_str:
            QMessageBox.warning(self, "Ошибка", "Укажите базовый путь!")
            return

        base_dir = Path(base_dir_str)
        try:
            base_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать базовую директорию: {e}")
            return

        # Парсим список прокси
        proxies_text = self.input_proxies.toPlainText().strip()
        proxies = [p.strip() for p in proxies_text.split("\n") if p.strip()]

        created_count = 0
        random_devices = self.check_random_devices.isChecked()
        two_fa_password = self.input_2fa.text().strip() or None

        for idx in range(start_idx, end_idx + 1):
            num_str = f"{idx:0{padding}d}"
            profile_name = f"{prefix}{num_str}"
            workdir = base_dir / profile_name

            # Проверяем
            config_data = config_manager._read_config(CONFIG_FILE)
            exists = False
            for acc in config_data.get("accounts", []):
                if acc["name"] == profile_name or Path(acc["workdir"]) == workdir:
                    exists = True
                    break
            
            if exists:
                continue

            proxy_url = None
            if proxies:
                pos = idx - start_idx
                # Always cycle by default since cycle checkbox is replaced
                proxy_url = proxies[pos % len(proxies)]

            device_name = self.generate_random_device_name() if random_devices else f"PC-{profile_name}"

            if account_manager.add_account(CONFIG_FILE, profile_name, workdir, proxy_url, device_name, password=two_fa_password):
                created_count += 1

        farm_manager.save_active_farm_config()

        parent = self.parent()
        if parent:
            if hasattr(parent, 'refresh_accounts'):
                parent.refresh_accounts()
            elif hasattr(parent, 'acc_list_page') and hasattr(parent.acc_list_page, 'refresh_accounts'):
                parent.acc_list_page.refresh_accounts()

        QMessageBox.information(
            self, 
            "Успех", 
            f"Массовое создание завершено!\nУспешно создано {created_count} профилей."
        )
