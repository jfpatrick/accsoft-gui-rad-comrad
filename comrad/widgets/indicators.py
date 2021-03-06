import logging
import copy
import json
import numpy as np
from typing import List, Union, Optional, cast, Dict
from qtpy.QtWidgets import QWidget
from qtpy.QtCore import Property
from qtpy.QtGui import QColor, QPalette, QGuiApplication
from pydm.widgets.scale import PyDMScaleIndicator
from pydm.widgets.label import PyDMLabel
from pydm.widgets.byte import PyDMByteIndicator
from pydm.utilities import is_qt_designer
from accwidgets.led import Led
from comrad.deprecations import deprecated_parent_prop
from comrad.data.japc_enum import CEnumValue
from comrad.data.channel import CChannelData
from .widget import PyDMWidget
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
        if val == self.rule_color():
            return
        super().set_color(val)
        color = QGuiApplication.palette().color(QPalette.WindowText) if val is None else QColor(val)
        palette = self.palette()
        palette.setColor(QPalette.WindowText, color)
        # We need custom property for rule_override.qss to detect it,
        # otherwise custom QSS will always override the color
        self.setProperty('rule-override', val is not None)
        self.style().unpolish(self)
        self.style().polish(self)
        self.setPalette(palette)

    def value_changed(self, packet: CChannelData[Union[bool, int, str, float, CEnumValue]]):
        """
        Slot that accepts types, not natively supported by PyDM
        CEnumValue: This will display either code or label of the enum, based on the display format.

        Args:
            packet: Incoming value.
        """
        if not isinstance(packet, CChannelData):
            return

        if isinstance(packet.value, CEnumValue) and self.displayFormat != self.DisplayFormat.Default:
            new_packet = copy.copy(packet)
            if self.displayFormat == self.DisplayFormat.String:
                new_packet.value = packet.value.label
            else:
                new_packet.value = packet.value.code
            super().value_changed(new_packet)
        else:
            super().value_changed(packet)


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
        list: Currently, :mod:`comrad.data.pyjapc_patch` is expected to convert EnumItemSet into ``List[CEnumValue]``.
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

    @deprecated_parent_prop(logger=logger, property_name='limitsFromChannel')
    def __set_limitsFromChannel(self, _):
        pass

    limitsFromChannel = Property(bool, lambda _: False, __set_limitsFromChannel, designable=False)


class CLed(CColorRulesMixin, CValueTransformerMixin, CInitializedMixin, CHideUnusedFeaturesMixin, CCustomizedTooltipMixin, PyDMWidget, Led):

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
        self._color_map: Dict[int, QColor] = {}
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

    def _get_color_map(self) -> Dict[int, QColor]:
        if is_qt_designer():
            return self.__pack_designer_color_map(self._color_map)  # type: ignore  # we want string here for Designer
        return self._color_map

    def _set_color_map(self, new_val: Dict[int, QColor]):
        if isinstance(new_val, str):  # Can happen inside the Designer or when initializing from *.ui file
            new_val = self._unpack_designer_color_map(cast(str, new_val))
        self._color_map = new_val

    color_map: Dict[int, QColor] = Property(str, fget=_get_color_map, fset=_set_color_map, designable=False)
    """
    Color mapping for arbitrary values that can be received by :class:`CLed`, e.g when working with enums.
    When working with boolean values only, consider :attr:`onColor` and :attr:`offColor`.
    """

    def value_changed(self, packet: CChannelData[Union[int, bool, CEnumValue]]):
        """
        Callback invoked when the channel value is changed.

        Args:
            packet: The new value from the channel.
        """
        if not isinstance(packet, CChannelData):
            return

        color: Optional[QColor] = None
        status: Optional[Led.Status] = None
        if self._color_map:
            key: Optional[int]
            if isinstance(packet.value, CEnumValue):
                key = packet.value.code
            elif isinstance(packet.value, int) and not isinstance(packet.value, bool):
                key = packet.value
            else:
                key = None
            if key is not None:
                try:
                    color = self._color_map[key]
                except KeyError:
                    pass

        if color is None:
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
            elif isinstance(packet.value, QColor):
                color = packet.value

        if color is None and status is None:
            return

        super().value_changed(packet)
        if status is not None:
            self.status = status
        else:
            self.color = color

    color: QColor = Property('QColor', Led.color.fget, Led.color.fset, designable=False)
    """Fill color of the LED."""

    status = Property(int, Led.status.fget, Led.status.fset, designable=False)
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

    @classmethod
    def _unpack_designer_color_map(cls, input: str) -> Dict[int, QColor]:
        try:
            contents = json.loads(input)
        except json.JSONDecodeError as ex:
            logger.warning(f'Failed to decode json: {ex!s}')
            return {}

        if not isinstance(contents, dict):
            logger.warning('Decoded color map is not a dictionary')
            return {}

        try:
            return {int(val): QColor(color) for val, color in contents.items()}
        except ValueError as ex:
            logger.warning(f'Failed to parse color map: {ex!s}')
            return {}

    @classmethod
    def __pack_designer_color_map(cls, input: Dict[int, QColor]) -> str:
        return json.dumps({str(val): color.name() for val, color in input.items()})
