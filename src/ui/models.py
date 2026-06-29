from PyQt6.QtCore import QAbstractListModel, Qt, QModelIndex, pyqtSignal
from src.core.managers.process_manager import is_process_running

class AccountItem:
    def __init__(self, config_data):
        self.config = config_data  # dict from config.json
        self.is_checked = False
        self.status = "Остановлен"
        self.tg_process = None
        self.gost_process = None
        self.avatar_pixmap = None

class AccountListModel(QAbstractListModel):
    DataRole = Qt.ItemDataRole.UserRole + 1
    
    def __init__(self, accounts_data=None, parent=None):
        super().__init__(parent)
        self.items = []
        if accounts_data:
            self.load_data(accounts_data)
            
    def load_data(self, accounts_data):
        self.beginResetModel()
        # preserve existing states if possible
        old_states = {item.config["name"]: item for item in self.items}
        self.items = []
        for acc in accounts_data:
            item = AccountItem(acc)
            if acc["name"] in old_states:
                old = old_states[acc["name"]]
                item.is_checked = old.is_checked
                item.status = old.status
                item.tg_process = old.tg_process
                item.gost_process = old.gost_process
                item.avatar_pixmap = old.avatar_pixmap
            self.items.append(item)
        self.endResetModel()
        
    def rowCount(self, parent=QModelIndex()):
        return len(self.items)
        
    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        item = self.items[index.row()]
        
        if role == Qt.ItemDataRole.DisplayRole:
            return item.config["name"]
        elif role == Qt.ItemDataRole.CheckStateRole:
            return Qt.CheckState.Checked if item.is_checked else Qt.CheckState.Unchecked
        elif role == self.DataRole:
            return item
        return None
        
    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if not index.isValid():
            return False
        item = self.items[index.row()]
        
        if role == Qt.ItemDataRole.CheckStateRole:
            item.is_checked = (value == Qt.CheckState.Checked.value)
            self.dataChanged.emit(index, index, [role])
            return True
            
        return False

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsUserCheckable
        
    def update_item_state(self, row, status=None, tg_process=None, gost_process=None):
        if 0 <= row < len(self.items):
            item = self.items[row]
            if status is not None: item.status = status
            if tg_process is not None: item.tg_process = tg_process
            if gost_process is not None: item.gost_process = gost_process
            idx = self.index(row, 0)
            self.dataChanged.emit(idx, idx, [self.DataRole])
