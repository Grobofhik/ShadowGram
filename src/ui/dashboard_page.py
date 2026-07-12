from src.core.constants import *
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
from PyQt6.QtWidgets import QDialog, QProgressBar, QPushButton, QWidget
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QFont

class ProxyCheckThread(QThread):
    progress_updated = pyqtSignal(int, int) # alive, total
    finished_check = pyqtSignal()
    
    def __init__(self, accounts, parent=None):
        super().__init__(parent)
        self.accounts = accounts
        
    def run(self):
        import socket
        alive = 0
        total = 0
        for acc in self.accounts:
            url = acc.get("proxy_url")
            if not url: continue
            
            total += 1
            ip, port = None, None
            try:
                if "://" in url:
                    parts = url.split("@")[-1].split(":")
                    ip = parts[0]
                    port = int(parts[1].split("/")[0])
                else:
                    parts = url.split(":")
                    ip = parts[0]
                    port = int(parts[1])
                    
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(2.0)
                s.connect((ip, port))
                s.close()
                alive += 1
            except Exception:
                pass
                
            self.progress_updated.emit(alive, total)
            
        self.finished_check.emit()

class ProgressIndicator(QFrame):
    def __init__(self, title, color):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)
        
        lbl_layout = QHBoxLayout()
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet(f"color: {styles.COLOR_TEXT_MAIN}; font-weight: bold;")
        self.val_lbl = QLabel("0 / 0 (0%)")
        self.val_lbl.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED};")
        lbl_layout.addWidget(self.title_lbl)
        lbl_layout.addStretch()
        lbl_layout.addWidget(self.val_lbl)
        
        self.bar = QProgressBar()
        self.bar.setFixedHeight(8)
        self.bar.setTextVisible(False)
        self.bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {styles.COLOR_CONSOLE_BG};
                border-radius: 4px;
                border: none;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """)
        
        layout.addLayout(lbl_layout)
        layout.addWidget(self.bar)
        
    def set_value(self, current, total):
        if total == 0:
            pct = 0
        else:
            pct = int((current / total) * 100)
            
        self.bar.setMaximum(total if total > 0 else 1)
        self.bar.setValue(current)
        self.val_lbl.setText(f"{current} / {total} ({pct}%)")

class CircularProgress(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0
        self.setFixedSize(60, 60)
        self.color = QColor(styles.COLOR_PRIMARY)
        
    def set_value(self, value, color_hex):
        self.value = value
        self.color = QColor(color_hex)
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = QRectF(5, 5, self.width() - 10, self.height() - 10)
        
        # Background circle
        pen_bg = QPen(QColor(styles.COLOR_BORDER))
        pen_bg.setWidth(6)
        pen_bg.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_bg)
        painter.drawArc(rect.toRect(), 0, 360 * 16)
        
        # Progress arc
        pen_fg = QPen(self.color)
        pen_fg.setWidth(6)
        pen_fg.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_fg)
        
        span_angle = int(-self.value * 3.6 * 16)
        painter.drawArc(rect.toRect(), 90 * 16, span_angle)
        
        # Text
        painter.setPen(self.color)
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        painter.setFont(font)
        painter.drawText(rect.toRect(), Qt.AlignmentFlag.AlignCenter, f"{self.value}%")
        
        painter.end()

class HealthPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            HealthPanel {{
                background-color: {styles.COLOR_ACCENT_BG};
                border-radius: 10px;
                border: 1px solid {styles.COLOR_BORDER};
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        hdr_layout = QHBoxLayout()
        title_lbl = QLabel("Индекс Качества Фермы")
        title_lbl.setStyleSheet(f"color: {styles.COLOR_TEXT_MAIN}; font-size: 16px; font-weight: bold; border: none;")
        hdr_layout.addWidget(title_lbl)
        hdr_layout.addStretch()
        
        self.circular_qi = CircularProgress()
        hdr_layout.addWidget(self.circular_qi)
        layout.addLayout(hdr_layout)
        
        self.ind_proxies = ProgressIndicator("Аккаунты с Прокси", styles.COLOR_INFO)
        self.ind_proxies_alive = ProgressIndicator("Живые Прокси", styles.COLOR_SUCCESS)
        self.ind_bios = ProgressIndicator("Заполнено Bio", styles.COLOR_PRIMARY)
        self.ind_names = ProgressIndicator("Заполнено 'Имя'", "#E67E22")
        self.ind_usernames = ProgressIndicator("Установлен @Username", styles.COLOR_WARNING)
        self.ind_avatars = ProgressIndicator("Установлен Аватар", "#9B59B6")
        self.ind_channels = ProgressIndicator("Личный канал", "#3498DB")
        self.ind_2fa = ProgressIndicator("Установлен 2FA (Пароль)", "#E74C3C")
        
        layout.addWidget(self.ind_proxies)
        layout.addWidget(self.ind_proxies_alive)
        layout.addWidget(self.ind_bios)
        layout.addWidget(self.ind_names)
        layout.addWidget(self.ind_usernames)
        layout.addWidget(self.ind_avatars)
        layout.addWidget(self.ind_channels)
        layout.addWidget(self.ind_2fa)
        
        self.btn_check_proxies = QPushButton("Проверить прокси (Ping)")
        self.btn_check_proxies.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.COLOR_CONSOLE_BG};
                color: {styles.COLOR_TEXT_MAIN};
                border: 1px solid {styles.COLOR_BORDER};
                border-radius: 4px; padding: 8px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {styles.COLOR_HOVER_BG}; }}
        """)
        self.btn_check_proxies.clicked.connect(self.start_proxy_check)
        layout.addWidget(self.btn_check_proxies)
        
        layout.addStretch()
        
    def start_proxy_check(self):
        farm_name = farm_manager.get_active_farm_name()
        if not farm_name: return
        
        from src.core.constants import FARMS_DIR
        from src.core.managers.config_manager import _read_config
        config_path = FARMS_DIR / farm_name / "config.json"
        config = _read_config(config_path)
        accounts = config.get("accounts", [])
        
        self.btn_check_proxies.setText("Проверка...")
        self.btn_check_proxies.setEnabled(False)
        
        self.proxy_thread = ProxyCheckThread(accounts, self)
        self.proxy_thread.progress_updated.connect(self.update_proxy_progress)
        self.proxy_thread.finished_check.connect(self.on_proxy_check_done)
        self.proxy_thread.start()
        
    def update_proxy_progress(self, alive, total):
        self.ind_proxies_alive.set_value(alive, total)
        
    def on_proxy_check_done(self):
        self.btn_check_proxies.setText("Проверить прокси (Ping)")
        self.btn_check_proxies.setEnabled(True)
        
    def calculate_health(self):
        farm_name = farm_manager.get_active_farm_name()
        if not farm_name: return
        
        from src.core.constants import FARMS_DIR
        farm_path = FARMS_DIR / farm_name
        config_path = farm_path / "config.json"
        
        from src.core.managers.config_manager import _read_config
        config = _read_config(config_path)
        accounts = config.get("accounts", [])
        
        total = len(accounts)
        if total == 0: return
        
        c_proxies = 0
        c_bios = 0
        c_names = 0
        c_usernames = 0
        c_avatars = 0
        c_channels = 0
        c_2fa = 0
        
        for acc in accounts:
            if acc.get("proxy_url"): c_proxies += 1
            if acc.get("bio"): c_bios += 1
            if acc.get("first_name"): c_names += 1
            if acc.get("username"): c_usernames += 1
            if acc.get("channel_link"): c_channels += 1
            if acc.get("password"): c_2fa += 1
            
            wd = acc.get("workdir")
            from pathlib import Path
            if wd and (Path(wd) / "avatar.jpg").exists():
                c_avatars += 1
                
        self.ind_proxies.set_value(c_proxies, total)
        self.ind_bios.set_value(c_bios, total)
        self.ind_names.set_value(c_names, total)
        self.ind_usernames.set_value(c_usernames, total)
        self.ind_avatars.set_value(c_avatars, total)
        self.ind_channels.set_value(c_channels, total)
        self.ind_2fa.set_value(c_2fa, total)
        
        # Calculate Quality Index: Average of all parameters per account
        total_points = (c_proxies + c_bios + c_names + c_usernames + c_avatars + c_channels + c_2fa)
        max_points = total * 7
        qi = int((total_points / max_points) * 100) if max_points > 0 else 0
        
        # We assign colors based on QI
        if qi >= 80: color = styles.COLOR_SUCCESS
        elif qi >= 50: color = styles.COLOR_WARNING
        else: color = styles.COLOR_DANGER
        
        self.circular_qi.set_value(qi, color)

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
        header = QLabel("Аналитика & Статистика")
        header.setStyleSheet(f"font-size: 26px; font-weight: bold; color: {styles.COLOR_TEXT_MAIN};")
        header_layout.addWidget(header)
        
        desc = QLabel("Данные синхронизируются в реальном времени.")
        desc.setStyleSheet(f"color: {styles.COLOR_TEXT_MUTED}; font-size: 12px;")
        
        header_layout.addStretch()
        
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
        
        # Bottom Layout (Graph + Health)
        bottom_layout = QHBoxLayout()
        
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
        bottom_layout.addWidget(graph_frame, stretch=6)
        
        # Health Panel
        self.health_panel = HealthPanel(self)
        bottom_layout.addWidget(self.health_panel, stretch=4)
        
        main_layout.addLayout(bottom_layout, stretch=1)
        
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
                    
            self.health_panel.calculate_health()
                    
        except Exception as e:
            print(f"Dashboard Error: {e}")
