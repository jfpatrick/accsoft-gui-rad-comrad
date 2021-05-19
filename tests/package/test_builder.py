import pytest
from comrad_package.builder import _path_replace


@pytest.mark.parametrize('input,expected_output', [
    ('@bundle', 'TEST_LOC'),
    ('@bundle ', 'TEST_LOC'),
    (' @bundle ', 'TEST_LOC'),
    ('@@bundle', '@@bundle'),
    ('@bundle/to/stuff', 'TEST_LOC/to/stuff'),
    ('@bundle\\to/stuff', '@bundle\\to/stuff'),
    ('@bundlesomewhere', '@bundlesomewhere'),
    ('my-branch@bundle', 'my-branch@bundle'),
    ('my-branch@bundle ', 'my-branch@bundle'),
    ('my-branch @bundle', 'my-branch @bundle'),
    ('my-branch@bundle-somewhere', 'my-branch@bundle-somewhere'),
    ('my-branch@bundlesomewhere', 'my-branch@bundlesomewhere'),
])
def test_path_replace(input, expected_output):
    assert _path_replace(input, 'TEST_LOC') == expected_output
