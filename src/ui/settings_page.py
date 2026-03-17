import json
import os
import shutil
import random
import threading
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QMessageBox, QFileDialog,
                             QTabWidget, QCheckBox, QSpinBox, QTextEdit, QScrollArea, QProgressBar)
from PyQt6.QtCore import pyqtSignal, Qt, QThread

from src.core import logic
from src.core.constants import CONFIG_FILE
from src.ui.docs_window import DocsWindow

"""
Страница настроек приложения.
Функции:

- init_ui: инициализация элементов управления настроек с вкладками
- load_settings: загрузка настроек из файла
- save_settings: сохранение настроек
- distribute_proxies: распределение пула прокси по профилям
- deep_clean_farm: глубокая очистка кэша всех аккаунтов
- run_export, run_import: работа с бэкапами
- check_proxy_pool: асинхронная проверка всех введенных прокси
"""

class ProxyCheckerWorker(QThread):
    progress_update = pyqtSignal(int, int) # current, total
    finished_check = pyqtSignal(list, list) # valid_proxies, invalid_proxies

    def __init__(self, proxies):
        super().__init__()
        self.proxies = proxies

    def run(self):
        valid = []
        invalid = []
        total = len(self.proxies)
        
        for i, proxy in enumerate(self.proxies):
            if logic.check_proxy_validity(proxy):
                valid.append(proxy)
            else:
                invalid.append(proxy)
            self.progress_update.emit(i + 1, total)
            
        self.finished_check.emit(valid, invalid)


class SettingsPage(QWidget):
    back_requested = pyqtSignal()
    settings_saved = pyqtSignal() # Сигнал для обновления UI (компактный режим)

    def __init__(self):
        super().__init__()
        self.docs_window = None
        self.proxy_worker = None
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(15)

        header_layout = QHBoxLayout()
        btn_back = QPushButton("← Назад")
        btn_back.setObjectName("BackBtn")
        btn_back.setFixedWidth(120)
        btn_back.clicked.connect(self.back_requested.emit)
        header_layout.addWidget(btn_back)

        header_layout.addStretch()

        btn_docs = QPushButton("📖 Документация")
        btn_docs.setFixedWidth(150)
        btn_docs.setStyleSheet("background-color: #0277bd; border: 1px solid #01579b;")
        btn_docs.clicked.connect(self.show_docs)
        header_layout.addWidget(btn_docs)

        main_layout.addLayout(header_layout)

        label_title = QLabel("Настройки")
        label_title.setObjectName("SettingsTitle")
        label_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #4caf50;")
        main_layout.addWidget(label_title)

        self.tabs = QTabWidget()
        
        # 1. API & AI
        tab_api = QWidget()
        l_api = QVBoxLayout(tab_api)
        l_api.addWidget(QLabel("API ID:", objectName="SettingLabel"))
        self.input_api_id = QLineEdit(); l_api.addWidget(self.input_api_id)
        l_api.addWidget(QLabel("API Hash:", objectName="SettingLabel"))
        self.input_api_hash = QLineEdit(); l_api.addWidget(self.input_api_hash)
        l_api.addWidget(QLabel("AI API Ключ (по умолчанию):", objectName="SettingLabel"))
        self.input_ai_api_key = QLineEdit(); self.input_ai_api_key.setEchoMode(QLineEdit.EchoMode.Password); l_api.addWidget(self.input_ai_api_key)
        l_api.addWidget(QLabel("AI Base URL (по умолчанию):", objectName="SettingLabel"))
        self.input_ai_base_url = QLineEdit(); l_api.addWidget(self.input_ai_base_url)
        l_api.addWidget(QLabel("AI Название модели (по умолчанию):", objectName="SettingLabel"))
        self.input_ai_model_name = QLineEdit(); l_api.addWidget(self.input_ai_model_name)
        l_api.addStretch()
        self.tabs.addTab(tab_api, "API & AI")

        # 2. Автоматизация и Безопасность
        tab_sec = QWidget()
        l_sec = QVBoxLayout(tab_sec)
        
        l_sec.addWidget(QLabel("Массовый запуск (Задержки):", objectName="SettingLabel"))
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Задержка между запусками Telegram (сек):"))
        self.spin_launch_delay = QSpinBox()
        self.spin_launch_delay.setRange(0, 60)
        self.spin_launch_delay.setValue(2)
        delay_layout.addWidget(self.spin_launch_delay)
        delay_layout.addStretch()
        l_sec.addLayout(delay_layout)

        l_sec.addSpacing(10)
        l_sec.addWidget(QLabel("Лимиты модулей:", objectName="SettingLabel"))
        
        flood_layout = QHBoxLayout()
        flood_layout.addWidget(QLabel("Макс. ожидание FloodWait (сек) (0 = ждать всегда):"))
        self.spin_flood_limit = QSpinBox()
        self.spin_flood_limit.setRange(0, 86400)
        self.spin_flood_limit.setValue(3600)
        flood_layout.addWidget(self.spin_flood_limit)
        flood_layout.addStretch()
        l_sec.addLayout(flood_layout)

        tasks_layout = QHBoxLayout()
        tasks_layout.addWidget(QLabel("Максимум одновременных задач в плагинах:"))
        self.spin_max_tasks = QSpinBox()
        self.spin_max_tasks.setRange(1, 100)
        self.spin_max_tasks.setValue(10)
        tasks_layout.addWidget(self.spin_max_tasks)
        tasks_layout.addStretch()
        l_sec.addLayout(tasks_layout)
        
        l_sec.addSpacing(10)
        l_sec.addWidget(QLabel("Поведение модулей:", objectName="SettingLabel"))
        self.cb_stealth_mode = QCheckBox("Режим Невидимки (+50% ко всем паузам в модулях)")
        l_sec.addWidget(self.cb_stealth_mode)
        
        l_sec.addStretch()
        self.tabs.addTab(tab_sec, "Автоматизация")

        # 3. Прокси Пул
        tab_proxy = QWidget()
        l_proxy = QVBoxLayout(tab_proxy)
        l_proxy.addWidget(QLabel("Пул прокси (по одному на строку, http/socks5):", objectName="SettingLabel"))
        self.text_proxy_pool = QTextEdit()
        self.text_proxy_pool.setPlaceholderText("socks5://user:pass@192.168.1.1:1080\nhttp://user:pass@10.0.0.1:8080")
        l_proxy.addWidget(self.text_proxy_pool)
        
        self.proxy_progress = QProgressBar()
        self.proxy_progress.setVisible(False)
        l_proxy.addWidget(self.proxy_progress)

        proxy_btns = QHBoxLayout()
        
        self.btn_check_pool = QPushButton("Проверить весь пул")
        self.btn_check_pool.setStyleSheet("background-color: #0288d1; color: white;")
        self.btn_check_pool.clicked.connect(self.check_proxy_pool)
        proxy_btns.addWidget(self.btn_check_pool)

        self.btn_distribute = QPushButton("Распределить прокси по аккаунтам")
        self.btn_distribute.setStyleSheet("background-color: #ff9800; color: white;")
        self.btn_distribute.clicked.connect(self.distribute_proxies)
        proxy_btns.addWidget(self.btn_distribute)
        
        l_proxy.addLayout(proxy_btns)
        self.tabs.addTab(tab_proxy, "Прокси")

        # 4. Обслуживание
        tab_maint = QWidget()
        l_maint = QVBoxLayout(tab_maint)
        
        l_maint.addWidget(QLabel("Очистка данных:", objectName="SettingLabel"))
        self.cb_auto_clean = QCheckBox("Автоматически чистить кэш профиля при закрытии Telegram")
        l_maint.addWidget(self.cb_auto_clean)
        
        log_layout = QHBoxLayout()
        log_layout.addWidget(QLabel("Очищать логи старше (дней):"))
        self.spin_log_days = QSpinBox()
        self.spin_log_days.setRange(1, 365)
        self.spin_log_days.setValue(7)
        log_layout.addWidget(self.spin_log_days)
        log_layout.addStretch()
        l_maint.addLayout(log_layout)
        
        l_maint.addSpacing(20)
        btn_clean_logs = QPushButton("Очистить устаревшие логи сейчас")
        btn_clean_logs.clicked.connect(self.clean_old_logs)
        l_maint.addWidget(btn_clean_logs)

        btn_deep_clean = QPushButton("Глубокая очистка кэша всей фермы")
        btn_deep_clean.setStyleSheet("background-color: #d32f2f; color: white;")
        btn_deep_clean.clicked.connect(self.deep_clean_farm)
        l_maint.addWidget(btn_deep_clean)

        l_maint.addSpacing(20)
        l_maint.addWidget(QLabel("Управление модулями:", objectName="SettingLabel"))
        btn_import_module = QPushButton("📥 Импорт нового модуля (.py)")
        btn_import_module.setStyleSheet("background-color: #00796b; color: white;")
        btn_import_module.clicked.connect(self.import_module)
        l_maint.addWidget(btn_import_module)

        l_maint.addStretch()
        self.tabs.addTab(tab_maint, "Данные и Обслуживание")

        # 5. Интерфейс
        tab_ui = QWidget()
        l_ui = QVBoxLayout(tab_ui)
        self.cb_compact_mode = QCheckBox("Компактный режим (уменьшенные строки аккаунтов)")
        l_ui.addWidget(self.cb_compact_mode)
        l_ui.addStretch()
        self.tabs.addTab(tab_ui, "Интерфейс")

        # 6. Бэкапы
        tab_backup = QWidget()
        l_backup = QVBoxLayout(tab_backup)
        l_backup.addWidget(QLabel("Управление резервными копиями:", objectName="SettingLabel"))
        
        btn_export = QPushButton("📤 Экспорт всех данных (ZIP)")
        btn_export.setFixedHeight(40)
        btn_export.clicked.connect(self.run_export)
        l_backup.addWidget(btn_export)

        btn_import = QPushButton("📥 Импорт из бэкапа (ZIP)")
        btn_import.setFixedHeight(40)
        btn_import.clicked.connect(self.run_import)
        l_backup.addWidget(btn_import)
        l_backup.addStretch()
        self.tabs.addTab(tab_backup, "Бэкапы")

        main_layout.addWidget(self.tabs)

        btn_save = QPushButton("💾 Сохранить настройки")
        btn_save.setFixedHeight(45)
        btn_save.setStyleSheet("background-color: #4caf50; font-weight: bold; font-size: 14px;")
        btn_save.clicked.connect(self.save_settings)
        main_layout.addWidget(btn_save)

    def show_docs(self):
        try:
            if self.docs_window is None:
                self.docs_window = DocsWindow()
            self.docs_window.show()
            self.docs_window.raise_()
            self.docs_window.activateWindow()
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть документацию: {e}")

    def load_settings(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f: data = json.load(f)
                s = data.get("settings", {})
                
                # API
                self.input_api_id.setText(str(s.get("api_id", "")))
                self.input_api_hash.setText(s.get("api_hash", ""))
                self.input_ai_api_key.setText(s.get("default_ai_api_key", ""))
                self.input_ai_base_url.setText(s.get("default_ai_base_url", "https://api.groq.com/openai/v1"))
                self.input_ai_model_name.setText(s.get("default_ai_model_name", "llama-3.1-8b-instant"))
                
                # Security & Automation
                self.spin_launch_delay.setValue(s.get("launch_delay", 2))
                self.spin_flood_limit.setValue(s.get("max_flood_wait", 3600))
                self.spin_max_tasks.setValue(s.get("max_concurrent_tasks", 10))
                self.cb_stealth_mode.setChecked(s.get("stealth_mode", False))
                
                # Maintenance & UI
                self.cb_auto_clean.setChecked(s.get("auto_clean_cache", False))
                self.spin_log_days.setValue(s.get("log_rotation_days", 7))
                self.cb_compact_mode.setChecked(s.get("compact_mode", False))
                
        except: pass

    def save_settings(self):
        try:
            data = {"settings": {}, "accounts": []}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f: data = json.load(f)
            
            data["settings"].update({
                "api_id": int(self.input_api_id.text()) if self.input_api_id.text().isdigit() else 0, 
                "api_hash": self.input_api_hash.text().strip(),
                "default_ai_api_key": self.input_ai_api_key.text().strip(),
                "default_ai_base_url": self.input_ai_base_url.text().strip(),
                "default_ai_model_name": self.input_ai_model_name.text().strip(),
                "launch_delay": self.spin_launch_delay.value(),
                "max_flood_wait": self.spin_flood_limit.value(),
                "max_concurrent_tasks": self.spin_max_tasks.value(),
                "stealth_mode": self.cb_stealth_mode.isChecked(),
                "auto_clean_cache": self.cb_auto_clean.isChecked(),
                "log_rotation_days": self.spin_log_days.value(),
                "compact_mode": self.cb_compact_mode.isChecked()
            })
            with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)
            self.settings_saved.emit()
            QMessageBox.information(self, "Успех", "Настройки сохранены!")
        except Exception as e: QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {e}")

    def check_proxy_pool(self):
        proxies_text = self.text_proxy_pool.toPlainText().strip()
        if not proxies_text:
            QMessageBox.warning(self, "Ошибка", "Пул прокси пуст!")
            return
            
        proxies = [p.strip() for p in proxies_text.split('\n') if p.strip()]
        
        self.btn_check_pool.setEnabled(False)
        self.btn_distribute.setEnabled(False)
        self.proxy_progress.setVisible(True)
        self.proxy_progress.setMaximum(len(proxies))
        self.proxy_progress.setValue(0)
        
        self.proxy_worker = ProxyCheckerWorker(proxies)
        self.proxy_worker.progress_update.connect(self.proxy_progress.setValue)
        self.proxy_worker.finished_check.connect(self.on_pool_checked)
        self.proxy_worker.start()

    def on_pool_checked(self, valid, invalid):
        self.btn_check_pool.setEnabled(True)
        self.btn_distribute.setEnabled(True)
        self.proxy_progress.setVisible(False)
        
        if not valid:
            QMessageBox.critical(self, "Результат", f"Все {len(invalid)} прокси из пула оказались нерабочими!")
            return
            
        # Оставляем в текстовом поле только рабочие прокси
        self.text_proxy_pool.setPlainText('\n'.join(valid))
        
        msg = f"Проверка завершена!\n\nРабочих: {len(valid)}\nМертвых: {len(invalid)}"
        if invalid:
            msg += "\n\nМертвые прокси были удалены из списка."
            
        QMessageBox.information(self, "Результат", msg)

    def distribute_proxies(self):
        proxies_text = self.text_proxy_pool.toPlainText().strip()
        if not proxies_text:
            QMessageBox.warning(self, "Ошибка", "Пул прокси пуст!")
            return
            
        proxies = [p.strip() for p in proxies_text.split('\n') if p.strip()]
        
        reply = QMessageBox.question(self, "Распределение", f"Найдено {len(proxies)} прокси. Перемешать и распределить их по всем профилям?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                data = {"settings": {}, "accounts": []}
                if os.path.exists(CONFIG_FILE):
                    with open(CONFIG_FILE, "r", encoding="utf-8") as f: data = json.load(f)
                
                accounts = data.get("accounts", [])
                if not accounts:
                    QMessageBox.warning(self, "Ошибка", "Нет созданных аккаунтов!")
                    return

                random.shuffle(proxies)
                proxy_count = len(proxies)
                
                updated = 0
                for i, acc in enumerate(accounts):
                    acc["proxy_url"] = proxies[i % proxy_count]
                    updated += 1
                
                with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(data, f, indent=4, ensure_ascii=False)
                
                self.text_proxy_pool.clear() # Очищаем поле после успешного распределения
                QMessageBox.information(self, "Готово", f"Прокси успешно распределены по {updated} аккаунтам. Обновите список на главной.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))

    def clean_old_logs(self):
        days = self.spin_log_days.value()
        cutoff = datetime.now() - timedelta(days=days)
        deleted = 0
        
        try:
            data = logic.load_config(CONFIG_FILE)
            for acc in data:
                workdir = acc.get("workdir")
                if not workdir or not os.path.exists(workdir): continue
                
                for filename in ["telegram_error.log", "gost_module.log"]:
                    filepath = os.path.join(workdir, filename)
                    if os.path.exists(filepath):
                        mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                        if mtime < cutoff:
                            os.remove(filepath)
                            deleted += 1
                            
            QMessageBox.information(self, "Готово", f"Удалено {deleted} старых файлов логов.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def deep_clean_farm(self):
        reply = QMessageBox.question(self, "Глубокая очистка", "Вы уверены, что хотите удалить кэш и временные файлы из ВСЕХ профилей? Это может занять время.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                data = {"settings": {}, "accounts": []}
                if os.path.exists(CONFIG_FILE):
                    with open(CONFIG_FILE, "r", encoding="utf-8") as f: data = json.load(f)
                
                accounts = data.get("accounts", [])
                total_cleaned = 0
                
                for acc in accounts:
                    success, _ = logic.clear_cache(acc["workdir"])
                    if success:
                        total_cleaned += 1
                
                QMessageBox.information(self, "Готово", f"Глубокая очистка завершена.\nОчищено профилей: {total_cleaned}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))

    def run_export(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить бэкап", f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip", "ZIP Files (*.zip)")
        if file_path:
            success, msg = logic.export_backup(CONFIG_FILE, file_path)
            if success: QMessageBox.information(self, "Бэкап", msg)
            else: QMessageBox.critical(self, "Ошибка", msg)

    def run_import(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите бэкап", "", "ZIP Files (*.zip)")
        if file_path:
            reply = QMessageBox.warning(self, "Внимание", "Импорт перезапишет текущий список. Продолжить?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                success, msg = logic.import_backup(file_path, CONFIG_FILE)
                if success: QMessageBox.information(self, "Бэкап", msg)
                else: QMessageBox.critical(self, "Ошибка", msg)

    def import_module(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите файл модуля Python", "", "Python Files (*.py)")
        if file_path:
            try:
                dest_dir = os.path.join(os.getcwd(), "src", "modules", "plugins")
                os.makedirs(dest_dir, exist_ok=True)
                dest_path = os.path.join(dest_dir, os.path.basename(file_path))
                
                shutil.copy2(file_path, dest_path)
                QMessageBox.information(self, "Успех", f"Модуль успешно импортирован!\nПерейдите в 'Модули' и обновите список.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось скопировать модуль: {e}")