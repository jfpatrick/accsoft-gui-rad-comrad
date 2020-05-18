import pytest
from unittest import mock
from qtpy.QtWidgets import QWidget, QVBoxLayout, QApplication, QMainWindow
from qtpy.QtCore import Signal
from comrad import CContextFrame, CContext, PyDMWidget


@pytest.fixture
def compliant_child():

    class ChildWidget(QWidget, PyDMWidget):

        def context_changed(self):
            pass

    return ChildWidget


@pytest.fixture
def real_window() -> QMainWindow:

    class WindowSubclass(QMainWindow):
        contextUpdated = Signal()

        def get_context_view(self):
            return QApplication.instance().main_window.window_context

    temp_window = WindowSubclass()
    temp_window.window_context = QApplication.instance().main_window.window_context
    temp_window.window_context.selectorChanged.connect(temp_window.contextUpdated.emit)
    temp_window.window_context.dataFiltersChanged.connect(temp_window.contextUpdated.emit)
    temp_window.window_context.wildcardsChanged.connect(temp_window.contextUpdated.emit)
    yield temp_window


@pytest.mark.parametrize('attr,ctx_attr,val,expected_val', [
    ('selector', 'selector', 'TEST.USER.ALL', 'TEST.USER.ALL'),
    ('selector', 'selector', '', None),
    ('selector', 'selector', None, None),
    # TODO: Do the same for wildcards and data_filters, when properties are implemented
])
def test_context_frame_properties_update_inner_context(qtbot, attr, ctx_attr, val, expected_val):
    widget = CContextFrame()
    qtbot.addWidget(widget)
    assert getattr(widget, attr) == getattr(widget._local_context, ctx_attr)
    setattr(widget, attr, val)
    assert getattr(widget._local_context, ctx_attr) == expected_val


@pytest.mark.parametrize('attr,slot,val', [
    ('wildcards', 'updateWildcards', {'key1': 'val1'}),
    ('data_filters', 'updateDataFilters', {'key1': 'val1'}),
    ('selector', 'updateSelector', 'TEST.USER.ALL'),
])
def test_update_context_attrs_fires_signal(qtbot, attr, slot, val):
    widget = CContextFrame()
    qtbot.addWidget(widget)
    assert getattr(widget._local_context, attr) is None
    with qtbot.wait_signal(widget.contextUpdated) as blocker:
        getattr(widget, slot)(val)
    assert blocker.args == []
    assert widget.get_context_view() == CContext(**{attr: val})


@pytest.mark.parametrize('show', [True, False])
def test_connects_context_signal_to_new_children(qtbot, compliant_child, show):
    widget = CContextFrame()
    qtbot.addWidget(widget)
    child = compliant_child()
    layout = QVBoxLayout()
    widget.setLayout(layout)
    assert widget.receivers(widget.contextUpdated) == 0
    layout.addWidget(child)

    # Connection happens on "ShowToParent" or "ParentChange" event, so it needs to be shown
    assert widget.receivers(widget.contextUpdated) == 1
    if show:
        widget.show()
        assert widget.receivers(widget.contextUpdated) == 1

    # Removing widget should disconnect the signals
    child.setParent(None)
    assert widget.receivers(widget.contextUpdated) == 0


def test_does_not_connect_context_signal_to_unsupported_children(qtbot):
    widget = CContextFrame()
    qtbot.addWidget(widget)
    child = QWidget()
    widget.setLayout(QVBoxLayout())
    assert widget.receivers(widget.contextUpdated) == 0
    widget.layout().addWidget(child)

    # Connection happens on "polish" event, so it needs to be shown
    assert widget.receivers(widget.contextUpdated) == 0
    widget.show()
    assert widget.receivers(widget.contextUpdated) == 0
    child.setParent(None)
    assert widget.receivers(widget.contextUpdated) == 0


@pytest.mark.parametrize('is_designer', [True, False])
@mock.patch('comrad.data.context.is_qt_designer')
def test_connects_to_window_context_when_not_nested_inside_another_frame(is_qt_designer, is_designer, real_window, qtbot):
    is_qt_designer.return_value = is_designer
    widget = CContextFrame(real_window)
    qtbot.addWidget(real_window)
    real_window.setCentralWidget(widget)
    assert real_window.receivers(real_window.contextUpdated) == 0
    real_window.show()
    assert real_window.receivers(real_window.contextUpdated) == 1


@pytest.mark.parametrize('is_designer', [True, False])
@mock.patch('comrad.data.context.is_qt_designer')
def test_does_not_connect_to_window_context_when_nested_inside_another_frame(is_qt_designer, is_designer, real_window, qtbot):
    is_qt_designer.return_value = is_designer
    intermediate_frame = CContextFrame(real_window)
    qtbot.addWidget(real_window)
    real_window.setCentralWidget(intermediate_frame)
    leaf_frame = CContextFrame(intermediate_frame)
    intermediate_frame.setLayout(QVBoxLayout())
    intermediate_frame.layout().addWidget(leaf_frame)
    real_window.show()
    assert real_window.receivers(real_window.contextUpdated) == 1
    real_window.contextUpdated.disconnect(intermediate_frame.context_changed)
    # Proves that it was intermediate frame connected, not leaf
    assert real_window.receivers(real_window.contextUpdated) == 0


def test_nested_context_propagation_inside_parent_frame(qtbot):
    intermediate_frame = CContextFrame(context=CContext(selector='INT', wildcards={'INT': 'INT'}))
    qtbot.addWidget(intermediate_frame)
    leaf_frame = CContextFrame(intermediate_frame, context=CContext(wildcards={'LEAF': 'LEAF'}))
    intermediate_frame.setLayout(QVBoxLayout())
    intermediate_frame.layout().addWidget(leaf_frame)

    with qtbot.wait_signal(leaf_frame.contextUpdated) as blocker:
        intermediate_frame.show()
    assert blocker.args == []
    assert leaf_frame.get_context_view() == CContext(selector='INT', wildcards={'INT': 'INT', 'LEAF': 'LEAF'})

    with qtbot.wait_signal(leaf_frame.contextUpdated) as blocker:
        intermediate_frame.updateSelector('CHANGED')
    assert blocker.args == []
    assert leaf_frame.get_context_view() == CContext(selector='CHANGED', wildcards={'INT': 'INT', 'LEAF': 'LEAF'})

    with qtbot.wait_signal(leaf_frame.contextUpdated) as blocker:
        leaf_frame.updateWildcards({'LEAF2': 'CHANGED'})
    assert blocker.args == []
    assert leaf_frame.get_context_view() == CContext(selector='CHANGED', wildcards={'INT': 'INT', 'LEAF2': 'CHANGED'})


@mock.patch('comrad.data.context.is_qt_designer', return_value=False)
def test_nested_context_propagation_inside_main_window(_, qtbot, real_window):
    real_window.window_context.selector = 'WINDOW'
    real_window.window_context.wildcards = {'WINDOW': 'val1'}
    qtbot.addWidget(real_window)
    widget = CContextFrame(real_window, context=CContext(wildcards={'FRAME': 'val2'}))
    real_window.setCentralWidget(widget)
    real_window.show()
    expected_ctx = CContext(selector='WINDOW', wildcards={'WINDOW': 'val1', 'FRAME': 'val2'})
    assert widget.get_context_view() == expected_ctx

    with qtbot.wait_signal(widget.contextUpdated) as blocker:
        real_window.window_context.selector = 'CHANGED'
    assert blocker.args == []
    assert widget.get_context_view() == CContext(selector='CHANGED', wildcards={'WINDOW': 'val1', 'FRAME': 'val2'})

    with qtbot.wait_signal(widget.contextUpdated) as blocker:
        widget.updateWildcards({'FRAME': 'CHANGED'})
    assert blocker.args == []
    assert widget.get_context_view() == CContext(selector='CHANGED', wildcards={'WINDOW': 'val1', 'FRAME': 'CHANGED'})


def test_context_view_without_hierarchy(qtbot, real_window):
    qtbot.addWidget(real_window)
    real_window.window_context.selector = 'WINDOW'
    real_window.show()
    ctx = CContext()
    dangling_widget = CContextFrame(context=ctx)
    widget_in_hierarchy = CContextFrame(context=ctx)
    real_window.setCentralWidget(widget_in_hierarchy)
    assert widget_in_hierarchy.get_context_view() == CContext(selector='WINDOW')
    assert dangling_widget.get_context_view() == CContext(selector=None)
