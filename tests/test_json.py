import json
from enum import Enum, IntEnum
from comrad.json import CJSONSerializable, CJSONEncoder


def test_json_encoder():

    class FakeSerializable(CJSONSerializable):

        def __init__(self, val: int = 0):
            super().__init__()
            self.val = val

        @classmethod
        def from_json(cls, contents):
            return cls()

        def to_json(self):
            return {
                'val': self.val,
            }

    class FakeEnum(Enum):
        TEST = 'TEST'

    class FakeIntEnum(IntEnum):
        TEST = 45

    sample = {
        'obj': FakeSerializable(val=78),
        'enum': FakeEnum.TEST,
        'intenum': FakeIntEnum.TEST,
    }

    res = json.dumps(sample, cls=CJSONEncoder)
    assert res == '{"obj": {"val": 78}, "enum": "TEST", "intenum": 45}'
