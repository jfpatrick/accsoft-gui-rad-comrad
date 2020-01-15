import pytest
from typing import Dict, Any, cast, Optional
from unittest import mock
from pytestqt.qtbot import QtBot
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QWidget
from comrad.rules import (CNumRangeRule, CExpressionRule, CJSONDeserializeError, unpack_rules,
                          CRulesEngine, CChannelError)
from comrad.json import CJSONEncoder


@pytest.mark.parametrize('channel,resulting_channel', [
    ('japc://dev/prop#field', 'japc://dev/prop#field'),
    ('__auto__', CNumRangeRule.Channel.DEFAULT),
])
@pytest.mark.parametrize('range_min,range_max', [
    (0.0, 1.0),
    (1.0, 0.0),
    (-1.5, 10.5),
])
@pytest.mark.parametrize('range_val', [
    0.5,
    'val',
    True,
    False,
])
def test_num_range_rule_deserialize_succeeds(channel, resulting_channel, range_min, range_max, range_val):
    rule = CNumRangeRule.from_json({
        'name': 'test_name',
        'prop': 'opacity',
        'channel': channel,
        'ranges': [{
            'min': range_min,
            'max': range_max,
            'value': range_val,
        }],
    })
    assert isinstance(rule, CNumRangeRule)
    assert rule.name == 'test_name'
    assert rule.prop == 'opacity'
    assert rule.channel == resulting_channel
    assert len(rule.ranges) == 1
    range = rule.ranges[0]
    assert range.min_val == range_min
    assert range.max_val == range_max
    assert range.prop_val == range_val


@pytest.mark.parametrize('json_obj,error_msg', [
    ({'prop': 'opacity', 'channel': '__auto__'}, r'Can\\\'t parse range JSON: "name" is not a string*'),
    ({'name': 2, 'prop': 'opacity', 'channel': '__auto__'}, r'Can\\\'t parse range JSON: "name" is not a string*'),
    ({'name': 'test_name', 'channel': '__auto__'}, r'Can\\\'t parse range JSON: "prop" is not a string*'),
    ({'name': 'test_name', 'prop': (), 'channel': '__auto__'}, r'Can\\\'t parse range JSON: "prop" is not a string*'),
    ({'name': 'test_name', 'prop': 'opacity'}, r'Can\\\'t parse range JSON: "channel" is not a string*'),
    ({'name': 'test_name', 'prop': 'opacity', 'channel': 53}, r'Can\\\'t parse range JSON: "channel" is not a string*'),
    ({'name': 'test_name', 'prop': 'opacity', 'channel': '__auto__'}, r'Can\\\'t parse range JSON: "ranges" is not a list*'),
    ({'name': 'test_name', 'prop': 'opacity', 'channel': '__auto__', 'ranges': [{'min': 0, 'max': 0.5, 'value': 0.1}]}, r'Can\\\'t parse range JSON: "min" is not float, "int" given*'),
    ({'name': 'test_name', 'prop': 'opacity', 'channel': '__auto__', 'ranges': [{'min': 0.0, 'max': 5, 'value': 0.1}]}, r'Can\\\'t parse range JSON: "max" is not float, "int" given*'),
    ({'name': 'test_name', 'prop': 'opacity', 'channel': '__auto__', 'ranges': [{'min': 0.0, 'max': 0.5}]}, r'Can\\\'t parse range JSON: "value" has unsupported type "NoneType"*'),
    ({'name': 'test_name', 'prop': 'opacity', 'channel': '__auto__', 'ranges': [{'min': 0.0, 'max': 0.5, 'value': ()}]}, r'Can\\\'t parse range JSON: "value" has unsupported type "tuple"*'),
    ({'name': 'test_name', 'prop': 'opacity', 'channel': '__auto__', 'ranges': [{'min': 0.0, 'max': 0.5, 'value': 4}]}, r'Can\\\'t parse range JSON: "value" has unsupported type "int"*'),
    ({'name': 'test_name', 'prop': 'opacity', 'channel': '__auto__', 'ranges': [{'max': 0.5, 'value': 0.5}]}, r'Can\\\'t parse range JSON: "min" is not float, "NoneType" given*'),
    ({'name': 'test_name', 'prop': 'opacity', 'channel': '__auto__', 'ranges': [{'min': 0.5, 'value': 0.5}]}, r'Can\\\'t parse range JSON: "max" is not float, "NoneType" given*'),
])
def test_num_range_rule_deserialize_fails(json_obj, error_msg):
    with pytest.raises(CJSONDeserializeError, match=error_msg):
        CNumRangeRule.from_json(json_obj)


@pytest.mark.parametrize('prop', [
    'opacity',
    'color',
    None,
])
@pytest.mark.parametrize('channel', [
    'japc://dev/prop#field',
    '__auto__',
    None,
])
@pytest.mark.parametrize('name', [
    'test_name',
    'Test Name 2',
    None,
])
@pytest.mark.parametrize('ranges', [
    [],
    [CNumRangeRule.Range(min_val=0.0, max_val=1.0, prop_val=0.5)],
    [CNumRangeRule.Range(min_val=1.0, max_val=0.0, prop_val=0.5)],
    [
        CNumRangeRule.Range(min_val=0.0, max_val=1.0, prop_val=0.5),
        CNumRangeRule.Range(min_val=1.0, max_val=2.0, prop_val=0.75),
    ],
    [
        CNumRangeRule.Range(min_val=0.0, max_val=1.0, prop_val='#FF0000'),
        CNumRangeRule.Range(min_val=1.0, max_val=2.0, prop_val='#00FF00'),
        CNumRangeRule.Range(min_val=2.0, max_val=3.0, prop_val='#0000FF'),
        CNumRangeRule.Range(min_val=3.0, max_val=4.0, prop_val='#000000'),
    ],
])
def test_num_range_rule_serialize_succeeds(name, prop, channel, ranges):
    rule = CNumRangeRule(name=name,
                         prop=prop,
                         channel=channel,
                         ranges=ranges)
    import json
    serialized = json.loads(json.dumps(rule.to_json(), cls=CJSONEncoder))  # To not compare against the string but rather a dictionary

    def map_range(range: CNumRangeRule.Range) -> Dict[str, Any]:
        return {
            'min': range.min_val,
            'max': range.max_val,
            'value': range.prop_val,
        }

    assert serialized == {
        'name': name,
        'prop': prop,
        'channel': channel,
        'ranges': list(map(map_range, ranges)),
        'type': CNumRangeRule.Type.NUM_RANGE.value,
    }


@pytest.mark.parametrize('prop', [
    'opacity',
    'color',
])
@pytest.mark.parametrize('channel', [
    'japc://dev/prop#field',
    '__auto__',
])
@pytest.mark.parametrize('ranges', [
    [CNumRangeRule.Range(min_val=0.0, max_val=1.0, prop_val=0.5)],
    [
        CNumRangeRule.Range(min_val=0.0, max_val=1.0, prop_val=0.5),
        CNumRangeRule.Range(min_val=1.0, max_val=2.0, prop_val=0.75),
    ],
    [
        CNumRangeRule.Range(min_val=0.0, max_val=0.0, prop_val=0.5),
    ],
    [
        CNumRangeRule.Range(min_val=0.0, max_val=1.0, prop_val='#FF0000'),
        CNumRangeRule.Range(min_val=1.0, max_val=2.0, prop_val='#00FF00'),
        CNumRangeRule.Range(min_val=2.0, max_val=3.0, prop_val='#0000FF'),
        CNumRangeRule.Range(min_val=3.0, max_val=4.0, prop_val='#000000'),
    ],
])
def test_num_range_rule_validate_succeeds(prop, channel, ranges):
    rule = CNumRangeRule(name='test_name',
                         prop=prop,
                         channel=channel,
                         ranges=ranges)
    rule.validate()  # If fails, will throw


@pytest.mark.parametrize('attr,val,err', [
    ('name', '', 'Not every rule has a name*'),
    ('name', False, 'Not every rule has a name*'),
    ('name', None, 'Not every rule has a name*'),
    ('name', [], 'Not every rule has a name*'),
    ('name', (), 'Not every rule has a name*'),
    ('prop', '', 'Rule "test_name" is missing property definition*'),
    ('prop', False, 'Rule "test_name" is missing property definition*'),
    ('prop', None, 'Rule "test_name" is missing property definition*'),
    ('prop', [], 'Rule "test_name" is missing property definition*'),
    ('prop', (), 'Rule "test_name" is missing property definition*'),
    ('ranges', [], 'Rule "test_name" must have at least one range defined*'),
    ('ranges', (), 'Rule "test_name" must have at least one range defined*'),
    ('ranges', [
        CNumRangeRule.Range(min_val=0.0, max_val=1.0, prop_val=0.5),
        CNumRangeRule.Range(min_val=0.5, max_val=1.5, prop_val=0.5),
    ], 'Rule "test_name" has overlapping ranges*'),
    ('ranges', [
        CNumRangeRule.Range(min_val=0.5, max_val=1.5, prop_val=0.5),
        CNumRangeRule.Range(min_val=0.0, max_val=1.0, prop_val=0.5),
    ], 'Rule "test_name" has overlapping ranges*'),
    ('ranges', [
        CNumRangeRule.Range(min_val=0.0, max_val=1.0, prop_val=0.5),
        CNumRangeRule.Range(min_val=0.0, max_val=1.0, prop_val=0.5),
    ], 'Rule "test_name" has overlapping ranges*'),
    ('ranges', [
        CNumRangeRule.Range(min_val=-1.0, max_val=1.0, prop_val=0.5),
        CNumRangeRule.Range(min_val=0.5, max_val=0.75, prop_val=0.5),
    ], 'Rule "test_name" has overlapping ranges*'),
    ('ranges', [
        CNumRangeRule.Range(min_val=0.5, max_val=0.75, prop_val=0.5),
        CNumRangeRule.Range(min_val=-1.0, max_val=1.0, prop_val=0.5),
    ], 'Rule "test_name" has overlapping ranges*'),
    ('ranges', [
        CNumRangeRule.Range(min_val=1.0, max_val=0.0, prop_val=0.5),
    ], 'Some ranges have inverted boundaries (max < min)*'),
])
def test_num_range_rule_validate_fails(attr, val, err):
    rule = CNumRangeRule(name='test_name',
                         prop='test_prop',
                         channel='japc://dev/prop#field',
                         ranges=[CNumRangeRule.Range(min_val=0.0, max_val=0.0, prop_val=0.5)])
    setattr(rule, attr, val)
    with pytest.raises(TypeError, match=fr'{err}'):
        rule.validate()


# TODO: CExpressionRule are disabled until CExpressionRule.from_json is implemented
@pytest.mark.parametrize('rule_cnt,rule_types,names,props,channels,payloads,json_str', [
    (1, [CNumRangeRule], ['rule1'], ['color'], ['__auto__'], [1],
     '[{"type":0,"name":"rule1","prop":"color","channel":"__auto__","ranges":[{"min":0.0,"max":0.1,"value":"#FF0000"}]}]'),
    # (1, [CExpressionRule], ['rule1'], ['color'], ['__auto__'], ["expr1"],
    #  '[{"type":1,"name":"rule1","prop":"color","channel":"__auto__","expr":"expr1"}]'),
    (1, [CNumRangeRule], ['rule2'], ['opacity'], ['japc://dev/prop#field'], [2],
     '[{"type":0,"name":"rule2","prop":"opacity","channel":"japc://dev/prop#field","ranges":[{"min":0.0,"max":0.1,"value":0.9}, {"min":0.1,"max":0.2,"value":0.5}]}]'),
    (1, [CNumRangeRule], ['rule2'], ['opacity'], ['japc://dev/prop#field'], [0],
     '[{"type":0,"name":"rule2","prop":"opacity","channel":"japc://dev/prop#field","ranges":[]}]'),
    (2, [CNumRangeRule, CNumRangeRule], ['rule1', 'rule2'], ['color', 'opacity'], ['__auto__', '__auto__'], [0, 0],
     '[{"type":0,"name":"rule1","prop":"color","channel":"__auto__","ranges":[]},{"type":0,"name":"rule2","prop":"opacity","channel":"__auto__","ranges":[]}]'),
    # (2, [CNumRangeRule, CExpressionRule], ['rule1', 'rule2'], ['color', 'opacity'], ['__auto__', '__auto__'], [0, 'expr2'],
    #  '[{"type":0,"name":"rule1","prop":"color","channel":"__auto__","ranges":[]},{"type":1,"name":"rule2","prop":"opacity","channel":"__auto__","expr":"expr2"}]'),
    # (2, [CExpressionRule, CExpressionRule], ['rule1', 'rule2'], ['color', 'opacity'], ['__auto__', '__auto__'], ['expr1', 'expr2'],
    #  '[{"type":1,"name":"rule1","prop":"color","channel":"__auto__","expr":"expr1"},{"type":1,"name":"rule2","prop":"opacity","channel":"__auto__","expr":"expr2"}]'),
])
def test_unpack_rules_succeeds(rule_cnt, rule_types, names, props, channels, payloads, json_str):
    res = unpack_rules(json_str)  # If fails, will throw
    assert len(res) == rule_cnt
    for rule, rule_type, name, prop, channel, payload in zip(res, rule_types, names, props, channels, payloads):
        assert isinstance(rule, rule_type)
        assert rule.name == name
        assert rule.prop == prop
        assert rule.channel == CNumRangeRule.Channel.DEFAULT if channel == '__auto__' else channel
        if rule_type == CNumRangeRule:
            assert len(cast(CNumRangeRule, rule).ranges) == payload
        elif rule_type == CExpressionRule:
            assert cast(CExpressionRule, rule).expr == payload


@pytest.mark.parametrize('err,err_type,json_str', [
    (r'type', KeyError, '[{"name":"rule2","prop":"opacity","channel":"japc://dev/prop#field","ranges":null}]'),
    (r'Can\\\'t parse range JSON: "name" is not a string', CJSONDeserializeError, '[{"type":0,"prop":"opacity","channel":"japc://dev/prop#field","ranges":null}]'),
    (r'Can\\\'t parse range JSON: "prop" is not a string', CJSONDeserializeError, '[{"name":"rule2","type":0,"channel":"japc://dev/prop#field","ranges":null}]'),
    (r'Can\\\'t parse range JSON: "channel" is not a string', CJSONDeserializeError, '[{"name":"rule2","prop":"opacity","type":0,"ranges":null}]'),
    (r'Can\\\'t parse range JSON: "ranges" is not a list', CJSONDeserializeError, '[{"name":"rule2","prop":"opacity","type":0,"channel":"__auto__"}]'),
    (r'Can\\\'t parse range JSON: "ranges" is not a list, "NoneType" given*', CJSONDeserializeError, '[{"type":0,"name":"rule2","prop":"opacity","channel":"japc://dev/prop#field","ranges":null}]'),
    (r'must have integer type, given str', CJSONDeserializeError, '[{"type":"test","name":"rule1","prop":"opacity","channel":"japc://dev/prop#field","ranges":[]}]'),
    (r'Rules does not appear to be a list', CJSONDeserializeError, '{"type":0,"name":"rule2","prop":"opacity","channel":"japc://dev/prop#field","ranges":[]}'),
    (r'Unknown rule type 2 for JSON', CJSONDeserializeError, '[{"type":2,"name":"rule2","prop":"opacity","channel":"japc://dev/prop#field","ranges":[]}]'),
    (r'', NotImplementedError, '[{"type":1,"name":"rule2","prop":"opacity","channel":"japc://dev/prop#field","expr":""}]'),  # TODO: Remove when expression rules are implemented
])
def test_unpack_rules_fails(err, err_type, json_str):
    with pytest.raises(err_type, match=err):
        unpack_rules(json_str)


@pytest.mark.parametrize('designer_online', [
    True,
    False,
])
def test_rules_engine_does_not_register_in_designer(qtbot: QtBot, designer_online):
    engine = CRulesEngine()
    widget = QWidget()
    qtbot.addWidget(widget)
    rule = CNumRangeRule(name='test_name',
                         prop='test_prop',
                         channel='japc://dev/prop#field',
                         ranges=[CNumRangeRule.Range(min_val=0.0, max_val=0.0, prop_val=0.5)])

    import comrad.rules
    import pydm.data_plugins
    pydm.data_plugins.plugin_for_address = comrad.rules.plugin_for_address = mock.MagicMock()
    comrad.rules.config.DESIGNER_ONLINE = designer_online
    comrad.rules.is_qt_designer = mock.MagicMock(return_value=True)
    engine.register(widget=widget, rules=[rule])

    try:
        job_summary = next(iter(engine.widget_map.values()))
    except StopIteration:
        job_summary = []

    if designer_online:
        assert len(job_summary) == 1
    else:
        assert len(job_summary) == 0


@pytest.mark.parametrize('faulty', [
    True,
    False,
])
def test_rules_engine_does_not_register_faulty_rules(qtbot: QtBot, faulty):
    engine = CRulesEngine()
    widget = QWidget()
    qtbot.addWidget(widget)
    rule = CNumRangeRule(name='test_name',
                         prop='test_prop',
                         channel='japc://dev/prop#field',
                         ranges=None if faulty else [CNumRangeRule.Range(min_val=0.0, max_val=0.0, prop_val=0.5)])

    import comrad.rules
    import pydm.data_plugins
    pydm.data_plugins.plugin_for_address = comrad.rules.plugin_for_address = mock.MagicMock()
    comrad.rules.is_qt_designer = mock.MagicMock(return_value=False)

    engine.register(widget=widget, rules=[rule])

    try:
        job_summary = next(iter(engine.widget_map.values()))
    except StopIteration:
        job_summary = []
    if faulty:
        assert len(job_summary) == 0
    else:
        assert len(job_summary) == 1


def test_rules_engine_unregisters_old_rules(qtbot: QtBot):
    engine = CRulesEngine()
    widget = QWidget()
    qtbot.addWidget(widget)

    import comrad.rules
    import pydm.data_plugins
    pydm.data_plugins.plugin_for_address = comrad.rules.plugin_for_address = mock.MagicMock()
    comrad.rules.is_qt_designer = mock.MagicMock(return_value=False)

    rule = CNumRangeRule(name='rule1',
                         prop='test_prop',
                         channel='japc://dev/prop#field',
                         ranges=[CNumRangeRule.Range(min_val=0.0, max_val=0.0, prop_val=0.5)])
    engine.register(widget=widget, rules=[rule])
    assert len(engine.widget_map) == 1
    job_summary = next(iter(engine.widget_map.values()))
    assert len(job_summary) == 1
    assert cast(CNumRangeRule, job_summary[0]['rule']).name == 'rule1'

    new_rule = CNumRangeRule(name='rule2',
                             prop='test_prop',
                             channel='japc://dev/prop#field',
                             ranges=[CNumRangeRule.Range(min_val=0.0, max_val=0.0, prop_val=0.5)])
    engine.register(widget=widget, rules=[new_rule])
    assert len(engine.widget_map) == 1
    job_summary = next(iter(engine.widget_map.values()))
    assert len(job_summary) == 1
    assert cast(CNumRangeRule, job_summary[0]['rule']).name == 'rule2'


@pytest.mark.parametrize('default_channel', [
    'japc://default_dev/prop#field',
    None,
])
def test_rules_engine_finds_default_channel(qtbot: QtBot, default_channel):
    from comrad.widgets.mixins import CWidgetRulesMixin

    class CustomWidget(QWidget, CWidgetRulesMixin):

        def __init__(self, parent: Optional[QWidget] = None):
            QWidget.__init__(self, parent)
            CWidgetRulesMixin.__init__(self)

        def default_rule_channel(self):
            return default_channel

    engine = CRulesEngine()
    widget = CustomWidget()
    qtbot.addWidget(widget)

    import comrad.rules
    import pydm.data_plugins
    pydm.data_plugins.plugin_for_address = comrad.rules.plugin_for_address = mock.MagicMock()
    comrad.rules.is_qt_designer = mock.MagicMock(return_value=False)

    rule = CNumRangeRule(name='test_name',
                         prop='test_prop',
                         channel=CNumRangeRule.Channel.DEFAULT,
                         ranges=[CNumRangeRule.Range(min_val=0.0, max_val=0.0, prop_val=0.5)])

    if default_channel is None:
        with pytest.raises(CChannelError):
            engine.register(widget=widget, rules=[rule])
        try:
            job_summary = next(iter(engine.widget_map.values()))
        except StopIteration:
            job_summary = []
        assert len(job_summary) == 0
    else:
        engine.register(widget=widget, rules=[rule])
        assert len(engine.widget_map) == 1
        job_summary = next(iter(engine.widget_map.values()))
        assert len(job_summary) == 1
        assert len(job_summary[0]['channels']) == 1

        from pydm.widgets.channel import PyDMChannel
        assert cast(PyDMChannel, job_summary[0]['channels'][0]).address == default_channel


def test_rules_engine_uses_custom_channels(qtbot: QtBot):
    engine = CRulesEngine()
    widget = QWidget()
    qtbot.addWidget(widget)

    import comrad.rules
    import pydm.data_plugins
    pydm.data_plugins.plugin_for_address = comrad.rules.plugin_for_address = mock.MagicMock()
    comrad.rules.is_qt_designer = mock.MagicMock(return_value=False)

    rule = CNumRangeRule(name='test_name',
                         prop='test_prop',
                         channel='japc://dev/prop#field',
                         ranges=[CNumRangeRule.Range(min_val=0.0, max_val=0.0, prop_val=0.5)])
    engine.register(widget=widget, rules=[rule])
    assert len(engine.widget_map) == 1
    job_summary = next(iter(engine.widget_map.values()))
    assert len(job_summary) == 1
    assert len(job_summary[0]['channels']) == 1
    from pydm.widgets.channel import PyDMChannel
    channel = cast(PyDMChannel, job_summary[0]['channels'][0])
    assert channel.address == 'japc://dev/prop#field'


@pytest.mark.parametrize('incoming_val,range_min,range_max,should_calc', [
    (0, -1, 1, True),
    (-1, -1, 1, True),
    (1, -1, 1, False),
    (-2, -1, 1, False),
    ('rubbish', -1, 1, False),
])
def test_rules_engine_calculates_range_value(qtbot: QtBot, incoming_val, range_min, range_max, should_calc):
    engine = CRulesEngine()
    callback = mock.MagicMock()
    engine.rule_signal.connect(callback, Qt.DirectConnection)

    class CustomWidget(QWidget):
        RULE_PROPERTIES = {
            'test_prop': (None, str),
        }

    widget = CustomWidget()
    qtbot.addWidget(widget)

    rule = CNumRangeRule(name='test_name',
                         prop='test_prop',
                         channel='japc://dev/prop#field',
                         ranges=[CNumRangeRule.Range(min_val=range_min, max_val=range_max, prop_val='HIT')])
    import weakref
    widget_ref = weakref.ref(widget, engine.widget_destroyed)
    job_unit = {
        'calculate': True,
        'rule': rule,
        'values': [incoming_val],
    }

    if isinstance(incoming_val, int):
        engine.calculate_expression(widget_ref=widget_ref, rule=job_unit)
        callback.assert_called_with({
            'widget': widget_ref,
            'name': 'test_name',
            'property': 'test_prop',
            'value': 'HIT' if should_calc else None,
        })
    else:
        with pytest.raises(ValueError):
            engine.calculate_expression(widget_ref=widget_ref, rule=job_unit)
        callback.assert_not_called()
