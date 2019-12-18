"""Graphs based on the library accsoft_gui_pyqt_widgets's package graph for comrad"""

from enum import Enum
import abc
from typing import cast, Type, Optional, Union, List, Dict, Iterable, Any
import json
import time
import copy
from collections import OrderedDict
import functools
import logging

from qtpy.QtWidgets import QWidget, QStyledItemDelegate, QComboBox, QStyleOptionViewItem
from qtpy.QtGui import QColor, QPen, QBrush
from qtpy.QtCore import Property, QObject, QModelIndex, QVariant, QAbstractTableModel, Qt
import pyqtgraph as pg
# from pydm.widgets.image import PyDMImageView
from pydm.widgets.baseplot import BasePlotCurveItem, PyDMPrimitiveWidget
from pydm.widgets.base import widget_destroyed
from pydm.widgets.channel import PyDMChannel
from pydm.widgets.baseplot_curve_editor import BasePlotCurvesModel, BasePlotCurveEditorDialog
from pydm.widgets.qtplugin_extensions import BasePlotExtension
from pydm import utilities
from accwidgets import graph as accgraph

LOGGER = logging.getLogger(__name__)


class ColumnNames(Enum):

    """
    Column names as strings for the plotting item editor dialog's table
    """

    channel: str = "Channel"
    label: str = "Label"
    color: str = "Color"
    line_style: str = "Line Style"
    line_width: str = "Item Width"
    symbol: str = "Symbol"
    symbol_size: str = "Symbol Size"
    layer: str = "Layer"
    style: str = "Style"


class PlottingStyles(Enum):

    """
    String values representing different plotting items (curve, bar graph, etc.).
    """

    line_graph: str = "Line Graph"
    bar_graph: str = "Bar Graph"
    injection_bar_graph: str = "Injection Bar Graph"
    timestamp_markers: str = "Timestamp Marker"


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
        Create a new source that is attached to a PyDM Channel

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
        self.address = channel_address

    @property
    def address(self) -> str:
        """Get the PyDMChannel the update source is based on."""
        if self._channel is not None:
            return self._channel.address
        return ""

    @address.setter
    def address(self, new_address: str) -> None:
        """
        Replace the PyDMChannel with one created from the passed channel address.

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
        """Get the current PyDMChannel the update source is based on."""
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
        if value is None:
            return
        if issubclass(self._data_type_to_emit, accgraph.PointData):
            kwargs = self._prepare_point_data_arguments(value)
        elif issubclass(self._data_type_to_emit, accgraph.BarData):
            kwargs = self._prepare_bar_data_arguments(value)
        elif issubclass(self._data_type_to_emit, accgraph.InjectionBarData):
            kwargs = self._prepare_injection_bar_data_arguments(value)
        elif issubclass(self._data_type_to_emit, accgraph.TimestampMarkerData):
            kwargs = self._prepare_timestamp_marker_data_arguments(value)
        else:
            return
        self.sig_data_update[self._data_type_to_emit].emit(self._data_type_to_emit(**kwargs))

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
        if value is None or (isinstance(value, (tuple, list)) and len(value) == 0):
            LOGGER.warning(
                f"Data {value} could not be properly interpreted and will be dropped."
            )
            return None
        if isinstance(value, (int, float)):
            value = [value]
        if isinstance(value, tuple):
            value = list(value)
        value = cast(List[float], value)
        if value == self._last_value:
            return None
        self._last_value = copy.copy(value)
        return value

    @staticmethod
    def _prepare_point_data_arguments(
            values: Union[
                List[float],
                List[int],
            ],
    ) -> Dict:
        """
        Convert list to a dictionary of keyword arguments for PointData.
        """
        kwargs = OrderedDict(
            x_value=time.time(),
            y_value=0.0,
        )
        return PyDMChannelDataSource._list_to_dict(kwargs, values)

    @staticmethod
    def _prepare_bar_data_arguments(
            values: Union[List[float], List[int]],
    ) -> Dict:
        """
        Convert list to a dictionary of keyword arguments for BarData.
        """
        kwargs = OrderedDict(
            x_value=time.time(),
            y_value=0.0,
            height=0.0,
        )
        return PyDMChannelDataSource._list_to_dict(kwargs, values)

    @staticmethod
    def _prepare_injection_bar_data_arguments(
            values: Union[List[float], List[int]],
    ) -> Dict:
        """Convert list to a dictionary of keyword arguments for InjectionBarData."""
        kwargs = OrderedDict(
            x_value=time.time(),
            y_value=0.0,
            height=0.0,
            width=0.0,
            label="",
        )
        return PyDMChannelDataSource._list_to_dict(kwargs, values)

    @staticmethod
    def _prepare_timestamp_marker_data_arguments(
            values: Union[List[float], List[int]],
    ) -> Dict:
        """Convert list to a dictionary of keyword arguments for TimestampMarkerData."""
        kwargs = OrderedDict(
            x_value=time.time(),
            color="white",
            label="",
        )
        return PyDMChannelDataSource._list_to_dict(kwargs, values)

    @staticmethod
    def _list_to_dict(keyword_args: OrderedDict, values_list: List):
        """
        Set values in dictionary according to the passed values list.
        If more keys exist than values in the list, values are set in the
        order the keys are listed in the dict. If more values are passed,
        they will be ignored.
        """
        for key in keyword_args.keys():
            try:
                keyword_args[key] = values_list.pop(0)
            except IndexError:
                break
        return keyword_args


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~ Base Classes ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class CPlotWidgetBase(PyDMPrimitiveWidget):

    """
    Base class providing functions used by the plotting item editor dialog
    for adding, removing and editing plotting items in a graph. This class
    allows sharing these functions with their implementation in
    different plot widgets.

    This class uses attributes of the ExPlotWidget and should only
    be used as a base class in classes derived from ExPlotWidget.
    For overwritten functions to be picked up, this class has to
    be mentioned before the ExPlotWidget in the derived classes definition
    of super classes:

    class Derived(CPlotWidgetBase, ExPlotWidget)  -> function's are overwritten

    class Derived(ExPlotWidget, CPlotWidgetBase)  -> original functions are picked up

    Subclasses can define in the class attribute **ITEM_TYPES** what
    type of plotting items they can display for which style. If the
    value is set to None, the style is interpreted as not supported.
    """

    ITEM_TYPES: OrderedDict = OrderedDict([
        (PlottingStyles.line_graph.value, None),
        (PlottingStyles.bar_graph.value, None),
        (PlottingStyles.injection_bar_graph.value, None),
        (PlottingStyles.timestamp_markers.value, None),
    ])

    # Which data structure is emitted on which plotting item style
    _SOURCE_EMIT_TYPE: OrderedDict = OrderedDict([
        (PlottingStyles.line_graph.value, accgraph.PointData),
        (PlottingStyles.bar_graph.value, accgraph.BarData),
        (PlottingStyles.injection_bar_graph.value, accgraph.InjectionBarData),
        (PlottingStyles.timestamp_markers.value, accgraph.TimestampMarkerData),
    ])

    def __init__(self):
        super().__init__()
        if not isinstance(self, accgraph.ExPlotWidget):
            LOGGER.warning(
                f"{CPlotWidgetBase.__name__} implementation relies on attributes"
                f"provided by {accgraph.ExPlotWidget.__name__}. "
                f"Use {CPlotWidgetBase.__name__} only as base class of classes"
                f"derived from {accgraph.ExPlotWidget.__name__}.",
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
        return self._items

    # Overwritten add... functions of the ExPlotWidget

    def addCurve(
            self,
            c: Optional[pg.PlotDataItem] = None,
            params: Optional[Dict[str, Any]] = None,
            data_source: Union[str, accgraph.UpdateSource, None] = None,
            layer_identifier: Optional[str] = None,
            buffer_size: int = accgraph.DEFAULT_BUFFER_SIZE,
            color: Union[str, QColor, None] = None,
            name: Optional[str] = None,
            symbol: Optional[str] = None,
            symbol_size: Optional[int] = None,
            line_style: Optional[int] = None,
            line_width: Optional[int] = None,
    ) -> Union["CItemPropertiesBase", pg.PlotDataItem]:
        """
        This function overrides the ExPlotItem's addCurve function and extends it
        by giving the option to pass a channel address for feeding data to the graph.
        Additionally you can pass stylistic parameters which are the same as
        CItemsPropertyBase's style properties that are supported by the item.

        Args:
            c: param for deprecated addCurve from PyQtGraph, only for catching calls
               for PlotItem.addCurve
            params: param for deprecated addCurve from PyQtGraph, only for catching calls
                    for PlotItem.addCurve
            data_source: Instance of **UpdateSource** that emits data or a string for a
                         channel address
            layer_identifier: Layer in which the curve should be added to
            buffer_size: amount of data the item's data model is holding
            color: color for the lines in the curve
            name: name of the curve that can be displayed in the plots legend (if added)
            symbol: symbol that represents the single data-points, see pg.ScatterPlotItem
                    for all possible values
            symbol_size: size for the symbols
            line_style: Style of the line, see QtCore.Qt PenStyle Enum for values
            line_width: thickness of the line in the graph

        Returns:
            Curve object which was added to the plot.
        """
        if isinstance(data_source, str):
            curve = self.add_channel_attached_item(
                style=PlottingStyles.line_graph.value,
                channel_address=data_source,
                layer=layer_identifier,
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
            layer_identifier=layer_identifier,
            buffer_size=buffer_size,
        )

    def addBarGraph(
            self,
            data_source: Union[str, accgraph.UpdateSource, None] = None,
            layer_identifier: Optional[str] = None,
            buffer_size: int = accgraph.DEFAULT_BUFFER_SIZE,
            color: Union[str, QColor, None] = None,
            bar_width: Optional[int] = None,
    ) -> Union["CItemPropertiesBase", pg.BarGraphItem]:
        """
        This function overrides the ExPlotItem's addBarGraph function and extends it
        by giving the option to pass a channel address for feeding data to the graph.
        Additionally you can pass stylistic parameters which are the same as
        CItemsPropertyBase's style properties that are supported by the item.

        Args:
            data_source: Instance of **UpdateSource** that emits data or a string for a
                         channel address
            layer_identifier: Layer in which the bar graph should be added to
            buffer_size: amount of data the item's data model is holding
            color: Color the bars are displayed in
            bar_width: width of each bar

        Returns:
            bar graph object which was added to the plot.
        """
        if isinstance(data_source, str):
            return self.add_channel_attached_item(
                style=PlottingStyles.bar_graph.value,
                channel_address=data_source,
                layer=layer_identifier,
                color=color,
                line_width=bar_width,
            )
        return accgraph.ExPlotWidget.addBarGraph(
            self,
            data_source=data_source,
            layer_identifier=layer_identifier,
            buffer_size=buffer_size,
        )

    def addInjectionBar(
            self,
            data_source: Union[str, accgraph.UpdateSource],
            layer_identifier: Optional[str] = None,
            buffer_size: int = accgraph.DEFAULT_BUFFER_SIZE,
            color: Union[str, QColor, None] = None,
            line_width: Optional[int] = None,
    ) -> Union["CItemPropertiesBase", pg.BarGraphItem]:
        """
        This function overrides the ExPlotItem's addInjectionBar function and extends it
        by giving the option to pass a channel address for feeding data to the graph.
        Additionally you can pass stylistic parameters which are the same as
        CItemsPropertyBase's style properties that are supported by the item.

        Args:
            data_source: Instance of **UpdateSource** that emits data or a string for a
                         channel address
            layer_identifier: Layer in which the injection bars should be added to
            buffer_size: amount of data the item's data model is holding
            color: Color for the lines in the injection bar
            line_width: Thickness of the lines in the injection bar

        Returns:
            injection bar graph object which was added to the plot.
        """
        if isinstance(data_source, str):
            return self.add_channel_attached_item(
                style=PlottingStyles.injection_bar_graph.value,
                channel_address=data_source,
                layer=layer_identifier,
                color=color,
                line_width=line_width,
            )
        return accgraph.ExPlotWidget.addInjectionBar(
            self,
            data_source=data_source,
            layer_identifier=layer_identifier,
            buffer_size=buffer_size,
        )

    def addTimestampMarker(
            self,
            data_source: Union[str, accgraph.UpdateSource],
            buffer_size: int = accgraph.DEFAULT_BUFFER_SIZE,
            line_width: Optional[int] = None,
    ) -> Union["CItemPropertiesBase", pg.BarGraphItem]:
        """
        This function overrides the ExPlotItem's addTimestampMarker function and extends it
        by giving the option to pass a channel address for feeding data to the graph.
        Additionally you can pass stylistic parameters which are the same as
        CItemsPropertyBase's style properties that are supported by the item.

        Args:
            data_source: Instance of **UpdateSource** that emits data or a string for a
                         channel address
            buffer_size: amount of data the item's data model is holding
            line_width: Thickness of the vertical line representing a specific timestamp

        Returns:
            Curve object that is added to the plot.
        """
        if isinstance(data_source, str):
            return self.add_channel_attached_item(
                style=PlottingStyles.timestamp_markers.value,
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
            style: str = PlottingStyles.line_graph.value,
            layer: Optional[str] = None,
            index: Optional[int] = None,
            name: Optional[str] = None,
            color: Union[str, QColor, None] = None,
            line_style: Optional[int] = None,
            line_width: Optional[int] = None,
            symbol: Optional[str] = None,
            symbol_size: Optional[int] = None,
    ) -> "CItemPropertiesBase":
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
    def _set_item_styling_properties(
            item: "CItemPropertiesBase",
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
            data_source: "PyDMChannelDataSource",
            style: str = PlottingStyles.line_graph.value,
    ) -> "CItemPropertiesBase":
        """
        Create a new plotting item fitting the passed styling.

        Args:
            data_source: data source containing the channel the curve
                         will receive data from
            style: string representation of what item to add
        """
        style = style or PlottingStyles.line_graph.value
        if self.ITEM_TYPES[style] is None:
            raise ValueError(
                f"{type(self).__name__} does not support style '{style}'"
            )
        return self.ITEM_TYPES[style](
            plot_item=self.plotItem,
            data_source=data_source,
        )

    def _add_created_item(
            self,
            new_item: "CItemPropertiesBase",
            layer: Union[str, accgraph.PlotItemLayer, None] = None,
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
        self.plotItem.addItem(item=new_item, layer=layer)

    def remove_channel_attached_item(self, item: "CItemPropertiesBase") -> None:
        """
        Remove a specific item from the plot item.

        Args:
            item : The curve to be removed.
        """
        self.removeItem(item)
        self._items.remove(item)
        for chan in item.channels:
            if chan:
                chan.disconnect()

    def remove_channel_attached_item_at_index(self, index: int) -> None:
        """
        Remove a item from the graph, given its index in the graph's _items list.

        Args:
            index : The item's index in the graph's _items list.
        """
        item = self._items[index]
        self.remove_channel_attached_item(item)

    def _get_items(self) -> List[str]:
        """
        Dump the current list of items and each item's settings into a list
        of JSON-formatted strings. This function is mainly for the Qt Designer plugin
        to represent all curves as one QStringList and not for calling it directly.

        Returns:
            A list of JSON-formatted strings, each containing an item's
            settings
        """
        return [json.dumps(item.to_dict()) for item in self._items]

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
            LOGGER.exception(f"Error parsing item json data: {error}")
            return
        self.clear_items()
        for item in items_loaded:
            self.add_channel_attached_item(
                style=item.get("style", PlottingStyles.line_graph.value),
                channel_address=item.get("channel", ""),
                name=item.get("name"),
                color=item.get("color"),
                line_style=item.get("line_style"),
                line_width=item.get("line_width"),
                symbol=item.get("symbol"),
                symbol_size=item.get("symbol_size"),
                layer=item.get("layer"),
            )

    curves = Property("QStringList", _get_items, _set_items)

    def clear_items(self) -> None:
        """Remove all prior added items from the plot."""
        for item in self._items:
            item.deleteLater()  # type: ignore[attr-defined]
        self.plotItem.clear()
        self._items = []


class CItemPropertiesBase(metaclass=abc.ABCMeta):

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

    plotting_item_editor_supported_columns: List[str] = []
    symbols = BasePlotCurveItem.symbols
    lines = BasePlotCurveItem.lines
    style: List[str] = [
        PlottingStyles.line_graph.value,
        PlottingStyles.bar_graph.value,
        PlottingStyles.injection_bar_graph.value,
        PlottingStyles.timestamp_markers.value,
    ]

    def __init__(self):
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
            self.setSymbolBrush(None)  # type: ignore[attr-defined]
        except AttributeError:
            pass
        # If curve is deleted, remove its listener from the channel
        if hasattr(self, "channels"):
            # widget_destroyed expects a function and calls the passed channels argument
            # -> we have to wrap out property as callable
            self.destroyed.connect(  # type: ignore[attr-defined]
                functools.partial(widget_destroyed, lambda: self.channels)
            )

    def to_dict(self) -> OrderedDict:
        """
        Returns an OrderedDict representation with values for all properties
        needed to recreate this item.
        """
        return OrderedDict([
            ("channel", self.address),
            ("style", self.style_string),
            ("layer", self.layer),
            ("name", self.label),
            ("color", self.color_string),
            ("line_style", self.line_style),
            ("line_width", self.line_width),
            ("symbol", self.symbol),
            ("symbol_size", self.symbol_size),
        ])

    # Properties with implementation shareable through all subclasses

    @property
    def channels(self) -> List[PyDMChannel]:
        """Returns channel the data source is connected to."""
        return [self.data_source.channel]  # type: ignore[attr-defined]

    @property
    def address(self) -> str:
        """Returns the address of the PyDMChannel the data source is based on"""
        return self.data_source.address  # type: ignore[attr-defined]

    @address.setter
    def address(self, new_address: str) -> None:
        """Change the address of the PyDMChannel the data source is based on"""
        self.data_source.address = new_address  # type: ignore[attr-defined]

    @property
    def layer(self) -> str:
        """Returns the address of the PyDMChannel the data source is based on"""
        return self._layer_identifier  # type: ignore[attr-defined]

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
        will be a hex color code, like #FF00FF, or an SVG spec color name, if
        a name exists for the color.
        """
        return str(utilities.colors.svg_color_from_hex(
            self.color.name(), hex_on_fail=True
        ))

    @color_string.setter
    def color_string(self, new_color_string: str) -> None:
        """
        A string representation of the color used for the item. This string
        will be a hex color code, like #FF00FF, or an SVG spec color name, if
        a name exists for the color.

        Args:
            new_color_string: The new string to use for the item color.
        """
        self.color = QColor(str(new_color_string))

    @property
    def color(self) -> QColor:
        """The color used for the item."""
        return getattr(self, "_color", None)

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
        """The name of the item displayed in the Legend."""
        return getattr(self, "_name", "")

    @label.setter
    def label(self, new_name: str) -> None:
        """Set the items name that is displayed in the Legend."""
        self._name = new_name

    @property
    def line_style(self) -> int:
        """
        Return the style of lines used in the item (if supported).
        Must be a value from the Qt::PenStyle enum
        (see http://doc.qt.io/qt-5/qt.html#PenStyle-enum).
        """
        return getattr(self, "_line_style", list(self.lines.values())[0])

    @line_style.setter
    def line_style(self, new_style: int) -> None:
        """
        Set the style of lines used in the item (if supported).
        Must be a value from the Qt::PenStyle enum
        (see http://doc.qt.io/qt-5/qt.html#PenStyle-enum).
        """
        if new_style in self.lines.values():
            self._line_style = new_style

    @property
    def line_width(self) -> int:
        """Return the width of the line connecting the data points."""
        return getattr(self, "_line_width", 1)

    @line_width.setter
    def line_width(self, new_width: int) -> None:
        """Set the width of the line connecting the data points."""
        if new_width >= 0:
            self._line_width = new_width

    @property
    def symbol(self) -> Optional[str]:
        """
        The single-character code for the symbol drawn at each data point.
        See the documentation for pyqtgraph.PlotDataItem for possible values.
        """
        return getattr(self, "_symbol", list(self.symbols.values())[0])

    @symbol.setter
    def symbol(self, new_symbol: Optional[str]) -> None:
        """
        The single-character code for the symbol drawn at each datapoint.
        See the documentation for pyqtgraph.PlotDataItem for possible values.
        """
        if new_symbol in self.symbols.values():
            self._symbol = new_symbol

    @property
    def symbol_size(self) -> int:
        """Return the size of the symbol to represent the data."""
        return getattr(self, "_symbol_size", 10)

    @symbol_size.setter
    def symbol_size(self, new_size: int) -> None:
        """Set the size of the symbol to represent the data."""
        if new_size >= 0:
            self._symbol_size = new_size


class CCurvePropertiesBase(CItemPropertiesBase):

    """
    Base class for different curve properties. This classes uses
    attributes of the LivePlotCurve and should only be used as a
    base class in classes derived from LivePlotCurve.
    """

    plotting_item_editor_supported_columns: List[str] = [e.value for e in ColumnNames]

    def __init__(self):
        CItemPropertiesBase.__init__(self)
        if not isinstance(self, accgraph.LivePlotCurve):
            LOGGER.warning(
                f"{CCurvePropertiesBase.__name__} implementation relies "
                f"on attributes provided by {accgraph.LivePlotCurve.__name__}. "
                f"Use {CCurvePropertiesBase.__name__} only as base class "
                f"of classes derived from {accgraph.LivePlotCurve.__name__}.",
            )

    @property
    def style_string(self) -> str:
        """Returns string representation of the items style"""
        return PlottingStyles.line_graph.value

    # Properties for convenient access to PlotDataItem.opts

    @property
    def pen(self) -> QPen:
        """Grant easier access to PlotDataItems pen"""
        self._prepare_pens_in_opts()
        return self.opts.get("pen")

    @property
    def symbol_pen(self) -> QPen:
        """Grant easier access to PlotDataItems symbolPen"""
        self._prepare_pens_in_opts()
        return self.opts.get("symbolPen")

    def _prepare_pens_in_opts(self) -> None:
        """
        Despite having access to mkPen() which returns QPens, PlotDataItems
        pen and symbolPen are initialized with (R,G,B) tuples instead of
        QPen's. This functions tries to transform all pens of the PlotDataItem
        to QPens to have consistent types and access to QPen functionality.
        """
        potential_pen = self.opts.get("pen")
        potential_symbol_pen = self.opts.get("symbolPen")
        if not isinstance(potential_pen, QPen):
            self.opts["pen"] = pg.mkPen(potential_pen)
        if not isinstance(potential_symbol_pen, QPen):
            self.opts["symbolPen"] = pg.mkPen(potential_symbol_pen)

    # Functions implemented from superclass

    @property
    def color_string(self) -> str:
        return str(utilities.colors.svg_color_from_hex(
            self.color.name(), hex_on_fail=True
        ))

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
        return self.name()  # type: ignore[attr-defined]

    @label.setter
    def label(self, new_name: str) -> None:
        if self.opts.get("name", None) != new_name:
            self.opts["name"] = new_name

    @property
    def line_style(self) -> int:
        return self.pen.style()

    @line_style.setter
    def line_style(self, line_style: int) -> None:
        if line_style in self.lines.values():
            self.pen.setStyle(line_style)

    @property
    def line_width(self) -> int:
        return self.pen.width()

    @line_width.setter
    def line_width(self, line_width: int) -> None:
        self.pen.setWidth(int(line_width))

    @property
    def symbol(self) -> Optional[str]:
        return self.opts["symbol"]

    @symbol.setter
    def symbol(self, symbol: str) -> None:
        if symbol in self.symbols.values():
            self.setSymbol(symbol)  # type: ignore[attr-defined]
            self.setSymbolPen(self.color)  # type: ignore[attr-defined]

    @property
    def symbol_size(self) -> int:
        return self.opts["symbolSize"]

    @symbol_size.setter
    def symbol_size(self, symbol_size: int) -> None:
        self.setSymbolSize(int(symbol_size))  # type: ignore[attr-defined]


class CBarGraphPropertiesBase(CItemPropertiesBase):

    """
    Base class for different bar graph properties. This classes uses
    attributes of the LiveBarGraphItem and should only be used as a
    base class in classes derived from LiveBarGraphItem.
    """

    plotting_item_editor_supported_columns: List[str] = [
        ColumnNames.channel.value,
        ColumnNames.label.value,
        ColumnNames.color.value,
        ColumnNames.line_width.value,
        ColumnNames.layer.value,
        ColumnNames.style.value,
    ]

    def __init__(self):
        CItemPropertiesBase.__init__(self)
        if not isinstance(self, accgraph.LiveBarGraphItem):
            LOGGER.warning(
                f"{CBarGraphPropertiesBase.__name__} implementation relies "
                f"on attributes provided by {accgraph.LiveBarGraphItem.__name__}. "
                f"Use {CBarGraphPropertiesBase.__name__} only as base class "
                f"of classes derived from {accgraph.LiveBarGraphItem.__name__}.",
            )

    @property
    def style_string(self) -> str:
        return PlottingStyles.bar_graph.value

    # Properties for convenient access to PlotDataItem.opts

    @property
    def brush(self) -> QBrush:
        """Grant easier access to BarGraphItem's pen"""
        self._prepare_pens_in_opts()
        return self.opts.get("brush")

    @property
    def pen(self) -> QPen:
        """Grant easier access to BarGraphItem's pen"""
        self._prepare_pens_in_opts()
        return self.opts.get("pen")

    def _prepare_pens_in_opts(self) -> None:
        """
        Despite having access to mkPen() which returns QPens, BarGraphItem's
        pen and symbolPen are initialized with (R,G,B) tuples instead of
        QPen's. This functions tries to transform all pens of the BarGraphItem
        to QPens to have consistent types and access to QPen functionality.
        """
        potential_pen = self.opts.get("pen")
        potential_brush = self.opts.get("brush")
        if not isinstance(potential_pen, QPen):
            self.opts["pen"] = pg.mkPen(potential_pen)
        if not isinstance(potential_brush, QBrush):
            self.opts["brush"] = pg.mkBrush(potential_brush)

    # Overwritten getters and setters for properties

    @property
    def color_string(self) -> str:
        color: Optional[QColor] = self.color
        if color is not None:
            return str(utilities.colors.svg_color_from_hex(
                color.name(),
                hex_on_fail=True
            ))
        return ""

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
            self.setOpts(  # type: ignore[attr-defined]
                brush=pg.mkBrush(new_color),
                pen=None,
            )

    @property
    def line_width(self) -> int:
        return self._fixed_bar_width

    @line_width.setter
    def line_width(self, line_width: int) -> None:
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
        ColumnNames.channel.value,
        ColumnNames.label.value,
        ColumnNames.color.value,
        ColumnNames.line_width.value,
        ColumnNames.layer.value,
        ColumnNames.style.value,
    ]

    def __init__(self):
        CItemPropertiesBase.__init__(self)
        if not isinstance(self, accgraph.LiveInjectionBarGraphItem):
            LOGGER.warning(
                f"{CInjectionBarGraphPropertiesBase.__name__} implementation relies "
                f"on attributes provided by {accgraph.LiveInjectionBarGraphItem.__name__}. "
                f"Use {CInjectionBarGraphPropertiesBase.__name__} only as base class "
                f"of classes derived from {accgraph.LiveInjectionBarGraphItem.__name__}.",
            )

    @property
    def style_string(self) -> str:
        return PlottingStyles.injection_bar_graph.value

    # Properties for convenient access to PlotDataItem.opts

    @property
    def pen(self) -> QPen:
        """Grant easier access to ErrorBarItem's pen"""
        self._prepare_pens_in_opts()
        return self.opts["pen"]

    def _prepare_pens_in_opts(self) -> None:
        """
        Despite having access to mkPen() which returns QPens, ErrorBarItem's
        pen and symbolPen are initialized with (R,G,B) tuples instead of
        QPen's. This functions tries to transform all pens of the ErrorBarItem
        to QPens to have consistent types and access to QPen functionality.
        """
        potential_pen = self.opts.get("pen")
        potential_symbol_pen = self.opts.get("symbolPen")
        if not isinstance(potential_pen, QPen):
            self.opts["pen"] = pg.mkPen(potential_pen)
        if not isinstance(potential_symbol_pen, QPen):
            self.opts["symbolPen"] = pg.mkPen(potential_symbol_pen)

    # Functions implemented from superclass

    @property
    def color_string(self) -> str:
        return str(utilities.colors.svg_color_from_hex(
            self.color.name(), hex_on_fail=True
        ))

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
    def line_width(self) -> int:
        return self.pen.width()

    @line_width.setter
    def line_width(self, line_width: int) -> None:
        self.pen.setWidth(int(line_width))


class CTimestampMarkerPropertiesBase(CItemPropertiesBase):

    """
    Base class for different timestamp marker properties. This
    classes uses attributes of the LiveTimestampMarker and should
    only be used as a base class in classes derived from
    LiveTimestampMarker.
    """

    plotting_item_editor_supported_columns: List[str] = [
        ColumnNames.channel.value,
        ColumnNames.label.value,
        ColumnNames.line_style.value,
        ColumnNames.layer.value,
        ColumnNames.style.value,
    ]

    def __init__(self):
        CItemPropertiesBase.__init__(self)
        if not isinstance(self, accgraph.LiveTimestampMarker):
            LOGGER.warning(
                f"{CTimestampMarkerPropertiesBase.__name__} implementation relies "
                f"on attributes provided by {accgraph.LiveTimestampMarker.__name__}. "
                f"Use {CTimestampMarkerPropertiesBase.__name__} only as base class "
                f"of classes derived from {accgraph.LiveTimestampMarker.__name__}.",
            )

    @property
    def style_string(self) -> str:
        return PlottingStyles.timestamp_markers.value

    # Functions implemented from superclass

    @property
    def line_width(self) -> int:
        return self.opts.get("pen_width", 0)

    @line_width.setter
    def line_width(self, line_width: int) -> None:
        self.opts["pen_width"] = line_width


# ~~~~~~~~~~~~~~~~~~~~~~ Scrolling Plotting Items ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class CScrollingCurve(
        accgraph.ScrollingPlotCurve,
        CCurvePropertiesBase,
):

    """
    Scrolling curve for a scrolling plot widget that
    receives its data through a PyDMChannel.
    """

    def __init__(
            self,
            plot_item: accgraph.ExPlotItem,
            data_source: accgraph.UpdateSource,
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
            data_source: source the item receives data from
            buffer_size: buffer size for the items data model
            color: color for the item
            line_width: thickness of the lines of the item
            line_style: style of the lines of them item
            kwargs: further keyword arguments for the base class
        """
        accgraph.ScrollingPlotCurve.__init__(
            self,
            plot_item=plot_item,
            data_source=data_source,
            buffer_size=buffer_size,
            pen=color,
            lineWidth=line_width,
            lineStyle=line_style,
            **kwargs,
        )
        self.data_source: Optional[PyDMChannelDataSource] = data_source
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
    receives its data through a PyDMChannel.
    """

    def __init__(
            self,
            plot_item: accgraph.ExPlotItem,
            data_source: accgraph.UpdateSource,
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
            data_source: source the item receives data from
            buffer_size: buffer size for the items data model
            color: color for the item
            line_width: thickness of the lines of the item
            line_style: will have no visual effect, this parameter
                        exists just for saving it between different
                        plotting items to not loose it
            kwargs: further keyword arguments for the base class
        """
        if line_width is not None:
            kwargs["width"] = line_width
        accgraph.ScrollingBarGraphItem.__init__(
            self,
            plot_item=plot_item,
            data_source=data_source,
            buffer_size=buffer_size,
            **kwargs,
        )
        self.data_source: Optional[PyDMChannelDataSource] = data_source
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
    that receives its data through a PyDMChannel.
    """

    def __init__(
            self,
            plot_item: accgraph.ExPlotItem,
            data_source: accgraph.UpdateSource,
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
            data_source: source the item receives data from
            buffer_size: buffer size for the items data model
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
            data_source=data_source,
            buffer_size=buffer_size,
            **kwargs,
        )
        self.data_source: Optional[PyDMChannelDataSource] = data_source
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
    receives its data through a PyDMChannel.
    """

    def __init__(
            self,
            plot_item: accgraph.ExPlotItem,
            data_source: accgraph.UpdateSource,
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
            data_source: source the item receives data from
            buffer_size: buffer size for the items data model
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
            data_source=data_source,
            buffer_size=buffer_size,
            **kwargs,
        )
        self.data_source: Optional[PyDMChannelDataSource] = data_source
        CTimestampMarkerPropertiesBase.__init__(self)
        CTimestampMarkerPropertiesBase.initialize_style_properties(
            self,
            color=color,
            line_style=line_style,
            line_width=line_width,
        )


class CScrollingPlot(CPlotWidgetBase, accgraph.ScrollingPlotWidget):

    """
    Plot widget for displaying scrolling curves,
    bar graphs and other plotting items.
    """

    ITEM_TYPES: OrderedDict = OrderedDict([
        (PlottingStyles.line_graph.value, CScrollingCurve),
        (PlottingStyles.bar_graph.value, CScrollingBarGraph),
        (PlottingStyles.injection_bar_graph.value, CScrollingInjectionBarGraph),
        (PlottingStyles.timestamp_markers.value, CScrollingTimestampMarker),
    ])

    def __init__(
            self,
            parent: QWidget = None,
            background: str = "default",
            config: accgraph.ExPlotWidgetConfig = accgraph.ExPlotWidgetConfig(),
            axis_items: Optional[Dict[str, pg.AxisItem]] = None,
            timing_source: Optional[accgraph.UpdateSource] = None,
            **plotitem_kwargs,
    ):
        accgraph.ScrollingPlotWidget.__init__(
            self,
            parent=parent,
            background=background,
            config=config,
            axis_items=axis_items,
            timing_source=timing_source,
            **plotitem_kwargs,
        )
        CPlotWidgetBase.__init__(self)


# ~~~~~~~~~~~~~~~~~~~~~~ Sliding Plotting Items ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CSlidingCurve(accgraph.SlidingPointerPlotCurve, CCurvePropertiesBase):

    """
    Sliding curve for a sliding pointer plot widget that
    receives its data through a PyDMChannel.
    """

    def __init__(
            self,
            plot_item: accgraph.ExPlotItem,
            data_source: accgraph.UpdateSource,
            buffer_size: int = accgraph.DEFAULT_BUFFER_SIZE,
            color: Optional[str] = None,
            line_width: Optional[int] = None,
            line_style: Optional[int] = None,
            **kwargs,
    ):
        """
        Create new sliding curve for a sliding plot.

        Args:
            plot_item: plot item that the item will be added to
            data_source: source the item receives data from
            buffer_size: buffer size for the items data model
            color: color for the item
            line_width: thickness of the lines of the item
            line_style: style of the lines of them item
            kwargs: further keyword arguments for the base class
        """
        accgraph.SlidingPointerPlotCurve.__init__(
            self,
            plot_item=plot_item,
            data_source=data_source,
            buffer_size=buffer_size,
            pen=color,
            lineWidth=line_width,
            lineStyle=line_style,
            **kwargs,
        )
        self.data_source: Optional[PyDMChannelDataSource] = data_source
        CCurvePropertiesBase.__init__(self)
        CCurvePropertiesBase.initialize_style_properties(
            self,
            color=color,
            line_style=line_style,
            line_width=line_width,
        )


class CSlidingPlot(CPlotWidgetBase, accgraph.SlidingPlotWidget):

    """Plot widget for displaying sliding curves."""

    ITEM_TYPES: OrderedDict = OrderedDict([
        (PlottingStyles.line_graph.value, CSlidingCurve),
        (PlottingStyles.bar_graph.value, None),
        (PlottingStyles.injection_bar_graph.value, None),
        (PlottingStyles.timestamp_markers.value, None),
    ])

    def __init__(
            self,
            parent: QWidget = None,
            background: str = "default",
            config: accgraph.ExPlotWidgetConfig = accgraph.ExPlotWidgetConfig(),
            axis_items: Optional[Dict[str, pg.AxisItem]] = None,
            timing_source: Optional[accgraph.UpdateSource] = None,
            **plotitem_kwargs,
    ):
        accgraph.SlidingPlotWidget.__init__(
            self,
            parent=parent,
            background=background,
            config=config,
            axis_items=axis_items,
            timing_source=timing_source,
            **plotitem_kwargs,
        )
        CPlotWidgetBase.__init__(self)


# ~~~~~~~~~~~~~~~~~~ Curve Editor Dialog and Table Model ~~~~~~~~~~~~~~~~~~~~~~


class CPlottingItemModel(BasePlotCurvesModel):

    """
    Data model for the table used in the CPlottingItemEditorDialog.
    The model is based on a plot widget. Each item in the plot will
    be represented as a row in the model.
    """

    def __init__(self, plot_widget: CPlotWidgetBase, parent: Optional[QObject] = None):
        """
        Create a new data model based on the passed plot widget
        for the curve editor dialogs table.

        Args:
            plot_widget: plot widget the data model is based on
            parent: parent item for the data model
        """
        super().__init__(plot_widget, parent=parent)
        self._column_names = [e.value for e in ColumnNames]

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        """
        Read data from the plotting item the table row is based on.
        What data is returned is defined by the column in the table.

        Args:
            index: position on which the data is stored in the
                   data model
            role: role under which the data is stored
        """
        try:
            return super().data(index, role)
        except (AttributeError, KeyError):
            return QVariant()

    def flags(self, index: QModelIndex) -> int:
        """
        Since not all plotting items support every stylistic parameter,
        we want to show this visually by greying out the unsupported
        cells in the table.

        Args:
            index: Index of the cell which flag should be looked up

        Returns:
            Flag, if cell should be editable or greyed out.
        """
        column_name = self._column_names[index.column()]
        curve: CItemPropertiesBase = self.plot._curves[index.row()]
        flags: int = Qt.ItemIsSelectable
        # Colors are enabled but handled by the color dialog, so we have
        # to keep it disabled for editing.
        if column_name in curve.plotting_item_editor_supported_columns:
            flags = flags | Qt.ItemIsEnabled
            if column_name != ColumnNames.color.value:
                flags = flags | Qt.ItemIsEditable
        return flags

    def get_data(
            self,
            column_name: str,
            item: CItemPropertiesBase,
    ) -> Union[QVariant, str, int, None]:
        """
        Get data from one of the plotting items of the plot the data
        model is based on, that should be displayed in a column by the
        column name. Each column name corresponds to an property
        in the plotting item.

        Args:
            column_name: column name displayed in the tables header
            item: item the row in the table model is based on

        Return:
            Value from the curve for the table cell
        """
        if column_name == ColumnNames.channel.value:
            return item.address or QVariant()
        if column_name == ColumnNames.label.value:
            return item.label or QVariant()
        if column_name == ColumnNames.color.value:
            return item.color_string
        if column_name == ColumnNames.line_style.value:
            return self.name_for_line[item.line_style]
        if column_name == ColumnNames.line_width.value:
            return int(item.line_width)
        if column_name == ColumnNames.symbol.value:
            return self.name_for_symbol[item.symbol]
        if column_name == ColumnNames.symbol_size.value:
            return int(item.symbol_size)
        if column_name == ColumnNames.layer.value:
            return str(item.layer)
        if column_name == ColumnNames.style.value:
            return str(item.style_string)
        return QVariant()

    def setData(
            self,
            index: QModelIndex,
            value: Union[str, int],
            role: int = Qt.EditRole,
    ) -> bool:
        """
        Take the values inserted into the table and set the plotting
        items style properties according to these values.

        Args:
            index: index in the table model where the data came from
            value: new value that should be set to the table model
            role: Describes the role of the item in the model, for more
                  information, look up Qt::ItemDataRole

        Returns:
            True if the data could be set
        """
        if not index.isValid():
            return False
        if index.row() >= self.rowCount():
            return False
        if index.column() >= self.columnCount():
            return False
        column_name = self._column_names[index.column()]
        item: CItemPropertiesBase = self.plot._curves[index.row()]
        if role == Qt.EditRole:
            if isinstance(value, QVariant):
                value = value.toString()
            if column_name == ColumnNames.layer.value:
                return self._change_item_layer(
                    item=item,
                    layer_identifier=cast(str, value),
                )
            if column_name == ColumnNames.style.value:
                return self._change_item_style(
                    item=item,
                    style=cast(str, value),
                )
            if not self.set_data(
                    column_name,
                    cast(CCurvePropertiesBase, item),
                    cast(str, value),
            ):
                return False
        else:
            return False
        self.dataChanged.emit(index, index)
        return True

    def _change_item_layer(self, item: CItemPropertiesBase, layer_identifier: str) -> bool:
        """
        Move the passed item to a new layer and remove it from the old one.

        Args:
            item: plotting item which should be moved to a different layer
            layer_identifier: identifier of the items new layer

        Returns:
            True if the item is now in the passed layer
        """
        try:
            new_layer: accgraph.PlotItemLayer = self.plot.get_layer_by_identifier(layer_identifier)
            old_layer: accgraph.PlotItemLayer = self.plot.get_layer_by_identifier(item.layer)
            if new_layer is not old_layer:
                old_layer.view_box.removeItem(item)
                self.plot.addItem(item=item, layer=new_layer)
            return True
        except KeyError:
            # No layer with the identifier specified in the table could be found
            return False

    def _change_item_style(self, item: CItemPropertiesBase, style: str) -> bool:
        """
        Change the style of the item, f.e. from a line graph to a bar graph.
        This is achieved by creating a new item taking the information from
        the old one, setting it to the new one and replacing the old one with it.

        Args:
            item: old item that is replaced by a new one fitting to the style
            style: string representation of what plotting item should be added
                   ( see enum PlottingStyles for possible values )

        Returns:
            True, if a item fitting to the passed style with the old items look
            could be created
        """
        try:
            if style != item.style_string:
                self.plot.get_layer_by_identifier(item.layer).view_box.removeItem(item)
                self.append(
                    style=style,
                    address=item.address,
                    name=item.label,
                    color=item.color,
                    line_style=item.line_style,
                    line_width=item.line_width,
                    symbol=item.symbol,
                    symbol_size=item.symbol_size,
                    layer=item.layer,
                    index=self.plot._items.index(item),
                )
            return True
        except KeyError:
            LOGGER.warning(
                f"Item of type {type(item).__name__} could not replaced with a new "
                f"{style}, since removing it from the plot failed. Check if layer "
                f"{item.layer} does exist in your plot."
            )
            return False

    def set_data(
            self,
            column_name: str,
            item: CCurvePropertiesBase,
            value: str,
    ) -> bool:
        """
        Set data in one of the plotting items of the plot widget this data model
        is based on from the provided values and column names. Each column name
        corresponds to an property in the item.

        Args:
            column_name:   name of the column that value is coming from
            item: item that is represented by the row of in which the
                  cell is placed
            value: value from the table's cell

        Returns:
            True if the data could be set successfully
        """
        if column_name == ColumnNames.channel.value:
            item.address = value
        elif column_name == ColumnNames.label.value:
            item.label = str(value)
        elif column_name == ColumnNames.color.value:
            item.color = value
        elif column_name == ColumnNames.line_style.value:
            item.line_style = int(value)
        elif column_name == ColumnNames.line_width.value:
            item.line_width = int(value)
        elif column_name == ColumnNames.symbol.value:
            if value is None:
                item.symbol = None
            else:
                item.symbol = str(value)
        elif column_name == ColumnNames.symbol_size.value:
            item.symbol_size = int(value)
        else:
            return False
        return True

    def append(
            self,
            style: str = PlottingStyles.line_graph.value,
            address: Optional[str] = None,
            name: Optional[str] = None,
            color: Optional[str] = None,
            line_style: Optional[int] = None,
            line_width: Optional[int] = None,
            symbol: Optional[str] = None,
            symbol_size: Optional[int] = None,
            layer: Optional[str] = None,
            index: Optional[int] = None,
    ) -> None:
        """
        Add a new plotting item to the plot. This item will be represented
        by a row in the curve editor dialog's table.

        Args:
            style: which kind of plotting item should be added (line graph,
                   bar graph, etc.)
            address: address the new curve should be receiving data from
            name: name of the new curve
            color: color of the new curve,
            line_style: style of the line that draws the item
            line_width: thickness of the line
            symbol: symbol for points in curves
            symbol_size: Size of the symbol for points in curves
            layer: layer in which the curve should be added
            index: index in the plot widgets curves array where to insert the curve
        """
        if index is None:
            self.beginInsertRows(
                QModelIndex(),
                len(self._plot.curves),
                len(self._plot.curves),
            )
        self._plot.add_channel_attached_item(
            style=style,
            channel_address=address,
            name=name,
            color=color,
            line_style=line_style,
            line_width=line_width,
            symbol=symbol,
            symbol_size=symbol_size,
            layer=layer,
            index=index,
        )
        if index is None:
            self.endInsertRows()

    def removeAtIndex(self, index: QModelIndex) -> None:
        """
        Remove an item from the plot widget. This will remove its
        corresponding row from the editor dialog's table as well.

        Args:
            index: row index of the item that should be removed
        """
        self.beginRemoveRows(QModelIndex(), index.row(), index.row())
        self._plot.remove_channel_attached_item_at_index(index.row())
        self.endRemoveRows()


class PlottingItemStyleColumnDelegate(QStyledItemDelegate):

    """
    PlottingItemStyleColumnDelegate draws a QComboBox in the Item Style column, so that users
    can pick the item style (line, bar graph, timestamp marker etc.) they want to display from
    a list, instead of having to type in strings by hand.
    """

    def createEditor(
            self,
            parent: QWidget,
            option: QStyleOptionViewItem,
            index: QModelIndex,
    ) -> QWidget:
        """
        Set the combobox text from the table item's model.
        This overrides QStyledItemDelegate base method.

        Args:
            parent: parent widget
            option: style option that controls how the editor
                    appears
            index: Position of the editor in the table

        Returns:
            The created editor widget
        """
        editor = QComboBox(parent)
        model_plot: CPlotWidgetBase = index.model().plot
        filtered_item_types: Dict = {
            style: item_type for style, item_type in model_plot.ITEM_TYPES.items()
            if item_type is not None
        }
        editor.addItems(list(filtered_item_types.keys()))
        return editor

    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        """
        Set the combobox text from the table item's model.
        This overrides QStyledItemDelegate base method.

        Args:
            editor: Editor which text should be set by the model
            index: Position of the editor in the table
        """
        val = str(index.model().data(index, Qt.EditRole))
        editor.setCurrentText(val)

    def setModelData(
            self,
            editor: QWidget,
            model: QAbstractTableModel,
            index: QModelIndex,
    ) -> None:
        """
        Sets the data to be displayed and edited by the editor from the
        data model item specified by the model index.
        This overrides QStyledItemDelegate base method.

        Args:
            editor: Editor the data was entered in
            model: Model the data should be saved in
            index: Position where the editor was located in the table
        """
        model.setData(index, editor.currentText(), Qt.EditRole)

    def updateEditorGeometry(
            self,
            editor: QWidget,
            option: QStyleOptionViewItem,
            index: QModelIndex,
    ) -> None:
        """
        Updates the editor for the item specified by index according to the
        style option given.
        This overrides QStyledItemDelegate base method.

        Args:
            editor: Editor that is updated
            option: style option for the editor
            index: position of the editor
        """
        editor.setGeometry(option.rect)


class CPlottingItemEditorDialog(BasePlotCurveEditorDialog):
    """
    CPlottingItemEditorDialog is a QDialog that is used in Qt Designer
    to edit the properties of the plotting item in a plot. This dialog is
    shown when you double-click the plot, or when you right click it and
    choose 'Edit Plotting Items...'.

    This thing is mostly just a wrapper for a table view, with a couple
    buttons to add and remove items, and a button to save the changes.
    """
    TABLE_MODEL_CLASS = CPlottingItemModel

    def __init__(self, plot: CPlotWidgetBase, parent: QWidget = None):
        """
        Create a new editor dialog for editing the items contained
        in the passed plot.

        Args:
            plot: plot which's content the table is representing
            parent: parent widget for the dialog
        """
        super().__init__(plot, parent)
        self.setup_delegate_columns(index=2)
        self.resize(960, 300)
        # You can add not only curves, but also other items
        self.add_button.setText("Add Item")
        self.remove_button.setText("Remove Item")
        self.setWindowTitle("Plotting Item Editor")

    def setup_delegate_columns(self, index: int = 2) -> None:
        """
        Create different delegates plotting item editor's table. These will add
        f.e. a color editor dialog in the color column.

        Args:
            index: start index from which the delegates are positioned relatively
        """
        super().setup_delegate_columns(index=2)
        symbol_delegate = PlottingItemStyleColumnDelegate(self)
        self.table_view.setItemDelegateForColumn(index + 6, symbol_delegate)


class CPlottingItemEditorExtension(BasePlotExtension):
    """
    PyDM Extension based on the CPlottingItemEditorDialog.
    """
    def __init__(self, widget: accgraph.ExPlotWidget):
        """
        Create a new extension for editing items in a plot
        through an extra dialog containing a table.

        Args:
            widget: plot the extension is added to
        """
        super().__init__(widget, CPlottingItemEditorDialog)
        self.edit_curves_action.setText("Edit Plotting Items...")


# TODO: Make available when proven useful
# class CImageView(WidgetRulesMixin, CustomizedTooltipMixin, HideUnusedFeaturesMixin, PyDMImageView):
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
#         WidgetRulesMixin.__init__(self)
#         CustomizedTooltipMixin.__init__(self)
#         HideUnusedFeaturesMixin.__init__(self)
#         PyDMImageView.__init__(self, parent=parent, image_channel=image_channel, width_channel=width_channel, **kwargs)
#
#     def default_rule_channel(self) -> str:
#         return self.imageChannel