import pytest
from typing import Dict, Any, cast, Optional
from unittest import mock
from pytestqt.qtbot import QtBot
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QWidget
from comrad.rules import (CNumRangeRule, CExpressionRule, CEnumRule, CJSONDeserializeError, unpack_rules,
                          CRulesEngine, CChannelError)
from comrad.json import CJSONEncoder
from comrad.data.channel import CChannelData
from comrad import CEnumValue


@pytest.mark.parametrize('channel,resulting_channel', [
    ('dev/prop#field', 'dev/prop#field'),
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
    'dev/prop#field',
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
    'dev/prop#field',
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
    ], 'Range 1.0-0.0 has inverted boundaries (max < min)*'),
])
def test_num_range_rule_validate_fails(attr, val, err):
    rule = CNumRangeRule(name='test_name',
                         prop='test_prop',
                         channel='dev/prop#field',
                         ranges=[CNumRangeRule.Range(min_val=0.0, max_val=0.0, prop_val=0.5)])
    setattr(rule, attr, val)
    with pytest.raises(TypeError, match=fr'{err}'):
        rule.validate()


@pytest.mark.parametrize('channel,resulting_channel', [
    ('dev/prop#field', 'dev/prop#field'),
    ('__auto__', CNumRangeRule.Channel.DEFAULT),
])
@pytest.mark.parametrize('enum_field,expected_field,field_val,expected_val', [
    (0, CEnumRule.EnumField.CODE, 99, 99),
    (1, CEnumRule.EnumField.LABEL, 'test-label', 'test-label'),
    (1, CEnumRule.EnumField.LABEL, '', ''),
    (1, CEnumRule.EnumField.LABEL, '99', '99'),
    (2, CEnumRule.EnumField.MEANING, int(CEnumValue.Meaning.ON.value), CEnumValue.Meaning.ON),
    (2, CEnumRule.EnumField.MEANING, int(CEnumValue.Meaning.OFF.value), CEnumValue.Meaning.OFF),
    (2, CEnumRule.EnumField.MEANING, int(CEnumValue.Meaning.WARNING.value), CEnumValue.Meaning.WARNING),
    (2, CEnumRule.EnumField.MEANING, int(CEnumValue.Meaning.ERROR.value), CEnumValue.Meaning.ERROR),
    (2, CEnumRule.EnumField.MEANING, int(CEnumValue.Meaning.NONE.value), CEnumValue.Meaning.NONE),
])
@pytest.mark.parametrize('applied_val', [
    0.5,
    'val',
    True,
    False,
])
def test_enum_rule_deserialize_succeeds(channel, resulting_channel, enum_field, expected_field, field_val, expected_val, applied_val):
    rule = CEnumRule.from_json({
        'name': 'test_name',
        'prop': 'opacity',
        'channel': channel,
        'config': [{
            'field': enum_field,
            'fv': field_val,
            'value': applied_val,
        }],
    })
    assert isinstance(rule, CEnumRule)
    assert rule.name == 'test_name'
    assert rule.prop == 'opacity'
    assert rule.channel == resulting_channel
    assert len(rule.config) == 1
    setting = rule.config[0]
    assert setting.field == expected_field
    assert setting.field_val == expected_val
    assert setting.prop_val == applied_val


@pytest.mark.parametrize('json_obj,error_msg', [
    ({'prop': 'opacity', 'channel': '__auto__'}, r'Can\\\'t parse rule JSON: "name" is not a string*'),
    ({'name': 2, 'prop': 'opacity', 'channel': '__auto__'}, r'Can\\\'t parse rule JSON: "name" is not a string*'),
    ({'name': 'test_name', 'channel': '__auto__'}, r'Can\\\'t parse rule JSON: "prop" is not a string*'),
    ({'name': 'test_name', 'prop': (), 'channel': '__auto__'}, r'Can\\\'t parse rule JSON: "prop" is not a string*'),
    ({'name': 'test_name', 'prop': 'opacity'}, r'Can\\\'t parse rule JSON: "channel" is not a string*'),
    ({'name': 'test_name', 'prop': 'opacity', 'channel': 53}, r'Can\\\'t parse rule JSON: "channel" is not a string*'),
    ({'name': 'test_name', 'prop': 'opacity', 'channel': '__auto__', 'config': [{'field': 0.5, 'fv': 0, 'value': 0.1}]}, r'Can\\\'t parse enum JSON: "field" is not int, "float" given*'),
    ({'name': 'test_name', 'prop': 'opacity', 'channel': '__auto__', 'config': [{'fv': 0, 'value': 0.1}]}, r'Can\\\'t parse enum JSON: "field" is not int, "NoneType" given*'),
    ({'name': 'test_name', 'prop': 'opacity', 'channel': '__auto__', 'config': [{'field': 0, 'fv': 'test', 'value': 0.1}]}, r'Can\\\'t parse enum JSON: "fv" is not int, as required by field type "CODE", "str" given*'),
    ({'name': 'test_name', 'prop': 'opacity', 'channel': '__auto__', 'config': [{'field': 1, 'fv': 3, 'value': 0.1}]}, r'Can\\\'t parse enum JSON: "fv" is not str, as required by field type "LABEL", "int" given'),
    ({'name': 'test_name', 'prop': 'opacity', 'channel': '__auto__', 'config': [{'field': 2, 'fv': 'test', 'value': 0.1}]}, r'Can\\\'t parse enum JSON: "fv" is not int, as required by field type "MEANING", "str" given'),
    ({'name': 'test_name', 'prop': 'opacity', 'channel': '__auto__', 'config': [{'field': 0, 'value': 0.1}]}, r'Can\\\'t parse enum JSON: "fv" is not int, as required by field type "CODE", "NoneType" given'),
    ({'name': 'test_name', 'prop': 'opacity', 'channel': '__auto__', 'config': [{'field': 2, 'fv': 99, 'value': 0.1}]}, r'Can\\\'t parse enum JSON: "fv" value "99" does not correspond to the known possible options of meaning*'),
    ({'name': 'test_name', 'prop': 'opacity', 'channel': '__auto__', 'config': [{'field': 99, 'fv': 'test', 'value': 0.1}]}, r'Can\\\'t parse enum JSON: "field" value "99" does not correspond to the known possible options*'),
    ({'name': 'test_name', 'prop': 'opacity', 'channel': '__auto__', 'config': [{'field': 0, 'fv': 1, 'value': ()}]}, r'Can\\\'t parse enum JSON: "value" has unsupported type "tuple"*'),
    ({'name': 'test_name', 'prop': 'opacity', 'channel': '__auto__', 'config': [{'field': 0, 'fv': 1, 'value': 4}]}, r'Can\\\'t parse enum JSON: "value" has unsupported type "int"*'),
])
def test_enum_rule_deserialize_fails(json_obj, error_msg):
    with pytest.raises(CJSONDeserializeError, match=error_msg):
        CEnumRule.from_json(json_obj)


@pytest.mark.parametrize('prop', [
    'opacity',
    'color',
    None,
])
@pytest.mark.parametrize('channel', [
    'dev/prop#field',
    '__auto__',
    None,
])
@pytest.mark.parametrize('name', [
    'test_name',
    'Test Name 2',
    None,
])
@pytest.mark.parametrize('config', [
    [],
    [CEnumRule.EnumConfig(field=CEnumRule.EnumField.CODE, field_val=31, prop_val=0.5)],
    [CEnumRule.EnumConfig(field=CEnumRule.EnumField.LABEL, field_val='test-label', prop_val=0.5)],
    [CEnumRule.EnumConfig(field=CEnumRule.EnumField.MEANING, field_val=CEnumValue.Meaning.ON, prop_val=0.5)],
    [CEnumRule.EnumConfig(field=CEnumRule.EnumField.MEANING, field_val=CEnumValue.Meaning.OFF, prop_val=0.5)],
    [CEnumRule.EnumConfig(field=CEnumRule.EnumField.MEANING, field_val=CEnumValue.Meaning.WARNING, prop_val=0.5)],
    [CEnumRule.EnumConfig(field=CEnumRule.EnumField.MEANING, field_val=CEnumValue.Meaning.ERROR, prop_val=0.5)],
    [CEnumRule.EnumConfig(field=CEnumRule.EnumField.MEANING, field_val=CEnumValue.Meaning.NONE, prop_val=0.5)],
    [
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.CODE, field_val=31, prop_val=0.5),
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.LABEL, field_val='test-label', prop_val=0.5),
    ],
    [
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.CODE, field_val=0, prop_val='#FF0000'),
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.CODE, field_val=1, prop_val='#00FF00'),
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.CODE, field_val=2, prop_val='#0000FF'),
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.CODE, field_val=3, prop_val='#000000'),
    ],
    [
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.LABEL, field_val='ON', prop_val='#FF0000'),
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.LABEL, field_val='OFF', prop_val='#00FF00'),
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.LABEL, field_val='UNKNOWN', prop_val='#0000FF'),
    ],
    [
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.MEANING, field_val=CEnumValue.Meaning.WARNING, prop_val='#FF0000'),
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.MEANING, field_val=CEnumValue.Meaning.ON, prop_val='#00FF00'),
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.MEANING, field_val=CEnumValue.Meaning.OFF, prop_val='#0000FF'),
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.MEANING, field_val=CEnumValue.Meaning.ERROR, prop_val='#000000'),
    ],
])
def test_enum_rule_serialize_succeeds(name, prop, channel, config):
    rule = CEnumRule(name=name,
                     prop=prop,
                     channel=channel,
                     config=config)
    import json
    serialized = json.loads(json.dumps(rule.to_json(), cls=CJSONEncoder))  # To not compare against the string but rather a dictionary

    def map_range(conf: CEnumRule.EnumConfig) -> Dict[str, Any]:
        return {
            'field': conf.field,
            'fv': conf.field_val,
            'value': conf.prop_val,
        }

    assert serialized == {
        'name': name,
        'prop': prop,
        'channel': channel,
        'config': list(map(map_range, config)),
        'type': CNumRangeRule.Type.ENUM.value,
    }


@pytest.mark.parametrize('prop', [
    'opacity',
    'color',
])
@pytest.mark.parametrize('channel', [
    'dev/prop#field',
    '__auto__',
])
@pytest.mark.parametrize('config', [
    [CEnumRule.EnumConfig(field=CEnumRule.EnumField.CODE, field_val=31, prop_val=0.5)],
    [CEnumRule.EnumConfig(field=CEnumRule.EnumField.LABEL, field_val='test-label', prop_val=0.5)],
    [CEnumRule.EnumConfig(field=CEnumRule.EnumField.MEANING, field_val=CEnumValue.Meaning.ON, prop_val=0.5)],
    [CEnumRule.EnumConfig(field=CEnumRule.EnumField.MEANING, field_val=CEnumValue.Meaning.OFF, prop_val=0.5)],
    [CEnumRule.EnumConfig(field=CEnumRule.EnumField.MEANING, field_val=CEnumValue.Meaning.WARNING, prop_val=0.5)],
    [CEnumRule.EnumConfig(field=CEnumRule.EnumField.MEANING, field_val=CEnumValue.Meaning.ERROR, prop_val=0.5)],
    [CEnumRule.EnumConfig(field=CEnumRule.EnumField.MEANING, field_val=CEnumValue.Meaning.NONE, prop_val=0.5)],
    [
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.CODE, field_val=31, prop_val=0.5),
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.LABEL, field_val='test-label', prop_val=0.5),
    ],
    [
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.CODE, field_val=0, prop_val='#FF0000'),
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.CODE, field_val=1, prop_val='#00FF00'),
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.CODE, field_val=2, prop_val='#0000FF'),
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.CODE, field_val=3, prop_val='#000000'),
    ],
    [
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.LABEL, field_val='ON', prop_val='#FF0000'),
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.LABEL, field_val='OFF', prop_val='#00FF00'),
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.LABEL, field_val='UNKNOWN', prop_val='#0000FF'),
    ],
    [
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.MEANING, field_val=CEnumValue.Meaning.WARNING, prop_val='#FF0000'),
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.MEANING, field_val=CEnumValue.Meaning.ON, prop_val='#00FF00'),
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.MEANING, field_val=CEnumValue.Meaning.OFF, prop_val='#0000FF'),
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.MEANING, field_val=CEnumValue.Meaning.ERROR, prop_val='#000000'),
    ],
])
def test_enum_rule_validate_succeeds(prop, channel, config):
    rule = CEnumRule(name='test_name',
                     prop=prop,
                     channel=channel,
                     config=config)
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
    ('config', [], 'Rule "test_name" must have at least one enum option defined*'),
    ('config', (), 'Rule "test_name" must have at least one enum option defined*'),
    ('config', [
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.CODE, field_val=11, prop_val=0.5),
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.CODE, field_val=11, prop_val=0.75),
    ], 'Rule "test_name" has redundant configuration*'),
    ('config', [
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.LABEL, field_val='ON', prop_val=0.5),
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.LABEL, field_val='ON', prop_val=0.75),
    ], 'Rule "test_name" has redundant configuration*'),
    ('config', [
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.MEANING, field_val=CEnumValue.Meaning.ERROR, prop_val=0.5),
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.MEANING, field_val=CEnumValue.Meaning.ERROR, prop_val=0.75),
    ], 'Rule "test_name" has redundant configuration*'),
    ('config', [
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.CODE, field_val='ON', prop_val=0.5),
    ], 'Value of type "str" is not compatible with enum field "Code"*'),
    ('config', [
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.CODE, field_val=CEnumValue.Meaning.ERROR, prop_val=0.5),
    ], 'Value of type "Meaning" is not compatible with enum field "Code"*'),
    ('config', [
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.LABEL, field_val=12, prop_val=0.5),
    ], 'Value of type "int" is not compatible with enum field "Label"*'),
    ('config', [
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.LABEL, field_val=CEnumValue.Meaning.ERROR, prop_val=0.5),
    ], 'Value of type "Meaning" is not compatible with enum field "Label"*'),
    ('config', [
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.MEANING, field_val=12, prop_val=0.5),
    ], 'Value of type "int" is not compatible with enum field "Meaning"*'),
    ('config', [
        CEnumRule.EnumConfig(field=CEnumRule.EnumField.MEANING, field_val='ON', prop_val=0.5),
    ], 'Value of type "str" is not compatible with enum field "Meaning"*'),
])
def test_enum_rule_validate_fails(attr, val, err):
    rule = CEnumRule(name='test_name',
                     prop='test_prop',
                     channel='dev/prop#field',
                     config=[CEnumRule.EnumConfig(field=CEnumRule.EnumField.CODE, field_val=31, prop_val=0.5)])
    setattr(rule, attr, val)
    with pytest.raises(TypeError, match=fr'{err}'):
        rule.validate()


# TODO: CExpressionRule are disabled until CExpressionRule.from_json is implemented
@pytest.mark.parametrize('rule_cnt,rule_types,names,props,channels,payloads,json_str', [
    (1, [CNumRangeRule], ['rule1'], ['color'], ['__auto__'], [1],
     '[{"type":0,"name":"rule1","prop":"color","channel":"__auto__","ranges":[{"min":0.0,"max":0.1,"value":"#FF0000"}]}]'),
    (1, [CEnumRule], ['rule1'], ['color'], ['__auto__'], [1],
     '[{"type":2,"name":"rule1","prop":"color","channel":"__auto__","config":[{"field":0,"fv":21,"value":"#FF0000"}]}]'),
    # (1, [CExpressionRule], ['rule1'], ['color'], ['__auto__'], ["expr1"],
    #  '[{"type":1,"name":"rule1","prop":"color","channel":"__auto__","expr":"expr1"}]'),
    (1, [CNumRangeRule], ['rule2'], ['opacity'], ['dev/prop#field'], [2],
     '[{"type":0,"name":"rule2","prop":"opacity","channel":"dev/prop#field","ranges":[{"min":0.0,"max":0.1,"value":0.9}, {"min":0.1,"max":0.2,"value":0.5}]}]'),
    (1, [CNumRangeRule], ['rule2'], ['opacity'], ['dev/prop#field'], [0],
     '[{"type":0,"name":"rule2","prop":"opacity","channel":"dev/prop#field","ranges":[]}]'),
    (2, [CNumRangeRule, CNumRangeRule], ['rule1', 'rule2'], ['color', 'opacity'], ['__auto__', '__auto__'], [0, 0],
     '[{"type":0,"name":"rule1","prop":"color","channel":"__auto__","ranges":[]},{"type":0,"name":"rule2","prop":"opacity","channel":"__auto__","ranges":[]}]'),
    (2, [CEnumRule, CEnumRule], ['rule1', 'rule2'], ['color', 'opacity'], ['__auto__', '__auto__'], [0, 0],
     '[{"type":2,"name":"rule1","prop":"color","channel":"__auto__","config":[]},{"type":2,"name":"rule2","prop":"opacity","channel":"__auto__","config":[]}]'),
    (2, [CNumRangeRule, CEnumRule], ['rule1', 'rule2'], ['color', 'opacity'], ['__auto__', '__auto__'], [0, 0],
     '[{"type":0,"name":"rule1","prop":"color","channel":"__auto__","ranges":[]},{"type":2,"name":"rule2","prop":"opacity","channel":"__auto__","config":[]}]'),
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
        elif rule_type == CEnumRule:
            assert len(cast(CEnumRule, rule).config) == payload
        elif rule_type == CExpressionRule:
            assert cast(CExpressionRule, rule).expr == payload


@pytest.mark.parametrize('err,err_type,json_str', [
    (r'type', KeyError, '[{"name":"rule2","prop":"opacity","channel":"dev/prop#field","ranges":null}]'),
    (r'Can\\\'t parse range JSON: "name" is not a string', CJSONDeserializeError, '[{"type":0,"prop":"opacity","channel":"dev/prop#field","ranges":null}]'),
    (r'Can\\\'t parse range JSON: "prop" is not a string', CJSONDeserializeError, '[{"name":"rule2","type":0,"channel":"dev/prop#field","ranges":null}]'),
    (r'Can\\\'t parse range JSON: "channel" is not a string', CJSONDeserializeError, '[{"name":"rule2","prop":"opacity","type":0,"ranges":null}]'),
    (r'Can\\\'t parse range JSON: "ranges" is not a list', CJSONDeserializeError, '[{"name":"rule2","prop":"opacity","type":0,"channel":"__auto__"}]'),
    (r'Can\\\'t parse range JSON: "ranges" is not a list, "NoneType" given*', CJSONDeserializeError, '[{"type":0,"name":"rule2","prop":"opacity","channel":"dev/prop#field","ranges":null}]'),
    (r'must have integer type, given str', CJSONDeserializeError, '[{"type":"test","name":"rule1","prop":"opacity","channel":"dev/prop#field","ranges":[]}]'),
    (r'Can\\\'t parse enum JSON: "field" is not int, "NoneType" given*', CJSONDeserializeError, '[{"type":2,"name":"rule1","prop":"opacity","channel":"dev/prop#field","config":[{}]}]'),
    (r'Rules does not appear to be a list', CJSONDeserializeError, '{"type":0,"name":"rule2","prop":"opacity","channel":"dev/prop#field","ranges":[]}'),
    (r'Unknown rule type 3 for JSON', CJSONDeserializeError, '[{"type":3,"name":"rule2","prop":"opacity","channel":"dev/prop#field","ranges":[]}]'),
    (r'', NotImplementedError, '[{"type":1,"name":"rule2","prop":"opacity","channel":"dev/prop#field","expr":""}]'),  # TODO: Remove when expression rules are implemented
])
def test_unpack_rules_fails(err, err_type, json_str):
    with pytest.raises(err_type, match=err):
        unpack_rules(json_str)


@pytest.mark.parametrize('designer_online', [
    True,
    False,
])
@mock.patch('comrad.rules.plugin_for_address')
@mock.patch('pydm.data_plugins.plugin_for_address')  # Need both here, as both participate on comrad and pydm level
@mock.patch('comrad.rules.is_qt_designer', return_value=True)
@mock.patch('comrad.rules.config')
def test_rules_engine_does_not_register_in_designer(config, _, __, ___, qtbot: QtBot, designer_online):
    config.DESIGNER_ONLINE = designer_online
    engine = CRulesEngine()
    widget = QWidget()
    qtbot.addWidget(widget)
    rule = CNumRangeRule(name='test_name',
                         prop='test_prop',
                         channel='dev/prop#field',
                         ranges=[CNumRangeRule.Range(min_val=0.0, max_val=0.0, prop_val=0.5)])

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
@mock.patch('comrad.rules.plugin_for_address')
@mock.patch('pydm.data_plugins.plugin_for_address')  # Need both here, as both participate on comrad and pydm level
@mock.patch('comrad.rules.is_qt_designer', return_value=False)
def test_rules_engine_does_not_register_faulty_rules(_, __, ___, qtbot: QtBot, faulty):
    engine = CRulesEngine()
    widget = QWidget()
    qtbot.addWidget(widget)
    rule = CNumRangeRule(name='test_name',
                         prop='test_prop',
                         channel='dev/prop#field',
                         ranges=None if faulty else [CNumRangeRule.Range(min_val=0.0, max_val=0.0, prop_val=0.5)])

    engine.register(widget=widget, rules=[rule])

    try:
        job_summary = next(iter(engine.widget_map.values()))
    except StopIteration:
        job_summary = []
    if faulty:
        assert len(job_summary) == 0
    else:
        assert len(job_summary) == 1


@mock.patch('comrad.rules.plugin_for_address')
@mock.patch('pydm.data_plugins.plugin_for_address')  # Need both here, as both participate on comrad and pydm level
@mock.patch('comrad.rules.is_qt_designer', return_value=False)
def test_rules_engine_unregisters_old_rules(_, __, ___, qtbot: QtBot):
    engine = CRulesEngine()
    widget = QWidget()
    qtbot.addWidget(widget)

    rule = CNumRangeRule(name='rule1',
                         prop='test_prop',
                         channel='dev/prop#field',
                         ranges=[CNumRangeRule.Range(min_val=0.0, max_val=0.0, prop_val=0.5)])
    engine.register(widget=widget, rules=[rule])
    assert len(engine.widget_map) == 1
    job_summary = next(iter(engine.widget_map.values()))
    assert len(job_summary) == 1
    assert cast(CNumRangeRule, job_summary[0]['rule']).name == 'rule1'

    new_rule = CNumRangeRule(name='rule2',
                             prop='test_prop',
                             channel='dev/prop#field',
                             ranges=[CNumRangeRule.Range(min_val=0.0, max_val=0.0, prop_val=0.5)])
    engine.register(widget=widget, rules=[new_rule])
    assert len(engine.widget_map) == 1
    job_summary = next(iter(engine.widget_map.values()))
    assert len(job_summary) == 1
    assert cast(CNumRangeRule, job_summary[0]['rule']).name == 'rule2'


@pytest.mark.parametrize('default_channel', [
    'default_dev/prop#field',
    None,
])
@mock.patch('comrad.rules.plugin_for_address')
@mock.patch('pydm.data_plugins.plugin_for_address')  # Need both here, as both participate on comrad and pydm level
@mock.patch('comrad.rules.is_qt_designer', return_value=False)
def test_rules_engine_finds_default_channel(_, __, ___, qtbot: QtBot, default_channel):
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


@mock.patch('comrad.rules.plugin_for_address')
@mock.patch('pydm.data_plugins.plugin_for_address')  # Need both here, as both participate on comrad and pydm level
@mock.patch('comrad.rules.is_qt_designer', return_value=False)
def test_rules_engine_uses_custom_channels(_, __, ___, qtbot: QtBot):
    engine = CRulesEngine()
    widget = QWidget()
    qtbot.addWidget(widget)

    rule = CNumRangeRule(name='test_name',
                         prop='test_prop',
                         channel='dev/prop#field',
                         ranges=[CNumRangeRule.Range(min_val=0.0, max_val=0.0, prop_val=0.5)])
    engine.register(widget=widget, rules=[rule])
    assert len(engine.widget_map) == 1
    job_summary = next(iter(engine.widget_map.values()))
    assert len(job_summary) == 1
    assert len(job_summary[0]['channels']) == 1
    from pydm.widgets.channel import PyDMChannel
    channel = cast(PyDMChannel, job_summary[0]['channels'][0])
    assert channel.address == 'dev/prop#field'


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
                         channel='dev/prop#field',
                         ranges=[CNumRangeRule.Range(min_val=range_min, max_val=range_max, prop_val='HIT')])
    import weakref
    widget_ref = weakref.ref(widget, engine.widget_destroyed)
    job_unit = {
        'calculate': True,
        'rule': rule,
        'values': [CChannelData(value=incoming_val, meta_info={})],
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


@pytest.mark.parametrize('incoming_val,field,field_val,should_calc', [
    (CEnumValue(code=12, label='test', meaning=CEnumValue.Meaning.NONE, settable=True), CEnumRule.EnumField.CODE, 12, True),
    (CEnumValue(code=4, label='test', meaning=CEnumValue.Meaning.NONE, settable=True), CEnumRule.EnumField.CODE, 12, False),
    (CEnumValue(code=12, label='ON', meaning=CEnumValue.Meaning.NONE, settable=True), CEnumRule.EnumField.LABEL, 'ON', True),
    (CEnumValue(code=12, label='test', meaning=CEnumValue.Meaning.NONE, settable=True), CEnumRule.EnumField.LABEL, 'ON', False),
    (CEnumValue(code=12, label='test', meaning=CEnumValue.Meaning.ERROR, settable=True), CEnumRule.EnumField.MEANING, CEnumValue.Meaning.ERROR, True),
    (CEnumValue(code=12, label='test', meaning=CEnumValue.Meaning.WARNING, settable=True), CEnumRule.EnumField.MEANING, CEnumValue.Meaning.ERROR, False),
    ('rubbish', CEnumRule.EnumField.CODE, 12, False),
])
def test_rules_engine_calculates_enum_value(qtbot: QtBot, incoming_val, field, field_val, should_calc):
    engine = CRulesEngine()
    callback = mock.MagicMock()
    engine.rule_signal.connect(callback, Qt.DirectConnection)

    class CustomWidget(QWidget):
        RULE_PROPERTIES = {
            'test_prop': (None, str),
        }

    widget = CustomWidget()
    qtbot.addWidget(widget)

    rule = CEnumRule(name='test_name',
                     prop='test_prop',
                     channel='dev/prop#field',
                     config=[CEnumRule.EnumConfig(field=field, field_val=field_val, prop_val='HIT')])
    import weakref
    widget_ref = weakref.ref(widget, engine.widget_destroyed)
    job_unit = {
        'calculate': True,
        'rule': rule,
        'values': [CChannelData(value=incoming_val, meta_info={})],
    }

    engine.calculate_expression(widget_ref=widget_ref, rule=job_unit)
    callback.assert_called_with({
        'widget': widget_ref,
        'name': 'test_name',
        'property': 'test_prop',
        'value': 'HIT' if should_calc else None,
    })
