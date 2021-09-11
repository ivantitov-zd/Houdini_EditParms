import hou
from PySide2.QtCore import Qt, Signal
from PySide2.QtGui import QDoubleValidator
from PySide2.QtWidgets import QHBoxLayout, QSizePolicy
from PySide2.QtWidgets import QWidget, QPushButton, QLabel

from .float_slider import FloatSlider


class ExprParmWidget(QWidget):
    removed = Signal(str)
    valueChanged = Signal()

    def __init__(self, name, value):
        super(ExprParmWidget, self).__init__()
        self._name = name

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._remove_button = QPushButton()
        self._remove_button.setFocusPolicy(Qt.NoFocus)
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
        self._value_field.setValue(value)
        self._value_field.setMinimumWidth(80)
        line_edit = self._value_field.lineEdits[0]
        line_edit.setValidator(QDoubleValidator())
        layout.addWidget(self._value_field)

        self._slider = FloatSlider(default=value)
        self._slider.setFocusPolicy(Qt.ClickFocus)
        self._slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        self._slider.setSingleStep(0.25)
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

    def wheelEvent(self, event):
        sign = 1 if event.angleDelta().y() > 0 else -1
        step = 1 if event.modifiers() & Qt.ControlModifier else 0.25
        self._value_field.setValue(self.value + sign * step)
