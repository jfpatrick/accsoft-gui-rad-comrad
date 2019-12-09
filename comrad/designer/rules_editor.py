import os
import sys
import functools
import logging
import json
from typing import Optional, Union, List, cast, Type, Callable
from pydm.utilities.iconfont import IconFont
from PyQt5.Qsci import QsciScintilla, QsciLexerJSON
from qtpy.QtWidgets import (QDialog, QWidget, QHBoxLayout, QFrame, QColorDialog, QToolButton, QSpacerItem,
                            QPushButton, QListWidget, QSizePolicy, QListWidgetItem,
                            QLabel, QLineEdit, QComboBox, QTableWidget, QStackedWidget,
                            QHeaderView, QCheckBox, QDialogButtonBox, QMessageBox)
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QFont
from qtpy.QtDesigner import QDesignerFormWindowInterface
from qtpy.uic import loadUi
from comrad.qt.rules import WidgetRulesMixin, RuleType, BaseRule, NumRangeRule, RuleRange, ExpressionRule
from comrad.qsci import configure_common_qsci, QSCI_INDENTATION
from comrad.json import ComRADJSONEncoder


logger = logging.getLogger(__name__)


class NewRulesEditor(QDialog):

    def __init__(self, widget: Union[QWidget, WidgetRulesMixin], parent: Optional[QWidget] = None):
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
        self.range_add_btn: QPushButton = None
        self.range_del_btn: QPushButton = None
        self.range_table: QTableWidget = None
        self.btn_box: QDialogButtonBox = None
        self.base_type_frame: QFrame = None
        self.base_type_lbl: QLabel = None
        self.details_frame: QFrame = None
        self.source_ranges_editor: QsciScintilla = None

        loadUi(os.path.join(os.path.dirname(__file__), 'rules_editor.ui'), self)

        self.rules_add_btn.setIcon(IconFont().icon('plus'))
        self.rules_del_btn.setIcon(IconFont().icon('minus'))
        self.range_add_btn.setIcon(IconFont().icon('plus'))
        self.range_del_btn.setIcon(IconFont().icon('minus'))
        self.custom_channel_search_btn.setIcon(IconFont().icon('search'))
        font = QFont('Monospace')
        font.setStyleHint(QFont.TypeWriter)
        self.base_type_lbl.setFont(font)
        self.base_type_frame.setHidden(True)

        header = self.range_table.horizontalHeader()
        header.setResizeMode(0, QHeaderView.ResizeToContents)
        header.setResizeMode(1, QHeaderView.Stretch)

        self._widget = widget
        self._current_rule_item: Optional[QListWidgetItem] = None
        self._loading_data: bool = True

        lexer = QsciLexerJSON(self.source_ranges_editor)
        self.source_ranges_editor.setLexer(lexer)
        configure_common_qsci(self.source_ranges_editor)
        self.source_ranges_editor.setReadOnly(False)

        try:
            self._rules: List[BaseRule] = widget.rules  # Rules here will be object-oriented because of WidgetRulesMixin
        except:
            self._rules: List[BaseRule] = []

        for rule in self._rules:
            self.rules_list_widget.addItem(rule.name)

        for name, prop in widget.RULE_PROPERTIES.items():
            self.prop_combobox.addItem(name, prop)

        self.eval_type_combobox.addItem('Numeric ranges', RuleType.NUM_RANGE)
        # self.eval_type.addItem('Python expression', RuleType.PY_EXPR) # TODO: Uncomment when python ready

        self.default_channel_checkbox.stateChanged.connect(
            lambda check: self.custom_channel_frame.setHidden(check))
        self.range_add_btn.clicked.connect(self._add_range)
        self.range_del_btn.clicked.connect(self._del_range)
        self.custom_channel_search_btn.clicked.connect(self._search_channel)
        self.rules_add_btn.clicked.connect(self._add_rule)
        self.rules_del_btn.clicked.connect(self._del_rule)
        self.rules_list_widget.itemSelectionChanged.connect(self._load_from_list)
        self.btn_box.button(QDialogButtonBox.Apply).clicked.connect(self._save_changes)
        self.btn_box.rejected.connect(self.close)
        self.rule_name_edit.textChanged.connect(self._name_changed)
        self.range_table.model().dataChanged.connect(self._tbl_states_changed)
        self.prop_combobox.currentIndexChanged.connect(self._property_changed)
        self.eval_type_combobox.currentIndexChanged.connect(self._eval_type_changed)

        self._clear_form()

    def _search_channel(self):
        QMessageBox().information(self,
                                  'Work in progress...',
                                  'In the future, this will allow you to look up channel address from CCDB.',
                                  QMessageBox.Ok)

    def _update_source_view(self):
        rule = cast(NumRangeRule, self._get_current_rule())
        # TODO: Connect QSci to signals and when editing, update table
        self.source_ranges_editor.setText(json.dumps(rule.ranges, cls=ComRADJSONEncoder, indent=QSCI_INDENTATION))

    def _add_range(self):
        """Add a new empty state to the table."""
        self._loading_data = True

        self.range_table.insertRow(self.range_table.rowCount())
        row = self.range_table.rowCount() - 1
        self.range_table.setCellWidget(row, 0, self._get_dynamic_state_item(row))

        try:
            rule = cast(NumRangeRule, self._get_current_rule())
        except IndexError:
            raise RuntimeError('Cannot create a dynamic state for non-existing rule')

        range = rule.ranges[row]
        self.range_table.setCellWidget(row, 1, self._make_range_widget(row=row, range=range))
        row_labels = [f' {x} ' for x in range(self.range_table.rowCount())]
        self.range_table.setVerticalHeaderLabels(row_labels)
        self._loading_data = False
        self._tbl_states_changed()

    def _del_range(self):
        """Delete the selected channel at the table."""
        items = self.range_table.selectionModel().selectedRows(0)
        if len(items) == 0:
            return

        # Ask for permission only for multiple rows deletion
        if len(items) > 1:
            reply = QMessageBox().question(self,
                                           'Message',
                                           f'Delete the selected states?',
                                           QMessageBox.Yes,
                                           QMessageBox.No)

            if reply != QMessageBox.Yes:
                return

        for itm in reversed(items):
            row = itm.row()
            self.range_table.removeRow(row)
        self._tbl_states_changed()

    def _add_rule(self):
        """Add a new rule to the list of rules."""
        default_name = 'New Rule'
        default_prop = self._widget.DEFAULT_RULE_PROPERTY
        _, prop_type = self._widget.RULE_PROPERTIES[self._widget.DEFAULT_RULE_PROPERTY]
        new_rule = NumRangeRule(name=default_name,
                                prop=default_prop,
                                channel=BaseRule.DEFAULT_CHANNEL)
        self._rules.append(new_rule)
        self._current_rule_item = QListWidgetItem()
        self._current_rule_item.setText(default_name)
        self.rules_list_widget.addItem(self._current_rule_item)
        self.rules_list_widget.setCurrentItem(self._current_rule_item)
        self._load_from_list()
        self.rule_name_edit.setFocus()

    def _del_rule(self):
        """Delete the rule selected in the rules list."""
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
        """Callback executed when the rule name is changed."""

        if not self._current_rule_item:
            # We may have blurred focus by this time already. Avoid crash
            return

        new_name = self.sender().text()
        self._current_rule_item.setText(new_name)
        self._get_current_rule().name = new_name

    def _tbl_states_changed(self):
        """Callback executed when the states in the table are modified."""
        if self._loading_data:
            return

        # TODO: Update inner data structure here
        self._update_source_view()

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
        rule_type = 0 if isinstance(rule, NumRangeRule) else 1
        self.eval_type_combobox.setCurrentIndex(rule_type)
        self.eval_stack_widget.setCurrentIndex(rule_type)
        if isinstance(rule, ExpressionRule):
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
        elif isinstance(rule, NumRangeRule):
            ranges = cast(NumRangeRule, rule).ranges
            self.range_table.clearContents()
            self.range_table.setRowCount(len(ranges))
            row_labels = [f' {x} ' for x in range(len(ranges))]
            self.range_table.setVerticalHeaderLabels(row_labels)
            _, base_type = self._widget.RULE_PROPERTIES[rule_prop]
            type_name = cast(Type, base_type).__name__
            for row_idx, range in enumerate(ranges):
                self.range_table.setCellWidget(row_idx, 0, self._get_dynamic_state_item(row=row_idx,
                                                                                        type_name=type_name,
                                                                                        prop_name=rule_prop,
                                                                                        current_range=range))
                self.range_table.setCellWidget(row_idx, 1, self._make_range_widget(row=row_idx, range=range))
            self._update_source_view()
        else:
            logger.exception(f'Unsupported rule type: {type(rule).__name__}')

        self._loading_data = False
        self.details_frame.setEnabled(True)

    def _save_changes(self):
        """Save the new rules at the widget `rules` property."""

        for rule in self._rules:
            try:
                rule.validate()
            except TypeError as e:
                QMessageBox.critical(self, 'Error Saving', os.linesep.join(str(e).split(';')), QMessageBox.Ok)
                return

        # TODO: Maybe this could be shared for all dialogs that we're about to create for designer?
        form_window = QDesignerFormWindowInterface.findFormWindow(self._widget)
        if form_window:
            form_window.cursor().setProperty('rules', json.dumps(self._rules, cls=ComRADJSONEncoder))
        self.accept()

    def _property_changed(self):
        """Callback executed when the property is selected."""
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


        if isinstance(curr_rule, NumRangeRule):
            _, prev_prop_type = self._widget.RULE_PROPERTIES[prev_prop]
            if prop_type != prev_prop_type:
                # Clear the state table because we can't map
                # different data types directly and it does not make sense
                cast(NumRangeRule, curr_rule).ranges.clear()
                self._clear_state_table()

    def _eval_type_changed(self):
        eval_type: RuleType = self.eval_type_combobox.currentData()
        self.eval_stack_widget.setCurrentIndex(eval_type.value())

    def _get_current_index(self) -> int:
        """
        Calculate and return the selected index from the list of rules.

        Returns:
            The index selected at the list of rules or -1 in case the item does not exist.
        """
        if self._current_rule_item is None:
            return -1
        return self.rules_list_widget.indexFromItem(self._current_rule_item).row()

    def _get_current_rule(self) -> BaseRule:
        idx = self._get_current_index()
        return self._rules[idx]

    def _make_range_widget(self, row: int, range: RuleRange):
        range_widget = QWidget()
        range_layout = QHBoxLayout()
        range_layout.setContentsMargins(0, 0, 0, 0)
        field = QLineEdit()
        field.is_max = False
        field.row_idx = row
        field.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        field.setText(str(range.min_val))
        field.setStyleSheet('background: transparent')
        field.setFrame(False)
        field.textChanged.connect(self._range_changed)
        field.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        range_layout.addWidget(field)
        lbl = QLabel(' ≤ channel value < ')
        range_layout.addWidget(lbl)
        field = QLineEdit()
        field.is_max = True
        field.row_idx = row
        field.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        field.setText(str(range.max_val))
        field.setStyleSheet('background: transparent')
        field.setFrame(False)
        field.textChanged.connect(self._range_changed)
        field.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        range_layout.addWidget(field)
        range_widget.setLayout(range_layout)
        return range_widget

    def _get_dynamic_state_item(self,
                                row: int,
                                type_name: Optional[str] = None,
                                prop_name: Optional[str] = None,
                                current_range: Optional[RuleRange] = None):
        if not prop_name:
            prop_name = self.prop_combobox.currentText()

        if not type_name:
            prop = self.prop_combobox.currentData()
            type_name = prop[1].__name__

        try:
            rule = cast(NumRangeRule, self._get_current_rule())
        except IndexError:
            raise RuntimeError('Cannot create a dynamic state for non-existing rule')

        if not current_range:
            range_list = rule.ranges
            try:
                current_range = range_list[row]
            except IndexError:
                current_range = RuleRange(min_val=0.0, max_val=1.0)
                range_list.append(current_range)

        if type_name == 'bool':
            if current_range.prop_val is None:
                value = row == 0
                current_range.prop_val = value
            else:
                value = bool(current_range.prop_val)
            value = Qt.Checked if value else Qt.Unchecked

            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            checkbox = QCheckBox()
            checkbox.setCheckState(value)
            checkbox.row_idx = row
            checkbox.setAttribute(Qt.WA_TransparentForMouseEvents)
            checkbox.stateChanged.connect(functools.partial(self._edit_value_changed, bool))
            btn = QToolButton()
            btn.setAutoRaise(True)
            btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
            btn.clicked.connect(checkbox.toggle)
            layout.addSpacerItem(QSpacerItem(10, 1, QSizePolicy.Expanding, QSizePolicy.Preferred))
            layout.addWidget(checkbox)
            layout.addSpacerItem(QSpacerItem(10, 1, QSizePolicy.Expanding, QSizePolicy.Preferred))
            btn.setLayout(layout)
            return btn
        elif type_name == 'int':
            if current_range.prop_val is None:
                value = 0
                current_range.prop_val = value
            else:
                value = int(current_range.prop_val)
            widget = QLineEdit()
            widget.setText(str(value))
            widget.setStyleSheet('background: transparent')
            widget.setPlaceholderText(f'Type {type_name} value...')
            widget.setAlignment(Qt.AlignCenter)
            widget.row_idx = row
            widget.textChanged.connect(functools.partial(self._edit_value_changed, int))
            return widget
        elif type_name == 'float':
            if current_range.prop_val is None:
                value = 0.0
                current_range.prop_val = value
            else:
                value = float(current_range.prop_val)
            widget = QLineEdit()
            widget.setText(str(value))
            widget.setStyleSheet('background: transparent')
            widget.setPlaceholderText(f'Type {type_name} value...')
            widget.setAlignment(Qt.AlignCenter)
            widget.row_idx = row
            widget.setFrame(False)
            widget.textChanged.connect(functools.partial(self._edit_value_changed, float))
            return widget
        elif prop_name == 'Color':
            if current_range.prop_val is None:
                value = '#000000'
                current_range.prop_val = value
            else:
                value = str(current_range.prop_val)
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
            raise TypeError(f'Unsupported property type: {type_name}')

    def _open_color_dialog(self):
        rule = cast(NumRangeRule, self._get_current_rule())
        range = rule.ranges[self.sender().row_idx]
        value = range.prop_val
        new_color = QColorDialog.getColor(QColor(value))
        if not new_color.isValid():
            # User cancelled the selection
            return
        range.prop_val = new_color.name()
        self._reload_state_table()

    def _range_changed(self, new_val: str):
        rule = cast(NumRangeRule, self._get_current_rule())
        range = rule.ranges[self.sender().row_idx]
        try:
            if self.sender().is_max:
                range.max_val = float(new_val)
            else:
                range.min_val = float(new_val)
        except ValueError:
            pass

    def _edit_value_changed(self, caster: Callable, new_val: str):
        rule = cast(NumRangeRule, self._get_current_rule())
        range = rule.ranges[self.sender().row_idx]
        try:
            range.prop_val = caster(new_val)
        except ValueError:
            pass

    def _clear_form(self):
        self._loading_data = True
        self._current_rule_item = None
        self.rule_name_edit.setText('')
        self.prop_combobox.setCurrentIndex(-1)
        self.default_channel_checkbox.setChecked(True)
        self._clear_state_table()
        self.details_frame.setEnabled(False)
        self._loading_data = False

    def _reload_state_table(self):
        for i in range(self.range_table.rowCount()):
            self.range_table.setCellWidget(i, 0, self._get_dynamic_state_item(i))

    def _clear_state_table(self):
        for _ in range(self.range_table.rowCount()):
            self.range_table.removeRow(0)
