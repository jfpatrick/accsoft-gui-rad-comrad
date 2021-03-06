import json
import logging
import copy
from typing import Any, List, cast, Union, Dict, Tuple, Callable, Optional
from qtpy.QtCore import Property, Signal, Slot
from qtpy.QtWidgets import QWidget
from pydm.utilities import is_qt_designer
from pydm.widgets.base import PyDMWidget
from pydm.widgets.rules import RulesDispatcher
from comrad.rules import CBaseRule, CChannelError, unpack_rules
from comrad.json import CJSONEncoder, CJSONDeserializeError
from comrad.deprecations import deprecated_parent_prop
from comrad.data.channel import CChannelData, PyDMChannel
from comrad.data.context import CContext
from comrad.widgets.widget import CWidget
from .value_transform import CValueTransformationBase


logger = logging.getLogger(__name__)


class CInitializedMixin:

    def __init__(self):
        """Simple mixin to set a flag when :meth:`__init__` method has finished the sequence."""
        self._widget_initialized = False


class CHideUnusedFeaturesMixin:
    """Mixin that hides PyDM properties that are exposed to Qt Designer and are not used in ComRAD."""

    @deprecated_parent_prop(logger=logger, property_name='alarmSensitiveBorder')
    def __set_alarmSensitiveBorder(self, _):
        pass

    alarmSensitiveBorder = Property(bool, lambda _: False, __set_alarmSensitiveBorder, designable=False)

    @deprecated_parent_prop(logger=logger, property_name='alarmSensitiveContent')
    def __set_alarmSensitiveContent(self, _):
        pass

    alarmSensitiveContent = Property(bool, lambda _: False, __set_alarmSensitiveContent, designable=False)


class CRequestingMixin:
    """
    Mixin for widgets that want to proactively request data from the channel, as opposed to regularly receiving udpates.
    (Relies on monkey-patched PyDMChannel instances).
    """

    request_signal = Signal(str)
    """Signal that is issued when the widget wants to actively request new data from the channel.
    Argument is a unique identifier of the widget so that it can filter only notifications that it is interested in."""

    def __init__(self, connect_value_slot: bool = True):
        """
        Args:
            connect_value_slot: Connect the default propagation slot automatically. Some widgets, that have ability to
                                request value explicitly, may want to opt out from receiving regular updates. Then this
                                value should be set to ``False``.
        """
        self._connect_value_slot = connect_value_slot

    def request_data(self):
        """Issue a request signal to the control system in order to retrieve data on demand."""
        self.request_signal.emit(self._request_uuid)

    def _on_request_fulfilled(self, value: Optional[Tuple[Any, Dict[str, Any]]], uuid: str):
        """
        Callback with additional filtering.
        """
        if uuid and uuid != self._request_uuid:  # None uuid will be empty string, when transferred thru signal
            # When it is None, everybody should handle the value (usually happens on initial populate)
            return
        cast(PyDMWidget, self).channelValueChanged(value)

    def create_channel(self, channel_address: str, context: Optional[CContext]) -> PyDMChannel:
        """Overridden method of CWidget to connect request signals/slots only when needed"""
        ch = cast(CWidget, super()).create_channel(channel_address, context)
        if not self.connect_value_slot:
            ch.request_signal = self.request_signal
            ch.request_slot = self._on_request_fulfilled
            ch.value_slot = None
        return ch

    def _set_connect_value_slot(self, new_val: bool):
        if new_val != self._connect_value_slot:
            self._connect_value_slot = new_val
            # Provoke channel recreation so that we don't have dangling slots
            # in case we disabled them with the new setting
            me = cast(PyDMWidget, self)
            prev_val = me._channel
            if prev_val is not None:
                me._channel = None
                # Because above statement will prevent existing channels from disconnecting, we need to perform it manually
                for channel, ch_addr in zip(me._channels, me._channel_ids):
                    if channel.address == prev_val:
                        channel.disconnect()
                        me._channels.remove(channel)
                        me._channel_ids.remove(ch_addr)
                # Now trigger the setter with full procedure
                me.channel = prev_val

    connect_value_slot = property(fget=lambda self: self._connect_value_slot, fset=_set_connect_value_slot)
    """
    Connect the default propagation slot automatically. Some widgets, that have ability to
                            request value explicitly, may want to opt out from receiving regular updates. Then this
                            value should be set to ``False``.
    """

    @property
    def _request_uuid(self):
        """Identifier to filter incoming notifications on-request to act only on those that are requested by us."""
        return cast(QWidget, self).objectName()


class CNoPVTextFormatterMixin:
    """
    Mixin that hides PyDM properties in :class:`pydm.widgets.base.TextFormatter` that are exposed to
    Qt Designer and are not used in ComRAD.
    """

    @deprecated_parent_prop(logger=logger, property_name='precisionFromPV')
    def __set_precisionFromPV(self, _):
        pass

    precisionFromPV = Property(bool, lambda _: False, __set_precisionFromPV, designable=False)

    @deprecated_parent_prop(logger=logger, property_name='showUnits')
    def __set_showUnits(self, _):
        pass

    # TODO: We should enable showUnits, when unit support is implemented on the CS level
    showUnits = Property(bool, lambda _: False, __set_showUnits, designable=False)


class CCustomizedTooltipMixin:
    """Mixin that customizes the message passed into the :attr:`QWidget.toolTip`."""

    def setToolTip(self, tooltip: str):
        """
        Re-implements Qt method to look for specific keywords and replace them.

        Args:
            tooltip:  widget's tooltip.
        """
        cast(QWidget, super()).setToolTip(tooltip.replace('PyDM', 'ComRAD').replace('PV ', 'Device Property '))


class CChannelDataProcessingMixin:

    def __init__(self):
        """
        Mixing that allows PyDM-derived widgets to work with updated
        channels that use :class:`~comrad.CChannelData`.
        """
        self.header: Optional[Dict[str, Any]] = None

    def value_changed(self, packet: CChannelData[Any]):
        """
        Overridden method to treat the incoming value with the header.

        Args:
            packet: New value from the channel.
        """
        if not isinstance(packet, CChannelData):
            new_val = None
        else:
            new_val = packet.value

        # Down to PyDM level, where widgets only expect actual data
        super().value_changed(new_val)  # type: ignore

    @Slot(CChannelData)
    def channelValueChanged(self, packet: CChannelData[Any]):
        """
        Define slot override for tuples.

        Args:
            packet: New value from the channel.
        """
        if not isinstance(packet, CChannelData):
            return
        else:
            # Save header here, so that it is available in all value_changed implementations
            self.header = packet.meta_info

        super().channelValueChanged(packet)  # type: ignore


class CValueTransformerMixin(CChannelDataProcessingMixin, CValueTransformationBase):

    def __init__(self):
        """
        Mixin that introduces :attr:`~comrad.widgets.value_transform.CValueTransformationBase.valueTransformation`
        property for client-side Python snippets acting on incoming values.
        """
        CChannelDataProcessingMixin.__init__(self)
        CValueTransformationBase.__init__(self)

    def getValueTransformation(self) -> str:
        return CValueTransformationBase.getValueTransformation(self)

    def setValueTransformation(self, new_formatter: str):
        """
        Reset generator code snippet.

        Args:
            new_val: New Python code snippet.
        """
        if self.getValueTransformation() != str(new_formatter):
            CValueTransformationBase.setValueTransformation(self, str(new_formatter))
            self.value_changed(self.value)  # type: ignore   # This is coming from PyDMWidget

    def channelValueChanged(self, packet: CChannelData[Any]):
        """
        Callback transforms the channel value through the
        :attr:`~comrad.widgets.value_transform.CValueTransformationBase.valueTransformation`
        code before displaying it in a standard way.

        Args:
            packet: The new value from the channel. The type depends on the channel.
        """
        if is_qt_designer() or not isinstance(packet, CChannelData):
            # Avoid code evaluation in Designer, as it can produce unnecessary errors with broken code
            super().channelValueChanged(None)  # type: ignore
            return

        transform = self.cached_value_transformation()
        if transform:
            new_val = transform(new_val=packet.value, header=packet.meta_info, widget=self)
            # Need a copy here, otherwise running transform on the same packet twice can happen
            new_packet = copy.copy(packet)
            new_packet.value = new_val
            super().channelValueChanged(new_packet)
        else:
            super().channelValueChanged(packet)


CWidgetRuleMap = Dict[str, Tuple[str, str, Callable[[Any], Any]]]


class CWidgetRulesMixin:

    DEFAULT_RULE_PROPERTY = 'Visibility'
    """Default rule property visible in the dialog."""

    RULE_PROPERTIES: CWidgetRuleMap = {
        CBaseRule.Property.ENABLED.value: ('isEnabled', 'setEnabled', bool),
        CBaseRule.Property.VISIBILITY.value: ('isVisible', 'setVisible', bool),
        CBaseRule.Property.OPACITY.value: ('opacity', 'set_opacity', float),
    }
    """All available rule properties with associated callbacks and data types."""

    def __init__(self):
        """
        Common rules mixin for all ComRAD widgets that limits the amount of properties for our widgets
        and ensures the synchronization between channel setter and rules setter regardless of the order.
        """
        self.__default_prop_values: Dict[str, Any] = {}

    def default_rule_channel(self) -> str:
        """
        Default channel to be used in the rule evaluation.

        Returns:
            Address of the channel.
        """
        try:
            return self.channel
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

    def _get_custom_rules(self) -> List[CBaseRule]:
        rules = cast(PyDMWidget, self)._rules
        if is_qt_designer():
            return cast(List[CBaseRule], json.dumps(rules, cls=CJSONEncoder))
        return rules

    def _set_custom_rules(self, new_rules: Union[str, List[CBaseRule], None]):
        if isinstance(new_rules, str):
            try:
                new_rules = unpack_rules(new_rules)
            except (json.JSONDecodeError, CJSONDeserializeError) as e:
                logger.exception(f'Invalid JSON format for rules: {str(e)}')
                return
        cast(PyDMWidget, self)._rules = new_rules
        if new_rules is None:
            return
        try:
            RulesDispatcher().register(widget=self, rules=new_rules)
        except CChannelError:
            logger.debug('Rules setting failed. We do not have the channel yet, will have to be repeated')
            # Set internal data structure without activating property setter behavior
            cast(PyDMWidget, self)._rules = new_rules

    rules: List[CBaseRule] = Property(type=str, fget=_get_custom_rules, fset=_set_custom_rules, designable=False)
    """
    This property will appear as a list of object oriented rules when used programmatically.

    However, it is converted into JSON-encoded string when used from Qt Designer, because Qt Designer
    cannot understand custom object format.
    """

    @Slot(dict)
    def rule_evaluated(self, payload: Dict[str, Any]):
        """
        Overridden :class:`~pydm.widgets.base.PyDMPrimitiveWidget`'s handler to allow ``None`` being passed from
        the rules engine. While it works out of the box for some types, e.g. color, it creates type incompatibility
        for others, e.g. boolean properties.
        We have also changed the format of RULE_PROPERTIES, so we need custom handling for it here.
        """
        name = payload.get('name', '')
        prop = payload.get('property', '')
        value = payload.get('value', None)

        if prop not in self.RULE_PROPERTIES:
            logger.error(f'Error at Rule: {name}. {prop} is not part of this widget properties.')
            return

        getter_name, setter_name, data_type = self.RULE_PROPERTIES[prop]

        # First time, assume current value of the property "the default"
        if setter_name not in self.__default_prop_values:
            getter_method = getattr(self, getter_name, None)
            if getter_method is None:
                logger.error(f'Error at Rule: {name}. Getter {getter_name} does not exist on this widget.')
            else:
                self.__default_prop_values[setter_name] = getter_method()

        setter_method = getattr(self, setter_name, None)
        if setter_method is None:
            logger.error(f'Error at Rule: {name}. Setter {setter_name} does not exist on this widget.')
            return

        if value is None:
            try:
                new_val = self.__default_prop_values[setter_name]
            except KeyError:
                logger.error(f"Error at Rule: {name}. Cannot reset property to its initial value, as it's not recorded")
                return
            setter_method(new_val)
        else:
            setter_method(value)


class CColorRulesMixin(CWidgetRulesMixin):

    RULE_PROPERTIES = dict(**{CBaseRule.Property.COLOR.value: ('rule_color', 'set_color', str)},
                           **CWidgetRulesMixin.RULE_PROPERTIES)

    def __init__(self):
        """Mixing that introduces color rule on top of the standard rules."""
        super().__init__()
        self.__color = None

    def rule_color(self) -> str:
        """
        Hexadecimal color in ``#XXXXXX`` format.

        Returns:
            color
        """
        return self.__color

    def set_color(self, val: str):
        """ Set new color. Val is assumed to be ``#XXXXXX`` string here. """
        self.__color = val
