import logging
import copy
from typing import Optional, Union, Any
from pydm.widgets.base import PyDMWritableWidget
from pydm.widgets.pushbutton import PyDMPushButton
from pydm.widgets.related_display_button import PyDMRelatedDisplayButton
from pydm.widgets.shell_command import PyDMShellCommand
from pydm.widgets.enum_button import PyDMEnumButton
from qtpy.QtWidgets import QWidget, QPushButton
from qtpy.QtGui import QIcon
from qtpy.QtCore import Signal, Property, Slot
from comrad.deprecations import deprecated_parent_prop
from comrad.data.channel import CChannelData
from comrad.data.japc_enum import CEnumValue
from .mixins import (CHideUnusedFeaturesMixin, CCustomizedTooltipMixin, CValueTransformerMixin,
                     CWidgetRulesMixin, CInitializedMixin, CChannelDataProcessingMixin)


logger = logging.getLogger(__name__)


class CPushButton(CChannelDataProcessingMixin, CWidgetRulesMixin, CCustomizedTooltipMixin, CInitializedMixin, CHideUnusedFeaturesMixin, PyDMPushButton):

    def __init__(self,
                 parent: Optional[QWidget] = None,
                 label: Optional[str] = None,
                 icon: Optional[QIcon] = None,
                 press_value: Union[str, int, float, None] = None,
                 release_value: Union[str, int, float, None] = None,
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
            release_value: Alternative to ``press_value`` to send the value on button release.
            relative: Choice to have the button perform a relative put, instead of always setting to an absolute value.
            init_channel: ID of channel to manipulate.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        CChannelDataProcessingMixin.__init__(self)
        CWidgetRulesMixin.__init__(self)
        CCustomizedTooltipMixin.__init__(self)
        CInitializedMixin.__init__(self)
        CHideUnusedFeaturesMixin.__init__(self)
        PyDMPushButton.__init__(self, parent=parent,
                                label=label,
                                icon=icon,
                                pressValue=press_value,
                                releaseValue=release_value,
                                relative=relative,
                                init_channel=init_channel,
                                **kwargs)
        self._widget_initialized = True

    def init_for_designer(self):
        super().init_for_designer()
        self.setText('RAD PushButton')

    @Slot()
    def sendValue(self) -> Any:
        """
        Send a new value to the channel.

        This function interprets the settings of the :class:`CPushButton` and sends
        the appropriate value out through the :attr:`send_value_signal`.

        The implementation is copied from :class:`PyDMPushButton` and overridden to take advantage of
        the local conversion logic.

        Returns:
            :obj:`None` if any of the following condition is :obj:`False`:
                #. There's no new value (:attr:`pressValue`) for the widget
                #. There's no initial or current value for the widget
                #. The confirmation dialog returns ``No`` as the user's answer to the dialog
                #. The password validation dialog returns a validation error

            Otherwise, return the value sent to the channel:
                #. The value sent to the channel is the same as the :attr:`pressValue` if the existing
                   channel type is a :obj:`str`, or the :attr:`relative` flag is :obj:`False`
                #. The value sent to the channel is the sum of the existing value and the :attr:`pressValue`
                   if the :attr:`relative` flag is :obj:`True`, and the channel type is not a :obj:`str`
        """
        self._released = False
        val = self.__execute_send(self._pressValue)

        if self._show_confirm_dialog or self._password_protected:
            self.__execute_send(self._releaseValue, is_release=True)

        return val

    @Slot()
    def sendReleaseValue(self) -> Any:
        """
        Send new release value to the channel.

        This function interprets the settings of the :class:`CPushButton` and sends
        the appropriate value out through the :attr:`send_value_signal`.

        The implementation is copied from :class:`PyDMPushButton` and overridden to take advantage of
        the local conversion logic.

        Returns:
            :obj:`None` if any of the following condition is :obj:`False`:
                #. There's no new value (:attr:`releaseValue`) for the widget
                #. There's no initial or current value for the widget
                #. The confirmation dialog returns ``No`` as the user's answer to the dialog
                #. The password validation dialog returns a validation error
                #. :attr:`writeWhenRelease` is :obj:`False`

            Otherwise, return the value sent to the channel:
                #. The value sent to the channel is the same as the :attr:`pressValue` if the existing
                   channel type is a :obj:`str`, or the :attr:`relative` flag is :obj:`False`
                #. The value sent to the channel is the sum of the existing value and the :attr:`pressValue`
                   if the :attr:`relative` flag is :obj:`True`, and the channel type is not a :obj:`str`
        """
        self._released = True
        if self._show_confirm_dialog or self._password_protected:
            # This will be handled via our friend sendValue
            return
        self.__execute_send(self._releaseValue, is_release=True)

    @Slot(int)
    @Slot(float)
    @Slot(str)
    def updatePressValue(self, value: Union[int, float, str]):
        """
        Update the :attr:`pressValue` of a function by passing a signal to the :class:`CPushButton`.

        This is useful to dynamically change the :attr:`pressValue` of the button
        during runtime. This enables the applied value to be linked to the
        state of a different widget, say a :class:`QLineEdit` or :class:`QSlider`.

        The implementation is copied from :class:`PyDMPushButton` and overridden to take advantage of
        the local conversion logic.

        Args:
            value: Incoming value.
        """
        try:
            self.pressValue = self._convert(value)
        except (ValueError, TypeError):
            logger.error(f"'{value}' is not a valid pressValue for '{self.channel}'.")

    @Slot(int)
    @Slot(float)
    @Slot(str)
    def updateReleaseValue(self, value: Union[int, float, str]):
        """
        Update the :attr:`releaseValue` of a function by passing a signal to the :class:`CPushButton`.

        This is useful to dynamically change the :attr:`releaseValue` of the button
        during runtime. This enables the applied value to be linked to the
        state of a different widget, say a :class:`QLineEdit` or :class:`QSlider`.

        The implementation is copied from :class:`PyDMPushButton` and overridden to take advantage of
        the local conversion logic.

        Args:
            value: Incoming value.
        """
        try:
            self.releaseValue = self._convert(value)
        except (ValueError, TypeError):
            logger.error(f"'{value}' is not a valid releaseValue for '{self.channel}'.")

    def _convert(self, value: Union[int, float, str]) -> Any:
        """
        Alternative conversion method to calling ``self.channeltype``, in order to remove quirks.

        Args:
            value: Original (string) value.

        Returns:
            Value of the converted type.
        """
        if self.channeltype == bool and (str(value) == '0' or str(value).lower() == 'false'):
            # allows 0, false, False to specify False values for boolean types
            return False
        return self.channeltype(value)

    @deprecated_parent_prop(logger=logger, property_name='passwordProtected')
    def __set_passwordProtected(self, _):
        pass

    passwordProtected = Property(bool, lambda _: False, __set_passwordProtected, designable=False)

    def __get_password(self) -> str:
        return super().password

    @deprecated_parent_prop(logger=logger, property_name='password')
    def __set_password(self, _):
        pass

    password = Property(str, __get_password, __set_password, designable=False)

    def __get_protectedPassword(self) -> str:
        return super().protectedPassword

    @deprecated_parent_prop(logger=logger, property_name='protectedPassword')
    def __set_protectedPassword(self, _):
        pass

    protectedPassword = Property(str, __get_protectedPassword, __set_protectedPassword, designable=False)

    def __execute_send(self,
                       new_value: Union[int, float, str],
                       skip_confirm: bool = False,
                       skip_password: bool = False,
                       is_release: bool = False):
        """

        Execute the send operation for push and release.

        Args:
            new_value: Value to send.
            skip_confirm: Whether or not to skip the confirmation dialog.
            skip_password: Whether or not to skip the password dialog.
            is_release: Whether or not this method is being invoked to handle a release event.
        """
        send_value = None
        if new_value is None or self.value is None:
            return None

        if is_release and not self._write_when_release:
            return None

        if not skip_confirm and not self.confirm_dialog(is_release=is_release):
            return None

        if not skip_password and not self.validate_password():
            return None

        if not self._relative or self.channeltype == str:
            send_value = self._convert(new_value)
            self.send_value_signal[self.channeltype].emit(send_value)
        else:
            send_value = self.value + self._convert(new_value)
            self.send_value_signal[self.channeltype].emit(send_value)
        return send_value


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
        CValueTransformerMixin.__init__(self)
        PyDMEnumButton.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        self._widget_initialized = True

    def init_for_designer(self):
        super().init_for_designer()
        self.items = ['RAD Item 1', 'RAD Item 2', 'RAD Item ...']

    def value_changed(self, packet: CChannelData[Union[int, CEnumValue]]):
        """
        Overridden data handler to allow JAPC enums coming as tuples.

        Args:
            packet: The new value from the channel.
        """
        if not isinstance(packet, CChannelData):
            return

        new_packet = packet
        if isinstance(packet.value, CEnumValue):
            new_packet = copy.copy(packet)
            try:
                new_packet.value = self.enum_strings.index(packet.value.label)
            except ValueError:
                return
        elif isinstance(packet.value, str):
            new_packet = copy.copy(packet)
            try:
                new_packet.value = self.enum_strings.index(packet.value)
            except ValueError:
                return

        super().value_changed(new_packet)


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
