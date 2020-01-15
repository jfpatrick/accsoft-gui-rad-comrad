import logging
from typing import Optional
from qtpy.QtWidgets import QWidget
from qtpy.QtCore import Property
from pydm.widgets.line_edit import PyDMLineEdit
from pydm.widgets.slider import PyDMSlider
from pydm.widgets.spinbox import PyDMSpinbox
from pydm.widgets.checkbox import PyDMCheckbox
from pydm.widgets.enum_combo_box import PyDMEnumComboBox
from .mixins import (CHideUnusedFeaturesMixin, CNoPVTextFormatterMixin, CCustomizedTooltipMixin,
                     CValueTransformerMixin, CColorRulesMixin, CWidgetRulesMixin, CInitializedMixin)
from .deprecations import superclass_deprecated


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

    @Property(bool, designable=False)
    def userDefinedLimits(self) -> bool:
        return True

    @userDefinedLimits.setter  # type: ignore
    @superclass_deprecated(logger)
    def userDefinedLimits(self, _):
        pass


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
