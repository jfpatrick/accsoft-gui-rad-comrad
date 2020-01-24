import pytest
from unittest import mock
from typing import List
from logging import LogRecord
from _pytest.logging import LogCaptureFixture
from qtpy.QtWidgets import QWidget
from comrad.deprecations import deprecated_args, deprecated_parent_prop
from comrad.widgets.mixins import CInitializedMixin


@pytest.fixture
def deprecated_fn():

    @deprecated_args(a2='b2', a3='b3')
    def fn(a1, b2, b3, a4):
        return a1, b2, b3, a4

    return fn


@pytest.mark.parametrize(
    'args,'
    'kwargs,'
    'expected_warnings', [
        ([], {'a1': 1, 'b2': 2, 'b3': 3, 'a4': 4}, []),
        ([], {'a1': 1, 'a2': 2, 'a3': 3, 'a4': 4}, ['Keyword-argument "a2" in function "fn" is deprecated, use "b2".', 'Keyword-argument "a3" in function "fn" is deprecated, use "b3".']),
        ([], {'a1': 1, 'a2': 2, 'b3': 3, 'a4': 4}, ['Keyword-argument "a2" in function "fn" is deprecated, use "b2".']),
        ([], {'a1': 1, 'b2': 2, 'a3': 3, 'a4': 4}, ['Keyword-argument "a3" in function "fn" is deprecated, use "b3".']),
        ([1], {'b2': 2, 'b3': 3, 'a4': 4}, []),
        ([1], {'a2': 2, 'a3': 3, 'a4': 4}, ['Keyword-argument "a2" in function "fn" is deprecated, use "b2".', 'Keyword-argument "a3" in function "fn" is deprecated, use "b3".']),
        ([1], {'a2': 2, 'b3': 3, 'a4': 4}, ['Keyword-argument "a2" in function "fn" is deprecated, use "b2".']),
        ([1], {'b2': 2, 'a3': 3, 'a4': 4}, ['Keyword-argument "a3" in function "fn" is deprecated, use "b3".']),
        ([1, 2], {'b3': 3, 'a4': 4}, []),
        ([1, 2], {'a3': 3, 'a4': 4}, ['Keyword-argument "a3" in function "fn" is deprecated, use "b3".']),
        ([1, 2, 3], {'a4': 4}, []),
        ((1, 2, 3, 4), {}, []),
    ])
def test_fn_arg_deprecations(caplog: LogCaptureFixture, args, kwargs, expected_warnings, deprecated_fn):
    res1, res2, res3, res4 = deprecated_fn(*args, **kwargs)
    assert res1 == 1
    assert res2 == 2
    assert res3 == 3
    assert res4 == 4
    warning_records: List[LogRecord] = caplog.records
    actual_warnings = [r.msg for r in warning_records]
    assert actual_warnings == expected_warnings


def test_fn_arg_deprecation_exc(deprecated_fn):

    with pytest.raises(TypeError, match='"fn" received both "a2" and "b2"'):
        deprecated_fn(a1=1, a2=2, b2=2, a3=3)


@pytest.mark.parametrize('superclasses', [
    [QWidget],
    [CInitializedMixin],
    [object],
])
def test_prop_deprecation_no_mixin(qtbot, superclasses):
    _ = qtbot
    import logging
    from qtpy.QtCore import Property
    with mock.patch('pydm.utilities.is_qt_designer', return_value=False):
        with pytest.raises(TypeError, match='This decorator is intended to be used with CInitializedMixin on QWidget subclasses. MyWidget is not recognized as one.'):
            class MyWidget(*superclasses):

                @Property(str)
                @deprecated_parent_prop(logging.getLogger())
                def test_prop(self):
                    return ''

            obj = MyWidget()
            _ = obj.test_prop


@pytest.mark.parametrize('in_designer,initialized,should_issue', [
    (True, True, False),
    (False, True, True),
    (True, False, False),
    (False, False, False),
])
@pytest.mark.parametrize('obj_name,expected_warning', [
    ('objName', f'test_prop property is disabled in ComRAD (found in objName)'),
    (None, f'test_prop property is disabled in ComRAD (found in unidentified MyWidget)'),
])
def test_prop_deprecation_displays_warning(qtbot, caplog: LogCaptureFixture, obj_name, in_designer, initialized, should_issue, expected_warning):
    _ = qtbot
    import logging
    from qtpy.QtCore import Property
    with mock.patch('pydm.utilities.is_qt_designer', return_value=in_designer):
        class MyWidget(QWidget, CInitializedMixin):

            def __init__(self):
                QWidget.__init__(self)
                CInitializedMixin.__init__(self)
                self._widget_initialized = initialized

            def objectName(self):
                return obj_name

            @Property(str)
            @deprecated_parent_prop(logging.getLogger())
            def test_prop(self):
                return ''

        obj = MyWidget()
        _ = obj.test_prop
        if should_issue:
            assert len(caplog.records) == 1
            warning_records: List[LogRecord] = caplog.records
            actual_warning = warning_records[0].msg
            assert actual_warning == expected_warning
        else:
            assert len(caplog.records) == 0