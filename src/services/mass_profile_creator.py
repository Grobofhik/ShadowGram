import os
import random
import string
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QSpinBox, QTextEdit, QCheckBox, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from src.core.managers import proxy_manager, farm_manager, config_manager, hw_manager, process_manager, account_manager
from src.core.constants import CONFIG_FILE
from src import styles

class MassProfileCreatorService(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Массовое создание профилей")
        self.setFixedSize(500, 580)
        if parent and hasattr(parent, 'styleSheet'):
            self.setStyleSheet(parent.styleSheet())
        else:
            self.setStyleSheet(styles.STYLESHEET)
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Заголовок
        title_label = QLabel("Массовое создание профилей")
        title_label.setStyleSheet(f"font-weight: bold; color: {styles.COLOR_PRIMARY}; font-size: 16px;")
        layout.addWidget(title_label)

        # Настройки шаблона имени
        name_settings_layout = QHBoxLayout()
        
        # Префикс
        prefix_vbox = QVBoxLayout()
        prefix_vbox.addWidget(QLabel("Префикс:"))
        self.input_prefix = QLineEdit("acc")
        self.input_prefix.setPlaceholderText("acc")
        prefix_vbox.addWidget(self.input_prefix)
        name_settings_layout.addLayout(prefix_vbox)

        # Старт
        start_vbox = QVBoxLayout()
        start_vbox.addWidget(QLabel("Старт:"))
        self.spin_start = QSpinBox()
        self.spin_start.setRange(1, 9999)
        self.spin_start.setValue(1)
        start_vbox.addWidget(self.spin_start)
        name_settings_layout.addLayout(start_vbox)

        # Энд
        end_vbox = QVBoxLayout()
        end_vbox.addWidget(QLabel("Конец:"))
        self.spin_end = QSpinBox()
        self.spin_end.setRange(1, 9999)
        self.spin_end.setValue(10)
        end_vbox.addWidget(self.spin_end)
        name_settings_layout.addLayout(end_vbox)

        # Дополнение нулями (padding)
        pad_vbox = QVBoxLayout()
        pad_vbox.addWidget(QLabel("Длина номера:"))
        self.spin_padding = QSpinBox()
        self.spin_padding.setRange(1, 10)
        self.spin_padding.setValue(1)
        self.spin_padding.setToolTip("Ширина числовой части (например, 3 для acc001)")
        pad_vbox.addWidget(self.spin_padding)
        name_settings_layout.addLayout(pad_vbox)

        layout.addLayout(name_settings_layout)

        # Выбор базовой директории
        dir_vbox = QVBoxLayout()
        dir_vbox.addWidget(QLabel("Базовая папка для профилей (workdir):"))
        dir_hbox = QHBoxLayout()
        self.input_path = QLineEdit()
        # По умолчанию берем активную ферму
        farm_dir = farm_manager.get_active_farm_dir()
        default_path = farm_dir / "accounts"
        self.input_path.setText(str(default_path))
        dir_hbox.addWidget(self.input_path)
        
        btn_browse = QPushButton("Обзор")
        btn_browse.clicked.connect(self.browse_directory)
        dir_hbox.addWidget(btn_browse)
        dir_vbox.addLayout(dir_hbox)
        layout.addLayout(dir_vbox)

        # Доп опции
        options_layout = QHBoxLayout()
        self.check_random_devices = QCheckBox("Случайные имена устройств")
        self.check_random_devices.setChecked(True)
        options_layout.addWidget(self.check_random_devices)
        
        self.check_cycle_proxies = QCheckBox("Циклить прокси")
        self.check_cycle_proxies.setChecked(True)
        self.check_cycle_proxies.setToolTip("Если прокси меньше чем аккаунтов, распределять их по кругу")
        options_layout.addWidget(self.check_cycle_proxies)
        layout.addLayout(options_layout)

        # Поле со списком прокси
        proxy_vbox = QVBoxLayout()
        proxy_vbox.addWidget(QLabel("Список прокси (по одному на строку):"))
        self.input_proxies = QTextEdit()
        self.input_proxies.setPlaceholderText(
            "Вставьте список прокси в формате:\n"
            "http://user:pass@host:port\n"
            "socks5://user:pass@host:port\n"
            "каждый с новой строки"
        )
        proxy_vbox.addWidget(self.input_proxies)
        layout.addLayout(proxy_vbox)

        # Кнопка создания
        self.btn_create = QPushButton("Создать профили")
        self.btn_create.setObjectName("LaunchBtn")
        self.btn_create.setFixedHeight(45)
        self.btn_create.clicked.connect(self.create_profiles)
        layout.addWidget(self.btn_create)

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
        cycle_proxies = self.check_cycle_proxies.isChecked()
        random_devices = self.check_random_devices.isChecked()

        for idx in range(start_idx, end_idx + 1):
            num_str = f"{idx:0{padding}d}"
            profile_name = f"{prefix}{num_str}"
            workdir = base_dir / profile_name

            # Проверяем, существует ли аккаунт с таким путем или именем, чтобы избежать дубликатов
            # Загружаем текущий конфиг
            config_data = config_manager._read_config(CONFIG_FILE)
            exists = False
            for acc in config_data.get("accounts", []):
                if acc["name"] == profile_name or Path(acc["workdir"]) == workdir:
                    exists = True
                    break
            
            if exists:
                continue

            # Распределение прокси
            proxy_url = None
            if proxies:
                pos = idx - start_idx
                if cycle_proxies:
                    proxy_url = proxies[pos % len(proxies)]
                else:
                    proxy_url = proxies[pos] if pos < len(proxies) else None

            # Имя устройства
            device_name = self.generate_random_device_name() if random_devices else f"PC-{profile_name}"

            if account_manager.add_account(CONFIG_FILE, profile_name, workdir, proxy_url, device_name):
                created_count += 1

        # Синхронизируем конфиг с фермой
        farm_manager.save_active_farm_config()

        # Обновляем интерфейс в главном окне
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
        self.accept()
