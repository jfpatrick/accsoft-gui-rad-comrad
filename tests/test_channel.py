import pytest
from unittest import mock
from typing import cast
from qtpy.QtCore import Signal, QObject
from comrad.data.channel import PyDMChannel, CChannel, format_address, CChannelData
from comrad.data.context import CContext


def test_equal_same():
    ch1 = PyDMChannel()
    ch2 = ch1
    assert ch1 == ch2


@pytest.mark.parametrize('addr1,addr2,addr_match', [
    ('addr1', 'addr1', True),
    ('addr1', 'addr2', False),
])
@pytest.mark.parametrize('ch1_signal_idx,ch2_signal_idx,signals_match', [
    (0, 0, True),
    (0, 1, False),
])
@pytest.mark.parametrize('use_ctx1,use_ctx2,context_match', [
    (True, True, True),
    (True, True, False),
    (False, True, False),
    (True, False, False),
    (False, False, True),
])
@pytest.mark.parametrize('same_request_slot', [True, False])
def test_equal_addresses(addr1, addr2, addr_match, ch1_signal_idx, ch2_signal_idx, signals_match,
                         same_request_slot, context_match, use_ctx1, use_ctx2):
    should_succeed = same_request_slot and context_match and signals_match and addr_match

    ctx1 = None if not use_ctx1 else CContext(selector='sel1')
    ctx2 = ctx1 if context_match else (CContext(selector='sel2') if use_ctx2 else None)
    ch1 = cast(CChannel, PyDMChannel(address=addr1))
    ch2 = cast(CChannel, PyDMChannel(address=addr2))
    ch1.request_slot = mock.Mock()

    def signal_factory():
        class Obj(QObject):
            sig1 = Signal()
            sig2 = Signal()

        obj = Obj()
        yield obj.sig1
        yield obj.sig2

    signals = list(signal_factory())
    ch1.context = ctx1
    ch2.context = ctx2
    ch1.request_signal = None if ch1_signal_idx is None else signals[ch1_signal_idx]
    ch2.request_signal = None if ch2_signal_idx is None else signals[ch2_signal_idx]
    ch2.request_slot = ch1.request_slot if same_request_slot else mock.Mock()
    equal = ch1 == ch2
    equal_revers = ch2 == ch1
    assert equal == equal_revers
    assert equal == should_succeed


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


@pytest.mark.parametrize('wildcards', [None, {}, {'val1': 'key1'}])
@pytest.mark.parametrize('addr,selector,data_filter,expected_addr', [
    ('device/prop#field', None, None, 'device/prop#field'),
    ('device/prop#field', 'TEST.USER.ALL', None, 'device/prop#field@TEST.USER.ALL'),
    ('device/prop#field', '', None, 'device/prop#field'),
    ('device/prop#field', None, {'val1': 'key1'}, 'device/prop#field?val1=key1'),
    ('device/prop#field', None, {'val1': 'key1', 'val2': 'key2'}, 'device/prop#field?val1=key1&val2=key2'),
    ('device/prop#field', 'TEST.USER.ALL', {'val1': 'key1'}, 'device/prop#field?val1=key1'),
    ('device/prop#field', 'TEST.USER.ALL', {'val1': 'key1', 'val2': 'key2'}, 'device/prop#field?val1=key1&val2=key2'),
    ('device/prop#field', '', {'val1': 'key1'}, 'device/prop#field?val1=key1'),
    ('device/prop#field', '', {'val1': 'key1', 'val2': 'key2'}, 'device/prop#field?val1=key1&val2=key2'),
    ('device/prop#field', None, {}, 'device/prop#field'),
    ('device/prop#field', 'TEST.USER.ALL', {}, 'device/prop#field@TEST.USER.ALL'),
    ('device/prop#field', '', {}, 'device/prop#field'),
])
def test_format_address(wildcards, addr, selector, data_filter, expected_addr):
    actual_addr = format_address(channel_address=addr,
                                 context=CContext(selector=selector, data_filters=data_filter, wildcards=wildcards))
    assert actual_addr == expected_addr


def test_address_setter():
    ch = PyDMChannel(address='addr1')
    context = CContext(selector='TEST.USER.ALL')
    cast(CChannel, ch).context = context
    with mock.patch('comrad.data.channel.format_address') as format_address:
        ch.address = 'addr2'
        _ = ch.address
        format_address.assert_called_with('addr2', context)


def test_context_setter():
    ch = PyDMChannel(address='addr1')
    context = CContext(selector='TEST.USER.ALL')
    cast(CChannel, ch).context = context
    context2 = CContext(selector='ANOTHER.USER.ALL')
    with mock.patch('comrad.data.channel.format_address') as format_address:
        cast(CChannel, ch).context = context2
        _ = ch.address
        format_address.assert_called_with('addr1', context2)
