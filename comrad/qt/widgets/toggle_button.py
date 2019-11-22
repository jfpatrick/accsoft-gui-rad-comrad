import logging
from typing import Union, Optional
from pydm.widgets.pushbutton import PyDMPushButton
from qtpy.QtCore import Property, Signal
from qtpy.QtWidgets import QWidget
from qtpy.QtGui import QIcon
from ..rules import WidgetRulesMixin


logger = logging.getLogger(__name__)


class CToggleButton(WidgetRulesMixin, PyDMPushButton):

    inverseToggled = Signal([bool])

    def __init__(self,
                 parent: Optional[QWidget] = None,
                 label: Optional[str] = None,
                 icon: Optional[QIcon] = None,
                 pressValue: Union[int, float, str, None] = None,
                 relative: bool = False,
                 init_channel: Optional[str] = None, **kwargs):
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
        WidgetRulesMixin.__init__(self)
        PyDMPushButton.__init__(self,
                                parent=parent,
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

    def _getCheckedText(self) -> str:
        return self._checked_text

    def setCheckedText(self, new_val: str):
        """
        Sets text for the button in the "checked" state.

        Args:
            new_val: New text.
        """
        if new_val != self._checked_text:
            self._checked_text = new_val
            self._on_checked(self.isChecked())

    # This is the way to preserve 'setCheckedText' as a method, while maintaining checkedText property-style assignment
    checkedText: str = Property(str, _getCheckedText, setCheckedText)
    """Text for the button in the "checked" state."""

    def _getUncheckedText(self) -> str:
        return self._unchecked_text

    def setUncheckedText(self, new_val: str):
        """
        Sets text for the button in the "unchecked" state.

        Args:
            new_val: New text.
        """
        if new_val != self._unchecked_text:
            self._unchecked_text = new_val
            self._on_checked(self.isChecked())

    # This is the way to preserve 'setUncheckedText' as a method, while maintaining checkedText property-style assignment
    uncheckedText: str = Property(str, _getUncheckedText, setUncheckedText)
    """Text for the button in the "unchecked" state."""

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
