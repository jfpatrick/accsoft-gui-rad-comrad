"""Graphs based on the library accwidgets' package graph for comrad"""

import abc
import json
import copy
import functools
import logging
import pyqtgraph as pg
import numpy as np
from enum import Enum
import collections
from typing import cast, Type, Optional, Union, List, Dict, Iterable, Any
from collections import OrderedDict
from qtpy.QtWidgets import QWidget
from qtpy.QtGui import QColor, QPen, QBrush
from qtpy.QtCore import Property, QObject
# from pydm.widgets.image import PyDMImageView
from pydm.widgets.baseplot import BasePlotCurveItem, PyDMPrimitiveWidget
from pydm.widgets.base import widget_destroyed
from pydm.widgets.channel import PyDMChannel
from pydm import utilities
from accwidgets import graph as accgraph


logger = logging.getLogger(__name__)


class ColumnNames(Enum):
    """Column names as strings for the plotting item editor dialog's table."""

    CHANNEL = 'Channel'
    LABEL = 'Label'
    COLOR = 'Color'
    LINE_STYLE = 'Line Style'
    LINE_WIDTH = 'Item Width'
    SYMBOL = 'Symbol'
    SYMBOL_SIZE = 'Symbol Size'
    LAYER = 'Layer'
    STYLE = 'Style'


class PlottingItemTypes(Enum):
    """String values representing different plotting items (curve, bar graph, etc.)."""

    LINE_GRAPH = 'Line Graph'
    BAR_GRAPH = 'Bar Graph'
    INJECTION_BAR_GRAPH = 'Injection Bar Graph'
    TIMESTAMP_MARKERS = 'Timestamp Marker'


class PyDMChannelDataSource(accgraph.UpdateSource):
    """
    Class for receiving data from a PyDM Channel and emit it through
    the update signal AccPyQtGraph plotting items are connected to.
    """

    def __init__(
            self,
            channel_address: str,
            data_type_to_emit: Type,
    ):
        """
        Create a new source that is attached to a :class:`pydm.widgets.channel.PyDMChannel`.

        Args:
            channel_address: address the channel is getting data from
            data_type_to_emit: type in which the received data should
                               be converted to
        """
        super().__init__()
        self._data_type_to_emit = data_type_to_emit
        self._channel: Optional[PyDMChannel] = None
        # Save last state to check if new value contains any changes
        self._last_value: Union[List[int], List[float], None] = None
        self._transform = accgraph.PlottingItemDataFactory.get_transformation(self._data_type_to_emit)
        self.address = channel_address

    @property
    def address(self) -> str:
        """Get the PyDMChannel the update source is based on."""
        if self._channel is not None:
            return self._channel.address
        return ''

    @address.setter
    def address(self, new_address: str) -> None:
        """
        Replace the :class:`pydm.widgets.channel.PyDMChannel` with one created from the passed channel address.

        Args:
            new_address: new address that will be used to create a channel for
                         data updates
        """
        if new_address is not None and len(new_address.strip()) > 0:
            self._channel = PyDMChannel(
                address=new_address.strip(),
                connection_slot=self._connection_state_changes,
                value_slot=self._emit_value,
            )
            self._channel.connect()

    @property
    def channel(self) -> Optional[PyDMChannel]:
        """Get the current :class:`pydm.widgets.channel.PyDMChannel` the update source is based on."""
        return self._channel

    def _connection_state_changes(self) -> None:
        """
        Slot to handle connection state changes from the channel.
        Currently we do not react in a special way to connection state changes.
        """
        pass

    def _emit_value(
            self,
            value: Union[
                float,
                int,
                Iterable[float],
                Iterable[int],
                None,
            ],
    ) -> None:
        """
        Handle values emitted by the channel. The values get wrapped
        in a fitting data type that can be processed by the plotting item.

        If a single value is passed, the timestamp of the time of
        arrival will be used as the x value for the point.

        Args:
            value: Value coming from the data source that is supposed to be
                   appended to a graph.
        """
        value = self._to_list_and_check_value_change(value)
        if value is not None:
            if accgraph.PlottingItemDataFactory.should_unwrap(value, self._data_type_to_emit):
                envelope = self._transform(*value)
            else:
                envelope = self._transform(value)
            self.sig_new_data[self._data_type_to_emit].emit(envelope)

    def _to_list_and_check_value_change(
            self,
            value: Union[
                float,
                int,
                Iterable[float],
                Iterable[int],
                None,
            ],
    ) -> Union[List[int], List[float], None]:
        """
        Transform the passed values to a list and check if the values are have been
        received before.

        Returns:
             Values as a list or None, if the values have been received before.
        """
        if value is None or (isinstance(value, collections.Sized) and len(value) == 0):
            # logger.info(f'Data {value} could not be properly interpreted and will be dropped.')
            return None
        if self._last_value is not None:
            if isinstance(value, np.ndarray) and isinstance(self._last_value, np.ndarray):
                if np.array_equal(value, self._last_value):
                    return None
            elif value == self._last_value:
                return None
        if isinstance(value, (int, float)):
            value = [value]
        if isinstance(value, tuple):
            value = list(value)
        # Cast for typing hints
        value = cast(List[float], value)
        self._last_value = copy.copy(value)
        return value


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~ Base Classes ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class CPlotWidgetBase(PyDMPrimitiveWidget):

    """
    Base class providing functions used by the plotting item editor dialog
    for adding, removing and editing plotting items in a graph. This class
    allows sharing these functions with their implementation in
    different plot widgets.

    This class uses attributes of the :class:`~accwidgets.graph.ExPlotWidget` and should only
    be used as a base class in classes derived from :class:`~accwidgets.graph.ExPlotWidget`.
    For overwritten functions to be picked up, this class has to
    be mentioned before the :class:`~accwidgets.graph.ExPlotWidget` in the derived classes definition
    of super classes:

    >>> class Derived(CPlotWidgetBase, ExPlotWidget)  # function's are overwritten

    >>> class Derived(ExPlotWidget, CPlotWidgetBase)  # original functions are picked up

    Subclasses can define in the class attribute :attr:`ITEM_TYPES` what
    type of plotting items they can display for which style. If the
    value is set to ``None``, the style is interpreted as not supported.
    """

    ITEM_TYPES: OrderedDict = OrderedDict([
        (PlottingItemTypes.LINE_GRAPH.value, None),
        (PlottingItemTypes.BAR_GRAPH.value, None),
        (PlottingItemTypes.INJECTION_BAR_GRAPH.value, None),
        (PlottingItemTypes.TIMESTAMP_MARKERS.value, None),
    ])

    # Which data structure is emitted on which plotting item style
    _SOURCE_EMIT_TYPE: OrderedDict = OrderedDict([
        (PlottingItemTypes.LINE_GRAPH.value, accgraph.PointData),
        (PlottingItemTypes.BAR_GRAPH.value, accgraph.BarData),
        (PlottingItemTypes.INJECTION_BAR_GRAPH.value, accgraph.InjectionBarData),
        (PlottingItemTypes.TIMESTAMP_MARKERS.value, accgraph.TimestampMarkerData),
    ])

    def __init__(self):
        super().__init__()
        if not isinstance(self, accgraph.ExPlotWidget):
            logger.warning(
                f'{CPlotWidgetBase.__name__} implementation relies on attributes'
                f'provided by {accgraph.ExPlotWidget.__name__}. '
                f'Use {CPlotWidgetBase.__name__} only as base class of classes'
                f'derived from {accgraph.ExPlotWidget.__name__}.',
            )
        self._items: List[CItemPropertiesBase] = []

    @property
    def _curves(self):
        """
        PyDM's BasePlotCurvesModel accesses the plots "_curve" attribute.
        We replaced it with "_items" since this list not only holds curves
        anymore. This property is a compromise to avoid the misleading "_curves"
        attribute without having to overwrite several BasePlotCurvesModel functions.
        """
        return self._items_checked

    @property
    def _items_checked(self):
        """
        Every time we want to access _items, we want to make sure, that the layer
        it is associated, is still existing, otherwise the underlying C++ object
        will be not existing anymore.
        To ensure this, we will search the layer of each item and move the item to
        it, in case it is not existing anymore.
        """
        for index, item in enumerate(self._items[:]):
            # If we detect any invalid layers, move element to the default one
            if item.layer and item.layer not in cast(accgraph.ExPlotWidgetProperties, self).layerIDs:
                try:
                    self._remove_from_plot_and_disconnect_channels(item)
                except RuntimeError:
                    # If the C++ Object is already deleted
                    pass
                self.add_channel_attached_item(
                    index=index,
                    style=item.style_string,
                    channel_address=item.address,
                    name=item.label,
                    color=item.color,
                    line_style=item.line_style,
                    line_width=item.line_width,
                    symbol=item.symbol,
                    symbol_size=item.symbol_size,
                    layer=None,
                )
        # Force to re-add all elements
        return self._items

    # Overwritten add... functions of the ExPlotWidget

    def addCurve(
            self,
            c: Optional[pg.PlotDataItem] = None,
            params: Optional[Dict[str, Any]] = None,
            data_source: Union[str, accgraph.UpdateSource, None] = None,
            layer: Optional[str] = None,
            buffer_size: int = accgraph.DEFAULT_BUFFER_SIZE,
            color: Union[str, QColor, None] = None,
            name: Optional[str] = None,
            symbol: Optional[str] = None,
            symbol_size: Optional[int] = None,
            line_style: Optional[int] = None,
            line_width: Optional[int] = None,
    ) -> Union['CItemPropertiesBase', pg.PlotDataItem]:
        """
        This function overrides the :class:`~accwidgets.graph.ExPlotItem`'s
        :meth:`~accwidgets.graph.ExPlotItem.addCurve` function and extends it
        by giving the option to pass a channel address for feeding data to the graph.
        Additionally you can pass stylistic parameters which are the same as
        :class:`CItemsPropertyBase`'s style properties that are supported by the item.

        Args:
            c: param for deprecated :meth:`~pyqtgraph.PlotItem.addCurve` from PyQtGraph,
               only for catching calls for :meth:`~pyqtgraph.PlotItem.addCurve`.
            params: param for deprecated addCurve from PyQtGraph, only for catching calls
                    for :meth:`~pyqtgraph.PlotItem.addCurve`.
            data_source: Instance of :class:`~accwidgets.graph.datamodel.connection.UpdateSource` that emits data
                         or a string for a channel address
            layer: Layer in which the curve should be added to
            buffer_size: amount of data the item's data model is holding
            color: color for the lines in the curve
            name: name of the curve that can be displayed in the plots legend (if added)
            symbol: symbol that represents the single data-points, see :class:`pyqtgraph.ScatterPlotItem`
                    for all possible values
            symbol_size: size for the symbols
            line_style: Style of the line, see :class:`PyQt5.QtCore.Qt.PenStyle` enum for values
            line_width: thickness of the line in the graph

        Returns:
            Curve object which was added to the plot.
        """
        if isinstance(data_source, str):
            curve = self.add_channel_attached_item(
                style=PlottingItemTypes.LINE_GRAPH.value,
                channel_address=data_source,
                layer=layer,
                color=color,
                name=name,
                symbol=symbol,
                symbol_size=symbol_size,
                line_style=line_style,
                line_width=line_width,
            )
            return curve
        return accgraph.ExPlotWidget.addCurve(
            self,
            c=c,
            params=params,
            data_source=data_source,
            layer=layer,
            buffer_size=buffer_size,
        )

    def addBarGraph(
            self,
            data_source: Union[str, accgraph.UpdateSource, None] = None,
            layer: Optional[str] = None,
            buffer_size: int = accgraph.DEFAULT_BUFFER_SIZE,
            color: Union[str, QColor, None] = None,
            bar_width: Optional[int] = None,
    ) -> Union['CItemPropertiesBase', pg.BarGraphItem]:
        """
        This function overrides the :class:`~accwdigets.graph.ExPlotItem`'s
        :meth:`~accwidgets.graph.ExPlotItem.addBarGraph` function and extends it
        by giving the option to pass a channel address for feeding data to the graph.
        Additionally you can pass stylistic parameters which are the same as
        :class:`CItemsPropertyBase`'s style properties that are supported by the item.

        Args:
            data_source: Instance of :class:`~accwidgets.graph.datamodel.connection.UpdateSource` that emits data
                         or a string for a channel address
            layer: Layer in which the bar graph should be added to
            buffer_size: amount of data the item's data model is holding
            color: Color the bars are displayed in
            bar_width: width of each bar

        Returns:
            bar graph object which was added to the plot.
        """
        if isinstance(data_source, str):
            return self.add_channel_attached_item(
                style=PlottingItemTypes.BAR_GRAPH.value,
                channel_address=data_source,
                layer=layer,
                color=color,
                line_width=bar_width,
            )
        return accgraph.ExPlotWidget.addBarGraph(
            self,
            data_source=data_source,
            layer=layer,
            buffer_size=buffer_size,
        )

    def addInjectionBar(
            self,
            data_source: Union[str, accgraph.UpdateSource],
            layer: Optional[str] = None,
            buffer_size: int = accgraph.DEFAULT_BUFFER_SIZE,
            color: Union[str, QColor, None] = None,
            line_width: Optional[int] = None,
    ) -> Union['CItemPropertiesBase', pg.BarGraphItem]:
        """
        This function overrides the :class:`~accwdigets.graph.ExPlotItem`'s
        :meth:`~accwidgets.graph.ExPlotItem.addInjectionBar` function and extends it
        by giving the option to pass a channel address for feeding data to the graph.
        Additionally you can pass stylistic parameters which are the same as
        :class:`CItemsPropertyBase`'s style properties that are supported by the item.

        Args:
            data_source: Instance of :class:`~accwidgets.graph.datamodel.connection.UpdateSource` that emits
                         data or a string for a channel address
            layer: Layer in which the injection bars should be added to
            buffer_size: amount of data the item's data model is holding
            color: Color for the lines in the injection bar
            line_width: Thickness of the lines in the injection bar

        Returns:
            injection bar graph object which was added to the plot.
        """
        if isinstance(data_source, str):
            return self.add_channel_attached_item(
                style=PlottingItemTypes.INJECTION_BAR_GRAPH.value,
                channel_address=data_source,
                layer=layer,
                color=color,
                line_width=line_width,
            )
        return accgraph.ExPlotWidget.addInjectionBar(
            self,
            data_source=data_source,
            layer=layer,
            buffer_size=buffer_size,
        )

    def addTimestampMarker(
            self,
            data_source: Union[str, accgraph.UpdateSource],
            buffer_size: int = accgraph.DEFAULT_BUFFER_SIZE,
            line_width: Optional[int] = None,
    ) -> Union['CItemPropertiesBase', pg.BarGraphItem]:
        """
        This function overrides the :class:`~accwdigets.graph.ExPlotItem`'s
        :meth:`~accwidgets.graph.ExPlotItem.addTimestampMarker` function and extends it
        by giving the option to pass a channel address for feeding data to the graph.
        Additionally you can pass stylistic parameters which are the same as
        :class:`CItemsPropertyBase`'s style properties that are supported by the item.

        Args:
            data_source: Instance of :class:`~accwidgets.graph.datamodel.connection.UpdateSource` that emits
                         data or a string for a channel address
            buffer_size: amount of data the item's data model is holding
            line_width: Thickness of the vertical line representing a specific timestamp

        Returns:
            Curve object that is added to the plot.
        """
        if isinstance(data_source, str):
            return self.add_channel_attached_item(
                style=PlottingItemTypes.TIMESTAMP_MARKERS.value,
                channel_address=data_source,
                line_width=line_width,
            )
        # Superclasses add injection bars item without channel
        return accgraph.ExPlotWidget.addTimestampMarker(
            self,
            data_source=data_source,
            buffer_size=buffer_size,
        )

    def add_channel_attached_item(
            self,
            channel_address: str,
            style: str = PlottingItemTypes.LINE_GRAPH.value,
            layer: Optional[str] = None,
            index: Optional[int] = None,
            name: Optional[str] = None,
            color: Union[str, QColor, None] = None,
            line_style: Optional[int] = None,
            line_width: Optional[int] = None,
            symbol: Optional[str] = None,
            symbol_size: Optional[int] = None,
    ) -> 'CItemPropertiesBase':
        """
        Add a new item attached to a channel to the plot.

        Args:
            style: which kind of item should be added (line graph, bar graph, etc.)
            channel_address : address for the channel the item is connected to
            name : The name of the item
            color : The color for the item
            line_style : The line style of the item, i.e. solid, dash, dot, etc.
                         (if it is supported by the item)
            line_width : How thick the item's line should be, if it is supported
                         by the item
            symbol : symbol to use as markers representing data (if it is supported
                     by the item)
            symbol_size : How big the symbols should be
            layer: identifier for the layer the item should be added to
            index: index for the plot widgets list of added items (position is
                   important for the positioning in the table)

        Returns:
            The newly created curve.
        """
        data_source = PyDMChannelDataSource(
            channel_address=channel_address,
            data_type_to_emit=self._SOURCE_EMIT_TYPE[style],
        )
        new_item: CItemPropertiesBase = self._create_fitting_item(
            data_source=data_source,
            style=style,
        )
        if color is None:
            color = CPlotWidgetBase._default_color(index or len(self._items_checked))
        if line_style is None:
            line_style = CPlotWidgetBase._default_line_style()
        if line_width is None:
            line_width = 1
        if symbol_size is None:
            symbol_size = 10
        self._set_item_styling_properties(
            item=new_item,
            color=color,
            name=name,
            line_style=line_style,
            line_width=line_width,
            symbol=symbol,
            symbol_size=symbol_size,
        )
        self._add_created_item(
            new_item=new_item,
            layer=layer,
            index=index,
        )
        return new_item

    @staticmethod
    def _default_color(index: int) -> str:
        return utilities.colors.default_colors[
            index % len(utilities.colors.default_colors)
        ]

    @staticmethod
    def _default_line_style() -> int:
        return CItemPropertiesBase.lines.get('Solid')

    @staticmethod
    def _set_item_styling_properties(
            item: 'CItemPropertiesBase',
            color: Union[str, QColor, None] = None,
            name: Optional[str] = None,
            symbol: Optional[str] = None,
            symbol_size: Optional[int] = None,
            line_style: Optional[int] = None,
            line_width: Optional[int] = None,
    ) -> None:
        """Set the items styling properties according to the passed values."""
        if color is not None:
            item.color = color
        if name is not None:
            item.label = name
        if symbol in CItemPropertiesBase.symbols.values():
            item.symbol = symbol
        if symbol_size is not None:
            item.symbol_size = symbol_size
        if line_style is not None:
            item.line_style = line_style
        if line_width is not None:
            item.line_width = line_width

    def _create_fitting_item(
            self,
            data_source: 'PyDMChannelDataSource',
            style: str = PlottingItemTypes.LINE_GRAPH.value,
    ) -> 'CItemPropertiesBase':
        """
        Create a new plotting item fitting the passed styling.

        Args:
            data_source: data source containing the channel the curve
                         will receive data from
            style: string representation of what item to add
        """
        style = style or PlottingItemTypes.LINE_GRAPH.value
        if self.ITEM_TYPES[style] is None:
            raise ValueError(f"{type(self).__name__} does not support style '{style}'")
        return self.ITEM_TYPES[style](
            plot_item=self.plotItem,
            data_model=data_source,
        )

    def _add_created_item(
            self,
            new_item: 'CItemPropertiesBase',
            layer: Optional[accgraph.LayerIdentification] = None,
            index: Optional[int] = None,
    ) -> None:
        """Add the passed plotting item to the plot item

        Args:
            new_item: item that should be added to the plot
            layer: layer in which the item should be added
            index: If the index is not None and inside the plot's curves
                   valid index range, replace the item there with the passed one
        """
        if index is None or index < 0 or index >= len(self._items):
            self._items.append(new_item)
        else:
            self._items[index] = new_item
        # F.e. if layers have been deleted...
        new_item = cast(accgraph.DataModelBasedItem, new_item)
        layer = (layer if isinstance(layer, str) or layer is None else layer.id)
        if layer and layer not in cast(accgraph.ExPlotWidgetProperties, self).layerIDs:
            layer = None
        cast(accgraph.ExPlotWidget, self).plotItem.addItem(item=new_item, layer=layer)

    def remove_channel_attached_item(self, item: 'CItemPropertiesBase') -> None:
        """
        Remove a specific item from the plot item.

        Args:
            item : The curve to be removed.
        """
        self._items.remove(item)
        self._remove_from_plot_and_disconnect_channels(item=item)

    def _remove_from_plot_and_disconnect_channels(self, item: 'CItemPropertiesBase'):
        """Remove given item from plot and disconnect the attached channels."""
        cast(accgraph.ExPlotWidget, self).removeItem(item)
        for chan in item.channels:
            if chan:
                chan.disconnect()

    def remove_channel_attached_item_at_index(self, index: int) -> None:
        """
        Remove a item from the graph, given its index in the graph's :attr:`_items` list.

        Args:
            index : The item's index in the graph's :attr:`_items` list.
        """
        item = self._items[index]
        self.remove_channel_attached_item(item)

    def _get_items(self) -> List[str]:
        """
        Dump the current list of items and each item's settings into a list
        of JSON-formatted strings. This function is mainly for the Qt Designer plugin
        to represent all curves as one :class:`~PyQt5.QtCore.QStringList` and not for calling it directly.

        Returns:
            A list of JSON-formatted strings, each containing an item's settings.
        """
        return [json.dumps(item.to_dict()) for item in self._items_checked]

    def _set_items(self, new_items: List[str]) -> None:
        """
        Add a list of items into the graph from a List of strings containing a JSON
        representing these curves. This function is mainly for the Qt Designer plugin
        to represent all curves as one QStringList and not for calling it directly.

        Args:
            new_items: A list of JSON-formatted strings, each contains a item and its
                        settings
        """
        try:
            items_loaded: List[Dict[str, Any]] = [json.loads(str(i)) for i in new_items]
        except ValueError as error:
            logger.exception(f'Error parsing item json data: {error}')
            return
        self.clear_items()
        for item in items_loaded:
            layer = item.get('layer')
            # Fish out invalid layers before adding
            if layer is not None and layer not in cast(accgraph.ExPlotWidgetProperties, self).layerIDs:
                layer = None
            self.add_channel_attached_item(
                style=item.get('style', PlottingItemTypes.LINE_GRAPH.value),
                channel_address=item.get('channel', ''),
                name=item.get('name'),
                color=item.get('color'),
                line_style=item.get('line_style'),
                line_width=item.get('line_width'),
                symbol=item.get('symbol'),
                symbol_size=item.get('symbol_size'),
                layer=layer,
            )

    curves = Property(type='QStringList', fget=_get_items, fset=_set_items, designable=False)

    def clear_items(self) -> None:
        """Remove all prior added items from the plot."""
        plot_item = cast(accgraph.ExPlotWidget, self).plotItem
        for item in self._items:
            try:
                cast(QObject, item).deleteLater()
                plot_item.removeItem(item)
            except RuntimeError:
                # In case the C++ object is already deleted
                pass
        try:
            plot_item.clear()
        except RuntimeError:
            plot_item.items.clear()
            plot_item.dataItems.clear()
            plot_item.curves.clear()
        self._items.clear()


class CItemPropertiesBase(metaclass=abc.ABCMeta):

    plotting_item_editor_supported_columns: List[str] = []
    symbols = BasePlotCurveItem.symbols
    lines = BasePlotCurveItem.lines
    style: List[str] = [
        PlottingItemTypes.LINE_GRAPH.value,
        PlottingItemTypes.BAR_GRAPH.value,
        PlottingItemTypes.INJECTION_BAR_GRAPH.value,
        PlottingItemTypes.TIMESTAMP_MARKERS.value,
    ]

    def __init__(self):
        """
        Base class for different plotting item properties. This classes uses
        provides common properties that can be used in curves, bar graphs, etc.

        All properties for style parameters are based on private getter and setter
        functions. With the base implementation, these style parameters are just
        saved in instance attributes and won't have any visual effect in the plot. If
        a plotting item can use one of these style parameters properly (f.e. a curve
        can use a line width), these functions should be overwritten in the subclasses.

        Saving these properties even if the plotting item can not use them is important
        when switching back to items that can use them to not loose prior set values.
        """
        self.opts: Dict

    def initialize_style_properties(
            self,
            color: Optional[str],
            line_style: Optional[int] = None,
            line_width: Optional[int] = None,
    ) -> None:
        """
        Initialize styling parameters for the item.

        Args:
            color: color the curve should be drawn with
            line_style: style (dot, solid etc.) of the line connecting points
            line_width: how thick should the lines between points be
        """
        if line_width is not None:
            self.line_width = line_width
        if line_style is not None:
            self.line_style = line_style
        if color is not None:
            self.color = color
        try:
            cast(pg.PlotItem, self).setSymbolBrush(None)
        except AttributeError:
            pass
        # If curve is deleted, remove its listener from the channel
        if hasattr(self, 'channels'):
            # widget_destroyed expects a function and calls the passed channels argument
            # -> we have to wrap out property as callable
            cast(QObject, self).destroyed.connect(functools.partial(widget_destroyed, lambda: self.channels))

    def to_dict(self) -> OrderedDict:
        """
        Returns an OrderedDict representation with values for all properties
        needed to recreate this item.
        """
        return OrderedDict([
            ('channel', self.address),
            ('style', self.style_string),
            ('layer', self.layer),
            ('name', self.label),
            ('color', self.color_string),
            ('line_style', self.line_style),
            ('line_width', self.line_width),
            ('symbol', self.symbol),
            ('symbol_size', self.symbol_size),
        ])

    # Properties with implementation shareable through all subclasses

    @property
    def channels(self) -> List[PyDMChannel]:
        """Returns channel the data source is connected to."""
        return [self.data_source.channel]

    @property
    def address(self) -> str:
        """Returns the address of the :class:`~pydm.widgets.channel.PyDMChannel` the data source is based on."""
        return self.data_source.address

    @address.setter
    def address(self, new_address: str) -> None:
        """Change the address of the :class:`~pydm.widgets.channel.PyDMChannel` the data source is based on."""
        self.data_source.address = new_address

    @property
    def layer(self) -> str:
        """Returns the address of the :class:`~pydm.widgets.channel.PyDMChannel` the data source is based on."""
        return cast(accgraph.DataModelBasedItem, self).layer_id

    @property
    def data_source(self) -> PyDMChannelDataSource:
        """Shortcut for PyDM-bound data source."""
        return cast(PyDMChannelDataSource, cast(accgraph.DataModelBasedItem, self).model().data_source)

    @property
    @abc.abstractmethod
    def style_string(self) -> str:
        """Returns string representation of the items style"""
        pass

    # Properties for handling values from the curve editor dialog table

    @property
    def color_string(self) -> str:
        """
        A string representation of the color used for the item. This string
        will be a hex color code, like ``#FF00FF``, or an SVG spec color name, if
        a name exists for the color.
        """
        return str(utilities.colors.svg_color_from_hex(self.color.name(), hex_on_fail=True))

    @color_string.setter
    def color_string(self, new_color_string: str) -> None:
        """
        A string representation of the color used for the item. This string
        will be a hex color code, like ``#FF00FF``, or an SVG spec color name, if
        a name exists for the color.

        Args:
            new_color_string: The new string to use for the item color.
        """
        self.color = QColor(str(new_color_string))

    @property
    def color(self) -> QColor:
        """The color used for the item."""
        return getattr(self, '_color', None)

    @color.setter
    def color(self, new_color: Union[str, QColor]) -> None:
        """The color used for the item.

        Args:
            new_color: The new color to use for the item.
        """
        if isinstance(new_color, str):
            self.color_string = new_color
        else:
            self._color = new_color

    @property
    def label(self) -> str:
        """The name of the item displayed in the legend."""
        return getattr(self, '_name', '')

    @label.setter
    def label(self, new_name: str) -> None:
        """Set the items name that is displayed in the legend."""
        self._name = new_name

    @property
    def line_style(self) -> int:
        """
        Return the style of lines used in the item (if supported).
        Must be a value from the :class:`~PyQt5.QtCore.Qt.PenStyle` enum
        (see http://doc.qt.io/qt-5/qt.html#PenStyle-enum).
        """
        return getattr(self, '_line_style', list(self.lines.values())[0])

    @line_style.setter
    def line_style(self, new_style: int) -> None:
        """
        Set the style of lines used in the item (if supported).
        Must be a value from the :class:`~PyQt5.QtCore.Qt.PenStyle` enum
        (see http://doc.qt.io/qt-5/qt.html#PenStyle-enum).
        """
        if new_style in self.lines.values():
            self._line_style = new_style

    @property
    def line_width(self) -> Union[float, int]:
        """Return the width of the line connecting the data points."""
        return getattr(self, '_line_width', 1)

    @line_width.setter
    def line_width(self, new_width: Union[float, int]) -> None:
        """Set the width of the line connecting the data points."""
        if new_width >= 0:
            self._line_width = new_width

    @property
    def symbol(self) -> Optional[str]:
        """
        The single-character code for the symbol drawn at each data point.
        See the documentation for pyqtgraph.PlotDataItem for possible values.
        """
        return getattr(self, '_symbol', list(self.symbols.values())[0])

    @symbol.setter
    def symbol(self, new_symbol: Optional[str]) -> None:
        """
        The single-character code for the symbol drawn at each data point.
        See the documentation for :class:`pyqtgraph.PlotDataItem` for possible values.
        """
        if new_symbol in self.symbols.values():
            self._symbol = new_symbol

    @property
    def symbol_size(self) -> int:
        """Return the size of the symbol to represent the data."""
        return getattr(self, '_symbol_size', 10)

    @symbol_size.setter
    def symbol_size(self, new_size: int) -> None:
        """Set the size of the symbol to represent the data."""
        if new_size >= 0:
            self._symbol_size = new_size


class CCurvePropertiesBase(CItemPropertiesBase):

    """
    Base class for different curve properties. This classes uses
    attributes of the :class:`accwidgets.graph.LivePlotCurve` and should only be used as a
    base class in classes derived from :class:`accwidgets.graph.LivePlotCurve`.
    """

    plotting_item_editor_supported_columns: List[str] = [e.value for e in ColumnNames]

    def __init__(self):
        CItemPropertiesBase.__init__(self)
        if not isinstance(self, accgraph.AbstractBasePlotCurve):
            logger.warning(
                f'{CCurvePropertiesBase.__name__} implementation relies '
                f'on attributes provided by {accgraph.AbstractBasePlotCurve.__name__}. '
                f'Use {CCurvePropertiesBase.__name__} only as base class '
                f'of classes derived from {accgraph.LivePlotCurve.__name__}.',
            )

    @property
    def style_string(self) -> str:
        """Returns string representation of the items style"""
        return PlottingItemTypes.LINE_GRAPH.value

    # Properties for convenient access to PlotDataItem.opts

    @property
    def pen(self) -> QPen:
        """Grant easier access to :attr:`~pyqtgraph.PlotDataItem.pen`."""
        self._prepare_pens_in_opts()
        return self.opts.get('pen')

    @property
    def symbol_pen(self) -> QPen:
        """Grant easier access to :attr:`~pyqtgraph.PlotDataItem.symbolPen`."""
        self._prepare_pens_in_opts()
        return self.opts.get('symbolPen')

    def _prepare_pens_in_opts(self) -> None:
        """
        Despite having access to :func:`pyqtgraph.mkPen` which returns :class:`PyQt5.QtGui.QPen`'s,
        :class:`pyqtgraph.PlotDataItem`'s :attr:`~pyqtgraph.PlotDataItem.pen` and
        :attr:`pyqtgraph.PlotDataItem.symbolPen` are initialized with (R,G,B) tuples instead of
        :class:`PyQt5.QtGui.QPen`'s. This functions tries to transform all pens of the :class:`pyqtgraph,PlotDataItem`
        to :class:`PyQt5.QtGui.QPen`s to have consistent types and access to :class:`PyQt5.QtGui.QPen` functionality.
        """
        potential_pen = self.opts.get('pen')
        potential_symbol_pen = self.opts.get('symbolPen')
        if not isinstance(potential_pen, QPen):
            self.opts['pen'] = pg.mkPen(potential_pen)
        if not isinstance(potential_symbol_pen, QPen):
            self.opts['symbolPen'] = pg.mkPen(potential_symbol_pen)

    # Functions implemented from superclass

    @property
    def color_string(self) -> str:
        return str(utilities.colors.svg_color_from_hex(self.color.name(), hex_on_fail=True))

    @color_string.setter
    def color_string(self, new_color_string: str) -> None:
        self.color = QColor(str(new_color_string))

    @property
    def color(self) -> QColor:
        return self.pen.color()

    @color.setter
    def color(self, new_color: Union[str, QColor]) -> None:
        if isinstance(new_color, str):
            self.color_string = new_color
        else:
            self.pen.setColor(new_color)
            self.symbol_pen.setColor(new_color)

    @property
    def label(self) -> str:
        return cast(pg.PlotDataItem, self).name()

    @label.setter
    def label(self, new_name: str) -> None:
        if self.opts.get('name', None) != new_name:
            self.opts['name'] = new_name

    @property
    def line_style(self) -> int:
        return self.pen.style()

    @line_style.setter
    def line_style(self, line_style: int) -> None:
        if line_style in self.lines.values():
            self.pen.setStyle(line_style)

    @property
    def line_width(self) -> Union[float, int]:
        return self.pen.width()

    @line_width.setter
    def line_width(self, line_width: Union[float, int]) -> None:
        self.pen.setWidth(int(line_width))

    @property
    def symbol(self) -> Optional[str]:
        return self.opts['symbol']

    @symbol.setter
    def symbol(self, symbol: str) -> None:
        if symbol in self.symbols.values():
            pg_self = cast(pg.PlotDataItem, self)
            pg_self.setSymbol(symbol)
            pg_self.setSymbolPen(self.color)

    @property
    def symbol_size(self) -> int:
        return self.opts['symbolSize']

    @symbol_size.setter
    def symbol_size(self, symbol_size: int) -> None:
        cast(pg.PlotDataItem, self).setSymbolSize(int(symbol_size))


class CBarGraphPropertiesBase(CItemPropertiesBase):

    """
    Base class for different bar graph properties. This classes uses
    attributes of the :class:`accwidgets.graph.LiveBarGraphItem` and should only be used as a
    base class in classes derived from :class:`accwidgets.graph.LiveBarGraphItem`.
    """

    plotting_item_editor_supported_columns: List[str] = [
        ColumnNames.CHANNEL.value,
        ColumnNames.LABEL.value,
        ColumnNames.COLOR.value,
        ColumnNames.LINE_WIDTH.value,
        ColumnNames.LAYER.value,
        ColumnNames.STYLE.value,
    ]

    def __init__(self):
        CItemPropertiesBase.__init__(self)
        if not isinstance(self, accgraph.AbstractBaseBarGraphItem):
            logger.warning(
                f'{CBarGraphPropertiesBase.__name__} implementation relies '
                f'on attributes provided by {accgraph.AbstractBaseBarGraphItem.__name__}. '
                f'Use {CBarGraphPropertiesBase.__name__} only as base class '
                f'of classes derived from {accgraph.LiveBarGraphItem.__name__}.',
            )

    @property
    def style_string(self) -> str:
        return PlottingItemTypes.BAR_GRAPH.value

    # Properties for convenient access to PlotDataItem.opts

    @property
    def brush(self) -> QBrush:
        """Grant easier access to :class:`~pyqtgraph.graphicsItems.GraphItem.GraphItem`'s pen"""
        self._prepare_pens_in_opts()
        return self.opts.get('brush')

    @property
    def pen(self) -> QPen:
        """Grant easier access to :class:`~pyqtgraph.graphicsItems.GraphItem.GraphItem`'s pen"""
        self._prepare_pens_in_opts()
        return self.opts.get('pen')

    def _prepare_pens_in_opts(self) -> None:
        """
        Despite having access to mkPen() which returns QPens, BarGraphItem's
        pen and symbolPen are initialized with (R,G,B) tuples instead of
        QPen's. This functions tries to transform all pens of the BarGraphItem
        to QPens to have consistent types and access to QPen functionality.
        """
        potential_pen = self.opts.get('pen')
        potential_brush = self.opts.get('brush')
        if not isinstance(potential_pen, QPen):
            self.opts['pen'] = pg.mkPen(potential_pen)
        if not isinstance(potential_brush, QBrush):
            self.opts['brush'] = pg.mkBrush(potential_brush)

    # Overwritten getters and setters for properties

    @property
    def color_string(self) -> str:
        color: Optional[QColor] = self.color
        if color is not None:
            return str(utilities.colors.svg_color_from_hex(color.name(), hex_on_fail=True))
        return ''

    @color_string.setter
    def color_string(self, new_color_string: str) -> None:
        self.color = QColor(str(new_color_string))

    @property
    def color(self) -> Optional[QColor]:
        return self.brush.color()

    @color.setter
    def color(self, new_color: Union[str, QColor]) -> None:
        if isinstance(new_color, str):
            self.color_string = new_color
        else:
            cast(pg.BarGraphItem, self).setOpts(brush=pg.mkBrush(new_color), pen=None)

    @property
    def line_width(self) -> Union[float, int]:
        return self._fixed_bar_width

    @line_width.setter
    def line_width(self, line_width: Union[float, int]) -> None:
        if line_width >= 0:
            self._fixed_bar_width = line_width


class CInjectionBarGraphPropertiesBase(CItemPropertiesBase):

    """
    Base class for different injection bar properties. This classes
    uses attributes of the LiveInjectionBarGraphItem and should only
    be used as a base class in classes derived from
    LiveInjectionBarGraphItem.
    """

    plotting_item_editor_supported_columns: List[str] = [
        ColumnNames.CHANNEL.value,
        ColumnNames.LABEL.value,
        ColumnNames.COLOR.value,
        ColumnNames.LINE_WIDTH.value,
        ColumnNames.LAYER.value,
        ColumnNames.STYLE.value,
    ]

    def __init__(self):
        CItemPropertiesBase.__init__(self)
        if not isinstance(self, accgraph.AbstractBaseInjectionBarGraphItem):
            logger.warning(
                f'{CInjectionBarGraphPropertiesBase.__name__} implementation relies '
                f'on attributes provided by {accgraph.AbstractBaseInjectionBarGraphItem.__name__}. '
                f'Use {CInjectionBarGraphPropertiesBase.__name__} only as base class '
                f'of classes derived from {accgraph.LiveInjectionBarGraphItem.__name__}.',
            )

    @property
    def style_string(self) -> str:
        return PlottingItemTypes.INJECTION_BAR_GRAPH.value

    # Properties for convenient access to PlotDataItem.opts

    @property
    def pen(self) -> QPen:
        """Grant easier access to ErrorBarItem's pen"""
        self._prepare_pens_in_opts()
        return self.opts['pen']

    def _prepare_pens_in_opts(self) -> None:
        """
        Despite having access to mkPen() which returns QPens, ErrorBarItem's
        pen and symbolPen are initialized with (R,G,B) tuples instead of
        QPen's. This functions tries to transform all pens of the ErrorBarItem
        to QPens to have consistent types and access to QPen functionality.
        """
        potential_pen = self.opts.get('pen')
        potential_symbol_pen = self.opts.get('symbolPen')
        if not isinstance(potential_pen, QPen):
            self.opts['pen'] = pg.mkPen(potential_pen)
        if not isinstance(potential_symbol_pen, QPen):
            self.opts['symbolPen'] = pg.mkPen(potential_symbol_pen)

    # Functions implemented from superclass

    @property
    def color_string(self) -> str:
        return str(utilities.colors.svg_color_from_hex(self.color.name(), hex_on_fail=True))

    @color_string.setter
    def color_string(self, new_color_string: str) -> None:
        self.color = QColor(str(new_color_string))

    @property
    def color(self) -> QColor:
        return self.pen.color()

    @color.setter
    def color(self, new_color: Union[str, QColor]) -> None:
        if isinstance(new_color, str):
            self.color_string = new_color
        else:
            self.pen.setColor(new_color)

    @property
    def line_width(self) -> Union[float, int]:
        return self.pen.width()

    @line_width.setter
    def line_width(self, line_width: Union[float, int]) -> None:
        self.pen.setWidth(int(line_width))


class CTimestampMarkerPropertiesBase(CItemPropertiesBase):

    """
    Base class for different timestamp marker properties. This
    classes uses attributes of the LiveTimestampMarker and should
    only be used as a base class in classes derived from
    LiveTimestampMarker.
    """

    plotting_item_editor_supported_columns: List[str] = [
        ColumnNames.CHANNEL.value,
        ColumnNames.LABEL.value,
        ColumnNames.LINE_STYLE.value,
        ColumnNames.LAYER.value,
        ColumnNames.STYLE.value,
    ]

    def __init__(self):
        CItemPropertiesBase.__init__(self)
        if not isinstance(self, accgraph.AbstractBaseTimestampMarker):
            logger.warning(
                f'{CTimestampMarkerPropertiesBase.__name__} implementation relies '
                f'on attributes provided by {accgraph.AbstractBaseTimestampMarker.__name__}. '
                f'Use {CTimestampMarkerPropertiesBase.__name__} only as base class '
                f'of classes derived from {accgraph.LiveTimestampMarker.__name__}.',
            )

    @property
    def style_string(self) -> str:
        return PlottingItemTypes.TIMESTAMP_MARKERS.value

    # Functions implemented from superclass

    @property
    def line_width(self) -> Union[float, int]:
        return self.opts.get('pen_width', 0)

    @line_width.setter
    def line_width(self, line_width: Union[float, int]) -> None:
        self.opts['pen_width'] = line_width


# ~~~~~~~~~~~~~~~~~~~~~~ Scrolling Plotting Items ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class CScrollingCurve(
        accgraph.ScrollingPlotCurve,
        CCurvePropertiesBase,
):

    """
    Scrolling curve for a scrolling plot widget that
    receives its data through a :class:`~pydm.widgets.channel.PyDMChannel`.
    """

    def __init__(
            self,
            plot_item: accgraph.ExPlotItem,
            data_model: Union[accgraph.LiveCurveDataModel, accgraph.UpdateSource],
            buffer_size: int = accgraph.DEFAULT_BUFFER_SIZE,
            color: Optional[str] = None,
            line_width: Optional[int] = None,
            line_style: Optional[int] = None,
            **kwargs,
    ):
        """
        Create new scrolling curve for a scrolling plot.

        Args:
            plot_item: plot item that the item will be added to
            data_model: Either an Update Source or a already initialized data
                        model
            buffer_size: Buffer size, which will be passed to the data model,
                         will only be used if the data_model is only an Update
                         Source.
            color: color for the item
            line_width: thickness of the lines of the item
            line_style: style of the lines of them item
            kwargs: further keyword arguments for the base class
        """
        accgraph.ScrollingPlotCurve.__init__(
            self,
            plot_item=plot_item,
            data_model=data_model,
            buffer_size=buffer_size,
            pen=color,
            lineWidth=line_width,
            lineStyle=line_style,
            **kwargs,
        )
        CCurvePropertiesBase.__init__(self)
        CCurvePropertiesBase.initialize_style_properties(
            self,
            color=color,
            line_style=line_style,
            line_width=line_width,
        )


class CScrollingBarGraph(
        accgraph.ScrollingBarGraphItem,
        CBarGraphPropertiesBase,
):

    """
    Scrolling bar graph item for a scrolling plot widget that
    receives its data through a :class:`~pydm.widgets.channel.PyDMChannel`.
    """

    def __init__(
            self,
            plot_item: accgraph.ExPlotItem,
            data_model: Union[accgraph.LiveBarGraphItem, accgraph.UpdateSource],
            buffer_size: int = accgraph.DEFAULT_BUFFER_SIZE,
            color: Optional[str] = None,
            line_width: Optional[int] = None,
            line_style: Optional[int] = None,
            **kwargs,
    ):
        """
        Create new scrolling bar graph for a scrolling plot.

        Args:
            plot_item: plot item that the item will be added to
            data_model: Either an Update Source or a already initialized data
                        model
            buffer_size: Buffer size, which will be passed to the data model,
                         will only be used if the data_model is only an Update
                         Source.
            color: color for the item
            line_width: thickness of the lines of the item
            line_style: will have no visual effect, this parameter
                        exists just for saving it between different
                        plotting items to not loose it
            kwargs: further keyword arguments for the base class
        """
        if line_width is not None:
            kwargs['width'] = line_width
        accgraph.ScrollingBarGraphItem.__init__(
            self,
            plot_item=plot_item,
            data_model=data_model,
            buffer_size=buffer_size,
            **kwargs,
        )
        CBarGraphPropertiesBase.__init__(self)
        CBarGraphPropertiesBase.initialize_style_properties(
            self,
            color=color,
            line_style=line_style,
            line_width=line_width,
        )


class CScrollingInjectionBarGraph(
        accgraph.ScrollingInjectionBarGraphItem,
        CInjectionBarGraphPropertiesBase,
):

    """
    Scrolling injection bar graph for a scrolling plot widget
    that receives its data through a :class:`~pydm.widgets.channel.PyDMChannel`.
    """

    def __init__(
            self,
            plot_item: accgraph.ExPlotItem,
            data_model: Union[accgraph.LiveInjectionBarDataModel, accgraph.UpdateSource],
            buffer_size: int = accgraph.DEFAULT_BUFFER_SIZE,
            color: Optional[str] = None,
            line_width: Optional[int] = None,
            line_style: Optional[int] = None,
            **kwargs,
    ):
        """
        Create new scrolling injection bar graph for a scrolling plot.

        Args:
            plot_item: plot item that the item will be added to
            data_model: Either an Update Source or a already initialized data
                        model
            buffer_size: Buffer size, which will be passed to the data model,
                         will only be used if the data_model is only an Update
                         Source.
            color: color for the item
            line_width: thickness of the lines of the item
            line_style: will have no visual effect, this parameter
                        exists just for saving it between different
                        plotting items to not loose it
            kwargs: further keyword arguments for the base class
        """
        accgraph.ScrollingInjectionBarGraphItem.__init__(
            self,
            plot_item=plot_item,
            data_model=data_model,
            buffer_size=buffer_size,
            **kwargs,
        )
        CInjectionBarGraphPropertiesBase.__init__(self)
        CInjectionBarGraphPropertiesBase.initialize_style_properties(
            self,
            color=color,
            line_style=line_style,
            line_width=line_width,
        )


class CScrollingTimestampMarker(
        accgraph.ScrollingTimestampMarker,
        CTimestampMarkerPropertiesBase,
):

    """
    Scrolling timestamp markers for a scrolling plot widget that
    receives its data through a :class:`~pydm.widgets.channel.PyDMChannel`.
    """

    def __init__(
            self,
            plot_item: accgraph.ExPlotItem,
            data_model: Union[accgraph.LiveTimestampMarkerDataModel, accgraph.UpdateSource],
            buffer_size: int = accgraph.DEFAULT_BUFFER_SIZE,
            color: Optional[str] = None,
            line_width: Optional[int] = None,
            line_style: Optional[int] = None,
            **kwargs,
    ):
        """
        Create new scrolling time stamp marker for a scrolling plot.

        Args:
            plot_item: plot item that the item will be added to
            data_model: Either an Update Source or a already initialized data
                        model
            buffer_size: Buffer size, which will be passed to the data model,
                         will only be used if the data_model is only an Update
                         Source.
            color: will have no visual effect, this parameter
                   exists just for saving it between different
                   plotting items to not loose it
            line_width: thickness of the lines of the item
            line_style: will have no visual effect, this parameter
                        exists just for saving it between different
                        plotting items to not loose it
            kwargs: further keyword arguments for the base class
        """
        accgraph.ScrollingTimestampMarker.__init__(
            self,
            plot_item=plot_item,
            data_model=data_model,
            buffer_size=buffer_size,
            **kwargs,
        )
        CTimestampMarkerPropertiesBase.__init__(self)
        CTimestampMarkerPropertiesBase.initialize_style_properties(
            self,
            color=color,
            line_style=line_style,
            line_width=line_width,
        )


class CScrollingPlot(CPlotWidgetBase, accgraph.ScrollingPlotWidget):

    ITEM_TYPES: OrderedDict = OrderedDict([
        (PlottingItemTypes.LINE_GRAPH.value, CScrollingCurve),
        (PlottingItemTypes.BAR_GRAPH.value, CScrollingBarGraph),
        (PlottingItemTypes.INJECTION_BAR_GRAPH.value, CScrollingInjectionBarGraph),
        (PlottingItemTypes.TIMESTAMP_MARKERS.value, CScrollingTimestampMarker),
    ])

    def __init__(
            self,
            parent: QWidget = None,
            background: str = 'default',
            time_span: Union[accgraph.TimeSpan, float, None] = 60.0,
            time_progress_line: bool = False,
            axis_items: Optional[Dict[str, pg.AxisItem]] = None,
            timing_source: Optional[accgraph.UpdateSource] = None,
            **plotitem_kwargs,
    ):
        """
        Plot widget for displaying scrolling curves, bar graphs and other
        plotting items.

        Args:
            parent: Parent item for the Plot
            background: Background color for the Plot
        """
        accgraph.ScrollingPlotWidget.__init__(
            self,
            parent=parent,
            background=background,
            time_span=time_span,
            time_progress_line=time_progress_line,
            axis_items=axis_items,
            timing_source=timing_source,
            **plotitem_kwargs,
        )
        CPlotWidgetBase.__init__(self)


# ~~~~~~~~~~~~~~~~~~~~~~ Cyclic Plotting Items ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CCyclicCurve(accgraph.CyclicPlotCurve, CCurvePropertiesBase):

    """
    Cyclic curve for a cyclic plot widget that
    receives its data through a :class:`~pydm.widgets.channel.PyDMChannel`.
    """

    def __init__(
            self,
            plot_item: accgraph.ExPlotItem,
            data_model: Union[accgraph.LiveCurveDataModel, accgraph.UpdateSource],
            buffer_size: int = accgraph.DEFAULT_BUFFER_SIZE,
            color: Optional[str] = None,
            line_width: Optional[int] = None,
            line_style: Optional[int] = None,
            **kwargs,
    ):
        """
        Create new cyclic curve for a cyclic plot.

        Args:
            plot_item: plot item that the item will be added to
            data_model: Either an Update Source or a already initialized data
                        model
            buffer_size: Buffer size, which will be passed to the data model,
                         will only be used if the data_model is only an Update
                         Source.
            color: color for the item
            line_width: thickness of the lines of the item
            line_style: style of the lines of them item
            kwargs: further keyword arguments for the base class
        """
        accgraph.CyclicPlotCurve.__init__(
            self,
            plot_item=plot_item,
            buffer_size=buffer_size,
            data_model=data_model,
            pen=color,
            lineWidth=line_width,
            lineStyle=line_style,
            **kwargs,
        )
        CCurvePropertiesBase.__init__(self)
        CCurvePropertiesBase.initialize_style_properties(
            self,
            color=color,
            line_style=line_style,
            line_width=line_width,
        )


class CCyclicPlot(CPlotWidgetBase, accgraph.CyclicPlotWidget):
    """Plot widget for displaying cyclic curves."""

    ITEM_TYPES: OrderedDict = OrderedDict([
        (PlottingItemTypes.LINE_GRAPH.value, CCyclicCurve),
        (PlottingItemTypes.BAR_GRAPH.value, None),
        (PlottingItemTypes.INJECTION_BAR_GRAPH.value, None),
        (PlottingItemTypes.TIMESTAMP_MARKERS.value, None),
    ])

    def __init__(
            self,
            parent: QWidget = None,
            background: str = 'default',
            time_span: Union[accgraph.TimeSpan, float, None] = 60.0,
            time_progress_line: bool = False,
            axis_items: Optional[Dict[str, pg.AxisItem]] = None,
            timing_source: Optional[accgraph.UpdateSource] = None,
            **plotitem_kwargs,
    ):
        accgraph.CyclicPlotWidget.__init__(
            self,
            parent=parent,
            background=background,
            time_span=time_span,
            time_progress_line=time_progress_line,
            axis_items=axis_items,
            timing_source=timing_source,
            **plotitem_kwargs,
        )
        CPlotWidgetBase.__init__(self)


# ~~~~~~~~~~~~~~~~~~~~~ Static Plot ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class CStaticCurve(accgraph.StaticPlotCurve, CCurvePropertiesBase):

    def __init__(
            self,
            plot_item: accgraph.ExPlotItem,
            data_model: Union[accgraph.LiveCurveDataModel, accgraph.UpdateSource],
            color: Optional[str] = None,
            line_width: Optional[int] = None,
            line_style: Optional[int] = None,
            **kwargs,
    ):
        """
        Static Curve for a static plot widget that
        receives its data through a :class:`~pydm.widgets.channel.PyDMChannel`.

        Args:
            plot_item: plot item that the item will be added to
            data_model: Either an Update Source or a already initialized data
                        model
            color: color for the item
            line_width: thickness of the lines of the item
            line_style: style of the lines of them item
            kwargs: further keyword arguments for the base class
        """
        accgraph.StaticPlotCurve.__init__(
            self,
            plot_item=plot_item,
            data_model=data_model,
            pen=color,
            lineWidth=line_width,
            lineStyle=line_style,
            **kwargs,
        )
        CCurvePropertiesBase.__init__(self)
        CCurvePropertiesBase.initialize_style_properties(
            self,
            color=color,
            line_style=line_style,
            line_width=line_width,
        )


class CStaticBarGraph(accgraph.StaticBarGraphItem, CBarGraphPropertiesBase):

    def __init__(
            self,
            plot_item: accgraph.ExPlotItem,
            data_model: Union[accgraph.LiveBarGraphItem, accgraph.UpdateSource],
            color: Optional[str] = None,
            line_width: Optional[int] = None,
            line_style: Optional[int] = None,
            **kwargs,
    ):
        """
        Static bar graph item for a static plot widget that
        receives its data through a :class:`~pydm.widgets.channel.PyDMChannel`.

        Args:
            plot_item: plot item that the item will be added to
            data_model: Either an Update Source or a already initialized data
                        model
            color: color for the item
            line_width: thickness of the lines of the item
            line_style: will have no visual effect, this parameter
                        exists just for saving it between different
                        plotting items to not loose it
            kwargs: further keyword arguments for the base class
        """
        if line_width is not None:
            kwargs['width'] = line_width
        accgraph.StaticBarGraphItem.__init__(
            self,
            plot_item=plot_item,
            data_model=data_model,
            **kwargs,
        )
        CBarGraphPropertiesBase.__init__(self)
        CBarGraphPropertiesBase.initialize_style_properties(
            self,
            color=color,
            line_style=line_style,
            line_width=line_width,
        )


class CStaticInjectionBarGraph(accgraph.StaticInjectionBarGraphItem,
                               CInjectionBarGraphPropertiesBase):

    def __init__(
            self,
            plot_item: accgraph.ExPlotItem,
            data_model: Union[accgraph.LiveInjectionBarDataModel, accgraph.UpdateSource],
            color: Optional[str] = None,
            line_width: Optional[int] = None,
            line_style: Optional[int] = None,
            **kwargs,
    ):
        """
        Static injection bar graph for a static plot widget
        that receives its data through a :class:`~pydm.widgets.channel.PyDMChannel`.

        Args:
            plot_item: plot item that the item will be added to
            data_model: Either an Update Source or a already initialized data
                        model
            color: color for the item
            line_width: thickness of the lines of the item
            line_style: will have no visual effect, this parameter
                        exists just for saving it between different
                        plotting items to not loose it
            kwargs: further keyword arguments for the base class
        """
        accgraph.StaticInjectionBarGraphItem.__init__(
            self,
            plot_item=plot_item,
            data_model=data_model,
            **kwargs,
        )
        CInjectionBarGraphPropertiesBase.__init__(self)
        CInjectionBarGraphPropertiesBase.initialize_style_properties(
            self,
            color=color,
            line_style=line_style,
            line_width=line_width,
        )


class CStaticTimestampMarker(accgraph.StaticTimestampMarker,
                             CTimestampMarkerPropertiesBase):

    def __init__(
            self,
            plot_item: accgraph.ExPlotItem,
            data_model: Union[accgraph.LiveTimestampMarkerDataModel, accgraph.UpdateSource],
            color: Optional[str] = None,
            line_width: Optional[int] = None,
            line_style: Optional[int] = None,
            **kwargs,
    ):
        """
        Static timestamp markers for a static plot widget that
        receives its data through a :class:`~pydm.widgets.channel.PyDMChannel`.

        Args:
            plot_item: plot item that the item will be added to
            data_model: Either an Update Source or a already initialized data
                        model
            color: will have no visual effect, this parameter
                   exists just for saving it between different
                   plotting items to not loose it
            line_width: thickness of the lines of the item
            line_style: will have no visual effect, this parameter
                        exists just for saving it between different
                        plotting items to not loose it
            kwargs: further keyword arguments for the base class
        """
        accgraph.StaticTimestampMarker.__init__(
            self,
            plot_item=plot_item,
            data_model=data_model,
            **kwargs,
        )
        CTimestampMarkerPropertiesBase.__init__(self)
        CTimestampMarkerPropertiesBase.initialize_style_properties(
            self,
            color=color,
            line_style=line_style,
            line_width=line_width,
        )


class CStaticPlot(CPlotWidgetBase, accgraph.StaticPlotWidget):

    ITEM_TYPES: OrderedDict = OrderedDict([
        (PlottingItemTypes.LINE_GRAPH.value, CStaticCurve),
        (PlottingItemTypes.BAR_GRAPH.value, CStaticBarGraph),
        (PlottingItemTypes.INJECTION_BAR_GRAPH.value, CStaticInjectionBarGraph),
        (PlottingItemTypes.TIMESTAMP_MARKERS.value, CStaticTimestampMarker),
    ])

    _SOURCE_EMIT_TYPE: OrderedDict = OrderedDict([
        (PlottingItemTypes.LINE_GRAPH.value, accgraph.CurveData),
        (PlottingItemTypes.BAR_GRAPH.value, accgraph.BarCollectionData),
        (PlottingItemTypes.INJECTION_BAR_GRAPH.value, accgraph.InjectionBarCollectionData),
        (PlottingItemTypes.TIMESTAMP_MARKERS.value, accgraph.TimestampMarkerCollectionData),
    ])

    def __init__(
            self,
            parent: QWidget = None,
            background: str = 'default',
            axis_items: Optional[Dict[str, pg.AxisItem]] = None,
            **plotitem_kwargs,
    ):
        """
        Plot widget for displaying static items. Static means in this case,
        that the plot itself is not moving its view anywhere (other than with
        live data plots). Example items that are suitable for this plot are
        waveform curves.

        Args:
            parent: parent widget for this plot
            background: background color for the plot widget
            axis_items: mapping of positions in the plot ('left', 'right', ...)
                        to axis items which should be used
            plotitem_kwargs: Further Keyword arguments for the plot item base
                             class
        """
        accgraph.StaticPlotWidget.__init__(
            self,
            parent=parent,
            background=background,
            axis_items=axis_items,
            **plotitem_kwargs,
        )
        CPlotWidgetBase.__init__(self)

# TODO: Make available when proven useful
# class CImageView(CWidgetRulesMixin, CCustomizedTooltipMixin, CHideUnusedFeaturesMixin, PyDMImageView):
#
#     def __init__(self,
#                  parent: Optional[QWidget] = None,
#                  image_channel: Optional[str] = None,
#                  width_channel: Optional[str] = None,
#                  **kwargs):
#         """
#         A :class:`pyqtgraph.ImageView` subclass with support for CS Channels.
#
#         If there is no :attr:`widthChannel` it is possible to define the width of
#         the image with the :attr:`width` property.
#
#         The :attr:`normalizeData` property defines if the colors of the images are
#         relative to the :attr:`colorMapMin` and :attr:`colorMapMax` property or to
#         the minimum and maximum values of the image.
#
#         Use the :attr:`newImageSignal` to hook up to a signal that is emitted when a new
#         image is rendered in the widget.
#
#         Args:
#             parent: The parent widget for the image view.
#             image_channel: The channel to be used by the widget for the image data.
#             width_channel: The channel to be used by the widget to receive the image width information.
#             **kwargs: Any future extras that need to be passed down to PyDM.
#         """
#         CWidgetRulesMixin.__init__(self)
#         CCustomizedTooltipMixin.__init__(self)
#         CHideUnusedFeaturesMixin.__init__(self)
#         PyDMImageView.__init__(self, parent=parent, image_channel=image_channel, width_channel=width_channel, **kwargs)
#
#     def default_rule_channel(self) -> str:
#         return self.imageChannel
