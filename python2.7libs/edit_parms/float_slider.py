from PySide2.QtWidgets import QSlider
from PySide2.QtGui import QMouseEvent
from PySide2.QtCore import Qt, QEvent

import hou


def isRevertToDefaultEvent(event):
    return event.modifiers() == Qt.ControlModifier and event.button() == Qt.MiddleButton


class FloatSlider(QSlider):
    def __init__(self, minimum=0, maximum=100, default=0, orientation=Qt.Horizontal, parent=None):
        super(FloatSlider, self).__init__(orientation, parent)
        self.setRange(minimum, maximum)
        self._default_value = default
        self.setValue(default)
        self._value_ladder_active = False

    def revertToDefault(self):
        self.setValue(self._default_value)

    def setDefaultValue(self, value):
        self._default_value = value * 100

    def setMinimum(self, value):
        raise NotImplementedError  # Todo

    def setMaximum(self, value):
        raise NotImplementedError  # Todo

    def setRange(self, minimum, maximum):
        super(FloatSlider, self).setRange(minimum, (maximum - minimum) * 100 + minimum)

    def setValue(self, value):
        super(FloatSlider, self).setValue(value * 100)

    def value(self):
        return super(FloatSlider, self).value() * 0.01

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:  # Todo: Revert to default
            hou.ui.openValueLadder(self.value(), self.setValue,
                                   data_type=hou.valueLadderDataType.Float)
            self._value_ladder_active = True
        elif event.button() == Qt.LeftButton:
            event = QMouseEvent(QEvent.MouseButtonPress, event.pos(),
                                Qt.MiddleButton, Qt.MiddleButton, Qt.NoModifier)
            super(FloatSlider, self).mousePressEvent(event)
        else:
            super(FloatSlider, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._value_ladder_active:
            hou.ui.updateValueLadder(event.globalX(), event.globalY(),
                                     bool(event.modifiers() & Qt.AltModifier),
                                     bool(event.modifiers() & Qt.ShiftModifier))
        else:
            super(FloatSlider, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._value_ladder_active and event.button() == Qt.MiddleButton:
            hou.ui.closeValueLadder()
            self._value_ladder_active = False
        elif isRevertToDefaultEvent(event):
            self.revertToDefault()
        else:
            super(FloatSlider, self).mouseReleaseEvent(event)
