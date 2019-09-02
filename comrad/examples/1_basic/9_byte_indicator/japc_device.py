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
    Demo device that exposes a single writable setting 'Settings#FloatVal'.
    """
    frequency = 1
    num_bits = 5
    max_val = 2 ** num_bits

    def __init__(self):
        int_val: int = 0
        super().__init__(name='DemoDevice', device_properties=(
            Acquisition(name='Acquisition', fields=(
                FieldType(name='IntVal', datatype='int', initial_value=int_val),
                FieldType(name='BitEnumVal', datatype='list', initial_value=[]),
                FieldType(name='BitEnumValNum', datatype='int', initial_value=0),
            )),
        ))
        self._int_val = int_val
        self._bit_enum_val: int = 0
        self._timer = RepeatedTimer(1 / self.frequency, self.time_tick)

    def time_tick(self):
        """Callback on timer fire."""
        self._int_val += 1

        self._bit_enum_val += 1
        if self._bit_enum_val >= self.max_val:
            self._bit_enum_val = 0

        new_list = []
        for idx in range(self.num_bits):
            bit_val = 1 << idx
            is_set = bool(self._bit_enum_val & bit_val)
            if is_set:
                new_list.append((bit_val, f'Bit {idx}'))

        self.set_state(new_values={
            'Acquisition#IntVal': self._int_val,
            'Acquisition#BitEnumValNum': self._bit_enum_val,
            'Acquisition#BitEnumVal': new_list,
        }, timing_selector='')


def create_device():
    """Entrypoint for the example to start simulating data flow."""
    d = DemoDevice()
    d.time_tick()  # Trigger the first/initial tick (gives us nicer values).
    return System(devices=[d])
