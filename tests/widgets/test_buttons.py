import pytest
import logging
import numpy as np
from typing import Optional, Type
from pytestqt.qtbot import QtBot
from qtpy.QtCore import Qt
from comrad import CPushButton, CChannelData


@pytest.mark.parametrize('prop_name,return_value,set_value,error_msg', [
    ('passwordProtected', False, True, 'passwordProtected property is disabled in ComRAD (found in unidentified CPushButton)'),
    ('passwordProtected', False, False, 'passwordProtected property is disabled in ComRAD (found in unidentified CPushButton)'),
    ('password', '', 'test-password', 'password property is disabled in ComRAD (found in unidentified CPushButton)'),
    ('protectedPassword', '', 'test-protected-password', 'protectedPassword property is disabled in ComRAD (found in unidentified CPushButton)'),
])
def test_cpushbutton_pydm_props_disabled(qtbot: QtBot, log_capture, prop_name, return_value, set_value, error_msg):
    widget = CPushButton()
    qtbot.add_widget(widget)
    assert getattr(widget, prop_name) == return_value

    setattr(widget, prop_name, set_value)

    warning_records = log_capture(logging.WARNING, 'comrad.widgets.buttons')
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
    (True, 'False', False),
    (True, 'false', False),
    (True, 'FALSE', False),
    (True, '0', False),
    (False, 'True', False),
    (False, '1', False),
    (False, 'true', False),
    (False, 'TRUE', False),
    (False, 'Anything', False),
    (False, 'True', True),
    (None, 'def', False),
    (None, None, False),
])
def test_cpushbutton_send_value(qtbot: QtBot, initial_value, press_value, is_value_relative):
    widget = CPushButton()
    qtbot.add_widget(widget)

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
            expected_value = widget._convert(widget.pressValue)
        else:
            expected_value = widget.value + widget._convert(widget.pressValue)

        with qtbot.wait_signal(widget.send_value_signal[channel_type]) as blocker:
            send_value = widget.sendValue()
        assert send_value == expected_value
        assert blocker.args == [expected_value]
    else:
        # send_value() should return None if either the initial value or the pressValue is empty
        assert widget.sendValue() is None


@pytest.mark.parametrize('send_on_release,initial_value,press_value,release_value,expected_press_value,expected_release_value', [
    (False, 0, 1, -2, 1, None),
    (False, 123, 345, 456, 345, None),
    (False, 123, '345', '456', 345, None),
    (False, 123.345, 345.678, 456.566, 345.678, None),
    (False, 123.345, '345.678', '456.566', 345.678, None),
    (False, '123', 345, 456, '345', None),
    (False, '123', 345.678, 456.566, '345.678', None),
    (False, '123.345', 345.678, 456.566, '345.678', None),
    (False, '123.345', '345.678', '456.566', '345.678', None),
    (False, '123', 345, 456, '345', None),
    (False, '123.345', 345.678, 456.566, '345.678', None),
    (False, '123.345', '345.678', '456.566', '345.678', None),
    (False, '123', 345, 456, '345', None),
    (False, 'abc', 'def', 'srd', 'def', None),
    (False, 'abc', 'def', None, 'def', None),
    (False, 'abc', None, 'srd', 'None', None),
    (False, True, 'False', 'True', False, None),
    (False, True, 'false', 'true', False, None),
    (False, True, 'FALSE', 'TRUE', False, None),
    (False, True, '0', '1', False, None),
    (False, True, 'False', True, False, None),
    (False, True, 'false', True, False, None),
    (False, True, 'FALSE', True, False, None),
    (False, True, '0', True, False, None),
    (False, False, 'True', 'False', True, None),
    (False, False, '1', '0', True, None),
    (False, False, 'true', 'false', True, None),
    (False, False, 'TRUE', 'FALSE', True, None),
    (False, False, 'True', False, True, None),
    (False, False, '1', False, True, None),
    (False, False, 'true', False, True, None),
    (False, False, 'TRUE', False, True, None),
    (False, False, 'Anything', 'Anything else', True, None),
    (False, None, 'def', False, None, None),
    (False, None, None, False, None, None),
    (True, 0, 1, -2, 1, -2),
    (True, 123, 345, 456, 345, 456),
    (True, 123, '345', '456', 345, 456),
    (True, 123.345, 345.678, 456.566, 345.678, 456.566),
    (True, 123.345, '345.678', '456.566', 345.678, 456.566),
    (True, '123', 345, 456, '345', '456'),
    (True, '123', 345.678, 456.566, '345.678', '456.566'),
    (True, '123.345', 345.678, 456.566, '345.678', '456.566'),
    (True, '123.345', '345.678', '456.566', '345.678', '456.566'),
    (True, '123', 345, 456, '345', '456'),
    (True, '123.345', 345.678, 456.566, '345.678', '456.566'),
    (True, '123.345', '345.678', '456.566', '345.678', '456.566'),
    (True, '123', 345, 456, '345', '456'),
    (True, 'abc', 'def', 'srd', 'def', 'srd'),
    (True, 'abc', 'def', None, 'def', 'None'),
    (True, 'abc', None, 'srd', 'None', 'srd'),
    (True, True, 'False', 'True', False, True),
    (True, True, 'false', 'true', False, True),
    (True, True, 'FALSE', 'TRUE', False, True),
    (True, True, '0', '1', False, True),
    (True, True, 'False', True, False, True),
    (True, True, 'false', True, False, True),
    (True, True, 'FALSE', True, False, True),
    (True, True, '0', True, False, True),
    (True, False, 'True', 'False', True, False),
    (True, False, '1', '0', True, False),
    (True, False, 'true', 'false', True, False),
    (True, False, 'TRUE', 'FALSE', True, False),
    (True, False, 'True', False, True, False),
    (True, False, '1', False, True, False),
    (True, False, 'true', False, True, False),
    (True, False, 'TRUE', False, True, False),
    (True, False, 'Anything', 'Anything else', True, True),
    (True, None, 'def', False, None, None),
    (True, None, None, False, None, None),
])
def test_send_on_release_value(qtbot: QtBot, initial_value, press_value, release_value, send_on_release, expected_press_value,
                               expected_release_value):
    widget = CPushButton()
    qtbot.add_widget(widget)

    widget.writeWhenRelease = send_on_release
    widget.pressValue = press_value
    widget.releaseValue = release_value

    channel_type: Optional[Type]
    if initial_value is not None:
        # If the user sets the initial value, emit the channel change signal. Otherwise, skip this signal emit part
        # and continue the test to see if the widget can handle a None initial value
        channel_type = type(initial_value)
        widget.channelValueChanged(CChannelData(value=initial_value, meta_info={}))
        assert widget.value == initial_value
    else:
        channel_type = str
        assert widget.value is None

    assert press_value != release_value

    with qtbot.wait_signal(widget.send_value_signal[channel_type], raising=False, timeout=100) as blocker:
        if send_on_release:
            qtbot.mousePress(widget, Qt.LeftButton)
        else:
            qtbot.mouseClick(widget, Qt.LeftButton)

    should_emit = (expected_press_value is not None)
    assert blocker.signal_triggered == should_emit
    if should_emit:
        assert blocker.args == [expected_press_value]

    with qtbot.wait_signal(widget.send_value_signal[channel_type], raising=False, timeout=100) as blocker:
        qtbot.mouseRelease(widget, Qt.LeftButton)

    should_emit = (expected_release_value is not None)
    assert blocker.signal_triggered == should_emit

    if should_emit:
        assert blocker.args == [expected_release_value]


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
    (True, False),
    (False, True),
    (False, False),
    (True, True),
    (True, '0'),
    (False, '1'),
    (False, '0'),
    (True, '1'),
    (True, 'false'),
    (False, 'true'),
    (False, 'false'),
    (True, 'true'),
    (False, 'Anything'),
])
def test_cpushbutton_update_press_value(qtbot, current_channel_value, updated_value):
    widget = CPushButton()
    qtbot.add_widget(widget)
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
    assert widget.pressValue == str(widget._convert(updated_value))


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
    (True, False),
    (False, True),
    (False, False),
    (True, True),
    (True, '0'),
    (False, '1'),
    (False, '0'),
    (True, '1'),
    (True, 'false'),
    (False, 'true'),
    (False, 'false'),
    (True, 'true'),
    (False, 'Anything'),
])
def test_cpushbutton_update_release_value(qtbot, current_channel_value, updated_value):
    widget = CPushButton()
    qtbot.add_widget(widget)
    assert widget.releaseValue == 'None'
    assert widget.value is None

    # First, set the current channel type
    widget.channelValueChanged(CChannelData(value=current_channel_value, meta_info={}))
    assert widget.releaseValue == 'None'
    if isinstance(current_channel_value, np.ndarray):
        assert (current_channel_value == widget.value).all()
    else:
        assert widget.value == current_channel_value

    # Verify the new value can be converted/cast as long as the casting can be done
    widget.updateReleaseValue(updated_value)

    # Verify the new value is assigned to be the new pressValue as a str
    if isinstance(current_channel_value, np.ndarray):
        assert (current_channel_value == widget.value).all()
    else:
        assert widget.value == current_channel_value
    assert widget.releaseValue == str(widget._convert(updated_value))


@pytest.mark.parametrize('current_channel_value,updated_value,expected_log_error', [
    (np.array([123.123, 456.456]), 10.10, "'10.1' is not a valid pressValue for '<channel>'."),
    (np.array(['abc', 'string in an array']), 'New str value', "'New str value' is not a valid pressValue for '<channel>'."),
    (10, 'New str value', "'New str value' is not a valid pressValue for '<channel>'."),
    (10.10, 'New str value', "'New str value' is not a valid pressValue for '<channel>'."),
])
def test_cpushbutton_update_press_value_incompatible_update_value(qtbot: QtBot, log_capture,
                                                                  current_channel_value, updated_value,
                                                                  expected_log_error):
    widget = CPushButton()
    qtbot.add_widget(widget)
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
    error_records = log_capture(logging.ERROR, 'comrad.widgets.buttons')
    assert error_records == [expected_log_error]


@pytest.mark.parametrize('current_channel_value,updated_value,expected_log_error', [
    (np.array([123.123, 456.456]), 10.10, "'10.1' is not a valid releaseValue for '<channel>'."),
    (np.array(['abc', 'string in an array']), 'New str value', "'New str value' is not a valid releaseValue for '<channel>'."),
    (10, 'New str value', "'New str value' is not a valid releaseValue for '<channel>'."),
    (10.10, 'New str value', "'New str value' is not a valid releaseValue for '<channel>'."),
])
def test_cpushbutton_update_release_value_incompatible_update_value(qtbot: QtBot, log_capture,
                                                                    current_channel_value, updated_value,
                                                                    expected_log_error):
    widget = CPushButton()
    qtbot.add_widget(widget)
    assert widget.releaseValue == 'None'
    assert widget.value is None

    # First, set the current channel type
    widget.channelValueChanged(CChannelData(value=current_channel_value, meta_info={}))
    assert widget.releaseValue == 'None'
    if isinstance(current_channel_value, np.ndarray):
        assert (current_channel_value == widget.value).all()
    else:
        assert widget.value == current_channel_value

    widget.channel = '<channel>'  # To make a fix value for warning message
    widget.updateReleaseValue(updated_value)

    # Make sure logging capture the error, and have the correct error message
    error_records = log_capture(logging.ERROR, 'comrad.widgets.buttons')
    assert error_records == [expected_log_error]
