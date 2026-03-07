import os
import markdown
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTextBrowser, QPushButton, 
    QHBoxLayout, QScrollArea, QFrame, QLabel, QTreeWidget, QTreeWidgetItem
)
from PyQt6.QtCore import Qt, QSize, QUrl
from PyQt6.QtGui import QIcon, QFont

from src.core.constants import FOLDER_ICON_PATH, LOGO_PATH, SERVER_ICON_PATH, MODULS_ICON_PATH
from src import styles

class DocsWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("DocsWindow")
        self.current_file = ""
        self.init_ui()
        # Применяем глобальные стили документации
        self.setStyleSheet(styles.DOCS_STYLESHEET)
        # По умолчанию загружаем START.md
        self.load_file("documentation/START.md")

    def init_ui(self):
        self.setWindowTitle("ShadowGram - База знаний")
        self.resize(1100, 800)

        main_h_layout = QHBoxLayout(self)
        main_h_layout.setContentsMargins(0, 0, 0, 0)
        main_h_layout.setSpacing(0)

        # ЛЕВАЯ ПАНЕЛЬ (Навигация)
        sidebar = QFrame()
        sidebar.setObjectName("DocsSidebar")
        sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 20, 10, 10)

        sidebar_title = QLabel("ShadowGram Wiki")
        sidebar_title.setObjectName("DocsSidebarTitle")
        sidebar_layout.addWidget(sidebar_title)

        self.tree = QTreeWidget()
        self.tree.setObjectName("DocsTree")
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(20)
        self.tree.setAnimated(True)
        self.tree.setIconSize(QSize(18, 18))
        self.tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tree.itemClicked.connect(self.on_item_clicked)
        
        self.setup_navigation()
        sidebar_layout.addWidget(self.tree)
        sidebar_layout.addStretch()
        
        self.btn_close = QPushButton(" Закрыть")
        self.btn_close.setObjectName("DocsCloseBtn")
        self.btn_close.setFixedHeight(38)
        self.btn_close.clicked.connect(self.close)
        sidebar_layout.addWidget(self.btn_close)

        main_h_layout.addWidget(sidebar)

        # ПРАВАЯ ПАНЕЛЬ (Контент)
        content_area = QFrame()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)

        self.browser = QTextBrowser()
        self.browser.setObjectName("DocsBrowser")
        self.browser.setOpenExternalLinks(False) 
        self.browser.anchorClicked.connect(self.on_anchor_clicked)
        content_layout.addWidget(self.browser)

        main_h_layout.addWidget(content_area, 1)

    def setup_navigation(self):
        folder_icon = QIcon(str(FOLDER_ICON_PATH))
        home_icon = QIcon(str(LOGO_PATH))
        server_icon = QIcon(str(SERVER_ICON_PATH))
        module_icon = QIcon(str(MODULS_ICON_PATH))

        def create_selectable_item(parent, name, path, icon=None):
            item = QTreeWidgetItem(parent, [name])
            if icon: item.setIcon(0, icon)
            item.setData(0, Qt.ItemDataRole.UserRole, path)
            return item

        def create_category(name, icon):
            item = QTreeWidgetItem(self.tree, [name])
            item.setIcon(0, icon)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            return item

        # 1. Введение
        create_selectable_item(self.tree, "🚀 Обзор ShadowGram", "documentation/START.md", home_icon)

        # 2. Профили
        cat_profiles = create_category("Управление профилями", folder_icon)
        create_selectable_item(cat_profiles, "Создание профиля", "documentation/profiles/create_profile.md")
        create_selectable_item(cat_profiles, "Кнопки управления", "documentation/profiles/profile_actions.md")

        # 3. Модули
        cat_modules = create_category("Модули автоматизации", module_icon)
        modules_dir = "documentation/modules"
        if os.path.exists(modules_dir):
            for file in sorted(os.listdir(modules_dir)):
                if file.endswith(".md"):
                    name = file.replace(".md", "").replace("_", " ").title()
                    create_selectable_item(cat_modules, name, os.path.join(modules_dir, file))

        # 4. Сервер
        cat_server = create_category("Управление сервером", server_icon)
        create_selectable_item(cat_server, "Настройка сервера", "documentation/server/server_setup.md")

        # 5. Разработка
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
                    
                    base_url = QUrl.fromLocalFile(os.path.abspath(file_path))
                    self.browser.document().setBaseUrl(base_url)
                    self.browser.setHtml(html)
                    self.browser.verticalScrollBar().setValue(0)
            except Exception as e:
                self.browser.setHtml(f"<h2 style='color: #f44336;'>Ошибка чтения файла:</h2><p>{e}</p>")
        else:
            self.browser.setHtml(f"<h2 style='color: #f44336;'>Документ не найден:</h2><p>{file_path}</p>")
