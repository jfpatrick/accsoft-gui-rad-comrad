"""
Widget rules can be used to control certain properties based on the incoming value from the control devices.
"""


import functools
import weakref
import logging
import json
from weakref import ReferenceType
from typing import List, Dict, Any, Optional, cast, Union, Iterator, Iterable
from enum import IntEnum, Enum
from abc import ABCMeta
from qtpy.QtWidgets import QWidget
from qtpy.QtCore import QMutexLocker
from pydm.widgets.rules import RulesEngine as PyDMRulesEngine
from pydm.widgets.channel import PyDMChannel
from pydm.data_plugins import plugin_for_address
from pydm.data_plugins.plugin import PyDMPlugin, PyDMConnection
from pydm.utilities import is_qt_designer
from pydm import config
from comrad.json import CJSONSerializable, CJSONDeserializeError
from .monkey import modify_in_place, MonkeyPatchedClass


logger = logging.getLogger(__name__)


RangeValue = Union[str, bool, float]


class CBaseRule(CJSONSerializable, metaclass=ABCMeta):

    class Channel(Enum):
        """Predefined channel values."""

        DEFAULT = '__auto__'
        """
        Take value from the default channel specified by the widget via
        :meth:`~CWidgetRulesMixin.default_rule_channel` method.
        """

        NOT_IMPORTANT = '__skip__'
        """Indicates that channel is used to aggregate value but does not act as a trigger for recalculating the rule."""

    class Type(IntEnum):
        """All available rule setting modes."""

        NUM_RANGE = 0
        """Numeric range where user defines lower and upper numeric
         boundaries and associates property value with each range."""

        PY_EXPR = 1
        """User defines Python expression that can read multiple channels and produce a desired property value."""

    class Property(Enum):
        """Predefined properties that can be controlled by rules."""

        ENABLED = 'Enabled'
        """Boolean flag to enable or disable the widget based on the incoming value."""

        VISIBILITY = 'Visibility'
        """Boolean flag to make the widget visible or make it disappear based on the incoming value."""

        OPACITY = 'Opacity'
        """Float value to set the transparency on the widget based on the incoming value."""

        COLOR = 'Color'
        """String value with HEX code of the RGB color to be applied on the widget."""

    def __init__(self, name: str, prop: Union['CBaseRule.Property', str], channel: Union[str, Channel]):
        """
        Rule that can be applied to widgets to change their behavior based on incoming value.

        Args:
            name: Name of the rule as it's visible in the rules list.
            prop: Name corresponding to the key in :attr:`~CWidgetRulesMixin.RULE_PROPERTIES`.
            channel: Channel address. Use :attr:`Channel.DEFAULT` to use the default channel of the widget
                     or :attr:`Channel.NOT_IMPORTANT` if the rule body is responsible for collecting the channel
                     information, e.g. in Python expressions. We never set it to None, to not confuse with absent
                     value because of the bug.
        """
        self._name = name
        self._prop: str = prop.value if isinstance(prop, CBaseRule.Property) else prop
        self.channel = channel

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
            errors.append('{rule_name} is missing property definition'.format(
                rule_name=f'Rule "{self.name}"' if self.name else 'Some rule',
            ))
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
    def type(self) -> 'CBaseRule.Type':
        return self._type

    @type.setter
    def type(self, new_val: 'CBaseRule.Type'):
        self._type = new_val


class CExpressionRule(CBaseRule):

    def __init__(self,
                 name: str,
                 prop: str,
                 channel: Union[str, CBaseRule.Channel],
                 expression: str):
        """
        Rule that evaluates Python expressions.

        Args:
            name: Name of the rule as it's visible in the rules list.
            prop: Name corresponding to the key in :attr:`CWidgetRulesMixin.RULE_PROPERTIES`.
            channel: Channel address. Use :attr:`CBaseRule.Channel.DEFAULT` to use the default channel of the widget
                     or :attr:`CBaseRule.Channel.NOT_IMPORTANT` if the rule body is responsible for collecting the channel
                     information, e.g. in Python expressions. We never set it to None, to not confuse with absent
                     value because of the bug.
            expression: Python expression.
        """
        super().__init__(name=name, prop=prop, channel=channel)
        self.expr = expression

    @classmethod
    def from_json(cls, contents):
        raise NotImplementedError()

    def to_json(self):
        raise NotImplementedError()


class CNumRangeRule(CBaseRule):

    class Range(CJSONSerializable):

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
        def prop_val(self) -> Optional[RangeValue]:
            """Value to be applied to the property in this range."""
            return self._prop_val

        @prop_val.setter
        def prop_val(self, new_val: RangeValue):
            self._prop_val = new_val

        @classmethod
        def from_json(cls, contents):
            logger.debug(f'Unpacking JSON range: {contents}')
            min_val: float = contents.get('min', None)
            max_val: float = contents.get('max', None)
            value: RangeValue = contents.get('value', None)

            if not isinstance(min_val, float):
                raise CJSONDeserializeError(
                    f'Can\'t parse range JSON: "min" is not float, "{type(min_val).__name__}" given.', None, 0)
            if not isinstance(max_val, float):
                raise CJSONDeserializeError(
                    f'Can\'t parse range JSON: "max" is not float, "{type(max_val).__name__}" given.', None, 0)
            if not isinstance(value, float) and not isinstance(value, str) and not isinstance(value, bool):
                raise CJSONDeserializeError(
                    f'Can\'t parse range JSON: "value" has unsupported type "{type(value).__name__}".', None, 0)
            return cls(min_val=min_val, max_val=max_val, prop_val=value)

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

    def __init__(self,
                 name: str,
                 prop: str,
                 channel: Union[str, CBaseRule.Channel] = CBaseRule.Channel.DEFAULT,
                 ranges: Optional[Iterable['CNumRangeRule.Range']] = None):
        """
        Rule that evaluates property based on a number of ranges, given that connected channel produces a number.

        Args:
            name: Name of the rule as it's visible in the rules list.
            prop: Name corresponding to the key in :attr:`CWidgetRulesMixin.RULE_PROPERTIES`.
            channel: Channel address. Use :attr:`CBaseRule.Channel.DEFAULT` to use the default channel of the widget
                     or :attr:`CBaseRule.Channel.NOT_IMPORTANT` if the rule body is responsible for collecting the channel
                     information, e.g. in Python expressions. We never set it to None, to not confuse with absent
                     value because of the bug.
            ranges: A list of numerical ranges that define which value should be set to the property when an incoming
                    number from the channel falls into ranges.
        """
        super().__init__(name=name, prop=prop, channel=channel)
        if ranges is None:
            ranges = []
        self.ranges: List['CNumRangeRule.Range'] = ranges if isinstance(ranges, list) else list(ranges)

    @classmethod
    def from_json(cls, contents):
        logger.debug(f'Unpacking JSON rule: {contents}')
        name: str = contents.get('name', None)
        prop: str = contents.get('prop', None)
        channel: Union[str, CBaseRule.Channel] = contents.get('channel', None)

        if not isinstance(name, str):
            raise CJSONDeserializeError(f'Can\'t parse range JSON: "name" is not a string, "{type(name).__name__}" given.', None, 0)
        if not isinstance(prop, str):
            raise CJSONDeserializeError(f'Can\'t parse range JSON: "prop" is not a string, "{type(prop).__name__}" given.', None, 0)
        if not isinstance(channel, str):
            raise CJSONDeserializeError(f'Can\'t parse range JSON: "channel" is not a string, "{type(channel).__name__}" given.', None, 0)

        json_ranges: List[Any] = contents.get('ranges', None)

        if not isinstance(json_ranges, list):
            raise CJSONDeserializeError(f'Can\'t parse range JSON: "ranges" is not a list, "{type(json_ranges).__name__}" given.', None, 0)

        ranges: Iterator['CNumRangeRule.Range'] = map(CNumRangeRule.Range.from_json, json_ranges)

        # If a string corresponds to enum, try to extract it
        try:
            channel = CBaseRule.Channel(channel)
        except ValueError:
            pass

        return cls(name=name, prop=prop, channel=channel, ranges=ranges)

    def to_json(self):
        return {
            'name': self.name,
            'prop': self.prop,
            'type': CBaseRule.Type.NUM_RANGE,
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

                for _, another_range in enumerate(self.ranges[row + 1:]):
                    if is_overlapping(min1=range.min_val,
                                      max1=range.max_val,
                                      min2=another_range.min_val,
                                      max2=another_range.max_val):
                        errors.append(f'Rule "{self.name}" has overlapping ranges')
        if errors:
            raise TypeError(';'.join(errors))

    def __repr__(self):
        return f'<{type(self).__name__} "{self.name}" [{self.prop}]>\n' + '\n'.join(map(repr, self.ranges))


def unpack_rules(contents: str) -> List[CBaseRule]:
    """Converts JSON-encoded string into a list of rule objects.

    Args:
        JSON-encoded string.

    Returns:
        Lis tof rule objects.
    """
    logger.debug(f'Unpacking JSON rules into the object: {contents}')
    parsed_contents: List[Dict[str, Any]] = json.loads(contents)
    res: List[CBaseRule] = []
    if isinstance(parsed_contents, list):
        for json_rule in parsed_contents:
            rule_type: int = json_rule['type']
            if not isinstance(rule_type, int):
                raise CJSONDeserializeError(f'Rule {json_rule} must have integer type, given {type(rule_type).__name__}.')
            if rule_type == CBaseRule.Type.NUM_RANGE:
                res.append(CNumRangeRule.from_json(json_rule))
            elif rule_type == CBaseRule.Type.PY_EXPR:
                res.append(CExpressionRule.from_json(json_rule))
            else:
                raise CJSONDeserializeError(f'Unknown rule type {rule_type} for JSON {json_rule}')
    elif parsed_contents is not None:
        raise CJSONDeserializeError(f'Rules does not appear to be a list')
    return res


class CChannelError(Exception):
    """Custom exception types to catch rule/channel-related exceptions."""
    pass


@modify_in_place
class CRulesEngine(PyDMRulesEngine, MonkeyPatchedClass):

    def __init__(self):
        """
        RulesEngine inherits from :class:`PyQt5.QtCore.QThread` and is responsible evaluating the rules
        for all the widgets in the application.
        """
        logger.debug(f'Instantiating custom rules engine')
        self._overridden_members['__init__'](self)

    def register(self, widget: QWidget, rules: List[CBaseRule]):

        if is_qt_designer() and not config.DESIGNER_ONLINE:
            logger.debug(f"Not registering rules because channels won't be connected in the offline designer")
            return

        widget_name = widget.objectName()
        logger.debug(f'Registering rules for "{widget_name}":\n{list(rules)}')
        widget_ref = weakref.ref(widget, self.widget_destroyed)
        if widget_ref in self.widget_map:
            self.unregister(widget_ref)

        with QMutexLocker(self.map_lock):
            self.widget_map[widget_ref] = []
            for idx, rule in enumerate(rules):
                channels_list: List[Dict[str, Any]]

                try:
                    rule.validate()
                except TypeError as e:
                    messages = str(e).split(';')
                    logger.warning('Skipping rule because of the errors:\n' + '\n'.join(messages))
                    continue

                # TODO: Will this work with wildcard channel? Certainly not dynamically changing one because it's evaluated once
                if rule.channel == CBaseRule.Channel.DEFAULT:
                    from comrad.widgets.mixins import CWidgetRulesMixin
                    default_channel = cast(CWidgetRulesMixin, widget_ref()).default_rule_channel()
                    if default_channel is None:
                        raise CChannelError(f"Default channel on the widget is not defined yet. We won't register it for now...")
                    channels_list = [{
                        'channel': default_channel,
                        'trigger': True,
                    }]
                elif rule.channel == CBaseRule.Channel.NOT_IMPORTANT:
                    # TODO: This is probably Python expression. Handle it differently from the body
                    logger.warning(f'Rules without explicit channel cannot be handled yet')
                    continue
                else:
                    channels_list = [{
                        'channel': rule.channel,
                        'trigger': True,
                    }]

                logger.debug(f'Channel list for rule "{widget_name}.{rule.name}" will be {channels_list}')

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

    def calculate_expression(self, widget_ref: ReferenceType, rule: Dict[str, Any]):
        job_unit = rule
        job_unit['calculate'] = False

        rule_obj = job_unit['rule']
        obj = self

        def notify_value(val):
            payload = {
                'widget': widget_ref,
                'name': rule_obj.name,
                'property': rule_obj.prop,
                'value': val,
            }
            obj.rule_signal.emit(payload)

        if isinstance(rule_obj, CExpressionRule):
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
        elif isinstance(rule_obj, CNumRangeRule):
            from comrad.widgets.mixins import CWidgetRulesMixin
            _, base_type = cast(CWidgetRulesMixin, widget_ref()).RULE_PROPERTIES[rule_obj.prop]
            val = float(job_unit['values'][0])
            for range in rule_obj.ranges:
                if range.min_val <= val < range.max_val:
                    notify_value(base_type(range.prop_val))
                    break
            else:
                notify_value(None)
            return
        else:
            logger.exception(f'Unsupported rule type: {type(rule_obj).__name__}')
            return

    def warn_unconnected_channels(self, widget_ref: ReferenceType, index: int):
        """
        Overrides the method because original method accesses in a dictionary-style way, which breaks
        our OO rule. It also changes the severity form error to warning.
        """
        job_unit = self.widget_map[widget_ref][index]
        rule_obj: CBaseRule = job_unit['rule']
        logger.warning(f'Rule "{rule_obj.name}": Not all channels are connected, skipping execution.')
