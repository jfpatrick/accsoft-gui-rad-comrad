import json
from dataclasses import dataclass
from typing import Any, Dict, Optional
from qtpy.QtWidgets import QHeaderView, QAction
from qtpy.QtCore import QModelIndex, QObject, Signal
from accwidgets.qt import AbstractTableDialog, ColorPropertyColumnDelegate, AbstractTableModel
from accwidgets._designer_base import get_designer_cursor, WidgetsTaskMenuExtension
from comrad import CLed


@dataclass
class CLedColorMapDialogEditorRow:
    color: str
    value: int


class CLedColorMapModel(AbstractTableModel):

    def columnCount(self, *_):
        return 2

    def create_row(self) -> CLedColorMapDialogEditorRow:
        return CLedColorMapDialogEditorRow(color=CLed.Status.color_for_status(CLed.Status.OFF).name(),
                                           value=0)

    def column_name(self, section: int) -> str:
        return 'Value' if section == 0 else 'Color'

    def get_cell_data(self, index: QModelIndex, row: CLedColorMapDialogEditorRow) -> Any:
        if index.column() == 0:
            return row.value
        return row.color

    def set_cell_data(self, index: QModelIndex, row: CLedColorMapDialogEditorRow, value: Any) -> bool:
        if index.column() == 0:
            row.value = value
        else:
            row.color = value
        return True

    def validate(self):
        used_codes = set()
        for item in self._data:
            if item.value in used_codes:
                raise ValueError(f'Value "{item.value}" is being used more than once.')
            used_codes.add(item.value)


class CLedColorMapDialog(AbstractTableDialog[CLedColorMapDialogEditorRow, CLedColorMapModel]):

    map_changed = Signal(dict)

    def __init__(self,
                 table_model: CLedColorMapModel,
                 parent: Optional[QObject] = None):
        """
        Dialog that is used in Qt Designer to edit the color map of the :class:`CLed` widget.

        Args:
            table_model: Table model object.
            on_save: Callback to propagate the values back.
            parent: Parent item for the dialog.
        """
        super().__init__(table_model=table_model, parent=parent)
        self.setWindowTitle('Edit Color Map')
        self.table.setItemDelegateForColumn(1, ColorPropertyColumnDelegate(self.table))
        self.table.set_persistent_editor_for_column(0)
        self.table.set_persistent_editor_for_column(1)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.resize(600, 300)

    def on_save(self):
        self.map_changed.emit({str(item.value): item.color for item in self._table_model.raw_data})


class CLedColorMapDialogExtension(WidgetsTaskMenuExtension):

    def __init__(self, widget: CLed):
        """
        Task-menu extension based on the :class:`CLedColorMapDialog`.

        Args:
            widget: Widget to apply the extension to.
        """
        super().__init__(widget)
        self.widget = widget
        self._action = QAction('Edit Color Map...', widget)
        self._action.triggered.connect(self._edit)

    def _edit(self):
        data = [CLedColorMapDialogEditorRow(value=val, color=color.name())
                for val, color in CLed._unpack_designer_color_map(self.widget.color_map).items()]
        model = CLedColorMapModel(data=data, parent=self.widget)
        dialog = CLedColorMapDialog(table_model=model, parent=self.widget)
        dialog.map_changed.connect(self._on_items_updated)
        dialog.exec_()

    def _on_items_updated(self, new_items: Dict[str, str]):
        cursor = get_designer_cursor(self.widget)
        if cursor:
            cursor.setProperty('color_map', json.dumps(new_items))

    def actions(self):
        return [self._action]
