from typing import Optional
from pydm.utilities.iconfont import IconFont
from qtpy.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QSizePolicy, QPushButton, QDialog
from qtpy.QtCore import Signal, Slot, Property
from comrad._device_dialog import DevicePropertyDialog


class DevicePropertyLineEdit(QWidget):

    address_changed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None, address: str = ''):
        super().__init__(parent)
        layout = QHBoxLayout()
        self._line_edit = QLineEdit(address)
        self._line_edit.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self._line_edit.setPlaceholderText('device/property#field')
        self._line_edit.textChanged.connect(self.address_changed.emit)
        self._btn = QPushButton()
        self._btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.MinimumExpanding)
        self._btn.setMaximumWidth(24)
        self._btn.setMinimumWidth(24)
        self._btn.setIcon(IconFont().icon('search'))
        self._btn.clicked.connect(self._open_dialog)
        layout.addWidget(self._line_edit)
        layout.addWidget(self._btn)
        layout.setSpacing(1)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self.setTabOrder(self._line_edit, self._btn)
        self.setFocusProxy(self._line_edit)

    def _get_address(self) -> str:
        return self._line_edit.text()

    def _set_address(self, new_val: str):
        self._line_edit.setText(new_val)

    address = Property(str, fget=_get_address, fset=_set_address)

    @Slot()
    def clear(self):
        self._line_edit.clear()

    def _open_dialog(self):
        dialog = DevicePropertyDialog(addr=self._line_edit.text())
        if dialog.exec_() == QDialog.Accepted:
            self._line_edit.setText(dialog.address)
