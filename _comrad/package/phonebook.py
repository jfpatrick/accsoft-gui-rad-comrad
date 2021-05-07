import logging
import getpass
from typing import Optional, Tuple


logger = logging.getLogger(__name__)


def suggest_maintainer_info(default_maintainer: Optional[str] = None,
                            default_email: Optional[str] = None,
                            force: bool = False) -> Tuple[Optional[str], Optional[str]]:
    try:
        import pyphonebook as pb
        import ldap
    except ImportError:
        logger.debug(f'Phonebook not accessible. No maintainer info will be suggested.')
    else:
        username = getpass.getuser()
        if username not in _IGNORED_USERNAMES:
            logger.debug(f'Obtaining contact information for user: {username}.')
            try:
                ldap.set_option(ldap.OPT_NETWORK_TIMEOUT, 1)  # Fail quickly if having troubles to connect to server (e.g. outside of CERN)
                try:
                    book = pb.PhoneBook()
                    results = book.search_by_login_name(username)
                except ldap.TIMEOUT:
                    logger.debug(f'Failed to contact phonebook in a reasonable time.')
                except ldap.SERVER_DOWN:
                    logger.debug(f'Failed to contact phonebook server.')
                else:
                    try:
                        record = results[0]
                        if force:
                            return record.full_name[0], record.email[0]
                        else:
                            return (default_maintainer or record.full_name[0]), (default_email or record.email[0])
                    except IndexError:
                        pass
            except Exception as e:  # noqa: B902
                logger.debug(f'Unknown pyphonebook error. Bailing out: {e!s}.')
        else:
            logger.debug(f"Won't attempt to obtain information for user: {username}.")
    return default_maintainer, default_email


_IGNORED_USERNAMES = [
    'root',
]
