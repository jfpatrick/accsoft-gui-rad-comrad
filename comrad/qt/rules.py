import functools
import weakref
import logging
from weakref import ReferenceType
from typing import List, Dict, Any, Optional, cast
from enum import IntEnum
from qtpy.QtWidgets import QWidget
from qtpy.QtCore import QMutexLocker, Property
from pydm.widgets.rules import RulesDispatcher, RulesEngine as PyDMRulesEngine
from pydm.widgets.channel import PyDMChannel
from pydm.widgets.base import PyDMWidget
from pydm.data_plugins import plugin_for_address
from pydm.data_plugins.plugin import PyDMPlugin, PyDMConnection
from pydm.utilities import is_qt_designer
from pydm import config


logger = logging.getLogger(__name__)


Rule = Dict[str, Any]
"""Rule data structure in the JSON format."""


class RuleType(IntEnum):
    """All available rule setting modes."""

    NUM_RANGE = 0
    """Numeric range where user defines lower and upper numeric
     boundaries and associates property value with each range."""

    PY_EXPR = 1
    """User defines Python expression that can read multiple channels and produce a desired property value."""


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

    @PyDMWidget.rules.setter
    def rules(self, new_rules: str):
        try:
            PyDMWidget.rules.fset(self, new_rules)
        except ChannelException:
            logger.debug(f'Rules setting failed. We do not have the channel yet, will have to be repeated')
            # Set internal data structure without activating property setter behavior
            base = cast(PyDMWidget, self)
            base._rules = new_rules


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


# Monkey-patch the rules engine to have our custom rule format
class RulesEngine(PyDMRulesEngine):

    def __init__(self):
        """
        RulesEngine inherits from QThread and is responsible evaluating the rules
        for all the widgets in the application.
        """
        logger.debug(f'Instantiating custom rules engine')
        super().__init__()

    def register(self: PyDMRulesEngine, widget: QWidget, rules: List[Rule]):

        if is_qt_designer() and not config.DESIGNER_ONLINE:
            logger.debug(f'Not registering rules because channels won\'t be connected in the offline designer')
            return

        logger.debug(f'Registering rules for "{type(widget).__name__}" ({id(widget)}):\n{rules}')
        widget_ref = weakref.ref(widget, self.widget_destroyed)
        if widget_ref in self.widget_map:
            self.unregister(widget_ref)

        # The data structure for the rules is:
        #   {
        #       name: str  # name of the rule, as presented in the rules list (of the rules dialog)
        #       property: str  # property name corresponding to the key in RULE_PROPERTIES
        #       channel: str         # name of the channel (e.g. japc:///dev/prop#field), or reserved keyword "__auto__"
        #                            # for using the default channel of the widget. Can be omitted for cases, where
        #                            # rule body is responsible to collecting the channel information, e.g. in
        #                            # Python expressions. In such case, the name should be "__skip__". We never set it
        #                            # to None, to not confuse with absent value because of the bug.
        #       type: int  # type of the rule: 0 - numerical ranges, 1 - Python expression
        #       body: list / dict # type-specific information. for numerical ranges, this will be list
        #                         # of boundaries, see below
        #   }
        #
        # The data structure for the body of numerical ranges:
        #   [
        #       {
        #           min: float / None  # minimum boundary of the range (can be absent,
        #                              # if no minimum boundary is specified)
        #           max: float / None  # maximum boundary of the range (can be absent,
        #                              # if no maximum boundary is specified)
        #           value: bool / str / float  # property-specific value, depending on the base type of the
        #                                      # property, this will contain the value to set
        #       }
        #   ]
        #
        with QMutexLocker(self.map_lock):
            self.widget_map[widget_ref] = []
            for idx, rule in enumerate(rules):
                channels_list: List[str]

                if 'channel' not in rule or rule['channel'] is None:
                    logger.warning(f'Rules must have a channel defined. This one does not: {rule}')
                    continue

                # TODO: Will this work with wildcard channel? Certainly not dynamically changing one because it's evaluated once
                channel = rule['channel']
                if channel == '__auto__':
                    default_channel = widget_ref().default_rule_channel()
                    if default_channel is None:
                        raise ChannelException(f'Default channel on the widget is not defined yet. We won\' register it for now...')
                    channels_list = [{
                        'channel': default_channel,
                        'trigger': True,
                    }]
                elif channel == '__skip__':
                    # TODO: This is probably Python expression. Handle it differently from the body
                    logger.warning(f'Rules without explicit channel cannot be handled yet')
                    continue
                else:
                    channels_list = [{
                        'channel': channel,
                        'trigger': True,
                    }]

                logger.debug(f'Channel list for rule "{rule.get("name", "")}" will be {channels_list}')

                item: Rule = {}
                item['rule'] = rule
                item['calculate'] = False
                item['values'] = [None] * len(channels_list)
                item['conn'] = [False] * len(channels_list)
                item['channels'] = []

                for ch_idx, ch in enumerate(channels_list):
                    conn_cb = functools.partial(self.callback_conn, widget_ref, idx, ch_idx)
                    value_cb = functools.partial(self.callback_value, widget_ref, idx, ch_idx, ch['trigger'])
                    addr = ch['channel']
                    c = PyDMChannel(address=addr, connection_slot=conn_cb, value_slot=value_cb)
                    item['channels'].append(c)
                    plugin: PyDMPlugin = plugin_for_address(addr)
                    try:
                        conn: PyDMConnection = plugin.connections[addr]
                        item['conn'][ch_idx] = conn.connected
                    except KeyError:
                        pass
                    c.connect()

                self.widget_map[widget_ref].append(item)

    def calculate_expression(self: PyDMRulesEngine, widget_ref: ReferenceType, rule: Rule):
        rule['calculate'] = False

        rule_dict = rule['rule']
        name = rule_dict['name']
        prop = rule_dict['property']
        rule_type = rule_dict['type']
        obj = self

        def notify_value(val):
            payload = {
                'widget': widget_ref,
                'name': name,
                'property': prop,
                'value': val
            }
            obj.rule_signal.emit(payload)

        if rule_type == RuleType.PY_EXPR:
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
        elif rule_type == RuleType.NUM_RANGE:
            _, base_type = cast(WidgetRulesMixin, widget_ref()).RULE_PROPERTIES[prop]
            val = float(rule['values'][0])
            body: List[Dict[str, Any]] = rule_dict['body']
            for condition in body:
                min_val: Optional[float] = condition.get('min')
                max_val: Optional[float] = condition.get('max')
                if (min_val is None or val >= min_val) and (max_val is None or val < max_val):
                    notify_value(base_type(condition['value']))
                    break
            else:
                notify_value(None)
            return
        else:
            logger.exception(f'Unsupported rule type: {rule_type}')
            return


import pydm.widgets.rules
pydm.widgets.rules.RulesEngine = RulesEngine
