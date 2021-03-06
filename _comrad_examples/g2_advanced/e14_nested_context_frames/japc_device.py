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
    Demo device produces separate string values every second
    on a 'Acquistion#Demo' field for one of the available timing selectors (each time randomly).
    """
    frequency = 1

    def __init__(self):
        super().__init__(
            name='DemoDevice',
            device_properties=(
                Acquisition(name='Acquisition', fields=(
                    FieldType(name='Demo', datatype='str', initial_value='-'),
                )),
            ),
            timing_selectors=(
                'PSB.USER.TOF',
                'PSB.USER.AD',
                'SPS.USER.AWAKE',
                '',
            ),
        )
        self._primary_cycle_cnt = 0
        self._secondary_cycle_cnt = 0
        self._tertiary_cycle_cnt = 0
        self._no_cycle_cnt = 0
        self._timer = RepeatedTimer(1 / self.frequency, self.time_tick)

    def time_tick(self):
        """Callback on timer fire."""
        rand = random.getrandbits(2)
        if rand == 0:
            self._primary_cycle_cnt += 1
            self.set_state(new_values={'Acquisition#Demo': f'nTOF-{self._primary_cycle_cnt}'},
                           timing_selector='PSB.USER.TOF')
        elif rand == 1:
            self._secondary_cycle_cnt += 1
            self.set_state(new_values={'Acquisition#Demo': f'AD-{self._secondary_cycle_cnt}'},
                           timing_selector='PSB.USER.AD')
        elif rand == 2:
            self._tertiary_cycle_cnt += 1
            self.set_state(new_values={'Acquisition#Demo': f'AWAKE-{self._tertiary_cycle_cnt}'},
                           timing_selector='SPS.USER.AWAKE')
        else:
            self._no_cycle_cnt += 1
            self.set_state(new_values={'Acquisition#Demo': f'empty-{self._tertiary_cycle_cnt}'},
                           timing_selector='')


def create_device():
    """Entrypoint for the example to start simulating data flow."""
    d = DemoDevice()
    return System(devices=[d])
