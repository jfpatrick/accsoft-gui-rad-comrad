import logging
import re
from typing import Optional, Tuple, Set
from packaging.requirements import Requirement, InvalidRequirement
from .importlib_shim import find_distribution_name, importlib_metadata


logger = logging.getLogger(__name__)


def parse_maintainer_info(input: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse maintainer info into name-email pair. This logic can recognize the following formats:

    - John Smith <john.smith@domain.com>
    - John Smith
    - john.smith@domain.com

    Args:
        input: Input string as received from the user.

    Returns:
        Tuple of maintainer name and maintainer email.
    """
    if input:
        mo = re.match(r'^(?P<name>[^<\n]+)(<(?P<email>.+@.+)>)?$', input)
        if mo and mo.groups():
            captures = mo.groupdict()
            if captures['email']:
                return captures['name'].strip(), captures['email'].strip()
            elif '@' in captures['name']:
                return '', captures['name'].strip()  # Treat name as email
            else:
                return captures['name'].strip(), ''
    return None, None


def make_requirement_safe(input: str, error: str) -> Optional[Requirement]:
    # Not only create a requirement object, but provide a real package name (if can be found) via
    # importlib_metadata, e.g.
    # qtpy -> QtPy
    # jpype -> JPype1
    dist_name = find_distribution_name(input)
    if dist_name:
        input = dist_name
    try:
        return Requirement(input)
    except InvalidRequirement:
        logger.warning(f'Cannot parse requirement "{input}". {error}')
        return None


def find_comrad_requirements() -> Set[Requirement]:
    comrad_pkg = importlib_metadata.distribution('comrad')  # type: ignore
    if comrad_pkg.requires is None:
        return set()
    return {Requirement(r) for r in comrad_pkg.requires if ' extra == ' not in r}
