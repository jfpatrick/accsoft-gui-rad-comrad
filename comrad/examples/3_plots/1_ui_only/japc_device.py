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
from datetime import datetime


class DemoDevice(Device):

    """
    Demo device producing some random float values
    """
    frequency = 1

    def __init__(self):
        super().__init__(
            name='DemoDevice',
            device_properties=(
                Acquisition(
                    name='Acquisition',
                    fields=(
                        FieldType(
                            name='RandomPoint',
                            datatype='list',
                        ),
                        FieldType(
                            name='RandomBar',
                            datatype='list',
                        ),
                        FieldType(
                            name='RandomInjectionBar',
                            datatype='list',
                        ),
                        FieldType(
                            name='RandomTimestampMarker',
                            datatype='list',
                        ),
                    ),
                ),
            ),
        )
        self._timer = RepeatedTimer(1 / self.frequency, self.emit_point)
        self.emit_threshold = 9

    def emit_point(self):
        """Callback on timer fire."""
        timestamp = datetime.now().timestamp()
        random_value = random.random()
        random_text = f'L {int(random_value * 10)}'
        random_color = ['r', 'b', 'g'][int(random_value * 3)]
        self.set_state({'Acquisition#RandomPoint': [
            timestamp,           # x value
            random_value,        # y value
        ]}, '')
        self.set_state({'Acquisition#RandomBar': [
            timestamp,           # x value
            0.5 * random_value,  # y value
            random_value,        # height
        ]}, '')
        if self.emit_threshold % 4 == 0:
            self.set_state({'Acquisition#RandomInjectionBar': [
                timestamp,           # x value
                random_value,        # y value
                1.0,                 # height
                0.5,                 # width
                random_text,         # label
            ]}, '')
        if self.emit_threshold % 10 == 0:
            self.set_state({'Acquisition#RandomTimestampMarker': [
                timestamp,           # x value
                random_color,        # color
                random_text,         # label
            ]}, '')

        if self.emit_threshold > 1:
            self.emit_threshold -= 1
        else:
            self.emit_threshold = 10


def create_device():
    d = DemoDevice()
    d.emit_point()  # Trigger the first/initial tick (gives us nicer values).
    return System(devices=[d])
