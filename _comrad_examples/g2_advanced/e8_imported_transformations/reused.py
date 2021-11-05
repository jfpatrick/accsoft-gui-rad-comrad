# This file can be reused from Python snippets or specified as a main external file
from typing import Callable, Any


def decorate(input: str) -> str:
    return f'<<{input}>>\nfrom {__file__}'


if __name__ == '__main__':
    new_val: str  # This is injected by the script machinery
    output: Callable[[Any], None]  # This is injected by the script machinery
    output(decorate(new_val))  # noqa: F821
