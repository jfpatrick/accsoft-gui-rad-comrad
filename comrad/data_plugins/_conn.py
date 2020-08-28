import logging
import numpy as np
from typing import Optional, Any
from qtpy.QtCore import QObject, Signal, Qt, Slot, QVariant
from pydm.data_plugins import is_read_only as pydm_read_only
from pydm.data_plugins.plugin import PyDMConnection
from comrad import CChannel, CChannelData
from comrad.generics import GenericQObjectMeta


logger = logging.getLogger('comrad.data_plugins')


class CDataConnection(PyDMConnection, metaclass=GenericQObjectMeta):

    new_value_signal = Signal([CChannelData],  # this overload will be default (when emit is used without key)
                              # Nevertheless, we don't need to make default connect/disconnect. For some reason it
                              # works with just PyDMConnection connect logic, which only uses explicit overloads.
                              # Potentially, it can be caused by the inner logic of PyQt/Qt, which relies on overload
                              # indexes. Since we replace index 0 here, but in the superclass it does connect index 0.
                              # Subsequent overloads are needed here to not fail .connect() in PyDMConnection super methods
                              # (otherwise KeyError will be thrown)
                              [int],
                              [float],
                              [str],
                              [np.ndarray])
    """Overrides superclass signal to implement the only overload - :class:`.CChannelData`."""

    def __init__(self, channel: CChannel, address: str, protocol: Optional[str] = None, parent: Optional[QObject] = None):
        """
        Base class for listeners that communicate with ComRAD Data plugin system.

        This base class makes no assumptions about the flow of the data. It can be unidirectional at will.
        For the common cases that use GET/SET/SUBSCRIBE operations, consider subclassing :class:`CCommonDataConnection`.
        Unlike underlying :class:`~pydm.data_plugins.plugin.PyDMConnection`, it is relying on a single data type
        transported over channels - :class:`.CChannelData`.

        Args:
            channel: Initial channel to connect to the data source.
            address: Address string of the device to be connected to.
            protocol: Protocol representation. Should be ``your-protocol://``.
            parent: Optional parent owner.
        """
        self._connected = False  # Needs to exist before super init, as self.connected is set there, and is writing into this var
        super().__init__(channel=channel, address=address, protocol=protocol, parent=parent)
        self._repr_name = channel.address

    @Slot(str)
    @Slot(bool)
    @Slot(int)
    @Slot(float)
    @Slot(QVariant)
    @Slot(np.ndarray)
    def write_value(self, new_val: Any):
        """
        Callback for the write signal.

        Default implementation does nothing. Override this method to implement the logic that writes a new
        value from a widget into the control system. When overriding the method in the subclass, remember to
        use multiple :func:`~qtpy.QtCore.Slot` decorators in order to allow signal connections with those types
        to succeed.

        Args:
            new_val: The value to write into the control system.
        """
        pass

    def send_command(self):
        """
        Send command is similar to the :meth:`write_value`, except that it takes no arguments.

        Default implementation does nothing. Override this method to implement the logic that sends a
        command a widget into the control system.
        """
        pass

    def add_listener(self, channel: CChannel):
        """
        Adds a listener to the connection.

        Listener is a channel that mediates the data between widgets and the actual data source, by passing
        widget's signals and slots to be connected to :class:`.CDataConnection`.

        Args:
            channel: A new listener.
        """
        logger.debug(f'Adding a listener for {self}')
        super().add_listener(channel)

        # Connect write slots even if we are in the read-only mode, since the mode can change dynamically,
        # and it will be hard to connect slots at that point. Rather forbid sending data over signals
        # in the read-only mode.
        if channel.value_signal is not None:
            logger.debug(f'{self}: Connecting value_signal to write into CS')
            self._connect_write_slots(channel.value_signal)

        enable_write_access = not self.read_only
        logger.debug(f'{self}: Emitting write access: {enable_write_access}')
        self.write_access_signal.emit(enable_write_access)

        # Issue a connection signal (e.g. if it's an additional listener for already connected channel, we need to let
        # it know that we are already connected
        self.connection_state_signal.emit(self.connected)

    def remove_listener(self, channel: CChannel, destroying: bool = False):
        """
        Detaches a listener from the connection.

        Listener is a channel that mediates the data between widgets and the actual data source, by passing
        widget's signals and slots to be connected to :class:`.CDataConnection`.

        Args:
            channel: Listener to remove.
            destroying: :obj:`True` if connection is being terminated completely.
        """
        if not destroying:
            if channel.value_signal is not None:
                try:
                    channel.value_signal.disconnect(self.write_value)
                    logger.debug(f'Disconnected value_signal ({channel.value_signal}) from {self}')
                except (TypeError):
                    pass
                for data_type in [str, bool, int, float, QVariant, np.ndarray]:
                    try:
                        channel.value_signal[data_type].disconnect(self.write_value)
                        logger.debug(f'Disconnected value_signal[{data_type.__name__}] ({channel.value_signal}) from {self}')
                    except (KeyError, TypeError):
                        continue
            logger.debug(f'{self}: Removed one of the listeners')
        else:
            logger.debug(f'{self}: Destroying the connection. All listeners should be disconnected automatically.')
        super().remove_listener(channel=channel, destroying=destroying)
        logger.debug(f'{self}: Listener count now is {self.listener_count}')

    @property
    def read_only(self) -> bool:
        """
        Determines if given channel should be allowed to write into the control system.

        By default, all channels are given permission based on the ``--read-only`` command line argument.
        You can override it to have more granular control, e.g. if you want to inspect device properties in CCDB
        and make a decision based on connection's address.
        """
        return pydm_read_only()

    def close(self):
        """
        Close connection and stop any ongoing subscriptions.

        Subclasses must clear their subscriptions by overriding this method.
        """
        logger.debug(f'{self}: Closing connection')
        self.connected = False
        super().close()

    def _get_connected(self) -> bool:
        return self._connected

    def _set_connected(self, connected: bool):
        if self._connected != connected:
            self._connected = connected
            logger.debug(f'{self} is {"online" if connected else "offline"}')
            self.connection_state_signal.emit(connected)

    connected = property(fget=_get_connected, fset=_set_connected)
    """Specifies if the subscription is considered active. Override this to customize your logic."""

    def __repr__(self) -> str:
        return f'<{type(self).__name__}[{self._repr_name}] at {hex(id(self))}>'

    def _connect_write_slots(self, signal: Signal):
        set_slot_connected: bool = False
        for data_type in [str, bool, int, float, QVariant, np.ndarray]:
            try:
                signal[data_type].connect(slot=self.write_value, type=Qt.QueuedConnection)
            except (KeyError, TypeError):
                continue
            logger.debug(f'Connected write_signal[{data_type.__name__}] to {self}')
            set_slot_connected = True

        if not set_slot_connected:
            try:
                signal.connect(slot=self.send_command, type=Qt.QueuedConnection)
                logger.debug(f'Connected write_signal to {self}')
            except (KeyError, TypeError):
                pass
