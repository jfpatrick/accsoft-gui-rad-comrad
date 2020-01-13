import pytest
from typing import Dict, Any, cast
from unittest import mock
from pytestqt.qtbot import QtBot
from qtpy.QtWidgets import QWidget
from comrad.rules import CNumRangeRule, CExpressionRule, BaseRule, JSONDeserializeError, unpack_rules, CRulesEngine
from comrad.json import ComRADJSONEncoder


@pytest.mark.parametrize('channel,resulting_channel', [
    ('japc://dev/prop#field', 'japc://dev/prop#field'),
    ('__auto__', BaseRule.Channel.DEFAULT),
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
    with pytest.raises(JSONDeserializeError, match=error_msg):
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
    serialized = json.loads(json.dumps(rule.to_json(), cls=ComRADJSONEncoder))  # To not compare against the string but rather a dictionary

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
        'type': BaseRule.Type.NUM_RANGE.value,
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
        assert rule.channel == BaseRule.Channel.DEFAULT if channel == '__auto__' else channel
        if rule_type == CNumRangeRule:
            assert len(cast(CNumRangeRule, rule).ranges) == payload
        elif rule_type == CExpressionRule:
            assert cast(CExpressionRule, rule).expr == payload


@pytest.mark.parametrize('err,err_type,json_str', [
    (r'type', KeyError, '[{"name":"rule2","prop":"opacity","channel":"japc://dev/prop#field","ranges":null}]'),
    (r'Can\\\'t parse range JSON: "name" is not a string', JSONDeserializeError, '[{"type":0,"prop":"opacity","channel":"japc://dev/prop#field","ranges":null}]'),
    (r'Can\\\'t parse range JSON: "prop" is not a string', JSONDeserializeError, '[{"name":"rule2","type":0,"channel":"japc://dev/prop#field","ranges":null}]'),
    (r'Can\\\'t parse range JSON: "channel" is not a string', JSONDeserializeError, '[{"name":"rule2","prop":"opacity","type":0,"ranges":null}]'),
    (r'Can\\\'t parse range JSON: "ranges" is not a list', JSONDeserializeError, '[{"name":"rule2","prop":"opacity","type":0,"channel":"__auto__"}]'),
    (r'Can\\\'t parse range JSON: "ranges" is not a list, "NoneType" given*', JSONDeserializeError, '[{"type":0,"name":"rule2","prop":"opacity","channel":"japc://dev/prop#field","ranges":null}]'),
    (r'must have integer type, given str', JSONDeserializeError, '[{"type":"test","name":"rule1","prop":"opacity","channel":"japc://dev/prop#field","ranges":[]}]'),
    (r'Rules does not appear to be a list', JSONDeserializeError, '{"type":0,"name":"rule2","prop":"opacity","channel":"japc://dev/prop#field","ranges":[]}'),
    (r'Unknown rule type 2 for JSON', JSONDeserializeError, '[{"type":2,"name":"rule2","prop":"opacity","channel":"japc://dev/prop#field","ranges":[]}]'),
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
    from comrad import CApplication
    with mock.patch.object(CApplication.instance(), 'aboutToQuit', create=True):
        engine = CRulesEngine()
        widget = QWidget()
        qtbot.addWidget(widget)
        rule = CNumRangeRule(name='test_name',
                             prop='test_prop',
                             channel='japc://dev/prop#field',
                             ranges=[CNumRangeRule.Range(min_val=0.0, max_val=0.0, prop_val=0.5)])

        import comrad.rules
        comrad.rules.plugin_for_address = mock.MagicMock()
        comrad.rules.config.DESIGNER_ONLINE = designer_online
        comrad.rules.is_qt_designer = mock.MagicMock(return_value=True)
        engine.register(widget=widget, rules=[rule])

        if designer_online:
            assert len(engine.widget_map) == 1
        else:
            assert engine.widget_map == {}


@pytest.mark.skip
def test_rules_engine_does_not_register_faulty_rules():
    pass


@pytest.mark.skip
def test_rules_engine_unregisters_old_rules():
    pass


@pytest.mark.skip
def test_rules_engine_finds_default_channel():
    pass


@pytest.mark.skip
def test_rules_engine_uses_custom_channels():
    pass


@pytest.mark.skip
@pytest.mark.parametrize('val,range_min,range_max', [
    (0, -1, 1),
    (-1, -1, 1),
    (1, -1, 1),
    (-2, -1, 1),
    ('rubbish', -1, 1),
])
def test_rules_engine_calculates_range_value(val, range_min, range_max):
    pass
