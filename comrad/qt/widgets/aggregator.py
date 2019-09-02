import logging
import numpy as np
from typing import List, Dict, Optional, Set, Any
from pydm.widgets.base import PyDMWidget
from pydm.widgets.channel import PyDMChannel
from pydm.data_plugins.plugin import PyDMConnection
from pydm.utilities import is_qt_designer
from qtpy.QtWidgets import QWidget, QFrame, QVBoxLayout, QLabel
from qtpy.QtCore import Property, Signal, Slot, Q_ENUM, Qt
from ..value_transform import ValueTransformationBase


logger = logging.getLogger(__name__)


class GeneratorTrigger:
    Any = 0
    AggregatedLast = 1
    AggregatedFirst = 2


class CValueAggregator(QWidget, PyDMWidget, ValueTransformationBase, GeneratorTrigger):
    Q_ENUM(GeneratorTrigger)
    GeneratorTrigger = GeneratorTrigger

    # Emitted when the user changes the value.
    updateTriggered = Signal([int], [float], [str], [bool], [np.ndarray])

    def __init__(self, parent: QWidget = None, init_channels: List[str] = None):
        """
        Widget that allows defining logic to expose a new value calculated on the fly.

        Args:
            parent: The parent widget for the generator.
            init_channel: The channel to be used by the widget.
        """
        QWidget.__init__(self, parent)
        PyDMWidget.__init__(self)
        ValueTransformationBase.__init__(self)
        self._channel_ids: List[str] = []
        self._active: bool = True
        # This type defines how often an update is fired and when cached values get overwritten
        self._trigger_type = self.GeneratorTrigger.Any

        # This table contains cached values of the channels that can be accessed from the generator logic.
        # Keys are channel addresses and values are cached values
        self._values: Dict[str, Any] = {}
        # This contains channels ids that have not yet updated their values and have not cached them
        # in _values
        self._obsolete_values: Optional[Set] = None

        if is_qt_designer():
            self._setup_ui_for_designer()
        else:
            # Trigger connection creation
            self.inputChannels = init_channels or []
            # Should be invisible in runtime
            self.hide()

    @Property('QStringList')
    def inputChannels(self) -> List[str]:
        """
        This property exposes PyDMWidget channels that we use as input primarily.

        Returns:
            List of PyDMChannel objects.
        """
        return self._channel_ids

    @inputChannels.setter
    def inputChannels(self, channels: List[str]):
        """
        Channel setter exposed to Qt Designer.

        Args:
            channels: List of new channels.
        """
        new_channels = set(channels)
        old_channels = set(self._channel_ids)

        channels_to_add = new_channels.difference(old_channels)
        channels_to_remove = old_channels.difference(new_channels)

        self._channel_ids = channels

        # Remove old connections
        channel_objs = self.channels()
        if channel_objs:
            for channel in channel_objs:
                if channel.address not in channels_to_remove:
                    continue
                channel.disconnect()
                self._channels.remove(channel)

        # Update trigger table
        if self._trigger_type == self.GeneratorTrigger.Any:
            self._values.clear()
            self._obsolete_values = None
        else:
            self._values = dict(self._channel_ids)
            self._obsolete_values = set(self._channel_ids)

        # Add new connections
        for addr in channels_to_add:
            # This could be a generalized approach to put into PyDMWidget,
            # currently it relies only on a single widget presence, but if changed to
            # work with multiple ones, this code could be reused from the base class...
            channel = PyDMChannel(address=addr, value_slot=self.channelValueChanged)
            channel.connect()
            self._channels.append(channel)

    @Slot(int)
    @Slot(float)
    @Slot(str)
    @Slot(bool)
    @Slot(np.ndarray)
    def channelValueChanged(self, new_val: Any):
        """
        Callback when a new value arrives on any of the inputChannels.

        Args:
            new_val: New value.
        """

        # This is the way to identify the channel, instead of initially used functools.partial,
        # which results in reference cycle
        conn: Optional[PyDMConnection] = self.sender()
        if conn is None:
            return
        channel_id: str = conn.address
        if channel_id.startswith('/'):
            # Because PyDM does not natively support /// notation of JAPC, leading slash is left
            # in the address. We need to remove it to not confuse the user.
            channel_id = channel_id[1:]

        if self._trigger_type == self.GeneratorTrigger.Any:
            self._values[channel_id] = new_val
            self._trigger_update()
            return

        if self._trigger_type == self.GeneratorTrigger.AggregatedFirst and channel_id not in self._obsolete_values:
            return

        # Common logic for AggregatedFirst and AggregatedLast from here on
        self._values[channel_id] = new_val
        try:
            self._obsolete_values.remove(channel_id)
        except KeyError:
            pass

        # Now empty
        if not self._obsolete_values:
            self._obsolete_values = set(self._channel_ids)
            self._trigger_update()

    @Slot(bool)
    def setActive(self, val):
        if val != self._active:
            self._active = val
            channels: List[PyDMChannel] = self.channels()
            for ch in channels:
                if ch is None:
                    continue
                if val:
                    ch.connect()
                else:
                    ch.disconnect()

    @Property(GeneratorTrigger)
    def generatorTrigger(self):
        """
        Trigger defines when the output is fired.

         - OnEveryValue will fire an update on any new incoming value from any channel
         - OnAggregatedValue will wait until all channels deliver value since the last
           update and only then fire a new one

        Returns:
            New update triggering type.
        """
        return self._trigger_type

    @generatorTrigger.setter
    def generatorTrigger(self, new_type: int):
        """
        Update for the generator trigger type.

        This update will clean up the hash table or will recreate it based on the incoming type.

        Args:
            new_type: New triggering type.
        """
        if self._trigger_type != new_type:
            if new_type == self.GeneratorTrigger.Any:
                self._obsolete_values = None
            elif self._channel_ids:
                # AggregatedFirst and AggregatedLast logic here
                self._obsolete_values = set(self._channel_ids)
            self._trigger_type = new_type

    @Property(str, designable=False)
    def channel(self):
        return

    @channel.setter
    def channel(self, ch):
        return

    @Property(str, designable=False)
    def alarmSensitiveBorder(self):
        return

    @alarmSensitiveBorder.setter
    def alarmSensitiveBorder(self, ch):
        logger.info(f'alarmSensitiveBorder property is disabled for the {type(self).__name__} widget.')
        return

    @Property(str, designable=False)
    def alarmSensitiveContent(self):
        return

    @alarmSensitiveContent.setter
    def alarmSensitiveContent(self, ch):
        logger.info(f'alarmSensitiveContent property is disabled for the {type(self).__name__} widget.')
        return

    @Property('QSize', designable=False)
    def minimumSize(self):
        return super().minimumSize()

    @Property('QSize', designable=False)
    def maximumSize(self):
        return super().maximumSize()

    @Property('QSize', designable=False)
    def baseSize(self):
        return super().baseSize()

    @Property('QSize', designable=False)
    def sizeIncrement(self):
        return super().sizeIncrement()

    def _trigger_update(self):
        if ((not self.valueTransformation and not self.snippetFilename)
                or is_qt_designer()):
            # Avoid code evaluation in Designer, as it can produce unnecessary errors with broken code
            return

        transform = self.cached_value_transformation()
        if not transform:
            return

        result = transform(values=self._values)
        if result is None:
            # With None, it will be impossible to determine the signal override, therefore we simply don't send it
            return
        try:
            self.updateTriggered[type(result)].emit(result)
        except KeyError:
            pass

    def _setup_ui_for_designer(self):
        """Improves visibility of the widget in Designer"""
        width = 40
        height = 25
        frame = QFrame(self)
        frame.setFrameShape(QFrame.Box)
        frame.setFrameShadow(QFrame.Sunken)
        frame.resize(width, height)
        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addChildWidget(frame)
        self.setMinimumWidth(width)
        self.setMinimumHeight(height)
        self.setMaximumWidth(width)
        self.setMaximumHeight(height)
        self.resize(width, height)
        layout = QVBoxLayout()
        frame.setLayout(layout)
        label = QLabel()
        label.setText('%')
        label.resize(width, height)
        label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        layout.addChildWidget(label)
