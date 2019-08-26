import logging
from typing import Union
from pydm.widgets.pushbutton import PyDMPushButton
from qtpy.QtCore import Property, Signal
from qtpy.QtWidgets import QWidget
from qtpy.QtGui import QIcon


logger = logging.getLogger(__file__)


class CToggleButton(PyDMPushButton):

    inverseToggled = Signal([bool])

    def __init__(self,
                 parent: QWidget = None,
                 label: str = None,
                 icon: QIcon = None,
                 pressValue: Union[int, float, str] = None,
                 relative: bool = False,
                 init_channel: str = None, **kwargs):
        """
        A toggle-button that brings some extra convenience features.

        Args:
            parent: The parent widget for the button.
            label: String to place on the button.
            icon: An Icon to display on the button.
            pressValue: Value to be sent when the button is clicked.
            relative: Choice to have the button perform a relative put, instead of always setting to an absolute value.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        super().__init__(parent=parent,
                         label=label,
                         icon=icon,
                         pressValue=pressValue,
                         relative=relative,
                         init_channel=init_channel,
                         **kwargs)
        super().setCheckable(True)
        self._unchecked_text: str = self.text
        self._checked_text: str = self.text
        self.toggled.connect(self._on_checked)

    def getCheckedText(self) -> str:
        return self._checked_text

    def setCheckedText(self, new_val: str):
        if new_val != self._checked_text:
            self._checked_text = new_val
            self._on_checked(self.isChecked())

    # This is the way to preserve 'setCheckedText' as a method, while maintaining checkedText property-style assignment
    checkedText = Property(str, getCheckedText, setCheckedText)

    def getUncheckedText(self) -> str:
        return self._unchecked_text

    def setUncheckedText(self, new_val: str):
        if new_val != self._unchecked_text:
            self._unchecked_text = new_val
            self._on_checked(self.isChecked())

    # This is the way to preserve 'setUncheckedText' as a method, while maintaining checkedText property-style assignment
    uncheckedText = Property(str, getUncheckedText, setUncheckedText)

    @Property(bool, designable=False)
    def checkable(self):
        return super().isCheckable()

    @Property(str, designable=False)
    def text(self) -> str:
        return super().text()

    def _on_checked(self, checked: bool):
        super().setText(self._checked_text if checked else self._unchecked_text)
        self.inverseToggled.emit(not checked)

    def setCheckable(self, val: bool):
        """Overrides to prevent from resetting it."""
        pass