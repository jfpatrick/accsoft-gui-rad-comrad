import pytest
from unittest import mock
from typing import cast
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication
from comrad.app.application import toolbar_style_from_str, toolbar_area_from_str, CApplication


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


@pytest.mark.parametrize('serialized_token,should_find', [
    (None, False),
    ('abcdef', True),
])
@mock.patch('comrad.app.application.subprocess.Popen')
def test_serialized_token_is_passed_to_subprocess(Popen, serialized_token, qtbot, should_find):
    _ = qtbot
    app = cast(CApplication, QApplication.instance())
    with mock.patch.object(app, 'rbac') as rbac:
        rbac.serialized_token = serialized_token
        Popen.assert_not_called()
        CApplication.new_pydm_process(app, ui_file='test_file.ui')
        Popen.assert_called_once()
        args = Popen.call_args[0][0]
        if should_find:
            assert '--rbac-token' in args
            idx = args.index('--rbac-token')
            assert len(args) > idx + 1
            assert args[idx + 1] == serialized_token
        else:
            assert '--rbac-token' not in args
