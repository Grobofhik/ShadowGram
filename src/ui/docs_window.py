import os
import webbrowser

import markdown
from PyQt6.QtCore import QSize, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src import styles
from src.core.constants import (
    CANCEL_ICON_PATH,
    FOLDER_ICON_PATH,
    LOGO_PATH,
    MODULS_ICON_PATH,
    SERVER_ICON_PATH,
    SETTINGS_ICON_PATH,
)
from src.ui.icon_cache import get_icon


class DocsPage(QWidget):
    back_requested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setObjectName("DocsPage")
        self.setStyleSheet(styles.DOCS_STYLESHEET)
        self.current_file = ""
        self.init_ui()
        self.load_file("documentation/START.md")

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(22, 22, 22, 22)
        main_layout.setSpacing(20)

        sidebar = QFrame()
        sidebar.setObjectName("DocsSidebar")
        sidebar.setFixedWidth(320)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 22, 20, 20)
        sidebar_layout.setSpacing(16)

        sidebar_title = QLabel("ShadowGram Wiki")
        sidebar_title.setObjectName("DocsSidebarTitle")
        sidebar_layout.addWidget(sidebar_title)

        sidebar_hint = QLabel("Навигация по документации, функциям и модулям")
        sidebar_hint.setObjectName("DocsHint")
        sidebar_hint.setWordWrap(True)
        sidebar_layout.addWidget(sidebar_hint)

        self.tree = QTreeWidget()
        self.tree.setObjectName("DocsTree")
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(18)
        self.tree.setAnimated(True)
        self.tree.setIconSize(QSize(18, 18))
        self.tree.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.setup_navigation()
        sidebar_layout.addWidget(self.tree, 1)

        self.btn_close = QPushButton("Вернуться к аккаунтам")
        self.btn_close.setObjectName("DocsCloseBtn")
        self.btn_close.setIcon(QIcon(str(CANCEL_ICON_PATH)))
        self.btn_close.setFixedHeight(44)
        self.btn_close.clicked.connect(self.back_requested.emit)
        sidebar_layout.addWidget(self.btn_close)

        main_layout.addWidget(sidebar)

        content_shell = QFrame()
        content_shell.setObjectName("DocsContentShell")
        content_layout = QVBoxLayout(content_shell)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(16)

        toolbar = QFrame()
        toolbar.setObjectName("DocsToolbar")
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(18, 16, 18, 16)
        toolbar_layout.setSpacing(12)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)

        toolbar_hint = QLabel("СПРАВКА")
        toolbar_hint.setObjectName("DocsHint")
        title_layout.addWidget(toolbar_hint)

        self.title_label = QLabel("Документация")
        self.title_label.setObjectName("DocsTitle")
        title_layout.addWidget(self.title_label)

        self.path_label = QLabel("documentation/START.md")
        self.path_label.setObjectName("DocsPath")
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        title_layout.addWidget(self.path_label)

        toolbar_layout.addLayout(title_layout, 1)

        self.btn_back_to_top = QPushButton("Наверх")
        self.btn_back_to_top.setObjectName("GhostBtn")
        self.btn_back_to_top.setFixedHeight(40)
        self.btn_back_to_top.clicked.connect(self.scroll_to_top)
        toolbar_layout.addWidget(self.btn_back_to_top)

        content_layout.addWidget(toolbar)

        self.browser = QTextBrowser()
        self.browser.setObjectName("DocsBrowser")
        self.browser.setOpenExternalLinks(False)
        self.browser.anchorClicked.connect(self.on_anchor_clicked)
        content_layout.addWidget(self.browser, 1)

        main_layout.addWidget(content_shell, 1)

    def setup_navigation(self):
        folder_icon = get_icon(FOLDER_ICON_PATH)
        home_icon = get_icon(LOGO_PATH)
        server_icon = get_icon(SERVER_ICON_PATH)
        module_icon = get_icon(MODULS_ICON_PATH)
        settings_icon = get_icon(SETTINGS_ICON_PATH)

        sections = [
            (
                "Введение",
                home_icon,
                [
                    ("Обзор ShadowGram", "documentation/START.md"),
                    ("Быстрый старт", "documentation/getting_started/first_start.md"),
                ],
            ),
            (
                "Управление профилями",
                folder_icon,
                [
                    ("Создание профиля", "documentation/profiles/create_profile.md"),
                    ("Кнопки управления", "documentation/profiles/profile_actions.md"),
                ],
            ),
            (
                "Настройки программы",
                settings_icon,
                [
                    ("Глобальные настройки", "documentation/settings/global_settings.md"),
                ],
            ),
            (
                "Функции",
                module_icon,
                [
                    ("Сценарии", "documentation/features/scenarios.md"),
                ],
            ),
            (
                "Защита от банов",
                folder_icon,
                [
                    ("Anti-Ban & Fingerprint", "documentation/best_practices/anti_ban.md"),
                ],
            ),
            (
                "Управление сервером",
                server_icon,
                [
                    ("Настройка сервера", "documentation/server/server_setup.md"),
                ],
            ),
            (
                "Решение проблем",
                settings_icon,
                [
                    ("Ошибки и ограничения", "documentation/troubleshooting/errors.md"),
                ],
            ),
            (
                "Для разработчиков",
                folder_icon,
                [
                    ("Создание плагинов", "documentation/developers/plugin_development_guide.md"),
                    ("Справочник Hydrogram API", "documentation/developers/hydrogram_api_reference.md"),
                ],
            ),
        ]

        for title, icon, items in sections:
            category = self._create_category(title, icon)
            for item_title, path in items:
                self._create_selectable_item(category, item_title, path)
            if category.childCount() == 0:
                index = self.tree.indexOfTopLevelItem(category)
                self.tree.takeTopLevelItem(index)

        modules_dir = "documentation/modules"
        if os.path.exists(modules_dir):
            modules_category = self._create_category("Модули автоматизации", module_icon)
            for file_name in sorted(os.listdir(modules_dir)):
                if not file_name.endswith(".md"):
                    continue
                readable_name = file_name.replace(".md", "").replace("_", " ").title()
                self._create_selectable_item(
                    modules_category,
                    readable_name,
                    os.path.join(modules_dir, file_name),
                )
            if modules_category.childCount() == 0:
                index = self.tree.indexOfTopLevelItem(modules_category)
                self.tree.takeTopLevelItem(index)

    def _create_category(self, name, icon):
        item = QTreeWidgetItem(self.tree, [name])
        item.setIcon(0, icon)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        item.setExpanded(True)
        return item

    def _create_selectable_item(self, parent, name, path, icon=None):
        if not os.path.exists(path):
            return None
        item = QTreeWidgetItem(parent, [name])
        if icon:
            item.setIcon(0, icon)
        item.setData(0, Qt.ItemDataRole.UserRole, path)
        return item

    def on_anchor_clicked(self, url: QUrl):
        link = url.toString()
        if link.startswith("http"):
            webbrowser.open(link)
            return

        if link.startswith("#"):
            self.browser.scrollToAnchor(link[1:])
            return

        current_dir = os.path.dirname(self.current_file)
        path_part, _, anchor = link.partition("#")
        new_path = os.path.normpath(os.path.join(current_dir, path_part))
        if not os.path.exists(new_path):
            return

        self.load_file(new_path)
        self.sync_tree_selection(new_path)
        if anchor:
            self.browser.scrollToAnchor(anchor)

    def sync_tree_selection(self, file_path):
        def scan_items(parent_item):
            for index in range(parent_item.childCount()):
                child = parent_item.child(index)
                if child.data(0, Qt.ItemDataRole.UserRole) == file_path:
                    self.tree.setCurrentItem(child)
                    return True
                if scan_items(child):
                    return True
            return False

        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            if scan_items(item):
                break

    def on_item_clicked(self, item, _column):
        if item.childCount() > 0:
            item.setExpanded(not item.isExpanded())
            return

        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if file_path:
            self.load_file(file_path)

    def load_file(self, file_path):
        if not os.path.exists(file_path):
            self.title_label.setText("Документ не найден")
            self.path_label.setText(file_path)
            self.browser.setHtml(self._build_message_html("Документ не найден", file_path))
            return

        try:
            self.current_file = file_path
            with open(file_path, "r", encoding="utf-8") as file:
                md_text = file.read()

            html = markdown.markdown(
                md_text,
                extensions=["fenced_code", "codehilite", "tables", "nl2br", "toc"],
                extension_configs={
                    "codehilite": {
                        "noclasses": True,
                        "pygments_style": "monokai",
                    }
                },
            )

            self.title_label.setText(self._extract_title(md_text, file_path))
            self.path_label.setText(file_path)

            base_url = QUrl.fromLocalFile(os.path.abspath(file_path))
            self.browser.document().setBaseUrl(base_url)
            self.browser.setHtml(self._wrap_markdown_html(html))
            self.sync_tree_selection(file_path)
            self.browser.verticalScrollBar().setValue(0)
        except Exception as error:
            self.title_label.setText("Ошибка чтения")
            self.path_label.setText(file_path)
            self.browser.setHtml(self._build_message_html("Ошибка чтения файла", str(error)))

    def scroll_to_top(self):
        self.browser.verticalScrollBar().setValue(0)

    def _extract_title(self, md_text, file_path):
        for line in md_text.splitlines():
            stripped = line.strip()
            if stripped.startswith("# "):
                return stripped[2:].strip()
        return os.path.splitext(os.path.basename(file_path))[0].replace("_", " ").title()

    def _wrap_markdown_html(self, html):
        return f"""
        <html>
            <head>
                <style>
                    body {{
                        color: {styles.COLOR_TEXT_MAIN};
                        font-family: 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif;
                        font-size: 15px;
                        line-height: 1.75;
                    }}
                    h1, h2, h3 {{
                        color: {styles.COLOR_PRIMARY_LIGHT};
                        margin-top: 28px;
                        margin-bottom: 14px;
                    }}
                    h1 {{
                        font-size: 30px;
                        border-bottom: 1px solid {styles.COLOR_BORDER};
                        padding-bottom: 10px;
                    }}
                    h2 {{
                        font-size: 22px;
                    }}
                    h3 {{
                        font-size: 18px;
                    }}
                    p {{
                        margin: 10px 0 16px 0;
                    }}
                    a {{
                        color: {styles.COLOR_PRIMARY_LIGHT};
                        text-decoration: none;
                    }}
                    a:hover {{
                        text-decoration: underline;
                    }}
                    ul, ol {{
                        margin: 0 0 16px 22px;
                    }}
                    li {{
                        margin-bottom: 8px;
                    }}
                    pre {{
                        background-color: {styles.COLOR_CONSOLE_BG};
                        border: 1px solid {styles.COLOR_BORDER};
                        border-radius: 12px;
                        padding: 16px;
                        overflow-x: auto;
                    }}
                    code {{
                        background-color: {styles.COLOR_CONSOLE_BG};
                        border: 1px solid {styles.COLOR_BORDER};
                        border-radius: 6px;
                        padding: 2px 6px;
                        color: {styles.COLOR_SUCCESS};
                        font-family: 'Consolas', 'JetBrains Mono', monospace;
                    }}
                    pre code {{
                        border: none;
                        padding: 0;
                    }}
                    blockquote {{
                        margin: 18px 0;
                        padding: 14px 16px;
                        border-left: 3px solid {styles.COLOR_PRIMARY};
                        background-color: {styles.COLOR_ACCENT_BG};
                        color: {styles.COLOR_TEXT_MUTED};
                        border-radius: 10px;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin: 18px 0 24px 0;
                    }}
                    th, td {{
                        border: 1px solid {styles.COLOR_BORDER};
                        padding: 12px 14px;
                        text-align: left;
                    }}
                    th {{
                        background-color: {styles.COLOR_ACCENT_BG};
                        color: {styles.COLOR_PRIMARY_LIGHT};
                    }}
                    hr {{
                        border: none;
                        border-top: 1px solid {styles.COLOR_BORDER};
                        margin: 28px 0;
                    }}
                </style>
            </head>
            <body>
                {html}
                <br><br>
            </body>
        </html>
        """

    def _build_message_html(self, title, text):
        return f"""
        <html>
            <body style="font-family: 'Segoe UI', sans-serif; color: {styles.COLOR_TEXT_MAIN};">
                <h2 style="color: {styles.COLOR_DANGER};">{title}</h2>
                <p style="color: {styles.COLOR_TEXT_MUTED};">{text}</p>
            </body>
        </html>
        """
