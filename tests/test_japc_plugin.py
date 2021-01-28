import pytest
import logging
import numpy as np
from pathlib import Path
from unittest import mock
from typing import cast, List
from logging import LogRecord
from pytestqt.qtbot import QtBot
from _pytest.logging import LogCaptureFixture
from qtpy.QtCore import Signal, Slot, QObject
from comrad.data import japc_plugin
from comrad.data.japc_plugin import CJapcConnection, CChannelData, SPECIAL_FIELDS, parse_field_trait
from comrad.data.channel import PyDMChannel, CChannel, CContext
from comrad.data.pyjapc_patch import CPyJapc
from _comrad.comrad_info import COMRAD_DEFAULT_PROTOCOL


@pytest.fixture(autouse=True)
def mock_singleton():
    with mock.patch('comrad.data.pyjapc_patch.CPyJapc.instance'):
        yield


@pytest.mark.parametrize('input,expected_output', [
    ('testField_min', (CChannelData.FieldTrait.MIN, 'testField')),
    ('testField_max', (CChannelData.FieldTrait.MAX, 'testField')),
    ('testField_units', (CChannelData.FieldTrait.UNITS, 'testField')),
    ('testField_madf', None),
    ('testField_ma', None),
    ('testField', None),
    ('_min', (CChannelData.FieldTrait.MIN, '')),
    ('_max', (CChannelData.FieldTrait.MAX, '')),
    ('_units', (CChannelData.FieldTrait.UNITS, '')),
    ('dev/prop#field_min', (CChannelData.FieldTrait.MIN, 'dev/prop#field')),
    ('dev/prop#field_max', (CChannelData.FieldTrait.MAX, 'dev/prop#field')),
    ('dev/prop#field_units', (CChannelData.FieldTrait.UNITS, 'dev/prop#field')),
    ('dev/prop#_min', (CChannelData.FieldTrait.MIN, 'dev/prop#')),
    ('dev/prop#_max', (CChannelData.FieldTrait.MAX, 'dev/prop#')),
    ('dev/prop#_units', (CChannelData.FieldTrait.UNITS, 'dev/prop#')),
])
def test_parse_field_trait(input, expected_output):
    assert parse_field_trait(input) == expected_output


@pytest.mark.parametrize('selector,filter,expected_selector', [
    (None, None, None),
    ('CERN.TEST.SELECTOR', None, 'CERN.TEST.SELECTOR'),
    (None, {'key': 'val', 'key2': 'val2'}, None),
    ('CERN.TEST.SELECTOR', {'key': 'val', 'key2': 'val2'}, None),
])
@pytest.mark.parametrize('param_name, expected_meta_field, expected_param_name', [
    ('mydevice/myprop#myfield', None, 'mydevice/myprop#myfield'),
    ('mydevice/myprop', None, 'mydevice/myprop'),
    ('mydevice/myprop#cycleName', 'cycleName', 'mydevice/myprop'),
    ('rda:///mydevice/myprop#myfield', None, 'rda:///mydevice/myprop#myfield'),
    ('rda:///mydevice/myprop', None, 'rda:///mydevice/myprop'),
    ('rda:///mydevice/myprop#cycleName', 'cycleName', 'rda:///mydevice/myprop'),
    ('rda://srv/mydevice/myprop#myfield', None, 'rda://srv/mydevice/myprop#myfield'),
    ('rda://srv/mydevice/myprop', None, 'rda://srv/mydevice/myprop'),
    ('rda://srv/mydevice/myprop#cycleName', 'cycleName', 'rda://srv/mydevice/myprop'),
    ('mydevice/myprop#_min', None, 'mydevice/myprop#_min'),
    ('mydevice/myprop#_max', None, 'mydevice/myprop#_max'),
    ('mydevice/myprop#_units', None, 'mydevice/myprop#_units'),
    ('mydevice/myprop#myfield_min', None, 'mydevice/myprop#myfield_min'),
    ('mydevice/myprop#myfield_max', None, 'mydevice/myprop#myfield_max'),
    ('mydevice/myprop#myfield_units', None, 'mydevice/myprop#myfield_units'),
    ('mydevice/myprop#cycleName_min', None, 'mydevice/myprop#cycleName_min'),
    ('mydevice/myprop#cycleName_max', None, 'mydevice/myprop#cycleName_max'),
    ('mydevice/myprop#cycleName_units', None, 'mydevice/myprop#cycleName_units'),
    ('rda:///mydevice/myprop#_min', None, 'rda:///mydevice/myprop#_min'),
    ('rda:///mydevice/myprop#_max', None, 'rda:///mydevice/myprop#_max'),
    ('rda:///mydevice/myprop#_units', None, 'rda:///mydevice/myprop#_units'),
    ('rda:///mydevice/myprop#myfield_min', None, 'rda:///mydevice/myprop#myfield_min'),
    ('rda:///mydevice/myprop#myfield_max', None, 'rda:///mydevice/myprop#myfield_max'),
    ('rda:///mydevice/myprop#myfield_units', None, 'rda:///mydevice/myprop#myfield_units'),
    ('rda:///mydevice/myprop#cycleName_min', None, 'rda:///mydevice/myprop#cycleName_min'),
    ('rda:///mydevice/myprop#cycleName_max', None, 'rda:///mydevice/myprop#cycleName_max'),
    ('rda:///mydevice/myprop#cycleName_units', None, 'rda:///mydevice/myprop#cycleName_units'),
    ('rda://srv/mydevice/myprop#_min', None, 'rda://srv/mydevice/myprop#_min'),
    ('rda://srv/mydevice/myprop#_max', None, 'rda://srv/mydevice/myprop#_max'),
    ('rda://srv/mydevice/myprop#_units', None, 'rda://srv/mydevice/myprop#_units'),
    ('rda://srv/mydevice/myprop#myfield_min', None, 'rda://srv/mydevice/myprop#myfield_min'),
    ('rda://srv/mydevice/myprop#myfield_max', None, 'rda://srv/mydevice/myprop#myfield_max'),
    ('rda://srv/mydevice/myprop#myfield_units', None, 'rda://srv/mydevice/myprop#myfield_units'),
    ('rda://srv/mydevice/myprop#cycleName_min', None, 'rda://srv/mydevice/myprop#cycleName_min'),
    ('rda://srv/mydevice/myprop#cycleName_max', None, 'rda://srv/mydevice/myprop#cycleName_max'),
    ('rda://srv/mydevice/myprop#cycleName_units', None, 'rda://srv/mydevice/myprop#cycleName_units'),
])
@mock.patch('comrad.data.japc_plugin.CJapcConnection.add_listener')
def test_connection_address(add_listener, param_name, selector, filter, expected_meta_field, expected_param_name,
                            expected_selector):
    ch = PyDMChannel(address=param_name)
    ctx = CContext(selector=selector, data_filters=filter)
    cast(CChannel, ch).context = ctx
    input_addr = ch.address.split('://')[-1]
    connection = CJapcConnection(channel=ch, protocol='rda', address=input_addr)
    add_listener.assert_called_once()
    assert connection._pyjapc_param_name == expected_param_name
    if expected_selector is None:
        assert 'timingSelectorOverride' not in connection._japc_additional_args
    else:
        assert connection._japc_additional_args['timingSelectorOverride'] == expected_selector
    if filter is None:
        assert 'dataFilterOverride' not in connection._japc_additional_args
    else:
        assert connection._japc_additional_args['dataFilterOverride'] == filter
    assert connection._meta_field == expected_meta_field


@pytest.mark.parametrize('channel_address', [
    'property#field',
    'device/property@LHC.USER.ALL',
    'device/property#field@LHC.USER.ALL',
])
@mock.patch('comrad.data.japc_plugin.CJapcConnection.add_listener')
def test_connection_fails_with_wrong_parameter_name(add_listener, channel_address, caplog: LogCaptureFixture):
    ch = PyDMChannel(address=channel_address)
    _ = CJapcConnection(channel=ch, protocol='rda', address=ch.address)
    add_listener.assert_not_called()
    actual_warnings = [r.msg for r in cast(List[LogRecord], caplog.records) if r.levelno == logging.ERROR]
    assert actual_warnings == [f'Cannot create connection with invalid parameter name format "{channel_address}"!']


@pytest.mark.parametrize('selector', [
    '@@@',
    'LHS.USER',
])
@mock.patch('comrad.data.japc_plugin.CJapcConnection.add_listener')
def test_connection_fails_with_wrong_context(add_listener, selector, caplog: LogCaptureFixture):
    ch = PyDMChannel(address='device/property')
    cast(CChannel, ch).context = CContext(selector=selector)
    _ = CJapcConnection(channel=ch, protocol='rda', address='/device/property')
    add_listener.assert_not_called()
    actual_warnings = [r.msg for r in cast(List[LogRecord], caplog.records) if r.levelno == logging.ERROR]
    assert actual_warnings == [f'Cannot create connection for address "device/property@{selector}"!']


@pytest.mark.parametrize('connected', [
    (True),
    (False),
])
def test_close_clears_subscriptions(connected):
    # FIXME: Test rather than unsubsribe calls clear subscriptions
    ch = PyDMChannel(address='dev/prop#field')
    connection = CJapcConnection(channel=ch, address='dev/prop#field', protocol='rda')
    connection.online = connected
    CPyJapc.instance.return_value.clearSubscriptions.assert_not_called()
    connection.close()
    CPyJapc.instance.return_value.clearSubscriptions.assert_called_with(parameterName='dev/prop#field', selector=None)


@pytest.mark.parametrize('other_type,sim_val', [
    (int, 99),
    (float, 52.3),
    (str, 'test'),
    (np.ndarray, np.array([1, 2])),
    (CChannelData, 99),
    (CChannelData, 52.3),
    (CChannelData, 'test'),
    (CChannelData, np.array([1, 2])),
])
def test_all_new_values_are_emitted_with_channel_data(other_type, sim_val, qtbot: QtBot):

    class Receiver(QObject):

        @Slot(other_type)
        def value_changed(self, _):
            pass

    receiver = Receiver()
    ch = PyDMChannel(address='device/property', value_slot=receiver.value_changed)
    connection = CJapcConnection(channel=ch, protocol='japc', address='/device/property')
    with qtbot.wait_signal(connection.new_value_signal) as blocker:
        connection._on_async_get(None, value=sim_val, headerInfo={})  # Simulate emission of a signal
    assert blocker.args == [CChannelData(value=sim_val, meta_info={})]


@pytest.mark.parametrize('meta_field,header_field', list(SPECIAL_FIELDS.items()))
def test_meta_field_resolved_on_field_level(meta_field, header_field):
    ch = PyDMChannel(address=f'device/property#{meta_field}')
    connection = CJapcConnection(channel=ch, protocol='rda', address=f'/device/property#{meta_field}')
    callback = mock.Mock()
    sig = mock.MagicMock()
    header = {
        'acqStamp': mock.MagicMock(),
        'setStamp': mock.MagicMock(),
        'cycleStamp': mock.MagicMock(),
        'selector': 'test-cycle-name',
    }
    connection._notify_listeners(f'device/property#{meta_field}', 42, header, emitter=callback, callback_signals=[sig])
    callback.assert_called_once_with(sig, CChannelData(value=header[header_field], meta_info=header))


def test_meta_field_missing_from_incoming_header(caplog: LogCaptureFixture):
    ch = PyDMChannel(address='device/property#acqStamp')
    connection = CJapcConnection(channel=ch, protocol='rda', address='/device/property#acqStamp')
    callback = mock.Mock()
    sig = mock.MagicMock()
    header = {
        'setStamp': mock.MagicMock(),
        'cycleStamp': mock.MagicMock(),
        'selector': 'test-cycle-name',
    }
    connection._notify_listeners('device/property#acqStamp', 42, header, emitter=callback, callback_signals=[sig])
    # We have to protect from warnings leaking from dependencies, e.g. cmmnbuild_dep_manager, regarding JVM :(
    warning_records = [r for r in cast(List[LogRecord], caplog.records) if r.levelno == logging.WARNING and r.name == 'comrad.data_plugins']
    assert len(warning_records) == 1
    assert 'Cannot locate meta-field "acqStamp" inside packet header' in warning_records[0].msg
    callback.assert_not_called()


@pytest.mark.parametrize('disregarded_header', [{}, {'notSpecial': 'ignore'}])
@pytest.mark.parametrize('val,considered_header,combined_val', [
    ({}, {}, {}),
    ({'val': 42}, {}, {'val': 42}),
    ({'val': 42, 'val2': 'val2'}, {}, {'val': 42, 'val2': 'val2'}),
    ({}, {'acqStamp': 'acqStamp'}, {'acqStamp': 'acqStamp'}),
    ({'val': 42}, {'acqStamp': 'acqStamp'}, {'val': 42, 'acqStamp': 'acqStamp'}),
    ({'val': 42, 'val2': 'val2'}, {'acqStamp': 'acqStamp'}, {'val': 42, 'val2': 'val2', 'acqStamp': 'acqStamp'}),
    ({}, {'selector': 'selector'}, {'cycleName': 'selector'}),
    ({'val': 42}, {'selector': 'selector'}, {'val': 42, 'cycleName': 'selector'}),
    ({'val': 42, 'val2': 'val2'}, {'selector': 'selector'}, {'val': 42, 'val2': 'val2', 'cycleName': 'selector'}),
    ({}, {'acqStamp': 'acqStamp', 'setStamp': 'setStamp', 'cycleStamp': 'cycleStamp', 'selector': 'selector'}, {'acqStamp': 'acqStamp', 'setStamp': 'setStamp', 'cycleStamp': 'cycleStamp', 'cycleName': 'selector'}),
    ({'val': 42}, {'acqStamp': 'acqStamp', 'setStamp': 'setStamp', 'cycleStamp': 'cycleStamp', 'selector': 'selector'}, {'val': 42, 'acqStamp': 'acqStamp', 'setStamp': 'setStamp', 'cycleStamp': 'cycleStamp', 'cycleName': 'selector'}),
    ({'val': 42, 'val2': 'val2'}, {'acqStamp': 'acqStamp', 'setStamp': 'setStamp', 'cycleStamp': 'cycleStamp', 'selector': 'selector'},
     {'val': 42, 'val2': 'val2', 'acqStamp': 'acqStamp', 'setStamp': 'setStamp', 'cycleStamp': 'cycleStamp', 'cycleName': 'selector'}),
    ({'acqStamp': 'valAcqStamp'}, {}, {'acqStamp': 'valAcqStamp'}),
    ({'acqStamp': 'valAcqStamp', 'val2': 'val2'}, {}, {'acqStamp': 'valAcqStamp', 'val2': 'val2'}),
    ({'acqStamp': 'valAcqStamp'}, {'acqStamp': 'acqStamp'}, {'acqStamp': 'acqStamp'}),
    ({'acqStamp': 'valAcqStamp', 'val2': 'val2'}, {'acqStamp': 'acqStamp'}, {'acqStamp': 'acqStamp', 'val2': 'val2'}),
])
def test_meta_fields_are_injected_into_full_property(val, considered_header, disregarded_header, combined_val):
    full_header = {**disregarded_header, **considered_header}
    ch = PyDMChannel(address='device/property')
    connection = CJapcConnection(channel=ch, protocol='japc', address='/device/property')
    callback = mock.Mock()
    sig = mock.MagicMock()
    connection._notify_listeners('device/property', val, full_header, emitter=callback, callback_signals=[sig])
    callback.assert_called_once_with(sig, CChannelData(value=combined_val, meta_info=full_header))


def test_write_slots_with_no_params_issue_empty_property_set(qtbot: QtBot):
    class TestWidget(QObject):
        sig = Signal()  # Notice no parameters here, this should be considered as "command"

    sender = TestWidget()
    ch = PyDMChannel(address='device/property', value_signal=sender.sig)
    _ = CJapcConnection(channel=ch, protocol='japc', address='/device/property')
    with qtbot.wait_signal(sender.sig):
        sender.sig.emit()
    CPyJapc.instance.return_value.setParam.assert_called_once_with(parameterName='device/property', parameterValue={})  # type: ignore


@pytest.mark.parametrize('protocol', ['japc', 'rda3', 'rda', 'tgm', 'no'])
def test_japc_plugin_is_used_on_protocols(protocol):
    def custom_env(env_name, *_, **__):
        if env_name == 'PYDM_DATA_PLUGINS_PATH':
            return str(Path(japc_plugin.__file__).parent.absolute())
        return mock.DEFAULT

    from pydm.data_plugins import initialize_plugins_if_needed, plugin_for_address, PyDMPlugin
    import pydm.data_plugins
    pydm.data_plugins.__plugins_initialized = False  # Force to reinitialize

    # In some tests custom environment maybe too late to create (because comrad and, subsequently pydm have already
    # been imported and resolved the environment. So we mock the environment getter for the force re-initialization
    with mock.patch('os.getenv', side_effect=custom_env):
        initialize_plugins_if_needed()
    plugin: PyDMPlugin = plugin_for_address(f'{protocol}:///device/property')
    assert plugin.protocol == protocol
    # Direct comparison does not work because loaded plugin has mangled class path
    assert plugin.connection_class.__name__ == CJapcConnection.__name__


def test_japc_plugin_is_used_on_no_protocol():
    def custom_env(env_name, *_, **__):
        if env_name == 'PYDM_DATA_PLUGINS_PATH':
            return str(Path(japc_plugin.__file__).parent.absolute())
        return mock.DEFAULT

    from pydm.data_plugins import initialize_plugins_if_needed, plugin_for_address, PyDMPlugin
    import pydm.data_plugins
    pydm.data_plugins.__plugins_initialized = False  # Force to reinitialize
    pydm.data_plugins.config.DEFAULT_PROTOCOL = COMRAD_DEFAULT_PROTOCOL

    # In some tests custom environment maybe too late to create (because comrad and, subsequently pydm have already
    # been imported and resolved the environment. So we mock the environment getter for the force re-initialization
    with mock.patch('os.getenv', side_effect=custom_env):
        initialize_plugins_if_needed()
    plugin: PyDMPlugin = plugin_for_address('device/property')
    assert plugin.protocol == COMRAD_DEFAULT_PROTOCOL
    # Direct comparison does not work because loaded plugin has mangled class path
    assert plugin.connection_class.__name__ == CJapcConnection.__name__
