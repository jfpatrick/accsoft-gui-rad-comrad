# This file creates demo devices that simulate data
# broadcast via PyJapc. It uses PAPC - a PyJapc
# Python simulation replacement. At runtime, PyJapc will
# be substituted with this interface and the data will
# be coming not from a real control system but devices
# created in this file. Hence, you can run the example
# outside of TN with deterministic data.

from papc.device import Device
from papc.system import System
from papc.deviceproperty import Setting
from papc.fieldtype import FieldType


class DemoDevice(Device):
    """
    Demo device that exposes a single writable setting 'Settings#BoolVal'.
    """

    def __init__(self):
        super().__init__(name='DemoDevice', device_properties=(
            Setting(name='Settings', fields=(
                FieldType(name='BoolVal', datatype='bool', initial_value=False),
            )),
        ))


def create_device():
    """Entrypoint for the example to start simulating data flow."""
    d = DemoDevice()
    return System(devices=[d])
