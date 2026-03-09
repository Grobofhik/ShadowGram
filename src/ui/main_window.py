import os
import subprocess
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget
# from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QTimer, QEvent, QUrl

"""
Главный контроллер интерфейса приложения.
Функции:

- init_ui: настройка главного окна и стека страниц
- init_audio: инициализация системы воспроизведения звука
- show_settings: переключение на страницу настроек
- show_list: переключение на страницу списка аккаунтов
- show_modules: открытие окна модулей управления
- show_server: открытие окна управления сервером
- sync_status: периодическая синхронизация статусов всех аккаунтов
- eventFilter: перехват событий (в частности, кликов по логотипу для воспроизведения звука)
"""

from src.ui.list_page import AccountListPage
from src.ui.settings_page import SettingsPage
from src.core.constants import SOUND_PATH

class TelegramManager(QWidget):
    def __init__(self):
        super().__init__()
        self.modules_win = None
        self.server_win = None
        self.init_ui()
        self.init_audio()
        self.timer = QTimer()
        self.timer.timeout.connect(self.sync_status)
        self.timer.start(1000)

    def init_ui(self):
        self.setWindowTitle("Shadowgram")
        self.resize(700, 750)
        self.stack = QStackedWidget(self)
        
        self.acc_list_page = AccountListPage(self)
        self.settings_page = SettingsPage()

        self.acc_list_page.settings_requested.connect(self.show_settings)
        self.acc_list_page.modules_requested.connect(self.show_modules)
        self.acc_list_page.server_requested.connect(self.show_server)
        self.acc_list_page.docs_requested.connect(self.show_docs)
        self.settings_page.back_requested.connect(self.show_list)

        self.stack.addWidget(self.acc_list_page)
        self.stack.addWidget(self.settings_page)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.stack)
        self.acc_list_page.refresh_accounts()

    def init_audio(self):
        self.sound_path = str(SOUND_PATH)
        # self.audio_output = QAudioOutput(self)
        # self.media_player = QMediaPlayer(self)
        # self.media_player.setAudioOutput(self.audio_output)
        # self.audio_output.setVolume(1.0)

    def show_settings(self):
        self.settings_page.load_settings()
        self.stack.setCurrentWidget(self.settings_page)

    def show_list(self):
        self.stack.setCurrentWidget(self.acc_list_page)

    def show_docs(self):
        self.settings_page.show_docs()

    def show_modules(self):
        if self.modules_win is None:
            from src.ui.modules_window import ModulesWindow
            self.modules_win = ModulesWindow()
        self.modules_win.show()
        self.modules_win.raise_()
        self.modules_win.activateWindow()

    def show_server(self):
        if self.server_win is None:
            from src.ui.server_window import ServerWindow
            self.server_win = ServerWindow()
        self.server_win.show()
        self.server_win.raise_()
        self.server_win.activateWindow()

    def sync_status(self):
        for r in self.acc_list_page.rows:
            if r.tg_process is not None:
                r.check_status()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            for cmd in ["mpv", "ffplay", "pw-play", "paplay"]:
                try:
                    args = [cmd, "--no-video", "--volume=100", self.sound_path] if cmd == "mpv" else [cmd, "-nodisp", "-autoexit", self.sound_path] if cmd == "ffplay" else [cmd, self.sound_path]
                    subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True
                except:
                    continue
            # self.media_player.setSource(QUrl.fromLocalFile(self.sound_path))
            # self.media_player.play()
            return True
        return super().eventFilter(obj, event)