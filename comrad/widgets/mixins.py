import json
import logging
from typing import Any, List, cast, Union, Dict, Tuple, Callable
from qtpy.QtCore import Property
from qtpy.QtWidgets import QWidget
from pydm.utilities import is_qt_designer
from pydm.widgets.base import PyDMWidget
from pydm.widgets.rules import RulesDispatcher
from comrad.rules import BaseRule, CChannelException, unpack_rules
from comrad.json import ComRADJSONEncoder, JSONDeserializeError
from .value_transform import ValueTransformationBase
from .deprecations import superclass_deprecated


logger = logging.getLogger(__name__)


class InitializedMixin:

    def __init__(self):
        """Simple mixin to set a flag when __init__ method has finished the sequence."""
        self._widget_initialized = False


class HideUnusedFeaturesMixin:
    """Mixin that hides PyDM properties that are exposed to Qt Designer and are not used in ComRAD."""

    @Property(bool, designable=False)
    def alarmSensitiveBorder(self) -> bool:
        return False

    @alarmSensitiveBorder.setter  # type: ignore
    @superclass_deprecated(logger)
    def alarmSensitiveBorder(self, _):
        pass

    @Property(bool, designable=False)
    def alarmSensitiveContent(self) -> bool:
        return False

    @alarmSensitiveContent.setter  # type: ignore
    @superclass_deprecated(logger)
    def alarmSensitiveContent(self, _):
        pass


class NoPVTextFormatterMixin:
    """
    Mixin that hides PyDM properties in :class:`pydm.widgets.base.TextFormatter` that are exposed to
    Qt Designer and are not used in ComRAD.
    """

    @Property(bool, designable=False)
    def precisionFromPV(self) -> bool:
        return False

    @precisionFromPV.setter  # type: ignore
    @superclass_deprecated(logger)
    def precisionFromPV(self, _):
        pass

    # TODO: We should enable showUnits, when unit support is implemented on the CS level
    @Property(bool, designable=False)
    def showUnits(self) -> bool:
        return False

    @showUnits.setter  # type: ignore
    @superclass_deprecated(logger)
    def showUnits(self, _):
        pass


class CustomizedTooltipMixin:
    """Mixin that customizes the message passed into the :meth:`qtpy.QWidget.tooltip()`."""

    def setToolTip(self, tooltip: str):
        """
        Re-implements Qt method to look for specific keywords and replace them.

        Args:
            tooltip:  widget's tooltip.
        """
        cast(QWidget, super()).setToolTip(tooltip.replace('PyDM', 'ComRAD').replace('PV ', 'Device Property '))


class ValueTransformerMixin(ValueTransformationBase):
    """Mixin that introduces valueTransformation property for client-side Python snippets acting on incoming values."""

    def getValueTransformation(self) -> str:
        return ValueTransformationBase.getValueTransformation(self)

    def setValueTransformation(self, new_formatter: str):
        """
        Reset generator code snippet.

        Args:
            new_val: New Python code snippet.
        """
        if self.getValueTransformation() != str(new_formatter):
            ValueTransformationBase.setValueTransformation(self, str(new_formatter))
            self.value_changed(self.value)  # type: ignore   # This is coming from PyDMWidget

    def value_changed(self, new_val: Any) -> None:
        """
        Callback transforms the Channel value through the :attr:`ValueTransformationBase.valueTransformation`
        code before displaying it in a standard way.

        Args:
            new_val: The new value from the channel. The type depends on the channel.
        """
        if is_qt_designer():
            val = new_val  # Avoid code evaluation in Designer, as it can produce unnecessary errors with broken code
        else:
            transform = self.cached_value_transformation()
            val = transform(new_val=new_val, widget=self) if transform else new_val
        super().value_changed(val)  # type: ignore


class WidgetRulesMixin:
    """
    Common rules mixin for all ComRAD widgets that limits the amount of properties for our widgets
    and ensures the synchronization between channel setter and rules setter regardless of the order.
    """

    DEFAULT_RULE_PROPERTY = 'Visibility'
    """Default rule property visible in the dialog."""

    RULE_PROPERTIES: Dict[str, Tuple[str, Callable[[Any], Any]]] = {
        BaseRule.Property.ENABLED.value: ('setEnabled', bool),
        BaseRule.Property.VISIBILITY.value: ('setVisible', bool),
        BaseRule.Property.OPACITY.value: ('set_opacity', float),
    }
    """All available rule properties with associated callbacks and data types."""

    def default_rule_channel(self) -> str:
        """
        Default channel to be used in the rule evaluation.

        Returns:
            Address of the channel.
        """
        try:
            return PyDMWidget.channel.fget(self)  # cast(PyDMWidget, self).channel
        except AttributeError:
            raise AttributeError(f'Rule is not supposed to be used with {type(self).__name__}, as it does not have a'
                                 f' default channel.')

    # We override the following setters to ensure that when unpacked from Designer file
    # the order of reading out these properties does not impact how they are processed.
    @PyDMWidget.channel.setter
    def channel(self, value: str):
        PyDMWidget.channel.fset(self, value)
        # Reset the rules once again (the inner data structure should have been reset, that
        # setter logic works again
        if value is not None:
            base = cast(PyDMWidget, self)
            rules = base._rules
            base._rules = None
            base.rules = rules

    def _get_custom_rules(self) -> List[BaseRule]:
        rules = cast(PyDMWidget, self)._rules
        if is_qt_designer():
            return cast(List[BaseRule], json.dumps(rules, cls=ComRADJSONEncoder))
        return rules

    def _set_custom_rules(self, new_rules: Union[str, List[BaseRule], None]):
        if isinstance(new_rules, str):
            try:
                new_rules = unpack_rules(new_rules)
            except (json.JSONDecodeError, JSONDeserializeError) as e:
                logger.exception(f'Invalid JSON format for rules: {str(e)}')
                return
        cast(PyDMWidget, self)._rules = new_rules
        if new_rules is None:
            return
        try:
            RulesDispatcher().register(widget=self, rules=new_rules)
        except CChannelException:
            logger.debug(f'Rules setting failed. We do not have the channel yet, will have to be repeated')
            # Set internal data structure without activating property setter behavior
            cast(PyDMWidget, self)._rules = new_rules

    rules: List[BaseRule] = Property(type=str, fget=_get_custom_rules, fset=_set_custom_rules, designable=False)
    """
    This property will appear as a list of object oriented rules when used programmatically.

    However, it is converted into JSON-encoded string when used from Qt Designer, because Qt Designer
    cannot understand custom object format.
    """


class ColorRulesMixin(WidgetRulesMixin):

    RULE_PROPERTIES = dict(**{BaseRule.Property.COLOR.value: ('set_color', str)},
                           **WidgetRulesMixin.RULE_PROPERTIES)

    def __init__(self):
        """Mixing that introduces color rule on top of the standard rules."""
        self._color = None

    def color(self) -> str:
        """
        Hexadecimal color in #XXXXXX format.

        Returns:
            color
        """
        return self._color

    def set_color(self, val: str):
        """ Set new color. Val is assumed to be #XXXXXX string here. """
        self._color = val
