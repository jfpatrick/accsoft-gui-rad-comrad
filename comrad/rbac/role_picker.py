import logging
import operator
from typing import Optional, Set, Any, Dict, cast, List
from pathlib import Path
from qtpy import uic
from qtpy.QtWidgets import QDialog, QWidget, QDialogButtonBox, QPushButton, QCheckBox, QListView, QVBoxLayout
from qtpy.QtCore import (QStringListModel, QSortFilterProxyModel, QObject, QModelIndex, QPersistentModelIndex, Qt,
                         QVariant)
from qtpy.QtGui import QBrush
from comrad.rbac import CRBACState, CRBACLoginStatus, is_rbac_role_critical
from comrad.app.application import CApplication
from .rbac_dialog import RbaAuthDialogWidget


logger = logging.getLogger(__name__)


class MscRolesModel(QSortFilterProxyModel):

    def __init__(self, parent: Optional[QObject] = None):
        """
        Custom filter-sort model that filters out non-MCS roles on demand.

        Args:
            parent: Owner object.
        """
        super().__init__(parent)
        self._msc_only: bool = False

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        """
        Returns ``True`` if the item in the row indicated by the given ``source_row`` and ``source_parent``
        should be included in the model; otherwise returns ``False``.

        Note: By default, the :attr:`Qt.DisplayRole` is used to determine if the row should be accepted or not.
        This can be changed by setting the :meth:`QSortFilterProxyModel.filterRole` property.

        Args:
            source_row: Row index in question.
            source_parent: Parent owning index for nested lists.

        Returns:
            ``True`` if item should be included in the visible list.
        """
        data = self.sourceModel().createIndex(source_row, 0).data(self.filterRole())
        return isinstance(data, str) and (is_rbac_role_critical(data) or not self._msc_only)

    def _set_msc_only(self, new_val: bool):
        self._msc_only = new_val
        self.invalidateFilter()

    msc_only = property(fget=lambda self: self._msc_only, fset=_set_msc_only)
    """Display only MCS roles."""


class RolesModel(QStringListModel):

    def __init__(self, data: Dict[str, bool], parent: Optional[QObject] = None):
        """
        Custom string list model that memorizes selected positions.

        Args:
            data: Initial data.
            parent: Owner object.
        """
        super().__init__(list(data.keys()), parent)
        self._checked_items: Set[QPersistentModelIndex] = {QPersistentModelIndex(self.createIndex(i, 0))
                                                           for i, active in enumerate(data.values()) if active}

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """
        Flags to render the list row.

        Args:
            index: Position of the row.

        Returns:
            Flags how to render the row.
        """
        default_flags = super().flags(index)
        if index.isValid():
            return default_flags | Qt.ItemIsUserCheckable
        return default_flags

    def setData(self, index: QModelIndex, value: Any, role: Qt.ItemDataRole = Qt.EditRole) -> bool:
        """
        Set Data to the list view's data model at the given index.

        Args:
            index: Position of the new value
            value: new value
            role: which property is requested

        Returns:
            ``True`` if the data could be successfully set.
        """
        if not index.isValid() or role != Qt.CheckStateRole:
            return False

        if value == Qt.Checked:
            val = self.data(index)
            if is_rbac_role_critical(val):
                # At most one critical role can be selected at any time
                # When selecting a new critical one, we need to deselect other critical ones
                prev_mcs_indices = sorted((idx for idx in self._checked_items if is_rbac_role_critical(idx.data())),
                                          key=operator.methodcaller('row'))
                for selected_index in reversed(prev_mcs_indices):
                    self.setData(self.createIndex(selected_index.row(), 0), Qt.Unchecked, Qt.CheckStateRole)
            self._checked_items.add(QPersistentModelIndex(index))
        else:
            self._checked_items.remove(QPersistentModelIndex(index))

        self.dataChanged.emit(index, index)
        return True

    def data(self, index: QModelIndex, role: Qt.ItemDataRole = Qt.DisplayRole) -> Any:
        """
        Get Data from the list's model by a given index.

        Args:
            index: row & column in the list view
            role: which property is requested

        Returns:
            Data associated with the passed index.
        """
        if not index.isValid():
            return QVariant()
        if role == Qt.CheckStateRole:
            return Qt.Checked if QPersistentModelIndex(index) in self._checked_items else Qt.Unchecked
        elif role == Qt.ForegroundRole:
            val = self.data(index)
            if is_rbac_role_critical(val):
                return QBrush(Qt.red)  # Else handle by default

        return super().data(index, role)

    def bulk_check(self, select: bool):
        """
        Affect all of the items in the list by either selecting all or clearing all.

        Args:
            select: Select all if ``True``, else clear all.
        """
        start = self.createIndex(0, 0)
        end = self.createIndex(self.rowCount(), 0)
        if select:
            all_idx = (self.createIndex(i, 0) for i in range(self.rowCount()))
            non_mcs_idx = (idx for idx in all_idx if not is_rbac_role_critical(idx.data()))
            self._checked_items = {QPersistentModelIndex(idx) for idx in non_mcs_idx} | self._checked_items
        else:
            self._checked_items.clear()
        self.dataChanged.emit(start, end)

    @property
    def selected_roles(self) -> Set[str]:
        return {index.data() for index in self._checked_items}


class RbaRolePicker(QDialog):

    def __init__(self, rbac: CRBACState, parent: Optional[QWidget] = None):
        """
        Dialog to select user roles.

        Args:
            rbac: Reference to the RBAC manager.
            parent: Parent widget to own this object.
        """
        super().__init__(parent)

        # For IDE support, assign types to dynamically created items from the *.ui file
        self.btn_box: QDialogButtonBox = None
        self.btn_clear_all: QPushButton = None
        self.btn_select_all: QPushButton = None
        self.mcs_checkbox: QCheckBox = None
        self.role_view: QListView = None

        uic.loadUi(Path(__file__).parent / 'role_picker.ui', self)

        self.btn_box.button(QDialogButtonBox.Apply).clicked.connect(self._save_changes)
        self.btn_box.rejected.connect(self.close)
        self.mcs_checkbox.stateChanged.connect(self._on_show_msc_only)
        self.btn_clear_all.clicked.connect(self._on_clear_all)
        self.btn_select_all.clicked.connect(self._on_select_all)

        self.setWindowTitle(f"RBAC Role Picker for '{rbac.user}'")
        self._username = rbac.user

        self._src_model = RolesModel(data=rbac.roles or {}, parent=self)
        self._model = MscRolesModel(self)
        self._model.setSourceModel(self._src_model)
        self._model.sort(0)
        self.role_view.setModel(self._model)
        self._on_show_msc_only()

    def _on_show_msc_only(self):
        msc_only = self.mcs_checkbox.isChecked()
        self._model.msc_only = msc_only
        self.btn_clear_all.setHidden(msc_only)
        self.btn_select_all.setHidden(msc_only)

    def _on_clear_all(self):
        self._src_model.bulk_check(False)

    def _on_select_all(self):
        self._src_model.bulk_check(True)

    def _save_changes(self):
        selected_roles = list(self._src_model.selected_roles)

        # Note! This is a workaround (cause we can't relogin again without storing user's credentials),
        # We must ask for login again.
        dialog = RbaLoginDialog(new_roles=selected_roles, username=self._username, parent=self)
        dialog.setWindowTitle('Authenticate to apply new roles')
        if dialog.exec_() == QDialog.Accepted:
            self.accept()


class RbaLoginDialog(QDialog):

    def __init__(self, new_roles: List[str], username: str, parent: Optional[QWidget] = None):
        """
        Wrapper for the :class:`comrad.rbac.rbac_dialog.RbaAuthDialogWidget`. Currently, we cannot re-login
        with new roles, as :mod:`pyrbac` does not provide such capability. Instead, we are bound to ask
        the user to login again with a new login dialog.

        Args:
            new_roles: Roles to use when signing in again.
            username: Username to prefill for convenience.
            parent: Owning object.
        """
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setSizeConstraint(QVBoxLayout.SetFixedSize)
        self.setLayout(layout)
        app = cast(CApplication, CApplication.instance())
        self._main_widget = RbaAuthDialogWidget(app=app,
                                                parent=self,
                                                initial_username=username,
                                                initial_login_strategy=app.rbac.status,
                                                roles=new_roles)
        self._main_widget.layout().setContentsMargins(0, 0, 0, 0)
        self._btn_box = QDialogButtonBox(QDialogButtonBox.Cancel, self)
        layout.addWidget(self._main_widget)
        layout.addWidget(self._btn_box)
        self._btn_box.rejected.connect(self.close)
        app.rbac.rbac_status_changed.connect(self._on_rbac_status_changed)

    def _on_rbac_status_changed(self, new_status: int):
        if new_status != CRBACLoginStatus.LOGGED_OUT:
            logger.debug(f'RBAC has connected, closing the login dialog')
            self.accept()
