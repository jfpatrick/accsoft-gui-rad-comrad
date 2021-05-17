import pytest
import re
from unittest import mock
from typing import Type, Union
from qtpy.QtWidgets import QWidget
from pydm.widgets.base import PyDMWidget, PyDMChannel
from comrad.widgets.widget import CWidget, CContext


@pytest.fixture
def dummy_widget() -> Type[Union[CWidget, QWidget]]:
    class Dummy(QWidget, PyDMWidget):
        pass

    return Dummy


def test_cwidget_is_pydmwidget():

    class cl1(CWidget):
        pass

    assert cl1.mro()[1] == PyDMWidget
    assert CWidget == PyDMWidget


def test_pydmwidget_has_context_prop(qtbot, dummy_widget):
    widget = dummy_widget()
    assert hasattr(widget, 'context')
    assert hasattr(widget, 'context_changed')


@pytest.mark.parametrize('widget_defined_methods,channel_attr_values', [
    (['writeAccessChanged'], ['writeAccessChanged', None]),
    (['send_value_signal'], [None, 'send_value_signal']),
    (['writeAccessChanged', 'send_value_signal'], ['writeAccessChanged', 'send_value_signal']),
    ([], [None, None]),
])
def test_create_channel(qtbot, dummy_widget, widget_defined_methods, channel_attr_values):
    widget = dummy_widget()
    for attr in widget_defined_methods:
        setattr(widget, attr, mock.Mock())
    ctx = CContext()
    ch = widget.create_channel(channel_address='rda:///dev/prop', context=ctx)
    assert ch.context == ctx
    assert ch.address == 'rda:///dev/prop'
    assert ch.connection_slot == widget.connectionStateChanged
    assert ch.value_slot == widget.channelValueChanged
    assert ch.severity_slot is None
    assert ch.enum_strings_slot is None
    assert ch.unit_slot is None
    assert ch.prec_slot is None
    assert ch.upper_ctrl_limit_slot is None
    assert ch.lower_ctrl_limit_slot is None

    def get_widget_handle(idx: int):
        val = channel_attr_values[idx]
        if val is None:
            return None
        return getattr(widget, val)

    assert ch.write_access_slot == get_widget_handle(0)
    assert ch.value_signal == get_widget_handle(1)


@pytest.mark.parametrize('old_context,new_context,old_addresses,new_addresses,disconnected,connected', [
    (None, None, [], [], [], []),
    (None, CContext(), [], [], [], []),
    (CContext(), None, [], [], [], []),
    (CContext(), CContext(), [], [], [], []),
    (CContext(), CContext(selector='TEST.USER.ALL'), [], [], [], []),
    (None, None, ['rda:///dev/prop'], [], ['rda:///dev/prop'], []),
    (None, CContext(), ['rda:///dev/prop'], [], ['rda:///dev/prop'], []),
    (CContext(), None, ['rda:///dev/prop'], [], ['rda:///dev/prop'], []),
    (CContext(), CContext(), ['rda:///dev/prop'], [], ['rda:///dev/prop'], []),
    (CContext(), CContext(selector='TEST.USER.ALL'), ['rda:///dev/prop'], [], ['rda:///dev/prop'], []),
    (None, None, ['rda:///dev/prop'], ['rda:///dev/prop'], [], []),
    (None, CContext(), ['rda:///dev/prop'], ['rda:///dev/prop'], ['rda:///dev/prop'], ['rda:///dev/prop']),
    (CContext(), None, ['rda:///dev/prop'], ['rda:///dev/prop'], ['rda:///dev/prop'], ['rda:///dev/prop']),
    (CContext(), CContext(), ['rda:///dev/prop'], ['rda:///dev/prop'], [], []),
    (CContext(), CContext(selector='TEST.USER.ALL'), ['rda:///dev/prop'], ['rda:///dev/prop'], ['rda:///dev/prop'], ['rda:///dev/prop']),
    (None, None, [], ['rda:///dev/prop'], [], ['rda:///dev/prop']),
    (None, CContext(), [], ['rda:///dev/prop'], [], ['rda:///dev/prop']),
    (CContext(), None, [], ['rda:///dev/prop'], [], ['rda:///dev/prop']),
    (CContext(), CContext(), [], ['rda:///dev/prop'], [], ['rda:///dev/prop']),
    (CContext(), CContext(selector='TEST.USER.ALL'), [], ['rda:///dev/prop'], [], ['rda:///dev/prop']),
    (None, None, ['rda:///dev/prop'], ['rda:///dev/prop2'], ['rda:///dev/prop'], ['rda:///dev/prop2']),
    (None, CContext(), ['rda:///dev/prop'], ['rda:///dev/prop2'], ['rda:///dev/prop'], ['rda:///dev/prop2']),
    (CContext(), None, ['rda:///dev/prop'], ['rda:///dev/prop2'], ['rda:///dev/prop'], ['rda:///dev/prop2']),
    (CContext(), CContext(), ['rda:///dev/prop'], ['rda:///dev/prop2'], ['rda:///dev/prop'], ['rda:///dev/prop2']),
    (CContext(), CContext(selector='TEST.USER.ALL'), ['rda:///dev/prop'], ['rda:///dev/prop2'], ['rda:///dev/prop'], ['rda:///dev/prop2']),
    (None, None, ['rda:///dev/prop', 'rda:///dev/prop2'], ['rda:///dev/prop2', 'rda:///dev/prop3'], ['rda:///dev/prop'], ['rda:///dev/prop3']),
    (None, CContext(), ['rda:///dev/prop', 'rda:///dev/prop2'], ['rda:///dev/prop2', 'rda:///dev/prop3'], ['rda:///dev/prop', 'rda:///dev/prop2'], ['rda:///dev/prop2', 'rda:///dev/prop3']),
    (CContext(), None, ['rda:///dev/prop', 'rda:///dev/prop2'], ['rda:///dev/prop2', 'rda:///dev/prop3'], ['rda:///dev/prop', 'rda:///dev/prop2'], ['rda:///dev/prop2', 'rda:///dev/prop3']),
    (CContext(), CContext(), ['rda:///dev/prop', 'rda:///dev/prop2'], ['rda:///dev/prop2', 'rda:///dev/prop3'], ['rda:///dev/prop'], ['rda:///dev/prop3']),
    (CContext(), CContext(selector='TEST.USER.ALL'), ['rda:///dev/prop', 'rda:///dev/prop2'], ['rda:///dev/prop2', 'rda:///dev/prop3'], ['rda:///dev/prop', 'rda:///dev/prop2'], ['rda:///dev/prop2', 'rda:///dev/prop3']),
    (None, None, ['rda:///dev/prop', 'rda:///dev/prop2'], ['rda:///dev/prop2'], ['rda:///dev/prop'], []),
    (None, CContext(), ['rda:///dev/prop', 'rda:///dev/prop2'], ['rda:///dev/prop2'], ['rda:///dev/prop', 'rda:///dev/prop2'], ['rda:///dev/prop2']),
    (CContext(), None, ['rda:///dev/prop', 'rda:///dev/prop2'], ['rda:///dev/prop2'], ['rda:///dev/prop', 'rda:///dev/prop2'], ['rda:///dev/prop2']),
    (CContext(), CContext(), ['rda:///dev/prop', 'rda:///dev/prop2'], ['rda:///dev/prop2'], ['rda:///dev/prop'], []),
    (CContext(), CContext(selector='TEST.USER.ALL'), ['rda:///dev/prop', 'rda:///dev/prop2'], ['rda:///dev/prop2'], ['rda:///dev/prop', 'rda:///dev/prop2'], ['rda:///dev/prop2']),
    (None, None, ['rda:///dev/prop'], ['rda:///dev/prop', 'rda:///dev/prop2'], [], ['rda:///dev/prop2']),
    (None, CContext(), ['rda:///dev/prop'], ['rda:///dev/prop', 'rda:///dev/prop2'], ['rda:///dev/prop'], ['rda:///dev/prop', 'rda:///dev/prop2']),
    (CContext(), None, ['rda:///dev/prop'], ['rda:///dev/prop', 'rda:///dev/prop2'], ['rda:///dev/prop'], ['rda:///dev/prop', 'rda:///dev/prop2']),
    (CContext(), CContext(), ['rda:///dev/prop'], ['rda:///dev/prop', 'rda:///dev/prop2'], [], ['rda:///dev/prop2']),
    (CContext(), CContext(selector='TEST.USER.ALL'), ['rda:///dev/prop'], ['rda:///dev/prop', 'rda:///dev/prop2'], ['rda:///dev/prop'], ['rda:///dev/prop', 'rda:///dev/prop2']),
])
@mock.patch('pydm.widgets.channel.PyDMChannel.connect')
def test_reconnect_channel_connection(_, qtbot, dummy_widget, old_context, new_context, old_addresses, new_addresses, disconnected, connected):

    def create_ch(addr):
        ch = mock.MagicMock(spec=PyDMChannel)
        ch.address = addr
        return ch

    old_channels = [create_ch(addr) for addr in old_addresses]

    widget = dummy_widget()
    widget._channels = list(old_channels)  # Need a copy for references to not mutate silently
    widget._channel_ids = [ch.address for ch in widget._channels]
    widget._context_tracker = mock.MagicMock()
    widget._context_tracker.context_ready = True
    widget._local_context = old_context

    expected_channels = list(set(old_addresses).union(set(new_addresses)).difference(set(disconnected)).union(set(connected)))

    new_channels = []

    def create_new_ch(addr, ctx=None):
        nonlocal new_channels
        ch = create_ch(addr)
        new_channels.append(ch)
        return ch

    with mock.patch.object(widget, 'create_channel', side_effect=create_new_ch) as create_channel:
        widget.reconnect(new_ch_addresses=new_addresses, new_context=new_context)

        assert create_channel.call_count == len(connected)
        for ch in old_channels:
            if ch.address in disconnected:
                ch.disconnect.assert_called_once()
            else:
                ch.disconnect.assert_not_called()

        for ch in new_channels:
            if ch.address in connected:
                ch.connect.assert_called_once()
            else:
                ch.connect.assert_not_called()

        if expected_channels:
            assert {ch.address for ch in widget.channels()} == set(expected_channels)
        else:
            assert widget.channels() is None


@pytest.mark.parametrize('prev_ctx_none,next_ctx_none', [
    (True, True),
    (False, True),
    (True, False),
    (False, False),
])
@pytest.mark.parametrize('prev_wildcards,next_wildcards', [
    (None, None),
    ({}, {}),
    (None, {}),
    ({}, None),
    (None, {'key1': 'val1'}),
    ({'key1': 'val1'}, None),
    ({}, {'key1': 'val1'}),
    ({'key1': 'val1'}, {}),
    ({'key1': 'val1'}, {'key1': 'val1', 'key2': 'val2'}),
    ({'key1': 'val1', 'key2': 'val2'}, {'key1': 'val1'}),
    ({'key1': 'val1'}, {'key1': 'CHANGED'}),
    ({'key1': 'val1'}, {'key1': 'val1'}),
])
@pytest.mark.parametrize('prev_filter,next_filter', [
    (None, None),
    ({}, {}),
    (None, {}),
    ({}, None),
    (None, {'key1': 'val1'}),
    ({'key1': 'val1'}, None),
    ({}, {'key1': 'val1'}),
    ({'key1': 'val1'}, {}),
    ({'key1': 'val1'}, {'key1': 'val1', 'key2': 'val2'}),
    ({'key1': 'val1', 'key2': 'val2'}, {'key1': 'val1'}),
    ({'key1': 'val1'}, {'key1': 'CHANGED'}),
    ({'key1': 'val1'}, {'key1': 'val1'}),
])
@pytest.mark.parametrize('prev_sel,next_sel', [
    (None, None),
    ('', ''),
    (None, ''),
    ('', None),
    (None, 'TEST.USER.ALL'),
    ('TEST.USER.ALL', None),
    ('', 'TEST.USER.ALL'),
    ('TEST.USER.ALL', ''),
    ('TEST.USER.ALL', 'CHANGED'),
    ('TEST.USER.ALL', 'TEST.USER.ALL'),
])
def test_set_context_reconnects_if_relevant_params_changed(qtbot, dummy_widget, prev_wildcards, next_wildcards,
                                                           prev_ctx_none, next_ctx_none,
                                                           prev_filter, next_filter,
                                                           prev_sel, next_sel):
    widget = dummy_widget()
    ch = mock.MagicMock()
    ch.address = 'rda:///dev/prop'
    widget._channels = [ch]
    widget._channel_ids = [ch.address for ch in widget._channels]
    prev_ctx = None if prev_ctx_none else CContext(selector=prev_sel,
                                                   data_filters=prev_filter,
                                                   wildcards=prev_wildcards)
    new_ctx = None if next_ctx_none else CContext(selector=next_sel,
                                                  data_filters=next_filter,
                                                  wildcards=next_wildcards)
    try:
        prev_filter = prev_ctx.data_filters
    except AttributeError:
        prev_filter = None

    try:
        next_filter = new_ctx.data_filters
    except AttributeError:
        next_filter = None

    try:
        prev_sel = prev_ctx.selector
    except AttributeError:
        prev_sel = None

    try:
        next_sel = new_ctx.selector
    except AttributeError:
        next_sel = None

    should_reconnect = prev_filter != next_filter or prev_sel != next_sel

    widget._local_context = prev_ctx
    with mock.patch.object(widget, 'reconnect') as reconnect:
        widget.context = new_ctx
        if should_reconnect:
            reconnect.assert_called_once_with([widget.channel], new_ctx)
        else:
            reconnect.assert_not_called()


@mock.patch('pydm.widgets.base.PyDMWidget.context', new_callable=mock.PropertyMock)
def test_context_changed_calls_context_setter(context, qtbot, dummy_widget):
    widget = dummy_widget()
    ctx = CContext()
    with mock.patch('comrad.widgets.widget.find_context_provider') as find_context_provider:
        find_context_provider.return_value.get_context_view.return_value = ctx
        widget.context_changed()
        context.assert_called_with(ctx)


# @pytest.mark.parametrize('initial_ctx,is_designer,use_window_ctx', [
#     (None, True, False),
#     (None, False, True),
#     (mock.MagicMock(), True, False),
#     (mock.MagicMock(), False, False),
# ])
# @mock.patch('comrad.data.context.is_qt_designer')
# def test_uses_window_context_when_no_context_provided(is_qt_designer, qtbot, dummy_widget, initial_ctx, is_designer, use_window_ctx):
#     is_qt_designer.return_value = is_designer
#     CApplication.instance().main_window.context_ready = False
#     widget = dummy_widget(init_channel='rda:///dev/prop')
#     widget.context = initial_ctx
#     CApplication.instance().main_window.context_ready = True
#     with mock.patch.object(widget, 'reconnect') as reconnect:
#         qtbot.add_widget(widget)
#
#         if use_window_ctx:
#             reconnect.assert_called_with('rda:///dev/prop', CApplication.instance().main_window.window_context)
#         else:
#             reconnect.assert_called_with('rda:///dev/prop', initial_ctx)


@pytest.mark.parametrize('set_object_name,regex', [
    (True, r'<[\w\.<>]*Dummy at 0x[\d\w]+ \(test-widget\)>'),
    (False, r'<[\w\.<>]*Dummy at 0x[\d\w]+>'),
])
def test_repr_injects_object_name(qtbot, dummy_widget, set_object_name, regex):
    widget = dummy_widget()
    if set_object_name:
        widget.setObjectName('test-widget')
    assert re.search(regex, repr(widget)) is not None


@pytest.mark.parametrize('old_addr,new_addr,should_reconnect', [
    (None, None, False),
    ('', None, False),
    (None, '', False),
    ('', '', False),
    ('protocol://channel', None, True),
    ('protocol://channel', '', True),
    (None, 'protocol://channel', True),
    ('', 'protocol://channel', True),
    ('protocol://channel', 'protocol://channel', False),
])
@mock.patch('comrad.widgets.widget.find_context_provider')
def test_channel_setter_reconnects_if_changed(find_context_provider, qtbot, dummy_widget, old_addr, new_addr, should_reconnect):
    find_context_provider.return_value.context_ready = True
    widget = dummy_widget(init_channel=old_addr)
    with mock.patch.object(widget, 'reconnect') as reconnect:
        widget.channel = new_addr
        if should_reconnect:
            reconnect.assert_called_once_with([new_addr] if new_addr else [], widget.context)
        else:
            reconnect.assert_not_called()
