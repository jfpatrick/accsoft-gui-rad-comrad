import logging
import numpy as np
from typing import List, Dict, Optional, Set, Any
from pydm.widgets.base import PyDMWidget
from pydm.widgets.channel import PyDMChannel
from pydm.data_plugins.plugin import PyDMConnection
from pydm.utilities import is_qt_designer
from qtpy.QtWidgets import QWidget, QFrame, QVBoxLayout, QLabel, QSizePolicy
from qtpy.QtCore import Property, Signal, Slot, Q_ENUM, Qt, QSize
from .mixins import HideUnusedFeaturesMixin, InitializedMixin, superclass_deprecated
from .value_transform import ValueTransformationBase


logger = logging.getLogger(__name__)


# This class cannot inherit from Enum or derivatives because it will cause Qt Designer to complain about
# metaclass incompatibility when this class will be inherited by the widget class
class GeneratorTrigger:
    """Enum defining when generator sequence must be triggered."""

    Any = 0
    """Any of the incoming values arriving."""

    AggregatedLast = 1
    """All values have been updated since the last trigger."""

    AggregatedFirst = 2
    """First new value arriving since the last trigger."""


class CValueAggregator(QWidget, InitializedMixin, HideUnusedFeaturesMixin, PyDMWidget, ValueTransformationBase, GeneratorTrigger):
    Q_ENUM(GeneratorTrigger)
    GeneratorTrigger = GeneratorTrigger

    # Emitted when the user changes the value.
    updateTriggered = Signal([int], [float], [str], [bool], [np.ndarray])

    def __init__(self, parent: Optional[QWidget] = None, init_channels: Optional[List[str]] = None):
        """
        Widget that allows defining logic to expose a new value calculated on the fly.

        Args:
            parent: The parent widget for the generator.
            init_channel: The channel to be used by the widget.
        """
        QWidget.__init__(self, parent)
        InitializedMixin.__init__(self)
        HideUnusedFeaturesMixin.__init__(self)
        PyDMWidget.__init__(self)
        ValueTransformationBase.__init__(self)
        self._widget_initialized = True
        self._channel_ids: List[str] = []
        self._active: bool = True
        # This type defines how often an update is fired and when cached values get overwritten
        self._trigger_type = self.GeneratorTrigger.Any

        # This table contains cached values of the channels that can be accessed from the generator logic.
        # Keys are channel addresses and values are cached values
        self._values: Dict[str, Any] = {}
        # This contains channels ids that have not yet updated their values and have not cached them
        # in _values
        self._obsolete_values: Optional[Set[str]] = None

        if is_qt_designer():
            self._setup_ui_for_designer()
        else:
            # Trigger connection creation
            self.inputChannels = init_channels or []  # type: ignore
            # Should be invisible in runtime
            self.hide()

    @Property('QStringList')
    def inputChannels(self) -> List[str]:
        """
        This property exposes :class:`pydm.widgets.base.PyDMWidget` channels that we use as input primarily.

        Returns:
            List of PyDMChannel objects.
        """
        return self._channel_ids

    @inputChannels.setter  # type: ignore
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
            self._values = dict.fromkeys(seq=self._channel_ids, value=None)
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
        Callback when a new value arrives on any of the :meth:`inputChannels`.

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

        if self._trigger_type == self.GeneratorTrigger.AggregatedFirst and (not self._obsolete_values
                                                                            or channel_id not in self._obsolete_values):
            return

        # Common logic for AggregatedFirst and AggregatedLast from here on
        self._values[channel_id] = new_val
        if self._obsolete_values:
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

    @generatorTrigger.setter  # type: ignore
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
    def channel(self) -> str:
        return ''

    @channel.setter  # type: ignore
    @superclass_deprecated(logger)
    def channel(self, _):
        pass

    @Property('QSize', designable=False)
    def minimumSize(self) -> QSize:
        return super().minimumSize()

    @minimumSize.setter  # type: ignore
    @superclass_deprecated(logger)
    def minimumSize(self, _):
        pass

    @Property('QSize', designable=False)
    def maximumSize(self) -> QSize:
        return super().maximumSize()

    @maximumSize.setter  # type: ignore
    @superclass_deprecated(logger)
    def maximumSize(self, _):
        pass

    @Property('QSize', designable=False)
    def baseSize(self) -> QSize:
        return super().baseSize()

    @baseSize.setter  # type: ignore
    @superclass_deprecated(logger)
    def baseSize(self, _):
        pass

    @Property('QSize', designable=False)
    def sizeIncrement(self) -> QSize:
        return super().sizeIncrement()

    @sizeIncrement.setter  # type: ignore
    @superclass_deprecated(logger)
    def sizeIncrement(self, _):
        pass

    @Property('QSizePolicy', designable=False)
    def sizePolicy(self) -> QSizePolicy:
        return QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    @sizePolicy.setter  # type: ignore
    @superclass_deprecated(logger)
    def sizePolicy(self, _):
        pass

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
