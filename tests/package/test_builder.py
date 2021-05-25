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
    ('=@bundle', '=@bundle'),
    ('=@bundlesomewhere', '=@bundlesomewhere'),
    ('test=@bundle', 'test=@bundle'),
    ('test=@bundlesomewhere', 'test=@bundlesomewhere'),
    ('-t=@bundle', '-t=@bundle'),
    ('-t=@bundlesomewhere', '-t=@bundlesomewhere'),
    ('--test=@bundle', '--test=TEST_LOC'),
    ('--test=@bundlesomewhere', '--test=@bundlesomewhere'),
    ('--t=@bundle', '--t=TEST_LOC'),
    ('--t=@bundlesomewhere', '--t=@bundlesomewhere'),
    ('--test2=@bundle', '--test2=TEST_LOC'),
    ('--test2=@bundlesomewhere', '--test2=@bundlesomewhere'),
    ('--nav-path=@bundle', '--nav-path=TEST_LOC'),
    ('--nav-path=@bundlesomewhere', '--nav-path=@bundlesomewhere'),
    ('--nav-path-=@bundle', '--nav-path-=@bundle'),
    ('--nav-path-=@bundlesomewhere', '--nav-path-=@bundlesomewhere'),
])
def test_path_replace(input, expected_output):
    assert _path_replace(input, 'TEST_LOC') == expected_output
