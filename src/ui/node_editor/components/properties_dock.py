from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QScrollArea, QWidget, QSpinBox, QTextEdit, QLineEdit, QHBoxLayout, QPushButton, QFileDialog
from PyQt6.QtCore import Qt, QSize
import os
from src import styles
from src.ui.node_editor.node_specs import NODE_SPECS
from src.ui.node_editor.node_classes import NodeBlockItem

class PropertiesDock(QFrame):
    def __init__(self, parent_window, parent=None):
        super().__init__(parent)
        self.parent_window = parent_window
        self.setObjectName("PropertiesDock")
        self.setStyleSheet(f"""
            QFrame#PropertiesDock {{
                background-color: {styles.COLOR_ACCENT_BG};
                border-left: 1px solid {styles.COLOR_BORDER};
            }}
        """)
        self.active_params_widgets = {}
        self.selected_node = None
        self.init_ui()
        
    def find_upstream_param(self, node, param_name, visited=None):
        if visited is None:
            visited = set()
            
        if not node or node in visited:
            return None
        visited.add(node)
        
        for input_port in node.inputs:
            for connection in input_port.connections:
                source_port = connection.start_port
                if source_port and source_port.parent_node:
                    upstream_node = source_port.parent_node
                    upstream_val = upstream_node.params.get(param_name, "")
                    if param_name == "message_id":
                        try:
                            val_str = str(upstream_val).strip()
                            if val_str and val_str != "0" and val_str != "":
                                return val_str
                        except Exception:
                            pass
                    else:
                        if isinstance(upstream_val, str) and upstream_val.strip() != "":
                            return upstream_val.strip()
                            
                    found = self.find_upstream_param(upstream_node, param_name, visited)
                    if found:
                        return found
        return None
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # 1. Properties Section (Top Half)
        lbl_props = QLabel("⚙️ СВОЙСТВА БЛОКА")
        lbl_props.setStyleSheet(f"""
            color: #e2e8f0;
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 0.5px;
            padding-bottom: 6px;
            border-bottom: 1px solid {styles.COLOR_BORDER};
        """)
        main_layout.addWidget(lbl_props)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.container = QWidget()
        self.container.setStyleSheet("background-color: transparent;")
        self.params_layout = QVBoxLayout(self.container)
        self.params_layout.setContentsMargins(0, 0, 0, 0)
        self.params_layout.setSpacing(12)
        
        self.scroll.setWidget(self.container)
        main_layout.addWidget(self.scroll, 1)  # Take equal vertical space
        
        # Divider Line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {styles.COLOR_BORDER}; height: 1px; margin: 4px 0;")
        main_layout.addWidget(separator)
        
        # 2. Required Files Section (Bottom Half)
        lbl_files = QLabel("📋 НЕОБХОДИМЫЕ ФАЙЛЫ")
        lbl_files.setStyleSheet(f"""
            color: #e2e8f0;
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 0.5px;
            padding-bottom: 6px;
            border-bottom: 1px solid {styles.COLOR_BORDER};
        """)
        main_layout.addWidget(lbl_files)
        
        self.files_scroll = QScrollArea()
        self.files_scroll.setWidgetResizable(True)
        self.files_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.files_container = QWidget()
        self.files_container.setStyleSheet("background-color: transparent;")
        self.files_layout = QVBoxLayout(self.files_container)
        self.files_layout.setContentsMargins(0, 0, 0, 0)
        self.files_layout.setSpacing(8)
        self.files_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.files_scroll.setWidget(self.files_container)
        main_layout.addWidget(self.files_scroll, 1)  # Take equal vertical space
        
    def save_current_params(self):
        try:
            if self.selected_node:
                for p_name, widget in self.active_params_widgets.items():
                    try:
                        if isinstance(widget, QSpinBox):
                            self.selected_node.params[p_name] = widget.value()
                        elif isinstance(widget, QTextEdit):
                            self.selected_node.params[p_name] = widget.toPlainText()
                        elif isinstance(widget, QLineEdit):
                            self.selected_node.params[p_name] = widget.text()
                    except RuntimeError:
                        pass
        except Exception:
            pass

    def save_param_on_edit(self, p_name, widget):
        if not self.selected_node:
            return
        if isinstance(widget, QSpinBox):
            self.selected_node.params[p_name] = widget.value()
        elif isinstance(widget, QTextEdit):
            self.selected_node.params[p_name] = widget.toPlainText()
        elif isinstance(widget, QLineEdit):
            self.selected_node.params[p_name] = widget.text()
            
        # If it is a file/folder parameter, update required files list dynamically
        spec = NODE_SPECS.get(self.selected_node.node_type)
        if spec and p_name in spec.get("params", {}):
            if spec["params"][p_name].get("type") in ["file", "folder"]:
                self.refresh_required_files()

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                elif item.layout() is not None:
                    self.clear_layout(item.layout())

    def update_properties(self, scene):
        self.save_current_params()
        self.clear_layout(self.params_layout)
        self.active_params_widgets = {}
        self.selected_node = None
        
        selected_items = scene.selectedItems()
        nodes = [item for item in selected_items if isinstance(item, NodeBlockItem)]
        
        if len(nodes) == 1:
            self.selected_node = nodes[0]
            spec = NODE_SPECS.get(self.selected_node.node_type)
            if spec:
                for p_name, p_info in spec["params"].items():
                    val = self.selected_node.params.get(p_name, p_info["default"])
                    
                    field_layout = QVBoxLayout()
                    field_layout.setSpacing(4)
                    
                    lbl = QLabel(p_info["label"])
                    lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
                    field_layout.addWidget(lbl)
                    
                    if p_info["type"] == "int":
                        sb = QSpinBox()
                        sb.setRange(0, 100000)
                        sb.setValue(int(val))
                        sb.setStyleSheet(f"QSpinBox {{ background-color: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 4px; color: #e2e8f0; height: 26px; padding-left: 5px; }}")
                        sb.valueChanged.connect(lambda _, name=p_name, w=sb: self.save_param_on_edit(name, w))
                        field_layout.addWidget(sb)
                        self.active_params_widgets[p_name] = sb
                        
                        if p_name == "message_id":
                            inherited_val = self.find_upstream_param(self.selected_node, "message_id")
                            if inherited_val:
                                hint_text = f"💡 Будет унаследовано: ID {inherited_val}"
                                color_hint = "#34d399"
                            else:
                                hint_text = "💡 0 = наследуется от предыдущего сообщения"
                                color_hint = "#94a3b8"
                            hint_lbl = QLabel(hint_text)
                            hint_lbl.setStyleSheet(f"font-style: italic; color: {color_hint}; font-size: 10px; margin-top: 1px;")
                            field_layout.addWidget(hint_lbl)
                            
                    elif p_info["type"] == "textarea":
                        te = QTextEdit()
                        te.setPlainText(str(val))
                        te.setStyleSheet(f"QTextEdit {{ background-color: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 4px; color: #e2e8f0; font-size: 12px; }}")
                        te.setFixedHeight(80)
                        te.textChanged.connect(lambda name=p_name, w=te: self.save_param_on_edit(name, w))
                        field_layout.addWidget(te)
                        self.active_params_widgets[p_name] = te
                        
                    elif p_info["type"] in ["str", "folder", "file"]:
                        le = QLineEdit()
                        le.setText(str(val))
                        le.setStyleSheet(f"QLineEdit {{ background-color: {styles.COLOR_CONSOLE_BG}; border: 1px solid {styles.COLOR_BORDER}; border-radius: 4px; color: #e2e8f0; height: 26px; padding-left: 5px; }}")
                        le.textChanged.connect(lambda text_val, name=p_name, w=le: self.save_param_on_edit(name, w))
                        
                        inherited_val = self.find_upstream_param(self.selected_node, p_name)
                        if inherited_val:
                            le.setPlaceholderText(f"(Унаследовано: {inherited_val})")
                            hint_text = f"💡 Будет унаследовано: {inherited_val}"
                            color_hint = "#34d399"
                        else:
                            if p_name in ["chat_id", "to_chat_id"]:
                                le.setPlaceholderText("(Наследуется от предыдущего блока)")
                            elif p_name == "bot_username":
                                le.setPlaceholderText("(Наследуется от предыдущего блока)")
                            hint_text = "💡 Оставьте пустым для наследования"
                            color_hint = "#94a3b8"
                            
                        if p_info["type"] in ["folder", "file"]:
                            row_layout = QHBoxLayout()
                            row_layout.addWidget(le, 1)
                            
                            browse_btn = QPushButton("...")
                            browse_btn.setFixedSize(30, 26)
                            browse_btn.setStyleSheet("background-color: #334155; border: none; border-radius: 4px; color: #ffffff;")
                            def make_browse_handler(line_edit=le, is_file=(p_info["type"] == "file")):
                                def handle():
                                    if is_file:
                                        path, _ = QFileDialog.getOpenFileName(self.parent_window, "Выберите файл", line_edit.text() or os.getcwd(), "Текстовые файлы (*.txt);;Все файлы (*)")
                                    else:
                                        path = QFileDialog.getExistingDirectory(self.parent_window, "Выберите папку", line_edit.text() or os.getcwd())
                                    if path:
                                        line_edit.setText(path)
                                return handle
                            browse_btn.clicked.connect(make_browse_handler(le))
                            row_layout.addWidget(browse_btn)
                            field_layout.addLayout(row_layout)
                        else:
                            field_layout.addWidget(le)
                            
                        self.active_params_widgets[p_name] = le
                        
                        if p_name in ["chat_id", "to_chat_id", "bot_username"]:
                            hint_lbl = QLabel(hint_text)
                            hint_lbl.setStyleSheet(f"font-style: italic; color: {color_hint}; font-size: 10px; margin-top: 1px;")
                            field_layout.addWidget(hint_lbl)
                            
                    self.params_layout.addLayout(field_layout)
                
                # Dynamic branching paths for random_branch
                if self.selected_node.node_type == "random_branch":
                    div = QFrame()
                    div.setFrameShape(QFrame.Shape.HLine)
                    div.setStyleSheet(f"background-color: {styles.COLOR_BORDER}; height: 1px; margin: 10px 0;")
                    self.params_layout.addWidget(div)
                    
                    lbl_paths = QLabel("ВЫХОДНЫЕ ПУТИ:")
                    lbl_paths.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold;")
                    self.params_layout.addWidget(lbl_paths)
                    
                    for out_port in self.selected_node.outputs:
                        p_lbl = QLabel(f"• {out_port.name}")
                        p_lbl.setStyleSheet("color: #e2e8f0; font-size: 11px; padding-left: 5px;")
                        self.params_layout.addWidget(p_lbl)
                        
                    btn_layout = QHBoxLayout()
                    btn_layout.setSpacing(8)
                    
                    btn_add = QPushButton("Добавить путь (+)")
                    btn_add.setStyleSheet("""
                        QPushButton {
                            background-color: #10b981;
                            color: #ffffff;
                            border: none;
                            border-radius: 4px;
                            height: 24px;
                            font-size: 11px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #059669;
                        }
                    """)
                    
                    btn_del = QPushButton("Удалить путь (-)")
                    btn_del.setStyleSheet("""
                        QPushButton {
                            background-color: #ef4444;
                            color: #ffffff;
                            border: none;
                            border-radius: 4px;
                            height: 24px;
                            font-size: 11px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #dc2626;
                        }
                    """)
                    
                    def make_add_handler(scene_ref=scene):
                        def handle():
                            current_count = len(self.selected_node.outputs)
                            next_letter = chr(ord('a') + current_count) if current_count < 26 else str(current_count)
                            port_name = f"path_{next_letter}"
                            self.selected_node.add_port(port_name, is_output=True)
                            self.update_properties(scene_ref)
                        return handle
                        
                    def make_del_handler(scene_ref=scene):
                        def handle():
                            current_count = len(self.selected_node.outputs)
                            if current_count > 2:
                                last_port = self.selected_node.outputs[-1]
                                self.selected_node.remove_output_port(last_port.name)
                                self.update_properties(scene_ref)
                        return handle
                        
                    btn_add.clicked.connect(make_add_handler(scene))
                    btn_del.clicked.connect(make_del_handler(scene))
                    btn_layout.addWidget(btn_add)
                    btn_layout.addWidget(btn_del)
                    self.params_layout.addLayout(btn_layout)
                    
                self.params_layout.addStretch()
        else:
            lbl = QLabel("Выберите 1 блок\nдля редактирования свойств")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #64748b; font-size: 12px; margin-top: 50px;")
            self.params_layout.addWidget(lbl)
            self.params_layout.addStretch()
            
        # Always refresh the required files list
        self.refresh_required_files()

    def refresh_required_files(self):
        self.clear_layout(self.files_layout)
        
        if not self.parent_window or not self.parent_window.scene:
            return
            
        items = self.parent_window.scene.items()
        nodes = [item for item in items if isinstance(item, NodeBlockItem)]
        
        required_assets = []
        for node in nodes:
            spec = NODE_SPECS.get(node.node_type)
            if not spec:
                continue
            for p_name, p_info in spec.get("params", {}).items():
                if p_info.get("type") in ["file", "folder"]:
                    val = node.params.get(p_name, p_info.get("default", ""))
                    required_assets.append({
                        "node": node,
                        "param_name": p_name,
                        "param_info": p_info,
                        "value": str(val).strip(),
                        "label": p_info.get("label", p_name),
                        "type": p_info.get("type"),
                        "block_title": node.title or spec.get("title", node.node_type)
                    })
                    
        if not required_assets:
            placeholder = QLabel("Сценарий не требует локальных файлов.")
            placeholder.setStyleSheet("color: #64748b; font-size: 11px; font-style: italic; padding: 15px 0;")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.files_layout.addWidget(placeholder)
            return
            
        for asset in required_assets:
            row_widget = QFrame()
            row_widget.setObjectName("AssetRow")
            row_widget.setFrameShape(QFrame.Shape.StyledPanel)
            
            path = asset["value"]
            status_text = ""
            status_color = ""
            exists = False
            
            if not path:
                status_text = "Не задан"
                status_color = "#f59e0b"
            elif os.path.exists(path):
                status_text = "Найден"
                status_color = "#10b981"
                exists = True
            else:
                status_text = "Отсутствует"
                status_color = "#ef4444"
                
            icon = "📁" if asset["type"] == "folder" else "📄"
            display_name = os.path.basename(path) if path else f"Выберите {asset['type'] == 'folder' and 'папку' or 'файл'}..."
            
            row_widget.setStyleSheet(f"""
                QFrame#AssetRow {{
                    background-color: {styles.COLOR_BG};
                    border: 1px solid {styles.COLOR_BORDER};
                    border-radius: 6px;
                }}
                QFrame#AssetRow:hover {{
                    background-color: {styles.COLOR_HOVER_BG};
                    border-color: {styles.COLOR_PRIMARY};
                }}
            """)
            
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(8, 6, 8, 6)
            row_layout.setSpacing(8)
            
            # Left: Icon
            icon_lbl = QLabel(icon)
            icon_lbl.setStyleSheet("font-size: 16px; background: transparent;")
            row_layout.addWidget(icon_lbl)
            
            # Center: Details (File name & target)
            text_layout = QVBoxLayout()
            text_layout.setSpacing(1)
            
            name_lbl = QLabel(display_name)
            name_lbl.setStyleSheet("color: #e2e8f0; font-size: 11px; font-weight: bold; background: transparent;")
            name_lbl.setWordWrap(True)
            
            desc_lbl = QLabel(f"{asset['label']} ({asset['block_title']})")
            desc_lbl.setStyleSheet("color: #64748b; font-size: 9px; background: transparent;")
            desc_lbl.setWordWrap(True)
            
            text_layout.addWidget(name_lbl)
            text_layout.addWidget(desc_lbl)
            row_layout.addLayout(text_layout, 1)
            
            # Right side controls layout
            ctrl_layout = QVBoxLayout()
            ctrl_layout.setSpacing(3)
            ctrl_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            
            # Status dot badge
            status_lbl = QLabel(f"● {status_text}")
            status_lbl.setStyleSheet(f"color: {status_color}; font-size: 9px; font-weight: bold; background: transparent;")
            ctrl_layout.addWidget(status_lbl)
            
            # Action Buttons Row
            btn_row = QHBoxLayout()
            btn_row.setSpacing(4)
            btn_row.setContentsMargins(0, 0, 0, 0)
            
            btn_style = "background-color: #334155; border: none; border-radius: 3px; color: #ffffff; font-size: 9px; padding: 2px 5px;"
            btn_hover_style = "background-color: #475569;"
            
            # 1. Browse Button (Always present)
            btn_browse = QPushButton("...")
            btn_browse.setFixedSize(22, 16)
            btn_browse.setStyleSheet(btn_style)
            btn_browse.setToolTip("Выбрать путь на диске")
            
            def make_browse_handler(asst=asset):
                def handler():
                    if asst["type"] == "folder":
                        new_path = QFileDialog.getExistingDirectory(self.parent_window, f"Выберите {asst['label']}", asst["value"] or os.getcwd())
                    else:
                        new_path, _ = QFileDialog.getOpenFileName(self.parent_window, f"Выберите {asst['label']}", asst["value"] or os.getcwd(), "Текстовые файлы (*.txt);;Все файлы (*)")
                    if new_path:
                        asst["node"].params[asst["param_name"]] = new_path
                        self.update_properties(self.parent_window.scene)
                        if hasattr(self.parent_window, "mark_dirty"):
                            self.parent_window.mark_dirty()
                return handler
                
            btn_browse.clicked.connect(make_browse_handler())
            btn_row.addWidget(btn_browse)
            
            # 2. Action Button (Create or Edit)
            if not exists and path:
                # File is specified but missing: show "Create"
                btn_create = QPushButton("➕")
                btn_create.setFixedSize(22, 16)
                btn_create.setStyleSheet("background-color: #047857; border: none; border-radius: 3px; color: #ffffff; font-size: 9px;")
                btn_create.setToolTip("Создать пустой файл/папку")
                
                def make_create_handler(asst=asset):
                    def handler():
                        p = asst["value"]
                        if not p:
                            return
                        try:
                            abs_p = os.path.abspath(p)
                            os.makedirs(os.path.dirname(abs_p), exist_ok=True)
                            if asst["type"] == "folder":
                                os.makedirs(abs_p, exist_ok=True)
                            else:
                                with open(abs_p, "w", encoding="utf-8") as f:
                                    f.write("")
                            self.refresh_required_files()
                        except Exception as e:
                            self.parent_window.append_console_log(f"⚠️ Ошибка автосоздания: {e}")
                    return handler
                    
                btn_create.clicked.connect(make_create_handler())
                btn_row.addWidget(btn_create)
                
            elif exists and asset["type"] == "file":
                # File exists: show "Edit/Open"
                btn_open = QPushButton("🖉")
                btn_open.setFixedSize(22, 16)
                btn_open.setStyleSheet(btn_style)
                btn_open.setToolTip("Открыть файл в системном редакторе")
                
                def make_open_handler(p=path):
                    def handler():
                        import subprocess
                        import sys
                        try:
                            if sys.platform == "win32":
                                os.startfile(p)
                            elif sys.platform == "darwin":
                                subprocess.run(["open", p])
                            else:
                                subprocess.run(["xdg-open", p])
                        except Exception as e:
                            self.parent_window.append_console_log(f"⚠️ Ошибка открытия файла: {e}")
                    return handler
                    
                btn_open.clicked.connect(make_open_handler())
                btn_row.addWidget(btn_open)
                
            ctrl_layout.addLayout(btn_row)
            row_layout.addLayout(ctrl_layout)
            
            # Click row -> focus & select node on canvas
            def make_row_click_handler(asst=asset):
                def handler(event):
                    if self.parent_window and self.parent_window.scene:
                        self.parent_window.scene.clearSelection()
                        asst["node"].setSelected(True)
                        self.parent_window.view.centerOn(asst["node"])
                return handler
                
            row_widget.mousePressEvent = make_row_click_handler()
            
            self.files_layout.addWidget(row_widget)
