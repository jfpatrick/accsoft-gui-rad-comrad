from typing import Any
from comrad.data.japc_enum import SimpleValueStandardMeaning


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


def meaning_from_jpype(orig: object) -> SimpleValueStandardMeaning:
    """
    Convert JPype enum into Python one.

    Args:
        orig: JPype object of the enum.

    Raises:
        ValueError if value is unknown
    """
    import jpype
    cern = jpype.JPackage('cern')  # type: ignore
    if orig == cern.japc.value.SimpleValueStandardMeaning.ON:
        return SimpleValueStandardMeaning.ON
    elif orig == cern.japc.value.SimpleValueStandardMeaning.OFF:
        return SimpleValueStandardMeaning.OFF
    elif orig == cern.japc.value.SimpleValueStandardMeaning.WARNING:
        return SimpleValueStandardMeaning.WARNING
    elif orig == cern.japc.value.SimpleValueStandardMeaning.ERROR:
        return SimpleValueStandardMeaning.ERROR
    elif orig == cern.japc.value.SimpleValueStandardMeaning.NONE:
        return SimpleValueStandardMeaning.NONE
    raise ValueError(f'Unsupported meaning value "{orig}"')
