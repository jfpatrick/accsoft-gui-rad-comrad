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


class DemoDevice(Device):
    """
    Demo device that exposes a single readable field 'Acquisition#Demo'.

    This field produces a numeric value that bounces in range 0.0-1.0
    with 0.01 increments.
    """
    frequency = 30

    def __init__(self):
        self._val: float = 0.0
        self._grow: bool = True
        super().__init__(name='DemoDevice', device_properties=(
            Acquisition(name='Acquisition', fields=(
                FieldType(name='Demo', datatype='float', initial_value=self._val),
            )),
        ))
        self._timer = RepeatedTimer(1 / self.frequency, self.time_tick)

    def time_tick(self):
        """Callback on timer fire."""
        if self._val > 0.99:
            self._grow = False
        elif self._val < 0.01:
            self._grow = True

        if self._grow:
            self._val += 0.01
        else:
            self._val -= 0.01
        self.set_state({'Acquisition#Demo': self._val}, '')


def create_device():
    """Entrypoint for the example to start simulating data flow."""
    d = DemoDevice()
    d.time_tick()  # Trigger the first/initial tick (gives us nicer values).
    return System(devices=[d])
