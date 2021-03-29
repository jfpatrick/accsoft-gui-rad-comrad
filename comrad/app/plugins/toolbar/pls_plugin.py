import logging
import os
from dataclasses import dataclass
from typing import Optional, cast, Tuple, Dict
from pathlib import Path
from qtpy.QtWidgets import (QDialog, QWidget, QFrame, QCheckBox, QToolButton,
                            QSpacerItem, QSizePolicy, QMenu, QAction, QHBoxLayout, QRadioButton, QDialogButtonBox,
                            QButtonGroup, QWIDGETSIZE_MAX)
from qtpy.QtCore import Signal, QTimer
from qtpy.uic import loadUi
from pydm.utilities.iconfont import IconFont
from accwidgets.timing_bar import TimingBar, TimingBarDomain, TimingBarModel
from comrad import CApplication
from comrad.data.pyjapc_patch import CPyJapc
from comrad.app.plugins.common import CToolbarWidgetPlugin
from comrad.app._toolbtn import ToolButton
from comrad._selector import PLSSelectorDialog, PLSSelectorConfig


logger = logging.getLogger('comrad.app.plugins.toolbar.pls_plugin')


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
    show_sel: bool = True
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


class PLSPluginButton(ToolButton):

    def __init__(self, parent: 'PLSToolbarWidget'):
        """
        Button that is embedded into the toolbar to open the dialog.

        Args:
            rbac: Handle to the RBAC manager.
            parent: Parent widget to hold this object.
        """
        super().__init__(horizontal=QSizePolicy.Minimum,
                         vertical=QSizePolicy.Expanding,
                         parent=parent)
        self.setPopupMode(QToolButton.InstantPopup)
        self.setAutoRaise(True)
        self.setText('PLS')
        icon_font = IconFont()
        self.setIcon(icon_font.icon('clock-o'))
        menu = QMenu(self)
        self.setMenu(menu)
        act_user = QAction(icon_font.icon('clock-o'), 'Select PLS user', self)
        act_user.triggered.connect(self._open_user_selector)
        menu.addAction(act_user)
        self.act_toggle = QAction(self)
        menu.addAction(self.act_toggle)
        menu.addSeparator()
        act_bar = QAction(icon_font.icon('cog'), 'Configure timing bar', self)
        act_bar.triggered.connect(self._open_bar_config)
        menu.addAction(act_bar)

    def _open_user_selector(self):
        tgm_info = get_telegram_info()
        config = PLSSelectorConfig(machine=tgm_info.machine,
                                   group=tgm_info.group,
                                   line=tgm_info.line,
                                   enabled=tgm_info.found_in_context)
        dialog = PLSSelectorDialog(config=config, parent=self)
        dialog.selector_selected.connect(self._on_timing_selector_updated)
        dialog.exec_()

    def _open_bar_config(self):
        parent = cast(PLSToolbarWidget, self.parent())
        dialog = PLSTimingConfigDialog(config=parent.config, parent=self)
        dialog.config_updated.connect(self._on_timing_config_updated)
        dialog.exec_()

    def _on_timing_config_updated(self, update: PLSToolbarConfig):
        parent = cast(PLSToolbarWidget, self.parent())
        parent.config = update

    def _on_timing_selector_updated(self, new_selector: str):
        cast(CApplication, CApplication.instance()).main_window.window_context.selector = new_selector

    def set_toggle_action_enable(self, is_already_enabled: bool):
        self.act_toggle.setIcon(IconFont().icon('eye-slash' if is_already_enabled else 'eye'))
        self.act_toggle.setText('Hide selector' if is_already_enabled else 'Show selector')


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
        self._btn.act_toggle.triggered.connect(self._on_selector_toggled)

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
        app = cast(CApplication, CApplication.instance())
        self._update_btn_menu(config)
        if config.show_sel:
            self._update_btn_text()
            app.main_window.window_context.selectorChanged.connect(self._update_btn_text)
        else:
            app.main_window.window_context.selectorChanged.disconnect(self._update_btn_text)
            self._btn.setText('PLS')

    def _update_btn_text(self):
        app = cast(CApplication, CApplication.instance())
        app_selector = app.main_window.window_context.selector or 'None'
        self._btn.setText(f'PLS: {app_selector}')

    def _update_btn_menu(self, config: Optional[PLSToolbarConfig] = None):
        if config is None:
            config = self._config
        self._btn.set_toggle_action_enable(config.show_sel)

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

    def _on_selector_toggled(self):
        config = self._config
        config.show_sel = not config.show_sel
        self._update_view_for_config(config)


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
