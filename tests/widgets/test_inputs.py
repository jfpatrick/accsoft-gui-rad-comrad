import pytest
import numpy as np
from pytestqt.qtbot import QtBot
from unittest import mock
from comrad import CPropertyEdit, CPropertyEditField, CPropertyEditWidgetDelegate, CEnumValue
from comrad.data.channel import CChannelData


def test_cpropertyedit_get_btn_emits_signal(qtbot: QtBot):
    widget = CPropertyEdit()
    widget.setObjectName('test-widget')
    qtbot.add_widget(widget)
    with qtbot.wait_signal(widget.request_signal) as blocker:
        widget._get_btn.click()
    assert blocker.args == [widget.objectName()]


def test_cpropertyedit_set_btn_emits_signal(qtbot: QtBot):
    widget = CPropertyEdit()
    widget.fields = [
        CPropertyEditField(field='str', type=CPropertyEdit.ValueType.STRING, editable=False),
        CPropertyEditField(field='int', type=CPropertyEdit.ValueType.INTEGER, editable=False),
        CPropertyEditField(field='bool', type=CPropertyEdit.ValueType.BOOLEAN, editable=False),
        CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=False),
    ]
    widget.sendOnlyUpdatedValues = False
    qtbot.add_widget(widget)
    val = {
        'str': 'val1',
        'int': 10,
        'bool': True,
        'float': 0.5,
    }
    widget.setValue(val)
    with qtbot.wait_signal(widget.send_value_signal) as blocker:
        widget._set_btn.click()
    assert blocker.args == [val]


@pytest.mark.parametrize('val,should_set_value', [
    ({'str': 'val1', 'int': 10}, True),
    ('value', False),
    (10, False),
    (10.0, False),
    (True, False),
    ([], False),
    ([(10, 'val')], False),
    (np.array([0, 1]), False),
])
def test_cpropertyedit_value_changed(qtbot: QtBot, val, should_set_value):
    widget = CPropertyEdit()
    qtbot.add_widget(widget)
    with mock.patch.object(widget, 'setValue') as setValue:
        widget.channelValueChanged(CChannelData(value=val, meta_info={}))
        if should_set_value:
            setValue.assert_called_with(val)
        else:
            setValue.assert_not_called()


@pytest.mark.parametrize('incoming_header,expected_config', [
    (
        {},
        {
            'str': None,
            'int': None,
            'bool': None,
            'float': None,
            'enum': {
                'options': [
                    ('none', 0),
                    ('one', 4),
                    ('two', 5),
                ],
            },
        },
    ),
    (
        {'min': {'int': -2}},
        {
            'str': None,
            'int': {
                'min': -2,
            },
            'bool': None,
            'float': None,
            'enum': {
                'options': [
                    ('none', 0),
                    ('one', 4),
                    ('two', 5),
                ],
            },
        },
    ),
    (
        {'max': {'int': 5}},
        {
            'str': None,
            'int': {
                'max': 5,
            },
            'bool': None,
            'float': None,
            'enum': {
                'options': [
                    ('none', 0),
                    ('one', 4),
                    ('two', 5),
                ],
            },
        },
    ),
    (
        {'units': {'int': 'TST'}},
        {
            'str': None,
            'int': {
                'units': 'TST',
            },
            'bool': None,
            'float': None,
            'enum': {
                'options': [
                    ('none', 0),
                    ('one', 4),
                    ('two', 5),
                ],
            },
        },
    ),
    (
        {'min': {'int': 1}, 'max': {'int': 5}},
        {
            'str': None,
            'int': {
                'min': 1,
                'max': 5,
            },
            'bool': None,
            'float': None,
            'enum': {
                'options': [
                    ('none', 0),
                    ('one', 4),
                    ('two', 5),
                ],
            },
        },
    ),
    (
        {'min': {'int': 1, 'float': 0.5}},
        {
            'str': None,
            'int': {
                'min': 1,
            },
            'bool': None,
            'float': {
                'min': 0.5,
            },
            'enum': {
                'options': [
                    ('none', 0),
                    ('one', 4),
                    ('two', 5),
                ],
            },
        },
    ),
    (
        {'min': {'int': 1, 'float': 0.5}, 'units': {'int': 'TST'}},
        {
            'str': None,
            'int': {
                'min': 1,
                'units': 'TST',
            },
            'bool': None,
            'float': {
                'min': 0.5,
            },
            'enum': {
                'options': [
                    ('none', 0),
                    ('one', 4),
                    ('two', 5),
                ],
            },
        },
    ),
])
@pytest.mark.parametrize('val', [
    {},
    {'str': 'val1', 'int': 10},
    {'float': -1.5, 'int': 10},
    {'float': -1.5, 'int': 10, 'str': 'val1', 'bool': True},
])
@pytest.mark.parametrize('disregarded_header', [
    {},
    {'notImportant': 'notImportant'},
])
def test_cpropertyedit_field_traits_are_updated_in_delegate(qtbot: QtBot, val, incoming_header,
                                                            expected_config, disregarded_header):
    full_header = {**disregarded_header, **incoming_header}
    map_widget_dict = lambda wmap: {k: v[1].user_data for k, v in wmap.items()}
    widget = CPropertyEdit()
    qtbot.add_widget(widget)
    widget.fields = [
        CPropertyEditField(field='str', type=CPropertyEdit.ValueType.STRING, editable=False),
        CPropertyEditField(field='int', type=CPropertyEdit.ValueType.INTEGER, editable=False),
        CPropertyEditField(field='bool', type=CPropertyEdit.ValueType.BOOLEAN, editable=False),
        CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=False),
        CPropertyEditField(field='enum', type=CPropertyEdit.ValueType.ENUM, editable=False, user_data=CPropertyEdit.ValueType.enum_user_data([('none', 0), ('one', 4), ('two', 5)])),
    ]
    assert map_widget_dict(widget.widget_delegate.widget_map) == {
        'str': None,
        'int': None,
        'bool': None,
        'float': None,
        'enum': {
            'options': [
                ('none', 0),
                ('one', 4),
                ('two', 5),
            ],
        },
    }
    widget.channelValueChanged(CChannelData(value=val, meta_info=full_header))
    assert map_widget_dict(widget.widget_delegate.widget_map) == expected_config


@pytest.mark.parametrize('buttons,expected_connect_slot', [
    (CPropertyEdit.Buttons.GET, False),
    (CPropertyEdit.Buttons.SET, True),
    (CPropertyEdit.Buttons.GET & CPropertyEdit.Buttons.SET, True),
    (CPropertyEdit.Buttons.GET | CPropertyEdit.Buttons.SET, False),
])
def test_cpropertyedit_buttons_affects_value_slot(qtbot: QtBot, buttons, expected_connect_slot):
    widget = CPropertyEdit()
    qtbot.add_widget(widget)
    assert widget.connect_value_slot is True
    widget.buttons = buttons
    assert widget.connect_value_slot == expected_connect_slot
    assert widget.buttons == buttons


@pytest.mark.parametrize('initial_config,updated_user_data,expected_initial_min,expected_initial_max,expected_initial_units,expected_min,expected_max,expected_units', [
    (CPropertyEditField(field='int', type=CPropertyEdit.ValueType.INTEGER, editable=True), None, -1073741823, 1073741823, '', -1073741823, 1073741823, ''),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=True), None, -1.7976931348623157e+308, 1.7976931348623157e+308, '', -1.7976931348623157e+308, 1.7976931348623157e+308, ''),
    (CPropertyEditField(field='int', type=CPropertyEdit.ValueType.INTEGER, editable=True), {'min': -2}, -1073741823, 1073741823, '', -2, 1073741823, ''),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=True), {'min': -2}, -1.7976931348623157e+308, 1.7976931348623157e+308, '', -2.0, 1.7976931348623157e+308, ''),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=True), {'min': -0.2}, -1.7976931348623157e+308, 1.7976931348623157e+308, '', -0.2, 1.7976931348623157e+308, ''),
    (CPropertyEditField(field='int', type=CPropertyEdit.ValueType.INTEGER, editable=True), {'max': 5}, -1073741823, 1073741823, '', -1073741823, 5, ''),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=True), {'max': 5}, -1.7976931348623157e+308, 1.7976931348623157e+308, '', -1.7976931348623157e+308, 5.0, ''),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=True), {'max': 5.5}, -1.7976931348623157e+308, 1.7976931348623157e+308, '', -1.7976931348623157e+308, 5.5, ''),
    (CPropertyEditField(field='int', type=CPropertyEdit.ValueType.INTEGER, editable=True), {'units': 'TST'}, -1073741823, 1073741823, '', -1073741823, 1073741823, ' TST'),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=True), {'units': 'TST'}, -1.7976931348623157e+308, 1.7976931348623157e+308, '', -1.7976931348623157e+308, 1.7976931348623157e+308, ' TST'),
    (CPropertyEditField(field='int', type=CPropertyEdit.ValueType.INTEGER, editable=True), {'units': 'TST', 'min': -2}, -1073741823, 1073741823, '', -2, 1073741823, ' TST'),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=True), {'units': 'TST', 'min': -2}, -1.7976931348623157e+308, 1.7976931348623157e+308, '', -2.0, 1.7976931348623157e+308, ' TST'),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=True), {'units': 'TST', 'min': -0.2}, -1.7976931348623157e+308, 1.7976931348623157e+308, '', -0.2, 1.7976931348623157e+308, ' TST'),
    (CPropertyEditField(field='int', type=CPropertyEdit.ValueType.INTEGER, editable=True), {'units': 'TST', 'max': 5}, -1073741823, 1073741823, '', -1073741823, 5, ' TST'),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=True), {'units': 'TST', 'max': 5}, -1.7976931348623157e+308, 1.7976931348623157e+308, '', -1.7976931348623157e+308, 5.0, ' TST'),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=True), {'units': 'TST', 'max': 5.5}, -1.7976931348623157e+308, 1.7976931348623157e+308, '', -1.7976931348623157e+308, 5.5, ' TST'),
    (CPropertyEditField(field='int', type=CPropertyEdit.ValueType.INTEGER, editable=True), {'min': -2, 'max': 5}, -1073741823, 1073741823, '', -2, 5, ''),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=True), {'min': -2, 'max': 5}, -1.7976931348623157e+308, 1.7976931348623157e+308, '', -2.0, 5.0, ''),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=True), {'min': -0.2, 'max': 5}, -1.7976931348623157e+308, 1.7976931348623157e+308, '', -0.2, 5.0, ''),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=True), {'min': -2, 'max': 5.5}, -1.7976931348623157e+308, 1.7976931348623157e+308, '', -2.0, 5.5, ''),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=True), {'min': -0.2, 'max': 5.5}, -1.7976931348623157e+308, 1.7976931348623157e+308, '', -0.2, 5.5, ''),
    (CPropertyEditField(field='int', type=CPropertyEdit.ValueType.INTEGER, editable=True), {'units': 'TST', 'min': -2, 'max': 5}, -1073741823, 1073741823, '', -2, 5, ' TST'),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=True), {'units': 'TST', 'min': -2, 'max': 5}, -1.7976931348623157e+308, 1.7976931348623157e+308, '', -2.0, 5.0, ' TST'),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=True), {'units': 'TST', 'min': -2, 'max': 5.5}, -1.7976931348623157e+308, 1.7976931348623157e+308, '', -2.0, 5.5, ' TST'),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=True), {'units': 'TST', 'min': -0.2, 'max': 5}, -1.7976931348623157e+308, 1.7976931348623157e+308, '', -0.2, 5.0, ' TST'),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=True), {'units': 'TST', 'min': -0.2, 'max': 5.5}, -1.7976931348623157e+308, 1.7976931348623157e+308, '', -0.2, 5.5, ' TST'),
])
def test_cpropertyeditdelegate_field_traits_affect_spinbox_configuration(qtbot: QtBot, expected_initial_min, expected_initial_max,
                                                                         expected_initial_units, initial_config, updated_user_data,
                                                                         expected_min, expected_max, expected_units):
    delegate = CPropertyEditWidgetDelegate()
    widget = delegate.widget_for_item(parent=None, config=initial_config)
    qtbot.add_widget(widget)
    assert widget.minimum() == expected_initial_min
    assert widget.maximum() == expected_initial_max
    assert widget.suffix() == expected_initial_units
    delegate.widget_map[initial_config.field][1].user_data = updated_user_data
    delegate.value_updated({initial_config.field: 1})
    assert widget.minimum() == expected_min
    assert widget.maximum() == expected_max
    assert widget.suffix() == expected_units


@pytest.mark.parametrize('initial_config,updated_user_data,expected_initial_text,new_val,expected_text,expect_warning', [
    (CPropertyEditField(field='int', type=CPropertyEdit.ValueType.INTEGER, editable=False), None, '', 4, '4', None),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=False), None, '', 5.6, '5.6', None),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.STRING, editable=False), None, '', 'test', 'test', None),
    (CPropertyEditField(field='enum',
                        type=CPropertyEdit.ValueType.ENUM,
                        editable=False,
                        user_data=CPropertyEdit.ValueType.enum_user_data([('none', 0), ('one', 4), ('two', 5)])),
     None, '', CEnumValue(code=4, label='one', settable=True, meaning=CEnumValue.Meaning.NONE), '', "Can't set data 4 to QLabel."),
    (CPropertyEditField(field='int', type=CPropertyEdit.ValueType.INTEGER, editable=False), {'units': 'TST'}, '', 4, '4 TST', None),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=False), {'units': 'TST'}, '', 5.6, '5.6 TST', None),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.STRING, editable=False), {'units': 'TST'}, '', 'test', 'test', None),
    (CPropertyEditField(field='enum',
                        type=CPropertyEdit.ValueType.ENUM,
                        editable=False,
                        user_data=CPropertyEdit.ValueType.enum_user_data([('none', 0), ('one', 4), ('two', 5)])),
     {'units': 'TST'}, '', CEnumValue(code=4, label='one', settable=True, meaning=CEnumValue.Meaning.NONE), '', "Can't set data 4 to QLabel."),
    (CPropertyEditField(field='int', type=CPropertyEdit.ValueType.INTEGER, editable=False), {'max': 5}, '', 4, '4', None),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=False), {'max': 5.5}, '', 5.6, '5.6', None),
    (CPropertyEditField(field='int', type=CPropertyEdit.ValueType.INTEGER, editable=False), {'min': -2}, '', 4, '4', None),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=False), {'min': -0.2}, '', 5.6, '5.6', None),
    (CPropertyEditField(field='int', type=CPropertyEdit.ValueType.INTEGER, editable=False), {'units': 'TST', 'min': -2}, '', 4, '4 TST', None),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=False), {'units': 'TST', 'min': -2}, '', 5.6, '5.6 TST', None),
    (CPropertyEditField(field='int', type=CPropertyEdit.ValueType.INTEGER, editable=False), {'units': 'TST', 'max': 5}, '', 4, '4 TST', None),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=False), {'units': 'TST', 'max': 5.5}, '', 5.6, '5.6 TST', None),
    (CPropertyEditField(field='int', type=CPropertyEdit.ValueType.INTEGER, editable=False), {'min': -2, 'max': 5}, '', 4, '4', None),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=False), {'min': -0.2, 'max': 5.5}, '', 5.6, '5.6', None),
    (CPropertyEditField(field='int', type=CPropertyEdit.ValueType.INTEGER, editable=True), {'units': 'TST', 'min': -2, 'max': 5}, '', 4, '4 TST', None),
    (CPropertyEditField(field='float', type=CPropertyEdit.ValueType.REAL, editable=False), {'units': 'TST', 'min': -2, 'max': 5.5}, '', 5.6, '5.6 TST', None),
])
def test_cpropertyeditdelegate_field_traits_affect_label_configuration(qtbot: QtBot, expected_initial_text, updated_user_data,
                                                                       expected_text, initial_config, new_val,
                                                                       expect_warning, recwarn):
    delegate = CPropertyEditWidgetDelegate()
    widget = delegate.widget_for_item(parent=None, config=initial_config)
    qtbot.add_widget(widget)
    assert widget.text() == expected_initial_text
    delegate.widget_map[initial_config.field][1].user_data = updated_user_data
    input = {initial_config.field: new_val}
    if expect_warning:
        with pytest.warns(UserWarning, match=expect_warning):
            delegate.value_updated(input)
    else:
        delegate.value_updated(input)
        assert recwarn.list == [], f"Got unexpected warning {recwarn.pop()}"
    assert widget.text() == expected_text
