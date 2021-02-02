import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Callable
from qtpy.QtCore import QModelIndex, QObject
from qtpy.QtWidgets import QComboBox, QAction, QHeaderView
from accwidgets import designer_check
from accwidgets.log_console import LogLevel
from accwidgets.qt import AbstractTableDialog, AbstractTableModel, AbstractComboBoxColumnDelegate
from accwidgets._designer_base import get_designer_cursor, WidgetsTaskMenuExtension
from comrad import CLogConsole


# Set accwidgets flag so that it does not throw warnings because it has a different way to detect
# Qt Designer than PyDM.
designer_check.set_designer()


@dataclass
class CLogConsoleLoggersEditorRow:
    logger_name: str
    logger_level: LogLevel


class CLogConsoleLoggersEditorModel(AbstractTableModel):

    def columnCount(self, *_):
        return 2

    def create_row(self) -> CLogConsoleLoggersEditorRow:
        return CLogConsoleLoggersEditorRow(logger_name='', logger_level=LogLevel.NOTSET)

    def column_name(self, section: int) -> str:
        return 'Logger' if section == 0 else 'Level'

    def get_cell_data(self, index: QModelIndex, row: CLogConsoleLoggersEditorRow) -> Any:
        if index.column() == 0:
            return row.logger_name
        return row.logger_level.value

    def set_cell_data(self, index: QModelIndex, row: CLogConsoleLoggersEditorRow, value: Any) -> bool:
        if index.column() == 0:
            row.logger_name = value
        else:
            row.logger_level = LogLevel(value)
        return True


class LogLevelComboBoxDelegate(AbstractComboBoxColumnDelegate):

    def configure_editor(self, editor: QComboBox, _):
        for level in LogLevel:
            editor.addItem(LogLevel.level_name(level), level.value)


class CLogConsoleLoggersEditorDialog(AbstractTableDialog[CLogConsoleLoggersEditorRow, CLogConsoleLoggersEditorModel]):

    def __init__(self,
                 table_model: CLogConsoleLoggersEditorModel,
                 on_save: Callable[[Dict[str, LogLevel]], None],
                 parent: Optional[QObject] = None):
        """
        Dialog that is used in Qt Designer to edit the predefined logger levels of the :class:`CLogConsole` widget.

        Args:
            table_model: Table model object.
            parent: Parent item for the dialog.
        """
        super().__init__(table_model=table_model, parent=parent)
        self.setWindowTitle('Edit Logger Levels')
        self.table.setItemDelegateForColumn(1, LogLevelComboBoxDelegate(self.table))
        self.table.set_persistent_editor_for_column(0)
        self.table.set_persistent_editor_for_column(1)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.resize(600, 300)
        self._on_save = on_save

    def on_save(self):
        json_data = {item.logger_name: item.logger_level.value for item in self._table_model.raw_data}
        self._on_save(json_data)


class CLogConsoleLoggersEditorExtension(WidgetsTaskMenuExtension):

    def __init__(self, widget: CLogConsole):
        """
        Task-menu extension based on the :class:`CLogConsoleLoggersEditorDialog`.

        Args:
            widget: Widget to apply the extension to.
        """
        super().__init__(widget)
        self.widget = widget
        self._action = QAction('Edit Logger Levels...', widget)
        self._action.triggered.connect(self._edit)

    def _edit(self):
        data = [CLogConsoleLoggersEditorRow(logger_name=name, logger_level=level)
                for name, level in CLogConsole._unpack_designer_levels(self.widget.loggers).items()]
        model = CLogConsoleLoggersEditorModel(data=data, parent=self.widget)
        dialog = CLogConsoleLoggersEditorDialog(table_model=model,
                                                on_save=self._on_items_updated,
                                                parent=self.widget)
        dialog.exec_()

    def _on_items_updated(self, new_items: Dict[str, LogLevel]):
        cursor = get_designer_cursor(self.widget)
        if cursor:
            cursor.setProperty('loggers', json.dumps(new_items))

    def actions(self):
        return [self._action]
