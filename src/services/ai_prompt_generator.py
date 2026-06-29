import random
import string
import requests
import json
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QListWidget, QMessageBox, 
                             QTextEdit, QProgressBar, QComboBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from src.core.managers import proxy_manager, farm_manager, config_manager, hw_manager, process_manager, account_manager
from src.core.constants import CONFIG_FILE
from src import styles

class PromptGeneratorWorker(QThread):
    progress_update = pyqtSignal(int, int) # current, total
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
            "Content-Type": "application/json"
        }

        theme_instructions = {
            "Криптовалюта и Web3": "Обязательно свяжи эту роль с миром криптовалют, трейдинга, NFT, майнинга или Web3.",
            "Программирование и IT": "Обязательно свяжи эту роль с программированием, разработкой ПО, кибербезопасностью, администрированием или IT-технологиями.",
            "Случайная (Tech / IT / Crypto)": "Обязательно свяжи эту роль либо с криптовалютами, либо с программированием, либо с высокими технологиями."
        }
        
        theme_addon = theme_instructions.get(self.theme, "")

        system_instruction = (
            "Ты — ИИ-ассистент, который помогает создавать уникальные инструкции (промпты) для ботов-комментаторов. "
            "Твоя задача — написать РАЗВЕРНУТЫЙ, УНИКАЛЬНЫЙ системный промпт "
            "от первого лица (как будто обращаешься к самому боту), который задаст стиль общения, интересы и роль. "
            f"{theme_addon} "
            "Ответь ТОЛЬКО готовым системным промптом, без приветствий, кавычек и лишних объяснений."
        )

        for i, acc in enumerate(self.accounts):
            if not self.is_running:
                break
                
            self.log_update.emit(f"Генерация для: {acc['name']}...")
            
            randomness = f"Добавь к этой роли уникальную особенность: {random.choice(['немного сарказма', 'использование эмодзи', 'любовь к точным фактам', 'короткие предложения', 'подростковый сленг', 'профессиональный жаргон', 'философский тон', 'пассивная агрессия', 'оптимизм', 'склонность к теориям заговора'])}."
            
            if self.base_prompt:
                user_content = f"Базовая идея:\n{self.base_prompt}\n\n{randomness}"
            else:
                user_content = f"Придумай абсолютно случайную, но реалистичную и интересную роль для пользователя в интернете в рамках заданной тематики. {randomness}"

            payload = {
                "model": self.model_name,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_content}
                ],
                "max_tokens": 300,
                "temperature": 0.9 # Высокая температура для большей уникальности
            }

            try:
                response = requests.post(f"{self.api_base_url}/chat/completions", headers=headers, json=payload, timeout=20)
                if response.status_code == 200:
                    data = response.json()
                    generated_prompt = data['choices'][0]['message']['content'].strip()
                    
                    if account_manager.update_prompt(CONFIG_FILE, acc['workdir'], generated_prompt):
                        updated_count += 1
                        self.log_update.emit(f"✓ Успешно для {acc['name']}")
                else:
                    self.log_update.emit(f"✗ Ошибка API ({response.status_code}) для {acc['name']}: {response.text}")
            except Exception as e:
                self.log_update.emit(f"✗ Ошибка сети для {acc['name']}: {str(e)}")

            self.progress_update.emit(i + 1, total)

        self.finished_work.emit(updated_count)

    def stop(self):
        self.is_running = False


class AIPromptGeneratorService(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Генератор уникальных AI Промптов")
        self.setFixedSize(540, 720) # Увеличили высоту для простора
        self.worker = None
        self.all_selected = False
        self.init_ui()
        self.load_accounts()
        self.load_api_keys()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8) # Более плотная компоновка
        layout.setContentsMargins(15, 15, 15, 15)

        info_label = QLabel("Генерация уникального стиля общения для выбранных аккаунтов.")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)

        # Настройки API
        api_layout = QVBoxLayout()
        api_layout.setSpacing(4)
        
        # Группируем API URL и Модель в одну строку
        url_model_layout = QHBoxLayout()
        url_model_layout.addWidget(QLabel("Base URL:"))
        self.input_base_url = QLineEdit()
        self.input_base_url.setText("https://api.groq.com/openai/v1")
        url_model_layout.addWidget(self.input_base_url)
        
        url_model_layout.addWidget(QLabel("Модель:"))
        self.input_model = QLineEdit()
        self.input_model.setText("llama-3.1-8b-instant")
        url_model_layout.addWidget(self.input_model)
        
        api_layout.addWidget(QLabel("API Ключ (Groq, OpenRouter и т.д.):"))
        self.input_api_key = QLineEdit()
        self.input_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addWidget(self.input_api_key)
        api_layout.addLayout(url_model_layout)
        layout.addLayout(api_layout)

        # Тематика и промпт
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Тематика:"))
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["Случайная (Tech / IT / Crypto)", "Криптовалюта и Web3", "Программирование и IT"])
        theme_layout.addWidget(self.combo_theme)
        layout.addLayout(theme_layout)

        layout.addWidget(QLabel("Базовая роль (оставьте пустым для генерации по тематике):"))
        self.input_base_prompt = QTextEdit()
        self.input_base_prompt.setFixedHeight(60)
        self.input_base_prompt.setPlaceholderText("Например: Ты инвестор, который любит обсуждать токены, всегда пишет коротко и по делу.")
        layout.addWidget(self.input_base_prompt)

        # Список аккаунтов и поиск
        list_header_layout = QHBoxLayout()
        list_header_layout.addWidget(QLabel("Выберите аккаунты:"))
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск аккаунта...")
        self.search_input.setFixedHeight(40)
        self.search_input.textChanged.connect(self.filter_accounts)
        list_header_layout.addWidget(self.search_input)
        layout.addLayout(list_header_layout)
        
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        layout.addWidget(self.list_widget)

        # Кнопки и прогресс плотно внизу
        bottom_layout = QVBoxLayout()
        bottom_layout.setSpacing(5)

        self.btn_select_all = QPushButton("Выбрать все")
        self.btn_select_all.clicked.connect(self.toggle_select_all)
        bottom_layout.addWidget(self.btn_select_all)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(15)
        self.progress_bar.setTextVisible(False)
        bottom_layout.addWidget(self.progress_bar)

        self.log_area = QTextEdit()
        self.log_area.setFixedHeight(90)
        self.log_area.setReadOnly(True)
        bottom_layout.addWidget(self.log_area)

        self.btn_generate = QPushButton("Начать генерацию")
        self.btn_generate.setStyleSheet(f"background-color: {styles.COLOR_PRIMARY_DARK}; color: {'#000000' if styles.COLOR_PRIMARY == '#00E676' else '#FFFFFF'}; font-weight: bold; height: 35px;")
        self.btn_generate.clicked.connect(self.start_generation)
        bottom_layout.addWidget(self.btn_generate)

        layout.addLayout(bottom_layout)

    def load_accounts(self):
        self.accounts = config_manager.load_config(CONFIG_FILE)
        for acc in self.accounts:
            self.list_widget.addItem(acc['name'])

    def filter_accounts(self, text):
        query = text.lower()
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setHidden(query not in item.text().lower())

    def toggle_select_all(self):
        self.all_selected = not self.all_selected
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if not item.isHidden():
                item.setSelected(self.all_selected)
        
        if self.all_selected:
            self.btn_select_all.setText("Снять выделение")
        else:
            self.btn_select_all.setText("Выбрать все")

    def load_api_keys(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                settings = config.get("settings", {})
                
                # Сначала пытаемся взять из общих настроек
                if "default_ai_api_key" in settings and settings["default_ai_api_key"]:
                    self.input_api_key.setText(settings["default_ai_api_key"])
                if "default_ai_base_url" in settings and settings["default_ai_base_url"]:
                    self.input_base_url.setText(settings["default_ai_base_url"])
                if "default_ai_model_name" in settings and settings["default_ai_model_name"]:
                    self.input_model.setText(settings["default_ai_model_name"])
                
                # Если в общих настройках пусто, пробуем вытащить из истории плагина AICommenter
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
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

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
        selected_accounts = [acc for acc in self.accounts if acc['name'] in selected_names]

        self.btn_generate.setEnabled(False)
        self.log_area.clear()
        self.progress_bar.setValue(0)
        self.append_log(f"Запуск генерации для {len(selected_accounts)} аккаунтов (Тема: {theme})...")

        self.worker = PromptGeneratorWorker(selected_accounts, api_key, api_base_url, model_name, base_prompt, theme)
        self.worker.log_update.connect(self.append_log)
        self.worker.progress_update.connect(self.update_progress)
        self.worker.finished_work.connect(self.on_finished)
        self.worker.start()

    def on_finished(self, updated_count):
        self.btn_generate.setEnabled(True)
        QMessageBox.information(self, "Готово", f"Генерация завершена.\nУспешно обновлено: {updated_count}")
        self.accept()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        super().closeEvent(event)
