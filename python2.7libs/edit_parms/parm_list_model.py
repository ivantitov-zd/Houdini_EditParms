from PySide2.QtCore import QAbstractListModel, Qt
from PySide2.QtGui import QIcon, QPixmap

import hou

EMPTY_ICON = QIcon(QPixmap(16, 16))


class ParmListModel(QAbstractListModel):
    def __init__(self, parent=None):
        super(ParmListModel, self).__init__(parent)

        self._parms = ()

    def setParmList(self, parms):
        self.beginResetModel()
        self._parms = tuple(parms)
        self.endResetModel()

    def rowCount(self, parent=None):
        return len(self._parms)

    def data(self, index, role=None):
        if not index.isValid():
            return

        parm = self._parms[index.row()]

        if role == Qt.DisplayRole:
            return parm.path()
        elif role == Qt.DecorationRole:
            try:
                return hou.qt.Icon(parm.node().type().icon(), 16, 16)
            except hou.OperationFailed:
                return EMPTY_ICON
        elif role == Qt.ToolTipRole:
            return parm.description()
        elif role == Qt.UserRole:
            return parm
