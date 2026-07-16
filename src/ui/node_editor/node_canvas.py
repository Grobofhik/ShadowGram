from PyQt6.QtWidgets import QGraphicsView, QGraphicsScene, QMenu
from PyQt6.QtCore import Qt, QPoint, QPointF
from PyQt6.QtGui import QPen, QBrush, QColor, QPainter, QAction
from src.ui.node_editor.node_classes import PortItem, ConnectionItem, NodeBlockItem
from src import styles

class NodeCanvasScene(QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundBrush(QBrush(QColor("#0f172a"))) # Dark background
        self.setSceneRect(-10000, -10000, 20000, 20000) # Infinite virtual space
        self.active_connection = None
        self.grid_size = 20
        
    def drawBackground(self, painter, rect):
        super().drawBackground(painter, rect)
        
        # Draw dotted background grid
        pen = QPen(QColor("#1e293b"), 1)
        painter.setPen(pen)
        
        left = int(rect.left()) - (int(rect.left()) % self.grid_size)
        top = int(rect.top()) - (int(rect.top()) % self.grid_size)
        
        points = []
        for x in range(left, int(rect.right()), self.grid_size):
            for y in range(top, int(rect.bottom()), self.grid_size):
                painter.drawPoint(x, y)

    def mousePressEvent(self, event):
        views = self.views()
        transform = views[0].transform() if views else QGraphicsView().transform()
        item = self.itemAt(event.scenePos(), transform)
        if isinstance(item, PortItem):
            if item.is_output: # Only start connections from output ports
                self.active_connection = ConnectionItem(item, None)
                self.active_connection.temp_end_pos = event.scenePos()
                self.addItem(self.active_connection)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.active_connection:
            self.active_connection.temp_end_pos = event.scenePos()
            self.active_connection.update_path()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.active_connection:
            views = self.views()
            transform = views[0].transform() if views else QGraphicsView().transform()
            item = self.itemAt(event.scenePos(), transform)
            success = False
            if isinstance(item, PortItem) and not item.is_output:
                if item.parent_node != self.active_connection.start_port.parent_node:
                    self.active_connection.end_port = item
                    item.connections.append(self.active_connection)
                    self.active_connection.update_path()
                    self.active_connection = None
                    success = True
                    
                    parent_win = self.parent()
                    if parent_win and hasattr(parent_win, "properties_dock") and parent_win.properties_dock:
                        parent_win.properties_dock.update_properties(self)
            
            if not success:
                self.active_connection.delete()
                self.active_connection = None
            event.accept()
            return
        super().mouseReleaseEvent(event)


class NodeCanvasView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        
        self.is_panning = False
        self.pan_start_pos = QPoint()
        
        # Zoom tracking parameters
        self.zoom_level = 1.0
        self.zoom_min = 0.35 # Maximum zoom out
        self.zoom_max = 2.5  # Maximum zoom in

    def wheelEvent(self, event):
        # Zoom in / out with strict limits
        zoom_factor = 1.15
        if event.angleDelta().y() > 0:
            new_zoom = self.zoom_level * zoom_factor
            if new_zoom <= self.zoom_max:
                self.scale(zoom_factor, zoom_factor)
                self.zoom_level = new_zoom
        else:
            new_zoom = self.zoom_level / zoom_factor
            if new_zoom >= self.zoom_min:
                self.scale(1.0 / zoom_factor, 1.0 / zoom_factor)
                self.zoom_level = new_zoom

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton or (event.button() == Qt.MouseButton.LeftButton and event.modifiers() == Qt.KeyboardModifier.AltModifier):
            self.is_panning = True
            self.pan_start_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_panning:
            delta = event.pos() - self.pan_start_pos
            self.pan_start_pos = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_panning:
            self.is_panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        # Delete selected nodes and connections
        if event.key() == Qt.Key.Key_Delete:
            for item in list(self.scene().selectedItems()):
                if isinstance(item, NodeBlockItem):
                    # Delete all connections first
                    for port in item.inputs + item.outputs:
                        for conn in list(port.connections):
                            conn.delete()
                    self.scene().removeItem(item)
                elif isinstance(item, ConnectionItem):
                    item.delete()
            event.accept()
            return
        super().keyPressEvent(event)
