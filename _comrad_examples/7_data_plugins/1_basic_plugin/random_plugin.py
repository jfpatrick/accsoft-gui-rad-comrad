import random
import re
import logging
from typing import Optional
from qtpy.QtCore import QTimer
from comrad.data_plugins import CDataPlugin, CDataConnection, CChannel, CChannelData


logger = logging.getLogger(__name__)


class RandomIntConnection(CDataConnection):
    """
    This connection accepts channels with address like "random://[0,100]",
    where digits define the range for the random numbers to be generated.
    New value is generated every second.
    """

    def __init__(self, channel: CChannel, address: str, protocol=None, parent=None):
        super().__init__(channel=channel, address=address, protocol=protocol, parent=parent)
        self._timer: Optional[QTimer] = None

        # Parse random value's ranges that are encoded in the channel address
        m = re.match(pattern=r'.*\[[\t\ ]*(?P<min>\d+)[\t\ ]*,[\t\ ]*(?P<max>\d+)[\t\ ]*\].*',
                     string=address)
        if m is None:
            logger.error(f'Channel address "{address}" is malformed. Please use this format: "random://[0,100]".')
        else:
            self._range = [int(m.group('min')), int(m.group('max'))]
            self.add_listener(channel)

    def add_listener(self, channel: CChannel):
        super().add_listener(channel)

        if self.connected:
            # Time has already been set up, no need to do that again
            return

        self._timer = QTimer()
        self._timer.timeout.connect(self.on_timer_fire)
        self._timer.start(1000)
        self.connected = True

    def close(self):
        if self._timer:
            self._timer.stop()
            self._timer = None
        super().close()

    def on_timer_fire(self):
        """
        This is our simulated notification from the control system.
        It produces a random value and that is defined in range specified by the channel address
        and then pushes it to listeners."""
        new_val = random.randint(*self._range)
        packet = CChannelData(value=new_val, meta_info={})
        self.new_value_signal.emit(packet)


class RandomPlugin(CDataPlugin):
    """
    ComRAD data plugin that handles communications with the channels on "random://" scheme.
    """

    protocol = 'random'
    connection_class = RandomIntConnection
