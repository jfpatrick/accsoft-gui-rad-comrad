import inspect
import logging
from typing import Type, Callable, Dict, cast


logger = logging.getLogger(__name__)


class MonkeyPatchedClass:
    """Just for typing reasons, this type exposes the method to be used by monkey-patched classes."""

    _overridden_members: Dict[str, Callable] = {}
    """Methods and properties overridden by monkey-patching."""


def modify_in_place(new_cls: Type):
    """Generic Monkey-patching solution for classes.

    Many PyDM classes do not support dependency injection and therefore timely modification
    of their behavior is difficult. This solution allows to define a subclass of PyDM class with the
    given decorator that will modify the class definition of PyDM and allow overridden methods and properties.

    Please note, in your subclass members you should not be calling super(), but instead access PyDM
    superclass' methods as

    >>> self._overridden_members['my_method_name'](self)

    and superclass' properties as

    >>> self._overridden_members['my_prop_name'].fset(self, val)

    Pay attention when overriding properties. When overridding both getter and setter, whichever comes first,
    must refer to the superclass'es property in the decorator, the later one should refer to the newly created property,
    e.g.

    >>> class Overriding(Base):
    >>>
    >>>    @Base.prop.getter  # Refer to the base class, so that we actually override base getter
    >>>    def prop(self):
    >>>        return self._overridden_members['prop'].fget(self)
    >>>
    >>>    @prop.setter  # We must not refer to Base here, as that property has been substituted by the new one, of
    >>>                  # this class, created by the getter above
    >>>    def prop(self, new_val):
    >>>        self._overridden_members['prop'].fset(self, new_val)

    Args:
        new_cls: Subclass defining member implementations that should be used to monkey-patch its direct superclass
                 (it will take the first superclass in the list in case of multiple inheritance).

    Returns:
        Modified superclass instance.
    """
    super_class = new_cls.mro()[1]
    logger.debug(f'Monkey-patching {super_class.__name__}...')
    predicate = lambda x: inspect.isfunction(x) or inspect.isdatadescriptor(x)
    super_members: Dict[str, Callable] = dict(inspect.getmembers(object=super_class, predicate=predicate))
    sub_members: Dict[str, Callable] = dict(inspect.getmembers(object=new_cls, predicate=predicate))
    new_members: Dict[str, Callable] = {}
    modified_members: Dict[str, Callable] = {}
    for name, impl in sub_members.items():
        if name not in super_members:
            new_members[name] = impl
        elif impl is not super_members.get(name, impl):
            modified_members[name] = impl

    super_class = cast(Type[MonkeyPatchedClass], super_class)
    super_class._overridden_members = {}
    for name, impl in modified_members.items():
        setattr(super_class, name, impl)
        super_class._overridden_members[name] = super_members[name]
        logger.debug(f'Overriding "{super_class.__name__}.{name}"')
    for name, impl in new_members.items():
        setattr(super_class, name, impl)
        logger.debug(f'Attaching new member "{super_class.__name__}.{name}" ({type(impl)})')

    return super_class
