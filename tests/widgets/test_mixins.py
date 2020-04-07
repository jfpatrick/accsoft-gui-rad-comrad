import pytest
from pytestqt.qtbot import QtBot
from unittest import mock
from typing import Type, Union, cast, Dict, Tuple, Any
from qtpy.QtWidgets import QWidget
from pydm.widgets.base import PyDMWidget
from comrad.widgets.mixins import CRequestingMixin
from comrad.data.channel import CChannel


def make_mixin_class(mixin_type: Type) -> Type[QWidget]:
    """
    Creates a subclass widget type that is mixed-in with a given addition.
    """
    class MixinSubclass(mixin_type, QWidget, PyDMWidget):  # type: ignore

        def __init__(self, *args, **kwargs):
            pydm_kwargs = {}
            if 'init_channel' in kwargs:
                pydm_kwargs['init_channel'] = kwargs.pop('init_channel')
            mixin_type.__init__(self, **kwargs)
            QWidget.__init__(self, *args)
            PyDMWidget.__init__(self, **pydm_kwargs)

    return MixinSubclass


@pytest.mark.parametrize('kwargs,expected_value', [
    ({'connect_value_slot': True}, True),
    ({'connect_value_slot': False}, False),
    ({}, True),
])
def test_requesting_mixin_init(qtbot: QtBot, kwargs, expected_value):
    mixin_class = make_mixin_class(CRequestingMixin)
    obj = cast(Union[CRequestingMixin, QWidget], mixin_class(**kwargs))
    qtbot.addWidget(obj)
    assert obj.connect_value_slot == expected_value


@pytest.mark.parametrize('initial_channel,connect_slot,slot_should_be_none', [
    (None, True, False),
    (None, False, True),
    ('rda:///initial/channel', True, False),
    ('rda:///initial/channel', False, True),
])
@mock.patch('pydm.data_plugins.plugin_for_address')  # Need both here, as both participate on comrad and pydm level
def test_requesting_mixin_assigns_request_signal_slot_to_channel(_, qtbot: QtBot, initial_channel, connect_slot, slot_should_be_none):
    mixin_class = make_mixin_class(CRequestingMixin)
    obj = cast(Union[CRequestingMixin, QWidget, PyDMWidget], mixin_class(init_channel=initial_channel))
    qtbot.addWidget(obj)
    obj.show()  # type: ignore
    obj.connect_value_slot = connect_slot
    obj._context_tracker = mock.MagicMock()  # type: ignore
    obj._context_tracker.context_ready = True  # type: ignore
    with mock.patch('pydm.widgets.channel.PyDMChannel.connect') as connect:
        obj.channel = 'rda:///some/other'  # type: ignore
        assert connect.call_count == 1
        assert len(obj.channels()) == 1  # type: ignore  # mypy does not resolve PyDMWidget here
        ch = cast(CChannel, obj.channels()[0])  # type: ignore  # mypy does not resolve PyDMWidget here
        if slot_should_be_none:
            assert ch.value_slot is None
            assert ch.request_slot == obj._on_request_fulfilled  # type: ignore  # mypy does not resolve PyDMWidget here
            # For some reason we can't compare signals directly, just their signal property
            assert ch.request_signal.signal == obj.request_signal.signal  # type: ignore
        else:
            assert ch.value_slot == obj.channelValueChanged  # type: ignore  # mypy does not resolve PyDMWidget here
            assert ch.request_slot is None
            # For some reason we can't compare signals directly, just their signal property
            assert ch.request_signal is None


def test_requesting_mixin_skips_channel_setter(qtbot: QtBot):
    mixin_class = make_mixin_class(CRequestingMixin)
    obj = cast(Union[CRequestingMixin, QWidget], mixin_class(init_channel='test/channel'))
    qtbot.addWidget(obj)
    with mock.patch.object(obj, 'request_signal', new_callable=mock.PropertyMock()) as request_signal:
        obj.channel = 'test/channel'  # type: ignore
        request_signal.assert_not_called()


def test_requesting_mixin_channels_are_reconnected_on_value_slot_config_change(qtbot: QtBot):
    mixin_class = make_mixin_class(CRequestingMixin)
    widget = cast(Union[CRequestingMixin, QWidget, PyDMWidget], mixin_class())
    qtbot.addWidget(widget)
    widget.show()  # type: ignore
    widget._context_tracker = mock.MagicMock()  # type: ignore
    widget._context_tracker.context_ready = True  # type: ignore
    with mock.patch('pydm.widgets.channel.PyDMChannel.connect') as connect:
        widget.channel = 'some/channel'  # type: ignore
        assert connect.call_count == 1
        assert len(widget.channels()) == 1  # type: ignore  # mypy does not resolve PyDMWidget here
        prev_ch = cast(CChannel, widget.channels()[0])  # type: ignore  # mypy does not resolve PyDMWidget here
        assert prev_ch.address == 'some/channel'
        connect.reset_mock()
        assert connect.call_count == 0
        with mock.patch.object(prev_ch, 'disconnect') as disconnect:
            widget.connect_value_slot = not widget.connect_value_slot
            disconnect.assert_called_once()
            assert connect.call_count == 1
            assert len(widget.channels()) == 1  # type: ignore  # mypy does not resolve PyDMWidget here
            new_ch = cast(CChannel, widget.channels()[0])  # type: ignore  # mypy does not resolve PyDMWidget here
            assert new_ch.address == 'some/channel'
            assert prev_ch != new_ch


@pytest.mark.parametrize('uuid, should_handle', [
    ('my-uuid', True),
    ('', True),
    (None, True),
    ('unknown', False),
])
def test_requesting_mixin_filters_request_slot_value(qtbot: QtBot, uuid, should_handle):
    mixin_class = make_mixin_class(CRequestingMixin)
    obj = cast(Union[CRequestingMixin, QWidget], mixin_class(init_channel='test/channel'))
    cast(QWidget, obj).setObjectName('my-uuid')
    qtbot.addWidget(obj)
    with mock.patch.object(obj, 'channelValueChanged') as channelValueChanged:
        some_data: Tuple[str, Dict[str, Any]] = ('blahblah', {})
        obj._on_request_fulfilled(some_data, uuid)
        if should_handle:
            channelValueChanged.assert_called_with(some_data)
        else:
            channelValueChanged.assert_not_called()
