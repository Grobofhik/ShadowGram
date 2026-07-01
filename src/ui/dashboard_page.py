import os
import sqlite3
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QGridLayout, QScrollArea, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QIcon
import pyqtgraph as pg

from src.core.managers import farm_manager
from src import styles

class StatCard(QFrame):
    def __init__(self, title, value_text, color, subtitle=""):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {styles.COLOR_ACCENT_BG};
                border-radius: 10px;
                border: 1px solid {styles.COLOR_BORDER};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 13px; font-weight: bold; border: none;")
        
        self.val_lbl = QLabel(value_text)
        self.val_lbl.setStyleSheet(f"color: {color}; font-size: 32px; font-weight: bold; border: none; margin-top: 5px;")
        
        layout.addWidget(title_lbl)
        layout.addWidget(self.val_lbl)
        
        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setStyleSheet(f"color: {styles.COLOR_TEXT_DISABLED}; font-size: 11px; border: none;")
            layout.addWidget(sub_lbl)
            
        layout.addStretch()

    def update_value(self, text):
        self.val_lbl.setText(str(text))

class DashboardPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_data()
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.load_data)
        self.timer.start(10000) # Обновление каждые 10 секунд
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 20, 30, 20)
        main_layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        header = QLabel("Аналитика & Статистика (SQLite Mirror)")
        header.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {styles.COLOR_TEXT_MAIN};")
        header_layout.addWidget(header)
        
        desc = QLabel("Данные синхронизируются из БД в реальном времени.")
        desc.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 12px;")
        header_layout.addStretch()
        header_layout.addWidget(desc)
        main_layout.addLayout(header_layout)
        
        # Первая линия карточек
        cards_layout1 = QHBoxLayout()
        self.card_total = StatCard("Всего аккаунтов на ферме", "0", styles.COLOR_TEXT_MAIN, "В базе SQLite")
        self.card_actions = StatCard("Событий (За 24ч)", "0", styles.COLOR_INFO, "Записи логов/действий")
        self.card_comments = StatCard("Успешных комментариев", "0", styles.COLOR_SUCCESS, "Оставлено нейросетью")
        
        cards_layout1.addWidget(self.card_total)
        cards_layout1.addWidget(self.card_actions)
        cards_layout1.addWidget(self.card_comments)
        main_layout.addLayout(cards_layout1)

        # Вторая линия карточек
        cards_layout2 = QHBoxLayout()
        self.card_warmups = StatCard("Авто-прогревов", "0", styles.COLOR_WARNING, "Успешно выполненных циклов")
        self.card_banned = StatCard("Заблокировано", "0", styles.COLOR_DANGER, "В спам-блоке или забанено")
        self.card_errors = StatCard("Ошибки (За 24ч)", "0", styles.COLOR_DANGER, "Неудачные попытки API")
        
        cards_layout2.addWidget(self.card_warmups)
        cards_layout2.addWidget(self.card_banned)
        cards_layout2.addWidget(self.card_errors)
        main_layout.addLayout(cards_layout2)
        
        # Graph
        graph_frame = QFrame()
        graph_frame.setStyleSheet(f"background-color: {styles.COLOR_ACCENT_BG}; border-radius: 10px; border: 1px solid {styles.COLOR_BORDER};")
        graph_layout = QVBoxLayout(graph_frame)
        
        lbl = QLabel("График активности аккаунтов (за сутки)")
        lbl.setStyleSheet(f"color: {styles.COLOR_TEXT_MAIN}; font-size: 16px; font-weight: bold; border: none; margin-bottom: 10px;")
        graph_layout.addWidget(lbl)
        
        pg.setConfigOption('background', styles.COLOR_ACCENT_BG)
        pg.setConfigOption('foreground', styles.COLOR_TEXT_MAIN)
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setStyleSheet("border: none;")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        
        # Настройка осей
        self.plot_widget.setLabel('left', 'Действия')
        self.plot_widget.setLabel('bottom', 'Часы')
        
        graph_layout.addWidget(self.plot_widget)
        main_layout.addWidget(graph_frame, stretch=1)
        
    def load_data(self):
        farm_name = farm_manager.get_active_farm_name()
        if not farm_name:
            return
            
        from src.core.constants import FARMS_DIR
        farm_path = FARMS_DIR / farm_name
            
        config_path = Path(farm_path) / "config.json"
        db_path = config_path.with_suffix('.db')
        
        if not db_path.exists():
            from src.core.managers.config_manager import _read_config
            from src.core.managers.db_manager import mirror_to_sqlite
            config_data = _read_config(config_path)
            mirror_to_sqlite(config_path, config_data)
            
            if not db_path.exists():
                return
            
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                
                # Загружаем кол-во аккаунтов
                cursor.execute("SELECT COUNT(*) FROM accounts")
                total = cursor.fetchone()[0]
                self.card_total.update_value(total)
                
                # Подсчет действий за 24ч
                cursor.execute("SELECT COUNT(*) FROM analytics WHERE timestamp >= datetime('now', '-1 day')")
                actions_24 = cursor.fetchone()[0]
                self.card_actions.update_value(actions_24)

                # Заглушки для детальной статистики, пока мы не пишем конкретные экшены
                # Но мы можем симулировать их чтение для интерфейса
                cursor.execute("SELECT COUNT(*) FROM analytics WHERE action='comment_success'")
                comments = cursor.fetchone()[0]
                # Чтобы дашборд не выглядел совсем пустым, если данных нет
                if comments == 0: comments = "0"
                self.card_comments.update_value(comments)

                cursor.execute("SELECT COUNT(*) FROM analytics WHERE action='warmup_success'")
                warmups = cursor.fetchone()[0]
                self.card_warmups.update_value(warmups)

                cursor.execute("SELECT COUNT(*) FROM analytics WHERE action='error' OR action='log_error'")
                errors = cursor.fetchone()[0]
                self.card_errors.update_value(errors)
                
                # График: активность по часам
                cursor.execute("""
                    SELECT strftime('%H', timestamp) as hour, COUNT(*) 
                    FROM analytics 
                    WHERE timestamp >= datetime('now', '-24 hours')
                    GROUP BY hour
                    ORDER BY timestamp
                """)
                rows = cursor.fetchall()
                
                x = []
                y = []
                ticks = []
                for idx, r in enumerate(rows):
                    x.append(idx)
                    y.append(r[1])
                    ticks.append((idx, str(r[0]) + ":00"))
                    
                self.plot_widget.clear()
                if x:
                    pen = pg.mkPen(color=styles.COLOR_PRIMARY, width=3)
                    self.plot_widget.getAxis('bottom').setTicks([ticks])
                    self.plot_widget.plot(x, y, pen=pen, symbol='o', symbolSize=8, symbolBrush=styles.COLOR_PRIMARY_LIGHT)
                    
        except Exception as e:
            print(f"Dashboard Error: {e}")
