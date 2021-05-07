import pytest
from _comrad.package import parse_maintainer_info


@pytest.mark.parametrize('input,expected_result', [
    (None, (None, None)),
    ('', (None, None)),
    ('John', ('John', '')),
    ('John Smith', ('John Smith', '')),
    ('John.Smith@example.com', ('', 'John.Smith@example.com')),
    ('John Smith <John.Smith@example.com>', ('John Smith', 'John.Smith@example.com')),
    ('John Smith <John.Smith@example.com', (None, None)),
    ('John Smith <>', (None, None)),
    ('<John.Smith@example.com> John Smith', (None, None)),
    ('John.Smith@', ('', 'John.Smith@')),
])
def test_parse_maintainer_info(input, expected_result):
    result = parse_maintainer_info(input)
    assert result == expected_result
