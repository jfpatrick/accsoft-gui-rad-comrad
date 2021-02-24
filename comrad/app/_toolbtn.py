from typing import Optional, cast, List
from abc import abstractmethod
from qtpy.QtWidgets import QToolButton, QSizePolicy, QWidget, QHBoxLayout, QVBoxLayout
from qtpy.QtCore import Qt, QObjectCleanupHandler
from comrad import CApplication
from comrad.generics import GenericQObjectMeta


class ToolButton(QToolButton):

    def __init__(self,
                 horizontal: QSizePolicy,
                 vertical: QSizePolicy,
                 track_orientation: bool = True,
                 track_style: bool = True,
                 track_icon_size: bool = True,
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._h_policy = horizontal
        self._v_policy = vertical
        toolbar = cast(CApplication, CApplication.instance()).main_window.ui.navbar
        self._update_size_policy(toolbar.orientation())
        if track_orientation:
            toolbar.orientationChanged.connect(self._update_size_policy)
        if track_style:
            self.setToolButtonStyle(toolbar.toolButtonStyle())
            toolbar.toolButtonStyleChanged.connect(self.setToolButtonStyle)
        if track_icon_size:
            self.setIconSize(toolbar.iconSize())
            toolbar.iconSizeChanged.connect(self.setIconSize)

    def _update_size_policy(self, orientation: Qt.Orientation):
        if orientation == Qt.Horizontal:
            self.setSizePolicy(self._h_policy, self._v_policy)
        else:
            self.setSizePolicy(self._v_policy, self._h_policy)


class ToolButtonSet(QWidget, metaclass=GenericQObjectMeta):

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Set of buttons accommodated side-by-side in a navigation bar.

        Args:
            parent: Parent widget to hold this object.
        """
        super().__init__(parent)
        self.app = cast(CApplication, CApplication.instance())
        toolbar = self.app.main_window.ui.navbar
        toolbar.orientationChanged.connect(self._set_layout_for_orientation)
        self.buttons = self.create_buttons(self.app)
        self._set_layout_for_orientation(toolbar.orientation())

    @abstractmethod
    def create_buttons(self, app: CApplication) -> List[QToolButton]:
        """
        Create button objects to be accommodated in the set.

        Args:
            app: Application instance, if needed by buttons.

        Returns:
            List of buttons.
        """
        pass

    def _set_layout_for_orientation(self, orientation: Qt.Orientation):
        new_layout_type = QHBoxLayout if orientation == Qt.Horizontal else QVBoxLayout
        prev_layout = self.layout()
        if type(prev_layout) == new_layout_type:
            return
        if prev_layout is not None:
            for child in prev_layout.children():  # children of a layout are always items
                prev_layout.removeItem(child)

        new_layout = new_layout_type()
        new_layout.setContentsMargins(0, 0, 0, 0)
        for btn in self.buttons:
            new_layout.addWidget(btn)

        if prev_layout is not None:
            # You can't directly delete a layout and you can't
            # replace a layout on a widget which already has one
            # Found here: https://stackoverflow.com/a/10439207
            QObjectCleanupHandler().add(prev_layout)
            prev_layout = None

        self.setLayout(new_layout)
