import pytest
import logging
import functools
import numpy as np
from unittest import mock
from pytestqt.qtbot import QtBot
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor
from comrad import CEnumValue, CLabel, CChannelData, CLed


@pytest.mark.parametrize('input_val,display_format,expected_value', [
    (CEnumValue(code=1, label='ONE', meaning=CEnumValue.Meaning.ON, settable=True), CLabel.DisplayFormat.Default, "CEnumValue(code=1, label='ONE', meaning=<Meaning.ON: 1>, settable=True)"),
    (CEnumValue(code=1, label='ONE', meaning=CEnumValue.Meaning.ON, settable=True), CLabel.DisplayFormat.String, 'ONE'),
    (CEnumValue(code=1, label='ONE', meaning=CEnumValue.Meaning.ON, settable=True), CLabel.DisplayFormat.Binary, '0b1'),
    (CEnumValue(code=1, label='ONE', meaning=CEnumValue.Meaning.ON, settable=True), CLabel.DisplayFormat.Hex, '0x1'),
    (CEnumValue(code=1, label='ONE', meaning=CEnumValue.Meaning.ON, settable=True), CLabel.DisplayFormat.Exponential, '1e+00'),
    (CEnumValue(code=1, label='ONE', meaning=CEnumValue.Meaning.ON, settable=True), CLabel.DisplayFormat.Decimal, '1'),
    (1, CLabel.DisplayFormat.Default, '1'),
    (1, CLabel.DisplayFormat.String, '1'),
    (1, CLabel.DisplayFormat.Decimal, '1'),
    (1, CLabel.DisplayFormat.Binary, '0b1'),
    (1, CLabel.DisplayFormat.Hex, '0x1'),
    (1, CLabel.DisplayFormat.Exponential, '1e+00'),
    ('1', CLabel.DisplayFormat.Default, '1'),
    ('1', CLabel.DisplayFormat.String, '1'),
    ('1', CLabel.DisplayFormat.Decimal, '1'),
    ('1', CLabel.DisplayFormat.Binary, '1'),
    ('1', CLabel.DisplayFormat.Hex, '1'),
    ('1', CLabel.DisplayFormat.Exponential, '1'),
])
def test_clabel_formats_displays_enum_field(qtbot: QtBot, input_val, display_format, expected_value):
    widget = CLabel()
    qtbot.add_widget(widget)
    packet = CChannelData(value=input_val, meta_info={})
    widget.displayFormat = display_format
    widget.channelValueChanged(packet)
    assert widget.text() == expected_value


@pytest.mark.parametrize('is_designer_value,init_map,expected_value', [
    (False, {}, {}),
    (False, {1: QColor(Qt.red)}, {1: QColor(Qt.red)}),
    (False, {-1: QColor(Qt.red), 2: QColor(Qt.green)}, {-1: QColor(Qt.red), 2: QColor(Qt.green)}),
    (True, {}, '{}'),
    (True, {1: QColor(Qt.red)}, '{"1": "#ff0000"}'),
    (True, {-1: QColor(Qt.red), 2: QColor(Qt.green)}, '{"-1": "#ff0000", "2": "#00ff00"}'),
])
@mock.patch('comrad.widgets.indicators.is_qt_designer')
def test_cled_color_map_getter(is_qt_designer, is_designer_value, expected_value, init_map, qtbot: QtBot):
    is_qt_designer.return_value = is_designer_value
    widget = CLed()
    qtbot.add_widget(widget)
    widget._color_map = init_map
    assert widget.color_map == expected_value


@pytest.mark.parametrize('is_designer_value,new_map,expected_value', [
    (False, {}, {}),
    (False, {1: QColor(Qt.red)}, {1: QColor(Qt.red)}),
    (False, {-1: QColor(Qt.red), 2: QColor(Qt.green)}, {-1: QColor(Qt.red), 2: QColor(Qt.green)}),
    (True, '{}', {}),
    (True, '{"1": "#ff0000"}', {1: QColor(Qt.red)}),
    (True, '{"-1": "#ff0000", "2": "#00ff00"}', {-1: QColor(Qt.red), 2: QColor(Qt.green)}),
])
@mock.patch('comrad.widgets.indicators.is_qt_designer')
def test_cled_color_map_setter(is_qt_designer, is_designer_value, expected_value, new_map, qtbot: QtBot):
    is_qt_designer.return_value = is_designer_value
    widget = CLed()
    qtbot.add_widget(widget)
    assert widget._color_map == {}
    widget.color_map = new_map
    assert widget._color_map == expected_value


@pytest.mark.parametrize('input,expected_warning', [
    ('{', 'Failed to decode json: Expecting property name enclosed in double quotes:'),
    ('{2: "#ff0000"}', 'Failed to decode json: Expecting property name enclosed in double quotes:'),
    ('', 'Failed to decode json: Expecting value:'),
])
@mock.patch('comrad.widgets.indicators.is_qt_designer', return_value=True)
def test_cled_color_map_setter_json_decode_error(_, input, qtbot: QtBot, expected_warning, log_capture):
    widget = CLed()
    qtbot.add_widget(widget)
    assert log_capture(logging.WARNING, logger_module='indicators') == []
    assert widget._color_map == {}
    widget.color_map = input
    assert widget._color_map == {}
    warning_messages = log_capture(logging.WARNING, logger_module='indicators')
    assert len(warning_messages) == 1
    assert warning_messages[0].startswith(expected_warning)


@pytest.mark.parametrize('input,expect_warning', [
    ('{}', False),
    ('[]', True),
    ('{"2": "#ff0000"}', False),
    ('[{"2": "#ff0000"}]', True),
])
@mock.patch('comrad.widgets.indicators.is_qt_designer', return_value=True)
def test_cled_color_map_setter_json_not_dict_error(_, input, qtbot: QtBot, expect_warning, log_capture):
    widget = CLed()
    qtbot.add_widget(widget)
    assert log_capture(logging.WARNING, logger_module='indicators') == []
    widget.color_map = input
    warning_messages = log_capture(logging.WARNING, logger_module='indicators')
    if expect_warning:
        assert warning_messages == ['Decoded color map is not a dictionary']
    else:
        assert warning_messages == []


@pytest.mark.parametrize('input,expected_warning', [
    ('{"abc": "#ff0000"}', "Failed to parse color map: invalid literal for int() with base 10: 'abc'"),
    ('{"2-a": "#ff0000"}', "Failed to parse color map: invalid literal for int() with base 10: '2-a'"),
    ('{"1e-6": "#ff0000"}', "Failed to parse color map: invalid literal for int() with base 10: '1e-6'"),
    ('{"0.00005": "#ff0000"}', "Failed to parse color map: invalid literal for int() with base 10: '0.00005'"),
])
@mock.patch('comrad.widgets.indicators.is_qt_designer', return_value=True)
def test_cled_color_map_setter_json_dict_key_error(_, input, qtbot: QtBot, expected_warning, log_capture):
    widget = CLed()
    qtbot.add_widget(widget)
    assert log_capture(logging.WARNING, logger_module='indicators') == []
    widget.color_map = input
    assert log_capture(logging.WARNING, logger_module='indicators') == [expected_warning]


@pytest.mark.parametrize('on_color,off_color', [
    (QColor(Qt.yellow), QColor(Qt.cyan)),
])
@pytest.mark.parametrize('input,color_map,expected_super_val,expected_status_setter,expected_color_setter', [
    (1, {}, 1, CLed.Status.ON, None),
    (2.5, {}, None, None, None),
    (True, {}, True, None, QColor(Qt.yellow)),
    (False, {}, False, None, QColor(Qt.cyan)),
    ('abc', {}, None, None, None),
    (CEnumValue(code=1, label='', meaning=CEnumValue.Meaning.NONE, settable=False), {},
     CEnumValue(code=1, label='', meaning=CEnumValue.Meaning.NONE, settable=False), CLed.Status.NONE, None),
    (CEnumValue(code=1, label='', meaning=CEnumValue.Meaning.WARNING, settable=False), {},
     CEnumValue(code=1, label='', meaning=CEnumValue.Meaning.WARNING, settable=False), CLed.Status.WARNING, None),
    (CEnumValue(code=1, label='', meaning=CEnumValue.Meaning.ERROR, settable=False), {},
     CEnumValue(code=1, label='', meaning=CEnumValue.Meaning.ERROR, settable=False), CLed.Status.ERROR, None),
    (QColor(Qt.green), {}, QColor(Qt.green), None, QColor(Qt.green)),
    (1, {1: QColor(Qt.red)}, 1, None, QColor(Qt.red)),
    (2.5, {1: QColor(Qt.red)}, None, None, None),
    (True, {1: QColor(Qt.red)}, True, None, QColor(Qt.yellow)),
    (False, {1: QColor(Qt.red)}, False, None, QColor(Qt.cyan)),
    ('abc', {1: QColor(Qt.red)}, None, None, None),
    (CEnumValue(code=1, label='', meaning=CEnumValue.Meaning.NONE, settable=False), {1: QColor(Qt.red)},
     CEnumValue(code=1, label='', meaning=CEnumValue.Meaning.NONE, settable=False), None, QColor(Qt.red)),
    (CEnumValue(code=1, label='', meaning=CEnumValue.Meaning.WARNING, settable=False), {1: QColor(Qt.red)},
     CEnumValue(code=1, label='', meaning=CEnumValue.Meaning.WARNING, settable=False), None, QColor(Qt.red)),
    (CEnumValue(code=1, label='', meaning=CEnumValue.Meaning.ERROR, settable=False), {1: QColor(Qt.red)},
     CEnumValue(code=1, label='', meaning=CEnumValue.Meaning.ERROR, settable=False), None, QColor(Qt.red)),
    (QColor(Qt.green), {1: QColor(Qt.red)}, QColor(Qt.green), None, QColor(Qt.green)),
])
@mock.patch('comrad.widgets.mixins.CChannelDataProcessingMixin.value_changed')
def test_cled_value_changed(super_value_changed, color_map, qtbot: QtBot, input, expected_color_setter,
                            expected_status_setter, expected_super_val, on_color, off_color):
    widget = CLed()
    qtbot.add_widget(widget)
    widget.color_map = color_map
    widget.onColor = on_color
    widget.offColor = off_color
    input_packed = CChannelData(value=input, meta_info={})
    with mock.patch.object(CLed, 'status', new_callable=mock.PropertyMock, wraps=functools.partial(CLed.status.__set__, widget)) as status:
        with mock.patch.object(CLed, 'color', new_callable=mock.PropertyMock, wraps=functools.partial(CLed.color.__set__, widget)) as color:
            widget.value_changed(input_packed)
            if expected_status_setter is not None:
                status.assert_called_once_with(expected_status_setter)
            else:
                status.assert_not_called()
            if expected_color_setter is not None:
                color.assert_called_once_with(expected_color_setter)
            else:
                color.assert_not_called()
    if expected_super_val is not None:
        super_value_changed.assert_called_once_with(CChannelData(value=expected_super_val, meta_info={}))
    else:
        super_value_changed.assert_not_called()


@pytest.mark.parametrize('input', [
    None,
    'abc',
    1,
    2.5,
    [],
    {},
    np.array([1, 2]),
    True,
    False,
])
@mock.patch('comrad.widgets.mixins.CChannelDataProcessingMixin.value_changed')
def test_cled_value_changed_skips_without_channel_data(super_value_changed, qtbot: QtBot, input):
    widget = CLed()
    qtbot.add_widget(widget)
    with mock.patch.object(CLed, 'status', new_callable=mock.PropertyMock, wraps=functools.partial(CLed.status.__set__, widget)) as status:
        with mock.patch.object(CLed, 'color', new_callable=mock.PropertyMock, wraps=functools.partial(CLed.color.__set__, widget)) as color:
            widget.value_changed(input)
            color.assert_not_called()
            status.assert_not_called()
    super_value_changed.assert_not_called()


@pytest.mark.parametrize('input,expected_status', [
    (CEnumValue.Meaning.NONE, CLed.Status.NONE),
    (CEnumValue.Meaning.ON, CLed.Status.ON),
    (CEnumValue.Meaning.OFF, CLed.Status.OFF),
    (CEnumValue.Meaning.WARNING, CLed.Status.WARNING),
    (CEnumValue.Meaning.ERROR, CLed.Status.ERROR),
])
def test_cled_meaning_to_status_succeeds(input, expected_status):
    assert CLed.meaning_to_status(input) == expected_status


@pytest.mark.parametrize('input,expected_error', [
    ('abc', 'Cannot correlate LED status with meaning "abc"'),
    (None, 'Cannot correlate LED status with meaning "None"'),
    (123, 'Cannot correlate LED status with meaning "123"'),
])
def test_cled_meaning_to_status_fails(input, expected_error):
    with pytest.raises(ValueError, match=expected_error):
        CLed.meaning_to_status(input)


@pytest.mark.parametrize('on_color', [QColor(Qt.cyan), QColor(Qt.yellow)])
@pytest.mark.parametrize('color_map', [{}, {1: QColor(Qt.red)}])
@pytest.mark.parametrize('input,off_color,expected_val', [
    (None, QColor(Qt.green), QColor(Qt.green)),
    (None, QColor(Qt.blue), QColor(Qt.blue)),
    ('#cecece', QColor(Qt.green), QColor('#cecece')),
    ('#cecece', QColor(Qt.blue), QColor('#cecece')),
])
@mock.patch('comrad.widgets.mixins.CColorRulesMixin.set_color')
def test_cled_set_color(set_color, qtbot: QtBot, input, expected_val, on_color, off_color, color_map):
    widget = CLed()
    qtbot.add_widget(widget)
    widget.onColor = on_color
    widget.offColor = off_color
    widget.color_map = color_map
    with mock.patch.object(CLed, 'color', new_callable=mock.PropertyMock, wraps=functools.partial(CLed.color.__set__, widget)) as color:
        widget.set_color(input)
        color.assert_called_once_with(expected_val)
    set_color.assert_called_once_with(input)
