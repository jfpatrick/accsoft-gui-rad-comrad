import pytest
from comrad.data.addr import ControlEndpointAddress


@pytest.mark.parametrize('selector', [
    None,
    'DOMAIN.GROUP.USER',
])
@pytest.mark.parametrize('filter,expected_filter', [
    ('one=two', {'one': 'two'}),
    ('one=two&three=four', {'one': 'two', 'three': 'four'}),
    (None, None),
])
@pytest.mark.parametrize('param_name,expected_protocol,expected_service,expected_dev,expected_prop,expected_field', [
    ('device/property', None, None, 'device', 'property', None),
    ('device/property#field', None, None, 'device', 'property', 'field'),
    ('protocol:///device/property', 'protocol', None, 'device', 'property', None),
    ('protocol:///device/property#field', 'protocol', None, 'device', 'property', 'field'),
    ('protocol://service/device/property', 'protocol', 'service', 'device', 'property', None),
    ('protocol://service/device/property#field', 'protocol', 'service', 'device', 'property', 'field'),
], ids=repr)
def test_from_string_succeeds(selector, param_name, filter, expected_filter, expected_protocol, expected_service, expected_dev, expected_prop, expected_field):
    input_str = param_name if selector is None else f'{param_name}@{selector}'
    if filter is not None:
        input_str += '?'
        input_str += filter
    addr = ControlEndpointAddress.from_string(input_str)
    assert addr is not None
    assert addr.valid
    assert addr.protocol == expected_protocol
    assert addr.service == expected_service
    assert addr.device == expected_dev
    assert addr.property == expected_prop
    assert addr.field == expected_field
    assert addr.selector == selector
    assert addr.data_filters == expected_filter


@pytest.mark.parametrize('selector', [
    '',
    '@DOMAIN.GROUP.USER',
])
@pytest.mark.parametrize('filter', [
    '?one=two',
    '?one=two&three=four',
    '',
])
@pytest.mark.parametrize('field', [
    '#field',
    '',
])
@pytest.mark.parametrize('param_name', [
    'device/property',
    'protocol:///device/property',
    'protocol://service/device/property',
], ids=repr)
def test_from_string_repr(param_name, selector, filter, field):
    input_str = f'{param_name}{field}{selector}{filter}'
    expected_str = f'{param_name}{field}{filter}' if filter else f'{param_name}{field}{selector}'
    addr = ControlEndpointAddress.from_string(input_str)
    assert addr.valid
    assert str(addr) == expected_str


@pytest.mark.parametrize('filter', [
    '',
    '?',
    '?=',
    '?key',
    '?key=',
    '?key=val&',
    '?key=val&key2',
    '?key=val&key2=',
])
@pytest.mark.parametrize('selector', [
    '',
    '@DOMAIN',
    '@DOMAIN.',
    '@DOMAIN.GROUP',
    '@DOMAIN.GROUP.',
    '@.GROUP.USER',
    '@..USER',
    '@.GROUP',
    '@.GROUP.',
    '@DOMAIN..',
    '@DOMAIN.USER.ALL',
])
@pytest.mark.parametrize('param_name', [
    'device',
    'device/',
    'device/property#',
    '/property',
    '/device/property',
    '/device/property#field',
    'property#field',
    'protocol://device',
    'protocol://device/property',
    'protocol://device/property#field',
    'protocol://device/#field',
    'protocol://service/device',
    'protocol://service/device/',
    'protocol://service/device/#',
    'protocol://service/device#field',
    'protocol://service/device/#field',
    'protocol://service//#',
    'protocol://service//#field',
    'service/device/property',
    'service/device/property#field',
    'protocol:///device',
    'protocol:///device#field',
    '///service/device/property',
    '///service/device#field',
    '///service/device/property#',
    '///service/device/#field',
], ids=repr)
def test_from_string_fails_invalid_address(param_name, selector, filter):
    input_str = f'{param_name}{selector}{filter}'
    addr = ControlEndpointAddress.from_string(input_str)
    assert addr is None


@pytest.mark.parametrize('selector', [
    'DOMAIN',
    'DOMAIN.',
    'DOMAIN.GROUP',
    'DOMAIN.GROUP.',
    '.GROUP.USER',
    '..USER',
    '.GROUP',
    '.GROUP.',
    'DOMAIN..',
])
@pytest.mark.parametrize('param_name', [
    'device/property',
    'device/property#field',
    'protocol:///device/property',
    'protocol:///device/property#field',
    'protocol://service/device/property',
    'protocol://service/device/property#field',
], ids=repr)
def test_from_string_fails_invalid_selector(param_name, selector):
    addr = ControlEndpointAddress.from_string(f'{param_name}@{selector}')
    assert addr is None


@pytest.mark.parametrize('filter', [
    '',
    '=',
    'key',
    'key=',
    'key=val&',
    'key=val&key2',
    'key=val&key2=',
])
@pytest.mark.parametrize('param_name', [
    'device/property',
    'device/property#field',
    'protocol:///device/property',
    'protocol:///device/property#field',
    'protocol://service/device/property',
    'protocol://service/device/property#field',
], ids=repr)
def test_from_string_fails_invalid_filter(param_name, filter):
    addr = ControlEndpointAddress.from_string(f'{param_name}?{filter}')
    assert addr is None


@pytest.mark.parametrize('valid,protocol,service,device,prop,field,selector', [
    (True, None, None, 'device', 'property', None, None),
    (True, None, None, 'device', 'property', 'field', None),
    (False, None, 'service', 'device', 'property', None, None),
    (False, None, 'service', 'device', 'property', 'field', None),
    (True, 'protocol', None, 'device', 'property', None, None),
    (True, 'protocol', None, 'device', 'property', 'field', None),
    (True, 'protocol', 'service', 'device', 'property', None, None),
    (True, 'protocol', 'service', 'device', 'property', 'field', None),
    (True, 'protocol', 'protocol', 'device', 'property', None, None),
    (True, 'protocol', 'protocol', 'device', 'property', 'field', None),
    (True, None, None, 'device', 'property', None, 'selector'),
    (True, None, None, 'device', 'property', 'field', 'selector'),
    (False, None, 'service', 'device', 'property', None, 'selector'),
    (False, None, 'service', 'device', 'property', 'field', 'selector'),
    (True, 'protocol', None, 'device', 'property', None, 'selector'),
    (True, 'protocol', None, 'device', 'property', 'field', 'selector'),
    (True, 'protocol', 'service', 'device', 'property', None, 'selector'),
    (True, 'protocol', 'service', 'device', 'property', 'field', 'selector'),
    (True, 'protocol', 'protocol', 'device', 'property', None, 'selector'),
    (True, 'protocol', 'protocol', 'device', 'property', 'field', 'selector'),
], ids=repr)
def test_is_valid(valid, protocol, service, device, prop, field, selector):
    # cases without device or property are not tested, because they are required arguments
    addr = ControlEndpointAddress(protocol=protocol, service=service, device=device, prop=prop, field=field, selector=selector)
    assert addr.valid == valid


@pytest.mark.parametrize('input_addr,succeeds', [
    ('device/property', True),
    ('device/property#field', True),
    ('protocol:///device/property', True),
    ('protocol:///device/property#field', True),
    ('protocol://service/device/property', True),
    ('protocol://service/device/property#field', True),
    ('device', False),
    ('device/', False),
    ('device/property#', False),
    ('/property', False),
    ('property#field', False),
    ('device/property@LHC.USER.ALL', False),
    ('device/property#field@LHC.USER.ALL', False),
    ('protocol:///device/property@LHC.USER.ALL', False),
    ('protocol://service/device/property@LHC.USER.ALL', False),
    ('device/property?key1=val1', False),
    ('device/property#field?key1=val1', False),
    ('protocol:///device/property?key1=val1', False),
    ('protocol://service/device/property?key1=val1', False),
    ('device/property@LHC.USER.ALL?key1=val1', False),
    ('device/property#field@LHC.USER.ALL?key1=val1', False),
    ('protocol:///device/property@LHC.USER.ALL?key1=val1', False),
    ('protocol://service/device/property@LHC.USER.ALL?key1=val1', False),
    ('protocol://device', False),
    ('protocol://device/property', False),
    ('protocol://device/property#field', False),
    ('protocol://device/#field', False),
    ('protocol://service/device', False),
    ('protocol://service/device/', False),
    ('protocol://service/device/#', False),
    ('protocol://service/device#field', False),
    ('protocol://service/device/#field', False),
    ('protocol://service//#', False),
    ('protocol://service//#field', False),
    ('service/device/property', False),
    ('service/device/property#field', False),
    ('protocol:///device', False),
    ('protocol:///device#field', False),
    ('///service/device/property', False),
    ('///service/device#field', False),
    ('///service/device/property#', False),
    ('///service/device/#field', False),
])
def test_validate_parameter_name(input_addr, succeeds):
    assert ControlEndpointAddress.validate_parameter_name(input_addr) == succeeds
