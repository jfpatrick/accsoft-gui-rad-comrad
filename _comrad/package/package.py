import logging
import re
from typing import Optional, Tuple


logger = logging.getLogger('comrad.package')


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
