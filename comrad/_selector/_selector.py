import logging
import operator
import functools
from dataclasses import dataclass
from typing import Optional, List, cast
from pathlib import Path
from qtpy.uic import loadUi
from qtpy.QtGui import QShowEvent
from qtpy.QtCore import QStringListModel, Qt, Signal
from qtpy.QtWidgets import QDialog, QWidget, QComboBox, QFrame, QCheckBox, QStackedWidget, QLabel
from pyccda import SyncAPI as CCDA, sync_models as CCDATypes
from pyccda.models import SelectorValue, SelectorGroup


logger = logging.getLogger(__name__)


@dataclass
class PLSSelectorConfig:
    machine: Optional[str] = None
    group: Optional[str] = None
    line: Optional[str] = None
    enabled: bool = True

    @classmethod
    def no_selector(cls):
        return cls(enabled=False)


class PLSSelectorDialog(QDialog):

    STACK_COMPLETE = 0
    STACK_LOADING = 1
    STACK_ERROR = 2

    selector_selected = Signal(str)

    def __init__(self, config: PLSSelectorConfig, parent: Optional[QWidget] = None):
        """
        Dialog for choosing control system "selector" on the window level.

        Args:
            config: Initial telegram info to configure UI for.
            parent: Owning widget.
        """
        super().__init__(parent)

        self.machine_combo: QComboBox = None
        self.group_combo: QComboBox = None
        self.line_combo: QComboBox = None
        self.chooser_frame: QFrame = None
        self.no_selector: QCheckBox = None
        self.stack: QStackedWidget = None
        self.error: QLabel = None

        loadUi(Path(__file__).parent / 'pls_dialog.ui', self)

        self._original_machine: Optional[str] = None
        self._original_group: Optional[str] = None
        self._original_line: Optional[str] = None

        self.ccda = CCDA()
        self._data: List[CCDATypes.SelectorDomain] = []
        self.machine_combo.setModel(QStringListModel())
        self.group_combo.setModel(QStringListModel())
        self.line_combo.setModel(QStringListModel())

        self.no_selector.setChecked(not config.enabled)
        self._toggle_selector(self.no_selector.checkState())

        self._original_machine = config.machine
        self._original_group = config.group
        self._original_line = config.line

        self.no_selector.stateChanged.connect(self._toggle_selector)
        self.accepted.connect(self._notify_new_selector)

    def showEvent(self, event: QShowEvent):
        super().showEvent(event)

        # Have we been shown?
        if event.spontaneous() or self._data:
            return

        # Only execute this once after being shown for the first time
        self.stack.setCurrentIndex(self.STACK_LOADING)
        try:
            raw_data = list(self.ccda.SelectorDomain.search())
        except Exception as e:  # noqa: B902
            err_msg = 'Failed to contact CCDB'
            logger.error(f'{err_msg}: {e}')
            self.stack.setCurrentIndex(self.STACK_ERROR)
            self.error.setText(err_msg)
            # FIXME: When PyCCDA fixes its exception to abstract it away from urllib3 implementation, we should catch it instead of general one
            return
        else:
            # Sort data alphabetically
            # 'USER' group should always stay on top, regardless of the alphabetical order
            # "ALL" user should always stay on top, regardless of the alphabetical order

            def compare_group(lhs: SelectorGroup, rhs: SelectorGroup):
                if lhs.name == 'USER':
                    return -1
                if rhs.name == 'USER':
                    return 1
                return (lhs.name > rhs.name) - (lhs.name < rhs.name)

            def compare_line(lhs: SelectorValue, rhs: SelectorValue):
                if lhs.name == 'ALL':
                    return -1
                if rhs.name == 'ALL':
                    return 1
                return (lhs.name > rhs.name) - (lhs.name < rhs.name)

            raw_data = sorted(raw_data, key=operator.attrgetter('name'))
            for domain in raw_data:
                domain.selector_groups = sorted(domain.selector_groups, key=functools.cmp_to_key(compare_group))
                for group in domain.selector_groups:
                    group.selector_values = sorted(group.selector_values, key=functools.cmp_to_key(compare_line))
            self._data = raw_data

        if not self._data:
            err_msg = 'Empty data received from CCDA. Cannot populate PLS dialog.'
            logger.debug(err_msg)
            self.stack.setCurrentIndex(self.STACK_ERROR)
            self.error.setText(err_msg)
            return

        self.stack.setCurrentIndex(self.STACK_COMPLETE)

        cast(QStringListModel, self.machine_combo.model()).setStringList([x.name for x in self._data])
        if self._original_machine is None:
            machine_idx = 0
        else:
            machine_idx = max(0, self.machine_combo.findText(self._original_machine))

        self.machine_combo.setCurrentIndex(machine_idx)
        self._update_groups_for_machine(machine_idx)

        if self._original_group is None:
            group_idx = 0
        else:
            group_idx = max(0, self.group_combo.findText(self._original_group))

        self.group_combo.setCurrentIndex(group_idx)
        self._update_lines_for_group(machine_idx=machine_idx, group_idx=group_idx)

        if self._original_line is None:
            line_idx = 0
        else:
            line_idx = max(0, self.line_combo.findText(self._original_line))

        self.line_combo.setCurrentIndex(line_idx)

        self.machine_combo.currentIndexChanged[str].connect(self._machine_updated)
        self.group_combo.currentIndexChanged[str].connect(self._group_updated)

    def _machine_updated(self, text: str):
        index = self.machine_combo.findText(text)
        if index == -1:
            return

        self._update_groups_for_machine(index)
        self.group_combo.setCurrentIndex(0)

    def _group_updated(self, text: str):
        index = self.group_combo.findText(text)
        if index == -1:
            return

        self._update_lines_for_group(machine_idx=self.machine_combo.currentIndex(), group_idx=index)
        self.line_combo.setCurrentIndex(0)

    def _update_groups_for_machine(self, index: int):
        machine = self._data[index]
        cast(QStringListModel, self.group_combo.model()).setStringList([x.name for x in machine.selector_groups])

    def _update_lines_for_group(self, machine_idx: int, group_idx: int):
        machine = self._data[machine_idx]
        group = machine.selector_groups[group_idx]
        cast(QStringListModel, self.line_combo.model()).setStringList([x.name for x in group.selector_values])

    def _toggle_selector(self, state: Qt.CheckState):
        self.chooser_frame.setEnabled(state != Qt.Checked)

    def _notify_new_selector(self):
        new_selector: Optional[str]
        if self.no_selector.isChecked():
            new_selector = None
        else:
            machine = self.machine_combo.currentText()
            group = self.group_combo.currentText()
            line = self.line_combo.currentText()
            if not machine or not group or not line:
                return

            new_selector = '.'.join([machine, group, line])

        self.selector_selected.emit(new_selector)
