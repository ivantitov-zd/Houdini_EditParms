import hou
from PySide2.QtCore import Qt
from PySide2.QtGui import QKeySequence
from PySide2.QtWidgets import QDialog, QAction
from PySide2.QtWidgets import QGridLayout
from PySide2.QtWidgets import QTabWidget, QPushButton

from .expr_widget import ExprWidget
from .parms_widget import ParmsWidget

HOUDINI_PARM_PATH_MIME_FORMAT = 'application/sidefx-houdini-parm.path'
HOUDINI_NODE_PATH_MIME_FORMAT = 'application/sidefx-houdini-node.path'


class MainWindow(QDialog):
    def __init__(self, parms=None, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setAcceptDrops(True)

        self.updateWindowTitle()
        self.setWindowIcon(hou.qt.Icon('PANETYPES_parameters', 32, 32))
        self.resize(300, 300)

        layout = QGridLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self._tabs = QTabWidget()
        self._tabs.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self._tabs, 0, 0, 1, -1)

        self._expr = ExprWidget()
        self._tabs.addTab(self._expr, hou.qt.Icon('DATATYPES_code_function', 16, 16), 'Expression')

        self._parm_list = ParmsWidget()
        self._parm_list.sourceParmChanged.connect(self.updateWindowTitle)
        self._tabs.addTab(self._parm_list, hou.qt.Icon('NETVIEW_image_link_located', 16, 16), 'Parameters')

        self._cancel_button = QPushButton('Cancel')
        self._cancel_button.setFocusPolicy(Qt.NoFocus)
        self._cancel_button.clicked.connect(self.reject)
        layout.addWidget(self._cancel_button, 1, 0)

        self._apply_button = QPushButton('Apply')
        self._apply_button.setFocusPolicy(Qt.NoFocus)
        self._apply_button.setDefault(True)
        self._apply_button.clicked.connect(self.accept)
        layout.addWidget(self._apply_button, 1, 1)

        self._expr.needPreview.connect(self.preview)
        self._parm_list.needPreview.connect(self.preview)

        if parms:
            self._expr.loadFromHistory(parms[0].name())
            self._parm_list.setSourceParm(parms[0])
            self._parm_list.addParms(parms)

        self._remove_library_action = QAction('Remove', self)
        self._remove_library_action.triggered.connect(self._parm_list.removeSelected)
        self._remove_library_action.setShortcut(QKeySequence.Delete)
        self._remove_library_action.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        self._parm_list.addAction(self._remove_library_action)

    def preview(self):
        """
        Sets new values to the parameters without adding actions
        to the undo stack.
        """
        with hou.undos.disabler():
            for parm, data in self._parm_list.parms().items():
                parm.set(self._expr.eval(data['initial']))

    def cancel(self):
        """
        Sets the initial values to the parameters without adding actions
        to the undo stack.
        """
        with hou.undos.disabler():
            for parm, data in self._parm_list.parms().items():
                parm.set(data['initial'])

    def apply(self):
        """
        Sets new values to the parameters grouped into the single action
        on the undo stack.
        """
        with hou.undos.disabler():
            for parm, data in self._parm_list.parms().items():
                parm.set(data['initial'])

        with hou.undos.group('Apply expression to parms'):
            for parm, data in self._parm_list.parms().items():
                new_value = self._expr.eval(data['initial'])
                parm.set(new_value)
        self.close()

    def dragEnterEvent(self, event):
        mime_data = event.mimeData()
        if (mime_data.hasFormat(HOUDINI_PARM_PATH_MIME_FORMAT) or
                mime_data.hasFormat(HOUDINI_NODE_PATH_MIME_FORMAT)):
            event.accept()

    def dropEvent(self, event):
        mime_data = event.mimeData()
        parms = []

        if mime_data.hasFormat(HOUDINI_PARM_PATH_MIME_FORMAT):
            for parm_path in str(mime_data.data(HOUDINI_PARM_PATH_MIME_FORMAT)).split('\t'):
                parms.append(hou.parm(parm_path))

        if mime_data.hasFormat(HOUDINI_NODE_PATH_MIME_FORMAT):
            source_parm = self._parm_list.sourceParm()
            source_parm_name = source_parm.name() if source_parm else None
            for node_path in str(mime_data.data(HOUDINI_NODE_PATH_MIME_FORMAT)).split('\t'):
                node = hou.node(node_path)
                if source_parm_name:
                    for parm in node.parms():
                        if parm.name() == source_parm_name:
                            parms.append(parm)
                else:
                    parms.extend(node.parms())

        self._parm_list.addParms(parms)

    def updateWindowTitle(self, parm=None):
        if not parm:
            self.setWindowTitle('No current parameter')
        else:
            self.setWindowTitle('Current parameter [{}]'.format(parm.name()))

    def showEvent(self, event):
        self._expr.createParms()
        self._expr.selectExpression()
        super(MainWindow, self).showEvent(event)

    def hideEvent(self, event):
        if self.result() == QDialog.Accepted:
            self.apply()
            parm_names = set(parm.name() for parm in self._parm_list.parms())
            for name in parm_names:
                self._expr.saveToHistory(name)
        else:
            self.cancel()
        super(MainWindow, self).hideEvent(event)
