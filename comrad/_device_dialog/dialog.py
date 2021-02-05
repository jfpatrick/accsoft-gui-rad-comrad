import logging
import functools
from enum import IntEnum
from copy import copy
from typing import Optional, List, cast
from pathlib import Path
from qtpy.uic import loadUi
from qtpy.QtCore import Signal, QStringListModel, QModelIndex, QItemSelectionModel, Qt
from qtpy.QtGui import QMovie, QKeyEvent
from qtpy.QtWidgets import (QWidget, QDialog, QVBoxLayout, QPushButton, QLineEdit, QLabel, QStackedWidget,
                            QGroupBox, QListView, QComboBox, QDialogButtonBox)
from _comrad.comrad_info import COMRAD_VERSION
from comrad.data.addr import ControlEndpointAddress
from .model import DeviceListModel, NestedListRootItem


logger = logging.getLogger(__name__)


class DevicePropertySelector(QWidget):

    class NetworkRequestStatus(IntEnum):
        COMPLETE = 0
        IN_PROGRESS = 1
        FAILED = 2

    device_search_status_changed = Signal(NetworkRequestStatus)
    device_search_requested = Signal(str)

    def __init__(self, ccda_endpoint: str, user_agent: str, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self._selected_address = ControlEndpointAddress(protocol='japc',
                                                        device='',
                                                        prop='')

        self.deviceSearchButton: QPushButton = None
        self.deviceSearchLineEdit: QLineEdit = None
        self.resultStaticLabel: QLabel = None
        self.selector: QLabel = None
        self.deviceSearchControlStack: QStackedWidget = None
        self.deviceResultPage: QWidget = None
        self.deviceResultGroupBox: QGroupBox = None
        self.devicesListView: QListView = None
        self.fieldsListView: QListView = None
        self.propertiesListView: QListView = None
        self.deviceLoadingPage: QWidget = None
        self.deviceSearchActivity: QLabel = None
        self.deviceSearchActivityLabel: QLabel = None
        self.deviceSearchCancelButton: QPushButton = None
        self.deviceSearchErrorPage: QWidget = None
        self.deviceSearchErrorLabel: QLabel = None
        self.protocolCombobox: QComboBox = None

        loadUi(Path(__file__).parent / 'device_property_selector.ui', self)

        self._search_results_model = DeviceListModel(self)
        self._requested_device: str = ''
        self._sub_requests_to_go: int = 0
        self._curr_search_status = DevicePropertySelector.NetworkRequestStatus.FAILED
        self._prev_search_status = DevicePropertySelector.NetworkRequestStatus.FAILED
        self._search_results: List[NestedListRootItem]

        movie = QMovie(str(Path(__file__).absolute().parent.parent / 'icons' / 'loader.gif'))
        self.deviceSearchActivity.setMovie(movie)
        movie.start()

        self.devicesListView.setModel(QStringListModel(self))
        self.propertiesListView.setModel(QStringListModel(self))
        self.fieldsListView.setModel(QStringListModel(self))

        # Protocol selector
        self.protocolCombobox.addItem('Use default', '')
        for proto in ['rda3', 'rda', 'tgm', 'no', 'rmi']:
            self.protocolCombobox.addItem(proto.upper(), proto)

        self.protocolCombobox.activated.connect(self._on_protocol_selected)

        # Device selector
        self.devicesListView.activated.connect(self._search_results_model.root_item_selection_changed)
        self.devicesListView.clicked.connect(self._search_results_model.root_item_selection_changed)
        self.propertiesListView.activated.connect(self._search_results_model.intermediate_item_selection_changed)
        self.propertiesListView.clicked.connect(self._search_results_model.intermediate_item_selection_changed)
        self.fieldsListView.activated.connect(self._search_results_model.leaf_selection_changed)
        self.fieldsListView.clicked.connect(self._search_results_model.leaf_selection_changed)
        self._search_results_model.root_items_changed.connect(functools.partial(self._on_list_changed, list_view=self.devicesListView))
        self._search_results_model.intermediate_items_changed.connect(functools.partial(self._on_list_changed, list_view=self.propertiesListView))
        self._search_results_model.leafs_changed.connect(functools.partial(self._on_list_changed, list_view=self.fieldsListView))
        self._search_results_model.result_changed.connect(self._on_result_changed)

        # Search
        self.deviceSearchLineEdit.textChanged.connect(self._on_device_search_changed)
        self.deviceSearchLineEdit.returnPressed.connect(self._start_search)
        self.deviceSearchButton.pressed.connect(self._start_search)
        self.device_search_status_changed.connect(self._update_from_status)
        self.device_search_requested.connect(self._on_search_requested)

        # Initially error page displays suggestion to start the search
        self.device_search_status_changed.emit(DevicePropertySelector.NetworkRequestStatus.FAILED)
        self._on_device_search_changed('')
        self._search_results_model.set_data([])

    @property
    def address(self) -> str:
        return str(self._selected_address)

    @address.setter
    def address(self, new_val: str):
        new_addr = ControlEndpointAddress.from_string(new_val)
        if new_addr is None:
            return

        self._selected_address = new_addr

        # Adjust protocol
        parsed_proto = self._selected_address.protocol
        if parsed_proto:
            proto_idx = self.protocolCombobox.findData(parsed_proto)
            if proto_idx == -1:
                self._selected_address.protocol = None
            else:
                self.protocolCombobox.setCurrentIndex(proto_idx)
        device_addr = copy(self._selected_address)
        device_addr.protocol = None
        final_addr = str(device_addr)
        self.device_search_requested.emit(final_addr)
        self.deviceSearchLineEdit.setText(final_addr)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            return
        super().keyPressEvent(event)

    def _on_device_search_changed(self, search_string: str):
        self.deviceSearchButton.setEnabled(len(search_string) > 0)

    def _on_device_search_results_changed(self):
        self._search_results_model.set_data(self._search_results)

        # If device is the only one, auto select it
        if len(self._search_results) == 1:
            self._search_results_model.select_device(0)
            return

        for idx, dev in enumerate(self._search_results):
            if dev.name == self._requested_device:
                self._search_results_model.select_device(idx)

    def _on_protocol_selected(self):
        text: str = self.protocolCombobox.currentData()
        self._selected_address.protocol = text.lower()
        self.selector.setText(self.address)

    def _on_list_changed(self, items: List[str], selected_index: QModelIndex, list_view: QListView):
        cast(QStringListModel, list_view.model()).setStringList(items)
        list_view.setEnabled(len(items) > 0)
        list_view.setCurrentIndex(selected_index)
        list_view.selectionModel().select(selected_index, QItemSelectionModel.Select)
        list_view.setFocus(Qt.ActiveWindowFocusReason)

    def _on_result_changed(self, result: str):
        parsed = ControlEndpointAddress.from_string(result)
        if parsed is None:
            return

        self._selected_address.device = parsed.device
        self._selected_address.property = parsed.property
        self._selected_address.field = parsed.field

        # When setting from CCDB, assume no service
        if self._selected_address.service:
            self._selected_address.service = None
        self.selector.setText(self.address)

    def _start_search(self):
        self.device_search_requested.emit(self.deviceSearchLineEdit.text())

    def _handle_lookup_error(self, error: str):
        self.deviceSearchErrorLabel.setText(error)
        self.device_search_status_changed.emit(DevicePropertySelector.NetworkRequestStatus.FAILED)

    def _handle_end_of_sub_requests(self, success: bool):
        self._sub_requests_to_go -= 1
        if success and self._sub_requests_to_go == 0:
            self._on_device_search_results_changed()
            self.device_search_status_changed.emit(DevicePropertySelector.NetworkRequestStatus.COMPLETE)

    def _update_from_status(self, status: 'DevicePropertySelector.NetworkRequestStatus'):
        in_progress = status == DevicePropertySelector.NetworkRequestStatus.IN_PROGRESS
        self.deviceSearchControlStack.setCurrentIndex(status.value)
        self.deviceSearchLineEdit.setEnabled(not in_progress)
        self.deviceSearchButton.setEnabled(not in_progress)

        # Disable these to allow tab order jump directly to the cancel button
        if in_progress:
            self.devicesListView.setEnabled(False)
            self.propertiesListView.setEnabled(False)
            self.fieldsListView.setEnabled(False)

        self._prev_search_status = self._curr_search_status
        self._curr_search_status = status

    def _on_search_requested(self, search_string: str):
        trimmed_search_string = search_string.strip()
        if not trimmed_search_string:
            return

        self.device_search_status_changed.emit(DevicePropertySelector.NetworkRequestStatus.IN_PROGRESS)
        device_addr = ControlEndpointAddress.from_string(trimmed_search_string)
        search_device = device_addr.device if device_addr is not None and device_addr.valid else trimmed_search_string
        self._requested_device = search_device

        self.deviceSearchActivityLabel.setText(f'Searching {search_device}...')


class DevicePropertyDialog(QDialog):

    def __init__(self, addr: str = '', parent: Optional[QWidget] = None):
        """
        Dialog for choosing device property (and field) interactively from CCDB.

        Args:
            addr: Previously selected address.
            parent: Owning widget.
        """
        super().__init__(parent)
        self.setWindowTitle('Select Device Property...')
        layout = QVBoxLayout()
        self._widget = DevicePropertySelector(ccda_endpoint='', user_agent=f'ComRAD Designer {COMRAD_VERSION}', parent=self)
        self._widget.address = addr
        layout.addWidget(self._widget)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        layout.addWidget(buttons)
        self.setLayout(layout)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.resize(526, 360)

    @property
    def address(self) -> str:
        """Selected address of the dialog"""
        return self._widget.address
