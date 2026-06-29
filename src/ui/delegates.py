from PyQt6.QtWidgets import QStyledItemDelegate, QApplication, QStyle, QMenu
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal, QSize, QEvent
from PyQt6.QtGui import QPainter, QColor, QFont, QIcon, QPixmap
from src.ui.models import AccountListModel

class AccountDelegate(QStyledItemDelegate):
    action_requested = pyqtSignal(int, str) # row, action ("start", "stop", "menu")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.btn_width = 100
        self.btn_height = 30
        self.menu_btn_width = 40
        self.margin = 10

    def paint(self, painter, option, index):
        painter.save()
        
        # Background
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor("#333333"))
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(option.rect, QColor("#2A2A2A"))
        else:
            painter.fillRect(option.rect, QColor("#1E1E1E"))
            
        item = index.data(AccountListModel.DataRole)
        if not item:
            painter.restore()
            return
            
        # Draw Checkbox
        checkbox_rect = QRect(option.rect.x() + self.margin, 
                              option.rect.y() + (option.rect.height() - 20) // 2, 
                              20, 20)
        
        from PyQt6.QtWidgets import QStyleOptionButton
        opts = QStyleOptionButton()
        opts.rect = checkbox_rect
        if item.is_checked:
            opts.state = QStyle.StateFlag.State_Enabled | QStyle.StateFlag.State_On
        else:
            opts.state = QStyle.StateFlag.State_Enabled | QStyle.StateFlag.State_Off
        QApplication.style().drawPrimitive(QStyle.PrimitiveElement.PE_IndicatorCheckBox, opts, painter)
        
        # Draw text
        text_rect = QRect(checkbox_rect.right() + 10, option.rect.y(), 300, option.rect.height())
        
        font = painter.font()
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#E0E0E0"))
        
        # Name
        name_rect = QRect(text_rect.x(), text_rect.y() + 10, text_rect.width(), 20)
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, item.config["name"])
        
        # Details
        font.setPointSize(9)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor("#888888"))
        details_rect = QRect(text_rect.x(), name_rect.bottom(), text_rect.width(), 20)
        proxy = item.config.get("proxy_url", "Нет прокси")
        painter.drawText(details_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"Прокси: {proxy}")
        
        # Status
        status_rect = QRect(details_rect.right() + 10, option.rect.y(), 100, option.rect.height())
        status_color = QColor("#4CAF50") if item.status == "Запущен" else QColor("#F44336")
        painter.setPen(status_color)
        painter.drawText(status_rect, Qt.AlignmentFlag.AlignCenter, item.status)
        
        # Menu Button ("...")
        menu_rect = QRect(option.rect.right() - self.margin - self.menu_btn_width,
                          option.rect.y() + (option.rect.height() - self.btn_height) // 2,
                          self.menu_btn_width, self.btn_height)
        
        painter.fillRect(menu_rect, QColor("#333333"))
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(menu_rect, Qt.AlignmentFlag.AlignCenter, "...")
        
        # Start/Stop Button
        btn_rect = QRect(menu_rect.left() - 10 - self.btn_width,
                         option.rect.y() + (option.rect.height() - self.btn_height) // 2,
                         self.btn_width, self.btn_height)
                         
        is_running = item.status == "Запущен"
        btn_color = QColor("#F44336") if is_running else QColor("#4CAF50")
        painter.fillRect(btn_rect, btn_color)
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(btn_rect, Qt.AlignmentFlag.AlignCenter, "Остановить" if is_running else "Запустить")
        
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 60)
        
    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            item = index.data(AccountListModel.DataRole)
            if not item:
                return False
                
            pos = event.pos()
            
            # Checkbox click
            checkbox_rect = QRect(option.rect.x() + self.margin, 
                                  option.rect.y() + (option.rect.height() - 20) // 2, 
                                  20, 20)
            if checkbox_rect.contains(pos):
                model.setData(index, Qt.CheckState.Unchecked if item.is_checked else Qt.CheckState.Checked, Qt.ItemDataRole.CheckStateRole)
                return True
                
            # Menu button click
            menu_rect = QRect(option.rect.right() - self.margin - self.menu_btn_width,
                              option.rect.y() + (option.rect.height() - self.btn_height) // 2,
                              self.menu_btn_width, self.btn_height)
            if menu_rect.contains(pos):
                self.action_requested.emit(index.row(), "menu")
                return True
                
            # Start/Stop button click
            btn_rect = QRect(menu_rect.left() - 10 - self.btn_width,
                             option.rect.y() + (option.rect.height() - self.btn_height) // 2,
                             self.btn_width, self.btn_height)
            if btn_rect.contains(pos):
                action = "stop" if item.status == "Запущен" else "start"
                self.action_requested.emit(index.row(), action)
                return True
                
        return super().editorEvent(event, model, option, index)
