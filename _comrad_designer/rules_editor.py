import os
import functools
import logging
import json
from abc import abstractmethod
from pathlib import Path
from typing import Optional, Union, cast, Type, Callable, List, Generic, TypeVar, Any
from pydm.utilities.iconfont import IconFont
from PyQt5.Qsci import QsciScintilla, QsciLexerJSON
from qtpy.QtWidgets import (QDialog, QWidget, QHBoxLayout, QFrame, QColorDialog, QToolButton, QSpacerItem,
                            QPushButton, QListWidget, QSizePolicy, QListWidgetItem, QTabWidget,
                            QLabel, QLineEdit, QComboBox, QTableWidget, QStackedWidget, QSpinBox,
                            QHeaderView, QCheckBox, QDialogButtonBox, QMessageBox)
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QFont
from qtpy.QtDesigner import QDesignerFormWindowInterface
from qtpy.uic import loadUi
from comrad.rules import CBaseRule, CNumRangeRule, CEnumRule, CExpressionRule, unpack_rules
from comrad.qsci import configure_common_qsci, QSCI_INDENTATION
from comrad.json import CJSONEncoder, CJSONDeserializeError
from comrad.widgets.mixins import CWidgetRulesMixin
from comrad.data.japc_enum import CEnumValue
from comrad.generics import GenericQObjectMeta


logger = logging.getLogger(__name__)


R = TypeVar('R', bound=CBaseRule)
S = TypeVar('S', CNumRangeRule.Range, CEnumRule.EnumConfig)


# FIXME: This is quite ugly. Didn figure out how to make model-based tables render nicely.
class TableDetailsView(QWidget, Generic[R, S], metaclass=GenericQObjectMeta):

    TAB_DECLARATIVE_VIEW: int = 0
    TAB_SOURCE_VIEW: int = 1

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Base class for rule details, that are based on table view.

        Args:
            parent: Parent owner.
        """
        super().__init__(parent)
        self._loading_data: bool = True
        self.get_current_rule: Callable[[], CBaseRule]  # lambda to be assigned from the outside
        self.get_prop_combo: Callable[[], QComboBox]  # lambda to be assigned from the outside. This is very much temporary
        self.get_widget: Callable[[], QWidget]  # lambda to be assigned from the outside. This is very much temporary

        self.add_btn: QPushButton = None
        self.del_btn: QPushButton = None
        self.decl_table: QTableWidget = None
        self.tabs: QTabWidget = None
        self.src_edit: QsciScintilla = None

        loadUi(Path(__file__).parent / 'rules_table.ui', self)

        self.add_btn.setIcon(IconFont().icon('plus'))
        self.del_btn.setIcon(IconFont().icon('minus'))

        column_count = self.column_count
        self.decl_table.setColumnCount(column_count)
        self.decl_table.setHorizontalHeaderLabels(['Property value'] + [self.column_name(idx) for idx in range(1, column_count)])

        header = self.decl_table.horizontalHeader()
        for idx in range(column_count - 1):
            # Avoids squashed view on column titles when the table is empty
            header.setResizeMode(idx, QHeaderView.ResizeToContents)

        lexer = QsciLexerJSON(self.src_edit)
        self.src_edit.setLexer(lexer)
        configure_common_qsci(self.src_edit)
        self.src_edit.setReadOnly(False)

        self._src_valid: bool = True

        self.add_btn.clicked.connect(self._add_row)
        self.del_btn.clicked.connect(self._del_row)
        self.tabs.currentChanged.connect(lambda idx: self.populate(idx))
        self.src_edit.textChanged.connect(self._src_edit_updated)

    @property
    def current_rule(self) -> R:
        return self.get_current_rule()  # type: ignore

    @property
    @abstractmethod
    def column_count(self) -> int:
        pass

    @abstractmethod
    def column_name(self, idx: int) -> str:
        pass

    @property
    @abstractmethod
    def rule_src_attr(self) -> str:
        pass

    @abstractmethod
    def make_config_widget(self, column: int, row: int, setting: S) -> QWidget:
        pass

    @abstractmethod
    def create_new_row(self) -> S:
        pass

    def populate(self, idx: Optional[int] = None):
        if idx is None:
            idx = self.tabs.currentIndex()

        if idx == self.TAB_DECLARATIVE_VIEW:
            self._populate_decl_table()
        elif idx == self.TAB_SOURCE_VIEW:
            self._update_src_edit()
        else:
            raise ValueError(f'Unsupported tab index: {idx}')

    @property
    def data_valid(self) -> bool:
        return not (self.tabs.currentIndex() == self.TAB_SOURCE_VIEW and not self._src_valid)

    def clear(self):
        self._loading_data = True
        self._clear_table()
        self.src_edit.clear()
        self._loading_data = False

    def _update_src_edit(self):
        self._loading_data = True
        self.src_edit.setText(json.dumps(getattr(self.current_rule, self.rule_src_attr),
                                         cls=CJSONEncoder,
                                         indent=QSCI_INDENTATION))
        self._loading_data = False
        self._src_valid = True

    def _add_row(self):
        try:
            rule = self.current_rule
        except IndexError:
            raise RuntimeError('Cannot create a dynamic widget for a non-existing rule')

        self._loading_data = True

        self.decl_table.insertRow(self.decl_table.rowCount())
        row = self.decl_table.rowCount() - 1
        self.decl_table.setCellWidget(row, 0, self._get_dynamic_setting_item(row))

        setting = getattr(rule, self.rule_src_attr)[row]
        for col in range(1, self.column_count):
            self.decl_table.setCellWidget(row, col, self.make_config_widget(col, row, setting))
        row_labels = [f' {x} ' for x in range(self.decl_table.rowCount())]
        self.decl_table.setVerticalHeaderLabels(row_labels)
        self._loading_data = False

    def _del_row(self):
        items = self.decl_table.selectionModel().selectedRows(0)
        if len(items) == 0:
            return

        # Ask for permission only for multiple rows deletion
        if len(items) > 1:
            reply = QMessageBox().question(self,
                                           'Message',
                                           'Delete selected rows?',
                                           QMessageBox.Yes,
                                           QMessageBox.No)

            if reply != QMessageBox.Yes:
                return

        self._loading_data = True
        try:
            rule = self.current_rule
        except IndexError:
            self._loading_data = False
            raise RuntimeError('Cannot create a dynamic setting for a non-existing rule')

        settings_list = getattr(rule, self.rule_src_attr)
        for itm in reversed(items):
            row = itm.row()
            self.decl_table.removeRow(row)
            del settings_list[row]
        self._loading_data = False

    def _get_dynamic_setting_item(self,
                                  row: int,
                                  type_name: Optional[str] = None,
                                  prop_name: Optional[str] = None,
                                  current_setting: Optional[S] = None):
        if not prop_name:
            prop_name = self.get_prop_combo().currentText()

        if not type_name:
            prop = self.get_prop_combo().currentData()
            type_name = prop[1].__name__

        try:
            rule = self.current_rule
        except IndexError:
            raise RuntimeError('Cannot create a dynamic setting for a non-existing rule')

        if not current_setting:
            settings_list = getattr(rule, self.rule_src_attr)
            try:
                current_setting = settings_list[row]
            except IndexError:
                current_setting = self.create_new_row()
                settings_list.append(current_setting)

        def ensure_setting(setting: S, default: Any, caster: Callable) -> Any:
            if setting.prop_val is None or (caster == str and not setting.prop_val):  # type: ignore  # Treat empty strings as None
                value = default
                setting.prop_val = value
            else:
                value = caster(setting.prop_val)
            return value

        if type_name == 'bool':
            bool_val: bool = ensure_setting(cast(S, current_setting), default=(row == 0), caster=bool)
            value: Qt.CheckState = Qt.Checked if bool_val else Qt.Unchecked
            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            checkbox = QCheckBox()
            checkbox.setCheckState(value)
            checkbox.setAttribute(Qt.WA_TransparentForMouseEvents)
            checkbox.stateChanged.connect(functools.partial(self._edit_value_changed, row_idx=row, caster=bool))
            btn = QToolButton()
            btn.setAutoRaise(True)
            btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
            btn.clicked.connect(checkbox.toggle)
            layout.addSpacerItem(QSpacerItem(10, 1, QSizePolicy.Expanding, QSizePolicy.Preferred))
            layout.addWidget(checkbox)
            layout.addSpacerItem(QSpacerItem(10, 1, QSizePolicy.Expanding, QSizePolicy.Preferred))
            btn.setLayout(layout)
            return btn
        elif prop_name == 'Color':
            value = ensure_setting(cast(S, current_setting), default='#000000', caster=str)
            layout = QHBoxLayout()
            layout.setContentsMargins(5, 0, 0, 0)
            icon = QFrame()
            icon.setFrameStyle(QFrame.Box)
            icon.setStyleSheet(f'background-color: {value}')
            icon.resize(10, 10)
            icon.setMinimumSize(10, 10)
            icon.setMaximumSize(10, 10)
            font = QFont('Monospace')
            font.setStyleHint(QFont.TypeWriter)
            btn = QToolButton()
            btn.setFont(font)
            btn.setText(value.upper())
            btn.setAutoRaise(True)
            btn.row_idx = row
            btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
            btn.clicked.connect(self._open_color_dialog)
            layout.addWidget(icon)
            layout.addSpacerItem(QSpacerItem(10, 1, QSizePolicy.Expanding, QSizePolicy.Preferred))
            btn.setLayout(layout)
            return btn
        else:
            if type_name == 'int':
                value = ensure_setting(cast(S, current_setting), default=0, caster=int)
            elif type_name == 'float':
                value = ensure_setting(cast(S, current_setting), default=0.0, caster=float)
            else:
                raise TypeError(f'Unsupported property type: {type_name}')

            widget = QLineEdit()
            widget.setStyleSheet('background: transparent')
            widget.setPlaceholderText(f'Type {type_name} value...')
            widget.setAlignment(Qt.AlignCenter)
            widget.setFrame(False)
            widget.setText(str(value))
            widget.textChanged.connect(functools.partial(self._edit_value_changed, row_idx=row, caster=int))
            return widget

    def _open_color_dialog(self):
        rule = self.current_rule
        setting = getattr(rule, self.rule_src_attr)[self.sender().row_idx]
        value = setting.prop_val
        new_color = QColorDialog.getColor(QColor(value))
        if not new_color.isValid():
            # User cancelled the selection
            return
        setting.prop_val = new_color.name()
        self._reload_table()

    def _edit_value_changed(self, caster: Callable, row_idx: int, new_val: str):
        rule = self.current_rule
        setting = getattr(rule, self.rule_src_attr)[row_idx]
        try:
            setting.prop_val = caster(new_val)
        except ValueError:
            pass

    def _reload_table(self):
        for i in range(self.decl_table.rowCount()):
            self.decl_table.setCellWidget(i, 0, self._get_dynamic_setting_item(i))

    def _clear_table(self):
        for _ in range(self.decl_table.rowCount()):
            self.decl_table.removeRow(0)

    def _populate_decl_table(self):
        self.decl_table.clearContents()
        rule = self.current_rule
        settings = getattr(rule, self.rule_src_attr)
        self.decl_table.setRowCount(len(settings))
        row_labels = [f' {x} ' for x in range(len(settings))]
        self.decl_table.setVerticalHeaderLabels(row_labels)
        _, base_type = self.get_widget().RULE_PROPERTIES[rule.prop]
        type_name = cast(Type, base_type).__name__
        for row_idx, rule_setting in enumerate(settings):
            self.decl_table.setCellWidget(row_idx, 0, self._get_dynamic_setting_item(row=row_idx,
                                                                                     type_name=type_name,
                                                                                     prop_name=rule.prop,
                                                                                     current_setting=rule_setting))
            for col_idx in range(1, self.column_count):
                self.decl_table.setCellWidget(row_idx, col_idx, self.make_config_widget(col_idx, row_idx, rule_setting))

    def _src_edit_updated(self):
        if self._loading_data:
            return
        try:
            contents = json.loads(self.src_edit.text())
            if not isinstance(contents, list):
                raise CJSONDeserializeError(f'Expected list of rules, got {type(contents).__name__}', None, 0)
            deserializer = type(self.create_new_row()).from_json  # A little costly, but whatever
            setattr(self.current_rule, self.rule_src_attr, list(map(deserializer, contents)))
        except (CJSONDeserializeError, json.JSONDecodeError):
            self._src_valid = False
            return
        self._src_valid = True


class EnumDetailsView(TableDetailsView[CEnumRule, CEnumRule.EnumConfig]):

    @property
    def column_count(self) -> int:
        return 3

    def column_name(self, idx: int) -> str:
        if idx == 1:
            return 'Enum field name'
        else:
            return 'Enum field value'

    @property
    def rule_src_attr(self) -> str:
        return 'config'

    def create_new_row(self) -> CEnumRule.EnumConfig:
        return CEnumRule.EnumConfig(field=CEnumRule.EnumField.CODE, field_val=0, prop_val='')

    def make_config_widget(self, column: int, row: int, setting: CEnumRule.EnumConfig) -> QWidget:
        if column == 1:
            combo = QComboBox()
            current_row = 0
            for idx, field_opt in enumerate(CEnumRule.EnumField):
                combo.addItem(str(field_opt).split('.')[-1].title(), (row, field_opt.value))
                if field_opt == setting.field:
                    current_row = idx
            combo.setCurrentIndex(current_row)
            combo.currentIndexChanged.connect(self._enum_option_changed)
            return combo
        elif setting.field == CEnumRule.EnumField.MEANING:
            combo = QComboBox()
            current_row = 0
            for idx, mean_opt in enumerate(CEnumValue.Meaning):
                combo.addItem(str(mean_opt).split('.')[-1].title(), (row, mean_opt.value))
                if mean_opt == setting.field_val:
                    current_row = idx
            combo.setCurrentIndex(current_row)
            combo.currentIndexChanged.connect(self._val_option_changed)
            return combo
        elif setting.field == CEnumRule.EnumField.CODE:
            box = QSpinBox()
            box.setStyleSheet('background: transparent')
            box.setValue(int(setting.field_val))
            box.row_idx = row
            box.valueChanged.connect(self._val_int_changed)
            return box
        else:
            edit = QLineEdit()
            edit.setStyleSheet('background: transparent')
            edit.setPlaceholderText('Type value here...')
            edit.setAlignment(Qt.AlignCenter)
            edit.setFrame(False)
            edit.row_idx = row
            edit.setText(str(setting.field_val))
            edit.textEdited.connect(self._val_edit_changed)
            return edit

    def _val_int_changed(self, val: int):
        rule = self.current_rule
        setting = getattr(rule, self.rule_src_attr)[self.sender().row_idx]
        setting.field_val = val

    def _val_edit_changed(self, new_val: str):
        rule = self.current_rule
        setting = getattr(rule, self.rule_src_attr)[self.sender().row_idx]
        setting.field_val = new_val

    def _val_option_changed(self, idx: int):
        combo = cast(QComboBox, self.sender())
        row, val = combo.itemData(idx)
        rule = self.current_rule
        settings = cast(List[CEnumRule.EnumConfig], getattr(rule, self.rule_src_attr))
        settings[row].field_val = CEnumValue.Meaning(val)

    def _enum_option_changed(self, idx: int):
        combo = cast(QComboBox, self.sender())
        row, val = combo.itemData(idx)
        rule = self.current_rule
        setting = cast(List[CEnumRule.EnumConfig], getattr(rule, self.rule_src_attr))[row]
        setting.field = CEnumRule.EnumField(val)
        curr_val = setting.field_val
        if setting.field == CEnumRule.EnumField.MEANING:
            if not isinstance(curr_val, CEnumValue.Meaning):
                setting.field_val = CEnumValue.Meaning.NONE
        elif setting.field == CEnumRule.EnumField.CODE and not isinstance(curr_val, int):
            setting.field_val = 0
        elif setting.field == CEnumRule.EnumField.LABEL and not isinstance(curr_val, str):
            setting.field_val = ''
        self._populate_decl_table()


class RangeDetailsView(TableDetailsView[CNumRangeRule, CNumRangeRule.Range]):

    @property
    def column_count(self) -> int:
        return 2

    def column_name(self, _: int) -> str:
        return 'Channel range value'

    @property
    def rule_src_attr(self) -> str:
        return 'ranges'

    def make_config_widget(self, _: int, row: int, setting: CNumRangeRule.Range) -> QWidget:

        def make_field(is_max: bool, h_align: int, text: float):
            field = QLineEdit()
            field.is_max = is_max
            field.row_idx = row
            field.setAlignment(h_align | Qt.AlignVCenter)
            field.setText(str(text))
            field.setStyleSheet('background: transparent')
            field.setFrame(False)
            field.textChanged.connect(self._range_changed)
            field.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            return field

        range_widget = QWidget()
        range_layout = QHBoxLayout()
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_layout.addWidget(make_field(is_max=False, h_align=Qt.AlignRight, text=setting.min_val))
        lbl = QLabel(' ≤ channel value < ')
        range_layout.addWidget(lbl)
        range_layout.addWidget(make_field(is_max=True, h_align=Qt.AlignLeft, text=setting.max_val))
        range_widget.setLayout(range_layout)
        return range_widget

    def create_new_row(self) -> CNumRangeRule.Range:
        return CNumRangeRule.Range(min_val=0.0, max_val=1.0, prop_val='')

    def _range_changed(self, new_val: str):
        rule = self.current_rule
        rule_range = rule.ranges[self.sender().row_idx]
        try:
            if self.sender().is_max:
                rule_range.max_val = float(new_val)
            else:
                rule_range.min_val = float(new_val)
        except ValueError:
            pass


class RulesEditor(QDialog):

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
        self.rules_list_widget: QListWidget = None
        self.prop_combobox: QComboBox = None
        self.rule_name_edit: QLineEdit = None
        self.default_channel_checkbox: QCheckBox = None
        self.custom_channel_frame: QFrame = None
        self.custom_channel_edit: QLineEdit = None
        self.custom_channel_search_btn: QPushButton = None
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

        self.rules_add_btn.setIcon(IconFont().icon('plus'))
        self.rules_del_btn.setIcon(IconFont().icon('minus'))

        self.custom_channel_search_btn.setIcon(IconFont().icon('search'))
        font = QFont('Monospace')
        font.setStyleHint(QFont.TypeWriter)
        self.base_type_lbl.setFont(font)
        self.base_type_frame.setHidden(True)

        self._widget = widget
        self._current_rule_item: Optional[QListWidgetItem] = None
        self._loading_data: bool = True

        rules = cast(str, widget.rules)  # In Qt Designer it's going to be JSON-encoded string
        self._rules: List[CBaseRule]
        if rules is None:
            self._rules = []
        else:
            logger.debug(f'Loading rules for {cast(QWidget, widget).objectName()} into the editor: {rules}')
            self._rules = unpack_rules(rules)

        for rule in self._rules:
            self.rules_list_widget.addItem(rule.name)

        for name, prop in widget.RULE_PROPERTIES.items():
            self.prop_combobox.addItem(name, prop)

        self.eval_type_combobox.addItem('Numeric ranges', CBaseRule.Type.NUM_RANGE.value)
        # self.eval_type.addItem('Python expression', CBaseRule.Type.PY_EXPR) # TODO: Uncomment when python ready
        self.eval_type_combobox.addItem('Enumerations', CBaseRule.Type.ENUM.value)

        self.default_channel_checkbox.stateChanged.connect(self._custom_channel_changed)
        self.custom_channel_edit.textChanged.connect(self._custom_channel_changed)
        self.custom_channel_search_btn.clicked.connect(self._search_channel)
        self.rules_add_btn.clicked.connect(self._add_rule)
        self.rules_del_btn.clicked.connect(self._del_rule)
        self.rules_list_widget.itemSelectionChanged.connect(self._load_from_list)
        self.btn_box.button(QDialogButtonBox.Apply).clicked.connect(self._save_changes)
        self.btn_box.rejected.connect(self.close)
        self.rule_name_edit.textChanged.connect(self._name_changed)
        self.prop_combobox.currentIndexChanged.connect(self._property_changed)
        self.eval_type_combobox.currentIndexChanged.connect(self._eval_type_changed)

        self._clear_form()

    def _search_channel(self):
        QMessageBox().information(self,
                                  'Work in progress...',
                                  'In the future, this will allow you to look up channel address from CCDB.',
                                  QMessageBox.Ok)

    def _add_rule(self):
        default_name = 'New Rule'
        default_prop = self._widget.DEFAULT_RULE_PROPERTY
        new_rule = CNumRangeRule(name=default_name,
                                 prop=default_prop,
                                 channel=CBaseRule.Channel.DEFAULT)
        self._rules.append(new_rule)
        self._current_rule_item = QListWidgetItem()
        self._current_rule_item.setText(default_name)
        self.rules_list_widget.addItem(self._current_rule_item)
        self.rules_list_widget.setCurrentItem(self._current_rule_item)
        self._load_from_list()
        self.rule_name_edit.setFocus()

    def _del_rule(self):
        idx = self._get_current_index()
        if idx < 0:
            return

        reply = QMessageBox().question(self,
                                       'Message',
                                       f'Are you sure you want to delete Rule: {self._current_rule_item.text()}?',
                                       QMessageBox.Yes,
                                       QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.rules_list_widget.takeItem(idx)
            self.rules_list_widget.clearSelection()
            self._rules.pop(idx)
            self._clear_form()

    def _name_changed(self):
        if not self._current_rule_item:
            # We may have blurred focus by this time already. Avoid crash
            return

        new_name = self.sender().text()
        self._current_rule_item.setText(new_name)
        self._get_current_rule().name = new_name

    def _load_from_list(self):
        item = self.rules_list_widget.currentItem()
        idx = self.rules_list_widget.indexFromItem(item).row()

        if idx < 0:
            return

        self._loading_data = True
        self._current_rule_item = item
        rule = self._rules[idx]
        self.rule_name_edit.setText(rule.name)
        rule_prop = rule.prop
        self.prop_combobox.setCurrentText(rule_prop)
        rule_type = rule.type()
        eval_idx = self.eval_type_combobox.findData(rule_type)
        if eval_idx != -1:
            self.eval_type_combobox.setCurrentIndex(eval_idx)
        self.eval_stack_widget.setCurrentIndex(rule_type)
        is_default_channel = rule.channel == CBaseRule.Channel.DEFAULT
        self.default_channel_checkbox.setChecked(is_default_channel)
        self.custom_channel_frame.setHidden(is_default_channel)
        if is_default_channel:
            self.custom_channel_edit.clear()
        else:
            self.custom_channel_edit.setText(rule.channel)

        if isinstance(rule, CExpressionRule):
            # TODO: Handle Python expression here
            #         if 'manual_rule' in data.keys():
            #             self.txt_expression.setText(self._get_entry(data, 'manual_rule.expression', ''))
            #             channels = self._get_entry(data, 'manual_rule.channels', [])
            #             self.tbl_channels.clearContents()
            #             self.tbl_channels.setRowCount(len(channels))
            #             vlabel = map(str, range(len(channels)))
            #             self.tbl_channels.setVerticalHeaderLabels(vlabel)
            #             for row, ch in enumerate(channels):
            #                 ch_name = ch.get('channel', '')
            #                 ch_tr = ch.get('trigger', False)
            #                 self.tbl_channels.setItem(row, 0,
            #                                           QtWidgets.QTableWidgetItem(str(ch_name)))
            #                 checkBoxItem = QtWidgets.QTableWidgetItem()
            #                 if ch_tr:
            #                     checkBoxItem.setCheckState(QtCore.Qt.Checked)
            #                 else:
            #                     checkBoxItem.setCheckState(QtCore.Qt.Unchecked)
            #                 self.tbl_channels.setItem(row, 1, checkBoxItem)
            pass
        elif isinstance(rule, (CNumRangeRule, CEnumRule)):
            self.table_view.get_current_rule = self._get_current_rule
            self.table_view.get_prop_combo = lambda: self.prop_combobox
            self.table_view.get_widget = lambda: self._widget
            self.table_view.populate()
        else:
            logger.exception(f'Unsupported rule type: {type(rule).__name__}')

        self._loading_data = False
        self._custom_channel_changed()
        self.details_frame.setEnabled(True)

    @property
    def table_view(self) -> TableDetailsView:
        return self.eval_stack_widget.currentWidget()

    def _save_changes(self):
        if self._get_current_index() != -1:
            if (isinstance(self._get_current_rule(), (CNumRangeRule, CEnumRule))
                    and not self.table_view.data_valid):
                QMessageBox.critical(self,
                                     'Error Saving',
                                     f'Rule "{self._get_current_rule().name}" has unfinished invalid source for ranges',
                                     QMessageBox.Ok)
                return

        for rule in self._rules:
            try:
                rule.validate()
            except TypeError as e:
                QMessageBox.critical(self, 'Error Saving', os.linesep.join(str(e).split(';')), QMessageBox.Ok)
                return

        # TODO: Maybe this could be shared for all dialogs that we're about to create for designer?
        form_window = QDesignerFormWindowInterface.findFormWindow(self._widget)
        if form_window:
            form_window.cursor().setProperty('rules', json.dumps(self._rules, cls=CJSONEncoder))
        self.accept()

    def _property_changed(self):
        try:
            text = self.prop_combobox.currentText()
            _, prop_type = self.prop_combobox.currentData()
        except TypeError:
            self.base_type_frame.setHidden(True)
            return

        try:
            curr_rule = self._get_current_rule()
        except IndexError:
            self.base_type_frame.setHidden(True)
            return

        prev_prop = curr_rule.prop
        curr_rule.prop = text

        type_name = cast(Type, prop_type).__name__
        self.base_type_lbl.setText(type_name)
        self.base_type_frame.setHidden(False)

        if isinstance(curr_rule, (CNumRangeRule, CEnumRule)):
            _, prev_prop_type = self._widget.RULE_PROPERTIES[prev_prop]
            if prop_type != prev_prop_type:
                # Clear the table because we can't map
                # different data types directly and it does not make sense
                getattr(curr_rule, self.table_view.rule_src_attr).clear()
                self.table_view.populate()

    def _eval_type_changed(self):
        eval_type: int = self.eval_type_combobox.currentData()
        if eval_type is None:
            return

        self.eval_stack_widget.setCurrentIndex(eval_type)
        curr_rule = self._get_current_rule()
        if eval_type == CBaseRule.Type.NUM_RANGE:
            new_rule = CNumRangeRule(name=curr_rule.name,
                                     prop=curr_rule.prop,
                                     channel=curr_rule.channel)
        elif eval_type == CBaseRule.Type.ENUM:
            new_rule = CEnumRule(name=curr_rule.name,
                                 prop=curr_rule.prop,
                                 channel=curr_rule.channel)
        else:
            raise NotImplementedError()
        idx = self._get_current_index()
        self._rules[idx] = new_rule
        self._load_from_list()

    def _custom_channel_changed(self):
        if self._loading_data:
            return
        uses_default = self.default_channel_checkbox.isChecked()
        if uses_default:
            self._get_current_rule().channel = CBaseRule.Channel.DEFAULT
        else:
            self._get_current_rule().channel = self.custom_channel_edit.text()
        self.custom_channel_frame.setHidden(uses_default)

    def _get_current_index(self) -> int:
        if self._current_rule_item is None:
            return -1
        return self.rules_list_widget.indexFromItem(self._current_rule_item).row()

    def _get_current_rule(self) -> CBaseRule:
        idx = self._get_current_index()
        return self._rules[idx]

    def _clear_form(self):
        self._loading_data = True
        self._current_rule_item = None
        self.rule_name_edit.setText('')
        self.prop_combobox.setCurrentIndex(-1)
        self.default_channel_checkbox.setChecked(True)
        self.table_view.get_current_rule = None
        self.table_view.get_prop_combo = None
        self.table_view.get_widget = None
        self.table_view.clear()
        self.details_frame.setEnabled(False)
        self._loading_data = False
