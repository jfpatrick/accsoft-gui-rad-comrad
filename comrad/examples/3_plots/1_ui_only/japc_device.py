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

    def emit_point(self, initial: bool = False):
        """Callback on timer fire."""
        timestamp = datetime.now().timestamp()
        random_value = random.random()
        random_text = f'L {int(random_value * 10)}'
        random_color = ['r', 'b', 'g'][int(random_value * 3)]
        # The order of values is important, see accwidget.graph's
        # SignalBoundDataSource for the order of updates
        self.set_state({'Acquisition#RandomPoint': [
            random_value,  # y value
            timestamp,     # x value
        ]}, '')
        self.set_state({'Acquisition#RandomBar': [
            random_value,  # height
            0.0,           # y value
            timestamp,     # x value
        ]}, '')
        if initial or self.emit_threshold % 4 == 0:
            self.set_state({'Acquisition#RandomInjectionBar': [
                1.0,           # height
                random_value,  # y value
                0.5,           # width
                timestamp,     # x value
                random_text,   # label
            ]}, '')
        if initial or self.emit_threshold % 10 == 0:
            self.set_state({'Acquisition#RandomTimestampMarker': [
                timestamp,     # x value
                random_text,   # label
                random_color,  # color
            ]}, '')

        if self.emit_threshold > 1:
            self.emit_threshold -= 1
        else:
            self.emit_threshold = 10


def create_device():
    d = DemoDevice()
    d.emit_point(initial=True)  # Trigger the first/initial tick (gives us nicer values).
    return System(devices=[d])
