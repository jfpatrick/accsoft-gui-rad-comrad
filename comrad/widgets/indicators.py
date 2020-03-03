import logging
import copy
import numpy as np
from typing import List, Union, Optional, cast
from qtpy.QtWidgets import QWidget
from qtpy.QtCore import Property
from qtpy.QtGui import QColor
from pydm.widgets.base import PyDMWidget
from pydm.widgets.scale import PyDMScaleIndicator
from pydm.widgets.label import PyDMLabel
from pydm.widgets.byte import PyDMByteIndicator
from accwidgets.led import Led
from comrad.deprecations import deprecated_parent_prop
from comrad.data.japc_enum import CEnumValue
from comrad.data.channel import CChannelData
from .mixins import (CHideUnusedFeaturesMixin, CNoPVTextFormatterMixin, CCustomizedTooltipMixin,
                     CValueTransformerMixin, CColorRulesMixin, CWidgetRulesMixin, CInitializedMixin)


logger = logging.getLogger(__name__)


class CLabel(CColorRulesMixin, CValueTransformerMixin, CCustomizedTooltipMixin, CInitializedMixin, CHideUnusedFeaturesMixin, CNoPVTextFormatterMixin, PyDMLabel):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
        """
        A :class:`~PyQt5.QtWidgets.QLabel` with support for setting the text via a control system channel, or
        through the rules system.

        **Note!:** If a :class:`CLabel` is configured to use a :attr:`channel`, and also with a rule
        which changes the :meth:`~PyQt5.QtWidgets.QLabel.text` property, the behavior is undefined. Use either
        the :attr:`channel` *or* a :meth:`~PyQt5.QtWidgets.QLabel.text` rule, but not both.

        Args:
            parent: The parent widget for the label.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        CColorRulesMixin.__init__(self)
        CCustomizedTooltipMixin.__init__(self)
        CInitializedMixin.__init__(self)
        CHideUnusedFeaturesMixin.__init__(self)
        CNoPVTextFormatterMixin.__init__(self)
        CValueTransformerMixin.__init__(self)
        PyDMLabel.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        self._widget_initialized = True

    def init_for_designer(self):
        super().init_for_designer()
        self.setText('RAD TextLabel')

    def setNum(self, new_val: Union[float, int]):
        """
        Callback transforms the directly set numeric value through the
        :attr:`~comrad.widgets.value_transform.CValueTransformationBase.valueTransformation` code before displaying it in a standard way.

        Args:
            new_val: The new value from the channel. The type depends on the channel.
        """
        self.value_changed(CChannelData(value=new_val, meta_info=self.header or {}))

    def set_color(self, val: str):
        """Overridden method of :class:`~comrad.widgets.mixins.CColorRulesMixin`.

        Args:
            val: The new value of the color."""
        super().set_color(val)
        # color = self._default_color if val is None else QColor(val)
        # palette = self.palette()
        # palette.setColor(self.foregroundRole(), color)
        # self.setPalette(palette)
        # We can't use palettes here because custom stylesheet passed via CLI will override it...
        # TODO: Also check QSS dynamic properties and polish/unpolish. But that means we need to parse rules and preset stylesheet before
        self.setStyleSheet(f'color: {val}' if val else None)


# TODO: Expose frame? What is it used for?
# class CFrame(PyDMFrame):
#     pass


class CByteIndicator(CWidgetRulesMixin, CValueTransformerMixin, CCustomizedTooltipMixin, CInitializedMixin, CHideUnusedFeaturesMixin, PyDMByteIndicator):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
        """
        Widget for graphical representation of bits from an integer number
        with support for channels from CS.

        Args:
            parent: The parent widget for the indicator.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        CWidgetRulesMixin.__init__(self)
        CCustomizedTooltipMixin.__init__(self)
        CInitializedMixin.__init__(self)
        CHideUnusedFeaturesMixin.__init__(self)
        CValueTransformerMixin.__init__(self)
        PyDMByteIndicator.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        self._widget_initialized = True

    def value_changed(self, packet: CChannelData[Union[bool, int, List[CEnumValue]]]):
        """
        Slot that accepts types, not natively supported by PyDM
        list: Currently, :mod:`pyjapc` is expected to convert EnumItemSet into ``List[Tuple[code, name]]``.
        bool: Indicator fails to display a single bool value

        :class:`~pydm.widgets.byte.PyDMByteIndicator` expects int value.
        So we construct int from the bit mask expressed by the list.

        Args:
            packet: Incoming value.
        """
        if not isinstance(packet, CChannelData):
            return

        new_packet = copy.copy(packet)
        if isinstance(packet.value, np.ndarray):
            bit_mask = 0
            row_length, = packet.value.shape()
            for (x, y), el in np.ndenumerate(packet.value):
                if int(el) != 0:
                    idx = x * row_length + y
                    bit_mask |= 1 << idx
            new_packet.value = bit_mask
        elif isinstance(packet.value, list):
            bit_mask = 0
            for val in cast(List[CEnumValue], packet.value):
                bit_mask |= val.code
            new_packet.value = bit_mask
        else:
            # Fallback to the original Byte indicator
            new_packet.value = int(packet.value)

        super().value_changed(new_packet)


class CScaleIndicator(CWidgetRulesMixin, CValueTransformerMixin, CCustomizedTooltipMixin, CInitializedMixin, CHideUnusedFeaturesMixin, CNoPVTextFormatterMixin, PyDMScaleIndicator):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
        """
        A bar-shaped indicator for scalar value with support for channels and
        more from the control system.
        Configurable features include indicator type (bar/pointer), scale tick
        marks and orientation (horizontal/vertical).

        Args:
            parent: The parent widget for the indicator.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        CWidgetRulesMixin.__init__(self)
        CCustomizedTooltipMixin.__init__(self)
        CInitializedMixin.__init__(self)
        CHideUnusedFeaturesMixin.__init__(self)
        CNoPVTextFormatterMixin.__init__(self)
        CValueTransformerMixin.__init__(self)
        PyDMScaleIndicator.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        self._limits_from_channel = False
        self._widget_initialized = True

    @deprecated_parent_prop(logger)
    def __set_limitsFromChannel(self, _):
        pass

    limitsFromChannel = Property(bool, lambda _: False, __set_limitsFromChannel, designable=False)


class CLed(CColorRulesMixin, CValueTransformerMixin, CInitializedMixin, CHideUnusedFeaturesMixin, PyDMWidget, Led):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None):
        """
        A :class:`accwidgets.led.Led` with support for channels and more from the control system.

        Args:
            parent: The parent widget for the spinbox.
            init_channel: The channel to be used by the widget.
        """
        CColorRulesMixin.__init__(self)
        CInitializedMixin.__init__(self)
        CHideUnusedFeaturesMixin.__init__(self)
        CValueTransformerMixin.__init__(self)
        Led.__init__(self, parent)
        PyDMWidget.__init__(self, init_channel=init_channel)
        self._on_color = Led.Status.color_for_status(Led.Status.ON)
        self._off_color = Led.Status.color_for_status(Led.Status.OFF)
        self.color = self._off_color

    def _get_on_color(self) -> QColor:
        return self._on_color

    def _set_on_color(self, new_val: QColor):
        self._on_color = new_val

    onColor = Property('QColor', _get_on_color, _set_on_color)
    """Color that is used when incoming boolean value is ``True``."""

    def _get_off_color(self) -> QColor:
        return self._off_color

    def _set_off_color(self, new_val: QColor):
        self._off_color = new_val

    offColor = Property('QColor', _get_off_color, _set_off_color)
    """Color that is used when incoming boolean value is ``False``."""

    def value_changed(self, packet: CChannelData[Union[int, bool, CEnumValue]]):
        """
        Callback invoked when the Channel value is changed.

        Args:
            packet: The new value from the channel.
        """
        if not isinstance(packet, CChannelData):
            return

        color: Optional[QColor] = None
        status: Optional[Led.Status] = None
        if isinstance(packet.value, bool):
            color = self.onColor if packet.value else self.offColor
        elif isinstance(packet.value, int):
            try:
                status = Led.Status(packet.value)
            except ValueError:
                pass
        elif isinstance(packet.value, CEnumValue):
            try:
                status = CLed.meaning_to_status(packet.value.meaning)
            except ValueError:
                pass

        if color is None and status is None:
            return

        super().value_changed(packet)
        if status is not None:
            self.status = status
        else:
            self.color = color

    def __get_color(self) -> QColor:
        return super().color

    def __set_color(self, new_val: QColor):
        Led._set_color_prop_wrapper(self, new_val)

    color: QColor = Property('QColor', __get_color, __set_color, designable=False)
    """Fill color of the LED."""

    def __get_status(self) -> Led.Status:
        return super().status

    def __set_status(self, new_val: Led.Status):
        Led._set_status(self, new_val)

    status = Property(int, __get_status, __set_status, designable=False)
    """Status to switch LED to a predefined color."""

    @staticmethod
    def meaning_to_status(orig_status: CEnumValue.Meaning) -> Led.Status:
        """
        Recognizes and extracts meaning flag from product of japc_plugin and then converts it to status
        understandable by :class:`~accwidgets.led.Led`.

        Args:
            new_val: Meaning of the incoming enum.

        Returns:
            Status corresponding to the meaning.

        Raises:
            ValueError: If input meaning has unexpected value.
        """
        if orig_status == CEnumValue.Meaning.NONE:
            return Led.Status.NONE
        elif orig_status == CEnumValue.Meaning.ON:
            return Led.Status.ON
        elif orig_status == CEnumValue.Meaning.OFF:
            return Led.Status.OFF
        elif orig_status == CEnumValue.Meaning.WARNING:
            return Led.Status.WARNING
        elif orig_status == CEnumValue.Meaning.ERROR:
            return Led.Status.ERROR
        else:
            raise ValueError(f'Cannot correlate LED status with meaning "{orig_status}"')

    def set_color(self, val: str):
        """Overridden method of :class:`~comrad.widgets.mixins.CColorRulesMixin`.

        Args:
            val: The new value of the color."""
        super().set_color(val)
        self.color = self._off_color if val is None else QColor(val)
