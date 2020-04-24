from typing import Optional, Set, List
from qtpy.QtWidgets import QTableView, QWidget, QAbstractItemDelegate
from qtpy.QtCore import Qt, QModelIndex, QAbstractItemModel


class PersistentEditorTableView(QTableView):

    def __init__(self, parent: Optional[QWidget] = None):
        """
        :class:`QTableView` subclass that assumes always-editable mode for specified columns or rows.

        By default, :class:`QTableView` will allow editing content (and hence display editors) only when user clicks
        inside a cell. This works well for spreadsheet-like applications but falls short for complex editing scenarios,
        where user needs open editors at his fingertips. Even when using :class:`QStyledItemDelegate` subclasses, your
        editor will be opened by the table view only when focus in the cell. :class:`QTableWidget` offers always-editable
        workflow, where you can define any editor you want. However, it does not allow working with user-defined models.
        """
        super().__init__(parent)
        self._persistent_cols: Set[int] = set()
        self._persistent_rows: Set[int] = set()

    def setModel(self, model: QAbstractItemModel):
        """
        Sets the model for the view to present.

        This function will create and set a new selection model, replacing any model that was previously set with
        :meth:`QAbstractItemView.setSelectionModel`. However, the old selection model will not be deleted as it may
        be shared between several views. We recommend that you delete the old selection model if it is no longer
        required. If both the old model and the old selection model do not have parents, or if their parents are
        long-lived objects, it may be preferable to call their :meth:`QObject.deleteLater` functions to explicitly
        delete them.

        The view does not take ownership of the model unless it is the model's parent object because the model may
        be shared between many different views.

        Args:
            model: New model.
        """
        prev_model: QAbstractItemModel = self.model()
        model_changed = prev_model != model
        if model_changed:
            if prev_model:
                prev_model.dataChanged.disconnect(self._check_persistent_editors_for_data)
            if model:
                model.dataChanged.connect(self._check_persistent_editors_for_data)

        super().setModel(model)

        if model_changed:
            # This needs self.model() to be up to date
            self._update_all_persistent_editors()

    def setItemDelegate(self, delegate: QAbstractItemDelegate):
        """
        Sets the item delegate for this view and its model to delegate. This is useful if you want complete
        control over the editing and display of items.

        Any existing delegate will be removed, but not deleted. :class:`QAbstractItemView` does not take ownership
        of delegate.

        **Warning:** You should not share the same instance of a delegate between views. Doing so can cause
        incorrect or unintuitive editing behavior since each view connected to a given delegate may receive the
        :meth:`QAbstractItemDelegate.closeEditor` signal, and attempt to access, modify or close an editor that
        has already been closed.

        Args:
            delegate: New delegate
        """
        super().setItemDelegate(delegate)
        # Reset editorHash amongst other things, so that previously created editors of different types
        # (due to different delegate) are removed and allow creating new ones
        self.reset()

        self._update_all_persistent_editors()

    def setItemDelegateForColumn(self, column: int, delegate: QAbstractItemDelegate):
        """
        Sets the given item delegate used by this view and model for the given column. All items on column will be
        drawn and managed by delegate instead of using the default delegate (i.e.,
        :meth:`QAbstractItemView.itemDelegate`).

        Any existing column delegate for column will be removed, but not deleted. :class:`QAbstractItemView` does not
        take ownership of delegate.

        **Note:** If a delegate has been assigned to both a row and a column, the row delegate will take precedence
        and manage the intersecting cell index.

        **Warning:** You should not share the same instance of a delegate between views. Doing so can cause incorrect
        or unintuitive editing behavior since each view connected to a given delegate may receive the
        :meth:`QAbstractItemDelegate.closeEditor` signal, and attempt to access, modify or close an editor that has
        already been closed.

        Args:
            column: Column index.
            delegate: New delegate.
        """
        super().setItemDelegateForColumn(column, delegate)
        model: QAbstractItemModel = self.model()
        if model is None or column >= model.columnCount():
            return
        rows = model.rowCount()
        if rows > 0:
            # Reset editorHash amongst other things, so that previously created editors of different types
            # (due to different delegate) are removed and allow creating new ones
            self.reset()
            self._check_persistent_editors_for_data(model.createIndex(0, column), model.createIndex(rows - 1, column))

    def setItemDelegateForRow(self, row: int, delegate: QAbstractItemDelegate):
        """
        Sets the given item delegate used by this view and model for the given row. All items on row will be drawn
        and managed by delegate instead of using the default delegate (i.e., :meth:`QAbstractItemView.itemDelegate`).

        Any existing row delegate for row will be removed, but not deleted. :class:`QAbstractItemView` does not take
        ownership of delegate.

        **Note:** If a delegate has been assigned to both a row and a column, the row delegate (i.e., this delegate)
        will take precedence and manage the intersecting cell index.

        **Warning:** You should not share the same instance of a delegate between views. Doing so can cause incorrect
        or unintuitive editing behavior since each view connected to a given delegate may receive the
        :meth:`QAbstractItemDelegate.closeEditor` signal, and attempt to access, modify or close an editor that has
        already been closed.

        Args:
            row: Row index.
            delegate: New delegate.
        """
        super().setItemDelegateForRow(row, delegate)
        model: QAbstractItemModel = self.model()
        if model is None or row >= model.rowCount():
            return
        cols = model.columnCount()
        if cols > 0:
            # Reset editorHash amongst other things, so that previously created editors of different types
            # (due to different delegate) are removed and allow creating new ones
            self.reset()
            self._check_persistent_editors_for_data(model.createIndex(row, 0), model.createIndex(row, cols - 1))

    def set_persistent_editor_for_column(self, col: int):
        """
        Marks the given column as the one possessing persistent editors.

        Args:
            col: Column index.
        """
        self._persistent_cols.add(col)
        self._update_persistent_editors_for_col(col)

    def set_persistent_editor_for_row(self, row: int):
        """
        Marks the given row as the one possessing persistent editors.

        Args:
            row: Row index.
        """
        self._persistent_rows.add(row)
        self._update_persistent_editors_for_row(row)

    def _update_persistent_editors_for_col(self, col: int):
        model = self.model()
        if model is None:
            return
        if col >= 0 and col < model.columnCount():
            for row in range(model.rowCount()):
                index = model.createIndex(row, col)
                self.openPersistentEditor(index)

    def _update_persistent_editors_for_row(self, row: int):
        model = self.model()
        if model is None:
            return
        if row >= 0 and row < model.rowCount():
            for col in range(model.columnCount()):
                index = model.createIndex(row, col)
                self.openPersistentEditor(index)

    def _update_all_persistent_editors(self):
        for row in self._persistent_rows:
            self._update_persistent_editors_for_row(row)
        for col in self._persistent_cols:
            self._update_persistent_editors_for_col(col)

    def _check_persistent_editors_for_data(self, top_left: QModelIndex, bottom_right: QModelIndex, roles: Optional[List[Qt.ItemDataRole]] = None):
        # In case where this slot was called after creating a new item in the model, we need to mark it
        if roles and (Qt.DisplayRole not in roles or Qt.EditRole not in roles):
            return

        model = top_left.model()
        if model is None:
            model = self.model()
        if model is None:
            return
        affected_indexes: List[QModelIndex] = []
        for col in self._persistent_cols:
            if col >= top_left.column() and col <= bottom_right.column():
                affected_indexes.extend([model.createIndex(r, col) for r in range(top_left.row(), bottom_right.row() + 1)])
        for row in self._persistent_rows:
            if row >= top_left.row() and row <= bottom_right.row():
                affected_indexes.extend([model.createIndex(row, c) for c in range(top_left.column(), bottom_right.column() + 1)])

        for index in affected_indexes:
            self.openPersistentEditor(index)
