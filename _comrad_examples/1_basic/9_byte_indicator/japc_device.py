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
from enum import IntEnum, IntFlag


class DemoDevice(Device):
    """
    Demo device that exposes 3 acquisition fields 'Acquisition#IntVal', 'Acquisition#BitEnumVal',
    and 'Acquisition#BitEnumValNum'.
    """
    frequency = 1
    num_bits = 5
    max_val = 2 ** num_bits

    names = [f'OPTION{idx}' for idx in range(2 ** num_bits)]
    MyEnum = IntEnum('MyEnum', names=names, start=0)
    MyBitMask = IntFlag('MyBitMask', names=[f'BIT{idx}' for idx in range(num_bits)])

    def __init__(self):
        int_val: int = 0
        super().__init__(name='DemoDevice', device_properties=(
            Acquisition(name='Acquisition', fields=(
                FieldType(name='IntVal', datatype='int', initial_value=int_val),
                FieldType(name='BitEnumVal', datatype=DemoDevice.MyBitMask, initial_value=0),
                FieldType(name='BitEnumValNum', datatype=DemoDevice.MyEnum),
            )),
        ))
        self._int_val = int_val
        self._bit_enum_val = DemoDevice.MyEnum.OPTION0
        self._timer = RepeatedTimer(1 / self.frequency, self.time_tick)

    def time_tick(self):
        """Callback on timer fire."""
        self._int_val += 1

        new_bit_enum_val = self._bit_enum_val.value + 1
        if new_bit_enum_val >= self.max_val:
            new_bit_enum_val = 0
        self._bit_enum_val = DemoDevice.MyEnum(new_bit_enum_val)

        new_bit_mask = 0
        for idx in range(self.num_bits):
            enum_code = 1 << idx
            is_set = bool(self._bit_enum_val.value & enum_code)
            if is_set:
                new_bit_mask |= enum_code

        self.set_state(new_values={
            'Acquisition#IntVal': self._int_val,
            'Acquisition#BitEnumValNum': self._bit_enum_val,
            'Acquisition#BitEnumVal': new_bit_mask,
        }, timing_selector='')


def create_device():
    """Entrypoint for the example to start simulating data flow."""
    d = DemoDevice()
    d.time_tick()  # Trigger the first/initial tick (gives us nicer values).
    return System(devices=[d])
