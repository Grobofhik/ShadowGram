from src.core.constants import *
from PyQt6.QtGui import QIcon
import asyncio
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QScrollArea, QFrame, QTextBrowser,
                             QLineEdit, QSplitter, QGraphicsDropShadowEffect, QSizePolicy,
                             QStackedWidget)
from PyQt6.QtGui import QColor, QFont, QIcon, QCursor
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from pathlib import Path
import sqlite3

from src import styles
from src.core.logger import logger
from src.core.constants import CONFIG_FILE
from src.core.managers import config_manager
from src.core.events import get_event_bus
from src.ai_agents.ai_runner import AIRunner

class AIFetchStateThread(QThread):
    finished = pyqtSignal(object)
    
    def __init__(self, runner_instance):
        super().__init__()
        self.runner_instance = runner_instance
        
    def run(self):
        try:
            farm_state = asyncio.run(self.runner_instance.get_farm_state(force_refresh=True))
            self.finished.emit(farm_state)
        except Exception as e:
            logger.error(f"Error fetching state: {e}")
            self.finished.emit({})

class AIChatThread(QThread):
    finished = pyqtSignal(str, object, object, object)
    error = pyqtSignal(str)

    def __init__(self, api_key, base_url, model, user_message, runner_instance=None):
        super().__init__()
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.user_message = user_message
        self.runner_instance = runner_instance

    def run(self):
        try:
            if not self.runner_instance:
                self.runner_instance = AIRunner(api_key=self.api_key, api_base_url=self.base_url, model_name=self.model)
            bot_msg, plan, mutations, farm_state = asyncio.run(self.runner_instance.chat_async(self.user_message))
            self.finished.emit(bot_msg, plan, mutations, farm_state)
        except Exception as e:
            self.error.emit(str(e))

class AIExecuteThread(QThread):
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, plan, mutations, runner_instance):
        super().__init__()
        self.plan = plan
        self.mutations = mutations
        self.runner_instance = runner_instance

    def run(self):
        try:
            asyncio.run(self.runner_instance.execute_plan_async(self.plan, self.mutations))
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class StatCard(QFrame):
    def __init__(self, title, value, color):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {styles.COLOR_ACCENT_BG};
                border-left: 4px solid {color};
                border-radius: 6px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(4)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 12px; font-weight: bold; text-transform: uppercase;")
        
        self.lbl_value = QLabel(str(value))
        self.lbl_value.setStyleSheet(f"color: {styles.COLOR_TEXT_MAIN}; font-size: 24px; font-weight: bold;")
        
        layout.addWidget(lbl_title)
        layout.addWidget(self.lbl_value)
        
    def set_value(self, val):
        self.lbl_value.setText(str(val))

class AIPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_plan = None
        self.current_mutations = None
        self.ai_runner = None
        self.init_ui()
        self._init_runner()

    def _init_runner(self):
        api_key, base_url, model = self._get_api_creds()
        if api_key:
            self.ai_runner = AIRunner(api_key=api_key, api_base_url=base_url, model_name=model)
            self._add_bot_message("👋 **Привет! Я твой ИИ-Оркестратор.**\nЯ проанализировал ферму. Опиши мне задачу (например, *«настрой био и запусти прогрев»*).")
            
            self.state_thread = AIFetchStateThread(self.ai_runner)
            self.state_thread.finished.connect(self._update_dashboard)
            self.state_thread.start()
        else:
            self._add_bot_message(" Ошибка: Ключ API не настроен в конфигурации.")

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {styles.COLOR_BORDER_DARK}; width: 1px; }}")

        # ==========================================
        # === LEFT PANEL: DASHBOARD & PLAN VIEWER ===
        # ==========================================
        left_container = QWidget()
        left_container.setStyleSheet(f"background-color: {styles.COLOR_BG};")
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(25, 25, 25, 25)
        left_layout.setSpacing(20)

        # Header
        header = QLabel("Панель Оркестратора")
        header.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {styles.COLOR_TEXT_MAIN};")
        left_layout.addWidget(header)

        # -- DASHBOARD --
        dashboard_layout = QHBoxLayout()
        dashboard_layout.setSpacing(15)
        
        self.card_total = StatCard("Всего аккаунтов", "-", styles.COLOR_TEXT_MUTED)
        self.card_active = StatCard("С аватарами", "-", styles.COLOR_INFO)
        self.card_bio = StatCard("С описанием", "-", styles.COLOR_WARNING)
        self.card_privacy = StatCard("Безопасность", "-", styles.COLOR_SUCCESS)
        
        dashboard_layout.addWidget(self.card_total)
        dashboard_layout.addWidget(self.card_active)
        dashboard_layout.addWidget(self.card_bio)
        dashboard_layout.addWidget(self.card_privacy)
        left_layout.addLayout(dashboard_layout)

        # -- TABS: PLAN VIEWER vs LOGS --
        tabs_layout = QHBoxLayout()
        tabs_layout.setContentsMargins(0, 15, 0, 5)
        tabs_layout.setSpacing(10)

        self.btn_tab_plan = QPushButton("План выполнения")
        self.btn_tab_plan.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_tab_plan.setCheckable(True)
        self.btn_tab_plan.setChecked(True)
        self.btn_tab_plan.setFixedHeight(30)
        
        self.btn_tab_logs = QPushButton("Активные логи")
        self.btn_tab_logs.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_tab_logs.setCheckable(True)
        self.btn_tab_logs.setFixedHeight(30)

        tab_btn_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {styles.COLOR_TEXT_MUTED};
                border: none;
                font-size: 16px;
                font-weight: bold;
                padding-bottom: 5px;
            }}
            QPushButton:checked {{
                color: {styles.COLOR_PRIMARY};
                border-bottom: 2px solid {styles.COLOR_PRIMARY};
            }}
            QPushButton:hover:!checked {{
                color: {styles.COLOR_TEXT_MAIN};
            }}
        """
        self.btn_tab_plan.setStyleSheet(tab_btn_style)
        self.btn_tab_logs.setStyleSheet(tab_btn_style)

        tabs_layout.addWidget(self.btn_tab_plan)
        tabs_layout.addWidget(self.btn_tab_logs)
        tabs_layout.addStretch()

        left_layout.addLayout(tabs_layout)

        self.stacked_widget = QStackedWidget()

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: transparent;
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 8px;
            }}
        """)

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background-color: transparent;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.cards_layout.setSpacing(10)
        self.scroll_area.setWidget(self.cards_container)
        
        self.stacked_widget.addWidget(self.scroll_area)

        # -- LOGS TEXT BROWSER --
        self.logs_browser = QTextBrowser()
        self.logs_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {styles.COLOR_CONSOLE_BG};
                color: {styles.COLOR_TEXT_MAIN};
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 8px;
                font-size: 13px;
                font-family: monospace;
                padding: 10px;
            }}
        """)
        self.stacked_widget.addWidget(self.logs_browser)

        left_layout.addWidget(self.stacked_widget)

        self.btn_tab_plan.clicked.connect(lambda: self._switch_tab(0))
        self.btn_tab_logs.clicked.connect(lambda: self._switch_tab(1))

        # Connect event bus to logs
        get_event_bus().ai_log_message.connect(self._add_live_log)

        self.empty_label = QLabel("Нет активных задач. Запросите генерацию плана у агента.")
        self.empty_label.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 14px; padding: 20px;")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cards_layout.addWidget(self.empty_label)

        self.btn_execute = QPushButton("Утвердить и Запустить план")
        self.btn_execute.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_execute.setEnabled(False)
        self.btn_execute.setFixedHeight(45)
        self.btn_execute.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.COLOR_PRIMARY};
                color: {styles.COLOR_BG};
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {styles.COLOR_PRIMARY_LIGHT}; }}
            QPushButton:disabled {{ background-color: {styles.COLOR_BORDER}; color: {styles.COLOR_TEXT_MUTED}; }}
        """)
        self.btn_execute.clicked.connect(self.execute_plan)
        left_layout.addWidget(self.btn_execute)

        splitter.addWidget(left_container)

        # ==========================================
        # === RIGHT PANEL: AI CHAT SIDEBAR ===
        # ==========================================
        chat_container = QWidget()
        chat_container.setStyleSheet(f"""
            QWidget {{
                background-color: {styles.COLOR_CONSOLE_BG};
            }}
        """)
        chat_layout = QVBoxLayout(chat_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)

        # Chat header
        chat_top = QLabel("AI Ассистент")
        chat_top.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chat_top.setStyleSheet(f"""
            QLabel {{
                background-color: {styles.COLOR_ACCENT_BG};
                font-size: 15px; 
                font-weight: bold; 
                color: {styles.COLOR_TEXT_MAIN}; 
                padding: 15px;
                border-bottom: 1px solid {styles.COLOR_BORDER};
            }}
        """)
        chat_layout.addWidget(chat_top)

        # Chat history
        self.chat_history = QTextBrowser()
        self.chat_history.setOpenLinks(False)
        self.chat_history.anchorClicked.connect(self._on_anchor_clicked)
        self.chat_history.setStyleSheet(f"""
            QTextBrowser {{
                background-color: transparent;
                color: {styles.COLOR_TEXT_MAIN};
                border: none;
                font-size: 14px;
                line-height: 1.6;
                padding: 15px;
            }}
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {styles.COLOR_BORDER};
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {styles.COLOR_TEXT_MUTED};
            }}
        """)
        chat_layout.addWidget(self.chat_history)

        # Chat input area
        input_container = QFrame()
        input_container.setStyleSheet(f"""
            QFrame {{
                background-color: {styles.COLOR_ACCENT_BG};
                border-top: 1px solid {styles.COLOR_BORDER};
                padding: 10px;
            }}
        """)
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(10, 5, 10, 5)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Опишите задачу...")
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {styles.COLOR_BG};
                color: {styles.COLOR_TEXT_MAIN};
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 6px;
                padding: 10px 15px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {styles.COLOR_PRIMARY};
            }}
        """)
        self.input_field.returnPressed.connect(self.send_message)
        
        self.btn_send = QPushButton("Отправить")
        self.btn_send.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_send.setFixedHeight(40)
        self.btn_send.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {styles.COLOR_PRIMARY};
                font-weight: bold;
                font-size: 14px;
                padding: 0 15px;
                border: none;
            }}
            QPushButton:hover {{ color: {styles.COLOR_PRIMARY_LIGHT}; }}
            QPushButton:disabled {{ color: {styles.COLOR_TEXT_MUTED}; }}
        """)
        self.btn_send.clicked.connect(self.send_message)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.btn_send)
        chat_layout.addWidget(input_container)
        
        splitter.addWidget(chat_container)
        
        # Set stretch factors (65% Left, 35% Right)
        splitter.setStretchFactor(0, 65)
        splitter.setStretchFactor(1, 35)

        main_layout.addWidget(splitter)

    def _get_api_creds(self):
        config_data = config_manager._read_config(Path(CONFIG_FILE))
        settings = config_data.get("settings", {})
        api_key = settings.get("default_ai_api_key", "")
        base_url = settings.get("default_ai_base_url", "")
        model = settings.get("default_ai_model_name", "")
        return api_key, base_url, model

    def _update_dashboard(self, farm_state: dict):
        if not farm_state:
            return
            
        total = len(farm_state)
        avatars = sum(1 for s in farm_state.values() if s.get("has_avatar", False))
        bios = sum(1 for s in farm_state.values() if s.get("bio"))
        secure = sum(1 for s in farm_state.values() if s.get("has_2fa") or s.get("privacy_setup"))
        
        self.card_total.set_value(total)
        self.card_active.set_value(avatars)
        self.card_bio.set_value(bios)
        self.card_privacy.set_value(secure)

    def _format_md(self, text: str):
        import re
        import urllib.parse
        
        # Сначала вытаскиваем все многострочные блоки
        blocks = []
        def save_block(match):
            code = match.group(1)
            # Убираем первую строку с названием языка (если есть)
            first_line_end = code.find('\n')
            if first_line_end != -1 and not ' ' in code[:first_line_end]:
                code = code[first_line_end+1:]
            
            code = code.strip()
            encoded_code = urllib.parse.quote(code)
            display_code = code.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
            
            block_html = f'''
            <div style="background-color: #1E293B; border: 1px solid #334155; border-radius: 6px; margin: 10px 0;">
                <div style="background-color: #0F172A; padding: 5px 10px; border-top-left-radius: 6px; border-top-right-radius: 6px; text-align: right;">
                    <a href="copy:{encoded_code}" style="color: #3B82F6; text-decoration: none; font-size: 12px; font-weight: bold;">📋 Копировать</a>
                </div>
                <div style="padding: 10px; font-family: monospace; color: #E2E8F0;">
                    {display_code}
                </div>
            </div>
            '''
            blocks.append(block_html)
            return f"__CODE_BLOCK_{len(blocks)-1}__"

        text = re.sub(r'```(.*?)```', save_block, text, flags=re.DOTALL)
        
        # Теперь безопасно заменяем \n на <br> для остального текста
        html = text.replace('\n', '<br>')
        
        # Возвращаем блоки на место
        for i, block_html in enumerate(blocks):
            html = html.replace(f"__CODE_BLOCK_{i}__", block_html)
            
        html = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', html)
        html = re.sub(r'\*(.*?)\*', r'<i>\1</i>', html)
        html = re.sub(r'`(.*?)`', r'<code style="color: #E2E8F0; background-color: #1E293B; padding: 2px 4px; border-radius: 4px; font-family: monospace;">\1</code>', html)
        return html

    def _switch_tab(self, index: int):
        self.stacked_widget.setCurrentIndex(index)
        self.btn_tab_plan.setChecked(index == 0)
        self.btn_tab_logs.setChecked(index == 1)

    def _add_live_log(self, text: str):
        # Format logs for better readability in the terminal-like view
        import html
        escaped_text = html.escape(text)
        
        # Add color based on keywords
        color = styles.COLOR_TEXT_MAIN
        if ""in text or "error"in text.lower():
            color = styles.COLOR_DANGER
        elif ""in text or "success"in text.lower():
            color = styles.COLOR_SUCCESS
        elif ""in text or "warning"in text.lower():
            color = styles.COLOR_WARNING
        elif ""in text or "[Фаза"in text:
            color = styles.COLOR_INFO
            
        styled_text = f"<span style='color: {color};'>{escaped_text}</span>"
        self.logs_browser.append(styled_text)
        
        # Scroll to bottom
        scrollbar = self.logs_browser.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _add_user_message(self, text: str):
        html = f"""
        <div style="margin: 8px 0; text-align: right;">
            <div style="background-color: {styles.COLOR_HOVER_BG}; color: {styles.COLOR_TEXT_MAIN}; padding: 10px 14px; border-radius: 8px; font-size: 14px; display: inline-block; max-width: 85%; text-align: left; border: 1px solid {styles.COLOR_BORDER};">
                {self._format_md(text)}
            </div>
        </div>
        """
        self.chat_history.append(html)

    def _on_anchor_clicked(self, url):
        import urllib.parse
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtWidgets import QApplication
        
        url_str = url.toString()
        if url_str.startswith("copy:"):
            text_to_copy = urllib.parse.unquote(url_str[5:])
            QApplication.clipboard().setText(text_to_copy)
        else:
            QDesktopServices.openUrl(url)

    def _add_bot_message(self, text: str):
        html = f"""
        <div style="margin: 8px 0; text-align: left;">
            <div style="background-color: transparent; color: {styles.COLOR_TEXT_MAIN}; padding: 10px 0; font-size: 14px; display: inline-block; max-width: 95%;">
                 {self._format_md(text)}
            </div>
        </div>
        """
        self.chat_history.append(html)

    def send_message(self):
        text = self.input_field.text().strip()
        if not text:
            return
            
        if not self.ai_runner:
            self._add_bot_message(" Ключ API не настроен.")
            return

        self._add_user_message(text)
        self.input_field.clear()
        self.input_field.setEnabled(False)
        self.btn_send.setEnabled(False)
        
        api_key, base_url, model = self._get_api_creds()
        self.chat_thread = AIChatThread(api_key, base_url, model, text, self.ai_runner)
        self.chat_thread.finished.connect(self._on_chat_finished)
        self.chat_thread.error.connect(self._on_chat_error)
        self.chat_thread.start()
        
        self._add_bot_message("<span style='color: #64748B;'>Анализирую и составляю план...</span>")

    def _on_chat_finished(self, bot_msg: str, plan: list, mutations: list, farm_state: dict):
        self.input_field.setEnabled(True)
        self.btn_send.setEnabled(True)
        self.input_field.setFocus()
        
        self._update_dashboard(farm_state)
        
        self._add_bot_message(bot_msg)
        
        self.current_plan = plan if plan else []
        self.current_mutations = mutations if mutations else []
        
        if self.current_plan or self.current_mutations:
            self._render_plan_cards(self.current_plan, self.current_mutations)
            self.btn_execute.setEnabled(True)
        else:
            self._render_plan_cards([], [])

    def _on_chat_error(self, error_str: str):
        self.input_field.setEnabled(True)
        self.btn_send.setEnabled(True)
        self._add_bot_message(f"<span style='color: {styles.COLOR_DANGER};'>Ошибка: {error_str}</span>")

    def execute_plan(self):
        if not self.current_plan and not self.current_mutations:
            return
            
        self.btn_execute.setEnabled(False)
        self.input_field.setEnabled(False)
        self.btn_send.setEnabled(False)
        
        self._add_user_message("Утвердить и выполнить план.")
        self._add_bot_message("Инициализация рабочих потоков. Запуск...")
        
        self.exec_thread = AIExecuteThread(self.current_plan, self.current_mutations, self.ai_runner)
        self.exec_thread.finished.connect(self._on_exec_finished)
        self.exec_thread.error.connect(self._on_exec_error)
        self.exec_thread.start()

    def _on_exec_finished(self):
        self.btn_execute.setEnabled(False)
        self.input_field.setEnabled(True)
        self.btn_send.setEnabled(True)
        self.current_plan = None
        self.current_mutations = None
        self._render_plan_cards([], [])
        self._add_bot_message(" План успешно выполнен.")
        
        self.state_thread = AIFetchStateThread(self.ai_runner)
        self.state_thread.finished.connect(self._update_dashboard)
        self.state_thread.start()

    def _on_exec_error(self, error_str: str):
        self.btn_execute.setEnabled(True)
        self.input_field.setEnabled(True)
        self.btn_send.setEnabled(True)
        self._add_bot_message(f"<span style='color: {styles.COLOR_DANGER};'>Сбой выполнения: {error_str}</span>")

    def _show_message_in_cards(self, message: str, is_error: bool = False):
        for i in reversed(range(self.cards_layout.count())):
            widget = self.cards_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                
        lbl = QLabel(message)
        lbl.setWordWrap(True)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        color = styles.COLOR_DANGER if is_error else styles.COLOR_TEXT_MUTED
        lbl.setStyleSheet(f"color: {color}; font-size: 14px; padding: 20px;")
        self.cards_layout.addWidget(lbl)

    def _render_plan_cards(self, plan: list, mutations: list):
        for i in reversed(range(self.cards_layout.count())):
            widget = self.cards_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                
        if not plan and not mutations:
            self._show_message_in_cards("План пуст. Ожидание команд...")
            return

        # Render Mutations first
        if mutations:
            mut_card = QFrame()
            mut_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {styles.COLOR_ACCENT_BG};
                    border: 1px solid {styles.COLOR_INFO};
                    border-radius: 8px;
                }}
            """)
            mut_layout = QVBoxLayout(mut_card)
            mut_layout.setContentsMargins(15, 10, 15, 10)
            
            lbl_mut = QLabel("🔧 <b>Прямые изменения конфига (Config Mutations)</b>")
            lbl_mut.setStyleSheet(f"color: {styles.COLOR_INFO}; font-size: 14px; border: none;")
            mut_layout.addWidget(lbl_mut)
            
            from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
            
            table = QTableWidget()
            # Calculate total rows needed (each change per mutation is a row)
            total_rows = sum(len(m.get("changes", {})) for m in mutations)
            table.setRowCount(total_rows)
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["Аккаунты", "Параметр", "Новое значение"])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            table.verticalHeader().setVisible(False)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setStyleSheet(f"""
                QTableWidget {{
                    background-color: {styles.COLOR_BG};
                    color: {styles.COLOR_TEXT_MAIN};
                    border: 1px solid {styles.COLOR_BORDER};
                    border-radius: 4px;
                    gridline-color: {styles.COLOR_BORDER};
                }}
                QHeaderView::section {{
                    background-color: {styles.COLOR_BORDER_DARK};
                    color: {styles.COLOR_TEXT_MAIN};
                    padding: 4px;
                    border: 1px solid {styles.COLOR_BORDER};
                    font-weight: bold;
                }}
            """)
            
            current_row = 0
            for m in mutations:
                w_str = ", ".join(m.get("workdirs", []))
                for key, val in m.get("changes", {}).items():
                    item_w = QTableWidgetItem(w_str)
                    item_k = QTableWidgetItem(key)
                    item_v = QTableWidgetItem(str(val))
                    
                    table.setItem(current_row, 0, item_w)
                    table.setItem(current_row, 1, item_k)
                    table.setItem(current_row, 2, item_v)
                    current_row += 1
            
            table.setMinimumHeight(min(200, 40 + total_rows * 30))
            mut_layout.addWidget(table)
            
            self.cards_layout.addWidget(mut_card)

        for acc_plan in plan:
            workdir = acc_plan.get("workdir", "")
            acc_name = Path(workdir).name if workdir else "Неизвестно"
            schedule = acc_plan.get("schedule", [])
            
            if not schedule:
                continue

            # Card for the account
            acc_card = QFrame()
            acc_card.setStyleSheet(f"""
                QFrame {{
                    background-color: {styles.COLOR_ACCENT_BG};
                    border: 1px solid {styles.COLOR_BORDER};
                    border-radius: 8px;
                }}
            """)
            acc_layout = QVBoxLayout(acc_card)
            acc_layout.setContentsMargins(0, 0, 0, 0)
            acc_layout.setSpacing(0)

            # Account Header (Darker/distinct background)
            header = QFrame()
            header.setStyleSheet(f"""
                QFrame {{
                    background-color: {styles.COLOR_BORDER_DARK};
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                }}
            """)
            header_layout = QHBoxLayout(header)
            header_layout.setContentsMargins(15, 10, 15, 10)
            
            lbl_acc = QLabel(f"📱 <b>{acc_name}</b>")
            lbl_acc.setStyleSheet(f"color: {styles.COLOR_TEXT_MAIN}; font-size: 14px; border: none;")
            
            lbl_count = QLabel(f"{len(schedule)} задач")
            lbl_count.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 12px; border: none; font-weight: bold;")
            
            header_layout.addWidget(lbl_acc)
            header_layout.addStretch()
            header_layout.addWidget(lbl_count)
            acc_layout.addWidget(header)

            # Timeline of tasks
            timeline_container = QWidget()
            timeline_layout = QVBoxLayout(timeline_container)
            timeline_layout.setContentsMargins(15, 10, 15, 15)
            timeline_layout.setSpacing(8)
            
            for idx, task_item in enumerate(schedule):
                task = task_item.get("action", "UNKNOWN")
                delay = task_item.get("delay_after_sec", 0)
                
                if task == "DELAY" and not delay:
                    continue
                    
                task_color = styles.COLOR_PRIMARY
                icon = ""
                reason = f"Ожидание: {delay}с"
                
                task_lower = task.lower()
                if "bio" in task_lower or "avatar" in task_lower or "privacy" in task_lower or "2fa" in task_lower:
                    task_color = styles.COLOR_WARNING
                    icon = "👤"
                    reason = "Оформление / Безопасность"
                elif "channel" in task_lower:
                    task_color = styles.COLOR_INFO
                    icon = "📢"
                    reason = "Работа с каналом"
                elif "username" in task_lower:
                    task_color = styles.COLOR_WARNING
                    icon = ""
                    reason = "Смена юзернейма"
                elif "warmup" in task_lower:
                    task_color = "#F59E0B"
                    icon = ""
                    reason = "Умный прогрев"
                elif "comment" in task_lower:
                    task_color = "#3B82F6"
                    icon = "💬"
                    reason = "Нейрокомментинг"
                elif task == "DELAY":
                    task_color = styles.COLOR_TEXT_MUTED
                    icon = "⏱"
                    reason = "Пауза"

                task_row = QWidget()
                row_layout = QHBoxLayout(task_row)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(10)
                
                # Step number or indicator
                step_indicator = QLabel(str(idx + 1))
                step_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
                step_indicator.setFixedSize(24, 24)
                step_indicator.setStyleSheet(f"""
                    QLabel {{
                        background-color: {styles.COLOR_BG};
                        color: {styles.COLOR_TEXT_MUTED};
                        border: 1px solid {styles.COLOR_BORDER};
                        border-radius: 12px;
                        font-size: 11px;
                        font-weight: bold;
                    }}
                """)
                
                # Task Pill
                task_lbl = QLabel(f"{icon} {task}")
                task_lbl.setStyleSheet(f"""
                    QLabel {{
                        background-color: {task_color}15;
                        color: {task_color};
                        border: 1px solid {task_color}40;
                        border-radius: 4px;
                        padding: 4px 8px;
                        font-size: 12px;
                        font-weight: bold;
                    }}
                """)
                
                # Reason / Info
                reason_lbl = QLabel(reason)
                reason_lbl.setStyleSheet(f"color: {styles.COLOR_TEXT_MAIN}; font-size: 13px;")
                reason_lbl.setWordWrap(True)
                
                row_layout.addWidget(step_indicator)
                row_layout.addWidget(task_lbl)
                row_layout.addWidget(reason_lbl, stretch=1)
                
                timeline_layout.addWidget(task_row)

            acc_layout.addWidget(timeline_container)
            self.cards_layout.addWidget(acc_card)
