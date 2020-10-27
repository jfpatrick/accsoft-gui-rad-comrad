# This file creates demo devices that simulate data
# broadcast via PyJapc. It uses PAPC - a PyJapc
# Python simulation replacement. At runtime, PyJapc will
# be substituted with this interface and the data will
# be coming not from a real control system but devices
# created in this file. Hence, you can run the example
# outside of TN with deterministic data.

from papc.device import Device
from papc.system import System
from papc.deviceproperty import Acquisition
from papc.fieldtype import FieldType
from papc.simulator.trig import RepeatedTimer

import random


class DemoDevice(Device):

    """
    Demo device producing arrays of random float values
    """
    frequency = 1

    def __init__(self):
        super().__init__(
            name='DemoDevice',
            device_properties=(
                Acquisition(
                    name='Acquisition',
                    fields=[
                        FieldType(name='field1', datatype='int'),
                        FieldType(name='field2', datatype='int'),
                    ],
                ),
            ),
        )
        self._timer = RepeatedTimer(1 / self.frequency, self.emit_values)

    def emit_values(self):
        """Callback on timer fire."""
        f1 = random.randint(0, 10)
        f2 = random.randint(0, 10)

        self.set_state({
            'Acquisition#field1': f1,
            'Acquisition#field2': f2,
        }, '')


def create_device():
    d = DemoDevice()
    d.emit_values()  # Trigger the first/initial tick (gives us nicer values).
    return System(devices=[d])
