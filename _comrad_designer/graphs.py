import json
from dataclasses import dataclass
from typing import Optional, cast, Dict, Any, List, Type, Callable
from qtpy.QtWidgets import QComboBox, QAction, QHeaderView, QWidget, QStyledItemDelegate, QStyleOptionViewItem
from qtpy.QtCore import QObject, QModelIndex, Qt, QPersistentModelIndex, QAbstractTableModel, QLocale, QSignalBlocker
from qtpy.QtGui import QColor, QPalette
from pydm.widgets.baseplot_curve_editor import BasePlotCurveItem as PyDMBasePlotCurveItem
from accwidgets.qt import (AbstractTableDialog, AbstractTableModel, _STYLED_ITEM_DELEGATE_INDEX,
                           AbstractComboBoxColumnDelegate)
from accwidgets import designer_check
from accwidgets._designer_base import WidgetsTaskMenuExtension
from accwidgets.graph.designer.designer_extensions import PlotLayerExtension as _PlotLayerExtension, get_designer_cursor
from comrad.widgets.graphs import CPlotWidgetBase, ColumnNames, CItemPropertiesBase, PlottingItemTypes
from _comrad_designer.common import ColorPropertyColumnDelegate
from _comrad_designer.device_edit import DevicePropertyLineEdit


# Set accwidgets flag so that it does not throw warnings because it has a different way to detect
# Qt Designer than PyDM.
designer_check.set_designer()


@dataclass
class PlottingItemRow:
    """
    View model class for Plotting Item Editor table view.
    """
    color: QColor
    line_style: Qt.PenStyle
    line_width: float
    symbol_size: int
    item_style: str
    layer: Optional[str] = None
    symbol: Optional[str] = None
    channel: Optional[str] = None
    label: Optional[str] = None


_FORBIDDEN_COLUMNS = {
    PlottingItemTypes.BAR_GRAPH.value: [3, 5, 6],
    PlottingItemTypes.INJECTION_BAR_GRAPH.value: [3, 5, 6],
    PlottingItemTypes.TIMESTAMP_MARKERS.value: [2, 4, 5, 6],
}


class CPlottingItemModel(AbstractTableModel[PlottingItemRow]):

    def __init__(self, item_styles: List[str], data: List[PlottingItemRow], parent: Optional[QObject] = None):
        """
        Data model for the table used in the CPlottingItemEditorDialog.
        The model is based on a plot widget. Each item in the plot will
        be represented as a row in the model.

        Args:
            item_styles: Items styles that are available for a given plot widget.
            data: Initial data.
            parent: Owning object.
        """
        super().__init__(data=data, parent=parent)
        self.item_styles = item_styles

    def get_cell_data(self, index: QModelIndex, row: PlottingItemRow) -> Any:
        section = index.column()
        try:
            if section in _FORBIDDEN_COLUMNS[row.item_style]:
                return None
        except KeyError:
            pass

        if section == 0:
            return row.channel
        elif section == 1:
            return row.label
        elif section == 2:
            return row.color
        elif section == 3:
            return row.line_style
        elif section == 4:
            return row.line_width
        elif section == 5:
            return row.symbol
        elif section == 6:
            return row.symbol_size
        elif section == 7:
            return row.layer
        else:
            return row.item_style

    def set_cell_data(self, index: QModelIndex, row: PlottingItemRow, value: Any) -> bool:
        section = index.column()
        try:
            if section in _FORBIDDEN_COLUMNS[row.item_style]:
                return False
        except KeyError:
            pass

        if section == 0:
            row.channel = value
        elif section == 1:
            row.label = value
        elif section == 2:
            row.color = value
        elif section == 3:
            row.line_style = value
        elif section == 4:
            if float(value) < 0:
                return False
            row.line_width = value
        elif section == 5:
            row.symbol = value
        elif section == 6:
            if int(value) < 0:
                return False
            row.symbol_size = value
        elif section == 7:
            row.layer = value
        else:
            row.item_style = value
        return True

    def columnCount(self, *args, **kwargs):
        return 9

    def column_name(self, section: int) -> str:
        all_names = [e.value for e in ColumnNames]
        return all_names[section]

    def create_row(self) -> PlottingItemRow:
        next_color = CPlotWidgetBase._default_color(self.rowCount())
        return PlottingItemRow(color=next_color,
                               line_style=Qt.SolidLine,
                               line_width=1.0,
                               symbol_size=10,
                               item_style=PlottingItemTypes.LINE_GRAPH.value)

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """
        Since not all plotting items support every stylistic parameter,
        we want to show this visually by greying out the unsupported
        cells in the table.

        Args:
            index: Index of the cell which flag should be looked up

        Returns:
            Flag, if cell should be editable or greyed out.
        """
        item_type = index.siblingAtColumn(8).data()
        try:
            restricted_cols = _FORBIDDEN_COLUMNS[item_type]
        except KeyError:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable
        if index.column() in restricted_cols:
            return Qt.ItemIsSelectable
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def notify_change(self, start: QModelIndex, end: QModelIndex, action_type: AbstractTableModel.ChangeType):
        if action_type == self.ChangeType.UPDATE_ITEM and start.column() == 8:
            # Update all row, as some columns get disabled based on the item style
            super().notify_change(start=start.siblingAtColumn(0),
                                  end=end.siblingAtColumn(end.model().columnCount() - 1),
                                  action_type=action_type)
        else:
            super().notify_change(start=start, end=end, action_type=action_type)

    @property
    def json_data(self) -> List[Dict[str, Any]]:
        """
        Serialize into format fitting "curves" property, so that it can be parsed by :meth:`CPlotWidgetBase._set_items`.
        """
        res = []
        for item in self._data:
            d = [
                ('channel', item.channel),
                ('name', item.label or ''),
                ('color', item.color),
                ('line_style', item.line_style),
                ('line_width', item.line_width),
                ('symbol', item.symbol),
                ('symbol_size', item.symbol_size),
                ('layer', item.layer),
                ('style', item.item_style),
            ]
            try:
                restricted_cols = _FORBIDDEN_COLUMNS[item.item_style]
            except KeyError:
                restricted_cols = []
            for col in reversed(sorted(restricted_cols)):
                d.pop(col)
            res.append(dict(d))
        return res


class PlottingItemStyleColumnDelegate(AbstractComboBoxColumnDelegate):
    """
    Delegate that draws a QComboBox in the Item Style column, so that users
    can pick the item style (line, bar graph, timestamp marker etc.) they want to display from
    a list, instead of having to type in strings by hand.
    """
    def configure_editor(self, editor: QComboBox, model: CPlottingItemModel):
        for style in model.item_styles:
            editor.addItem(style, style)


class LineStyleColumnDelegate(AbstractComboBoxColumnDelegate):

    def configure_editor(self, editor: QComboBox, _):
        for name, val in PyDMBasePlotCurveItem.lines.items():
            editor.addItem(name, val)

    def displayText(self, _, __) -> str:
        # Make sure that transparent button does not expose set label underneath
        return ''


class SymbolStyleColumnDelegate(AbstractComboBoxColumnDelegate):

    def configure_editor(self, editor: QComboBox, _):
        for name, val in PyDMBasePlotCurveItem.symbols.items():
            editor.addItem(name, val)

    def displayText(self, _, __) -> str:
        # Make sure that transparent button does not expose set label underneath
        return ''


class ChannelColumnDelegate(QStyledItemDelegate):
    """
    Table delegate that draws :class:`DevicePropertyLineEdit` widget in the cell.
    """

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex) -> QWidget:
        editor = DevicePropertyLineEdit(parent)
        editor.address_changed.connect(self._val_changed)
        setattr(editor, _STYLED_ITEM_DELEGATE_INDEX, QPersistentModelIndex(index))
        return editor

    def setEditorData(self, editor: DevicePropertyLineEdit, index: QModelIndex):
        if not isinstance(editor, DevicePropertyLineEdit):
            return

        blocker = QSignalBlocker(editor)
        editor.address = index.data()
        blocker.unblock()

        if getattr(editor, _STYLED_ITEM_DELEGATE_INDEX, None) != index:
            setattr(editor, _STYLED_ITEM_DELEGATE_INDEX, QPersistentModelIndex(index))

    def setModelData(self, editor: DevicePropertyLineEdit, model: QAbstractTableModel, index: QModelIndex):
        if not isinstance(editor, DevicePropertyLineEdit):
            return
        index.model().setData(index, editor.address)

    def displayText(self, value: Any, locale: QLocale) -> str:
        # Make sure that transparent button does not expose set label underneath
        return ''

    def _val_changed(self):
        editor = self.sender()
        index: Optional[QPersistentModelIndex] = getattr(editor, _STYLED_ITEM_DELEGATE_INDEX, None)
        if index and index.isValid():
            self.setModelData(editor, index.model(), QModelIndex(index))


class CPlottingItemEditorDialog(AbstractTableDialog[PlottingItemRow, CPlottingItemModel]):

    def __init__(self,
                 table_model: CPlottingItemModel,
                 on_save: Callable[[List[Dict[str, Any]]], None],
                 parent: Optional[QObject] = None):
        """
        Dialog that is used in Qt Designer to edit the properties of the plotting item in
        a plot. This dialog is shown when you double-click the plot, or when you right click it and
        choose 'Edit Plotting Items...'.

        Args:
            table_model: Table model object.
            parent: Parent item for the dialog.
        """
        super().__init__(table_model=table_model, parent=parent)
        self.setWindowTitle('Plotting Item Editor')
        palette = self.table.palette()
        palette.setColor(QPalette.Highlight, palette.color(QPalette.Base))  # Do not make any highlighted background
        palette.setColor(QPalette.HighlightedText, palette.color(QPalette.Text))  # Do not leave text white (on white background)
        self.table.setPalette(palette)

        self.table.setItemDelegateForColumn(0, ChannelColumnDelegate(self.table))
        self.table.setItemDelegateForColumn(2, ColorPropertyColumnDelegate(self.table))
        self.table.setItemDelegateForColumn(3, LineStyleColumnDelegate(self.table))
        self.table.setItemDelegateForColumn(5, SymbolStyleColumnDelegate(self.table))
        self.table.setItemDelegateForColumn(8, PlottingItemStyleColumnDelegate(self.table))
        for i in [0, 1, 2, 3, 5, 7, 8]:  # Skipping spinbox columns here, as they annoyingly highlight contents by default
            self.table.set_persistent_editor_for_column(i)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.resizeSection(0, 200)
        self.resize(1200, 400)
        self._on_save = on_save

    def on_save(self):
        self._on_save(self._table_model.json_data)


class CPlottingItemEditorExtension(WidgetsTaskMenuExtension):

    def __init__(self, widget: CPlotWidgetBase):
        """
        Task-menu extension based on the :class:`CPlottingItemEditorDialog`.

        Args:
            widget: Widget to apply the extension to.
        """
        super().__init__(widget)
        self.widget = widget
        self._action = QAction('Edit Plotting Items...', widget)
        self._action.triggered.connect(self._edit)

    def _edit(self):
        def map_to_view_model(item: CItemPropertiesBase) -> PlottingItemRow:
            return PlottingItemRow(label=item.label,
                                   channel=item.address,
                                   color=item.color_string,
                                   line_style=item.line_style,
                                   line_width=float(item.line_width),
                                   symbol=item.symbol,
                                   symbol_size=item.symbol_size,
                                   layer=item.layer,
                                   item_style=item.style_string)

        data = list(map(map_to_view_model, self.widget._items_checked))
        model = CPlottingItemModel(item_styles=cast(Type[CPlotWidgetBase], type(self.widget)).ITEM_TYPES.keys(),
                                   data=data,
                                   parent=self.widget)
        CPlottingItemEditorDialog(table_model=model, on_save=self._on_items_updated, parent=self.widget).exec_()

    def _on_items_updated(self, new_items: List[Dict[str, Any]]):
        cursor = get_designer_cursor(self.widget)
        if cursor:
            cursor.setProperty('curves', [json.dumps(item) for item in new_items])

    def actions(self):
        return [self._action]


CLayerEditorExtension = _PlotLayerExtension
