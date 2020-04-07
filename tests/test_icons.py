import pytest
from pathlib import Path
from unittest import mock
import comrad.icons


@pytest.mark.parametrize('file_path,icon_name,expected_path', [
    ('/loc1/__init__.py', 'favicon', '/loc1/icons/favicon.ico'),
    ('/loc1/subdir1/__init__.py', 'favicon', '/loc1/subdir1/icons/favicon.ico'),
    (None, 'favicon', f'{str(Path(comrad.icons.__file__).parent.absolute())}/favicon.ico'),
])
def test_load_icon(file_path, icon_name, expected_path):
    with mock.patch('comrad.icons.QPixmap') as QPixmap:
        with mock.patch('comrad.icons.QIcon'):
            _ = comrad.icons.icon(name=icon_name, file_path=file_path)
            QPixmap.assert_called_with(expected_path)
