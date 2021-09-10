from PySide2.QtCore import Signal, Qt
from PySide2.QtWidgets import QGridLayout, QSizePolicy, QSpacerItem
from PySide2.QtWidgets import QWidget, QPushButton, QListView

import hou

from .parm_list_model import ParmListModel


class ParmsWidget(QWidget):
    sourceParmChanged = Signal(hou.Parm)
    needPreview = Signal()

    def __init__(self):
        super(ParmsWidget, self).__init__()

        self._source_parm = None
        self._parms = {}

        layout = QGridLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self._unbind_button = QPushButton()
        self._unbind_button.setFixedWidth(self._unbind_button.sizeHint().height())
        self._unbind_button.setIcon(hou.qt.Icon('BUTTONS_list_delete', 16, 16))
        self._unbind_button.setToolTip('Unbind selected parameters.\tDelete')
        self._unbind_button.clicked.connect(self.removeSelected)
        layout.addWidget(self._unbind_button, 0, 0)

        self._set_as_source_button = QPushButton()
        self._set_as_source_button.setFixedWidth(self._set_as_source_button.sizeHint().height())
        self._set_as_source_button.setIcon(hou.qt.Icon('BUTTONS_link', 16, 16))
        self._set_as_source_button.setToolTip('Set as current.')
        self._set_as_source_button.clicked.connect(self.setCurrentAsSource)
        layout.addWidget(self._set_as_source_button, 0, 1)

        spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Ignored)
        layout.addItem(spacer, 0, 2, 1, -1)

        self._view = QListView()
        self._view.setSelectionMode(QListView.ExtendedSelection)
        layout.addWidget(self._view, 1, 0, 1, -1)

        self._model = ParmListModel(self)
        self._view.setModel(self._model)

        spacer = QSpacerItem(0, 0, QSizePolicy.Ignored, QSizePolicy.Expanding)
        layout.addItem(spacer, 1, 0, 1, -1)

    def setSourceParm(self, parm):
        """
        Sets parameter as the source. This parameter will be used to match
        names of the added node parameters.
        """
        self._source_parm = parm
        self.sourceParmChanged.emit(parm)

    def sourceParm(self):
        return self._source_parm

    def setCurrentAsSource(self):
        index = self._view.currentIndex()
        if not index.isValid():
            return

        self.setSourceParm(index.data(Qt.UserRole))

    def _updateParmList(self):
        self._model.setParmList(self._parms.keys())

    def removeSelected(self):
        """Unbind selected parameters."""
        with hou.undos.disabler():
            for index in self._view.selectedIndexes():
                parm = index.data(Qt.UserRole)
                parm_data = self._parms[parm]
                parm.set(parm_data['initial'])
                self._parms.pop(parm, None)
        self._updateParmList()
        self.needPreview.emit()

    def addParms(self, parms):
        """
        Adds parameters to the list. Already added parameters will be skipped.
        """
        for parm in parms:
            if not parm:
                continue

            if parm.isLocked():
                continue

            if parm in self._parms:
                continue

            parm_template = parm.parmTemplate()
            if parm_template.type() not in (hou.parmTemplateType.Int, hou.parmTemplateType.Float):
                continue

            self._parms[parm] = {
                'initial': parm.eval(),
            }
        self._updateParmList()
        self.needPreview.emit()

    def parms(self):
        """Returns all parameters and their data."""
        return self._parms.copy()
