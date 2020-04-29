import pytest
from typing import cast
from comrad.monkey import modify_in_place, MonkeyPatchedClass


@pytest.mark.parametrize('obj_cls', [
    'BaseClass',
    'SubClass',
])
def test_modify_in_place_overrides_existing_methods(obj_cls):
    class BaseClass:

        def __init__(self):
            self.base_method_called: bool = False
            self.base_getter_called: bool = False
            self.base_setter_called: bool = False

        def method(self):
            self.base_method_called = True

        @property
        def prop(self) -> str:
            self.base_getter_called = True
            return 'base'

        @prop.setter
        def prop(self, _: str):
            self.base_setter_called = True

    @modify_in_place
    class SubClass(BaseClass, MonkeyPatchedClass):

        def __init__(self):
            self.sub_method_called: bool = False
            self.sub_setter_called: bool = False
            self.sub_getter_called: bool = False
            self._overridden_members['__init__'](self)

        def method(self):
            self.sub_method_called = True
            self._overridden_members['method'](self)

        @BaseClass.prop.setter
        def prop(self, new_val: str):
            self.sub_setter_called = True
            self._overridden_members['prop'].fset(self, new_val)

        @prop.getter
        def prop(self):
            self.sub_getter_called = True
            return self._overridden_members['prop'].fget(self)

    base_obj = eval(obj_cls)()
    assert hasattr(base_obj, 'sub_method_called')
    assert hasattr(base_obj, 'sub_setter_called')
    assert hasattr(base_obj, 'sub_getter_called')
    assert hasattr(base_obj, '_overridden_members')
    real_obj = cast(SubClass, base_obj)
    assert set(real_obj._overridden_members.keys()) == {'__init__', 'method', 'prop'}
    assert real_obj.base_method_called is False
    assert real_obj.sub_method_called is False
    real_obj.method()
    assert real_obj.base_method_called is True
    assert real_obj.sub_method_called is True
    assert real_obj.base_getter_called is False
    assert real_obj.sub_getter_called is False
    assert real_obj.base_setter_called is False
    assert real_obj.sub_setter_called is False
    _ = real_obj.prop
    assert real_obj.base_getter_called is True
    assert real_obj.sub_getter_called is True
    assert real_obj.base_setter_called is False
    assert real_obj.sub_setter_called is False
    real_obj.prop = 'test'
    assert real_obj.base_setter_called is True
    assert real_obj.sub_setter_called is True


@pytest.mark.parametrize('obj_cls', [
    'BaseClass',
    'SubClass',
])
def test_modify_in_place_adds_new_methods(obj_cls):

    class BaseClass:

        def __init__(self):
            pass

        def old_method(self):
            pass

    @modify_in_place
    class SubClass(BaseClass, MonkeyPatchedClass):

        def __init__(self):
            self._overridden_members['__init__'](self)

        def new_method(self):
            pass

    obj = cast(SubClass, eval(obj_cls)())
    assert set(obj._overridden_members.keys()) == {'__init__'}

    import inspect
    import operator
    all_members = set(map(operator.itemgetter(0), inspect.getmembers(obj.__class__)))
    assert 'old_method' in all_members
    assert 'new_method' in all_members
    assert '__init__' in all_members


@pytest.mark.parametrize('obj_cls,getter_overridden,setter_overridden', [
    ('Sub1', True, True),
    ('Sub2', False, True),
    ('Sub3', True, False),
    ('Sub4', True, True),
])
def test_modify_in_place_property_combinations(obj_cls, getter_overridden, setter_overridden):

    class BaseClass:

        def __init__(self):
            self.base_getter_called: bool = False
            self.base_setter_called: bool = False
            self.sub_getter_called: bool = False
            self.sub_setter_called: bool = False

        @property
        def prop(self) -> str:
            self.base_getter_called = True
            return 'base'

        @prop.setter
        def prop(self, _: str):
            self.base_setter_called = True

    class Medium1(BaseClass):
        pass

    class Medium2(BaseClass):
        pass

    class Medium3(BaseClass):
        pass

    class Medium4(BaseClass):
        pass

    @modify_in_place
    class Sub1(Medium1, MonkeyPatchedClass):
        """Class that defines properties correctly, so that both getter and setter can be used."""

        @Medium1.prop.setter
        def prop(self, new_val: str):
            self.sub_setter_called = True
            self._overridden_members['prop'].fset(self, new_val)

        @prop.getter
        def prop(self):
            self.sub_getter_called = True
            return self._overridden_members['prop'].fget(self)

    @modify_in_place
    class Sub2(Medium2, MonkeyPatchedClass):
        """Class that defines properties incorrectly, so only setter is usable."""

        @Medium2.prop.getter  # noqa: F811   flake8 actually catches this mistake
        def prop(self):
            self.sub_getter_called = True
            return self._overridden_members['prop'].fget(self)

        @Medium2.prop.setter  # noqa: F811   flake8 actually catches this mistake
        def prop(self, new_val: str):  # noqa: F811   flake8 actually catches this mistake
            self.sub_setter_called = True
            self._overridden_members['prop'].fset(self, new_val)

    @modify_in_place
    class Sub3(Medium3, MonkeyPatchedClass):
        """Class that defines properties incorrectly, so only getter is usable."""

        @Medium3.prop.setter  # noqa: F811   flake8 actually catches this mistake
        def prop(self, new_val: str):
            self.sub_setter_called = True
            self._overridden_members['prop'].fset(self, new_val)

        @Medium3.prop.getter  # noqa: F811   flake8 actually catches this mistake
        def prop(self):  # noqa: F811   flake8 actually catches this mistake
            self.sub_getter_called = True
            return self._overridden_members['prop'].fget(self)

    @modify_in_place
    class Sub4(Medium4, MonkeyPatchedClass):
        """Class that defines properties correctly, so both getter and setter are usable."""

        @Medium4.prop.getter
        def prop(self):
            self.sub_getter_called = True
            return self._overridden_members['prop'].fget(self)

        @prop.setter
        def prop(self, new_val: str):
            self.sub_setter_called = True
            self._overridden_members['prop'].fset(self, new_val)

    obj = eval(obj_cls)()
    assert obj.base_getter_called is False
    assert obj.sub_getter_called is False
    assert obj.base_setter_called is False
    assert obj.sub_setter_called is False
    _ = obj.prop
    assert obj.base_getter_called is True
    assert obj.sub_getter_called is getter_overridden
    assert obj.base_setter_called is False
    assert obj.sub_setter_called is False
    obj.prop = 'test'
    assert obj.base_setter_called is True
    assert obj.sub_setter_called is setter_overridden
