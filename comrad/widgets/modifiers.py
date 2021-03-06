import logging
from enum import IntEnum
from typing import List, Dict, Optional, Set, Any
from pydm.widgets.base import PyDMWidget
from pydm.widgets.channel import PyDMChannel
from pydm.data_plugins.plugin import PyDMConnection
from pydm.utilities import is_qt_designer
from qtpy.QtWidgets import QWidget, QFrame, QVBoxLayout, QLabel, QSizePolicy
from qtpy.QtCore import Property, Signal, Slot, Q_ENUM, Qt, QSize
from comrad.data.channel import CChannelData, CContext
from .mixins import CChannelDataProcessingMixin, CHideUnusedFeaturesMixin, CInitializedMixin, deprecated_parent_prop
from .value_transform import CValueTransformationBase


logger = logging.getLogger(__name__)


class _QtDesignerGeneratorTrigger:
    Any = 0
    AggregatedLast = 1
    AggregatedFirst = 2


class CValueAggregator(QWidget, CChannelDataProcessingMixin, CInitializedMixin, CHideUnusedFeaturesMixin, PyDMWidget, CValueTransformationBase, _QtDesignerGeneratorTrigger):

    Q_ENUM(_QtDesignerGeneratorTrigger)

    class GeneratorTrigger(IntEnum):
        """Enum defining when generator sequence must be triggered."""

        ANY = _QtDesignerGeneratorTrigger.Any
        """Any of the incoming values arriving."""

        AGGREGATED_LAST = _QtDesignerGeneratorTrigger.AggregatedLast
        """All values have been updated since the last trigger."""

        AGGREGATED_FIRST = _QtDesignerGeneratorTrigger.AggregatedFirst
        """First new value arriving since the last trigger."""

    updateTriggered = Signal([int], [float], [str], [bool], ['PyQt_PyObject'])
    """Emitted when the user changes the value."""

    def __init__(self, parent: Optional[QWidget] = None, init_channels: Optional[List[str]] = None):
        """
        Widget that allows defining logic to expose a new value calculated on the fly.

        Args:
            parent: The parent widget for the generator.
            init_channel: The channel to be used by the widget.
        """
        QWidget.__init__(self, parent)
        CChannelDataProcessingMixin.__init__(self)
        CInitializedMixin.__init__(self)
        CHideUnusedFeaturesMixin.__init__(self)
        self._channel_ids: List[str] = []  # Just for typing purposes. It should be set in PyDMWidget monkey-patch
        self._local_context: CContext = None  # type: ignore  # Just for typing purposes. It should be set in PyDMWidget monkey-patch
        PyDMWidget.__init__(self)
        CValueTransformationBase.__init__(self)
        self._widget_initialized = True
        self._active: bool = True
        # This type defines how often an update is fired and when cached values get overwritten
        self._trigger_type = CValueAggregator.GeneratorTrigger.ANY

        # This table contains cached values of the channels that can be accessed from the generator logic.
        # Keys are channel addresses and values are cached values
        self._values: Dict[str, Any] = {}
        # Similarly to values, we store headers arriving from the control system
        self._headers: Dict[str, Optional[Dict[str, Any]]] = {}
        # This contains channels ids that have not yet updated their values and have not cached them
        # in _values
        self._obsolete_values: Optional[Set[str]] = None

        if is_qt_designer():
            self._setup_ui_for_designer()
        else:
            # Trigger connection creation
            self.inputChannels = init_channels or []
            # Should be invisible in runtime
            self.hide()

    def _get_input_channels(self) -> List[str]:
        return self._channel_ids

    def _set_input_channels(self, new_val: List[str]):
        if new_val != self._channel_ids:
            self.reconnect(new_val, self._local_context)

    inputChannels = Property('QStringList', _get_input_channels, _set_input_channels)
    """This property exposes :class:`PyDMWidget`'s channels that we use as input primarily."""

    def reconnect(self, channels: List[str], new_context: Optional[CContext]):
        """
        Overridden method of :class:`~comrad.widgets.widget.CWidget` that monkey-patches PyDMWidget.

        Args:
            new_ch_addresses: New channel addresses to connect to.
            new_context: New context assisting the connection.
        """
        # Update trigger table
        if self._trigger_type == CValueAggregator.GeneratorTrigger.ANY:
            self._values.clear()
            self._headers.clear()
            self._obsolete_values = None
        else:
            self._values = dict.fromkeys(self._channel_ids, None)
            self._headers = dict.fromkeys(self._channel_ids, None)
            self._obsolete_values = set(self._channel_ids)

        # Handle the channel reconnection by the base class
        PyDMWidget.reconnect(self, channels, new_context)

    def value_changed(self, packet: CChannelData[Any]):
        """
        Callback when a new value arrives on any of the :attr:`inputChannels`.

        Args:
            packet: New value.
        """

        # This is the way to identify the channel, instead of initially used functools.partial,
        # which results in reference cycle
        conn: Optional[PyDMConnection] = self.sender()
        if conn is None or not isinstance(packet, CChannelData):
            return
        channel_id: str = conn.address
        if channel_id.startswith('/'):
            # Because PyDM does not natively support /// notation of JAPC, leading slash is left
            # in the address. We need to remove it to not confuse the user.
            channel_id = channel_id[1:]

        # Strip away context information from the address, to always have a consistent keys in the dictionary
        # If we happen to sit inside CContextFrame or have a global selector defined, channel_id can be different here
        # from what was recorder in self._obsolete_values. Also, the valueTransformation becomes sensitive to the
        # environment if keys are used to access data.
        for delim in ['?', '@', '&']:
            idx = channel_id.find(delim)
            if idx != -1:
                channel_id = channel_id[:idx]

        super().value_changed(packet)

        if self._trigger_type == CValueAggregator.GeneratorTrigger.ANY:
            self._values[channel_id] = packet.value
            self._headers[channel_id] = packet.meta_info
            self._trigger_update()
            return

        if self._trigger_type == CValueAggregator.GeneratorTrigger.AGGREGATED_FIRST and (not self._obsolete_values
                                                                                         or channel_id not in self._obsolete_values):
            return

        # Common logic for AggregatedFirst and AggregatedLast from here on
        self._values[channel_id] = packet.value
        self._headers[channel_id] = packet.meta_info
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

    def _get_generator_trigger(self) -> 'CValueAggregator.GeneratorTrigger':
        return self._trigger_type

    def _set_generator_trigger(self, new_type: 'CValueAggregator.GeneratorTrigger'):
        """
        Update for the generator trigger type.

        This update will clean up the hash table or will recreate it based on the incoming type.

        Args:
            new_type: New triggering type.
        """
        if self._trigger_type != new_type:
            if new_type == CValueAggregator.GeneratorTrigger.ANY:
                self._obsolete_values = None
            elif self._channel_ids:
                # AggregatedFirst and AggregatedLast logic here
                self._obsolete_values = set(self._channel_ids)
            self._trigger_type = new_type

    generatorTrigger: 'CValueAggregator.GeneratorTrigger' = Property(_QtDesignerGeneratorTrigger, _get_generator_trigger, _set_generator_trigger)
    """
    Trigger defines when the output is fired.

    - OnEveryValue will fire an update on any new incoming value from any channel
    - OnAggregatedValue will wait until all channels deliver value since the last
      update and only then fire a new one.
    """

    @deprecated_parent_prop(logger=logger, property_name='channel')
    def __set_channel(self, _):
        pass

    channel = Property(str, lambda _: '', __set_channel, designable=False)

    def __get_minimumSize(self) -> QSize:
        return super().minimumSize()

    @deprecated_parent_prop(logger=logger, property_name='minimumSize')
    def __set_minimumSize(self, _):
        pass

    minimumSize = Property('QSize', __get_minimumSize, __set_minimumSize, designable=False)

    def __get_maximumSize(self) -> QSize:
        return super().maximumSize()

    @deprecated_parent_prop(logger=logger, property_name='maximumSize')
    def __set_maximumSize(self, _):
        pass

    maximumSize = Property('QSize', __get_maximumSize, __set_maximumSize, designable=False)

    def __get_baseSize(self) -> QSize:
        return super().baseSize()

    @deprecated_parent_prop(logger=logger, property_name='baseSize')
    def __set_baseSize(self, _):
        pass

    baseSize = Property('QSize', __get_baseSize, __set_baseSize, designable=False)

    def __get_sizeIncrement(self) -> QSize:
        return super().sizeIncrement()

    @deprecated_parent_prop(logger=logger, property_name='sizeIncrement')
    def __set_sizeIncrement(self, _):
        pass

    sizeIncrement = Property('QSize', __get_sizeIncrement, __set_sizeIncrement, designable=False)

    @deprecated_parent_prop(logger=logger, property_name='sizePolicy')
    def __set_sizePolicy(self, _):
        pass

    sizePolicy = Property('QSizePolicy', lambda _: QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed), __set_sizePolicy, designable=False)

    def _trigger_update(self):
        if ((not self.valueTransformation and not self.snippetFilename)
                or is_qt_designer()):
            # Avoid code evaluation in Designer, as it can produce unnecessary errors with broken code
            return

        transform = self.cached_value_transformation()
        if not transform:
            return

        result = transform(values=self._values, headers=self._headers)
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
