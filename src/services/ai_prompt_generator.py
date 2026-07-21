import json
import random

import requests
from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.constants import CONFIG_FILE
from src.core.managers import account_manager, config_manager


LIST_STYLE = """
QListWidget {
    border-radius: 12px;
    padding: 8px;
}
QListWidget::item {
    padding: 8px 10px;
    border-radius: 6px;
}
"""


class PromptGeneratorWorker(QThread):
    progress_update = pyqtSignal(int, int)
    log_update = pyqtSignal(str)
    finished_work = pyqtSignal(int)

    def __init__(self, accounts, api_key, api_base_url, model_name, base_prompt, theme):
        super().__init__()
        self.accounts = accounts
        self.api_key = api_key
        self.api_base_url = api_base_url.rstrip("/")
        self.model_name = model_name
        self.base_prompt = base_prompt
        self.theme = theme
        self.is_running = True

    def run(self):
        updated_count = 0
        total = len(self.accounts)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        theme_instructions = {
            "Криптовалюта и Web3": "Обязательно свяжи эту роль с миром криптовалют, трейдинга, NFT, майнинга или Web3.",
            "Программирование и IT": "Обязательно свяжи эту роль с программированием, разработкой ПО, кибербезопасностью, администрированием или IT-технологиями.",
            "Случайная (Tech / IT / Crypto)": "Обязательно свяжи эту роль либо с криптовалютами, либо с программированием, либо с высокими технологиями.",
        }

        theme_addon = theme_instructions.get(self.theme, "")

        system_instruction = (
            "Ты - ИИ-ассистент, который помогает создавать уникальные инструкции (промпты) для ботов-комментаторов. "
            "Твоя задача - написать развернутый, уникальный системный промпт "
            "от первого лица (как будто обращаешься к самому боту), который задаст стиль общения, интересы и роль. "
            f"{theme_addon} "
            "Ответь только готовым системным промптом, без приветствий, кавычек и лишних объяснений."
        )

        for index, account in enumerate(self.accounts):
            if not self.is_running:
                break

            self.log_update.emit(f"Генерация для: {account['name']}...")

            randomness = (
                "Добавь к этой роли уникальную особенность: "
                f"{random.choice(['немного сарказма', 'использование эмодзи', 'любовь к точным фактам', 'короткие предложения', 'подростковый сленг', 'профессиональный жаргон', 'философский тон', 'пассивная агрессия', 'оптимизм', 'склонность к теориям заговора'])}."
            )

            if self.base_prompt:
                user_content = f"Базовая идея:\n{self.base_prompt}\n\n{randomness}"
            else:
                user_content = (
                    "Придумай абсолютно случайную, но реалистичную и интересную роль "
                    f"для пользователя в интернете в рамках заданной тематики. {randomness}"
                )

            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_content},
                ],
                "max_tokens": 300,
                "temperature": 0.9,
            }

            try:
                response = requests.post(
                    f"{self.api_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=20,
                )
                if response.status_code == 200:
                    data = response.json()
                    generated_prompt = data["choices"][0]["message"]["content"].strip()

                    if account_manager.update_prompt(CONFIG_FILE, account["workdir"], generated_prompt):
                        updated_count += 1
                        self.log_update.emit(f"OK: {account['name']}")
                else:
                    self.log_update.emit(
                        f"API error ({response.status_code}) для {account['name']}: {response.text}"
                    )
            except Exception as error:
                self.log_update.emit(f"Network error для {account['name']}: {error}")

            self.progress_update.emit(index + 1, total)

        self.finished_work.emit(updated_count)

    def stop(self):
        self.is_running = False


class AIPromptGeneratorService(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Генератор уникальных AI-промптов")
        self.resize(1120, 820)
        self.setObjectName("PageRoot")
        self.worker = None
        self.all_selected = False
        self.init_ui()
        self.load_accounts()
        self.load_api_keys()

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

        eyebrow = QLabel("AI ROLE FORGE")
        eyebrow.setObjectName("PageEyebrow")
        hero_layout.addWidget(eyebrow)

        title = QLabel("Генератор уникальных AI-промптов")
        title.setObjectName("PageTitle")
        hero_layout.addWidget(title)

        subtitle = QLabel(
            "Собирает уникальные роли для аккаунтов через OpenAI-совместимый API и сразу сохраняет результат в профили."
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

        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(16)

        left_col = QVBoxLayout()
        left_col.setSpacing(16)

        api_card, api_layout = self.create_card(
            "Параметры API",
            "Поддерживается любой OpenAI-совместимый endpoint с методом `chat/completions`.",
        )
        api_form = QFormLayout()
        api_form.setSpacing(12)
        api_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.input_base_url = QLineEdit("https://api.groq.com/openai/v1")
        self.input_base_url.setPlaceholderText("https://api.openai.com/v1")
        api_form.addRow("API URL:", self.input_base_url)

        self.input_model = QLineEdit("llama-3.1-8b-instant")
        self.input_model.setPlaceholderText("gpt-4o-mini")
        api_form.addRow("Модель:", self.input_model)

        self.input_api_key = QLineEdit()
        self.input_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_api_key.setPlaceholderText("sk-...")
        api_form.addRow("API ключ:", self.input_api_key)
        api_layout.addLayout(api_form)
        left_col.addWidget(api_card)

        theme_card, theme_layout = self.create_card(
            "Параметры роли",
            "Тематика задает рамку генерации, а базовая роль помогает сузить стиль будущего промпта.",
        )
        theme_form = QFormLayout()
        theme_form.setSpacing(12)
        theme_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.combo_theme = QComboBox()
        self.combo_theme.addItems(
            [
                "Случайная (Tech / IT / Crypto)",
                "Криптовалюта и Web3",
                "Программирование и IT",
            ]
        )
        theme_form.addRow("Тематика:", self.combo_theme)
        theme_layout.addLayout(theme_form)

        prompt_label = QLabel("Базовая роль")
        prompt_label.setObjectName("StatHint")
        theme_layout.addWidget(prompt_label)

        self.input_base_prompt = QTextEdit()
        self.input_base_prompt.setFixedHeight(150)
        self.input_base_prompt.setPlaceholderText(
            "Оставьте пустым для полной автогенерации.\nНапример: ты крипто-инвестор, который любит рисковать..."
        )
        theme_layout.addWidget(self.input_base_prompt)
        left_col.addWidget(theme_card)
        left_col.addStretch(1)

        right_col = QVBoxLayout()
        right_col.setSpacing(16)

        acc_card, acc_layout = self.create_card(
            "Выбор аккаунтов",
            "Поиск фильтрует список по имени. Генерация затронет только выделенные аккаунты.",
        )

        head_row = QHBoxLayout()
        head_row.setSpacing(12)
        head_row.addStretch()

        self.summary_label = QLabel("")
        self.summary_label.setObjectName("MetaBadge")
        head_row.addWidget(self.summary_label)
        acc_layout.addLayout(head_row)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск аккаунта...")
        self.search_input.textChanged.connect(self.filter_accounts)
        acc_layout.addWidget(self.search_input)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.list_widget.setStyleSheet(LIST_STYLE)
        self.list_widget.itemSelectionChanged.connect(self.update_summary)
        acc_layout.addWidget(self.list_widget, 1)

        self.btn_select_all = QPushButton("Выбрать все")
        self.btn_select_all.setObjectName("GhostBtn")
        self.btn_select_all.clicked.connect(self.toggle_select_all)
        acc_layout.addWidget(self.btn_select_all)
        right_col.addWidget(acc_card, 1)

        control_card, control_layout = self.create_card(
            "Прогресс",
            "Лог обновляется в реальном времени по мере генерации и записи промптов.",
        )

        self.log_area = QTextEdit()
        self.log_area.setObjectName("LogOutput")
        self.log_area.setReadOnly(True)
        self.log_area.setFixedHeight(140)
        control_layout.addWidget(self.log_area)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(14)
        control_layout.addWidget(self.progress_bar)

        self.btn_generate = QPushButton("Начать генерацию")
        self.btn_generate.setObjectName("LaunchBtn")
        self.btn_generate.clicked.connect(self.start_generation)
        control_layout.addWidget(self.btn_generate)
        right_col.addWidget(control_card)

        columns_layout.addLayout(left_col, 1)
        columns_layout.addLayout(right_col, 1)
        layout.addLayout(columns_layout)

        scroll.setWidget(container)
        main_layout.addWidget(scroll, 1)

    def load_accounts(self):
        self.accounts = config_manager.load_config(CONFIG_FILE)
        self.list_widget.clear()
        for account in self.accounts:
            self.list_widget.addItem(account["name"])
        self.update_summary()

    def filter_accounts(self, text):
        query = text.lower()
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            item.setHidden(query not in item.text().lower())
        self.all_selected = False
        self.btn_select_all.setText("Выбрать все")
        self.update_summary()

    def toggle_select_all(self):
        self.all_selected = not self.all_selected
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            if not item.isHidden():
                item.setSelected(self.all_selected)

        self.btn_select_all.setText("Снять выделение" if self.all_selected else "Выбрать все")
        self.update_summary()

    def update_summary(self):
        visible_count = 0
        for index in range(self.list_widget.count()):
            if not self.list_widget.item(index).isHidden():
                visible_count += 1
        self.summary_label.setText(f"{len(self.list_widget.selectedItems())} выбрано / {visible_count} видно")

    def load_api_keys(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as file_obj:
                config = json.load(file_obj)
                settings = config.get("settings", {})

                if settings.get("default_ai_api_key"):
                    self.input_api_key.setText(settings["default_ai_api_key"])
                if settings.get("default_ai_base_url"):
                    self.input_base_url.setText(settings["default_ai_base_url"])
                if settings.get("default_ai_model_name"):
                    self.input_model.setText(settings["default_ai_model_name"])

                modules_data = config.get("modules", {})
                ai_plugin = modules_data.get("ai_commenter.py", {})

                if not self.input_api_key.text() and "api_key" in ai_plugin:
                    self.input_api_key.setText(ai_plugin["api_key"])
                if not self.input_base_url.text() and "api_base_url" in ai_plugin:
                    self.input_base_url.setText(ai_plugin["api_base_url"])
                if not self.input_model.text() and "model_name" in ai_plugin:
                    self.input_model.setText(ai_plugin["model_name"])
        except Exception:
            pass

    def append_log(self, text):
        self.log_area.append(text)
        scrollbar = self.log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def update_progress(self, current, total):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

    def start_generation(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Внимание", "Выберите хотя бы один аккаунт!")
            return

        api_key = self.input_api_key.text().strip()
        api_base_url = self.input_base_url.text().strip()
        model_name = self.input_model.text().strip()
        base_prompt = self.input_base_prompt.toPlainText().strip()
        theme = self.combo_theme.currentText()

        if not all([api_key, api_base_url, model_name]):
            QMessageBox.warning(self, "Внимание", "Заполните все поля API!")
            return

        selected_names = [item.text() for item in selected_items]
        selected_accounts = [account for account in self.accounts if account["name"] in selected_names]

        self.btn_generate.setEnabled(False)
        self.log_area.clear()
        self.progress_bar.setValue(0)
        self.append_log(
            f"Запуск генерации для {len(selected_accounts)} аккаунтов. Тема: {theme}"
        )

        self.worker = PromptGeneratorWorker(
            selected_accounts,
            api_key,
            api_base_url,
            model_name,
            base_prompt,
            theme,
        )
        self.worker.log_update.connect(self.append_log)
        self.worker.progress_update.connect(self.update_progress)
        self.worker.finished_work.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, updated_count):
        self.btn_generate.setEnabled(True)
        QMessageBox.information(
            self,
            "Готово",
            f"Генерация завершена.\nУспешно обновлено: {updated_count}",
        )
        self.accept()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        super().closeEvent(event)
