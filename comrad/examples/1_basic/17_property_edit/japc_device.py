# This file creates demo devices that simulate data
# broadcast via PyJapc. It uses PAPC - a PyJapc
# Python simulation replacement. At runtime, PyJapc will
# be substituted with this interface and the data will
# be coming not from a real control system but devices
# created in this file. Hence, you can run the example
# outside of TN with deterministic data.

from typing import Mapping, Any
from papc.device import Device
from papc.system import System
from papc.deviceproperty import Setting, Acquisition
from papc.fieldtype import FieldType


class ReprFieldType(FieldType):

    def update_from_dependencies(self, dependencies: Mapping[str, Any]):
        import json
        return json.dumps(dependencies, indent=4)


class DemoDevice(Device):
    """
    Demo device that exposes a property with multiple fields and a string representation property of it, SettingsRepr.
    """

    def __init__(self):
        super().__init__(name='DemoDevice', device_properties=(
            Setting(name='Settings', fields=(
                FieldType(name='IntVal', datatype='int', initial_value=0),
                FieldType(name='FloatVal', datatype='float', initial_value=0.5),
                FieldType(name='StrVal', datatype='str', initial_value='test'),
                FieldType(name='BoolVal', datatype='bool', initial_value=True),
                FieldType(name='EnumVal', datatype='int', initial_value=1),
            )),
            Acquisition(name='SettingsRepr', fields=(
                ReprFieldType(name='str', datatype='str', initial_value='', dependencies=frozenset([
                    'Settings#IntVal',
                    'Settings#FloatVal',
                    'Settings#StrVal',
                    'Settings#BoolVal',
                    'Settings#EnumVal',
                ])),
            )),
        ))


def create_device():
    """Entrypoint for the example to start simulating data flow."""
    d = DemoDevice()
    return System(devices=[d])
