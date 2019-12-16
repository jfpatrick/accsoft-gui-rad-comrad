from typing import Optional
from qtpy.QtWidgets import QWidget
from pydm.widgets.line_edit import PyDMLineEdit
from pydm.widgets.slider import PyDMSlider
from pydm.widgets.spinbox import PyDMSpinbox
from pydm.widgets.checkbox import PyDMCheckbox
from pydm.widgets.enum_combo_box import PyDMEnumComboBox
from .mixins import (HideUnusedFeaturesMixin, NoPVTextFormatterMixin, CustomizedTooltipMixin,
                     ValueTransformerMixin, ColorRulesMixin, WidgetRulesMixin)


class CCheckBox(WidgetRulesMixin, ValueTransformerMixin, CustomizedTooltipMixin, HideUnusedFeaturesMixin, PyDMCheckbox):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
        """
        A :class:`qtpy.QCheckbox` with support for Channels from the control system.

        Args:
            parent: The parent widget for the checkbox.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        WidgetRulesMixin.__init__(self)
        CustomizedTooltipMixin.__init__(self)
        HideUnusedFeaturesMixin.__init__(self)
        PyDMCheckbox.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        ValueTransformerMixin.__init__(self)

    def init_for_designer(self):
        super().init_for_designer()
        self.setText('RAD CheckBox')


class CEnumComboBox(WidgetRulesMixin, ValueTransformerMixin, CustomizedTooltipMixin, HideUnusedFeaturesMixin, PyDMEnumComboBox):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
        """
        A :class:`qtpy.QComboBox` with support for Channels from the control system.

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
        WidgetRulesMixin.__init__(self)
        CustomizedTooltipMixin.__init__(self)
        HideUnusedFeaturesMixin.__init__(self)
        PyDMEnumComboBox.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        ValueTransformerMixin.__init__(self)


class CLineEdit(ColorRulesMixin, ValueTransformerMixin, CustomizedTooltipMixin, HideUnusedFeaturesMixin, NoPVTextFormatterMixin, PyDMLineEdit):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
        """

        A :class:`qtpy.QLineEdit` (writable text field) with support for CS Channels.
        This widget offers an unit conversion menu when users Right Click
        into it.

        Args:
            parent: The parent widget for the line edit.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        ColorRulesMixin.__init__(self)
        CustomizedTooltipMixin.__init__(self)
        HideUnusedFeaturesMixin.__init__(self)
        NoPVTextFormatterMixin.__init__(self)
        PyDMLineEdit.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        ValueTransformerMixin.__init__(self)

    def set_color(self, val: str):
        """Overridden method of :class:`ColorRulesMixin`.

        Args:
            val: The new value of the color."""
        super().set_color(val)
        self.setStyleSheet(f'background-color: {val}' if val else None)
        # TODO: Calculate color and choose appropriate text color by the contrast ratio


class CSlider(WidgetRulesMixin, ValueTransformerMixin, CustomizedTooltipMixin, HideUnusedFeaturesMixin, NoPVTextFormatterMixin, PyDMSlider):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
        """
        A :class:`qtpy.QSlider` with support for Channels and more from the control system.

        Args:
            parent: The parent widget for the slider.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        WidgetRulesMixin.__init__(self)
        CustomizedTooltipMixin.__init__(self)
        HideUnusedFeaturesMixin.__init__(self)
        NoPVTextFormatterMixin.__init__(self)
        PyDMSlider.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        ValueTransformerMixin.__init__(self)


class CSpinBox(WidgetRulesMixin, ValueTransformerMixin, CustomizedTooltipMixin, HideUnusedFeaturesMixin, NoPVTextFormatterMixin, PyDMSpinbox):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
        """
        A :class:`qtpy.QDoubleSpinBox` with support for Channels and more from the control system.

        Args:
            parent: The parent widget for the spinbox.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        WidgetRulesMixin.__init__(self)
        CustomizedTooltipMixin.__init__(self)
        HideUnusedFeaturesMixin.__init__(self)
        NoPVTextFormatterMixin.__init__(self)
        PyDMSpinbox.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        ValueTransformerMixin.__init__(self)
