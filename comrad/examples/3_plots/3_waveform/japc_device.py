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

from datetime import datetime
import numpy as np
import math


class DemoDevice(Device):

    frequency = 60

    def __init__(self):
        """
        Demo Device with a single Property 'Acquisition' containing a field
        'Curve'. The field is a one dimensional numpy array which is able to
        is representing a scaled sinus curve. Over time this sinus curve will
        scale smaller and bigger.
        """
        super().__init__(
            name='DemoDevice',
            device_properties=(
                Acquisition(
                    name='Acquisition',
                    fields=(
                        FieldType(
                            name='Curve',
                            datatype='ndarray',
                        ),
                    ),
                ),
            ),
        )
        self.y_base = np.sin(np.linspace(0, 2 * math.pi, 100))
        self._timer = RepeatedTimer(1 / self.frequency, self.emit_point)

    def emit_point(self) -> None:
        """Scale the sinus curve according to the current time stamp."""
        y = self.y_base * np.sin(datetime.now().timestamp())
        self.set_state({'Acquisition#Curve': y}, '')


def create_device():
    d = DemoDevice()
    d.emit_point()
    return System(devices=[d])
