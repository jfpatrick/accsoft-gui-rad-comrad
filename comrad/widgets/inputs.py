import logging
from typing import Optional, Dict, Any, cast
from qtpy.QtWidgets import QWidget, QLabel, QComboBox
from qtpy.QtCore import Property, QVariant, Signal, Slot
from pydm.widgets.base import PyDMWritableWidget
from pydm.widgets.line_edit import PyDMLineEdit
from pydm.widgets.slider import PyDMSlider
from pydm.widgets.spinbox import PyDMSpinbox
from pydm.widgets.checkbox import PyDMCheckbox
from pydm.widgets.enum_combo_box import PyDMEnumComboBox
from accwidgets.property_edit import (PropertyEdit, PropertyEditField as _PropertyEditField,
                                      AbstractPropertyEditLayoutDelegate as _AbstractPropertyEditLayoutDelegate,
                                      AbstractPropertyEditWidgetDelegate as _AbstractPropertyEditWidgetDelegate)
from accwidgets.property_edit.propedit import PropertyEditWidgetDelegate as _PropertyEditWidgetDelegate
from accwidgets.led import Led
from comrad.widgets.indicators import CLed, _JapcEnum
from comrad.deprecations import deprecated_parent_prop
from .mixins import (CHideUnusedFeaturesMixin, CNoPVTextFormatterMixin, CCustomizedTooltipMixin, CRequestingMixin,
                     CValueTransformerMixin, CColorRulesMixin, CWidgetRulesMixin, CInitializedMixin)


logger = logging.getLogger(__name__)


class CCheckBox(CWidgetRulesMixin, CValueTransformerMixin, CCustomizedTooltipMixin, CInitializedMixin, CHideUnusedFeaturesMixin, PyDMCheckbox):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
        """
        A :class:`qtpy.QtWidgets.QCheckBox` with support for channels from the control system.

        Args:
            parent: The parent widget for the checkbox.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        CWidgetRulesMixin.__init__(self)
        CCustomizedTooltipMixin.__init__(self)
        CInitializedMixin.__init__(self)
        CHideUnusedFeaturesMixin.__init__(self)
        PyDMCheckbox.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        CValueTransformerMixin.__init__(self)
        self._widget_initialized = True

    def init_for_designer(self):
        super().init_for_designer()
        self.setText('RAD CheckBox')


class CEnumComboBox(CWidgetRulesMixin, CValueTransformerMixin, CCustomizedTooltipMixin, CInitializedMixin, CHideUnusedFeaturesMixin, PyDMEnumComboBox):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
        """
        A :class:`qtpy.QtWidgets.QComboBox` with support for channels from the control system.

        Signals:
         - send_value_signal: Emitted when the user changes the value.
         - activated: Emitted when the user chooses an item in the combobox.
         - currentIndexChanged: Emitted when the index is changed in the combobox.
         - highlighted: Emitted when an item in the combobox popup list is highlighted by the user.

        Args:
            parent: The parent widget for the combobox.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        CWidgetRulesMixin.__init__(self)
        CCustomizedTooltipMixin.__init__(self)
        CInitializedMixin.__init__(self)
        CHideUnusedFeaturesMixin.__init__(self)
        PyDMEnumComboBox.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        CValueTransformerMixin.__init__(self)
        self._widget_initialized = True

    def value_changed(self, new_val: Any):
        """
        Overridden data handler to allow JAPC enums coming as tuples.

        Args:
            new_val: The new value from the channel.
        """
        if isinstance(new_val, tuple):
            option_name = new_val[1]
            super().value_changed(option_name)
        else:
            super().value_changed(new_val)

    @Slot(QVariant)
    def channelValueChanged(self, new_val: Any):
        """Overridden method to define custom slot overload."""
        super().channelValueChanged(new_val)


class CLineEdit(CColorRulesMixin, CValueTransformerMixin, CCustomizedTooltipMixin, CInitializedMixin, CHideUnusedFeaturesMixin, CNoPVTextFormatterMixin, PyDMLineEdit):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
        """

        A :class:`PyQt5.QtWidgets.QLineEdit` (writable text field) with support for CS channels.
        This widget offers an unit conversion menu when users Right Click
        into it.

        Args:
            parent: The parent widget for the line edit.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        CColorRulesMixin.__init__(self)
        CCustomizedTooltipMixin.__init__(self)
        CInitializedMixin.__init__(self)
        CHideUnusedFeaturesMixin.__init__(self)
        CNoPVTextFormatterMixin.__init__(self)
        PyDMLineEdit.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        CValueTransformerMixin.__init__(self)
        self._widget_initialized = True

    def set_color(self, val: str):
        """Overridden method of :class:`~comrad.widgets.mixins.CColorRulesMixin`.

        Args:
            val: The new value of the color."""
        super().set_color(val)
        self.setStyleSheet(f'background-color: {val}' if val else None)
        # TODO: Calculate color and choose appropriate text color by the contrast ratio


class CSlider(CWidgetRulesMixin, CValueTransformerMixin, CCustomizedTooltipMixin, CInitializedMixin, CHideUnusedFeaturesMixin, CNoPVTextFormatterMixin, PyDMSlider):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
        """
        A :class:`qtpy.QtWidgets.QSlider` with support for channels and more from the control system.

        Args:
            parent: The parent widget for the slider.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        CWidgetRulesMixin.__init__(self)
        CCustomizedTooltipMixin.__init__(self)
        CInitializedMixin.__init__(self)
        CHideUnusedFeaturesMixin.__init__(self)
        CNoPVTextFormatterMixin.__init__(self)
        PyDMSlider.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        CValueTransformerMixin.__init__(self)
        self._user_defined_limits = True
        self._widget_initialized = True

    @deprecated_parent_prop(logger)
    def __set_userDefinedLimits(self, _):
        pass

    userDefinedLimits = Property(bool, lambda _: True, __set_userDefinedLimits, designable=False)


class CSpinBox(CWidgetRulesMixin, CValueTransformerMixin, CCustomizedTooltipMixin, CInitializedMixin, CHideUnusedFeaturesMixin, CNoPVTextFormatterMixin, PyDMSpinbox):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
        """
        A :class:`qtpy.QtWidgets.QDoubleSpinBox` with support for channels and more from the control system.

        Args:
            parent: The parent widget for the spinbox.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        CWidgetRulesMixin.__init__(self)
        CCustomizedTooltipMixin.__init__(self)
        CInitializedMixin.__init__(self)
        CHideUnusedFeaturesMixin.__init__(self)
        CNoPVTextFormatterMixin.__init__(self)
        PyDMSpinbox.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        CValueTransformerMixin.__init__(self)
        self._widget_initialized = True


CPropertyEditField = _PropertyEditField
CAbstractPropertyEditLayoutDelegate = _AbstractPropertyEditLayoutDelegate
CAbstractPropertyEditWidgetDelegate = _AbstractPropertyEditWidgetDelegate


class CPropertyEdit(CRequestingMixin, CWidgetRulesMixin, CInitializedMixin, CHideUnusedFeaturesMixin, PropertyEdit, PyDMWritableWidget):

    send_value_signal = Signal(QVariant)
    """Overridden signal to define custom overload."""

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, title: Optional[str] = None):
        """
        A :class:`accwidgets.property_edit.PropertyEdit` with support for channels and more from the control system.

        Args:
            parent: The parent widget for the spinbox.
            init_channel: The channel to be used by the widget.
            title: Optional title to be displayed when selected style is GroupBox.
        """
        CRequestingMixin.__init__(self)
        CWidgetRulesMixin.__init__(self)
        CInitializedMixin.__init__(self)
        CHideUnusedFeaturesMixin.__init__(self)
        PropertyEdit.__init__(self, parent=parent, title=title)
        PyDMWritableWidget.__init__(self, init_channel=init_channel)
        self._alarm_sensitive_border = False
        self.widget_delegate = CPropertyEditWidgetDelegate()
        self.valueUpdated.connect(self.send_value_signal[QVariant].emit)
        self.valueRequested.connect(self.request_data)

    def value_changed(self, new_val: Dict[str, Any]):
        """
        Callback invoked when the Channel value is changed.

        Args:
            new_val: The new value from the channel.
        """
        if not isinstance(new_val, dict):
            return

        super().value_changed(new_val)
        self.setValue(new_val)

    @Slot(QVariant)
    def channelValueChanged(self, new_val: Dict[str, Any]):
        """Overridden method to define custom slot overload."""
        super().channelValueChanged(new_val)

    @PropertyEdit.buttons.setter
    def buttons(self, new_val: PropertyEdit.Buttons):
        """
        Overridden in order to regulate default slot connection (when "Get" button is present,
        we do not want to receive values via SUBSCRIBE).
        """
        PropertyEdit.buttons.fset(self, new_val)
        disable_subscribe = bool(new_val & PropertyEdit.Buttons.GET)
        self.connect_value_slot = not disable_subscribe


class CPropertyEditWidgetDelegate(_PropertyEditWidgetDelegate):
    """
    Subclass to make sure that tuple-based enums with meaning can be represented correctly by inner LEDs.
    """
    def display_data(self,
                     field_id: str,
                     value: Any,
                     user_data: Optional[Dict[str, Any]],
                     item_type: PropertyEdit.ValueType,
                     widget: QWidget):
        if isinstance(value, tuple) and len(value) == 4:  # Enum tuples
            if isinstance(widget, Led) and item_type == PropertyEdit.ValueType.BOOLEAN:
                try:
                    value = CLed.meaning_to_status(cast(_JapcEnum, value))
                except ValueError:
                    return
            elif item_type == PropertyEdit.ValueType.ENUM:
                if isinstance(widget, QLabel) or isinstance(widget, QComboBox):
                    value = value[0]  # Communicate the code to the widget, which will choose the correct text
        super().display_data(field_id=field_id,
                             value=value,
                             user_data=user_data,
                             item_type=item_type,
                             widget=widget)
