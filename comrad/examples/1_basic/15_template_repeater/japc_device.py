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
    Demo device produces "Tick"/"Tock" string values every second
    on a 'Acquistion#Demo' field.
    """
    frequency = 1

    def __init__(self, name: str):
        super().__init__(name=name, device_properties=(
            Acquisition(name='Acquisition', fields=(
                FieldType(name='IntVal', datatype='int', initial_value=0),
            )),
        ))
        self._timer = RepeatedTimer(1 / self.frequency, self.time_tick)

    def time_tick(self):
        """Callback on timer fire."""
        self.set_state({'Acquisition#IntVal': random.randint(1, 101)}, '')


def create_device():
    """Entrypoint for the example to start simulating data flow."""
    d1 = DemoDevice(name='Dev1')
    d1.time_tick() # Trigger the first/initial tick (gives us nicer values).
    d2 = DemoDevice(name='Dev2')
    d2.time_tick()
    return System(devices=[d1, d2])