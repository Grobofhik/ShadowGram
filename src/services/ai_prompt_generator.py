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
        self.worker = None
        self.all_selected = False
        self.init_ui()
        self.load_accounts()
        self.load_api_keys()

    def create_card(self, title):
        from PyQt6.QtWidgets import QFrame
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background-color: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 10px; }}")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(15, 15, 15, 15)
        card_layout.setSpacing(10)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {styles.COLOR_PRIMARY}; border: none;")
        card_layout.addWidget(lbl_title)
        return card, card_layout

    def init_ui(self):
        from PyQt6.QtWidgets import QScrollArea, QWidget, QFormLayout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        
        layout = QVBoxLayout(container)
        layout.setSpacing(20)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(5)
        title_label = QLabel("Генератор уникальных ИИ-ролей")
        title_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {styles.COLOR_TEXT_MAIN};")
        
        info_label = QLabel("Умный конструктор запросов для ИИ-модулей. Сгенерируйте уникальные роли и стили общения для аккаунтов на основе заданной тематики.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 14px;")
        
        header_layout.addWidget(title_label)
        header_layout.addWidget(info_label)
        layout.addLayout(header_layout)
        
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(20)
        
        # --- LEFT COLUMN ---
        left_col = QVBoxLayout()
        left_col.setSpacing(20)
        
        # API Card
        api_card, api_layout = self.create_card("🔑 Настройки нейросети")
        api_form = QFormLayout()
        api_form.setSpacing(15)
        api_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        self.input_base_url = QLineEdit("https://api.groq.com/openai/v1")
        self.input_base_url.setStyleSheet(f"background-color: {styles.COLOR_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 6px; padding: 8px;")
        self.input_base_url.setPlaceholderText("https://api.openai.com/v1")
        lbl_url = QLabel("API URL:")
        lbl_url.setStyleSheet("border: none; font-weight: bold;")
        api_form.addRow(lbl_url, self.input_base_url)
        
        self.input_model = QLineEdit("llama-3.1-8b-instant")
        self.input_model.setStyleSheet(f"background-color: {styles.COLOR_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 6px; padding: 8px;")
        self.input_model.setPlaceholderText("gpt-4o-mini")
        lbl_model = QLabel("Модель:")
        lbl_model.setStyleSheet("border: none; font-weight: bold;")
        api_form.addRow(lbl_model, self.input_model)
        
        self.input_api_key = QLineEdit()
        self.input_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_api_key.setPlaceholderText("sk-...")
        self.input_api_key.setStyleSheet(f"background-color: {styles.COLOR_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 6px; padding: 8px;")
        lbl_key = QLabel("API Ключ:")
        lbl_key.setStyleSheet("border: none; font-weight: bold;")
        api_form.addRow(lbl_key, self.input_api_key)
        
        api_layout.addLayout(api_form)
        left_col.addWidget(api_card)
        
        # Theme Card
        theme_card, theme_layout = self.create_card("🎭 Настройки роли")
        theme_form = QFormLayout()
        theme_form.setSpacing(15)
        
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["Случайная (Tech / IT / Crypto)", "Криптовалюта и Web3", "Программирование и IT"])
        self.combo_theme.setStyleSheet(f"background-color: {styles.COLOR_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 6px; padding: 8px; color: {styles.COLOR_TEXT_MAIN};")
        lbl_theme = QLabel("Тематика:")
        lbl_theme.setStyleSheet("border: none; font-weight: bold;")
        theme_form.addRow(lbl_theme, self.combo_theme)
        
        theme_layout.addLayout(theme_form)
        
        lbl_prompt = QLabel("Базовая роль (дополнительно):")
        lbl_prompt.setStyleSheet("border: none; color: {styles.COLOR_TEXT_MUTED};")
        theme_layout.addWidget(lbl_prompt)

        self.input_base_prompt = QTextEdit()
        self.input_base_prompt.setFixedHeight(120)
        self.input_base_prompt.setStyleSheet(f"""
            QTextEdit {{
                background-color: {styles.COLOR_BG}; 
                border: 1px solid {styles.COLOR_BORDER}; 
                border-radius: 6px; 
                padding: 10px;
                line-height: 1.4;
            }}
        """)
        self.input_base_prompt.setPlaceholderText("Оставьте пустым для полной автогенерации. \nНапример: 'Ты крипто-инвестор, который любит рисковать...'")
        theme_layout.addWidget(self.input_base_prompt)
        
        left_col.addWidget(theme_card)
        left_col.addStretch(1)
        
        # --- RIGHT COLUMN ---
        right_col = QVBoxLayout()
        right_col.setSpacing(20)
        
        # Accounts Card
        acc_card, acc_layout = self.create_card("👥 Выбор аккаунтов")
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск аккаунта...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {styles.COLOR_BG}; 
                border: 1px solid {styles.COLOR_BORDER}; 
                border-radius: 6px; 
                padding: 8px;
            }}
            QLineEdit:focus {{
                border: 1px solid {styles.COLOR_PRIMARY};
            }}
        """)
        self.search_input.textChanged.connect(self.filter_accounts)
        acc_layout.addWidget(self.search_input)
        
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {styles.COLOR_BG}; 
                border: 1px solid {styles.COLOR_BORDER}; 
                border-radius: 6px;
                padding: 5px;
            }}
            QListWidget::item {{
                padding: 6px;
                border-radius: 4px;
            }}
            QListWidget::item:selected {{
                background-color: {styles.COLOR_PRIMARY_DARK};
                color: #ffffff;
            }}
            QListWidget::item:hover {{
                background-color: {styles.COLOR_HOVER_BG};
            }}
        """)
        acc_layout.addWidget(self.list_widget, 1) # Expand vertically
        
        self.btn_select_all = QPushButton("✅ Выбрать все / Снять")
        self.btn_select_all.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.COLOR_HOVER_BG}; 
                border: 1px solid {styles.COLOR_BORDER}; 
                border-radius: 6px; 
                padding: 8px;
                color: {styles.COLOR_TEXT_MAIN};
            }}
            QPushButton:hover {{
                background-color: {styles.COLOR_CONSOLE_BG};
                border: 1px solid {styles.COLOR_PRIMARY};
            }}
        """)
        self.btn_select_all.clicked.connect(self.toggle_select_all)
        acc_layout.addWidget(self.btn_select_all)
        
        right_col.addWidget(acc_card, 1) # Give this card stretch
        
        # Controls Section
        control_card, control_layout = self.create_card("📊 Прогресс")
        
        self.log_area = QTextEdit()
        self.log_area.setFixedHeight(100)
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet(f"""
            QTextEdit {{
                background-color: {styles.COLOR_BG}; 
                border: 1px solid {styles.COLOR_BORDER}; 
                border-radius: 6px; 
                padding: 8px; 
                color: {styles.COLOR_PRIMARY}; 
                font-family: monospace;
            }}
        """)
        control_layout.addWidget(self.log_area)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{ 
                border: none; 
                border-radius: 6px; 
                background: {styles.COLOR_BG}; 
            }}
            QProgressBar::chunk {{ 
                background-color: {styles.COLOR_PRIMARY}; 
                border-radius: 6px; 
            }}
        """)
        control_layout.addWidget(self.progress_bar)

        self.btn_generate = QPushButton("🚀 Начать генерацию")
        self.btn_generate.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.COLOR_PRIMARY};
                color: #000000;
                border: none;
                border-radius: 8px;
                padding: 14px;
                font-weight: bold;
                font-size: 15px;
            }}
            QPushButton:hover {{
                background-color: {styles.COLOR_PRIMARY_LIGHT};
            }}
            QPushButton:disabled {{
                background-color: {styles.COLOR_HOVER_BG};
                color: {styles.COLOR_TEXT_MUTED};
            }}
        """)
        self.btn_generate.clicked.connect(self.start_generation)
        control_layout.addWidget(self.btn_generate)
        
        right_col.addWidget(control_card)

        # Build columns
        columns_layout.addLayout(left_col, 1)
        columns_layout.addLayout(right_col, 1)
        
        layout.addLayout(columns_layout)
        scroll.setWidget(container)
        main_layout.addWidget(scroll)

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
            self.btn_select_all.setText("✅ Выбрать все")

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
