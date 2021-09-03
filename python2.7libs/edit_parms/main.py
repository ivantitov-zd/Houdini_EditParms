import re

from PySide2.QtCore import Qt, QRegExp, Signal
from PySide2.QtGui import QRegExpValidator
from PySide2.QtWidgets import QDialog, QWidget, QTabWidget
from PySide2.QtWidgets import QGridLayout, QHBoxLayout, QVBoxLayout, QSizePolicy, QSpacerItem
from PySide2.QtWidgets import QLineEdit, QPushButton, QLabel

import hou

from .float_slider import FloatSlider

HOUDINI_PARM_PATH_MIME_FORMAT = 'application/sidefx-houdini-parm.path'
HOUDINI_NODE_PATH_MIME_FORMAT = 'application/sidefx-houdini-node.path'

DEFAULT_EXPR = 'v * a + b'
EXPR_PATTERN = r'[()\.\w\/\*\-\+_% ]*'
EXPR_PARM_PATTERN = r'[a-zA-Z_]\w*'


class ExprParmWidget(QWidget):
    removed = Signal(str)
    valueChanged = Signal()

    def __init__(self, name):
        super(ExprParmWidget, self).__init__()
        self._name = name

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._remove_button = QPushButton()
        self._remove_button.setFixedWidth(self._remove_button.sizeHint().height())
        self._remove_button.setIcon(hou.qt.Icon('BUTTONS_multi_remove', 16, 16))
        self._remove_button.setToolTip('Remove parameter.')
        self._remove_button.clicked.connect(self._remove)
        layout.addWidget(self._remove_button)

        self._name_label = QLabel(name)
        self._name_label.setToolTip('Variable: ' + name)
        self._name_label.setMinimumWidth(20)
        self._name_label.setMaximumWidth(50)
        self._name_label.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Ignored)
        layout.addWidget(self._name_label)

        self._value_field = hou.qt.InputField(hou.qt.InputField.FloatType, 1)
        self._value_field.setMinimumWidth(80)
        layout.addWidget(self._value_field)

        self._slider = FloatSlider()
        self._slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        layout.addWidget(self._slider)

        self._value_field.valueChanged.connect(self._setSliderValue)
        self._slider.valueChanged.connect(self._setFieldValue)

    def _setFieldValue(self):
        """Prevents cyclic changes."""
        self._value_field.blockSignals(True)
        self._value_field.setValue(self._slider.value())
        self._value_field.blockSignals(False)
        self.valueChanged.emit()

    def _setSliderValue(self):
        """Prevents cyclic changes."""
        self._slider.blockSignals(True)
        self._slider.setValue(self._value_field.value())
        self._slider.blockSignals(False)
        self.valueChanged.emit()

    @property
    def name(self):
        """Returns stored read-only variable name."""
        return self._name

    @property
    def value(self):
        """Returns current value of the field."""
        return self._value_field.value()

    def _remove(self):
        """Removes item and emits signal with the variable name."""
        self.removed.emit(self.name)
        self.deleteLater()


class ExprWidget(QWidget):
    needPreview = Signal()

    def __init__(self):
        super(ExprWidget, self).__init__()

        self._variables = {}

        main_layout = QGridLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        self._expr_field = QLineEdit()
        self._expr_field.setText(DEFAULT_EXPR)
        expr_validator = QRegExpValidator(QRegExp(EXPR_PATTERN))
        self._expr_field.setValidator(expr_validator)
        self._expr_field.textChanged.connect(self.needPreview)
        main_layout.addWidget(self._expr_field, 0, 0)

        self._create_parms_button = QPushButton()
        self._create_parms_button.setFixedWidth(self._create_parms_button.sizeHint().height())
        self._create_parms_button.setIcon(hou.qt.Icon('BUTTONS_create_parm_from_ch', 16, 16))
        self._create_parms_button.setToolTip('Create parameters for the expression variables.')
        self._create_parms_button.clicked.connect(self.createParms)
        main_layout.addWidget(self._create_parms_button, 0, 1)

        self._parms_layout = QVBoxLayout()
        self._parms_layout.setContentsMargins(0, 0, 0, 0)
        self._parms_layout.setSpacing(4)
        main_layout.addLayout(self._parms_layout, 1, 0, 1, -1)

        spacer = QSpacerItem(0, 0, QSizePolicy.Ignored, QSizePolicy.Expanding)
        main_layout.addItem(spacer, 2, 0, 1, -1)

    @property
    def expr(self):
        """Returns expression."""
        return self._expr_field.text()

    def _removeVariable(self, name):
        """Removes the variable by name. Used on parm widget destruction."""
        self._variables.pop(name, None)
        self.needPreview.emit()

    def createParms(self):
        """Creates parameters for the expression variables, skipping existing."""
        for match in re.finditer(EXPR_PARM_PATTERN, self.expr):
            var_name = match.group()
            if var_name == 'v':
                continue

            if var_name in self._variables:
                continue

            parm = ExprParmWidget(var_name)
            parm.removed.connect(self._removeVariable)
            parm.valueChanged.connect(self.needPreview)
            self._variables[var_name] = parm
            self._parms_layout.addWidget(parm)

    def eval(self, value):
        """Evaluates the expression for the given value."""
        var_values = {name: parm.value for name, parm in self._variables.items()}
        var_values['v'] = value
        try:
            value = eval(self.expr, {}, var_values)
        except Exception as e:
            hou.ui.setStatusMessage(str(e), hou.severityType.Error)
            return

        try:
            text, severity = hou.ui.statusMessage()
            if text.startswith('Error:'):
                hou.ui.setStatusMessage('')
        except AttributeError:
            hou.ui.setStatusMessage('')

        return value


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

        self._add_nodes_button = QPushButton()
        self._add_nodes_button.setFixedWidth(self._add_nodes_button.sizeHint().height())
        self._add_nodes_button.setIcon(hou.qt.Icon('BUTTONS_list_add', 16, 16))
        self._add_nodes_button.setToolTip('Add selected nodes.')
        # self._add_nodes_button.clicked.connect(self.createParms)
        layout.addWidget(self._add_nodes_button, 0, 0)

        self._add_parms_button = QPushButton()
        self._add_parms_button.setFixedWidth(self._add_parms_button.sizeHint().height())
        self._add_parms_button.setIcon(hou.qt.Icon('BUTTONS_list_add', 16, 16))
        self._add_parms_button.setToolTip('Choose and add parameters.')
        # self._add_parms_button.clicked.connect(self.createParms)
        layout.addWidget(self._add_parms_button, 0, 1)

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
        self.needPreview.emit()

    def parms(self):
        """Returns all parameters and their data."""
        return self._parms.copy()


class EditParmsWindow(QDialog):
    def __init__(self, source_parm=None, parent=hou.qt.mainWindow()):
        super(EditParmsWindow, self).__init__(parent)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setAcceptDrops(True)

        self.updateWindowTitle()
        self.setWindowIcon(hou.qt.Icon('PANETYPES_parameters', 32, 32))
        self.resize(300, 300)

        layout = QGridLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self._tabs = QTabWidget()
        layout.addWidget(self._tabs, 0, 0, 1, -1)

        self._expr = ExprWidget()
        self._tabs.addTab(self._expr, hou.qt.Icon('DATATYPES_code_function', 16, 16), 'Expression')

        self._parm_list = ParmsWidget()
        self._parm_list.sourceParmChanged.connect(self.updateWindowTitle)
        self._parm_list.setSourceParm(source_parm)
        self._parm_list.addParms([source_parm])
        # self._tabs.addTab(self._parm_list, hou.qt.Icon('NETVIEW_image_link_located', 16, 16), 'Parameters')

        self._cancel_button = QPushButton('Cancel')
        self._cancel_button.clicked.connect(self.cancel)
        layout.addWidget(self._cancel_button, 1, 0)

        self._apply_button = QPushButton('Apply')
        self._apply_button.clicked.connect(self.apply)
        layout.addWidget(self._apply_button, 1, 1)

        self._expr.needPreview.connect(self.preview)
        self._parm_list.needPreview.connect(self.preview)

    def preview(self):
        """
        Sets new values to the parameters without adding actions
        to the undo stack.
        """
        with hou.undos.disabler():
            for parm, data in self._parm_list.parms().items():
                new_value = self._expr.eval(data['initial'])
                parm.set(new_value)

    def cancel(self):
        """
        Sets the initial values to the parameters without adding actions
        to the undo stack.
        """
        with hou.undos.disabler():
            for parm, data in self._parm_list.parms().items():
                parm.set(data['initial'])
        self.close()

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
            self.setWindowTitle('Edit Parms')
        else:
            self.setWindowTitle('Edit [{}]'.format(parm.name()))
