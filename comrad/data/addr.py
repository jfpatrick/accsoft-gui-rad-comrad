from typing import Optional


class ControlEndpointAddress:

    def __init__(self,
                 device: str,
                 prop: str,
                 field: Optional[str] = None,
                 protocol: Optional[str] = None,
                 service: Optional[str] = None,
                 selector: Optional[str] = None):
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
        """
        self.device = device
        self.property = prop
        self.field = field
        self.protocol = protocol
        self.service = service
        self.selector = selector

    @property
    def valid(self) -> bool:
        """Address is complete and can be successfully resolved."""
        return (len(self.device) > 0 and len(self.property) > 0 and (
                (self.protocol is None and self.service is None)
                or self.protocol is not None))

    @classmethod
    def from_string(cls, input: str) -> Optional['ControlEndpointAddress']:
        """
        Factory method to construct an object from string representation.

        Args:
            input: String formatted according to the device-property specification.
        """
        import re
        mo = re.match(r'^((?P<protocol>[^:/]+)://(?P<service>[^/]+)?/)?(?P<device>[^/#@\n\t]+)/(?P<property>[^/#@\n\t]+)(#(?P<field>[^@\n\t]+))?(@(?P<selector>[^\.]+\.[^\.]+\.[^\.]+))?$', input)
        if mo and mo.groups():
            captures = mo.groupdict()
            return cls(device=captures['device'],
                       prop=captures['property'],
                       field=captures['field'],
                       protocol=captures['protocol'],
                       service=captures['service'],
                       selector=captures['selector'])
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
        if self.selector:
            res += '@'
            res += self.selector
        return res
