import inspect
import logging
from typing import Type, Callable, Dict, cast


logger = logging.getLogger(__name__)


class MonkeyPatchedClass:
    """Just for typing reasons, this type exposes the method to be used by monkey-patched classes."""

    _overridden_methods: Dict[str, Callable] = {}
    """Methods overridden by monkey-patching."""



def modify_in_place(new_cls: Type):
    """Generic Monkey-patching solution for classes.

    Many PyDM classes do not support dependency injection and therefore timely modification
    of their behavior is difficult. This solution allows to define a subclass of PyDM class with the
    given decorator that will modify the class definition of PyDM and allow overridden methods.

    Please note, in your subclass methods you should not be calling super(), but instead access PyDM
    superclass' methods as `self._overridden_methods["my_method_name"]`.

    Args:
        new_cls: Subclass defining method implementations that should be used to monkey-patch its direct superclass
                 (it will take the first superclass in the list in case of multiple inheritance).

    Returns:
        Subclass instance.
    """
    orig_class = new_cls.__mro__[1]
    orig_methods = dict(inspect.getmembers(object=orig_class, predicate=inspect.isfunction))
    new_methods = dict(inspect.getmembers(object=new_cls, predicate=inspect.isfunction))
    modified_methods = {name: impl for name, impl in new_methods.items()
                        if impl is not orig_methods.get(name, impl)}

    orig_class = cast(MonkeyPatchedClass, orig_class)
    orig_class._overridden_methods = {}
    for name, impl in modified_methods.items():
        setattr(orig_class, name, impl)
        orig_class._overridden_methods[name] = orig_methods[name]
        logger.debug(f'Class {orig_class.__name__} received an overridden method "{name}"')

    return new_cls
