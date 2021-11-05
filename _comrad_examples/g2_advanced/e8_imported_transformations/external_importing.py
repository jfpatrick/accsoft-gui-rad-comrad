# This file is an example of an external Python snippet that imports another Python file

from imported import decorate
from typing import Callable, Any


new_val: str  # This is injected by the script machinery
output: Callable[[Any], None]  # This is injected by the script machinery
output(decorate(new_val))  # noqa: F821
