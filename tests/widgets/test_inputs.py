import pytest
import numpy as np
from pytestqt.qtbot import QtBot
from unittest import mock
from comrad import CPropertyEdit
from PyQt5.QtTest import QSignalSpy  # TODO: qtpy does not seem to expose QSignalSpy: https://github.com/spyder-ide/qtpy/issues/197


def test_cpropertyedit_get_btn_emits_signal(qtbot: QtBot):
    widget = CPropertyEdit()
    widget.setObjectName('test-widget')
    qtbot.addWidget(widget)
    spy = QSignalSpy(widget.request_signal)
    assert len(spy) == 0
    widget.valueRequested.emit()
    assert len(spy) == 1
    assert len(spy[0]) == 1
    assert spy[0][0] == widget.objectName()


def test_cpropertyedit_set_btn_emits_signal(qtbot: QtBot):
    widget = CPropertyEdit()
    qtbot.addWidget(widget)
    spy = QSignalSpy(widget.send_value_signal)
    val = {
        'str': 'val1',
        'int': 10,
        'bool': True,
        'float': 0.5,
    }
    widget.valueUpdated.emit(val)
    send_value_spy = spy[0]
    received_val = send_value_spy[0]
    assert received_val == val


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
    with mock.patch.object(widget, 'setValue') as mocked_set_value:

        widget.channelValueChanged(val)
        if should_set_value:
            mocked_set_value.assert_called_with(val)
        else:
            mocked_set_value.assert_not_called()


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
