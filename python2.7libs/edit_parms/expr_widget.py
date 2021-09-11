from __future__ import division

import re

import hou
from PySide2.QtCore import Qt, Signal, QRegExp
from PySide2.QtGui import QRegExpValidator
from PySide2.QtWidgets import QGridLayout, QVBoxLayout, QSizePolicy, QSpacerItem
from PySide2.QtWidgets import QWidget, QLineEdit, QPushButton

from . import utils
from .expr_parm_widget import ExprParmWidget
from .storage import Storage

DEFAULT_EXPR = 'v * k'
EXPR_PATTERN = r'[()\.\w\/\*\-\+_% ]*'
EXPR_VAR_PATTERN = r'[a-zA-Z_]\w*'


class ExprWidget(QWidget):
    needPreview = Signal()

    def __init__(self):
        super(ExprWidget, self).__init__()

        self._var_parms = {}

        main_layout = QGridLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        self._expr_field = QLineEdit()
        expr_validator = QRegExpValidator(QRegExp(EXPR_PATTERN))
        self._expr_field.setValidator(expr_validator)
        self._expr_field.setText(DEFAULT_EXPR)
        self._expr_field.textChanged.connect(self.needPreview)
        main_layout.addWidget(self._expr_field, 0, 0)

        self._create_parms_button = QPushButton()
        self._create_parms_button.setFocusPolicy(Qt.NoFocus)
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

    def selectExpression(self):
        self._expr_field.setFocus()
        v_match = re.match(r'^v\b|\bv$', self.expr)
        if v_match:
            self._expr_field.setSelection(v_match.start() == 0, len(self.expr) - 1)
        else:
            self._expr_field.selectAll()

    @property
    def expr(self):
        """Returns expression."""
        return self._expr_field.text()

    def _removeVariable(self, name):
        """Removes the variable by name. Used on parm widget destruction."""
        self._var_parms.pop(name, None)
        self.needPreview.emit()

    def _createVarParm(self, name, value):
        parm = ExprParmWidget(name, value)
        parm.removed.connect(self._removeVariable)
        parm.valueChanged.connect(self.needPreview)
        return parm

    def createParms(self, values=None):
        """Creates parameters for the expression variables, skipping existing."""
        if values is None:
            values = {}

        for match in re.finditer(EXPR_VAR_PATTERN, self.expr):
            var_name = match.group()
            if var_name == 'v':
                continue

            if var_name in self._var_parms:
                continue

            parm = self._createVarParm(var_name, values.get(var_name, 1))
            self._var_parms[var_name] = parm
            self._parms_layout.addWidget(parm)

    def removeAllParms(self):
        for var_name, parm in self._var_parms.items():
            self._removeVariable(var_name)
            parm.deleteLater()

    def eval(self, value):
        """Evaluates the expression for the given value."""
        var_values = {name: parm.value for name, parm in self._var_parms.items()}
        var_values['v'] = value
        try:
            value = eval(self.expr, {}, var_values)
        except (NameError, AttributeError, ZeroDivisionError) as e:
            hou.ui.setStatusMessage(str(e).replace('name', 'variable'), hou.severityType.Error)
            return
        except SyntaxError as e:
            hou.ui.setStatusMessage(utils.markErrorInExpr(self.expr, e), hou.severityType.Error)
            return
        except Exception:
            hou.ui.setStatusMessage('bad expression', hou.severityType.Error)
            return

        try:
            text, severity = hou.ui.statusMessage()
            if text.startswith('Error:'):
                hou.ui.setStatusMessage('')
        except AttributeError:
            hou.ui.setStatusMessage('')

        return value

    def saveToHistory(self, parm_name):
        """Saves current expression and variable values to the storage."""
        data = {
            'expression': self.expr,
            'variables': {name: parm.value for name, parm in self._var_parms.items()}
        }
        storage = Storage()
        storage.addToHistory(parm_name, data)

    def loadFromHistory(self, parm_name):
        """Loads expression and variable values from the storage."""
        storage = Storage()
        data = storage.setupFromHistory(parm_name)
        if data is None:
            return

        expression = data.get('expression')
        if not expression:
            return
        self._expr_field.setText(expression)

        self.removeAllParms()
        self.createParms(data.get('variables', {}))
