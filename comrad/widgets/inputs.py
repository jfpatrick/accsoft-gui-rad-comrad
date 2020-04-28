import logging
from typing import Optional, Dict, Any, Union, cast
from qtpy.QtWidgets import QWidget, QLabel, QComboBox
from qtpy.QtCore import Property, QVariant, Signal
from qtpy.QtGui import QFocusEvent, QGuiApplication, QPalette, QColor
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
from comrad.widgets.indicators import CLed
from comrad.data.japc_enum import CEnumValue
from comrad.data.channel import CChannelData
from comrad.deprecations import deprecated_parent_prop
from .mixins import (CHideUnusedFeaturesMixin, CNoPVTextFormatterMixin, CCustomizedTooltipMixin, CRequestingMixin,
                     CValueTransformerMixin, CColorRulesMixin, CWidgetRulesMixin, CInitializedMixin,
                     CChannelDataProcessingMixin)


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
        CValueTransformerMixin.__init__(self)
        PyDMCheckbox.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
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
        CValueTransformerMixin.__init__(self)
        PyDMEnumComboBox.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        self.setInsertPolicy(QComboBox.NoInsert)
        self._widget_initialized = True

    def value_changed(self, packet: CChannelData[Union[str, int, CEnumValue]]):
        """
        Overridden data handler to allow JAPC enums coming as tuples.

        Args:
            packet: The new value from the channel.
        """
        if not isinstance(packet, CChannelData):
            return

        if isinstance(packet.value, CEnumValue):
            if not packet.value.settable and self.findText(packet.value.label) == -1:
                # Jump over PyDMEnumComboBox to not emit error,
                # but rather display it in the combobox without any other logic involved
                self.setEditable(True)
                self.setEditText(packet.value.label)
                return
            else:
                packet.value = packet.value.label

        self.setEditable(False)
        super().value_changed(packet)

    def focusInEvent(self, e: QFocusEvent) -> None:
        if self.isEditable():
            self.setEditable(False)
        super().focusInEvent(e)


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
        CValueTransformerMixin.__init__(self)
        PyDMLineEdit.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        self._widget_initialized = True

    def set_color(self, val: str):
        """Overridden method of :class:`~comrad.widgets.mixins.CColorRulesMixin`.

        Args:
            val: The new value of the color."""
        if val == self.rule_color():
            return
        super().set_color(val)
        app_palette = QGuiApplication.palette()
        bkg_color = app_palette.color(QPalette.Base) if val is None else QColor(val)
        palette = self.palette()
        palette.setColor(QPalette.Base, bkg_color)

        if val is not None:
            # Invert text color using HSV model to make it readable on the background:
            # https://doc.qt.io/qt-5/qcolor.html#the-hsv-color-model
            brightness = bkg_color.value()
            new_val = 0 if brightness >= 127 else 255
            new_color = QColor.fromHsv(0, 0, new_val)
            palette.setColor(QPalette.Text, new_color)
        else:
            palette.setColor(QPalette.Text, app_palette.color(QPalette.Text))

        # We need custom property for rule_override.qss to detect it,
        # otherwise custom QSS will always override the color
        self.setProperty('rule-override', val is not None)
        self.style().unpolish(self)
        self.style().polish(self)
        self.setPalette(palette)


class CSlider(CWidgetRulesMixin, CValueTransformerMixin, CCustomizedTooltipMixin, CInitializedMixin, CHideUnusedFeaturesMixin, CNoPVTextFormatterMixin, PyDMSlider):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
        """
        A :class:`qtpy.QtWidgets.QSlider` with support for channels and more from the control system.

        Args:
            parent: The parent widget for the slider.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        CChannelDataProcessingMixin.__init__(self)
        CWidgetRulesMixin.__init__(self)
        CCustomizedTooltipMixin.__init__(self)
        CInitializedMixin.__init__(self)
        CHideUnusedFeaturesMixin.__init__(self)
        CNoPVTextFormatterMixin.__init__(self)
        CValueTransformerMixin.__init__(self)
        PyDMSlider.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
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
        CChannelDataProcessingMixin.__init__(self)
        CWidgetRulesMixin.__init__(self)
        CCustomizedTooltipMixin.__init__(self)
        CInitializedMixin.__init__(self)
        CHideUnusedFeaturesMixin.__init__(self)
        CNoPVTextFormatterMixin.__init__(self)
        CValueTransformerMixin.__init__(self)
        PyDMSpinbox.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        self._widget_initialized = True


CPropertyEditField = _PropertyEditField
CAbstractPropertyEditLayoutDelegate = _AbstractPropertyEditLayoutDelegate
CAbstractPropertyEditWidgetDelegate = _AbstractPropertyEditWidgetDelegate


class CPropertyEdit(CChannelDataProcessingMixin, CRequestingMixin, CWidgetRulesMixin, CInitializedMixin, CHideUnusedFeaturesMixin, PropertyEdit, PyDMWritableWidget):

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
        CChannelDataProcessingMixin.__init__(self)
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

    def value_changed(self, packet: CChannelData[Dict[str, Any]]):
        """
        Callback invoked when the Channel value is changed.

        Args:
            packet: The new value from the channel.
        """
        if not isinstance(packet, CChannelData):
            return

        if not isinstance(packet.value, dict):
            return

        super().value_changed(packet)
        self.setValue(packet.value)

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

    class _SensitiveCombobox(QComboBox):

        def focusInEvent(self, e: QFocusEvent) -> None:
            if self.isEditable():
                self.setEditable(False)
            super().focusInEvent(e)

    def create_widget(self,
                      field_id: str,
                      item_type: PropertyEdit.ValueType,
                      editable: bool,
                      user_data: Optional[Dict[str, Any]],
                      parent: Optional[QWidget] = None) -> QWidget:
        if editable and item_type == PropertyEdit.ValueType.ENUM:
            widget = CPropertyEditWidgetDelegate._SensitiveCombobox(parent)
            for label, code in (user_data or {}).get('options', []):
                widget.addItem(label, code)
            return widget

        return super().create_widget(field_id=field_id,
                                     item_type=item_type,
                                     editable=editable,
                                     user_data=user_data,
                                     parent=parent)

    def display_data(self,
                     field_id: str,
                     value: Any,
                     user_data: Optional[Dict[str, Any]],
                     item_type: PropertyEdit.ValueType,
                     widget: QWidget):
        if isinstance(value, CEnumValue):
            if isinstance(widget, Led) and item_type == PropertyEdit.ValueType.BOOLEAN:
                try:
                    value = CLed.meaning_to_status(value.meaning)
                except ValueError:
                    return
            elif item_type == PropertyEdit.ValueType.ENUM:
                if isinstance(widget, QLabel):
                    value = value.code  # Communicate the code to the widget, which will choose the correct text
                elif isinstance(widget, QComboBox):
                    combo = cast(QComboBox, widget)
                    if not value.settable and combo.findText(value.label) == -1:
                        # Jump over PyDMEnumComboBox to not emit error,
                        # but rather display it in the combobox without any other logic involved
                        combo.setEditable(True)
                        combo.setEditText(value.label)
                        return
                    else:
                        combo.setEditable(False)
                        value = value.code

        super().display_data(field_id=field_id,
                             value=value,
                             user_data=user_data,
                             item_type=item_type,
                             widget=widget)
