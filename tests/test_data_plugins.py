import pytest
from typing import cast
from pytestqt.qtbot import QtBot
from unittest import mock
from comrad.data import channel
from comrad.data_plugins import CCommonDataConnection, CChannelData


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


@pytest.mark.skip
def test_base_add_listener_connects_extra_signal_types():
    # Check CCHannelData can be transfered over standard signal
    pass


@pytest.mark.skip
def test_base_add_listener_connects_write_signals():
    pass


@pytest.mark.skip
def test_base_add_listener_emits_write_signal():
    pass


@pytest.mark.skip
def test_base_add_listener_emits_connection_status():
    pass


@pytest.mark.skip
def test_base_picky_read_only_connection():
    pass


@pytest.mark.skip
def test_base_close_issues_disconnected_signal():
    pass


@pytest.mark.skip
@mock.patch('pydm.widgets.channel.PyDMChannel')
def test_remove_listener_disconnects_slots(PyDMChannel):
    pass
    # FIXME: Cant properly mock 'connect'
    # japc = japc_plugin.get_japc()
    # mocker.patch.object(japc, 'stopSubscriptions')
    # mocker.patch.object(PyDMChannel.value_signal, 'connect')
    # _ = japc_plugin.CJapcConnection(channel=PyDMChannel, address='test_addr')
    # PyDMChannel.value_signal.connect.assert_called_once()


def test_common_requested_get_returns_same_uuid(qtbot: QtBot, make_common_conn):
    ch = channel.PyDMChannel(address='device/property')
    cast(channel.CChannel, ch).request_slot = lambda *_: None
    connection = make_common_conn(ch, '/device/property', 'rda')
    with qtbot.wait_signal(connection.requested_value_signal) as blocker:
        connection.request_value('test-uuid')
    assert blocker.args == [channel.CChannelData(value=1, meta_info={}), 'test-uuid']


@pytest.mark.skip
def test_common_subscribes_on_first_connection():
    # Check where it subscribes value_slot or request_slot
    pass


@pytest.mark.skip
def test_common_gets_on_repeated_connection():
    # Check that does not subscribe on repeated connections
    # Check where it subscribes value_slot or request_slot
    pass


@pytest.mark.skip
def test_common_assumes_connected_for_not_provided_slots():
    # Line 146 of common_conn.py
    pass


@pytest.mark.skip
def test_common_connects_request_slots_on_add_listener():
    pass


@pytest.mark.skip
def test_common_disconnects_request_slots_on_remove_listener():
    pass


@pytest.mark.skip
def test_common_unsubscribes_on_close():
    pass


@pytest.mark.skip
def test_common_get_fires_back_on_new_value_signal():
    pass


@pytest.mark.skip
def test_common_requested_get_fires_back_on_requested_signal():
    pass


@pytest.mark.skip
def test_common_failure_to_process_incoming_value():
    # Test prints warning
    # Test does not fire any signals
    pass


@pytest.mark.skip
def test_custom_plugin_used_on_custom_protocols():
    pass
