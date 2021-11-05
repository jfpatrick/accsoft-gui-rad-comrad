# This file is an example of a self-sufficient Python file
from typing import Callable, Any


new_val: str  # This is injected by the script machinery
output: Callable[[Any], None]  # This is injected by the script machinery
output(f'<<{new_val}>>\nfrom {__file__}')  # noqa: F821
