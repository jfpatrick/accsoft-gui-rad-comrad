import os
import sys
import functools
import copy
import logging
import json
from typing import Optional, Union, List, Any, Dict, cast, Tuple, Type, Callable
from pydm.widgets.rules_editor import RulesEditor as PyDMRulesEditor
from pydm.utilities.iconfont import IconFont
from qtpy import QtWidgets, QtCore, QtGui, QtDesigner
from qtpy.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QColorDialog, QToolButton, QSpacerItem,
                            QPushButton, QListWidget, QSizePolicy, QFormLayout, QListWidgetItem,
                            QLabel, QLineEdit, QComboBox, QTabWidget, QTableWidget, QGroupBox, QStackedWidget,
                            QHeaderView, QCheckBox, QDialogButtonBox, QMessageBox)
from qtpy.QtCore import Qt
from qtpy.QtGui import QColor, QFont
from qtpy.QtDesigner import QDesignerFormWindowInterface
from qtpy.uic import loadUi
from comrad.qt.rules import WidgetRulesMixin, Rule, RuleType


logger = logging.getLogger(__name__)


class NewRulesEditor(QDialog):

    def __init__(self, widget: Union[QWidget, WidgetRulesMixin], parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.rules_add: QPushButton = None
        self.rules_del: QPushButton = None
        self.rules_list: QListWidget = None
        self.prop_combobox: QComboBox = None
        self.rule_name_edit: QLineEdit = None
        self.default_channel_checkbox: QCheckBox = None
        self.custom_channel_frame: QFrame = None
        self.custom_channel_edit: QLineEdit = None
        self.custom_channel_search: QPushButton = None
        self.eval_type: QComboBox = None
        self.eval_stack: QStackedWidget = None
        self.page_ranges: QWidget = None
        self.page_python: QWidget = None
        self.state_add: QPushButton = None
        self.state_del: QPushButton = None
        self.state_table: QTableWidget = None
        self.btn_box: QDialogButtonBox = None
        self.base_type_frame: QFrame = None
        self.base_type: QLabel = None
        self.details_frame: QFrame = None

        loadUi(os.path.join(os.path.dirname(__file__), 'rules_editor.ui'), self)

        self.rules_add.setIcon(IconFont().icon('plus'))
        self.rules_del.setIcon(IconFont().icon('minus'))
        self.state_add.setIcon(IconFont().icon('plus'))
        self.state_del.setIcon(IconFont().icon('minus'))
        self.custom_channel_search.setIcon(IconFont().icon('search'))
        font = QFont('Monospace')
        font.setStyleHint(QFont.TypeWriter)
        self.base_type.setFont(font)
        self.base_type_frame.setHidden(True)

        header = self.state_table.horizontalHeader()
        header.setResizeMode(0, QHeaderView.ResizeToContents)
        header.setResizeMode(1, QHeaderView.Stretch)

        self._widget = widget
        self._current_rule: Optional[QListWidgetItem] = None
        self._loading_data: bool = True

        try:
            self._rules: List[Rule] = json.loads(widget.rules)
        except:
            self._rules: List[Rule] = []

        for rule in self._rules:
            self.rules_list.addItem(rule.get('name', ''))

        for name, prop in widget.RULE_PROPERTIES.items():
            self.prop_combobox.addItem(name, prop)

        self.eval_type.addItem('Numeric ranges', RuleType.NUM_RANGE)
        # self.eval_type.addItem('Python expression', RuleType.PY_EXPR) # TODO: Uncomment when python ready

        self.default_channel_checkbox.stateChanged.connect(
            lambda check: self.custom_channel_frame.setHidden(check))
        self.state_add.clicked.connect(self._add_state)
        self.state_del.clicked.connect(self._del_state)
        self.custom_channel_search.clicked.connect(self._search_channel)
        self.rules_add.clicked.connect(self._add_rule)
        self.rules_del.clicked.connect(self._del_rule)
        self.rules_list.itemSelectionChanged.connect(self._load_from_list)
        self.btn_box.button(QDialogButtonBox.Apply).clicked.connect(self._save_changes)
        self.btn_box.rejected.connect(self.close)
        self.rule_name_edit.textChanged.connect(self._name_changed)
        self.state_table.model().dataChanged.connect(self._tbl_states_changed)
        self.prop_combobox.currentIndexChanged.connect(self._property_changed)
        self.eval_type.currentIndexChanged.connect(self._eval_type_changed)

        self._clear_form()

    def _search_channel(self):
        QMessageBox().information(self,
                                  'Work in progress...',
                                  'In the future, this will allow you to look up channel address from CCDB.',
                                  QMessageBox.Ok)

    def _add_state(self):
        """Add a new empty state to the table."""
        self._loading_data = True

        self.state_table.insertRow(self.state_table.rowCount())
        row = self.state_table.rowCount() - 1
        self.state_table.setCellWidget(row, 0, self._get_dynamic_state_item(row))

        try:
            data = self._get_current_rule()
        except IndexError:
            raise RuntimeError('Cannot create a dynamic state for non-existing rule')

        rule_list = cast(List[Rule], data['body'])
        rule = rule_list[row]
        self.state_table.setCellWidget(row, 1, self._make_range_widget(row=row, rule=rule))
        row_labels = [f' {x} ' for x in range(self.state_table.rowCount())]
        self.state_table.setVerticalHeaderLabels(row_labels)
        self._loading_data = False
        self._tbl_states_changed()

    def _del_state(self):
        """Delete the selected channel at the table."""
        items = self.state_table.selectionModel().selectedRows(0)
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
            self.state_table.removeRow(row)
        self._tbl_states_changed()

    def _add_rule(self):
        """Add a new rule to the list of rules."""
        default_name = 'New Rule'
        default_prop = self._widget.DEFAULT_RULE_PROPERTY
        _, prop_type = self._widget.RULE_PROPERTIES[self._widget.DEFAULT_RULE_PROPERTY]
        new_rule = {
            'name': default_name,
            'property': default_prop,
            'channel': '__auto__',
            'type': RuleType.NUM_RANGE.value,
            'body': [],
        }
        self._rules.append(new_rule)
        self._current_rule = QListWidgetItem()
        self._current_rule.setText(default_name)
        self.rules_list.addItem(self._current_rule)
        self.rules_list.setCurrentItem(self._current_rule)
        self._load_from_list()
        self.rule_name_edit.setFocus()

    def _del_rule(self):
        """Delete the rule selected in the rules list."""
        idx = self._get_current_index()
        if idx < 0:
            return

        reply = QMessageBox().question(self,
                                       'Message',
                                       f'Are you sure you want to delete Rule: {self._current_rule.text()}?',
                                       QMessageBox.Yes,
                                       QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.rules_list.takeItem(idx)
            self.rules_list.clearSelection()
            self._rules.pop(idx)
            self._clear_form()

    def _name_changed(self):
        """Callback executed when the rule name is changed."""

        if not self._current_rule:
            # We may have blurred focus by this time already. Avoid crash
            return

        new_name = self.sender().text()
        self._current_rule.setText(new_name)
        self._get_current_rule()['name'] = new_name

    def _tbl_states_changed(self):
        """Callback executed when the states in the table are modified."""
        if self._loading_data:
            return

        # TODO: Update inner data structure here

    def _load_from_list(self):
        item = self.rules_list.currentItem()
        idx = self.rules_list.indexFromItem(item).row()

        if idx < 0:
            return

        self._loading_data = True
        self._current_rule = item
        data = self._rules[idx]
        self.rule_name_edit.setText(data['name'])
        rule_prop = data['property']
        self.prop_combobox.setCurrentText(rule_prop)
        rule_type: int = data['type']
        self.eval_type.setCurrentIndex(rule_type)
        self.eval_stack.setCurrentIndex(rule_type)
        if rule_type == RuleType.PY_EXPR:
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
        elif rule_type == RuleType.NUM_RANGE:
            rules = cast(List[Rule], data['body'])
            self.state_table.clearContents()
            self.state_table.setRowCount(len(rules))
            # row_labels = map(str, range(len(rules)))
            row_labels = [f' {x} ' for x in range(len(rules))]
            self.state_table.setVerticalHeaderLabels(row_labels)
            _, base_type = self._widget.RULE_PROPERTIES[rule_prop]
            type_name = cast(Type, base_type).__name__
            for row_idx, rule in enumerate(rules):
                self.state_table.setCellWidget(row_idx, 0, self._get_dynamic_state_item(row=row_idx,
                                                                                        type_name=type_name,
                                                                                        prop_name=rule_prop,
                                                                                        current_rule=rule))
                self.state_table.setCellWidget(row_idx, 1, self._make_range_widget(row=row_idx, rule=rule))
        else:
            logger.exception(f'Unsupported rule type: {rule_type}')

        self._loading_data = False
        self.details_frame.setEnabled(True)

    def _save_changes(self):
        """Save the new rules at the widget `rules` property."""

        errors = self._form_errors()
        if len(errors) > 0:
            QMessageBox.critical(self, 'Error Saving', os.linesep.join(errors), QMessageBox.Ok)
            return

        # TODO: Maybe this could be shared for all dialogs that we're about to create for designer?
        form_window = QDesignerFormWindowInterface.findFormWindow(self._widget)
        if form_window:
            form_window.cursor().setProperty('rules', json.dumps(self._rules))
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

        prev_prop: str = curr_rule['property']
        curr_rule['property'] = text

        type_name = cast(Type, prop_type).__name__
        self.base_type.setText(type_name)
        self.base_type_frame.setHidden(False)


        if curr_rule['type'] == RuleType.NUM_RANGE:
            _, prev_prop_type = self._widget.RULE_PROPERTIES[prev_prop]
            if prop_type != prev_prop_type:
                # Clear the state table because we can't map
                # different data types directly and it does not make sense
                cast(List, curr_rule['body']).clear()
                self._clear_state_table()

    def _eval_type_changed(self):
        eval_type: RuleType = self.eval_type.currentData()
        self.eval_stack.setCurrentIndex(eval_type.value())

    def _get_current_index(self) -> int:
        """
        Calculate and return the selected index from the list of rules.

        Returns:
            The index selected at the list of rules or -1 in case the item does not exist.
        """
        if self._current_rule is None:
            return -1
        return self.rules_list.indexFromItem(self._current_rule).row()

    def _get_current_rule(self) -> Rule:
        idx = self._get_current_index()
        return self._rules[idx]

    def _make_range_widget(self, row: int, rule: Rule):
        range_widget = QWidget()
        range_layout = QHBoxLayout()
        range_layout.setContentsMargins(0, 0, 0, 0)
        field = QLineEdit()
        field.is_max = False
        field.row_idx = row
        field.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        field.setText(str(rule['min']))
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
        field.setText(str(rule['max']))
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
                                current_rule: Optional[Rule] = None):
        if not prop_name:
            prop_name = self.prop_combobox.currentText()

        if not type_name:
            prop = self.prop_combobox.currentData()
            type_name = prop[1].__name__

        try:
            data = self._get_current_rule()
        except IndexError:
            raise RuntimeError('Cannot create a dynamic state for non-existing rule')

        if not current_rule:
            rule_list = cast(List[Rule], data['body'])
            try:
                current_rule = rule_list[row]
            except IndexError:
                current_rule = {
                    'min': 0.0,
                    'max': 1.0,
                }
                rule_list.append(current_rule)

        if type_name == 'bool':
            try:
                value = bool(current_rule['value'])
            except KeyError:
                value = row == 0
                current_rule['value'] = value
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
            try:
                value = int(current_rule['value'])
            except KeyError:
                value = ''
                current_rule['value'] = value
            widget = QLineEdit()
            widget.setText(str(value))
            widget.setStyleSheet('background: transparent')
            widget.setPlaceholderText(f'Type {type_name} value...')
            widget.setAlignment(Qt.AlignCenter)
            widget.row_idx = row
            widget.textChanged.connect(functools.partial(self._edit_value_changed, int))
            return widget
        elif type_name == 'float':
            try:
                value = float(current_rule['value'])
            except KeyError:
                value = ''
                current_rule['value'] = value
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
            try:
                value = str(current_rule['value'])
            except KeyError:
                value = '#000000'
                current_rule['value'] = value
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
        data = self._get_current_rule()
        map = cast(List[Rule], data['body'])[self.sender().row_idx]
        value = map['value']
        new_color = QColorDialog.getColor(QColor(value))
        if not new_color.isValid():
            # User cancelled the selection
            return
        map['value'] = new_color.name()
        self._reload_state_table()

    def _range_changed(self, new_val: str):
        data = self._get_current_rule()
        map = cast(List[Rule], data['body'])[self.sender().row_idx]
        key = 'max' if self.sender().is_max else 'min'
        try:
            map[key] = float(new_val)
        except ValueError:
            pass

    def _edit_value_changed(self, caster: Callable, new_val: str):
        data = self._get_current_rule()
        map = cast(List[Rule], data['body'])[self.sender().row_idx]
        try:
            map['value'] = caster(new_val)
        except ValueError:
            pass

    def _clear_form(self):
        self._loading_data = True
        self._current_rule = None
        self.rule_name_edit.setText('')
        self.prop_combobox.setCurrentIndex(-1)
        self.default_channel_checkbox.setChecked(True)
        self._clear_state_table()
        self.details_frame.setEnabled(False)
        self._loading_data = False

    def _reload_state_table(self):
        for i in range(self.state_table.rowCount()):
            self.state_table.setCellWidget(i, 0, self._get_dynamic_state_item(i))

    def _clear_state_table(self):
        for _ in range(self.state_table.rowCount()):
            self.state_table.removeRow(0)

    def _form_errors(self) -> List[str]:
        """
        Sanity check the form data.

        Returns:
            List of error messages. If none found, list will be empty.
        """
        errors: List[str] = []
        for idx, rule in enumerate(self._rules):
            name: str = rule['name']

            if name is None or name == "":
                errors.append(f'Rule #{idx+1} has no name.')

            rule_type: int = rule['type']
            if rule_type == RuleType.PY_EXPR:
                # TODO: Implement check for Python expressions
                logger.warning(f'Check for Python expressions is not implemented')
                # try:
                #     expression: str = self._get_entry(rule, 'manual_rule.expression')
                # except KeyError:
                #     continue

                # if check_custom_channels:
                #     channels: List[Dict[str, str]] = self._get_entry(rule, 'manual_rule.channels', [])
                #
                #     if expression is None or expression == "":
                #         errors.append(f'Rule #{idx+1} has no expression.')
                #     if len(channels) == 0:
                #         errors.append(f'Rule #{idx+1} has no channel.')
                #     else:
                #         found_trigger: bool = False
                #         for ch_idx, ch in enumerate(channels):
                #             if not ch.get('channel'):
                #                 errors.append(f'Rule #{idx+1} - Ch. #{ch_idx} has no channel.')
                #             if ch.get('trigger', False) and not found_trigger:
                #                 found_trigger = True
                #
                #         if not found_trigger:
                #             errors.append(f'Rule #{idx+1} has no channel for trigger.')
                # else:
            elif rule_type == RuleType.NUM_RANGE:
                rules = cast(List[Rule], rule['body'])

                if len(rules) == 0:
                    errors.append(f'Rule #{idx+1}.{row} must have at least one range defined.')
                else:
                    def is_overlapping(min1: float, max1: float, min2: float, max2: float) -> bool:
                        if min1 is None:
                            min1 = -sys.float_info.max
                        if min2 is None:
                            min2 = -sys.float_info.max
                        if max1 is None:
                            max1 = sys.float_info.max
                        if max2 is None:
                            max2 = sys.float_info.max
                        return max(min1, min2) < min(max1, max2)

                    # TODO: This could be better optimized
                    for row, val in enumerate(rules):
                        range_min = val.get('min')
                        range_max = val.get('max')
                        if range_min is not None and range_max is not None and range_min > range_max:
                            errors.append(f'Rule #{idx + 1}.{row} has inverted ranges (max < min)')
                        else:
                            for another_row, another_val in enumerate(rules[row+1:]):
                                another_min = another_val.get('min')
                                another_max = another_val.get('max')
                                if is_overlapping(range_min, range_max, another_min, another_max):
                                    errors.append(f'Rule #{idx + 1}.{row} has overlapping ranges with '
                                                  f'Rule #{idx + 1}.{another_row+row+1}')
            else:
                logger.exception(f'Unsupported rule type: {rule_type}')
                errors.append(f'Rule #{idx+1} has unsupported type')

        return errors
