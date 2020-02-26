import logging
import numpy as np
from typing import List, Tuple, Union, Optional, cast
from qtpy.QtWidgets import QWidget
from qtpy.QtCore import Slot, Property, QVariant
from qtpy.QtGui import QColor
from pydm.widgets.base import PyDMWidget
from pydm.widgets.scale import PyDMScaleIndicator
from pydm.widgets.label import PyDMLabel
from pydm.widgets.byte import PyDMByteIndicator
from accwidgets.led import Led
from comrad.deprecations import deprecated_parent_prop
from comrad.data.japc_enum import SimpleValueStandardMeaning
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
        PyDMLabel.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        CValueTransformerMixin.__init__(self)
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
        self.value_changed(new_val)

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
        PyDMByteIndicator.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        CValueTransformerMixin.__init__(self)
        self._widget_initialized = True

    @Slot(list)
    @Slot(bool)
    @Slot(int)
    @Slot(float)
    @Slot(str)
    @Slot(np.ndarray)
    def channelValueChanged(self, new_val: Union[bool, int, List[Tuple[int, str]]]):
        """
        Slot that accepts types, not natively supported by PyDM
        list: Currently, :mod:`pyjapc` is expected to convert EnumItemSet into ``List[Tuple[code, name]]``.
        bool: Indicator fails to display a single bool value

        :class:`~pydm.widgets.byte.PyDMByteIndicator` expects int value.
        So we construct int from the bit mask expressed by the list.

        Args:
            new_val: Incoming value.
        """
        if isinstance(new_val, np.ndarray):
            bit_mask = 0
            row_length, = new_val.shape()
            for (x, y), el in np.ndenumerate(new_val):
                if int(el) != 0:
                    idx = x * row_length + y
                    bit_mask |= 1 << idx
            PyDMByteIndicator.channelValueChanged(self, bit_mask)
        elif isinstance(new_val, list):
            bit_mask = 0
            for val, _ in new_val:
                bit_mask |= val
            PyDMByteIndicator.channelValueChanged(self, bit_mask)
        else:
            # Fallback to the original Byte indicator
            PyDMByteIndicator.channelValueChanged(self, int(new_val))


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
        PyDMScaleIndicator.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        CValueTransformerMixin.__init__(self)
        self._limits_from_channel = False
        self._widget_initialized = True

    @Property(bool, designable=False)
    def limitsFromChannel(self) -> bool:
        return False

    @limitsFromChannel.setter  # type: ignore
    @deprecated_parent_prop(logger)
    def limitsFromChannel(self, _):
        pass


_JapcEnum = Tuple[int, str, SimpleValueStandardMeaning, bool]


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
        Led.__init__(self, parent)
        PyDMWidget.__init__(self, init_channel=init_channel)
        CValueTransformerMixin.__init__(self)
        self._on_color = Led.Status.color_for_status(Led.Status.ON)
        self._off_color = Led.Status.color_for_status(Led.Status.OFF)

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

    def value_changed(self, new_val: Union[int, bool, _JapcEnum]):
        """
        Callback invoked when the Channel value is changed.

        Args:
            new_val: The new value from the channel.
        """
        color: Optional[QColor] = None
        status: Optional[Led.Status] = None
        if isinstance(new_val, bool):
            color = self.onColor if new_val else self.offColor
        elif isinstance(new_val, int):
            try:
                status = Led.Status(new_val)
            except ValueError:
                pass
        elif isinstance(new_val, tuple) and len(new_val) == 4:
            orig_status = cast(_JapcEnum, new_val)[2]
            if orig_status == SimpleValueStandardMeaning.NONE:
                status = Led.Status.NONE
            elif orig_status == SimpleValueStandardMeaning.ON:
                status = Led.Status.ON
            elif orig_status == SimpleValueStandardMeaning.OFF:
                status = Led.Status.OFF
            elif orig_status == SimpleValueStandardMeaning.WARNING:
                status = Led.Status.WARNING
            elif orig_status == SimpleValueStandardMeaning.ERROR:
                status = Led.Status.ERROR

        if color is None and status is None:
            return

        super().value_changed(new_val)
        if status is not None:
            self.status = status  # type: ignore
        else:
            self.color = color  # type: ignore

    @Slot(QVariant)
    @Slot(bool)
    @Slot(int)
    def channelValueChanged(self, new_val: Union[int, bool, _JapcEnum]):
        """Overridden method to define custom slot overload."""
        super().channelValueChanged(new_val)

    @Property('QColor', designable=False)
    def color(self) -> QColor:
        return super().color

    @color.setter  # type: ignore
    def color(self, new_val: QColor):
        Led._set_color_prop_wrapper(self, new_val)

    @Property(int, designable=False)
    def status(self) -> Led.Status:
        return super().status

    @status.setter  # type: ignore
    def status(self, new_val: Led.Status):
        Led._set_status(self, new_val)
