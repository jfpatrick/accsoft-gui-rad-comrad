import functools
import weakref
import logging
import json
from weakref import ReferenceType
from typing import List, Dict, Any, Optional, cast, Union, Iterator, Iterable
from enum import IntEnum
from abc import ABCMeta
from qtpy.QtWidgets import QWidget
from qtpy.QtCore import QMutexLocker, Property
from pydm.widgets.rules import RulesEngine as PyDMRulesEngine, RulesDispatcher
from pydm.widgets.channel import PyDMChannel
from pydm.widgets.base import PyDMWidget
from pydm.data_plugins import plugin_for_address
from pydm.data_plugins.plugin import PyDMPlugin, PyDMConnection
from pydm.utilities import is_qt_designer
from pydm import config
from comrad.json import JSONSerializable, ComRADJSONEncoder, JSONDeserializeError
from .monkey import modify_in_place, MonkeyPatchedClass


logger = logging.getLogger(__name__)


RangeValue = Union[str, bool, float]


class RuleType(IntEnum):
    """All available rule setting modes."""

    NUM_RANGE = 0
    """Numeric range where user defines lower and upper numeric
     boundaries and associates property value with each range."""

    PY_EXPR = 1
    """User defines Python expression that can read multiple channels and produce a desired property value."""


class RuleRange(JSONSerializable):

    def __init__(self, min_val: float, max_val: float, prop_val: Optional[RangeValue] = None):
        """
        Describes a single entry in the numeric ranges rules.

        Args:
            min_val: Lower boundary of the range (included in the range).
            max_val: Upper boundary of the range (excluded from the range).
            prop_val: Value to be applied to the property in this range.
        """
        self._min_val = min_val
        self._max_val = max_val
        self._prop_val = prop_val

    @property
    def min_val(self) -> float:
        """Lower boundary of the range (included in the range)."""
        return self._min_val

    @min_val.setter
    def min_val(self, new_val: float):
        self._min_val = new_val

    @property
    def max_val(self) -> float:
        """Upper boundary of the range (excluded from the range)."""
        return self._max_val

    @max_val.setter
    def max_val(self, new_val: float):
        self._max_val = new_val

    @property
    def prop_val(self) -> float:
        """Value to be applied to the property in this range."""
        return self._prop_val

    @prop_val.setter
    def prop_val(self, new_val: float):
        self._prop_val = new_val

    @classmethod
    def from_json(cls, contents):
        logger.debug(f'Unpacking JSON range: {contents}')
        min_val: float = contents.get('min', None)
        max_val: float = contents.get('max', None)
        value: RangeValue = contents.get('value', None)

        if not isinstance(min_val, float):
            raise JSONDeserializeError(f'Can\'t parse range JSON: "min" is not float, "{type(min_val).__name__}" given.', None, 0)
        if not isinstance(max_val, float):
            raise JSONDeserializeError(f'Can\'t parse range JSON: "max" is not float, "{type(max_val).__name__}" given.', None, 0)
        if not isinstance(value, float) and not isinstance(value, str) and not isinstance(value, bool):
            raise JSONDeserializeError(f'Can\'t parse range JSON: "value" has unsupported type "{type(value).__name__}".', None, 0)
        return RuleRange(min_val=min_val, max_val=max_val, prop_val=value)

    def to_json(self):
        return {
            'min': self._min_val,
            'max': self._max_val,
            'value': self._prop_val,
        }

    def validate(self):
        """
        Ensure that the range does not violate any common sense.

        Raises:
            TypeError: If any of the range properties do not make sense.
        """
        if self.min_val is not None and self.max_val is not None and self.min_val > self.max_val:
            raise TypeError('Some ranges have inverted boundaries (max < min)')

    def __repr__(self) -> str:
        return f'<{type(self).__name__} {self.min_val}:{self.max_val} => {self.prop_val}>'


class BaseRule(JSONSerializable, metaclass=ABCMeta):

    DEFAULT_CHANNEL = '__auto__'
    NOT_IMPORTANT_CHANNEL = '__skip__'

    def __init__(self, name: str, prop: str, channel: Union[str, DEFAULT_CHANNEL, NOT_IMPORTANT_CHANNEL]):
        """
        Rule that can be applied to widgets to change their behavior based on incoming value.

        Args:
            name: Name of the rule as it's visible in the rules list.
            prop: Name corresponding to the key in RULE_PROPERTIES.
            channel: Channel address. Use :attr:`DEFAULT_CHANNEL` to use the default channel of the widget
                     or :attr:`NOT_IMPORTANT_CHANNEL` if the rule body is responsible for collecting the channel
                     information, e.g. in Python expressions. We never set it to None, to not confuse with absent
                     value because of the bug.
        """
        self._name = name
        self._prop = prop
        self.channel = channel
        self.body: Union[List[RuleRange], Dict[str, str], None] = None

    def validate(self):
        """
        Ensure that rule does not violate any common sense.

        Raises:
            TypeError: If any of the rule properties do not make sense.
        """
        errors: List[str] = []

        if not self.name:
            errors.append(f'Not every rule has a name')
        if not self.prop:
            errors.append(f'Rule "{self.name}"' if self.name else "Some rule" + ' is missing property definition')
        if errors:
            raise TypeError(';'.join(errors))

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, new_val: str):
        self._name = new_val

    @property
    def prop(self) -> str:
        return self._prop

    @prop.setter
    def prop(self, new_val: str):
        self._prop = new_val

    @property
    def type(self) -> RuleType:
        return self._type

    @type.setter
    def type(self, new_val: RuleType):
        self._type = new_val


class ExpressionRule(BaseRule):

    def __init__(self,
                 name: str,
                 prop: str,
                 channel: Union[str, BaseRule.DEFAULT_CHANNEL, BaseRule.NOT_IMPORTANT_CHANNEL],
                 expression: str):
        """
        Rule that evaluates Python expressions.

        Args:
            name: Name of the rule as it's visible in the rules list.
            prop: Name corresponding to the key in RULE_PROPERTIES.
            channel: Channel address. Use :attr:`DEFAULT_CHANNEL` to use the default channel of the widget
                     or :attr:`NOT_IMPORTANT_CHANNEL` if the rule body is responsible for collecting the channel
                     information, e.g. in Python expressions. We never set it to None, to not confuse with absent
                     value because of the bug.
            expression: Python expression.
        """
        super().__init__(name=name, prop=prop, channel=channel)
        self.expr = expression

    @staticmethod
    def from_json(contents: Dict[str, Any]):
        raise NotImplementedError()

    def to_json(self):
        raise NotImplementedError()


class NumRangeRule(BaseRule):

    def __init__(self,
                 name: str,
                 prop: str,
                 channel: Union[str, BaseRule.DEFAULT_CHANNEL, BaseRule.NOT_IMPORTANT_CHANNEL],
                 ranges: Optional[Iterable[RuleRange]] = None):
        """
        Rule that evaluates property based on a number of ranges, given that connected channel produces a number.

        Args:
            name: Name of the rule as it's visible in the rules list.
            prop: Name corresponding to the key in RULE_PROPERTIES.
            channel: Channel address. Use :attr:`DEFAULT_CHANNEL` to use the default channel of the widget
                     or :attr:`NOT_IMPORTANT_CHANNEL` if the rule body is responsible for collecting the channel
                     information, e.g. in Python expressions. We never set it to None, to not confuse with absent
                     value because of the bug.
            ranges: A list of numerical ranges that define which value should be set to the property when an incoming
                    number from the channel falls into ranges.
        """
        super().__init__(name=name, prop=prop, channel=channel)
        if ranges is None:
            ranges = []
        self.ranges: List[RuleRange] = ranges if isinstance(ranges, list) else list(ranges)

    @staticmethod
    def from_json(contents: Dict[str, Any]):
        logger.debug(f'Unpacking JSON rule: {contents}')
        name: str = contents.get('name', None)
        prop: str = contents.get('prop', None)
        channel: str = contents.get('channel', None)

        if not isinstance(name, str):
            raise JSONDeserializeError(f'Can\'t parse range JSON: "name" is not a string, "{type(name).__name__}" given.', None, 0)
        if not isinstance(prop, str):
            raise JSONDeserializeError(f'Can\'t parse range JSON: "prop" is not a string, "{type(prop).__name__}" given.', None, 0)
        if not isinstance(channel, str):
            raise JSONDeserializeError(f'Can\'t parse range JSON: "channel" is not a string, "{type(channel).__name__}" given.', None, 0)

        json_ranges: List[Any] = contents.get('ranges', None)

        if not isinstance(json_ranges, list):
            raise JSONDeserializeError(f'Can\'t parse range JSON: "ranges" is not a list, "{type(json_ranges).__name__}" given.', None, 0)

        ranges: Iterator[RuleRange] = map(RuleRange.from_json, json_ranges)
        return NumRangeRule(name=name, prop=prop, channel=channel, ranges=ranges)

    def to_json(self):
        return {
            'name': self.name,
            'prop': self.prop,
            'type': RuleType.NUM_RANGE,
            'channel': self.channel,
            'ranges': self.ranges,
        }

    def validate(self):
        errors: List[str] = []
        try:
            super().validate()
        except TypeError as e:
            errors.append(str(e))

        if len(self.ranges) == 0:
            errors.append(f'Rule "{self.name}" must have at least one range defined.')
        else:
            def is_overlapping(min1: float, max1: float, min2: float, max2: float) -> bool:
                import sys
                if min1 is None:
                    min1 = -sys.float_info.max
                if min2 is None:
                    min2 = -sys.float_info.max
                if max1 is None:
                    max1 = sys.float_info.max
                if max2 is None:
                    max2 = sys.float_info.max
                return max(min1, min2) < min(max1, max2)

            # TODO: This could be better optimized
            for row, range in enumerate(self.ranges):
                try:
                    range.validate()
                except TypeError as e:
                    errors.append(str(e))
                    continue

                for another_row, another_range in enumerate(self.ranges[row + 1:]):
                    if is_overlapping(min1=range.min_val,
                                      max1=range.max_val,
                                      min2=another_range.min_val,
                                      max2=another_range.max_val):
                        errors.append(f'Rule "{self.name}" has overlapping ranges')
        if errors:
            raise TypeError(';'.join(errors))

    def __repr__(self):
        return f'<{type(self).__name__} "{self.name}" [{self.prop}]>\n' + '\n'.join(map(repr, self.ranges))


def unpack_rules(contents: str) -> List[BaseRule]:
    """Converts JSON-encoded string into a list of rule objects.

    Args:
        JSON-encoded string.

    Returns:
        Lis tof rule objects.
    """
    logger.debug(f'Unpacking JSON rules into the object: {contents}')
    contents: List[Dict[str, Any]] = json.loads(contents)
    res: List[BaseRule] = []
    if isinstance(contents, list):
        for json_rule in contents:
            rule_type: int = json_rule['type']
            if not isinstance(rule_type, int):
                raise JSONDeserializeError(f'Rule {json_rule} must have integer type, given {type(rule_type).__name__}.')
            if rule_type == RuleType.NUM_RANGE:
                res.append(NumRangeRule.from_json(json_rule))
            elif rule_type == RuleType.PY_EXPR:
                res.append(ExpressionRule.from_json(json_rule))
            else:
                raise JSONDeserializeError(f'Unknown rule type {rule_type} for JSON {json_rule}')
    elif contents is not None:
        raise JSONDeserializeError(f'Rules does not appear to be a list')
    return res


class ChannelException(Exception):
    """Custom exception types to catch rule/channel-related exceptions."""
    pass


class WidgetRulesMixin:
    """
    Common rules mixin for all ComRAD widgets that limits the amount of properties for our widgets
    and ensures the synchronization between channel setter and rules setter regardless of the order.
    """

    DEFAULT_RULE_PROPERTY = 'Visibility'
    """Default rule property visible in the dialog."""

    RULE_PROPERTIES = {
        'Enabled': ['setEnabled', bool],
        'Visibility': ['setVisible', bool],
        'Opacity': ['set_opacity', float],
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
            return json.dumps(rules, cls=ComRADJSONEncoder)
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
        except ChannelException:
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

    RULE_PROPERTIES = dict(Color=['set_color', str],
                           **WidgetRulesMixin.RULE_PROPERTIES)

    def __init__(self):
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


@modify_in_place
class RulesEngine(PyDMRulesEngine, MonkeyPatchedClass):

    def __init__(self):
        """
        RulesEngine inherits from QThread and is responsible evaluating the rules
        for all the widgets in the application.
        """
        logger.debug(f'Instantiating custom rules engine')
        self._overridden_methods['__init__'](self)

    def register(self: PyDMRulesEngine, widget: QWidget, rules: List[BaseRule]):

        if is_qt_designer() and not config.DESIGNER_ONLINE:
            logger.debug(f'Not registering rules because channels won\'t be connected in the offline designer')
            return

        logger.debug(f'Registering rules for "{type(widget).__name__}" ({id(widget)}):\n{list(rules)}')
        widget_ref = weakref.ref(widget, self.widget_destroyed)
        if widget_ref in self.widget_map:
            self.unregister(widget_ref)

        with QMutexLocker(self.map_lock):
            self.widget_map[widget_ref] = []
            for idx, rule in enumerate(rules):
                channels_list: List[str]

                try:
                    rule.validate()
                except TypeError as e:
                    messages = str(e).split(';')
                    logger.warning('Skipping rule because of the errors:\n' + '\n'.join(messages))
                    continue

                # TODO: Will this work with wildcard channel? Certainly not dynamically changing one because it's evaluated once
                if rule.channel == BaseRule.DEFAULT_CHANNEL:
                    default_channel = widget_ref().default_rule_channel()
                    if default_channel is None:
                        raise ChannelException(f'Default channel on the widget is not defined yet. We won\' register it for now...')
                    channels_list = [{
                        'channel': default_channel,
                        'trigger': True,
                    }]
                elif rule.channel == BaseRule.NOT_IMPORTANT_CHANNEL:
                    # TODO: This is probably Python expression. Handle it differently from the body
                    logger.warning(f'Rules without explicit channel cannot be handled yet')
                    continue
                else:
                    channels_list = [{
                        'channel': rule.channel,
                        'trigger': True,
                    }]

                logger.debug(f'Channel list for rule "{rule.name}" will be {channels_list}')

                job_unit: Dict[str, Any] = {}
                job_unit['rule'] = rule
                job_unit['calculate'] = False
                job_unit['values'] = [None] * len(channels_list)
                job_unit['conn'] = [False] * len(channels_list)
                job_unit['channels'] = []

                for ch_idx, ch in enumerate(channels_list):
                    conn_cb = functools.partial(self.callback_conn, widget_ref, idx, ch_idx)
                    value_cb = functools.partial(self.callback_value, widget_ref, idx, ch_idx, ch['trigger'])
                    addr = ch['channel']
                    c = PyDMChannel(address=addr, connection_slot=conn_cb, value_slot=value_cb)
                    job_unit['channels'].append(c)
                    plugin: PyDMPlugin = plugin_for_address(addr)
                    try:
                        conn: PyDMConnection = plugin.connections[addr]
                        job_unit['conn'][ch_idx] = conn.connected
                    except KeyError:
                        pass
                    c.connect()

                self.widget_map[widget_ref].append(job_unit)

    def calculate_expression(self: PyDMRulesEngine, widget_ref: ReferenceType, rule: Dict[str, Any]):
        job_unit = rule
        job_unit['calculate'] = False

        rule = job_unit['rule']
        obj = self

        def notify_value(val):
            payload = {
                'widget': widget_ref,
                'name': rule.name,
                'property': rule.prop,
                'value': val
            }
            obj.rule_signal.emit(payload)

        if isinstance(rule, ExpressionRule):
            logger.warning(f'Python expressions are not supported for evaluation yet')
            # TODO: Handle Python expression here
            # eval_env = {
            #     'np': np,
            #     'ch': rule['values']
            # }
            # eval_env.update({k: v for k, v in math.__dict__.items() if k[0] != '_'})
            # try:
            #     val = eval(expression, eval_env)
            #     notify_value(val)
            # except Exception as e:
            #     logger.exception(f'Error while evaluating Rule: {e}')
        elif isinstance(rule, NumRangeRule):
            _, base_type = cast(WidgetRulesMixin, widget_ref()).RULE_PROPERTIES[rule.prop]
            val = float(job_unit['values'][0])
            for range in rule.ranges:
                if range.min_val <= val < range.max_val:
                    notify_value(base_type(range.prop_val))
                    break
            else:
                notify_value(None)
            return
        else:
            logger.exception(f'Unsupported rule type: {type(rule).__name__}')
            return
