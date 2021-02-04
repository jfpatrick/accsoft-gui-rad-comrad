import pytest
from qtpy.QtCore import Qt
from comrad.app.application import toolbar_style_from_str, toolbar_area_from_str


@pytest.mark.parametrize('input,expected_output', [
    ('icon', Qt.ToolButtonIconOnly),
    ('text', Qt.ToolButtonTextOnly),
    ('vstack', Qt.ToolButtonTextUnderIcon),
    ('hstack', Qt.ToolButtonTextBesideIcon),
])
def test_toolbar_style_from_str_succeeds(input, expected_output):
    assert toolbar_style_from_str(input) == expected_output


@pytest.mark.parametrize('input,expected_error', [
    ('', 'Unsupported navbar style: '),
    ('test', 'Unsupported navbar style: test'),
    ('Icon', 'Unsupported navbar style: Icon'),
    ('ICON', 'Unsupported navbar style: ICON'),
    ('Text', 'Unsupported navbar style: Text'),
    ('TEXT', 'Unsupported navbar style: TEXT'),
    ('Vstack', 'Unsupported navbar style: Vstack'),
    ('VSTACK', 'Unsupported navbar style: VSTACK'),
    ('Hstack', 'Unsupported navbar style: Hstack'),
    ('HSTACK', 'Unsupported navbar style: HSTACK'),
])
def test_toolbar_style_from_str_fails(input, expected_error):
    with pytest.raises(ValueError, match=expected_error):
        toolbar_style_from_str(input)


@pytest.mark.parametrize('input,expected_output', [
    ('top', Qt.TopToolBarArea),
    ('left', Qt.LeftToolBarArea),
])
def test_toolbar_area_from_str_succeeds(input, expected_output):
    assert toolbar_area_from_str(input) == expected_output


@pytest.mark.parametrize('input,expected_error', [
    ('', 'Unsupported navbar position: '),
    ('TOP', 'Unsupported navbar position: TOP'),
    ('LEFT', 'Unsupported navbar position: LEFT'),
    ('Top', 'Unsupported navbar position: Top'),
    ('Left', 'Unsupported navbar position: Left'),
    ('test', 'Unsupported navbar position: test'),
    ('right', 'Unsupported navbar position: right'),
    ('botton', 'Unsupported navbar position: botton'),
])
def test_toolbar_area_from_str_fails(input, expected_error):
    with pytest.raises(ValueError, match=expected_error):
        toolbar_area_from_str(input)
