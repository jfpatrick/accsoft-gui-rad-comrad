import pytest
import numpy as np
from pytestqt.qtbot import QtBot
from unittest import mock
from comrad import CPropertyEdit, CPropertyEditField
from comrad.data.channel import CChannelData


def test_cpropertyedit_get_btn_emits_signal(qtbot: QtBot):
    widget = CPropertyEdit()
    widget.setObjectName('test-widget')
    qtbot.addWidget(widget)
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
    qtbot.addWidget(widget)
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
    qtbot.addWidget(widget)
    with mock.patch.object(widget, 'setValue') as setValue:
        widget.channelValueChanged(CChannelData(value=val, meta_info={}))
        if should_set_value:
            setValue.assert_called_with(val)
        else:
            setValue.assert_not_called()


@pytest.mark.parametrize('buttons,expected_connect_slot', [
    (CPropertyEdit.Buttons.GET, False),
    (CPropertyEdit.Buttons.SET, True),
    (CPropertyEdit.Buttons.GET & CPropertyEdit.Buttons.SET, True),
    (CPropertyEdit.Buttons.GET | CPropertyEdit.Buttons.SET, False),
])
def test_cpropertyedit_buttons_affects_value_slot(qtbot: QtBot, buttons, expected_connect_slot):
    widget = CPropertyEdit()
    qtbot.addWidget(widget)
    assert widget.connect_value_slot is True
    widget.buttons = buttons
    assert widget.connect_value_slot == expected_connect_slot
    assert widget.buttons == buttons
