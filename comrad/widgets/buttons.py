import logging
from typing import Optional, Union
from pydm.widgets.base import PyDMWritableWidget
from pydm.widgets.pushbutton import PyDMPushButton
from pydm.widgets.related_display_button import PyDMRelatedDisplayButton
from pydm.widgets.shell_command import PyDMShellCommand
from pydm.widgets.enum_button import PyDMEnumButton
from qtpy.QtWidgets import QWidget, QPushButton
from qtpy.QtGui import QIcon
from qtpy.QtCore import Signal, Property
from comrad.deprecations import deprecated_parent_prop
from .mixins import CHideUnusedFeaturesMixin, CCustomizedTooltipMixin, CValueTransformerMixin, CWidgetRulesMixin, CInitializedMixin


logger = logging.getLogger(__name__)


class CPushButton(CWidgetRulesMixin, CCustomizedTooltipMixin, CInitializedMixin, CHideUnusedFeaturesMixin, PyDMPushButton):

    def __init__(self,
                 parent: Optional[QWidget] = None,
                 label: Optional[str] = None,
                 icon: Optional[QIcon] = None,
                 press_value: Union[str, int, float, None] = None,
                 relative: bool = False,
                 init_channel: Optional[str] = None,
                 **kwargs):
        """
        Basic push-button to send a fixed value.

        This type is meant to hold a specific value, and send that value
        to a channel when it is clicked. It works in two different modes of operation:

            1. A fixed value can be given to the ``press_value`` argument. Whenever the
               button is clicked a signal containing this value will be sent to the connected channel.
               This is the default behavior of the button.
            2. However, if the ``relative`` is set to ``True``, the fixed value will be added
               to the current value of the channel. This means that the button will increment a channel by
               a fixed amount with every click, a consistent relative move.

        Args:
            parent: The parent widget for the button.
            label: String to place on button.
            icon: An icon to display on the button.
            press_value: Value to be sent when the button is clicked.
            relative: Choice to have the button perform a relative put, instead of always setting to an absolute value.
            init_channel: ID of channel to manipulate.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        CWidgetRulesMixin.__init__(self)
        CCustomizedTooltipMixin.__init__(self)
        CInitializedMixin.__init__(self)
        CHideUnusedFeaturesMixin.__init__(self)
        PyDMPushButton.__init__(self, parent=parent,
                                label=label,
                                icon=icon,
                                pressValue=press_value,
                                relative=relative,
                                init_channel=init_channel,
                                **kwargs)
        self._widget_initialized = True

    def init_for_designer(self):
        super().init_for_designer()
        self.setText('RAD PushButton')

    @Property(bool, designable=False)
    def passwordProtected(self) -> bool:
        return False

    @passwordProtected.setter  # type: ignore
    @deprecated_parent_prop(logger)
    def passwordProtected(self, _):
        pass

    @Property(str, designable=False)
    def password(self) -> str:
        return super().password

    @password.setter  # type: ignore
    @deprecated_parent_prop(logger)
    def password(self, _):
        pass

    @Property(str, designable=False)
    def protectedPassword(self) -> str:
        return super().protectedPassword

    @protectedPassword.setter  # type: ignore
    @deprecated_parent_prop(logger)
    def protectedPassword(self, _):
        pass


class CRelatedDisplayButton(PyDMRelatedDisplayButton):

    def __init__(self, parent: Optional[QWidget] = None, filename: Optional[str] = None, **kwargs):
        """
        A :class:`~PyQt5.QtWidgets.QPushButton` capable of opening a new :class:`CDisplay` at the same of at a new window.

        Args:
            parent: The parent widget for the button.
            filename: The file to be opened.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        super().__init__(parent=parent, filename=filename, **kwargs)


class CShellCommand(PyDMShellCommand):

    def __init__(self, parent: Optional[QWidget] = None, command: Optional[str] = None, **kwargs):
        """
        A :class:`~PyQt5.QtWidgets.QPushButton` capable of executing shell commands.

        Args:
            parent: The parent widget for the button.
            command: Command to execute.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        super().__init__(parent=parent, command=command, **kwargs)


class CEnumButton(CWidgetRulesMixin, CValueTransformerMixin, CCustomizedTooltipMixin, CInitializedMixin, CHideUnusedFeaturesMixin, PyDMEnumButton):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
        """
        A :class:`~PyQt5.QtWidgets.QWidget` that renders buttons for every option of enum items.
        For now three types of buttons can be rendered:

        - Push button
        - Radio button

        Signals:
            send_value_signal: Emitted when the user changes the value.

        Args:
            parent: The parent widget for the button.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        CWidgetRulesMixin.__init__(self)
        CCustomizedTooltipMixin.__init__(self)
        CInitializedMixin.__init__(self)
        CHideUnusedFeaturesMixin.__init__(self)
        PyDMEnumButton.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        CValueTransformerMixin.__init__(self)
        self._widget_initialized = True

    def init_for_designer(self):
        super().init_for_designer()
        self.items = ['RAD Item 1', 'RAD Item 2', 'RAD Item ...']


class CCommandButton(CCustomizedTooltipMixin, QPushButton, CInitializedMixin, CHideUnusedFeaturesMixin, PyDMWritableWidget):

    send_value_signal = Signal()
    """Overridden channel to allow only dictionaries."""

    def __init__(self,
                 parent: Optional[QWidget] = None,
                 label: Optional[str] = None,
                 icon: Optional[QIcon] = None,
                 init_channel: Optional[str] = None):
        """
        A push-button that allows to send a command to the control system.

        Args:
            parent: The parent widget for the button.
            label: String to place on the button.
            icon: An Icon to display on the button.
            init_channel: The channel to be used by the widget.
        """

        if icon:
            QPushButton.__init__(self, icon, label, parent)
        elif label:
            QPushButton.__init__(self, label, parent)
        else:
            QPushButton.__init__(self, parent)
        CCustomizedTooltipMixin.__init__(self)
        CInitializedMixin.__init__(self)
        CHideUnusedFeaturesMixin.__init__(self)
        PyDMWritableWidget.__init__(self, init_channel=init_channel)
        self._widget_initialized = True
        self.clicked.connect(self._send_cmd)

    channelValueChanged = None  # Prevent widget from subscribing

    def init_for_designer(self):
        super().init_for_designer()
        self.setText('RAD CommandButton')

    def _send_cmd(self):
        # Commands are supposed to be properties without fields, thus we are
        # sending signal without value, that will be recognized by japc_plugin
        # as command
        self.send_value_signal.emit()


# Do not use unless there's a use-case for that
# class CToggleButton(CWidgetRulesMixin, CInitializedMixin, CHideUnusedFeaturesMixin, PyDMPushButton):
#
#     inverseToggled = Signal([bool])
#
#     def __init__(self,
#                  parent: Optional[QWidget] = None,
#                  label: Optional[str] = None,
#                  icon: Optional[QIcon] = None,
#                  pressValue: Union[int, float, str, None] = None,
#                  relative: bool = False,
#                  init_channel: Optional[str] = None, **kwargs):
#         """
#         A toggle-button that brings some extra convenience features.
#
#         Args:
#             parent: The parent widget for the button.
#             label: String to place on the button.
#             icon: An Icon to display on the button.
#             pressValue: Value to be sent when the button is clicked.
#             relative: Choice to have the button perform a relative put, instead of always setting to an absolute value.
#             init_channel: The channel to be used by the widget.
#             **kwargs: Any future extras that need to be passed down to PyDM.
#         """
#         CWidgetRulesMixin.__init__(self)
#         CInitializedMixin.__init__(self)
#         CHideUnusedFeaturesMixin.__init__(self)
#         PyDMPushButton.__init__(self,
#                                 parent=parent,
#                                 label=label,
#                                 icon=icon,
#                                 pressValue=pressValue,
#                                 relative=relative,
#                                 init_channel=init_channel,
#                                 **kwargs)
#         super().setCheckable(True)
#         self._widget_initialized = True
#         self._unchecked_text: str = self.text
#         self._checked_text: str = self.text
#         self.toggled.connect(self._on_checked)
#
#     def init_for_designer(self):
#         super().init_for_designer()
#         self.setUncheckedText('RAD Toggle Released')
#         self.setCheckedText('RAD Toggle Pressed')
#
#     def _getCheckedText(self) -> str:
#         return self._checked_text
#
#     def setCheckedText(self, new_val: str):
#         """
#         Sets text for the button in the "checked" state.
#
#         Args:
#             new_val: New text.
#         """
#         if new_val != self._checked_text:
#             self._checked_text = new_val
#             self._on_checked(self.isChecked())
#
#     # This is the way to preserve 'setCheckedText' as a method, while maintaining checkedText property-style assignment
#     checkedText: str = Property(str, _getCheckedText, setCheckedText)
#     """Text for the button in the "checked" state."""
#
#     def _getUncheckedText(self) -> str:
#         return self._unchecked_text
#
#     def setUncheckedText(self, new_val: str):
#         """
#         Sets text for the button in the "unchecked" state.
#
#         Args:
#             new_val: New text.
#         """
#         if new_val != self._unchecked_text:
#             self._unchecked_text = new_val
#             self._on_checked(self.isChecked())
#
#     # This is the way to preserve 'setUncheckedText' as a method, while maintaining checkedText property-style assignment
#     uncheckedText: str = Property(str, _getUncheckedText, setUncheckedText)
#     """Text for the button in the "unchecked" state."""
#
#     @Property(bool, designable=False)
#     def checkable(self):
#         return super().isCheckable()
#
#     @Property(str, designable=False)
#     def text(self) -> str:
#         return super().text()
#
#     def _on_checked(self, checked: bool):
#         super().setText(self._checked_text if checked else self._unchecked_text)
#         self.inverseToggled.emit(not checked)
#
#     def setCheckable(self, val: bool):
#         """Overrides to prevent from resetting it."""
#         pass
