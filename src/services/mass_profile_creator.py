from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.constants import CONFIG_FILE
from src.core.managers import account_manager, config_manager, farm_manager, hw_manager


class MassProfileCreatorService(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Массовое создание профилей")
        self.resize(820, 760)
        self.setObjectName("PageRoot")
        self.init_ui()

    def create_card(self, title, subtitle=None):
        card = QFrame()
        card.setObjectName("PageCard")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setObjectName("ServiceTitle")
        layout.addWidget(title_label)

        if subtitle:
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("PageSubtitle")
            subtitle_label.setWordWrap(True)
            layout.addWidget(subtitle_label)

        return card, layout

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        hero = QFrame()
        hero.setObjectName("PageHero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 22, 24, 22)
        hero_layout.setSpacing(6)

        eyebrow = QLabel("BULK PROFILE BUILDER")
        eyebrow.setObjectName("PageEyebrow")
        hero_layout.addWidget(eyebrow)

        title = QLabel("Массовое создание профилей")
        title.setObjectName("PageTitle")
        hero_layout.addWidget(title)

        subtitle = QLabel(
            "Генерирует профили по шаблону имени, создает `workdir`, раскладывает прокси и при необходимости назначает отпечатки устройств."
        )
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)
        hero_layout.addWidget(subtitle)

        main_layout.addWidget(hero)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        container.setObjectName("ScrollContent")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        name_card, name_layout = self.create_card(
            "Шаблон имен",
            "Префикс и диапазон определяют, какие имена и папки будут созданы.",
        )
        form_name = QFormLayout()
        form_name.setSpacing(12)
        form_name.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.input_prefix = QLineEdit("acc")
        form_name.addRow("Префикс:", self.input_prefix)

        self.spin_start = QSpinBox()
        self.spin_start.setRange(1, 9999)
        self.spin_start.setValue(1)
        form_name.addRow("Старт:", self.spin_start)

        self.spin_end = QSpinBox()
        self.spin_end.setRange(1, 9999)
        self.spin_end.setValue(10)
        form_name.addRow("Конец:", self.spin_end)

        self.spin_padding = QSpinBox()
        self.spin_padding.setRange(1, 10)
        self.spin_padding.setValue(1)
        form_name.addRow("Длина номера:", self.spin_padding)
        name_layout.addLayout(form_name)
        layout.addWidget(name_card)

        dir_card, dir_layout = self.create_card(
            "Рабочая директория",
            "Базовый путь для новых `workdir`. Каталог будет создан автоматически, если его нет.",
        )
        dir_row = QHBoxLayout()
        dir_row.setSpacing(10)

        self.input_path = QLineEdit()
        farm_dir = farm_manager.get_active_farm_dir()
        self.input_path.setText(str(farm_dir / "accounts"))
        dir_row.addWidget(self.input_path, 1)

        btn_browse = QPushButton("Обзор")
        btn_browse.setObjectName("GhostBtn")
        btn_browse.clicked.connect(self.browse_directory)
        dir_row.addWidget(btn_browse)

        dir_layout.addLayout(dir_row)
        layout.addWidget(dir_card)

        adv_card, adv_layout = self.create_card(
            "Дополнительные параметры",
            "Общие настройки 2FA, генерация device name и загрузка списка прокси для пачки профилей.",
        )

        form_2fa = QFormLayout()
        form_2fa.setSpacing(12)
        form_2fa.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.input_2fa = QLineEdit()
        self.input_2fa.setPlaceholderText("Общий облачный пароль, если нужен")
        form_2fa.addRow("2FA пароль:", self.input_2fa)
        adv_layout.addLayout(form_2fa)

        option_row = QHBoxLayout()
        option_row.setSpacing(12)

        self.check_random_devices = QCheckBox("Генерировать отпечатки устройств")
        self.check_random_devices.setChecked(True)
        option_row.addWidget(self.check_random_devices)

        option_row.addStretch()

        self.btn_load_proxies = QPushButton("Загрузить из Proxy Pool")
        self.btn_load_proxies.setObjectName("GhostBtn")
        self.btn_load_proxies.clicked.connect(self.load_proxy_pool)
        option_row.addWidget(self.btn_load_proxies)

        adv_layout.addLayout(option_row)

        proxy_label = QLabel("Прокси, по одному на строку")
        proxy_label.setObjectName("StatHint")
        adv_layout.addWidget(proxy_label)

        self.input_proxies = QTextEdit()
        self.input_proxies.setPlaceholderText(
            "http://user:pass@host:port\nsocks5://user:pass@host:port"
        )
        self.input_proxies.setFixedHeight(110)
        adv_layout.addWidget(self.input_proxies)

        layout.addWidget(adv_card)

        action_bar = QFrame()
        action_bar.setObjectName("ToolbarCard")
        action_layout = QHBoxLayout(action_bar)
        action_layout.setContentsMargins(14, 12, 14, 12)
        action_layout.setSpacing(10)

        note = QLabel("Профили с уже существующим именем или `workdir` будут пропущены.")
        note.setObjectName("PageSubtitle")
        note.setWordWrap(True)
        action_layout.addWidget(note, 1)

        self.btn_create = QPushButton("Создать профили")
        self.btn_create.setObjectName("LaunchBtn")
        self.btn_create.clicked.connect(self.create_profiles)
        action_layout.addWidget(self.btn_create)

        layout.addWidget(action_bar)
        layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll, 1)

    def load_proxy_pool(self):
        farm_name = farm_manager.get_active_farm_name()
        if not farm_name:
            return

        from src.core.constants import FARMS_DIR

        config_path = FARMS_DIR / farm_name / "config.json"
        config = config_manager._read_config(config_path)
        pool = config.get("settings", {}).get("proxy_pool", [])
        if pool:
            proxy_texts = []
            for proxy in pool:
                if isinstance(proxy, dict):
                    proxy_texts.append(proxy.get("url", ""))
                else:
                    proxy_texts.append(str(proxy))
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
        except Exception as error:
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать базовую директорию: {error}")
            return

        proxies_text = self.input_proxies.toPlainText().strip()
        proxies = [proxy.strip() for proxy in proxies_text.split("\n") if proxy.strip()]

        created_count = 0
        random_devices = self.check_random_devices.isChecked()
        two_fa_password = self.input_2fa.text().strip() or None

        for idx in range(start_idx, end_idx + 1):
            num_str = f"{idx:0{padding}d}"
            profile_name = f"{prefix}{num_str}"
            workdir = base_dir / profile_name

            config_data = config_manager._read_config(CONFIG_FILE)
            exists = False
            for account in config_data.get("accounts", []):
                if account["name"] == profile_name or Path(account["workdir"]) == workdir:
                    exists = True
                    break

            if exists:
                continue

            proxy_url = None
            if proxies:
                pos = idx - start_idx
                proxy_url = proxies[pos % len(proxies)]

            device_name = (
                self.generate_random_device_name() if random_devices else f"PC-{profile_name}"
            )

            if account_manager.add_account(
                CONFIG_FILE,
                profile_name,
                workdir,
                proxy_url,
                device_name,
                password=two_fa_password,
            ):
                created_count += 1

        farm_manager.save_active_farm_config()

        parent = self.parent()
        if parent:
            if hasattr(parent, "refresh_accounts"):
                parent.refresh_accounts()
            elif hasattr(parent, "acc_list_page") and hasattr(parent.acc_list_page, "refresh_accounts"):
                parent.acc_list_page.refresh_accounts()

        QMessageBox.information(
            self,
            "Успех",
            f"Массовое создание завершено!\nУспешно создано {created_count} профилей.",
        )
