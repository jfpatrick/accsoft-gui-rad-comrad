import pytest
from comrad.data.addr import ControlEndpointAddress


@pytest.mark.parametrize('selector', [
    None,
    'DOMAIN.GROUP.USER',
])
@pytest.mark.parametrize('input,expected_protocol,expected_service,expected_dev,expected_prop,expected_field', [
    ('device/property', None, None, 'device', 'property', None),
    ('device/property#field', None, None, 'device', 'property', 'field'),
    ('protocol:///device/property', 'protocol', None, 'device', 'property', None),
    ('protocol:///device/property#field', 'protocol', None, 'device', 'property', 'field'),
    ('protocol://service/device/property', 'protocol', 'service', 'device', 'property', None),
    ('protocol://service/device/property#field', 'protocol', 'service', 'device', 'property', 'field'),
], ids=repr)
def test_from_string_succeeds(selector, input, expected_protocol, expected_service, expected_dev, expected_prop, expected_field):
    input_str = input if selector is None else f'{input}@{selector}'
    addr = ControlEndpointAddress.from_string(input_str)
    assert addr is not None
    assert addr.valid
    assert addr.protocol == expected_protocol
    assert addr.service == expected_service
    assert addr.device == expected_dev
    assert addr.property == expected_prop
    assert addr.field == expected_field
    assert addr.selector == selector


@pytest.mark.parametrize('selector', [
    None,
    'DOMAIN.GROUP.USER',
])
@pytest.mark.parametrize('input', [
    'device/property',
    'device/property#field',
    'protocol:///device/property',
    'protocol:///device/property#field',
    'protocol://service/device/property',
    'protocol://service/device/property#field',
], ids=repr)
def test_from_string_repr(input, selector):
    input_str = input if selector is None else f'{input}@{selector}'
    addr = ControlEndpointAddress.from_string(input_str)
    assert addr.valid
    assert str(addr) == input_str


@pytest.mark.parametrize('selector', [
    None,
    'DOMAIN',
    'DOMAIN.',
    'DOMAIN.GROUP',
    'DOMAIN.GROUP.',
    '.GROUP.USER',
    '..USER',
    '.GROUP',
    '.GROUP.',
    'DOMAIN..',
    'DOMAIN.USER.ALL',
])
@pytest.mark.parametrize('input', [
    'device',
    'device/',
    'device/property#',
    '/property',
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
def test_from_string_fails_invalid_address(input, selector):
    input_str = input if selector is None else f'{input}@{selector}'
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
@pytest.mark.parametrize('input', [
    'device/property',
    'device/property#field',
    'protocol:///device/property',
    'protocol:///device/property#field',
    'protocol://service/device/property',
    'protocol://service/device/property#field',
], ids=repr)
def test_from_string_fails_invalid_selector(input, selector):
    addr = ControlEndpointAddress.from_string(f'{input}@{selector}')
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
