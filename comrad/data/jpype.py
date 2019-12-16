from typing import Any


def get_java_exc(jpype_exc: Any) -> Any:
    """
    Extracts instance of the Java exception from the wrapper.

    Args:
        jpype_exc: jPype exception wrapper produced with jpype.JException(cern.java.smth.Exception).

    Returns:
        Instance of the Java exception
    """
    return jpype_exc.__javaobject__


def _iter_causes(jpype_exc: Any) -> Any:
    """
    Iterates through the hierarchy of exceptions in the nested exception.

    Args:
        jpype_exc: jPype exception wrapper produced with jpype.JException(cern.java.smth.Exception).

    Returns:
        Instance of each Java exception.
    """
    throwable = get_java_exc(jpype_exc)
    yield throwable
    while True:
        cause = throwable.getCause()
        if cause is None:
            break
        throwable = cause
        yield throwable


def get_root_cause(jpype_exc: Any) -> Any:
    """
    Extracts instance of the Java exception that caused the problem.

    Args:
        jpype_exc: jPype exception wrapper produced with jpype.JException(cern.java.smth.Exception).

    Returns:
        Instance of the Java exception
    """
    *_, last = _iter_causes(jpype_exc)
    return last


def get_user_message(jpype_exc: Any) -> str:
    """
    Extracts the last part of the Java exception from the wrapper.

    It seems that Java does not particularly nest the exceptions so that particular message can be extracted.
    Instead, a composite string is returned without any API to break it into layers. For now, we assume that
    the last component in the message is the user-facing (least technical) part of it.

    Args:
        jpype_exc: jPype exception wrapper produced with jpype.JException(cern.java.smth.Exception).

    Returns:
        String extracted from the message.
    """
    throwable = get_root_cause(jpype_exc)
    parts = throwable.getMessage().split(' : ')
    parts = parts[-1].split(' --> ')
    return parts[-1]


def is_security_exception(jpype_exc: Any) -> bool:
    """
    Checks whether given exception is the security exception related to user permissions.

    To not be coupled with the PyJAPC implementation, we actually look for pattern in the name
    of the causes of the exception. It's just an assumption, but it's the best guess to not
    have a hardcoded types here...

    Args:
        jpype_exc: jPype exception wrapper produced with jpype.JException(cern.java.smth.Exception).

    Returns:
        True if exception related to user permissions.
    """
    for exc in _iter_causes(jpype_exc):
        if type(exc).__name__.endswith('SecurityException'):
            return True
    return False
