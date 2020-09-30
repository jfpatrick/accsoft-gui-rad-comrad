from importlib.util import find_spec
from typing import Optional
from pathlib import Path

try:
    # Python >=3.8
    import importlib.metadata as importlib_metadata
except ImportError:
    # Python <3.8
    import importlib_metadata  # type: ignore


def find_distribution_name(module_name: str) -> Optional[str]:

    try:
        hashmap = importlib_metadata.packages_distributions()  # type: ignore
    except AttributeError:
        return _backport_find_distribution(module_name)
    else:
        return hashmap.get(module_name, [None])[0]


def _backport_find_distribution(module_name: str) -> Optional[str]:
    file_spec = find_spec(module_name)
    if file_spec is None or file_spec.origin is None:
        return None

    file_path = Path(file_spec.origin)
    for distribution in importlib_metadata.distributions():  # type: ignore
        try:
            relative = file_path.relative_to(distribution.locate_file(''))  # type: ignore
        except ValueError:
            pass
        else:
            if relative in distribution.files:
                try:
                    return distribution.metadata['Name']
                except KeyError:
                    continue
    else:
        return None
