import pytest
from pytestqt.qtbot import QtBot
from comrad import CEnumValue, CLabel, CChannelData


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
    qtbot.addWidget(widget)
    packet = CChannelData(value=input_val, meta_info={})
    widget.displayFormat = display_format
    widget.channelValueChanged(packet)
    assert widget.text() == expected_value
