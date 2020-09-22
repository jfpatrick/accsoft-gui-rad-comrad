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
import numpy as np
from datetime import datetime


class DemoDevice(Device):

    """
    Demo device producing arrays of random float values
    """
    frequency = 1
    total_injection_count = 5

    def __init__(self):
        super().__init__(
            name='DemoDevice',
            device_properties=(
                Acquisition(
                    name='Acquisition',
                    fields=[
                        FieldType(name='injection',
                                  datatype='list'),
                    ],
                ),
            ),
        )
        self._timer = RepeatedTimer(1 / self.frequency, self.emit_array)

    def emit_array(self):
        """Callback on timer fire."""
        timestamp = datetime.now().timestamp()
        values = np.random.rand(self.total_injection_count)
        missing_values_cnt = random.randint(0, self.total_injection_count - 1)
        for _ in range(missing_values_cnt):
            missing_idx = random.randint(0, self.total_injection_count - 1)
            values[missing_idx] = 0.0   # Make zero, signifying that injection event should be ignored

        self.set_state({'Acquisition#injection': [
            values,        # y value(s)
            timestamp,     # x value
        ]}, '')


def create_device():
    d = DemoDevice()
    d.emit_array()  # Trigger the first/initial tick (gives us nicer values).
    return System(devices=[d])
