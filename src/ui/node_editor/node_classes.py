from PyQt6.QtWidgets import (QGraphicsItem, QGraphicsPathItem, QGraphicsTextItem, 
                             QGraphicsEllipseItem, QGraphicsWidget, QGraphicsSimpleTextItem)
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal, QObject
from PyQt6.QtGui import QPen, QBrush, QColor, QPainterPath, QPainter, QFont

import uuid
from src import styles

class PortItem(QGraphicsEllipseItem):
    def __init__(self, name, is_output, parent_node):
        super().__init__(-5, -5, 10, 10, parent_node)
        self.name = name
        self.is_output = is_output
        self.parent_node = parent_node
        self.connections = []
        
        self.setAcceptHoverEvents(True)
        # Flow port styling: clean white dot
        self.setBrush(QBrush(QColor("#ffffff")))
        self.setPen(QPen(QColor("#0f172a"), 1.5))
        
        # Text label
        label_text = "Условие" if name == "condition" else name
        self.label = QGraphicsSimpleTextItem(label_text, self)
        self.label.setFont(QFont("Inter", 8))
        self.label.setBrush(QBrush(QColor("#94a3b8")))
        if is_output:
            self.label.setPos(-self.label.boundingRect().width() - 8, -6)
        else:
            if name == "condition":
                # Center label above the port, will be positioned correctly in arrange_ports
                self.label.setPos(-self.label.boundingRect().width() / 2, -18)
            else:
                self.label.setPos(8, -6)

    def hoverEnterEvent(self, event):
        self.setBrush(QBrush(QColor(styles.COLOR_PRIMARY)))
        self.setPen(QPen(QColor("#ffffff"), 2))
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setBrush(QBrush(QColor("#ffffff")))
        self.setPen(QPen(QColor("#0f172a"), 1.5))
        super().hoverLeaveEvent(event)

    def get_port_scene_pos(self):
        return self.mapToScene(0, 0)

    def mousePressEvent(self, event):
        if not self.is_output and event.button() == Qt.MouseButton.LeftButton:
            if self.connections:
                for conn in list(self.connections):
                    conn.delete()
                
                sc = self.scene()
                if sc and sc.parent():
                    parent_win = sc.parent()
                    if hasattr(parent_win, "properties_dock") and parent_win.properties_dock:
                        parent_win.properties_dock.update_properties(sc)
                        
                event.accept()
                return
        super().mousePressEvent(event)


class ConnectionItem(QGraphicsPathItem):
    def __init__(self, start_port, end_port=None):
        super().__init__()
        self.start_port = start_port
        self.end_port = end_port
        self.temp_end_pos = None
        
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setZValue(-1) # Behind nodes
        
        if start_port:
            start_port.connections.append(self)
        if end_port:
            end_port.connections.append(self)
            
        self.update_path()

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.isSelected():
            pen = QPen(QColor(styles.COLOR_PRIMARY), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        else:
            pen = QPen(QColor("#475569"), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawPath(self.path())

    def update_path(self):
        if not self.start_port:
            return
            
        p1 = self.start_port.get_port_scene_pos()
        
        if self.end_port:
            p2 = self.end_port.get_port_scene_pos()
        elif self.temp_end_pos:
            p2 = self.temp_end_pos
        else:
            return
            
        path = QPainterPath()
        path.moveTo(p1)
        
        # S-curve Bezier calculations
        dx = abs(p2.x() - p1.x()) * 0.5
        c1 = QPointF(p1.x() + dx, p1.y())
        c2 = QPointF(p2.x() - dx, p2.y())
        path.cubicTo(c1, c2, p2)
        
        self.setPath(path)

    def delete(self):
        if self.start_port and self.start_port.connections:
            if self in self.start_port.connections:
                self.start_port.connections.remove(self)
        if self.end_port and self.end_port.connections:
            if self in self.end_port.connections:
                self.end_port.connections.remove(self)
        if self.scene():
            self.scene().removeItem(self)


class DeleteButtonItem(QGraphicsEllipseItem):
    def __init__(self, parent_node):
        super().__init__(-6, -6, 12, 12, parent_node)
        self.parent_node = parent_node
        self.setAcceptHoverEvents(True)
        self.setBrush(QBrush(QColor("#ef4444"))) # Red
        self.setPen(QPen(QColor("#0f172a"), 1))
        
        # Add simple "x" text
        self.text = QGraphicsSimpleTextItem("×", self)
        self.text.setFont(QFont("Inter", 8, QFont.Weight.Bold))
        self.text.setBrush(QBrush(QColor("#ffffff")))
        self.text.setPos(-4.5, -7.5)
        
    def hoverEnterEvent(self, event):
        self.setBrush(QBrush(QColor("#b91c1c"))) # Darker red
        super().hoverEnterEvent(event)
        
    def hoverLeaveEvent(self, event):
        self.setBrush(QBrush(QColor("#ef4444")))
        super().hoverLeaveEvent(event)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Delete parent node
            # 1. Delete all connections
            for port in self.parent_node.inputs + self.parent_node.outputs:
                for conn in list(port.connections):
                    conn.delete()
            # 2. Remove node from scene
            scene = self.parent_node.scene()
            if scene:
                scene.removeItem(self.parent_node)
            event.accept()
            return
        super().mousePressEvent(event)


class NodeBlockItem(QGraphicsPathItem):
    def __init__(self, title, node_type, params=None):
        super().__init__()
        self.id = str(uuid.uuid4())
        self.title = title
        self.node_type = node_type
        self.params = params or {}
        
        self.width = 170
        self.height = 95
        
        self.inputs = []
        self.outputs = []
        
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        
        # Delete button at top-right, hidden by default
        self.del_btn = DeleteButtonItem(self)
        self.del_btn.setPos(self.width - 18, 18)
        self.del_btn.setVisible(False)
        
        # Path for overall background rounded rect
        bg_path = QPainterPath()
        bg_path.addRoundedRect(0, 0, self.width, self.height, 8, 8)
        self.setPath(bg_path)
        
        # Fonts
        self.title_item = QGraphicsSimpleTextItem(title, self)
        self.title_item.setFont(QFont("Inter", 9, QFont.Weight.Bold))
        self.title_item.setBrush(QBrush(QColor("#ffffff")))
        self.title_item.setPos(12, 8)
        
        # Subtitle type
        self.type_item = QGraphicsSimpleTextItem(node_type.upper(), self)
        self.type_item.setFont(QFont("Consolas", 6))
        self.type_item.setBrush(QBrush(QColor("#ffffff")))
        self.type_item.setOpacity(0.6)
        self.type_item.setPos(12, 23)
        
    def add_port(self, name, is_output):
        port = PortItem(name, is_output, self)
        if is_output:
            self.outputs.append(port)
        else:
            self.inputs.append(port)
        self.arrange_ports()
        return port

    def remove_output_port(self, name):
        port = next((p for p in self.outputs if p.name == name), None)
        if port:
            for conn in list(port.connections):
                conn.delete()
            self.outputs.remove(port)
            if self.scene():
                self.scene().removeItem(port)
            self.arrange_ports()

    def arrange_ports(self):
        # Dynamic height adaptation based on left/right port counts (excluding condition)
        left_ports_count = sum(1 for p in self.inputs if p.name != "condition")
        max_ports = max(left_ports_count, len(self.outputs))
        new_height = max(95, 42 + max_ports * 20)
        
        if new_height != self.height:
            self.height = new_height
            bg_path = QPainterPath()
            bg_path.addRoundedRect(0, 0, self.width, self.height, 8, 8)
            self.setPath(bg_path)
            
        # Arrange inputs on left
        input_idx = 0
        for port in self.inputs:
            if port.name == "condition":
                port.setPos(self.width / 2, self.height)
                port.label.setPos(-port.label.boundingRect().width() / 2, -18)
            else:
                y = 48 + input_idx * 20
                port.setPos(0, y)
                input_idx += 1
                
        # Arrange outputs on right
        for i, port in enumerate(self.outputs):
            y = 48 + i * 20
            port.setPos(self.width, y)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for port in self.inputs + self.outputs:
                for conn in port.connections:
                    conn.update_path()
        return super().itemChange(change, value)

    def paint(self, painter, option, widget):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw sleek selection border / glow
        if self.isSelected():
            painter.setPen(QPen(QColor(styles.COLOR_PRIMARY), 2))
        else:
            painter.setPen(QPen(QColor("#334155"), 1.2))
            
        # Slate card background
        painter.setBrush(QBrush(QColor("#1e293b")))
        painter.drawRoundedRect(0, 0, self.width, self.height, 8, 8)
        
        # Unreal Engine / Blender style category header coloring
        color_map = {
            "start": QColor("#ef4444"),         # Red
            "end": QColor("#ef4444"),           # Red
            "delay": QColor("#f97316"),         # Orange
            "loop": QColor("#f97316"),          # Orange
            "random_branch": QColor("#f97316"), # Orange
            "if_condition": QColor("#eab308"),  # Yellow
            "send_message": QColor("#3b82f6"),  # Blue
            "join_chat": QColor("#6366f1"),     # Indigo
            "leave_chat": QColor("#a855f7"),    # Purple
            "set_bio": QColor("#10b981"),       # Emerald
            "set_avatar": QColor("#06b6d4"),    # Cyan
            "auto_react": QColor("#ec4899")     # Pink
        }
        header_color = color_map.get(self.node_type)
        if not header_color:
            if self.node_type.startswith("bot_"):
                header_color = QColor("#14b8a6")
            elif self.node_type.startswith("check_"):
                header_color = QColor("#f43f5e") # Rose / Pink
            elif "premium" in self.node_type or self.node_type == "set_emoji_status":
                header_color = QColor("#d97706") # Gold
            elif self.node_type in ["get_post_comments", "ai_prompt", "string_contains", "write_file", "read_file", "get_chat_history_messages", "get_unread_dialogs"]:
                header_color = QColor("#6366f1") # Indigo
            else:
                from src.ui.node_editor.node_specs import NODE_SPECS
                spec = NODE_SPECS.get(self.node_type, {})
                if spec.get("category") == "Плагины":
                    header_color = QColor("#8b5cf6") # Violet
                else:
                    header_color = QColor("#64748b")
        
        # Header path with top rounded corners
        header_path = QPainterPath()
        header_path.moveTo(0, 8)
        header_path.arcTo(0, 0, 16, 16, 180, -90) # Top Left
        header_path.lineTo(self.width - 8, 0)
        header_path.arcTo(self.width - 16, 0, 16, 16, 90, -90) # Top Right
        header_path.lineTo(self.width, 36)
        header_path.lineTo(0, 36)
        header_path.closeSubpath()
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(header_color))
        painter.drawPath(header_path)
        
        # Separator line
        painter.setPen(QPen(QColor("#334155"), 1))
        painter.drawLine(0, 36, self.width, 36)

    def hoverEnterEvent(self, event):
        self.del_btn.setVisible(True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.del_btn.setVisible(False)
        super().hoverLeaveEvent(event)
