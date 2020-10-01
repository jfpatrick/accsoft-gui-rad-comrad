import pytest
import logging
import functools
import numpy as np
from typing import cast, Type, Optional, List
from logging import LogRecord
from pytestqt.qtbot import QtBot
from _pytest.logging import LogCaptureFixture
from unittest import mock
from qtpy.QtCore import QVariant, QObject, Signal
from comrad.data import channel
from comrad.data_plugins import CCommonDataConnection, CChannelData, CDataConnection, CDataPlugin


@pytest.fixture
def signal_factory():

    def make_obj(overloads):
        class Obj(QObject):
            sig1 = Signal(*overloads)

        return Obj()

    return make_obj


@pytest.fixture
def make_common_conn():

    class TestCommonConnection(CCommonDataConnection):

        def get(self, callback):
            callback(1)

        def set(self, value):
            pass

        def subscribe(self, callback):
            callback(1)

        def unsubscribe(self):
            pass

        def process_incoming_value(self, *args, **kwargs):
            try:
                val = args[0]
            except IndexError:
                val = None
            return CChannelData(value=val, meta_info={})

    return TestCommonConnection


def make_plugin():

    class TestPlugin(CDataPlugin):
        pass

    return TestPlugin


def assert_signal_has_receivers(count: int, sig: Signal, owner: QObject, signal_exists: bool, overload: Optional[Type] = None):
    if signal_exists:
        if overload is None:
            assert owner.receivers(sig) == count
        else:
            assert owner.receivers(sig[overload]) == count
    else:
        assert sig is None


def test_base_add_listener_connects_extra_signal_types(qtbot: QtBot):
    ch = cast(channel.CChannel, channel.PyDMChannel(address='device/property'))
    value_slot = mock.Mock()
    ch.value_slot = value_slot
    conn = CDataConnection(ch, ch.address)
    # Assuming add_listener was not called in the constructor
    assert conn.receivers(conn.new_value_signal) == 0
    conn.add_listener(ch)  # This should have connected default signal overload that is of CChannelData type
    assert conn.receivers(conn.new_value_signal) == 1
    value_slot.assert_not_called()
    dummy_payload = CChannelData(value=None, meta_info={})
    with qtbot.wait_signal(conn.new_value_signal) as blocker:
        conn.new_value_signal.emit(dummy_payload)  # Verify that CChannelData can indeed be transferred
    assert blocker.args == [dummy_payload]
    value_slot.assert_called_once_with(dummy_payload)


@pytest.mark.parametrize('value_signal_exists,signal_overloads,connected_signal_overloads', [
    (True, {str}, {str}),
    (True, {str, int}, {str, int}),
    (True, {str, bool, int, float, QVariant, np.ndarray}, {str, bool, int, float, QVariant, np.ndarray}),
    (True, {str, bool, int, float, QObject}, {str, bool, int, float}),
    (False, {str, bool, int, float, QVariant, np.ndarray}, {}),
])
def test_base_add_listener_connects_write_signals(qtbot: QtBot, value_signal_exists, signal_overloads, connected_signal_overloads, signal_factory):
    signal_owner = signal_factory([[t] for t in signal_overloads])
    ch = cast(channel.CChannel, channel.PyDMChannel(address='device/property'))
    ch.value_signal = signal_owner.sig1 if value_signal_exists else None

    assert_has_receivers = functools.partial(assert_signal_has_receivers,
                                             owner=signal_owner,
                                             signal_exists=value_signal_exists,
                                             sig=ch.value_signal)

    assert_has_receivers(0)
    for data_type in signal_overloads:
        assert_has_receivers(0, overload=data_type)
    conn = CDataConnection(ch, ch.address)
    # Assuming add_listener was not called in the constructor
    assert_has_receivers(0)
    for data_type in signal_overloads:
        assert_has_receivers(0, overload=data_type)

    write_value = mock.Mock()
    conn.write_value = write_value
    conn.add_listener(ch)  # This should have connected value_signal to write_value
    # Do not check default overload here, because if the unsupported overload comes first, it will produce receivers == 0
    for data_type in connected_signal_overloads:
        assert_has_receivers(1, overload=data_type)
    for data_type in signal_overloads.difference(connected_signal_overloads):
        assert_has_receivers(0, overload=data_type)
    write_value.assert_not_called()
    if not value_signal_exists:
        # Create a dummy signal just to test that sending over it does not do anything
        ch.value_signal = signal_owner.sig1

    def make_payload(data_type):
        try:
            return data_type()
        except TypeError:
            return data_type([1, 1])  # Special case for np.ndarray

    write_value.assert_not_called()

    for data_type in connected_signal_overloads:
        dummy_payload = make_payload(data_type)
        write_value.reset_mock()
        with qtbot.wait_signal(ch.value_signal[data_type]) as blocker:
            ch.value_signal[data_type].emit(dummy_payload)  # Verify that CChannelData can indeed be transferred
        assert blocker.args == [dummy_payload]
        write_value.assert_called_once_with(dummy_payload)
    for data_type in signal_overloads.difference(connected_signal_overloads):
        dummy_payload = make_payload(data_type)
        write_value.reset_mock()
        ch.value_signal[data_type].emit(dummy_payload)  # Verify that CChannelData cannot be transferred
        write_value.assert_not_called()


@pytest.mark.parametrize('read_only,write_access', [
    (True, False),
    (False, True),
])
@mock.patch('comrad.data_plugins._conn.pydm_read_only')
def test_base_add_listener_emits_write_signal(pydm_read_only, qtbot: QtBot, read_only, write_access):
    pydm_read_only.return_value = read_only
    ch = channel.PyDMChannel(address='device/property')
    conn = CDataConnection(ch, ch.address)
    with qtbot.wait_signal(conn.write_access_signal) as blocker:
        conn.add_listener(ch)
    assert blocker.args == [write_access]
    ch2 = channel.PyDMChannel(address='device/property')
    with qtbot.wait_signal(conn.write_access_signal) as blocker:
        conn.add_listener(ch2)
    assert blocker.args == [write_access]


def test_base_connection_status(qtbot: QtBot):
    # Checks that add_listener forcefully emits an existing connection status
    # Checks that any status change propagates to all existing listeners
    ch1 = channel.PyDMChannel(address='device/property')
    connection_slot1 = mock.Mock()
    ch1.connection_slot = connection_slot1
    conn = CDataConnection(ch1, ch1.address, 'rda')
    assert conn.receivers(conn.connection_state_signal) == 0
    connection_slot1.assert_not_called()
    with qtbot.wait_signal(conn.connection_state_signal) as blocker:
        conn.add_listener(ch1)
    assert blocker.args == [False]
    connection_slot1.assert_called_once_with(False)
    assert conn.receivers(conn.connection_state_signal) == 1
    connection_slot1.reset_mock()
    with qtbot.wait_signal(conn.connection_state_signal) as blocker:
        conn.connected = True
    assert blocker.args == [True]
    connection_slot1.assert_called_once_with(True)
    connection_slot1.reset_mock()
    ch2 = channel.PyDMChannel(address='device/property')
    connection_slot2 = mock.Mock()
    ch2.connection_slot = connection_slot2
    with qtbot.wait_signal(conn.connection_state_signal) as blocker:
        conn.add_listener(ch2)
    assert blocker.args == [True]
    connection_slot1.assert_called_once_with(True)
    connection_slot2.assert_called_once_with(True)
    connection_slot1.reset_mock()
    connection_slot2.reset_mock()
    with qtbot.wait_signal(conn.connection_state_signal) as blocker:
        conn.connected = False
    assert blocker.args == [False]
    connection_slot1.assert_called_once_with(False)
    connection_slot2.assert_called_once_with(False)


@mock.patch('comrad.data_plugins.CDataConnection.read_only', new_callable=mock.PropertyMock)
def test_base_picky_read_only_connection(read_only, qtbot: QtBot):
    read_only.__get__ = lambda self, conn, _: conn.address == 'device/read-only'

    ch1 = channel.PyDMChannel(address='device/read-write')
    ch2 = channel.PyDMChannel(address='device/read-only')
    write_access_slot1 = mock.Mock()
    ch1.write_access_slot = write_access_slot1
    write_access_slot2 = mock.Mock()
    ch2.write_access_slot = write_access_slot2
    conn1 = CDataConnection(ch1, ch1.address)
    conn2 = CDataConnection(ch2, ch2.address)
    assert conn1.receivers(conn1.write_access_signal) == 0
    assert conn2.receivers(conn2.write_access_signal) == 0
    write_access_slot1.assert_not_called()
    write_access_slot2.assert_not_called()
    with qtbot.wait_signal(conn1.write_access_signal) as blocker:
        conn1.add_listener(ch1)
    assert blocker.args == [True]
    write_access_slot1.assert_called_once_with(True)
    write_access_slot2.assert_not_called()
    write_access_slot1.reset_mock()
    assert conn1.receivers(conn1.write_access_signal) == 1
    assert conn2.receivers(conn2.write_access_signal) == 0
    with qtbot.wait_signal(conn2.write_access_signal) as blocker:
        conn2.add_listener(ch2)
    assert blocker.args == [False]
    write_access_slot1.assert_not_called()
    write_access_slot2.assert_called_once_with(False)
    assert conn1.receivers(conn1.write_access_signal) == 1
    assert conn2.receivers(conn2.write_access_signal) == 1


@mock.patch('comrad.data_plugins.CDataConnection.read_only', new_callable=mock.PropertyMock)
def test_base_listeners_with_incompatible_addresses_do_not_impact_read_only(read_only, qtbot: QtBot):
    read_only.__get__ = lambda self, conn, _: conn.address == 'device/read-only'

    ch1 = channel.PyDMChannel(address='device/read-write')
    ch2 = channel.PyDMChannel(address='device/read-only')
    write_access_slot1 = mock.Mock()
    ch1.write_access_slot = write_access_slot1
    write_access_slot2 = mock.Mock()
    ch2.write_access_slot = write_access_slot2
    conn1 = CDataConnection(ch1, ch1.address)
    assert conn1.receivers(conn1.write_access_signal) == 0
    write_access_slot1.assert_not_called()
    write_access_slot2.assert_not_called()
    with qtbot.wait_signal(conn1.write_access_signal) as blocker:
        conn1.add_listener(ch1)
    assert blocker.args == [True]
    write_access_slot1.assert_called_once_with(True)
    write_access_slot2.assert_not_called()
    write_access_slot1.reset_mock()
    assert conn1.receivers(conn1.write_access_signal) == 1
    with qtbot.wait_signal(conn1.write_access_signal) as blocker:
        # This should neve happen, because ch2 has a different address from what conn1 is configured 2,
        # so in theory it should trigger creation of a new connection and added there. But in case
        # this assumption got broken, test that incompatible channel address does not impact the
        # original connection, and its native channels do not suffer a mistake.
        conn1.add_listener(ch2)
    assert blocker.args == [True]
    write_access_slot1.assert_called_once_with(True)
    write_access_slot2.assert_called_once_with(True)
    assert conn1.receivers(conn1.write_access_signal) == 2


@pytest.mark.parametrize('listener_added,signal_received', [
    (True, True),
    (False, False),
])
def test_base_close_issues_disconnected_signal(qtbot: QtBot, listener_added, signal_received):
    ch = channel.PyDMChannel(address='device/property')
    connection_slot = mock.Mock()
    ch.connection_slot = connection_slot
    conn = CDataConnection(ch, ch.address)
    if listener_added:
        with qtbot.wait_signal(conn.connection_state_signal):
            conn.add_listener(ch)

    if signal_received:
        connection_slot.assert_called_once_with(False)
    else:
        connection_slot.assert_not_called()

    conn.connected = True

    connection_slot.reset_mock()
    with qtbot.wait_signal(conn.connection_state_signal):
        conn.close()
    if signal_received:
        connection_slot.assert_called_once_with(False)
    else:
        connection_slot.assert_not_called()


@pytest.mark.parametrize('destroying', [True, False])
@pytest.mark.parametrize('value_signal_exists,signal_overloads', [
    (True, [str]),
    (True, [str, int]),
    (True, [str, bool, int, float, QVariant, np.ndarray]),
    (True, [str, bool, int, float, QObject]),
    (False, [str, bool, int, float, QVariant, np.ndarray]),
])
def test_remove_listener_disconnects_slots(qtbot: QtBot, value_signal_exists, signal_overloads, destroying, signal_factory):
    signal_owner = signal_factory([[t] for t in signal_overloads])
    ch = cast(channel.CChannel, channel.PyDMChannel(address='device/property'))
    ch.value_signal = signal_owner.sig1 if value_signal_exists else None

    assert_has_receivers = functools.partial(assert_signal_has_receivers,
                                             owner=signal_owner,
                                             signal_exists=value_signal_exists,
                                             sig=ch.value_signal)

    conn = CDataConnection(ch, ch.address)
    write_value = mock.Mock()
    conn.write_value = write_value
    assert conn.listener_count == 0
    conn.add_listener(ch)  # This should have connected value_signal to write_value
    # Do not check default overload here, because if the unsupported overload comes first, it will produce receivers == 0
    assert_has_receivers(1)
    for data_type in signal_overloads:
        assert_has_receivers(0 if data_type == QObject else 1, overload=data_type)
    write_value.assert_not_called()
    signal_owner.sig1[str].emit('test')
    if value_signal_exists:
        write_value.assert_called_once_with('test')
    else:
        write_value.assert_not_called()
    assert conn.listener_count == 1

    # Now do the removal, expect everything disconnected
    conn.remove_listener(ch, destroying=destroying)
    assert conn.listener_count == 0

    if destroying:
        # Signals are staying untouched. This is driven by PyDM's logic. Presumably it does not bother to
        # disconnect, because connection object is about to die anyway, so signals will be detached.
        assert_has_receivers(1)
        for data_type in signal_overloads:
            assert_has_receivers(0 if data_type == QObject else 1, overload=data_type)
    else:
        assert_has_receivers(0)
        for data_type in signal_overloads:
            assert_has_receivers(0, overload=data_type)

        # Verify that we are actually not getting anything
        write_value.reset_mock()
        write_value.assert_not_called()
        with qtbot.wait_signal(signal_owner.sig1[str]):
            signal_owner.sig1[str].emit('test')
        write_value.assert_not_called()


@pytest.mark.parametrize('initiator_uid,expected_return_uid', [
    ('test1', 'test1'),
    ('test2', 'test2'),
    ('', ''),
    (None, ''),  # Seems None is automatically turned into empty string by PyQt in signal that only accepts strings
])
def test_common_requested_get_returns_same_uuid(qtbot: QtBot, initiator_uid, expected_return_uid, make_common_conn):
    ch = cast(channel.CChannel, channel.PyDMChannel(address='device/property'))
    request_slot = mock.Mock()
    ch.request_slot = request_slot
    conn = make_common_conn(ch, ch.address)
    conn.add_listener(ch)
    request_slot.reset_mock()
    expected_payload = channel.CChannelData(value=1, meta_info={})
    with qtbot.wait_signal(conn.requested_value_signal) as blocker:
        conn.request_value(initiator_uid)
    assert blocker.args == [expected_payload, expected_return_uid]
    request_slot.assert_called_once_with(expected_payload, expected_return_uid)


@pytest.mark.parametrize('value_slot_exists,request_slot_exists,subscribes', [
    (True, True, True),
    (True, False, True),
    (False, True, True),
    (False, False, False),
])
def test_common_subscribes_on_first_connection(value_slot_exists, request_slot_exists, subscribes, make_common_conn):
    ch = cast(channel.CChannel, channel.PyDMChannel(address='device/property'))
    if value_slot_exists:
        ch.value_slot = mock.Mock()
    if request_slot_exists:
        ch.request_slot = mock.Mock()
    conn = make_common_conn(ch, ch.address)
    with mock.patch.object(conn, 'subscribe') as subscribe:
        conn.add_listener(ch)
        if subscribes:
            subscribe.assert_called_once_with(callback=conn._subscribe_callback)
        else:
            subscribe.assert_not_called()


@pytest.mark.parametrize('value_slot_exists,request_slot_exists,get_issued_on_repeat', [
    (True, True, True),
    (True, False, True),
    (False, True, True),
    (False, False, False),
])
def test_common_gets_on_repeated_connection(value_slot_exists, request_slot_exists, get_issued_on_repeat, make_common_conn):
    ch1 = cast(channel.CChannel, channel.PyDMChannel(address='device/property'))
    ch2 = cast(channel.CChannel, channel.PyDMChannel(address='device/property'))
    if value_slot_exists:
        ch1.value_slot = mock.Mock()
        ch2.value_slot = mock.Mock()
    if request_slot_exists:
        ch1.request_slot = mock.Mock()
        ch2.request_slot = mock.Mock()
    conn = make_common_conn(ch1, ch1.address)
    conn.add_listener(ch1)  # First connection might have issued subscribe (checked in another test case)
    with mock.patch.object(conn, 'get') as get:
        conn.add_listener(ch2)
        if get_issued_on_repeat:
            if value_slot_exists:
                get.assert_called_once_with(callback=conn._on_async_get)
            else:
                get.assert_called_once_with(callback=conn._on_requested_get)
        else:
            get.assert_not_called()


@pytest.mark.parametrize('value_slot_exists,request_slot_exists,connected_is_turned', [
    (True, True, False),
    (True, False, False),
    (False, True, False),
    (False, False, True),
])
def test_common_assumes_connected_for_not_provided_slots(value_slot_exists, request_slot_exists, connected_is_turned, make_common_conn):
    ch1 = cast(channel.CChannel, channel.PyDMChannel(address='device/property'))
    ch2 = cast(channel.CChannel, channel.PyDMChannel(address='device/property'))
    if value_slot_exists:
        ch1.value_slot = mock.Mock()
        ch2.value_slot = mock.Mock()
    if request_slot_exists:
        ch1.request_slot = mock.Mock()
        ch2.request_slot = mock.Mock()
    conn = make_common_conn(ch1, ch1.address)
    with mock.patch.multiple(conn, subscribe=mock.DEFAULT, get=mock.DEFAULT):  # Just make sure connected is not affected in those methods
        for ch in [ch1, ch2]:
            conn.add_listener(ch)
            assert conn.connected == connected_is_turned


@pytest.mark.parametrize('request_signal_exists,request_slot_exists', [
    (True, True),
    (True, False),
    (False, True),
    (False, False),
])
def test_common_connects_request_slots_on_add_listener(qtbot: QtBot, request_signal_exists, request_slot_exists, signal_factory, make_common_conn):
    signal_owner = signal_factory([[str]])
    ch = cast(channel.CChannel, channel.PyDMChannel(address='device/property'))
    ch.request_signal = signal_owner.sig1 if request_signal_exists else None
    if request_slot_exists:
        ch.request_slot = mock.Mock()

    assert_has_receivers = functools.partial(assert_signal_has_receivers,
                                             owner=signal_owner,
                                             signal_exists=request_signal_exists)

    assert_has_receivers(0, sig=ch.request_signal)
    conn = make_common_conn(ch, ch.address)
    request_value = mock.Mock()
    conn.request_value = request_value
    # Assuming add_listener was not called in the constructor
    assert_has_receivers(0, sig=ch.request_signal)
    assert conn.receivers(conn.requested_value_signal) == 0
    conn.add_listener(ch)  # This should have connected request_signal and request_slot
    assert_has_receivers(1, sig=ch.request_signal)
    if request_slot_exists:
        assert conn.receivers(conn.requested_value_signal) == 1
    else:
        assert conn.receivers(conn.requested_value_signal) == 0

    dummy_payload = CChannelData(value=1, meta_info={})
    with qtbot.wait_signal(conn.requested_value_signal) as blocker:
        conn.requested_value_signal.emit(dummy_payload, 'test-uuid')
    assert blocker.args == [dummy_payload, 'test-uuid']
    if request_slot_exists:
        cast(mock.Mock, ch.request_slot).assert_called_once_with(dummy_payload, 'test-uuid')

    request_value.assert_not_called()
    if request_signal_exists:
        with qtbot.wait_signal(ch.request_signal) as blocker:
            ch.request_signal.emit('test-uuid2')  # type: ignore
        assert blocker.args == ['test-uuid2']
        request_value.assert_called_once_with('test-uuid2')


@pytest.mark.parametrize('destroying', [True, False])
@pytest.mark.parametrize('request_signal_exists,request_slot_exists', [
    (True, True),
    (True, False),
    (False, True),
    (False, False),
])
def test_common_disconnects_request_slots_on_remove_listener(qtbot: QtBot, request_signal_exists, request_slot_exists, destroying, signal_factory, make_common_conn):
    signal_owner = signal_factory([[str]])
    ch = cast(channel.CChannel, channel.PyDMChannel(address='device/property'))
    ch.request_signal = signal_owner.sig1 if request_signal_exists else None
    if request_slot_exists:
        ch.request_slot = mock.Mock()

    assert_has_receivers = functools.partial(assert_signal_has_receivers,
                                             owner=signal_owner,
                                             signal_exists=request_signal_exists)

    conn = make_common_conn(ch, ch.address)
    request_value = mock.Mock()
    conn.request_value = request_value
    assert conn.listener_count == 0
    conn.add_listener(ch)  # This should have connected request_signal and request_slot
    assert_has_receivers(1, sig=ch.request_signal)
    if request_slot_exists:
        assert conn.receivers(conn.requested_value_signal) == 1
    else:
        assert conn.receivers(conn.requested_value_signal) == 0
    assert conn.listener_count == 1

    # Now do the removal, expect everything disconnected
    conn.remove_listener(ch, destroying=destroying)
    assert conn.listener_count == 0

    if destroying:
        # Signals are staying untouched. This is driven by PyDM's logic. Presumably it does not bother to
        # disconnect, because connection object is about to die anyway, so signals will be detached.
        assert_has_receivers(1, sig=ch.request_signal)
        if request_slot_exists:
            assert conn.receivers(conn.requested_value_signal) == 1
        else:
            assert conn.receivers(conn.requested_value_signal) == 0
    else:
        assert_has_receivers(0, sig=ch.request_signal)
        assert conn.receivers(conn.requested_value_signal) == 0

        # Verify that we are actually not getting anything
        request_value.reset_mock()
        request_value.assert_not_called()
        if request_signal_exists:
            with qtbot.wait_signal(ch.request_signal):
                ch.request_signal.emit('test-uuid1')  # type: ignore
            request_value.assert_not_called()
        if request_slot_exists:
            cast(mock.Mock, ch.request_slot).reset_mock()
            cast(mock.Mock, ch.request_slot).assert_not_called()
            with qtbot.wait_signal(conn.requested_value_signal):
                conn.requested_value_signal.emit(CChannelData(value=3, meta_info={}), 'test-uuid2')
            cast(mock.Mock, ch.request_slot).assert_not_called()


def test_common_unsubscribes_on_close(make_common_conn):
    ch = cast(channel.CChannel, channel.PyDMChannel(address='device/property'))
    conn = make_common_conn(ch, ch.address)
    conn.add_listener(ch)
    with mock.patch.object(conn, 'unsubscribe') as unsubscribe:
        unsubscribe.assert_not_called()
        conn.close()
        unsubscribe.assert_called_once()


def test_common_get_fires_back_on_new_value_signal(qtbot: QtBot, make_common_conn):
    ch = cast(channel.CChannel, channel.PyDMChannel(address='device/property'))
    value_slot = mock.Mock()
    ch.value_slot = value_slot
    conn = make_common_conn(ch, ch.address)
    conn.add_listener(ch)
    value_slot.reset_mock()
    dummy_val = 345
    with mock.patch.object(conn, 'get', side_effect=lambda cb: cb(dummy_val)):
        ch.value_slot.assert_not_called()
        expected_payload = CChannelData(value=dummy_val, meta_info={})  # Packaging defined in make_common_conn
        with qtbot.wait_signal(conn.new_value_signal) as blocker:
            conn.get(conn._on_async_get)
        assert blocker.args == [expected_payload]
        value_slot.assert_called_once_with(expected_payload)


def test_common_requested_get_fires_back_on_requested_signal(qtbot: QtBot, make_common_conn, signal_factory):
    signal_owner = signal_factory([[str]])
    ch = cast(channel.CChannel, channel.PyDMChannel(address='device/property'))
    ch.request_signal = signal_owner.sig1
    request_slot = mock.Mock()
    ch.request_slot = request_slot
    conn = make_common_conn(ch, ch.address)
    conn.add_listener(ch)
    request_slot.reset_mock()
    dummy_val = 345

    def fake_get(callback):
        callback(dummy_val)

    with mock.patch.object(conn, 'get', side_effect=fake_get):
        request_slot.assert_not_called()
        expected_payload = CChannelData(value=dummy_val, meta_info={})  # Packaging defined in make_common_conn
        with qtbot.wait_signal(conn.requested_value_signal) as blocker:
            ch.request_signal.emit('test-uuid')
        assert blocker.args == [expected_payload, 'test-uuid']
        request_slot.assert_called_once_with(expected_payload, 'test-uuid')


def test_common_failure_to_process_incoming_value(qtbot: QtBot, make_common_conn, caplog: LogCaptureFixture):
    ch = cast(channel.CChannel, channel.PyDMChannel(address='device/property'))
    value_slot = mock.Mock()
    ch.value_slot = value_slot
    conn = make_common_conn(ch, ch.address)
    conn.add_listener(ch)
    value_slot.reset_mock()
    with mock.patch.object(conn, 'process_incoming_value', side_effect=ValueError('Test message')):
        value_slot.assert_not_called()
        with qtbot.wait_signal(conn.new_value_signal, raising=False):
            conn.get(conn._on_async_get)
        # We have to protect from warnings leaking from dependencies, e.g. cmmnbuild_dep_manager, regarding JVM :(
        warning_records = [r for r in cast(List[LogRecord], caplog.records) if
                           r.levelno == logging.WARNING and r.name == 'comrad.data_plugins']
        assert len(warning_records) == 1
        assert warning_records[0].msg.endswith(': Test message')
        value_slot.assert_not_called()


@pytest.mark.parametrize('protocol,connection_class', [
    ('test1proto', CDataConnection),
    ('test2proto', 'custom'),
])
def test_plugin_connection_mapping(protocol, connection_class):
    if connection_class == 'custom':
        class CustomDataConnection(CDataConnection):
            pass

        connection_class = CustomDataConnection

    plugin_class = make_plugin()
    plugin_class.protocol = protocol
    plugin_class.connection_class = connection_class

    plugin = plugin_class()

    ch = channel.PyDMChannel(address=f'{protocol}://device/property')
    assert len(plugin.connections) == 0
    plugin.add_connection(ch)
    assert list(plugin.connections.keys()) == ['device/property']
    assert type(plugin.connections['device/property']) == connection_class
    assert plugin.connections['device/property'].protocol == protocol
