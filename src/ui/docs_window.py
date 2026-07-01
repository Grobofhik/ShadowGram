from src.ui.icon_cache import get_icon
import os
import markdown
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTextBrowser, QPushButton, 
    QHBoxLayout, QScrollArea, QFrame, QLabel, QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import Qt, QSize, QUrl, pyqtSignal
from PyQt6.QtGui import QIcon, QFont

from src.core.constants import FOLDER_ICON_PATH, LOGO_PATH, SERVER_ICON_PATH, MODULS_ICON_PATH, SETTINGS_ICON_PATH
from src import styles

class DocsPage(QWidget):
    back_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("DocsPage")
        self.current_file = ""
        self.init_ui()
        self.load_file("documentation/START.md")

    def init_ui(self):
        main_h_layout = QHBoxLayout(self)
        main_h_layout.setContentsMargins(0, 0, 0, 0)
        main_h_layout.setSpacing(0)

        # ЛЕВАЯ ПАНЕЛЬ (Навигация)
        sidebar = QFrame()
        sidebar.setObjectName("DocsSidebar")
        sidebar.setFixedWidth(300)
        sidebar.setStyleSheet(f"""
            QFrame#DocsSidebar {{
                background-color: {styles.COLOR_ACCENT_BG};
                border-right: 1px solid {styles.COLOR_BORDER};
            }}
            QLabel#DocsSidebarTitle {{
                color: {styles.COLOR_PRIMARY};
                font-size: 18px;
                font-weight: bold;
                padding-bottom: 15px;
                border-bottom: 1px solid {styles.COLOR_BORDER};
            }}
            QTreeWidget {{
                background-color: transparent;
                border: none;
                color: {styles.COLOR_TEXT_MAIN};
                font-size: 14px;
                outline: none;
            }}
            QTreeWidget::item {{
                padding: 8px;
                border-radius: 6px;
            }}
            QTreeWidget::item:selected {{
                background-color: {styles.COLOR_PRIMARY};
                color: #ffffff;
            }}
            QTreeWidget::item:hover:!selected {{
                background-color: {styles.COLOR_HOVER_BG};
            }}
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 30, 20, 20)
        sidebar_layout.setSpacing(15)

        sidebar_title = QLabel("ShadowGram Wiki")
        sidebar_title.setObjectName("DocsSidebarTitle")
        sidebar_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(sidebar_title)

        self.tree = QTreeWidget()
        self.tree.setObjectName("DocsTree")
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(20)
        self.tree.setAnimated(True)
        self.tree.setIconSize(QSize(20, 20))
        self.tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tree.itemClicked.connect(self.on_item_clicked)
        
        self.setup_navigation()
        sidebar_layout.addWidget(self.tree)
        sidebar_layout.addStretch()
        
        self.btn_close = QPushButton("⬅ Вернуться назад")
        self.btn_close.setObjectName("SecondaryBtn")
        self.btn_close.setFixedHeight(45)
        self.btn_close.setStyleSheet(f"""
            QPushButton#SecondaryBtn {{
                background-color: {styles.COLOR_SELECT_BG};
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
            }}
            QPushButton#SecondaryBtn:hover {{
                background-color: {styles.COLOR_HOVER_BG};
            }}
        """)
        self.btn_close.clicked.connect(self.back_requested.emit)
        sidebar_layout.addWidget(self.btn_close)

        main_h_layout.addWidget(sidebar)

        # ПРАВАЯ ПАНЕЛЬ (Контент)
        content_area = QFrame()
        content_area.setStyleSheet(f"background-color: {styles.COLOR_BG};")
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(40, 40, 40, 40)

        self.browser = QTextBrowser()
        self.browser.setObjectName("DocsBrowser")
        self.browser.setOpenExternalLinks(False) 
        self.browser.anchorClicked.connect(self.on_anchor_clicked)
        self.browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: transparent;
                border: none;
                color: {styles.COLOR_TEXT_MAIN};
                font-size: 15px;
                line-height: 1.6;
            }}
            QScrollBar:vertical {{
                background: {styles.COLOR_BG};
                width: 12px;
                margin: 0px 0px 0px 0px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {styles.COLOR_BORDER};
                min-height: 20px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {styles.COLOR_PRIMARY_LIGHT};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        content_layout.addWidget(self.browser)

        main_h_layout.addWidget(content_area, 1)

    def setup_navigation(self):
        folder_icon = get_icon(FOLDER_ICON_PATH)
        home_icon = get_icon(LOGO_PATH)
        server_icon = get_icon(SERVER_ICON_PATH)
        module_icon = get_icon(MODULS_ICON_PATH)
        settings_icon = get_icon(SETTINGS_ICON_PATH)

        def create_selectable_item(parent, name, path, icon=None):
            item = QTreeWidgetItem(parent, [name])
            if icon: item.setIcon(0, icon)
            item.setData(0, Qt.ItemDataRole.UserRole, path)
            return item

        def create_category(name, icon):
            item = QTreeWidgetItem(self.tree, [name])
            item.setIcon(0, icon)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            # Expand by default
            item.setExpanded(True)
            return item

        # 1. Введение
        cat_intro = create_category("Введение", home_icon)
        create_selectable_item(cat_intro, "🚀 Обзор ShadowGram", "documentation/START.md")
        create_selectable_item(cat_intro, "🎯 Быстрый старт (Первый запуск)", "documentation/getting_started/first_start.md")

        # 2. Профили
        cat_profiles = create_category("Управление профилями", folder_icon)
        create_selectable_item(cat_profiles, "Создание профиля", "documentation/profiles/create_profile.md")
        create_selectable_item(cat_profiles, "Кнопки управления", "documentation/profiles/profile_actions.md")

        # 3. Настройки
        cat_settings = create_category("Настройки программы", settings_icon)
        create_selectable_item(cat_settings, "Глобальные настройки", "documentation/settings/global_settings.md")

        # 4. Модули
        cat_modules = create_category("Модули автоматизации", module_icon)
        modules_dir = "documentation/modules"
        if os.path.exists(modules_dir):
            for file in sorted(os.listdir(modules_dir)):
                if file.endswith(".md"):
                    name = file.replace(".md", "").replace("_", " ").title()
                    create_selectable_item(cat_modules, name, os.path.join(modules_dir, file))

        # 5. Сценарии
        cat_features = create_category("Функции", module_icon)
        create_selectable_item(cat_features, "Сценарии (Scenarios)", "documentation/features/scenarios.md")

        # 6. Практики и Защита (Anti-Ban)
        cat_best_practices = create_category("Защита от банов", folder_icon)
        create_selectable_item(cat_best_practices, "Anti-Ban & Fingerprint", "documentation/best_practices/anti_ban.md")

        # 7. Сервер
        cat_server = create_category("Управление сервером", server_icon)
        create_selectable_item(cat_server, "Настройка сервера", "documentation/server/server_setup.md")

        # 8. Ошибки и Решения
        cat_troubleshooting = create_category("Решение проблем", settings_icon)
        create_selectable_item(cat_troubleshooting, "Ошибки (FloodWait и др.)", "documentation/troubleshooting/errors.md")

        # 9. Разработка
        cat_dev = create_category("Для разработчиков", folder_icon)
        create_selectable_item(cat_dev, "Создание плагинов", "documentation/developers/plugin_development_guide.md")
        
    def on_anchor_clicked(self, url: QUrl):
        link = url.toString()
        if link.startswith("http"):
            import webbrowser
            webbrowser.open(link)
        else:
            current_dir = os.path.dirname(self.current_file)
            new_path = os.path.normpath(os.path.join(current_dir, link))
            if os.path.exists(new_path):
                self.load_file(new_path)
                self.sync_tree_selection(new_path)

    def sync_tree_selection(self, file_path):
        def scan_items(parent_item):
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                if child.data(0, Qt.ItemDataRole.UserRole) == file_path:
                    self.tree.setCurrentItem(child)
                    return True
                if scan_items(child): return True
            return False
        
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.data(0, Qt.ItemDataRole.UserRole) == file_path:
                self.tree.setCurrentItem(item)
                break
            if scan_items(item): break

    def on_item_clicked(self, item, column):
        if item.childCount() > 0:
            item.setExpanded(not item.isExpanded())
            return

        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if file_path:
            self.load_file(file_path)

    def load_file(self, file_path):
        if os.path.exists(file_path):
            try:
                self.current_file = file_path
                with open(file_path, "r", encoding="utf-8") as f:
                    md_text = f.read()
                    
                    extensions = ['fenced_code', 'codehilite', 'tables', 'nl2br', 'toc']
                    extension_configs = {
                        'codehilite': {
                            'noclasses': True,
                            'pygments_style': 'monokai'
                        }
                    }
                    
                    html = markdown.markdown(md_text, extensions=extensions, extension_configs=extension_configs)
                    
                    # Wrap in a modern body style
                    html = f"""
                    <html><head><style>
                        body {{ font-family: 'Inter', sans-serif; color: {styles.COLOR_TEXT_MAIN}; }}
                        h1, h2, h3 {{ color: {styles.COLOR_PRIMARY}; border-bottom: 1px solid {styles.COLOR_BORDER}; padding-bottom: 5px; }}
                        a {{ color: {styles.COLOR_PRIMARY_LIGHT}; text-decoration: none; }}
                        a:hover {{ text-decoration: underline; }}
                        pre {{ background-color: {styles.COLOR_CONSOLE_BG}; padding: 15px; border-radius: 8px; border: 1px solid {styles.COLOR_BORDER}; overflow-x: auto; }}
                        code {{ background-color: {styles.COLOR_CONSOLE_BG}; padding: 2px 6px; border-radius: 4px; color: {styles.COLOR_SUCCESS}; font-family: 'Consolas', monospace; }}
                        blockquote {{ border-left: 4px solid {styles.COLOR_PRIMARY}; padding-left: 15px; color: #888888; font-style: italic; background-color: {styles.COLOR_ACCENT_BG}; padding: 10px; border-radius: 4px; }}
                        table {{ border-collapse: collapse; width: 100%; margin-top: 15px; }}
                        th, td {{ border: 1px solid {styles.COLOR_BORDER}; padding: 10px; text-align: left; }}
                        th {{ background-color: {styles.COLOR_ACCENT_BG}; color: {styles.COLOR_PRIMARY}; }}
                        li {{ margin-bottom: 8px; }}
                    </style></head><body>
                    {html}
                    <br><br><br>
                    </body></html>
                    """
                    
                    base_url = QUrl.fromLocalFile(os.path.abspath(file_path))
                    self.browser.document().setBaseUrl(base_url)
                    self.browser.setHtml(html)
                    self.browser.verticalScrollBar().setValue(0)
            except Exception as e:
                self.browser.setHtml(f"<h2 style='color: #f44336;'>Ошибка чтения файла:</h2><p>{e}</p>")
        else:
            self.browser.setHtml(f"<h2 style='color: #f44336;'>Документ не найден:</h2><p>{file_path}</p>")
