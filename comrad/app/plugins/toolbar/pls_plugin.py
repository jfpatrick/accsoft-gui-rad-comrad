import logging
import os
from dataclasses import dataclass
from typing import Optional, List, cast, Tuple, Dict
from pathlib import Path
from qtpy.QtWidgets import (QDialog, QWidget, QComboBox, QFrame, QCheckBox, QStackedWidget, QLabel, QToolButton,
                            QSpacerItem, QSizePolicy, QMenu, QAction, QHBoxLayout, QRadioButton, QDialogButtonBox,
                            QButtonGroup, QWIDGETSIZE_MAX)
from qtpy.QtGui import QShowEvent
from qtpy.QtCore import QStringListModel, Qt, Signal, QTimer
from qtpy.uic import loadUi
from pydm.utilities.iconfont import IconFont
from pyccda import SyncAPI as CCDA, sync_models as CCDATypes
from accwidgets.timing_bar import TimingBar, TimingBarDomain, TimingBarModel
from comrad import CApplication
from comrad.data.pyjapc_patch import CPyJapc
from comrad.app.plugins.common import CToolbarWidgetPlugin


logger = logging.getLogger(__name__)


@dataclass
class TelegramInfo:
    machine: Optional[str] = None
    group: Optional[str] = None
    line: Optional[str] = None
    found_in_context: bool = False


def get_telegram_info() -> TelegramInfo:
    app = cast(CApplication, CApplication.instance())
    app_selector = app.main_window.window_context.selector

    if app_selector:
        try:
            machine, group, line = tuple(app_selector.split('.'))
            found = True
        except ValueError:
            found = False
        if found:
            return TelegramInfo(machine=machine,
                                group=group,
                                line=line,
                                found_in_context=True)
    machine = os.environ.get('PLS_TELEGRAM', None)
    if machine:
        return TelegramInfo(machine=machine,
                            group='USER',
                            line='ALL')
    return TelegramInfo()


class PLSSelectorDialog(QDialog):

    STACK_COMPLETE = 0
    STACK_LOADING = 1
    STACK_ERROR = 2

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Dialog for choosing control system "selector" on the window level.

        Args:
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

        self.main_window = cast(CApplication, CApplication.instance()).main_window

        self.ccda = CCDA()
        self._data: List[CCDATypes.SelectorDomain] = []
        self.machine_combo.setModel(QStringListModel())
        self.group_combo.setModel(QStringListModel())
        self.line_combo.setModel(QStringListModel())

        tgm_info = get_telegram_info()

        self.no_selector.setChecked(not tgm_info.found_in_context)
        self._toggle_selector(self.no_selector.checkState())

        self._original_machine = tgm_info.machine
        self._original_group = tgm_info.group
        self._original_line = tgm_info.line

        self.no_selector.stateChanged.connect(self._toggle_selector)
        self.accepted.connect(self._update_window_context)

    def showEvent(self, event: QShowEvent):
        super().showEvent(event)

        # Have we been shown?
        if event.spontaneous() or self._data:
            return

        # Only execute this once after being shown for the first time
        self.stack.setCurrentIndex(self.STACK_LOADING)
        try:
            self._data = list(self.ccda.SelectorDomain.search())
        except Exception as e:  # noqa: B902
            err_msg = 'Failed to contact CCDB'
            logger.error(f'{err_msg}: {e}')
            self.stack.setCurrentIndex(self.STACK_ERROR)
            self.error.setText(err_msg)
            # FIXME: When PyCCDA fixes its exception to abstract it away from urllib3 implementation, we should catch it instead of general one
            return

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

    def _update_window_context(self):
        if self.no_selector.isChecked():
            self.main_window.window_context.selector = None
        else:
            machine = self.machine_combo.currentText()
            group = self.group_combo.currentText()
            line = self.line_combo.currentText()
            if not machine or not group or not line:
                return

            self.main_window.window_context.selector = f'{machine}.{group}.{line}'


@dataclass
class PLSToolbarConfig:
    show_bar: bool = False
    supercycle: bool = True
    show_domain: bool = True
    show_time: bool = True
    show_start: bool = True
    show_user: bool = True
    show_lsa: bool = True
    show_tz: bool = False
    microseconds: bool = False
    heartbeat: bool = True
    utc: bool = False

    @classmethod
    def parse(cls, input: Optional[Dict[str, str]]):
        obj = cls()
        if input is None:
            return obj
        for key, val in input.items():
            if not hasattr(obj, key):
                continue
            if val == '1':
                processed_val = True
            elif val == '0':
                processed_val = False
            else:
                continue
            setattr(obj, key, processed_val)
        return obj


class PLSTimingConfigDialog(QDialog):

    config_updated = Signal(PLSToolbarConfig)

    def __init__(self, config: PLSToolbarConfig, parent: Optional[QWidget] = None):
        """
        Dialog for configure the timing bar.

        Args:
              config: Initial configuration.
              parent: Owning widget.
        """
        super().__init__(parent)

        self.bar_config: QWidget = None
        self.chkbx_heart: QCheckBox = None
        self.chkbx_super: QCheckBox = None
        self.chkbx_domain: QCheckBox = None
        self.chkbx_lsa: QCheckBox = None
        self.chkbx_start: QCheckBox = None
        self.chkbx_timestamp: QCheckBox = None
        self.chkbx_user: QCheckBox = None
        self.chkbx_bar: QCheckBox = None
        self.chkbx_us: QCheckBox = None
        self.chkbx_tz: QCheckBox = None
        self.timestamp_details: QFrame = None
        self.buttons: QDialogButtonBox = None
        self.radio_local: QRadioButton = None
        self.radio_utc: QRadioButton = None

        loadUi(Path(__file__).parent / 'timing_dialog.ui', self)

        self.displayed_tz_group = QButtonGroup(self)
        self.displayed_tz_group.addButton(self.radio_local, TimingBar.TimeZone.LOCAL.value)
        self.displayed_tz_group.addButton(self.radio_utc, TimingBar.TimeZone.UTC.value)

        self.chkbx_bar.stateChanged.connect(self._on_bar_tick)
        self.chkbx_timestamp.stateChanged.connect(self._on_timestamp_toggled)
        self.buttons.accepted.connect(self._on_accept)

        self.chkbx_bar.setChecked(config.show_bar)
        self.chkbx_heart.setChecked(config.heartbeat)
        self.chkbx_super.setChecked(config.supercycle)
        self.chkbx_domain.setChecked(config.show_domain)
        self.chkbx_lsa.setChecked(config.show_lsa)
        self.chkbx_start.setChecked(config.show_start)
        self.chkbx_user.setChecked(config.show_user)
        self.chkbx_tz.setChecked(config.show_tz)
        self.chkbx_us.setChecked(config.microseconds)
        self.chkbx_timestamp.setChecked(config.show_time)

        active_id = TimingBar.TimeZone.UTC if config.utc else TimingBar.TimeZone.LOCAL
        self.displayed_tz_group.button(active_id.value).setChecked(True)

        self._on_bar_tick()
        self._on_timestamp_toggled()

    def _on_accept(self):
        config = PLSToolbarConfig(show_bar=self.chkbx_bar.isChecked(),
                                  supercycle=self.chkbx_super.isChecked(),
                                  show_domain=self.chkbx_domain.isChecked(),
                                  show_time=self.chkbx_timestamp.isChecked(),
                                  show_start=self.chkbx_start.isChecked(),
                                  show_user=self.chkbx_user.isChecked(),
                                  show_lsa=self.chkbx_lsa.isChecked(),
                                  heartbeat=self.chkbx_heart.isChecked(),
                                  microseconds=self.chkbx_us.isChecked(),
                                  show_tz=self.chkbx_tz.isChecked(),
                                  utc=self.displayed_tz_group.checkedId() == TimingBar.TimeZone.UTC)
        self.config_updated.emit(config)
        self.accept()

    def _on_bar_tick(self):
        self.bar_config.setEnabled(self.chkbx_bar.isChecked())

    def _on_timestamp_toggled(self):
        self.timestamp_details.setEnabled(self.chkbx_timestamp.isChecked())


class PLSPluginButton(QToolButton):

    def __init__(self, parent: 'PLSToolbarWidget'):
        """
        Button that is embedded into the toolbar to open the dialog.

        Args:
            rbac: Handle to the RBAC manager.
            parent: Parent widget to hold this object.
        """
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.setPopupMode(QToolButton.InstantPopup)
        toolbar = cast(CApplication, CApplication.instance()).main_window.ui.navbar
        self.setToolButtonStyle(toolbar.toolButtonStyle())
        toolbar.toolButtonStyleChanged.connect(self.setToolButtonStyle)
        self.setAutoRaise(True)
        self.setText('PLS')
        icon_font = IconFont()
        self.setIcon(icon_font.icon('clock-o'))
        self.setIconSize(toolbar.iconSize())  # Needed because gets smaller inside a layout
        menu = QMenu(self)
        self.setMenu(menu)
        act_user = QAction(icon_font.icon('clock-o'), 'Select PLS user', self)
        act_user.triggered.connect(self._open_user_selector)
        menu.addAction(act_user)
        menu.addSeparator()
        act_bar = QAction(icon_font.icon('cog'), 'Configure timing bar', self)
        act_bar.triggered.connect(self._open_bar_config)
        menu.addAction(act_bar)

    def _open_user_selector(self):
        PLSSelectorDialog().exec_()

    def _open_bar_config(self):
        parent = cast(PLSToolbarWidget, self.parent())
        dialog = PLSTimingConfigDialog(parent.config)
        dialog.config_updated.connect(self._on_timing_config_updated)
        dialog.exec_()

    def _on_timing_config_updated(self, update: PLSToolbarConfig):
        parent = cast(PLSToolbarWidget, self.parent())
        parent.config = update


class PLSToolbarWidget(QWidget):

    def __init__(self, parent: Optional[QWidget] = None, config: Optional[Dict[str, str]] = None):
        """
        Container for PLS button and (optionally) the timing bar.

        Args:
            parent: Parent widget to hold this object.
        """
        super().__init__(parent)
        self._config = PLSToolbarConfig.parse(config)
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self._bar: Optional[TimingBar] = None
        self._btn = PLSPluginButton(self)
        self._largest_known_width: Optional[float] = None  # Predict wanted size to avoid timing bar abruptly resizing with different cycle name lengths
        layout.addWidget(self._btn)
        layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred))  # Avoid stretching the button
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.setLayout(layout)
        self._update_view_for_config(self._config)
        cast(CApplication, CApplication.instance()).main_window.window_context.selectorChanged.connect(self._on_selector_changed)

    @property
    def config(self) -> PLSToolbarConfig:
        return self._config

    @config.setter
    def config(self, config: PLSToolbarConfig):
        if config == self._config:
            return
        self._config = config
        self._update_view_for_config(self._config)

    def _update_view_for_config(self, config: PLSToolbarConfig):
        self._reset_bar_width()
        if config.show_bar and not self._bar:
            bar_config = get_bar_config_for_current_selector()
            user: Optional[str] = None
            # Here we are using singleton PyJapc instance to ensure that configuration of separate instances does not
            # get conflicting. (E.g. JAPC has only global configuration for InCA usage, therefore disabling InCA here
            # may affect data plugins and vice versa.
            if bar_config is not None:
                domain, highlighted_user = bar_config
                model = TimingBarModel(domain=domain, japc=CPyJapc.instance())
                user = highlighted_user
            else:
                model = TimingBarModel(domain=DEFAULT_DOMAIN, japc=CPyJapc.instance())
            self._bar = TimingBar(model=model, parent=self)
            model.timingUpdateReceived.connect(self._adjust_bar_width_on_data)
            model.timingErrorReceived.connect(self._adjust_bar_width_on_error)
            model.domainNameChanged.connect(self._reset_bar_width)
            self._bar.highlightedUser = user
            self.layout().insertWidget(0, self._bar)
        elif not config.show_bar and self._bar:
            self._bar.model.timingUpdateReceived.disconnect(self._adjust_bar_width_on_data)
            self._bar.model.timingErrorReceived.disconnect(self._adjust_bar_width_on_error)
            self._bar.model.domainNameChanged.disconnect(self._reset_bar_width)
            self.layout().removeWidget(self._bar)
            self._bar.setParent(None)
            self._bar.deleteLater()
            self._bar = None
        if self._bar:
            bar = cast(TimingBar, self._bar)
            bar.renderSuperCycle = config.supercycle
            label_config: TimingBar.Labels = 0
            if config.show_domain:
                label_config |= TimingBar.Labels.TIMING_DOMAIN
            if config.show_time:
                label_config |= TimingBar.Labels.DATETIME
            if config.show_start:
                label_config |= TimingBar.Labels.CYCLE_START
            if config.show_user:
                label_config |= TimingBar.Labels.USER
            if config.show_lsa:
                label_config |= TimingBar.Labels.LSA_CYCLE_NAME
            bar.labels = label_config
            bar.showMicroSeconds = config.microseconds
            bar.showTimeZone = config.show_tz
            bar.indicateHeartbeat = config.heartbeat
            bar.displayedTimeZone = TimingBar.TimeZone.UTC if config.utc else TimingBar.TimeZone.LOCAL

    def _reset_bar_width(self):
        self._largest_known_width = None
        if self._bar:
            self._bar.setMinimumWidth(0)
            self._bar.setMaximumWidth(QWIDGETSIZE_MAX)

    def _adjust_bar_width_on_data(self):
        self._adjust_bar_width()

    def _adjust_bar_width_on_error(self):
        self._adjust_bar_width(min_width=300)

    def _adjust_bar_width(self, min_width: Optional[float] = None):
        if not self._bar:
            return

        def calc_new_width():
            if not self._bar.sizeHint().isValid():
                if min_width is None:
                    return
                else:
                    new_width = min_width
            else:
                new_width = self._bar.sizeHint().width()
            if min_width is not None:
                new_width = max(new_width, min_width)
            if self._largest_known_width is None or new_width > self._largest_known_width:
                self._largest_known_width = new_width
                self._bar.setMinimumWidth(self._largest_known_width)
                self._bar.setMaximumWidth(self._largest_known_width)
                self._bar.update()
                self.layout().update()

        # This is just to execute logic in the end of run loop iteration
        # We want to delay that to give bar a chance to adjust its size hint, because we cannot guarantee that labels
        # have been populated with new data at this point, therefore this calculation will not be effective until
        # the next chunk of data triggers the same callback.
        QTimer.singleShot(0, calc_new_width)

    def _on_selector_changed(self):
        # If domain has changed, update it in timing bar
        if self._bar:
            bar = cast(TimingBar, self._bar)
            config = get_bar_config_for_current_selector()
            if config is not None:
                domain, user = config
                bar.highlightedUser = user
                bar.model.domain = domain
            else:
                bar.highlightedUser = None
                bar.model.domain = DEFAULT_DOMAIN


def get_bar_config_for_current_selector() -> Optional[Tuple[TimingBarDomain, Optional[str]]]:
    tgm_info = get_telegram_info()
    try:
        domain = TimingBarDomain(tgm_info.machine)
    except ValueError:
        return None
    user = None if tgm_info.line is None or tgm_info.line.upper() == 'ALL' else tgm_info.line
    return domain, user


class PLSPlugin(CToolbarWidgetPlugin):
    """Plugin to display cycle selector button in the toolbar."""

    plugin_id = 'comrad.pls'
    position = CToolbarWidgetPlugin.Position.LEFT

    def create_widget(self, config: Optional[Dict[str, str]]) -> QWidget:
        return PLSToolbarWidget(config=config)


DEFAULT_DOMAIN = TimingBarDomain.LHC
