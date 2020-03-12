import re
from typing import Optional, Dict, Any
from comrad.data.context import CContext


class ControlEndpointAddress:

    param_name_regex = r'^((?P<protocol>[^:/]+)://(?P<service>[^/]+)?/)?(?P<device>[^/#@&\n\t]+)/' \
                       r'(?P<property>[^/#@\?\n\t]+)(#(?P<field>[^@?\n\t]+))?'

    def __init__(self,
                 device: str,
                 prop: str,
                 field: Optional[str] = None,
                 protocol: Optional[str] = None,
                 service: Optional[str] = None,
                 selector: Optional[str] = None,
                 data_filters: Optional[Dict[str, Any]] = None):
        """
        Address of the device property (field) in the control system.

        Args:
            device: Name of the device recognized by the directory service.
            prop: Name of the property in the given device.
            field: Optional field name, if referring to only one field, as opposed to the full property.
            protocol: Optional protocol, e.g. rda3
            service: Service is the control node that resolves the device names,
                     if the main directory service is unaware of it.
            selector: Optional timing/cycle/user selector, e.g. LHC.USER.ALL
            data_filters: Optional data filters for expert users in equipment groups.
        """
        self.device = device
        self.property = prop
        self.field = field
        self.protocol = protocol
        self.service = service
        self.selector = selector
        self.data_filters = data_filters

    @property
    def valid(self) -> bool:
        """Address is complete and can be successfully resolved."""
        return (len(self.device) > 0 and len(self.property) > 0 and (
                (self.protocol is None and self.service is None)
                or self.protocol is not None))

    @classmethod
    def validate_parameter_name(cls, input_addr: str) -> bool:
        """Convenience method to validate only the parameter name value, as it is
        separated from the context, containing selectors and data filters.

        Args:
            input_addr: String formatted according to the device-property specification.

        Returns:
             ``True`` if validation succeeds.
        """
        mo = re.match(cls.param_name_regex + r'$', input_addr)
        return bool(mo and mo.groups())

    @classmethod
    def from_string(cls, input_addr: str) -> Optional['ControlEndpointAddress']:
        """
        Factory method to construct an object from string representation.

        Args:
            input_addr: String formatted according to the device-property specification.

        Returns:
            New object or ``None`` if could not parse the string.
        """
        mo = re.match(cls.param_name_regex
                      + r'(@(?P<selector>[^\.\?]+'
                        r'\.[^\.\?]+\.[^\.\?]+))?(\?(?P<filter>[^=&\n\t]+=[^=&\n\t]+(&[^=&\n\t]+=[^=&\n\t]+)*))?$', input_addr)
        if mo and mo.groups():
            captures = mo.groupdict()
            filters: Optional[Dict[str, Any]] = None
            captured_filters: Optional[str]
            try:
                captured_filters = captures['filter']
            except KeyError:
                captured_filters = None
            if captured_filters:
                filters = {}
                for pair in captured_filters.split('&'):
                    key, value = tuple(pair.split('='))
                    filters[key] = value
            return cls(device=captures['device'],
                       prop=captures['property'],
                       field=captures['field'],
                       protocol=captures['protocol'],
                       service=captures['service'],
                       selector=captures['selector'],
                       data_filters=filters)
        else:
            return None

    def __str__(self):
        res = ''
        if not self.valid:
            return res

        if self.protocol:
            res += self.protocol
            res += '://'

            if self.service and self.service != self.protocol:
                res += self.service
            res += '/'
        res += self.device
        res += '/'
        res += self.property
        if self.field:
            res += '#'
            res += self.field
        return res + CContext.to_string_suffix(data_filters=self.data_filters, selector=self.selector)
