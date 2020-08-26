import logging
from typing import Optional, Dict
from dataclasses import dataclass
from qtpy.QtCore import QTimer
from comrad.data_plugins import CDataPlugin, CCommonDataConnection, CChannel, CChannelData


logger = logging.getLogger(__name__)


@dataclass
class CountingControlSystem:
    counter: int = 0

    def reset(self, val: int):
        self.counter = val

    @property
    def next_counter_value(self) -> int:
        returned_val = self.counter
        self.counter += 1
        return returned_val


_control_system = CountingControlSystem()


class CountingConnection(CCommonDataConnection):
    """
    This connection accepts channels with address like "count://3",
    where digits define the range for the random numbers to be generated.
    New value is generated every second.
    """

    def __init__(self, channel: CChannel, address: str, protocol=None, parent=None):
        super().__init__(channel=channel, address=address, protocol=protocol, parent=parent)
        self._timer: Optional[QTimer] = None

        # Parse counter's initial value in the channel address
        try:
            init_val = int(address)
        except ValueError:
            logger.error(f'Channel address "{address}" is malformed. Please use an integer value, e.g. "count://3".')
            return

        _control_system.reset(init_val)
        self.add_listener(channel)

    def get(self, callback):
        callback(_control_system.next_counter_value)

    def set(self, value: Dict[str, int]):
        try:
            new_counter_val = value['counter']
        except KeyError:
            return
        _control_system.reset(new_counter_val)

    def subscribe(self, callback):
        if self._timer is None:
            self._timer = QTimer()
            self._timer.timeout.connect(lambda: callback(_control_system.next_counter_value))
            self._timer.start(1000)
        self.connected = True

    def unsubscribe(self):
        if self._timer:
            self._timer.stop()
            self._timer = None

    def process_incoming_value(self, value: int):
        # The incoming value here is defined by the way how we call "callback" in get() and timer.timeout.connect().
        return CChannelData(value={'counter': value}, meta_info={})


class CounterPlugin(CDataPlugin):
    """
    ComRAD data plugin that handles communications with the channels on "count://" scheme.
    """

    protocol = 'count'
    connection_class = CountingConnection
