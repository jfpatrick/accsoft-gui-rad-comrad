import logging
from typing import Optional, Union, cast, Dict
from qtpy.QtWidgets import QWidget, QStyledItemDelegate, QComboBox, QStyleOptionViewItem
from qtpy.QtCore import QObject, QModelIndex, QVariant, QAbstractTableModel, Qt
from pydm.widgets.baseplot_curve_editor import BasePlotCurvesModel, BasePlotCurveEditorDialog
from pydm.widgets.qtplugin_extensions import BasePlotExtension
from accwidgets.graph import PlotItemLayer, ExPlotWidget, designer_check as accgraph_designer_check
from accwidgets.graph.designer.designer_extensions import PlotLayerExtension
from comrad.widgets.graphs import (CPlotWidgetBase, ColumnNames, CItemPropertiesBase, CCurvePropertiesBase,
                                   PlottingItemTypes)


logger = logging.getLogger(__name__)


# Set accwidgets flag so that it does not throw warnings because it has a different way to detect
# Qt Designer than PyDM.
accgraph_designer_check.set_designer()


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
            if column_name != ColumnNames.COLOR.value:
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
        if column_name == ColumnNames.CHANNEL.value:
            return item.address or QVariant()
        if column_name == ColumnNames.LABEL.value:
            return item.label or QVariant()
        if column_name == ColumnNames.COLOR.value:
            return item.color_string
        if column_name == ColumnNames.LINE_STYLE.value:
            return self.name_for_line[item.line_style]
        if column_name == ColumnNames.LINE_WIDTH.value:
            return int(item.line_width)
        if column_name == ColumnNames.SYMBOL.value:
            return self.name_for_symbol[item.symbol]
        if column_name == ColumnNames.SYMBOL_SIZE.value:
            return int(item.symbol_size)
        if column_name == ColumnNames.LAYER.value:
            return str(item.layer)
        if column_name == ColumnNames.STYLE.value:
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
            if column_name == ColumnNames.LAYER.value:
                return self._change_item_layer(
                    item=item,
                    layer_identifier=cast(str, value),
                )
            if column_name == ColumnNames.STYLE.value:
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
            new_layer: PlotItemLayer = self.plot.layer(layer_identifier)
            old_layer: PlotItemLayer = self.plot.layer(item.layer)
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
                self.plot.removeItem(item)
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
            logger.warning(f'Item of type {type(item).__name__} could not replaced with a new '
                           f'{style}, since removing it from the plot failed. Check if layer '
                           f'{item.layer} does exist in your plot.')
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
        if column_name == ColumnNames.CHANNEL.value:
            item.address = value
        elif column_name == ColumnNames.LABEL.value:
            item.label = str(value)
        elif column_name == ColumnNames.COLOR.value:
            item.color = value
        elif column_name == ColumnNames.LINE_STYLE.value:
            item.line_style = int(value)
        elif column_name == ColumnNames.LINE_WIDTH.value:
            item.line_width = int(value)
        elif column_name == ColumnNames.SYMBOL.value:
            if value is None:
                item.symbol = None
            else:
                item.symbol = str(value)
        elif column_name == ColumnNames.SYMBOL_SIZE.value:
            item.symbol_size = int(value)
        else:
            return False
        return True

    def append(
            self,
            style: str = PlottingItemTypes.LINE_GRAPH.value,
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
        self.add_button.setText('Add Item')
        self.remove_button.setText('Remove Item')
        self.setWindowTitle('Plotting Item Editor')

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
    def __init__(self, widget: ExPlotWidget):
        """
        Create a new extension for editing items in a plot
        through an extra dialog containing a table.

        Args:
            widget: plot the extension is added to
        """
        super().__init__(widget, CPlottingItemEditorDialog)
        self.edit_curves_action.setText('Edit Plotting Items...')


class CLayerEditorExtension(PlotLayerExtension):

    """
    Non PYDM Extension for editing layers of the Plot.
    This Extension is already part of the widgets library
    and can be simply taken without any changes.
    """

    pass
