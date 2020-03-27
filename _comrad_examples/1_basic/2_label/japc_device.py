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
    Demo device produces "Tick"/"Tock" string values every second
    on a 'Acquistion#Demo' field.
    """
    frequency = 1

    def __init__(self):
        super().__init__(name='DemoDevice', device_properties=(
            Acquisition(name='Acquisition', fields=(
                FieldType(name='Demo', datatype='str', initial_value='Tick'),
            )),
        ))
        self._is_tick = True
        self._timer = RepeatedTimer(1 / self.frequency, self.time_tick)

    def time_tick(self):
        """Callback on timer fire."""
        val = 'Tick' if self._is_tick else 'Tock'
        self.set_state({'Acquisition#Demo': val}, '')
        self._is_tick = not self._is_tick


def create_device():
    """Entrypoint for the example to start simulating data flow."""
    d = DemoDevice()
    d.time_tick()  # Trigger the first/initial tick (gives us nicer values).
    return System(devices=[d])
