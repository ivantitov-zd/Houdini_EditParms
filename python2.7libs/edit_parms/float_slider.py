import hou
from PySide2.QtCore import Qt, QEvent
from PySide2.QtGui import QMouseEvent
from PySide2.QtWidgets import QSlider


class FloatSlider(QSlider):
    _float_factor = 100.

    def __init__(self, minimum=0, maximum=100, default=0, orientation=Qt.Horizontal, parent=None):
        super(FloatSlider, self).__init__(orientation, parent)
        self.setRange(minimum, maximum)
        self._default_value = default * self._float_factor
        self.setValue(default)
        self._value_ladder_active = False

    def revertToDefault(self):
        self.setValue(self._default_value)

    def setDefaultValue(self, value):
        self._default_value = value * self._float_factor

    def setMinimum(self, value):
        return super(FloatSlider, self).setMinimum(value * self._float_factor)

    def minimum(self):
        return super(FloatSlider, self).minimum() / self._float_factor

    def setMaximum(self, value):
        return super(FloatSlider, self).setMaximum(value * self._float_factor)

    def maximum(self):
        return super(FloatSlider, self).maximum() / self._float_factor

    def setRange(self, minimum, maximum):
        return super(FloatSlider, self).setRange(minimum * self._float_factor, maximum * self._float_factor)

    def setValue(self, value):
        return super(FloatSlider, self).setValue(value * self._float_factor)

    def value(self):
        return super(FloatSlider, self).value() / self._float_factor

    def setSingleStep(self, value):
        return super(FloatSlider, self).setSingleStep(value * self._float_factor)

    def singleStep(self):
        return float(super(FloatSlider, self).singleStep() / self._float_factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            event = QMouseEvent(QEvent.MouseButtonPress, event.pos(),
                                Qt.MiddleButton, Qt.MiddleButton, Qt.NoModifier)
            super(FloatSlider, self).mousePressEvent(event)
        elif event.button() == Qt.MiddleButton:
            return
        else:
            super(FloatSlider, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MiddleButton:
            if self._value_ladder_active:
                hou.ui.updateValueLadder(event.globalX(), event.globalY(),
                                         bool(event.modifiers() & Qt.AltModifier),
                                         bool(event.modifiers() & Qt.ShiftModifier))
            else:
                hou.ui.openValueLadder(self.value(), self.setValue,
                                       data_type=hou.valueLadderDataType.Float)
                self._value_ladder_active = True
        else:
            super(FloatSlider, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            if self._value_ladder_active:
                self._value_ladder_active = False
                hou.ui.closeValueLadder()
            elif event.modifiers() & Qt.ControlModifier:
                self.revertToDefault()
        else:
            super(FloatSlider, self).mouseReleaseEvent(event)
