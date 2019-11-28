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
    throwable = get_java_exc(jpype_exc)
    while True:
        cause = throwable.getCause()
        if cause is None:
            break
        throwable = cause
    parts = throwable.getMessage().split(' : ')
    parts = parts[-1].split(' --> ')
    return parts[-1]
