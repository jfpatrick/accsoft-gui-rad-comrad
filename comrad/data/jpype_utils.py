from typing import Iterator
from comrad import CEnumValue
from comrad._cwm_utils import parse_cmw_error_message
from jpype.types import JException


def _iter_causes(jpype_exc: JException) -> Iterator[JException]:
    """
    Iterates through the hierarchy of exceptions in the nested exception.

    Args:
        jpype_exc: jPype exception, e.g. cern.java.smth.Exception.

    Returns:
        Instance of each Java exception.
    """
    throwable = jpype_exc
    yield throwable
    while True:
        cause = throwable.getCause()
        if cause is None:
            break
        throwable = cause
        yield throwable


def get_root_cause(jpype_exc: JException) -> JException:
    """
    Extracts instance of the Java exception that caused the problem.

    Args:
        jpype_exc: jPype exception, e.g. cern.java.smth.Exception

    Returns:
        Instance of the root Java exception
    """
    *_, last = _iter_causes(jpype_exc)
    return last


def get_java_user_message(jpype_exc: JException) -> str:
    """
    Extracts the Java exception message.

    Args:
        jpype_exc: jPype exception, e.g. java.lang.Exception

    Returns:
        String extracted from the message.
    """
    throwable = get_root_cause(jpype_exc)
    return throwable.getMessage()


def get_cmw_user_message(jpype_exc: JException) -> str:
    """
    Extracts the last part of the Java exception message.

    It seems that Java (CERN CMW libraries) do not particularly nest the exceptions so that particular
    message can be extracted. Instead, a composite string is returned without any API to break it into layers.
    For now, we assume that the last component in the message is the user-facing (least technical) part of it.

    Args:
        jpype_exc: jPype exception, e.g. cern.java.smth.Exception

    Returns:
        String extracted from the message.
    """
    return parse_cmw_error_message(get_java_user_message(jpype_exc))


def meaning_from_jpype(orig: object) -> CEnumValue.Meaning:
    """
    Convert JPype enum into Python one.

    Args:
        orig: JPype object of the enum.

    Raises:
        ValueError if value is unknown
    """
    import jpype
    cern = jpype.JPackage('cern')
    if orig == cern.japc.value.SimpleValueStandardMeaning.ON:
        return CEnumValue.Meaning.ON
    elif orig == cern.japc.value.SimpleValueStandardMeaning.OFF:
        return CEnumValue.Meaning.OFF
    elif orig == cern.japc.value.SimpleValueStandardMeaning.WARNING:
        return CEnumValue.Meaning.WARNING
    elif orig == cern.japc.value.SimpleValueStandardMeaning.ERROR:
        return CEnumValue.Meaning.ERROR
    elif orig == cern.japc.value.SimpleValueStandardMeaning.NONE:
        return CEnumValue.Meaning.NONE
    raise ValueError(f'Unsupported meaning value "{orig}"')
