from typing import Optional, cast
from qtpy.QtWidgets import QToolButton, QSizePolicy, QWidget
from qtpy.QtCore import Qt
from comrad import CApplication


class OrientedToolButton(QToolButton):

    def __init__(self, horizontal: QSizePolicy, vertical: QSizePolicy, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._h_policy = horizontal
        self._v_policy = vertical
        toolbar = cast(CApplication, CApplication.instance()).main_window.ui.navbar
        self._update_size_policy(toolbar.orientation())
        toolbar.orientationChanged.connect(self._update_size_policy)

    def _update_size_policy(self, orientation: Qt.Orientation):
        if orientation == Qt.Horizontal:
            self.setSizePolicy(self._h_policy, self._v_policy)
        else:
            self.setSizePolicy(self._v_policy, self._h_policy)
