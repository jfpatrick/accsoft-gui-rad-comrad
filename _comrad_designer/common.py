from typing import Optional, Any
from qtpy.QtWidgets import (QColorDialog, QToolButton, QSpacerItem, QSizePolicy, QStyleOptionViewItem,
                            QStyledItemDelegate, QWidget, QFrame, QHBoxLayout)
from qtpy.QtCore import QObject, QPersistentModelIndex, QAbstractTableModel, QModelIndex, QLocale
from qtpy.QtGui import QFont, QColor


_STYLED_ITEM_DELEGATE_INDEX = '_comrad_persistent_index_'


class ColorButton(QToolButton):

    def __init__(self, parent: Optional[QObject] = None):
        """
        Button that opens a picker and displays the selected color using the RBG hex, as well as a thumbnail
        with background color corresponding to the picked color.

        Args:
            parent: Owning object.
        """
        super().__init__(parent)
        font = QFont('Monospace')
        font.setStyleHint(QFont.TypeWriter)
        self.setFont(font)
        self.setAutoRaise(True)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 0, 0, 0)
        icon = QFrame(self)
        icon.setFrameStyle(QFrame.Box)
        icon.resize(10, 10)
        icon.setMinimumSize(10, 10)
        icon.setMaximumSize(10, 10)
        layout.addWidget(icon)
        layout.addSpacerItem(QSpacerItem(10, 1, QSizePolicy.Expanding, QSizePolicy.Preferred))
        self._color_thumb = icon
        self.setLayout(layout)
        self.color = '#000000'

    @property
    def color(self) -> str:
        """Currently selected color, in RGB hex notation."""
        return self.text()

    @color.setter
    def color(self, new_val: str):
        name = QColor(new_val).name()  # Transform things like 'red' or 'darkblue' to HEX
        self.setText(name.upper())
        self._color_thumb.setStyleSheet(f'background-color: {new_val}')


class ColorPropertyColumnDelegate(QStyledItemDelegate):
    """
    Table delegate that draws :class:`ColorButton` widget in the cell.
    """

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex) -> QWidget:
        editor = ColorButton(parent)
        editor.clicked.connect(self._open_color_dialog)
        setattr(editor, _STYLED_ITEM_DELEGATE_INDEX, QPersistentModelIndex(index))
        return editor

    def setEditorData(self, editor: ColorButton, index: QModelIndex):
        if not isinstance(editor, ColorButton):
            return
        editor.color = str(index.data())
        if getattr(editor, _STYLED_ITEM_DELEGATE_INDEX, None) != index:
            setattr(editor, _STYLED_ITEM_DELEGATE_INDEX, QPersistentModelIndex(index))

    def setModelData(self, editor: QWidget, model: QAbstractTableModel, index: QModelIndex):
        # Needs to be overridden so that underlying implementation does not set garbage data to the model
        # This delegate is read-only, as we don not propagate value to the model from the editor, but rather
        # open the dialog ourselves.
        pass

    def displayText(self, value: Any, locale: QLocale) -> str:
        # Make sure that transparent button does not expose set label underneath
        return ''

    def _open_color_dialog(self):
        # This can't be part of the ColorButton, as sometimes it gets deallocated by the table, while color dialog
        # is open, resulting in C++ deallocation, while Python logic is in progress. Therefore, we keep it in the
        # delegate, that exists as long as table model exists.
        editor: ColorButton = self.sender()
        index: Optional[QPersistentModelIndex] = getattr(editor, _STYLED_ITEM_DELEGATE_INDEX, None)
        if not index or not index.isValid():
            return
        new_color = QColorDialog.getColor(QColor(str(index.data())))
        if not new_color.isValid():
            # User cancelled the selection
            return
        new_name = new_color.name()
        index.model().setData(QModelIndex(index), new_name)
