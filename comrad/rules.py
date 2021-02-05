"""
Widget rules can be used to control certain properties based on the incoming value from the control devices.
"""


import functools
import weakref
import logging
import json
from weakref import ReferenceType
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, cast, Union, Iterable, Type
from enum import IntEnum, Enum
from abc import ABCMeta, abstractmethod
from qtpy.QtWidgets import QWidget
from qtpy.QtCore import QMutexLocker
from qtpy.QtGui import QColor
from pydm.widgets.rules import RulesEngine as PyDMRulesEngine
from pydm.widgets.channel import PyDMChannel
from pydm.data_plugins import plugin_for_address
from pydm.data_plugins.plugin import PyDMPlugin, PyDMConnection
from pydm.utilities import is_qt_designer
from pydm import config
from comrad.json import CJSONSerializable, CJSONDeserializeError
from comrad.data.channel import CChannelData, CContext, CChannel
from comrad.data.japc_enum import CEnumValue
from .monkey import modify_in_place, MonkeyPatchedClass


logger = logging.getLogger(__name__)


AppliedValue = Union[str, bool, float]


context_cache: Dict[str, CContext] = {}


class Validatable(metaclass=ABCMeta):

    @abstractmethod
    def validate(self):
        """
        Ensure that the object does not violate any common sense.

        Raises:
            TypeError: If any misuse is detected. The error message may contain multiple errors delimited by ``;``.
        """
        pass


# @dataclass(init=False, repr=False, eq=False)
class CBaseRule(CJSONSerializable, Validatable, metaclass=ABCMeta):

    class Channel(Enum):
        """Predefined channel values."""

        DEFAULT = '__auto__'
        """
        Take value from the default channel specified by the widget via
        :meth:`~comrad.widgets.mixins.CWidgetRulesMixin.default_rule_channel` method.
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

        ENUM = 2
        """Enum based rules which are able to compare against either meaning, label or code value"""

        @classmethod
        def rule_map(cls) -> Dict['CBaseRule.Type', Type['CBaseRule']]:
            """Returns a mapping between enum values and rule classes."""
            return {
                CBaseRule.Type.NUM_RANGE: CNumRangeRule,
                CBaseRule.Type.ENUM: CEnumRule,
                CBaseRule.Type.PY_EXPR: CExpressionRule,
            }

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

    name: str
    """Name of the rule as it's visible in the rules list."""

    prop: str
    """Name corresponding to the key in :attr:`~comrad.widgets.mixins.CWidgetRulesMixin.RULE_PROPERTIES`."""

    channel: Union[str, Channel]
    """
    Channel address. Use :attr:`Channel.DEFAULT` to use the default channel of the widget
                     or :attr:`Channel.NOT_IMPORTANT` if the rule body is responsible for collecting the channel
                     information, e.g. in Python expressions. We never set it to None, to not confuse with absent
                     value because of the bug.
    """

    selector: Optional[str]
    """Timing selector associated with the :attr:`channel`."""

    def __init__(self,
                 name: str,
                 prop: Union['CBaseRule.Property', str],
                 channel: Union[str, Channel],
                 selector: Optional[str] = None):
        """
        Rule that can be applied to widgets to change their behavior based on incoming value.

        Args:
            name: Name of the rule as it's visible in the rules list.
            prop: Name corresponding to the key in :attr:`~comrad.widgets.mixins.CWidgetRulesMixin.RULE_PROPERTIES`.
            channel: Channel address. Use :attr:`Channel.DEFAULT` to use the default channel of the widget
                     or :attr:`Channel.NOT_IMPORTANT` if the rule body is responsible for collecting the channel
                     information, e.g. in Python expressions. We never set it to None, to not confuse with absent
                     value because of the bug.
            selector: Timing selector associated with the ``channel``.
        """
        self.name = name
        self.prop = prop.value if isinstance(prop, CBaseRule.Property) else prop
        self.channel = channel
        self.selector = selector

    def validate(self):
        errors: List[str] = []

        if not self.name:
            errors.append('Not every rule has a name')
        if not self.prop:
            errors.append('{rule_name} is missing property definition'.format(
                rule_name=f'Rule "{self.name}"' if self.name else 'Some rule',
            ))
        if self.selector is not None:
            comps = self.selector.split('.')
            if len(comps) != 3 or any(not comp for comp in comps):
                errors.append('{rule_name} has malformed selector (use MACHINE.GROUP.LINE format)'.format(
                    rule_name=f'Rule "{self.name}"' if self.name else 'Some rule'))
        if errors:
            raise TypeError(';'.join(errors))

    @classmethod
    def type(cls) -> 'CBaseRule.Type':
        """Defines to which type the given rule belongs."""
        return next((enum_val for enum_val, rule_class in CBaseRule.Type.rule_map().items()
                     if issubclass(cls, rule_class)))


@dataclass(init=False, repr=False, eq=False)
class CEnumRule(CBaseRule):

    class EnumField(IntEnum):
        """Defines which PyJapc :class:`CEnumValue` field will be used for the comparison"""

        CODE = 0
        """The comparison will be performed on :attr:`~comrad.data.japc_enum.CEnumValue.code` field."""

        LABEL = 1
        """The comparison will be performed on :attr:`~comrad.data.japc_enum.CEnumValue.label` field."""

        MEANING = 2
        """The comparison will be performed on :attr:`~comrad.data.japc_enum.CEnumValue.meaning` field."""

    @dataclass(repr=False)
    class EnumConfig(CJSONSerializable, Validatable):
        """Describes a single entry in the Enum rules."""

        field: 'CEnumRule.EnumField'
        """Indicates which PyJapc enum field will be compared for this rule."""

        field_val: Union[int, str, CEnumValue.Meaning]
        """Value to compare against, the type should be compliant with the chosen field."""

        prop_val: AppliedValue
        """Value to be applied to the property if received value and rule value match."""

        @classmethod
        def from_json(cls, contents):
            logger.debug(f'Unpacking JSON enum setting: {contents}')
            field: Union[int, CEnumRule.EnumField] = contents.get('field', None)
            field_val: Union[int, str, CEnumValue.Meaning] = contents.get('fv', None)
            value: AppliedValue = contents.get('value', None)

            if not isinstance(field, int):
                raise CJSONDeserializeError(f'Can\'t parse enum JSON: "field" is not int, "{type(field).__name__}" given.', None, 0)
            try:
                field = CEnumRule.EnumField(field)
            except ValueError:
                raise CJSONDeserializeError(f'Can\'t parse enum JSON: "field" value "{field}" does not correspond to the known possible options.', None, 0)
            if field == CEnumRule.EnumField.CODE and not isinstance(field_val, int):
                raise CJSONDeserializeError(f'Can\'t parse enum JSON: "fv" is not int, as required by field type "CODE", "{type(field_val).__name__}" given.', None, 0)
            elif field == CEnumRule.EnumField.LABEL and not isinstance(field_val, str):
                raise CJSONDeserializeError(f'Can\'t parse enum JSON: "fv" is not str, as required by field type "LABEL", "{type(field_val).__name__}" given.', None, 0)
            elif field == CEnumRule.EnumField.MEANING and not isinstance(field_val, int):
                raise CJSONDeserializeError(f'Can\'t parse enum JSON: "fv" is not int, as required by field type "MEANING", "{type(field_val).__name__}" given.', None, 0)
            if field == CEnumRule.EnumField.MEANING:
                try:
                    field_val = CEnumValue.Meaning(field_val)
                except ValueError:
                    raise CJSONDeserializeError(f'Can\'t parse enum JSON: "fv" value "{field_val}" does not correspond to the known possible options of meaning.', None, 0)
            if not isinstance(value, float) and not isinstance(value, str) and not isinstance(value, bool):
                raise CJSONDeserializeError(f'Can\'t parse enum JSON: "value" has unsupported type "{type(value).__name__}".', None, 0)
            return cls(field=field, field_val=field_val, prop_val=value)

        def to_json(self):
            return {
                'field': self.field,
                'fv': self.field_val,
                'value': self.prop_val,
            }

        def validate(self):
            if isinstance(self.field_val, CEnumValue.Meaning):  # Need to check this first, to avoid false positive on a simple int
                if self.field == CEnumRule.EnumField.MEANING:
                    return
            elif self.field == CEnumRule.EnumField.CODE and isinstance(self.field_val, int):
                return
            elif self.field == CEnumRule.EnumField.LABEL and isinstance(self.field_val, str):
                return
            raise TypeError(f'Value of type "{type(self.field_val).__name__}" is not compatible with enum field "{str(self.field).split(".")[-1].title()}"')

        def __repr__(self) -> str:
            return f'<{type(self).__name__} {self.field}=={self.field_val} => {self.prop_val}>'

    config: List['CEnumRule.EnumConfig']
    """
    A list of :class:`~CEnumRule.EnumConfig` objects that define which value should be set to the property
    when an incoming enum from the channel is equal to the compared value.
    """

    def __init__(self,
                 name: str,
                 prop: str,
                 channel: Union[str, CBaseRule.Channel] = CBaseRule.Channel.DEFAULT,
                 selector: Optional[str] = None,
                 config: Optional[Iterable['CEnumRule.EnumConfig']] = None):
        """
        Rule that evaluates property based on a enum [code / meaning / label], given that connected channel produces an
        enum.

        Args:
            name: Name of the rule as it's visible in the rules list.
            prop: Name corresponding to the key in :attr:`~comrad.widgets.mixins.CWidgetRulesMixin.RULE_PROPERTIES`.
            channel: Channel address. Use :attr:`CBaseRule.Channel.DEFAULT` to use the default channel of the widget
                     or :attr:`CBaseRule.Channel.NOT_IMPORTANT` if the rule body is responsible for collecting the
                     channel information, e.g. in Python expressions. We never set it to None, to not confuse with
                     absent value because of the bug.
            selector: Timing selector associated with the ``channel``.
            config: A list of :class:`~CEnumRule.EnumConfig` objects that define which value should be set to the property
                    when an incoming enum from the channel is equal to the compared value.
        """
        super().__init__(name=name, prop=prop, channel=channel, selector=selector)
        if config is None:
            config = []
        self.config: List['CEnumRule.EnumConfig'] = config if isinstance(config, list) else list(config)

    @classmethod
    def from_json(cls, contents):
        logger.debug(f'Unpacking JSON rule: {contents}')
        name: str = contents.get('name', None)
        prop: str = contents.get('prop', None)
        selector: Optional[str] = contents.get('sel', None)
        channel: Union[str, CBaseRule.Channel] = contents.get('channel', None)

        if not isinstance(name, str):
            raise CJSONDeserializeError(f'Can\'t parse rule JSON: "name" is not a string, "{type(name).__name__}" given.', None, 0)
        if not isinstance(prop, str):
            raise CJSONDeserializeError(f'Can\'t parse rule JSON: "prop" is not a string, "{type(prop).__name__}" given.', None, 0)
        if not (isinstance(channel, str)):
            raise CJSONDeserializeError(f'Can\'t parse rule JSON: "channel" is not a string, "{type(channel).__name__}" given.', None, 0)
        if selector is not None and not (isinstance(selector, str)):
            raise CJSONDeserializeError(f'Can\'t parse rule JSON: "sel" is not a string, "{type(selector).__name__}" given.', None, 0)

        json_config: List[Any] = contents.get('config', [])

        if not isinstance(json_config, list):
            raise CJSONDeserializeError(f'Can\'t parse rule JSON: "config" is not a list, "{type(json_config).__name__}" given.', None, 0)

        # Need list right away, since map will be drained after the first iteration attempt
        config: List['CEnumRule.EnumConfig'] = list(map(CEnumRule.EnumConfig.from_json, json_config))
        if prop == CBaseRule.Property.COLOR.value:
            if any(not is_valid_color(entry) for entry in config):
                raise CJSONDeserializeError('Can\'t parse rule JSON: "config" contains invalid color definitions.', None, 0)

        # If a string corresponds to enum, try to extract it
        try:
            channel = CBaseRule.Channel(channel)
        except ValueError:
            pass

        return cls(name=name, prop=prop, channel=channel, selector=selector, config=config)

    def to_json(self):
        return {
            'name': self.name,
            'prop': self.prop,
            'type': self.type(),
            'channel': self.channel,
            'sel': self.selector,
            'config': self.config,
        }

    def validate(self):
        errors: List[str] = []
        try:
            super().validate()
        except TypeError as e:
            errors.append(str(e))

        if len(self.config) == 0:
            errors.append(f'Rule "{self.name}" must have at least one enum option defined.')
        else:
            def is_overlapping(enum_value1: CEnumRule.EnumConfig, enum_value2: CEnumRule.EnumConfig) -> bool:
                return enum_value1.field == enum_value2.field and enum_value1.field_val == enum_value2.field_val

            # TODO: This could be better optimized
            for row, enum_value in enumerate(self.config):
                if self.prop == CBaseRule.Property.COLOR.value and not is_valid_color(enum_value):
                    errors.append(f'Rule "{self.name}" has an entry with invalid color ({enum_value.prop_val})')
                try:
                    enum_value.validate()
                except TypeError as e:
                    errors.append(str(e))
                    continue

                for another_enum_value in self.config[row + 1:]:
                    if is_overlapping(enum_value, another_enum_value):
                        field_val = (enum_value.field_val if enum_value.field != CEnumRule.EnumField.MEANING
                                     else str(CEnumValue.Meaning(enum_value.field_val)).split('.')[-1].title())
                        errors.append(f'Rule "{self.name}" has redundant configuration '
                                      f'({str(CEnumRule.EnumField(enum_value.field)).split(".")[-1].title()}:'
                                      f' "{field_val}")')
        if errors:
            raise TypeError(';'.join(errors))

    def __repr__(self) -> str:
        return f'<{type(self).__name__} "{self.name}" [{self.prop}]>\n' + '\n'.join(map(repr, self.config))


@dataclass(init=False, eq=False)
class CExpressionRule(CBaseRule):

    expr: str
    """Python expression."""

    def __init__(self,
                 name: str,
                 prop: str,
                 channel: Union[str, CBaseRule.Channel],
                 expression: str):
        """
        Rule that evaluates Python expressions.

        Args:
            name: Name of the rule as it's visible in the rules list.
            prop: Name corresponding to the key in :attr:`~comrad.widgets.mixins.CWidgetRulesMixin.RULE_PROPERTIES`.
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


@dataclass(init=False, repr=False, eq=False)
class CNumRangeRule(CBaseRule):

    @dataclass(repr=False)
    class Range(CJSONSerializable, Validatable):
        """Describes a single entry in the numeric ranges rules."""

        min_val: float
        """Lower boundary of the range (included in the range)."""

        max_val: float
        """Upper boundary of the range (excluded from the range)."""

        prop_val: AppliedValue
        """Value to be applied to the property in this range."""

        @classmethod
        def from_json(cls, contents):
            logger.debug(f'Unpacking JSON range: {contents}')
            min_val: float = contents.get('min', None)
            max_val: float = contents.get('max', None)
            value: AppliedValue = contents.get('value', None)

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
                'min': self.min_val,
                'max': self.max_val,
                'value': self.prop_val,
            }

        def validate(self):
            if self.min_val is not None and self.max_val is not None and self.min_val > self.max_val:
                raise TypeError(f'Range {self.min_val}-{self.max_val} has inverted boundaries (max < min)')

        def __repr__(self) -> str:
            return f'<{type(self).__name__} {self.min_val}:{self.max_val} => {self.prop_val}>'

    ranges: List['CNumRangeRule.Range']
    """
    A list of numerical ranges that define which value should be set to the property when an incoming
    number from the channel falls into ranges.
    """

    def __init__(self,
                 name: str,
                 prop: str,
                 channel: Union[str, CBaseRule.Channel] = CBaseRule.Channel.DEFAULT,
                 selector: Optional[str] = None,
                 ranges: Optional[Iterable['CNumRangeRule.Range']] = None):
        """
        Rule that evaluates property based on a number of ranges, given that connected channel produces a number.

        Args:
            name: Name of the rule as it's visible in the rules list.
            prop: Name corresponding to the key in :attr:`~comrad.widgets.mixins.CWidgetRulesMixin.RULE_PROPERTIES`.
            channel: Channel address. Use :attr:`CBaseRule.Channel.DEFAULT` to use the default channel of the widget
                     or :attr:`CBaseRule.Channel.NOT_IMPORTANT` if the rule body is responsible for collecting the channel
                     information, e.g. in Python expressions. We never set it to None, to not confuse with absent
                     value because of the bug.
            selector: Timing selector associated with the ``channel``.
            ranges: A list of numerical ranges that define which value should be set to the property when an incoming
                    number from the channel falls into ranges.
        """
        super().__init__(name=name, prop=prop, channel=channel, selector=selector)
        if ranges is None:
            ranges = []
        self.ranges: List['CNumRangeRule.Range'] = ranges if isinstance(ranges, list) else list(ranges)

    @classmethod
    def from_json(cls, contents):
        logger.debug(f'Unpacking JSON rule: {contents}')
        name: str = contents.get('name', None)
        prop: str = contents.get('prop', None)
        selector: Optional[str] = contents.get('sel', None)
        channel: Union[str, CBaseRule.Channel] = contents.get('channel', None)

        if not isinstance(name, str):
            raise CJSONDeserializeError(f'Can\'t parse range JSON: "name" is not a string, "{type(name).__name__}" given.', None, 0)
        if not isinstance(prop, str):
            raise CJSONDeserializeError(f'Can\'t parse range JSON: "prop" is not a string, "{type(prop).__name__}" given.', None, 0)
        if not isinstance(channel, str):
            raise CJSONDeserializeError(f'Can\'t parse range JSON: "channel" is not a string, "{type(channel).__name__}" given.', None, 0)
        if selector is not None and not isinstance(selector, str):
            raise CJSONDeserializeError(f'Can\'t parse range JSON: "sel" is not a string, "{type(selector).__name__}" given.', None, 0)

        json_ranges: List[Any] = contents.get('ranges', None)

        if not isinstance(json_ranges, list):
            raise CJSONDeserializeError(f'Can\'t parse range JSON: "ranges" is not a list, "{type(json_ranges).__name__}" given.', None, 0)

        # Need list right away, since map will be drained after the first iteration attempt
        ranges: List['CNumRangeRule.Range'] = list(map(CNumRangeRule.Range.from_json, json_ranges))

        if prop == CBaseRule.Property.COLOR.value:
            if any(not is_valid_color(entry) for entry in ranges):
                raise CJSONDeserializeError('Can\'t parse rule JSON: "ranges" contains invalid color definitions.', None, 0)

        # If a string corresponds to enum, try to extract it
        try:
            channel = CBaseRule.Channel(channel)
        except ValueError:
            pass

        return cls(name=name, prop=prop, channel=channel, selector=selector, ranges=ranges)

    def to_json(self):
        return {
            'name': self.name,
            'prop': self.prop,
            'type': self.type(),
            'channel': self.channel,
            'sel': self.selector,
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
                if self.prop == CBaseRule.Property.COLOR.value and not is_valid_color(range):
                    errors.append(f'Rule "{self.name}" has a range ({range.min_val}-{range.max_val}) that defines '
                                  f'invalid color ({range.prop_val})')
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
                        errors.append(f'Rule "{self.name}" has overlapping ranges ({range.min_val}-{range.max_val} '
                                      f'and {another_range.min_val}-{another_range.max_val})')

        if errors:
            raise TypeError(';'.join(errors))

    def __repr__(self) -> str:
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

    rule_map: Dict[int, Type] = {}
    for sub in CBaseRule.__subclasses__():
        rule_map[sub.type()] = sub

    if isinstance(parsed_contents, list):
        for json_rule in parsed_contents:
            rule_type: int = json_rule['type']
            if not isinstance(rule_type, int):
                raise CJSONDeserializeError(f'Rule {json_rule} must have integer type, given {type(rule_type).__name__}.')
            try:
                sub = rule_map[rule_type]
            except KeyError:
                raise CJSONDeserializeError(f'Unknown rule type {rule_type} for JSON {json_rule}')
            res.append(sub.from_json(json_rule))
    elif parsed_contents is not None:
        raise CJSONDeserializeError('Rules does not appear to be a list')
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
        logger.debug('Instantiating custom rules engine')
        self._overridden_members['__init__'](self)

    def register(self, widget: QWidget, rules: List[CBaseRule]):

        if is_qt_designer() and not config.DESIGNER_ONLINE:
            logger.debug("Not registering rules because channels won't be connected in the offline designer")
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
                        raise CChannelError("Default channel on the widget is not defined yet. We won't register it for now...")
                    channels_list = [{
                        'channel': default_channel,
                        'trigger': True,
                    }]
                elif rule.channel == CBaseRule.Channel.NOT_IMPORTANT:
                    # TODO: This is probably Python expression. Handle it differently from the body
                    logger.warning('Rules without explicit channel cannot be handled yet')
                    continue
                else:
                    channels_list = [{
                        'channel': rule.channel,
                        'selector': rule.selector,
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
                    ctx: Optional[CContext] = None
                    selector = ch.get('selector', None)
                    if selector is not None:
                        try:
                            ctx = context_cache[selector]
                        except KeyError:
                            ctx = CContext(selector=selector)
                            context_cache[selector] = ctx
                    c = PyDMChannel(address=addr, connection_slot=conn_cb, value_slot=value_cb)
                    cast(CChannel, c).context = ctx
                    job_unit['channels'].append(c)
                    plugin: PyDMPlugin = plugin_for_address(addr)
                    try:
                        conn: PyDMConnection = plugin.connections[addr]
                        job_unit['conn'][ch_idx] = conn.connected
                    except KeyError:
                        pass
                    c.connect()

                self.widget_map[widget_ref].append(job_unit)

    def calculate_expression(self, widget_ref: ReferenceType, _: int, rule: Dict[str, Any]):
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
            logger.warning('Python expressions are not supported for evaluation yet')
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
            return
        elif isinstance(rule_obj, (CEnumRule, CNumRangeRule)):
            from comrad.widgets.mixins import CWidgetRulesMixin
            __, ___, base_type = cast(CWidgetRulesMixin, widget_ref()).RULE_PROPERTIES[rule_obj.prop]
            packet = cast(CChannelData[Any], job_unit['values'][0])
            if not isinstance(packet, CChannelData):
                notify_value(None)
                return

            if isinstance(rule_obj, CNumRangeRule):
                range_val = float(packet.value)
                for range in rule_obj.ranges:
                    if range.min_val <= range_val < range.max_val:
                        notify_value(base_type(range.prop_val))
                        break
                else:
                    notify_value(None)
                return
            elif isinstance(rule_obj, CEnumRule):
                enum_val: CEnumValue = packet.value
                if not isinstance(enum_val, CEnumValue):
                    notify_value(None)
                else:
                    for setting in rule_obj.config:
                        if ((setting.field == CEnumRule.EnumField.CODE and enum_val.code == setting.field_val)
                                or (setting.field == CEnumRule.EnumField.MEANING and enum_val.meaning == setting.field_val)
                                or (setting.field == CEnumRule.EnumField.LABEL and enum_val.label == setting.field_val)):
                            notify_value(base_type(setting.prop_val))
                            break
                    else:
                        notify_value(None)
                return

        logger.exception(f'Unsupported rule type: {type(rule_obj).__name__}')

    def warn_unconnected_channels(self, widget_ref: ReferenceType, index: int):
        """
        Overrides the method because original method accesses in a dictionary-style way, which breaks
        our OO rule. It also changes the severity form error to warning.
        """
        job_unit = self.widget_map[widget_ref][index]
        rule_obj: CBaseRule = job_unit['rule']
        logger.warning(f'Rule "{rule_obj.name}": Not all channels are connected, skipping execution.')


def is_valid_color(entry: Any) -> bool:
    """
    Validates that color format is correct.

    Args:
        entry: Entry possessing the value.

    Returns:
        ``True`` if the color is valid.
    """
    val = getattr(entry, 'prop_val', '')
    return isinstance(val, str) and QColor.isValidColor(val)
