import pytest
from unittest import mock
from typing import cast
from qtpy.QtCore import Signal, QObject
from comrad.data.channel import PyDMChannel, CChannel, allow_connections, CChannelData


def test_equal_same():
    ch1 = PyDMChannel()
    ch2 = ch1
    assert ch1 == ch2


def signal_factory():

    class Obj(QObject):
        sig1 = Signal()
        sig2 = Signal()

    obj = Obj()
    yield obj.sig1
    yield obj.sig2


@pytest.mark.parametrize('addr1,addr2,ch1_signal_idx,ch2_signal_idx,same_request_slot,should_succeed', [
    ('addr1', 'addr1', 0, 0, True, True),
    ('addr1', 'addr1', 0, 0, False, False),
    ('addr1', 'addr1', 0, 1, True, False),
    ('addr1', 'addr1', 0, 1, False, False),
    ('addr1', 'addr1', 0, None, True, False),
    ('addr1', 'addr1', 0, None, False, False),
    ('addr1', 'addr1', None, 1, True, False),
    ('addr1', 'addr1', None, 1, False, False),
    ('addr1', 'addr1', None, None, True, True),
    ('addr1', 'addr1', None, None, False, False),
    ('addr1', 'addr2', 0, 0, True, False),
    ('addr1', 'addr2', 0, 0, False, False),
    ('addr1', 'addr2', 0, 1, True, False),
    ('addr1', 'addr2', 0, 1, False, False),
    ('addr1', 'addr2', 0, None, True, False),
    ('addr1', 'addr2', 0, None, False, False),
    ('addr1', 'addr2', None, 1, True, False),
    ('addr1', 'addr2', None, 1, False, False),
    ('addr1', 'addr2', None, None, True, False),
    ('addr1', 'addr2', None, None, False, False),
])
def test_equal_addresses(addr1, addr2, ch1_signal_idx, ch2_signal_idx, same_request_slot, should_succeed):
    ch1 = cast(CChannel, PyDMChannel(address=addr1))
    ch2 = cast(CChannel, PyDMChannel(address=addr2))
    ch1.request_slot = mock.Mock()
    signals = list(signal_factory())
    ch1.request_signal = None if ch1_signal_idx is None else signals[ch1_signal_idx]
    ch2.request_signal = None if ch2_signal_idx is None else signals[ch2_signal_idx]
    ch2.request_slot = ch1.request_slot if same_request_slot else mock.Mock()
    equal = ch1 == ch2
    equal_revers = ch2 == ch1
    assert equal == equal_revers
    assert equal == should_succeed


@pytest.mark.parametrize('enable_conn,should_be_called', [
    (True, True),
    (False, False),
])
def test_does_not_connect_when_connections_disabled(enable_conn, should_be_called):
    ch = cast(CChannel, PyDMChannel(address='test'))
    connect_mock = mock.MagicMock()
    ch._overridden_members['connect'] = connect_mock
    allow_connections(enable_conn)
    ch.connect()
    if should_be_called:
        connect_mock.assert_called_once()
    else:
        connect_mock.assert_not_called()
    connect_mock.reset_mock()
    allow_connections(True)
    ch.connect()
    connect_mock.assert_called_once()


@pytest.mark.parametrize('val1,val2,meta1,meta2,should_equal', [
    (1, 2, {}, {}, False),
    (1, 1, {}, {}, True),
    (1, 'str', {}, {}, False),
    (1, '1', {}, {}, False),
    (1, 1, {'key1': 'val1'}, {}, False),
])
def test_channel_data(val1, val2, meta1, meta2, should_equal):
    data1 = CChannelData(value=val1, meta_info=meta1)
    data2 = CChannelData(value=val2, meta_info=meta2)
    is_equal = data1 == data2
    assert should_equal == is_equal
