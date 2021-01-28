import pytest
import numpy as np
from pytestqt.qtbot import QtBot
from unittest import mock
from comrad import CPropertyEdit, CPropertyEditField
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
