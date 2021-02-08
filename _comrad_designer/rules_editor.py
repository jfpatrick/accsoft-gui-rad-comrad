import os
import logging
import json
from collections import OrderedDict
from abc import abstractmethod
from pathlib import Path
from typing import Optional, Union, cast, Type, Callable, List, Generic, TypeVar, Any, Tuple, Dict
from pydm.utilities.iconfont import IconFont
from PyQt5.Qsci import QsciScintilla, QsciLexerJSON
from qtpy.QtWidgets import (QDialog, QWidget, QHBoxLayout, QFrame,
                            QPushButton, QListView, QSizePolicy, QTabWidget,
                            QLabel, QLineEdit, QComboBox, QStackedWidget, QSpinBox, QStyledItemDelegate,
                            QHeaderView, QCheckBox, QDialogButtonBox, QMessageBox, QStyleOptionViewItem)
from qtpy.QtCore import (Qt, QAbstractTableModel, QObject, QModelIndex, QVariant, Signal, QLocale, QSignalBlocker,
                         QAbstractListModel, QIdentityProxyModel, QAbstractProxyModel, QItemSelectionModel,
                         QPersistentModelIndex)
from qtpy.QtGui import QFont, QFocusEvent, QShowEvent
from qtpy.uic import loadUi
from accwidgets.qt import (BooleanPropertyColumnDelegate, AbstractComboBoxColumnDelegate,
                           AbstractListModel as BaseListModel, AbstractTableModel as BaseTableModel,
                           PersistentEditorTableView)
from accwidgets._designer_base import get_designer_cursor
from comrad.rules import CBaseRule, CNumRangeRule, CEnumRule, unpack_rules, is_valid_color
from comrad.qsci import configure_common_qsci, QSCI_INDENTATION
from comrad.json import CJSONEncoder, CJSONDeserializeError
from comrad.widgets.mixins import CWidgetRulesMixin, CWidgetRuleMap
from comrad.data.japc_enum import CEnumValue
from comrad.generics import GenericMeta, GenericQObjectMeta
from comrad._selector import PLSSelectorDialog, PLSSelectorConfig
from comrad._device_dialog import DevicePropertyDialog
from _comrad_designer.common import ColorPropertyColumnDelegate, _STYLED_ITEM_DELEGATE_INDEX
from _comrad_designer.device_edit import DevicePropertyLineEdit


logger = logging.getLogger(__name__)


R = TypeVar('R', bound=CBaseRule)
"""Generic rule type"""

S = TypeVar('S', CNumRangeRule.Range, CEnumRule.EnumConfig)
"""Generic sub-rule configuration type. It's relevant for those rules that use table models."""


class JsonModelMixin:

    def to_json(self, indent: Optional[int] = None) -> str:
        """Dumps contents as JSON-formatter string.

        Args:
            indent: Indentation in number of spaces.

        Returns:
            JSON-formatter string.
        """
        return json.dumps(cast(BaseListModel, self).raw_data, cls=CJSONEncoder, indent=indent)


class AbstractTableModel(BaseTableModel[S], JsonModelMixin, Generic[S], metaclass=GenericMeta):

    def __init__(self, data: List[S], rule_prop: CBaseRule.Property, prop_map: CWidgetRuleMap, parent: Optional[QObject] = None):
        """
        Base class for the models used in the table, of the rule sub-components, e.g. range lists or enum options.

        Args:
            data: Initial data.
            rule_prop: Property of the rule (some properties need special initial value for the "Property value".
            prop_map: Mapping between Property names and their base types.
            parent: Owning object.
        """
        BaseTableModel.__init__(self, data=data, parent=parent)
        JsonModelMixin.__init__(self)
        self.prop_enum_type = rule_prop
        self._prop_map = prop_map

    @abstractmethod
    def create_row_item(self) -> S:
        """Create a new empty object when appending a new row to the table."""
        pass

    def json_contents_updated(self, new_val: List[S]):
        """
        Slot to update the model, whenever the source of the JSON editor changes. This is implemented as a separate
        call-out, instead of going through :meth:`QAbstractItemModel.setData` calls, because normally we wipe-out
        all of the contents and re-generate them from scratch from JSON, which is different form changing rows
        one by one.

        Args:
            new_val: New contents parsed from JSON.
        """
        # Can't simply replace self._data, need to keep the same reference
        self.beginResetModel()
        self._data.clear()
        self._data.extend(new_val)
        self.endResetModel()

        # Even though endResetModel() is issuing a modelReset signal, which is supposed
        # to update attached views, tableView cells do not get re-rendered, so we issue a
        # dataChange to fix that
        rows = self.rowCount()
        cols = self.columnCount()
        if rows > 0 and cols > 0:
            self.notify_change(start=self.createIndex(0, 0),
                               end=self.createIndex(rows - 1, cols - 1),
                               action_type=self.ChangeType.UPDATE_ITEM)

    def create_row(self) -> S:
        new_obj = self.create_row_item()
        if self.prop_enum_type == CBaseRule.Property.COLOR:
            new_obj.prop_val = '#000000'
        else:
            _, __, caster = self._prop_map[self.prop_enum_type.value]
            if caster != str:
                new_obj.prop_val = caster(0)  # 0, 0.0 or False, based on the caster
        return new_obj

    def headerData(self, section: int, orientation: Qt.Orientation, role: Qt.ItemDataRole = Qt.DisplayRole) -> str:
        if role == Qt.DisplayRole and orientation == Qt.Horizontal and section < self.columnCount() and section == 0:
            return 'Property value'
        return super().headerData(section, orientation, role)

    def data(self, index: QModelIndex, role: Qt.ItemDataRole = Qt.DisplayRole) -> Union[str, int, float, bool]:
        if index.isValid() and role in [Qt.DisplayRole, Qt.EditRole] and index.column() == 0:
            # Common logic to process shared first column (rule value)
            row = self._data[index.row()]
            # Because prop_val can be string when unpacked, we must convert it to the actual type,
            # otherwise the usage of standard QStyledItemDelegates is not possible, as they will
            # present line edits always, instead of spin boxes for ints/floats.
            _, __, caster = self._prop_map[self.prop_enum_type.value]
            try:
                return caster(row.prop_val)
            except ValueError:
                # Can't convert number from empty string
                return caster(0)
        else:
            return super().data(index, role)

    def setData(self, index: QModelIndex, value: Any, role: Qt.ItemDataRole = Qt.EditRole) -> bool:
        if index.isValid() and role == Qt.EditRole and index.column() == 0:
            # Common logic to process shared first column (rule value)
            row = self._data[index.row()]
            row.prop_val = value
            self.notify_change(start=index.siblingAtColumn(0),
                               end=index.siblingAtColumn(self.columnCount() - 1),
                               action_type=self.ChangeType.UPDATE_ITEM)
            return True
        else:
            return super().setData(index, value, role)


class JSONEditorWrapper(QObject):

    json_changed = Signal(list)
    """JSON contents have been edited by the user and were successfully parsed."""

    def __init__(self, editor: QsciScintilla, parent: Optional[QObject] = None):
        """
        We can't promote :class:`QSciScintilla` in Qt Designer, because it fails to allow
        selection of non-standard base classes, and therefore promotion can never
        be applied on the :class:`QsciScintilla` component. This object creates a logical wrapper around
        the widget to encapsulate some logic.

        Args:
            editor: Original editor widget.
            parent: Owning object.
        """
        super().__init__(parent)
        self._editor = editor
        self._src_valid: bool = True
        self._updating_model: bool = False
        self._model: Optional[AbstractTableModel] = None
        lexer = QsciLexerJSON(self._editor)
        self._editor.setLexer(lexer)
        configure_common_qsci(self._editor)
        self._editor.setReadOnly(False)
        self._editor.textChanged.connect(self._text_changed)

    @property
    def valid(self) -> bool:
        """Source is a valid JSON that corresponds to the rule structure."""
        return self._src_valid

    def set_model(self, model: Optional[AbstractTableModel]):
        """Connects the view to the model."""
        if self._model:
            self._model.dataChanged.disconnect(self._model_updated)
            self.json_changed.disconnect(self._model.json_contents_updated)
        self._model = model
        if model:
            model.dataChanged.connect(self._model_updated)
            self.json_changed.connect(model.json_contents_updated)
            self._set_editor(model)

    def clear(self):
        """Clears editor."""
        self._editor.clear()
        self._src_valid = True
        self._updating_model = False

    def _model_updated(self):
        if not self._updating_model:
            model = cast(AbstractTableModel, self.sender())
            self._set_editor(model)

    def _set_editor(self, model: AbstractTableModel):
        self._src_valid = True
        blocker = QSignalBlocker(self._editor)  # Will reset in the destructor == when going out of scope
        self._editor.setText(model.to_json(indent=QSCI_INDENTATION))
        blocker.unblock()

    def _text_changed(self):
        if not self._model:
            logger.warning('Cannot deserialize JSON without knowing which type should be used.')
            return
        row_type = type(self._model.create_row())
        try:
            contents = json.loads(self._editor.text())
            if not isinstance(contents, list):
                raise CJSONDeserializeError(f'Expected list of rules, got {type(contents).__name__}', None, 0)
            parsed_json = list(map(row_type.from_json, contents))
            if self._model.prop_enum_type == CBaseRule.Property.COLOR:
                if any(not is_valid_color(entry) for entry in parsed_json):
                    raise CJSONDeserializeError('Invalid color format', None, 0)
        except (CJSONDeserializeError, json.JSONDecodeError):
            self._src_valid = False
            return
        self._src_valid = True
        self._updating_model = True
        self.json_changed.emit(parsed_json)
        self._updating_model = False


class AbstractTableDetailsView(QWidget, Generic[R, S], metaclass=GenericQObjectMeta):

    MODEL_CLASS: Type = AbstractTableModel
    """Model class that is applied to the table. It must be the subclass of :class:`AbstractTableModel`."""

    ITEM_DELEGATES: Dict[int, Type] = {}
    """Map of the column indexes and :class:`QStyledItemDelegate` subclasses that should serve that column."""

    RULE_TYPE: CBaseRule.Type
    """Type of the rule that the view should work with."""

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Base class for rule details, that are based on table view.

        Args:
            parent: Parent owner.
        """
        super().__init__(parent)
        self.property_map: CWidgetRuleMap = {}  # Copied from the widget for resolution

        self.add_btn: QPushButton = None
        self.del_btn: QPushButton = None
        self.decl_table: PersistentEditorTableView = None  # type: ignore  # Instantiated in loadUi
        self.tabs: QTabWidget = None
        self.src_edit: QsciScintilla = None
        self._model: Optional[AbstractTableModel] = None

        loadUi(Path(__file__).parent / 'rules_table.ui', self)

        self.json_edit = JSONEditorWrapper(editor=self.src_edit, parent=self)

        self.decl_table.set_persistent_editor_for_column(0)
        self.decl_table.set_persistent_editor_for_column(1)
        for col, delegate_type in self.ITEM_DELEGATES.items():
            # Attention! Always pass parent here. Not doing so, will result in crash without any trace log.
            self.decl_table.setItemDelegateForColumn(col, delegate_type(self.decl_table))

        self.add_btn.setIcon(IconFont().icon('plus'))
        self.del_btn.setIcon(IconFont().icon('minus'))
        self.add_btn.clicked.connect(self._add_row)
        self.del_btn.clicked.connect(self._del_row)

    def set_rule(self, rule: CBaseRule, rule_type: int):
        """Slot to update the view whenever a rule in the details view has changed.

        Args:
            rule: Rule instance.
            rule_type: Type of the rule that is currently being edited. This type is checked against the type
                       that the view is committed with and ignore calls for irrelevant types.
        """
        if rule_type != self.RULE_TYPE:
            # Message is not meant for us
            return
        rule_prop = CBaseRule.Property(rule.prop)
        self._set_model(self.MODEL_CLASS(data=getattr(rule, _TABLE_RULE_ATTR_NAME[type(rule)]),
                                         rule_prop=rule_prop,
                                         prop_map=self.property_map,
                                         parent=self))
        self._configure_table(rule_prop)
        self.tabs.setCurrentIndex(0)

    def clear(self):
        """Slot to clear the view when no rule is selected."""
        self._set_model(None)
        self.decl_table.reset()
        self.json_edit.clear()

    def _set_model(self, new_val: Optional[AbstractTableModel]):
        self._model = new_val
        self.json_edit.set_model(new_val)
        self.decl_table.setModel(new_val)

        if new_val:
            cols = new_val.columnCount()
            if cols > 0:
                header = self.decl_table.horizontalHeader()
                for idx in range(cols - 1):
                    # Avoids squashed view on column titles when the table is empty
                    header.setResizeMode(idx, QHeaderView.ResizeToContents)

    def _configure_table(self, rule_prop: CBaseRule.Property):
        # Delegates must be set after setting the model, especially resetting the model
        self.decl_table.horizontalHeader().setResizeMode(0, QHeaderView.ResizeToContents)  # default
        if rule_prop == CBaseRule.Property.COLOR:
            self.decl_table.setItemDelegateForColumn(0, ColorPropertyColumnDelegate())
        else:
            _, __, new_type = self.property_map[rule_prop.value]
            if new_type == bool:
                self.decl_table.setItemDelegateForColumn(0, BooleanPropertyColumnDelegate())
            else:
                # Fallback to default implementations (QLineEdit for strings and spinboxes for numerical)
                self.decl_table.setItemDelegateForColumn(0, None)
                self.decl_table.horizontalHeader().setResizeMode(0, QHeaderView.Fixed)  # Otherwise, it claims too much space

    def _add_row(self):
        if self._model:
            self._model.append_row()

    def _del_row(self):
        if not self._model:
            return

        indexes = self.decl_table.selectionModel().selectedRows(0)
        if len(indexes) == 0:
            return

        # Ask for permission only for multiple rows deletion
        if len(indexes) > 1:
            reply = QMessageBox().question(self,
                                           'Message',
                                           'Delete selected rows?',
                                           QMessageBox.Yes,
                                           QMessageBox.No)

            if reply != QMessageBox.Yes:
                return

        for index in reversed(indexes):
            self._model.remove_row_at_index(index)


class RangeEdit(QWidget):

    value_changed = Signal()
    """Range value has been updated by the user."""

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Widget that allows editing ranges (min-max) by providing two line edits in a row.

        Args:
            parent: Owning object.
        """

        super().__init__(parent)
        self._edited_val: str = ''

        class FocusLineEdit(QLineEdit):

            editing_started = Signal(str)

            def focusOutEvent(self, event: QFocusEvent):
                super().focusOutEvent(event)
                self.editingFinished.emit()

            def focusInEvent(self, event: QFocusEvent):
                super().focusInEvent(event)
                self.editing_started.emit(self.text())

            def hasAcceptableInput(self) -> bool:
                val = self.text()
                try:
                    return str(float(val)) == val or str(int(val)) == val
                except ValueError:
                    return False

        def make_field(h_align: Qt.Alignment) -> FocusLineEdit:
            field = FocusLineEdit()
            field.setAlignment(h_align | Qt.AlignVCenter)
            field.setStyleSheet('background: transparent')
            field.setFrame(False)
            field.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            return field

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)
        self._min_field = make_field(h_align=Qt.AlignRight)
        self._min_field.editing_started.connect(self._field_editing_started)
        self._min_field.editingFinished.connect(self._field_editing_finished)
        layout.addWidget(self._min_field)
        lbl = QLabel(' ≤ channel value < ')
        layout.addWidget(lbl)
        self._max_field = make_field(h_align=Qt.AlignLeft)
        self._max_field.editing_started.connect(self._field_editing_started)
        self._max_field.editingFinished.connect(self._field_editing_finished)
        layout.addWidget(self._max_field)

    @property
    def range(self) -> Tuple[float, float]:
        """Range that is displayed in the widget"""
        return float(self._min_field.text()), float(self._max_field.text())

    @range.setter
    def range(self, new_val: Tuple[float, float]):
        min_val, max_val = new_val
        self._min_field.setText(str(min_val))
        self._max_field.setText(str(max_val))

    def _field_editing_started(self, val: str):
        self._edited_val = val

    def _field_editing_finished(self):
        field = cast(QLineEdit, self.sender())
        if field.hasAcceptableInput():
            self.value_changed.emit()
        else:
            field.setText(self._edited_val)


class RangeColumnDelegate(QStyledItemDelegate):
    """
    Table delegate that draws :class:`RangeEdit` widget in the cell.
    """

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex) -> QWidget:
        editor = RangeEdit(parent)
        setattr(editor, _STYLED_ITEM_DELEGATE_INDEX, QPersistentModelIndex(index))
        editor.value_changed.connect(self._range_changed)
        return editor

    def setEditorData(self, editor: RangeEdit, index: QModelIndex) -> None:
        if not isinstance(editor, RangeEdit):
            return
        editor.range = index.data()
        if getattr(editor, _STYLED_ITEM_DELEGATE_INDEX, None) != index:
            setattr(editor, _STYLED_ITEM_DELEGATE_INDEX, QPersistentModelIndex(index))

    def setModelData(self, editor: RangeEdit, model: QAbstractTableModel, index: QModelIndex):
        if not isinstance(editor, RangeEdit):
            return
        model.setData(index, editor.range)

    def _range_changed(self):
        editor = self.sender()
        index: Optional[QPersistentModelIndex] = getattr(editor, _STYLED_ITEM_DELEGATE_INDEX, None)
        if not index or not index.isValid():
            return
        self.setModelData(editor, index.model(), QModelIndex(index))


class RangeTableModel(AbstractTableModel[CNumRangeRule.Range]):
    """
    Table model that works with range rule table.
    """

    def column_name(self, section: int) -> str:
        return 'Channel range value'

    def columnCount(self, parent: Optional[QModelIndex] = None) -> int:
        return 2

    def create_row_item(self) -> CNumRangeRule.Range:
        return CNumRangeRule.Range(min_val=0.0, max_val=1.0, prop_val='')

    def get_cell_data(self, index: QModelIndex, row: CNumRangeRule.Range) -> Any:
        return row.min_val, row.max_val

    def set_cell_data(self, index: QModelIndex, row: CNumRangeRule.Range, value: Any) -> bool:
        row.min_val, row.max_val = value
        return True


class RangeDetailsView(AbstractTableDetailsView[CNumRangeRule, CNumRangeRule.Range]):
    """
    Concrete implementation of the details view that works with :class:`CNumRangeRule.Range` tables.
    """

    MODEL_CLASS = RangeTableModel
    ITEM_DELEGATES = {
        1: RangeColumnDelegate,
    }
    RULE_TYPE = CBaseRule.Type.NUM_RANGE


class EnumFieldColumnDelegate(AbstractComboBoxColumnDelegate):
    """
    Delegate to render the combobox in the cell that displays available enum field names.
    """

    def configure_editor(self, editor: QComboBox, _):
        for field_opt in CEnumRule.EnumField:
            editor.addItem(str(field_opt).split('.')[-1].title(), field_opt.value)

    def user_data_to_model(self, value: Any) -> Any:
        return CEnumRule.EnumField(value)  # This may throw ValueError, that's expected outside

    def model_to_user_data(self, value: Any) -> Any:
        return value.value   # FIXME: What's the type here?


SubEdit = TypeVar('SubEdit', bound=QWidget)
"""Sub-editor generic type"""

SubValue = TypeVar('SubValue', int, str, CEnumValue.Meaning)
"""Value type that :obj:`SubEdit` works with."""


class AbstractEnumValueSubEditorFactory(Generic[SubEdit, SubValue], metaclass=GenericMeta):
    """
    Factory skeleton to provide information about sub-editors that can be dynamically created in the
    cell based on the "Enum field name" that is selected for the given row.
    """

    @classmethod
    @abstractmethod
    def create_subeditor(cls, slot: Callable) -> SubEdit:
        """Instantiate a widget, but do not populate data inside. This has a similar principal,
        as :meth:`QAbstractItemDelegate.createEditor`."""
        pass

    @classmethod
    @abstractmethod
    def populate_subeditor(cls, subeditor: SubEdit, value: SubValue):
        """Populate a previously created widget with the given model. This has a similar principal,
        as :meth:`QAbstractItemDelegate.setEditorData`."""
        pass

    @classmethod
    @abstractmethod
    def read_subeditor(cls, subeditor: SubEdit) -> SubValue:
        """Read the edited data from the widget to propagate it further to the model. This has a similar principal,
        as :meth:`QAbstractItemDelegate.setModelData`."""
        pass


class EnumValueCodeFactory(AbstractEnumValueSubEditorFactory[QSpinBox, int]):
    """Factory that manages widgets for the "Code" editor of the enum."""

    @classmethod
    def create_subeditor(cls, slot: Callable) -> QSpinBox:
        subeditor = QSpinBox()
        subeditor.setStyleSheet('background: transparent')
        subeditor.editingFinished.connect(slot)
        return subeditor

    @classmethod
    def populate_subeditor(cls, subeditor: QSpinBox, value: int):
        subeditor.setValue(value)

    @classmethod
    def read_subeditor(cls, subeditor: QSpinBox) -> int:
        return subeditor.value()


class EnumValueLabelFactory(AbstractEnumValueSubEditorFactory[QLineEdit, str]):
    """Factory that manages widgets for the "Label" editor of the enum."""

    @classmethod
    def create_subeditor(cls, slot: Callable) -> QLineEdit:
        subeditor = QLineEdit()
        subeditor.setStyleSheet('background: transparent')
        subeditor.setPlaceholderText('Type value here...')
        subeditor.setAlignment(Qt.AlignCenter)
        subeditor.setFrame(False)
        subeditor.editingFinished.connect(slot)
        return subeditor

    @classmethod
    def populate_subeditor(cls, subeditor: QLineEdit, value: str):
        subeditor.setText(value)

    @classmethod
    def read_subeditor(cls, subeditor: QLineEdit) -> str:
        return subeditor.text()


class EnumValueMeaningFactory(AbstractEnumValueSubEditorFactory[QComboBox, CEnumValue.Meaning]):
    """Factory that manages widgets for the "Meaning" editor of the enum."""

    @classmethod
    def create_subeditor(cls, slot: Callable) -> QComboBox:
        subeditor = QComboBox()
        for mean_opt in CEnumValue.Meaning:
            subeditor.addItem(str(mean_opt).split('.')[-1].title(), mean_opt.value)
        subeditor.activated.connect(slot)
        return subeditor

    @classmethod
    def populate_subeditor(cls, subeditor: QComboBox, value: CEnumValue.Meaning):
        combo_idx = subeditor.findData(value.value)
        if combo_idx != -1:
            subeditor.setCurrentIndex(combo_idx)

    @classmethod
    def read_subeditor(cls, subeditor: QComboBox) -> CEnumValue.Meaning:
        return subeditor.currentData()


class EnumValueColumnDelegate(QStyledItemDelegate):
    """
    Delegate to render the dynamic widget in the cell based on the "Enum field name" selected option.
    """

    # Ordering so that insertWidget does not overflow index and fallback to a different index
    FACTORIES: Dict[int, Type[AbstractEnumValueSubEditorFactory]] = OrderedDict([
        (CEnumRule.EnumField.CODE.value, EnumValueCodeFactory),
        (CEnumRule.EnumField.LABEL.value, EnumValueLabelFactory),
        (CEnumRule.EnumField.MEANING.value, EnumValueMeaningFactory),
    ])

    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex) -> QWidget:
        editor = QStackedWidget(parent)
        for idx, factory in self.FACTORIES.items():
            editor.insertWidget(idx, factory.create_subeditor(self._value_changed))
        setattr(editor, _STYLED_ITEM_DELEGATE_INDEX, QPersistentModelIndex(index))
        return editor

    def setEditorData(self, editor: QStackedWidget, index: QModelIndex):
        if not isinstance(editor, QStackedWidget):
            return
        if index != getattr(editor, _STYLED_ITEM_DELEGATE_INDEX, None):
            setattr(editor, _STYLED_ITEM_DELEGATE_INDEX, QPersistentModelIndex(index))
        try:
            field_type = self._get_field_type(index)
        except ValueError:
            return
        editor.setCurrentIndex(field_type.value)
        subeditor = editor.widget(field_type.value)
        if not subeditor:
            return
        value = index.data()
        factory = self.FACTORIES[field_type]
        factory.populate_subeditor(subeditor, value)

    def setModelData(self, editor: QStackedWidget, model: QAbstractTableModel, index: QModelIndex):
        if not isinstance(editor, QStackedWidget):
            return
        try:
            field_type = self._get_field_type(index)
        except ValueError:
            return
        factory = self.FACTORIES[field_type]
        subeditor = editor.widget(field_type)
        if not subeditor:
            return
        value = factory.read_subeditor(subeditor)
        model.setData(index, value)

    def displayText(self, value: Any, locale: QLocale) -> str:
        # Make sure that transparent button does not expose set label underneath
        return ''

    def _get_field_type(self, index: QModelIndex) -> CEnumRule.EnumField:
        prev_col = index.siblingAtColumn(index.column() - 1)

        # This will produce ValueError if unknown enum option. So be prepared
        return CEnumRule.EnumField(prev_col.data())

    def _value_changed(self):
        subeditor = self.sender()
        editor = subeditor.parent()
        index: Optional[QPersistentModelIndex] = getattr(editor, _STYLED_ITEM_DELEGATE_INDEX, None)
        if not index or not index.isValid():
            return
        self.setModelData(editor, index.model(), QModelIndex(index))


class EnumTableModel(AbstractTableModel[CEnumRule.EnumConfig]):
    """
    Table model that works with enum rule table.
    """

    def column_name(self, section: int) -> str:
        if section == 1:
            return 'Enum field name'
        else:
            return 'Enum field value'

    def columnCount(self, parent: Optional[QModelIndex] = None) -> int:
        return 3

    def create_row_item(self) -> CEnumRule.EnumConfig:
        return CEnumRule.EnumConfig(field=CEnumRule.EnumField.CODE, field_val=0, prop_val='')

    def get_cell_data(self, index: QModelIndex, row: CEnumRule.EnumConfig) -> Any:
        return row.field if index.column() == 1 else row.field_val

    def set_cell_data(self, index: QModelIndex, row: CEnumRule.EnumConfig, value: Any) -> bool:
        col = index.column()
        if col == 2:
            if row.field == CEnumRule.EnumField.MEANING:
                row.field_val = CEnumValue.Meaning(value)
            else:
                row.field_val = value
            return True
        elif col == 1:
            new_type = CEnumRule.EnumField(value)
            if row.field != new_type:
                row.field = new_type
                new_field_val: Union[None, int, str, CEnumValue.Meaning] = None
                if new_type == CEnumRule.EnumField.MEANING:
                    if not isinstance(row.field_val, CEnumValue.Meaning):
                        new_field_val = CEnumValue.Meaning.NONE
                elif new_type == CEnumRule.EnumField.CODE and (not isinstance(row.field_val, int)
                                                               or isinstance(row.field_val, CEnumValue.Meaning)):
                    # Additional check for CEnumValue.Meaning battles indifference when switching from Meaning
                    # to Code, which does not update the field value cell
                    new_field_val = 0
                elif new_type == CEnumRule.EnumField.LABEL and not isinstance(row.field_val, str):
                    new_field_val = ''
                if new_field_val is not None:
                    # Doing it through the model API, so that table gets re-rendered
                    next_col = index.siblingAtColumn(col + 1)
                    self.setData(next_col, new_field_val)
                return True
        return False


class EnumDetailsView(AbstractTableDetailsView[CEnumRule, CEnumRule.EnumConfig]):

    MODEL_CLASS = EnumTableModel
    ITEM_DELEGATES = {
        1: EnumFieldColumnDelegate,
        2: EnumValueColumnDelegate,
    }
    RULE_TYPE = CBaseRule.Type.ENUM

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Concrete implementation of the details view that works with :class:`CEnumRule.EnumConfig` tables.

        Args:
            parent: Parent owner.
        """
        super().__init__(parent)
        self.decl_table.set_persistent_editor_for_column(2)

    def _configure_table(self, rule_prop: CBaseRule.Property):
        super()._configure_table(rule_prop)
        self.decl_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)


class RulesEditorModel(BaseListModel[CBaseRule], QAbstractListModel, JsonModelMixin):

    def __init__(self, data: List[CBaseRule], default_prop: str, parent: Optional[QObject] = None):
        """
        Global model for the whole of editor dialog. It manages the list of rules of the widget.

        Args:
            data: Initial data.
            default_prop: Default "Property" that should be selected for new rules.
                          This setting is defined by the widget.
            parent: Owning object.
        """
        BaseListModel.__init__(self, data=data)
        QAbstractListModel.__init__(self, parent)
        JsonModelMixin.__init__(self)
        self._default_prop = default_prop

    def create_row(self) -> CBaseRule:
        return CNumRangeRule(name='New Rule',
                             prop=self._default_prop,
                             channel=CBaseRule.Channel.DEFAULT)

    def validate(self):
        for rule in self._data:
            rule.validate()


class RuleNameProxyModel(QIdentityProxyModel):
    """Proxy model used for the sidebar, that exposes only the name of the rule."""

    def data(self, index: QModelIndex, role: Qt.ItemDataRole = Qt.DisplayRole) -> Any:
        rule = self.sourceModel().data(index, role)
        if isinstance(rule, CBaseRule):
            return rule.name
        return QVariant()


class CurrentRuleSelectionModel(QItemSelectionModel):

    def __init__(self, prop_map: CWidgetRuleMap, model: QAbstractListModel, parent: Optional[QObject] = None):
        """
        Selection model that allows manipulating currently selected rule.
        It always assumes that only one item can be selected (as should be configured by the sidebar :class:`QListView`.

        It is set as the selection model of the aforementioned view, and thus is directly related to
        :class:`RuleNameProxyModel`, however often we want to modify more than just the rule name, therefore, it
        reaches the original model to propagate the data.

        Args:
            prop_map: Mapping between property names and base types. This is used to detect the change in the underlying
                      base type, when switching "Property" and only then wipe out the configuraiton of the rule.
            model: Related model.
            parent: Owning object.
        """
        super().__init__(model, parent)
        self._prop_map = prop_map

    @property
    def current_rule(self) -> Optional[CBaseRule]:
        """Currently selected rule or ``None`` if no selection exists."""
        try:
            index = self._current_row
        except IndexError:
            return None
        return self._orig_model.data(index)

    def set_rule_name(self, name: str):
        """
        Update the name of the current rule.

        Args:
            name: New name.
        """
        curr_rule = self.current_rule
        if curr_rule:
            curr_rule.name = name
            # We do not use _set_current_rule here to not notify all of the views to re-render, as it's expensive
            # We just want sidebar to re-render, thus notifying only the related model
            index = self.model().index(self._current_row.row(), 0)
            self.model().dataChanged.emit(index, index)

    def set_rule_channel(self, channel: Union[str, CBaseRule.Channel]):
        """
        Update the channel of the current rule.

        Args:
            channel: New channel.
        """
        curr_rule = self.current_rule
        if curr_rule:
            curr_rule.channel = channel
            if isinstance(channel, CBaseRule.Channel):
                curr_rule.selector = None

    def set_rule_selector(self, selector: Optional[str]):
        """
        Update the selector of the current rule.

        Args:
            channel: New channel.
        """
        curr_rule = self.current_rule
        if curr_rule:
            curr_rule.selector = selector

    def set_rule_property(self, prop: str):
        """
        Update the property of the current rule.

        Args:
            prop: New property.
        """
        curr_rule = self.current_rule
        if not curr_rule:
            return
        _, __, new_base_type = self._prop_map[prop]
        _, __, prev_base_type = self._prop_map[curr_rule.prop]

        curr_rule.prop = prop

        # We do not notify view, if base type hasn't changed, because
        # UI stays the same in that case.
        if new_base_type != prev_base_type:
            table_prop = _TABLE_RULE_ATTR_NAME.get(type(curr_rule), None)
            if table_prop:
                # Reset the table contents because they should not be directly
                # applied to the new type.
                getattr(curr_rule, table_prop, []).clear()  # Do not allocate new, but clean existing
            self._set_current_rule(curr_rule)

    def replace_current_rule(self, new_type: Type[CBaseRule]):
        """
        Replace current rule with the new type. This happens when we change "Evaluation type", thus changing
        the rule class completely.

        Args:
            new_type: New rule class.
        """
        curr_rule = self.current_rule
        if curr_rule:
            new_rule = new_type(name=curr_rule.name,
                                prop=curr_rule.prop,
                                selector=curr_rule.selector,
                                channel=curr_rule.channel)
            self._set_current_rule(new_rule)

    def remove_current_rule(self):
        """Delete currently selected rule from the list."""
        try:
            curr_idx = self._current_row
        except IndexError:
            return
        self._orig_model.remove_row_at_index(self._orig_model.index(curr_idx.row()))

    def select_first(self):
        """Select the first row if possible."""
        if self._orig_model.rowCount() > 0:
            index = self._orig_model.createIndex(0, 0)
            self.select(index, self.Select)

    @property
    def _orig_model(self) -> RulesEditorModel:
        return cast(QAbstractProxyModel, self.model()).sourceModel()

    @property
    def _current_row(self) -> QModelIndex:
        return self.selectedIndexes()[0]

    def _set_current_rule(self, rule: CBaseRule):
        try:
            index = self._orig_model.index(self._current_row.row())
        except IndexError:
            return
        self._orig_model.setData(index, rule)


class RulesEditor(QDialog):

    rule_updated = Signal(CBaseRule, int)
    """Rule has been updated and details view should react accordingly."""

    rule_closed = Signal()
    """Rule selection has changed, and no rule is currently selected. Details view should clear itself."""

    def __init__(self, widget: Union[QWidget, CWidgetRulesMixin], parent: Optional[QWidget] = None):
        """
        Editor dialog for rules in Qt Designer.

        Args:
            widget: The widget that holds the rules to be edited.
            parent: Parent owner to hold the reference to the dialog object.
        """
        super().__init__(parent)

        self.rules_add_btn: QPushButton = None
        self.rules_del_btn: QPushButton = None
        self.sidebar_list: QListView = None
        self.prop_combobox: QComboBox = None
        self.rule_name_edit: QLineEdit = None
        self.default_channel_checkbox: QCheckBox = None
        self.custom_channel_frame: QFrame = None
        self.custom_channel_edit: DevicePropertyLineEdit = None  # type: ignore
        self.custom_selector_btn: QPushButton = None
        self.custom_selector_edit: QLineEdit = None
        self.eval_type_combobox: QComboBox = None
        self.eval_stack_widget: QStackedWidget = None
        self.page_ranges: QWidget = None
        self.page_python: QWidget = None
        self.page_enum: QWidget = None
        self.btn_box: QDialogButtonBox = None
        self.base_type_frame: QFrame = None
        self.base_type_lbl: QLabel = None
        self.details_frame: QFrame = None

        loadUi(Path(__file__).parent / 'rules_editor.ui', self)

        # Fix layout, because QWidget placeholder does not have a layout in rules_editor.ui
        # FIXME: Does not help
        # self.custom_channel_frame.layout().invalidate()

        self.rules_add_btn.setIcon(IconFont().icon('plus'))
        self.rules_del_btn.setIcon(IconFont().icon('minus'))

        font = QFont('Monospace')
        font.setStyleHint(QFont.TypeWriter)
        self.details_frame.setEnabled(False)
        self.base_type_lbl.setFont(font)
        self.base_type_frame.setHidden(True)
        self.default_channel_checkbox.setChecked(True)
        self.custom_channel_frame.setHidden(True)

        self._widget = widget

        rules = cast(str, widget.rules)  # In Qt Designer it's going to be JSON-encoded string
        parsed_rules: List[CBaseRule]
        if rules is None:
            parsed_rules = []
        else:
            logger.debug(f'Loading rules for {cast(QWidget, widget).objectName()} into the editor: {rules}')
            parsed_rules = unpack_rules(rules)

        self.prop_combobox.addItems(widget.RULE_PROPERTIES.keys())

        self.eval_type_combobox.addItem('Numeric ranges', CBaseRule.Type.NUM_RANGE.value)
        # self.eval_type.addItem('Python expression', CBaseRule.Type.PY_EXPR) # TODO: Uncomment when python ready
        self.eval_type_combobox.addItem('Enumerations', CBaseRule.Type.ENUM.value)

        self.default_channel_checkbox.clicked.connect(self._custom_channel_changed)
        self.custom_channel_edit.address_changed.connect(self._custom_channel_changed)
        self.custom_selector_btn.clicked.connect(self._search_selector)
        self.custom_selector_edit.textEdited.connect(self._custom_selector_changed)
        self.rules_del_btn.clicked.connect(self._del_rule)
        self.btn_box.button(QDialogButtonBox.Apply).clicked.connect(self._save_changes)
        self.btn_box.rejected.connect(self.close)

        self._model = RulesEditorModel(data=parsed_rules, default_prop=widget.DEFAULT_RULE_PROPERTY, parent=self)
        self._sidebar_model = RuleNameProxyModel(self)
        self._sidebar_model.setSourceModel(self._model)
        self._selection_model = CurrentRuleSelectionModel(prop_map=widget.RULE_PROPERTIES, model=self._sidebar_model, parent=self)
        self.rule_name_edit.textEdited.connect(self._selection_model.set_rule_name)
        self.prop_combobox.currentTextChanged.connect(self._selection_model.set_rule_property)
        self.eval_type_combobox.currentIndexChanged.connect(self._eval_type_changed)
        self.sidebar_list.setModel(self._sidebar_model)
        self.sidebar_list.setSelectionModel(self._selection_model)
        self._selection_model.selectionChanged.connect(self._set_rule_details)
        self._model.dataChanged.connect(self._set_rule_details)
        self.rules_add_btn.clicked.connect(self._model.append_row)

        for page in range(self.eval_stack_widget.count()):
            eval_widget = self.eval_stack_widget.widget(page)
            try:
                eval_widget.property_map = widget.RULE_PROPERTIES
            except AttributeError:
                pass
            try:
                self.rule_updated.connect(eval_widget.set_rule)
            except AttributeError:
                pass
            try:
                self.rule_closed.connect(eval_widget.clear)
            except AttributeError:
                pass

    def showEvent(self, event: QShowEvent):
        super().showEvent(event)

        # Pre-select the first rule by default
        if not self._selection_model.hasSelection():
            self._selection_model.select_first()

    def _search_channel(self):
        curr_rule = self._selection_model.current_rule
        if not curr_rule:
            return

        dialog = DevicePropertyDialog(addr=curr_rule.channel)
        if dialog.exec_() == QDialog.Accepted:
            self._selection_model.set_rule_channel(dialog.address or None)
        self._set_rule_details()  # Update UI

    def _search_selector(self):
        curr_rule = self._selection_model.current_rule
        if not curr_rule:
            return
        if curr_rule.selector is None:
            config = PLSSelectorConfig.no_selector()
        else:
            try:
                machine, group, line = tuple(curr_rule.selector.split('.'))
                config = PLSSelectorConfig(machine=machine,
                                           group=group,
                                           line=line)
            except ValueError:
                config = PLSSelectorConfig.no_selector()
        dialog = PLSSelectorDialog(config=config, parent=self)
        # dialog.selector_selected.connect(self._custom_selector_changed)
        dialog.selector_selected.connect(self.custom_selector_edit.setText)
        dialog.exec_()

    def _del_rule(self):
        curr_rule = self._selection_model.current_rule
        if not curr_rule:
            return

        reply = QMessageBox().question(self,
                                       'Message',
                                       f'Are you sure you want to delete rule "{curr_rule.name}"?',
                                       QMessageBox.Yes,
                                       QMessageBox.No)

        if reply == QMessageBox.Yes:
            self._selection_model.remove_current_rule()

    def _save_changes(self):
        open_rule = self._selection_model.current_rule
        if (open_rule is not None and isinstance(open_rule, (CNumRangeRule, CEnumRule))
                and not self.eval_stack_widget.currentWidget().json_edit.valid):
            QMessageBox.critical(self,
                                 'Error Saving',
                                 f'Fix JSON in the rule "{open_rule.name}" before saving',
                                 QMessageBox.Ok)
            return

        try:
            self._model.validate()
        except TypeError as e:
            QMessageBox.critical(self, 'Error Saving', os.linesep.join(str(e).split(';')), QMessageBox.Ok)
            return

        cursor = get_designer_cursor(self._widget)
        if cursor:
            cursor.setProperty('rules', self._model.to_json())
        self.accept()

    def _eval_type_changed(self):
        eval_type = self.sender().currentData()
        new_rule_type = CBaseRule.Type.rule_map()[CBaseRule.Type(eval_type)]
        self._selection_model.replace_current_rule(new_rule_type)

    def _custom_channel_changed(self):
        uses_default = self.default_channel_checkbox.isChecked()
        self.custom_channel_frame.setHidden(uses_default)
        new_channel = CBaseRule.Channel.DEFAULT if uses_default else self.custom_channel_edit.address
        self._selection_model.set_rule_channel(new_channel)

    def _custom_selector_changed(self, selector: str):
        self._selection_model.set_rule_selector(selector or None)

    def _set_rule_details(self):
        rule = self._selection_model.current_rule
        rule_exists = rule is not None
        self.details_frame.setEnabled(rule_exists)
        if rule_exists:
            self.rule_name_edit.setText(rule.name)
            rule_prop = rule.prop
            self.prop_combobox.setCurrentText(rule_prop)
            rule_type = rule.type()
            eval_idx = self.eval_type_combobox.findData(rule_type.value)
            if eval_idx != -1:
                # We don't use "activated" and instead "currentIndexChanged" to not fire on the same option
                # but for that we need to block the signals to avoid a loop
                blocker = QSignalBlocker(self.eval_type_combobox)
                self.eval_type_combobox.setCurrentIndex(eval_idx)
                blocker.unblock()
            self.eval_stack_widget.setCurrentIndex(rule_type)
            is_default_channel = rule.channel == CBaseRule.Channel.DEFAULT
            self.default_channel_checkbox.setChecked(is_default_channel)
            self.custom_channel_frame.setHidden(is_default_channel)
            if is_default_channel:
                self.custom_channel_edit.clear()
                self.custom_selector_edit.clear()
            else:
                blocker = QSignalBlocker(self.custom_channel_edit)
                self.custom_channel_edit.address = rule.channel
                blocker.unblock()
                self.custom_selector_edit.setText(rule.selector)

            self.base_type_frame.setHidden(False)
            _, __, base_type = self._widget.RULE_PROPERTIES[rule.prop]
            self.base_type_lbl.setText(base_type.__name__)

            self.rule_updated.emit(rule, rule_type.value)
        else:
            self.rule_name_edit.clear()
            self.prop_combobox.setCurrentIndex(0)
            self.eval_type_combobox.setCurrentIndex(0)
            self.eval_stack_widget.setCurrentIndex(0)
            self.default_channel_checkbox.setChecked(True)
            self.custom_channel_frame.setHidden(True)
            self.base_type_frame.setHidden(True)
            self.rule_closed.emit()


_TABLE_RULE_ATTR_NAME = {
    CNumRangeRule: 'ranges',
    CEnumRule: 'config',
}
