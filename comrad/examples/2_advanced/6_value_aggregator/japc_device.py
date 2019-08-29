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
    Demo device produces two fields with random integers in range (0, 100).
    """
    frequency = 1

    def __init__(self):
        super().__init__(name='DemoDevice', device_properties=(
            Acquisition(name='Acquisition', fields=(
                FieldType(name='ChannelA', datatype='int', initial_value=0),
                FieldType(name='ChannelB', datatype='int', initial_value=0),
            )),
        ))
        self._is_tick = True
        self._timer = RepeatedTimer(1 / self.frequency, self.time_tick)

    def time_tick(self):
        """Callback on timer fire."""
        self.set_state(new_values={
            'Acquisition#ChannelA': random.randint(0, 100),
            'Acquisition#ChannelB': random.randint(0, 100),
        }, timing_selector='')


def create_device():
    """Entrypoint for the example to start simulating data flow."""
    d = DemoDevice()
    d.time_tick() # Trigger the first/initial tick (gives us nicer values).
    return System(devices=[d])