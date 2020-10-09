import pytest
import logging
import numpy as np
from typing import List, cast, Optional, Type
from logging import LogRecord
from pytestqt.qtbot import QtBot
from _pytest.logging import LogCaptureFixture
from comrad import CPushButton, CChannelData


@pytest.mark.parametrize('prop_name,return_value,set_value,error_msg', [
    ('passwordProtected', False, True, 'passwordProtected property is disabled in ComRAD (found in unidentified CPushButton)'),
    ('passwordProtected', False, False, 'passwordProtected property is disabled in ComRAD (found in unidentified CPushButton)'),
    ('password', '', 'test-password', 'password property is disabled in ComRAD (found in unidentified CPushButton)'),
    ('protectedPassword', '', 'test-protected-password', 'protectedPassword property is disabled in ComRAD (found in unidentified CPushButton)'),
])
def test_cpushbutton_pydm_props_disabled(qtbot: QtBot, caplog: LogCaptureFixture, prop_name, return_value, set_value, error_msg):
    widget = CPushButton()
    qtbot.addWidget(widget)
    assert getattr(widget, prop_name) == return_value

    setattr(widget, prop_name, set_value)

    warning_records = [r.msg for r in cast(List[LogRecord], caplog.records) if
                       r.levelno == logging.WARNING and r.name == 'comrad.widgets.buttons']
    assert warning_records == [error_msg]

    # Check that value has not changed after the set
    assert getattr(widget, prop_name) == return_value


# CPushButton tests are copied from PyDM (with changes to reflect CPushButton behavior over PyDMPushButton),
# because current functionality is also mostly copy-pasted to do some minor adjustments

@pytest.mark.parametrize('initial_value,press_value,is_value_relative,', [
    (0, 1, False),
    (123, 345, True),
    (123, '345', True),
    (123.345, 345.678, True),
    (123.345, '345.678', True),
    ('123', 345, True),
    ('123', 345.678, True),
    ('123.345', 345.678, True),
    ('123.345', '345.678', True),
    ('123', 345, True),
    ('123', 345, True),
    ('123', 345, False),
    ('123', 345, False),
    ('123.345', 345.678, False),
    ('123.345', '345.678', False),
    ('123', 345, True),
    ('123', 345, False),
    ('abc', 'def', False),
    ('abc', None, False),
    (None, 'def', False),
    (None, None, False),
])
def test_cpushbutton_send_value(qtbot: QtBot, initial_value, press_value, is_value_relative):
    widget = CPushButton()
    qtbot.addWidget(widget)

    widget.relativeChange = is_value_relative
    widget.pressValue = press_value

    channel_type: Optional[Type]
    if initial_value:
        # If the user sets the initial value, emit the channel change signal. Otherwise, skip this signal emit part
        # and continue the test to see if the widget can handle a None initial value
        channel_type = type(initial_value)
        widget.channelValueChanged(CChannelData(value=initial_value, meta_info={}))
        assert widget.value == initial_value
    else:
        channel_type = None
        assert widget.value is None
    if channel_type:
        if not widget.pressValue:
            expected_value = None
        elif not is_value_relative or channel_type == str:
            expected_value = channel_type(widget.pressValue)
        else:
            expected_value = widget.value + channel_type(widget.pressValue)

        with qtbot.wait_signal(widget.send_value_signal[channel_type]) as blocker:
            send_value = widget.sendValue()
        assert send_value == expected_value
        assert blocker.args == [expected_value]
    else:
        # send_value() should return None if either the initial value or the pressValue is empty
        assert widget.sendValue() is None


@pytest.mark.parametrize('current_channel_value,updated_value', [
    # Current channel value type is array, getting a new int value
    (np.array([123, 456]), 10),
    # Test if the current channel value type is int, and the widget is getting new int, float, or string value
    (10, 20),
    (10, 20.20),
    (10, '100'),
    # Test if the current channel value type is float, and the widget getting new int, float, or string value
    (10.10, 20.20),
    (10.10, 42),
    (10.10, '100.5'),
    # Test if the current channel value type is string, and the widget is getting new int, float, or string value
    ('Old str value', 'New str value'),
    ('Old str value', 42),
    ('Old str value', 10.10),
])
def test_cpushbutton_update_press_value(qtbot, current_channel_value, updated_value):
    widget = CPushButton()
    qtbot.addWidget(widget)
    assert widget.pressValue == 'None'
    assert widget.value is None

    # First, set the current channel type
    widget.channelValueChanged(CChannelData(value=current_channel_value, meta_info={}))
    assert widget.pressValue == 'None'
    if isinstance(current_channel_value, np.ndarray):
        assert (current_channel_value == widget.value).all()
    else:
        assert widget.value == current_channel_value

    # Verify the new value can be converted/cast as long as the casting can be done
    widget.updatePressValue(updated_value)

    # Verify the new value is assigned to be the new pressValue as a str
    if isinstance(current_channel_value, np.ndarray):
        assert (current_channel_value == widget.value).all()
    else:
        assert widget.value == current_channel_value
    assert widget.pressValue == str(type(current_channel_value)(updated_value))


@pytest.mark.parametrize('current_channel_value,updated_value,expected_log_error', [
    (np.array([123.123, 456.456]), 10.10, "'10.1' is not a valid pressValue for '<channel>'."),
    (np.array(['abc', 'string in an array']), 'New str value', "'New str value' is not a valid pressValue for '<channel>'."),
    (10, 'New str value', "'New str value' is not a valid pressValue for '<channel>'."),
    (10.10, 'New str value', "'New str value' is not a valid pressValue for '<channel>'."),
])
def test_cpushbutton_update_press_value_incompatible_update_value(qtbot: QtBot, caplog: LogCaptureFixture,
                                                                  current_channel_value, updated_value,
                                                                  expected_log_error):
    widget = CPushButton()
    qtbot.addWidget(widget)
    assert widget.pressValue == 'None'
    assert widget.value is None

    # First, set the current channel type
    widget.channelValueChanged(CChannelData(value=current_channel_value, meta_info={}))
    assert widget.pressValue == 'None'
    if isinstance(current_channel_value, np.ndarray):
        assert (current_channel_value == widget.value).all()
    else:
        assert widget.value == current_channel_value

    widget.channel = '<channel>'  # To make a fix value for warning message
    widget.updatePressValue(updated_value)

    # Make sure logging capture the error, and have the correct error message
    error_records = [r.msg for r in cast(List[LogRecord], caplog.records) if
                     r.levelno == logging.ERROR and r.name.startswith('pydm')]
    assert error_records == [expected_log_error]
