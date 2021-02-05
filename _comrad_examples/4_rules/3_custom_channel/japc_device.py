# This file creates demo devices that simulate data
# broadcast via PyJapc. It uses PAPC - a PyJapc
# Python simulation replacement. At runtime, PyJapc will
# be substituted with this interface and the data will
# be coming not from a real control system but devices
# created in this file. Hence, you can run the example
# outside of TN with deterministic data.

from papc.device import Device, TimingSelector
from papc.system import System
from papc.deviceproperty import Acquisition
from papc.fieldtype import FieldType
from papc.simulator.trig import RepeatedTimer


class DemoDevice(Device):
    """
    Demo device that exposes several properties with a single readable field 'Demo'.

    This field produces a numeric value that bounces in range 0.0-1.0
    with 0.01 increments.
    """
    frequency = 30

    def __init__(self):
        self.val: float = 0.0
        self.ppm_val: float = 0.3
        self.non_ppm_val: float = 0.6
        self.grow: bool = True
        self.grow_ppm: bool = True
        self.grow_non_ppm: bool = True
        super().__init__(name='DemoDevice',
                         device_properties=(
                             Acquisition(name='Acquisition', fields=(
                                 FieldType(name='Demo', datatype='float', initial_value=self.val),
                             )),
                             Acquisition(name='Color', fields=(
                                 FieldType(name='Demo', datatype='float', initial_value=self.non_ppm_val),
                             )),
                             Acquisition(name='ColorMultiplexed', fields=(
                                 FieldType(name='Demo', datatype='float', initial_value=self.ppm_val),
                             )),
                         ),
                         timing_selectors=(
                             TimingSelector(''),
                             TimingSelector(''),
                             TimingSelector('SAMPLE.USER.MD1'),
                         ))
        self._timer = RepeatedTimer(1 / self.frequency, self.time_tick)

    def advance_val(self, val_name: str, grow_flag: str) -> float:
        val = getattr(self, val_name)

        if val > 0.99:
            setattr(self, grow_flag, False)
        elif val < 0.01:
            setattr(self, grow_flag, True)

        grow = getattr(self, grow_flag)

        if grow:
            val += 0.01
        else:
            val -= 0.01

        setattr(self, val_name, val)
        return val

    def time_tick(self):
        """Callback on timer fire."""
        self.set_state({
            'Acquisition#Demo': self.advance_val('val', 'grow'),
            'Color#Demo': self.advance_val('non_ppm_val', 'grow_non_ppm'),
        }, '')
        self.set_state({
            'ColorMultiplexed#Demo': self.advance_val('ppm_val', 'grow_ppm'),
        }, 'SAMPLE.USER.MD1')


def create_device():
    """Entrypoint for the example to start simulating data flow."""
    d = DemoDevice()
    d.time_tick()  # Trigger the first/initial tick (gives us nicer values).
    return System(devices=[d])
