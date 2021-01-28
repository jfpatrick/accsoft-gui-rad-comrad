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
    Demo device exposes 2 numerical fields in a setting property
    """

    def __init__(self):
        super().__init__(name='DemoDevice', device_properties=(
            Setting(name='Settings', fields=(
                FieldType(name='readOnlyField', datatype='int', initial_value=3),
                FieldType(name='writableField', datatype='float', initial_value=0.5),
                FieldType(name='readOnlyField_units', datatype='str', initial_value='kEUR'),
                FieldType(name='writableField_units', datatype='str', initial_value='kCHF'),
                FieldType(name='writableField_min', datatype='float', initial_value=0.1),
                FieldType(name='writableField_max', datatype='float', initial_value=10.1),
                FieldType(name='readOnlyField_min', datatype='int', initial_value=0),
                FieldType(name='readOnlyField_max', datatype='int', initial_value=10),
            )),
        ))


def create_device():
    """Entrypoint for the example to start simulating data flow."""
    d = DemoDevice()
    return System(devices=[d])
