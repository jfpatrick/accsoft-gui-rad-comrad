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
        Modified superclass instance.
    """
    super_class = new_cls.__mro__[1]
    logger.debug(f'Monkey-patching {super_class.__name__}...')
    predicate = lambda x: inspect.isfunction(x) or inspect.isdatadescriptor(x)
    super_methods: Dict[str, Callable] = dict(inspect.getmembers(object=super_class, predicate=predicate))
    sub_methods: Dict[str, Callable] = dict(inspect.getmembers(object=new_cls, predicate=predicate))
    new_methods: Dict[str, Callable] = {}
    modified_methods: Dict[str, Callable] = {}
    for name, impl in sub_methods.items():
        if name not in super_methods:
            new_methods[name] = impl
        elif impl is not super_methods.get(name, impl):
            modified_methods[name] = impl

    super_class = cast(MonkeyPatchedClass, super_class)
    super_class._overridden_methods = {}
    for name, impl in modified_methods.items():
        setattr(super_class, name, impl)
        super_class._overridden_methods[name] = super_methods[name]
        logger.debug(f'Class {super_class.__name__} received an overridden method "{name}"')
    for name, impl in new_methods.items():
        setattr(super_class, name, impl)

    return super_class
