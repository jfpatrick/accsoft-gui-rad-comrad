import pytest
import os
from datetime import datetime
from pytestqt.qtbot import QtBot
from typing import List, cast
from unittest import mock
from qtpy.QtWidgets import QToolBar, QApplication
from accwidgets.timing_bar._model import TimingUpdate
from comrad import CApplication
from comrad.app.plugins.toolbar.pls_plugin import (PLSToolbarConfig, PLSToolbarWidget, TimingBar, TelegramInfo,
                                                   TimingBarDomain, DEFAULT_DOMAIN, get_telegram_info)


@pytest.fixture(autouse=True)
def clean_env():
    try:
        del os.environ['PLS_TELEGRAM']
    except KeyError:
        pass


@pytest.fixture(autouse=True, scope='function')
def mock_pyjapc():
    with mock.patch('comrad.data.pyjapc_patch.CPyJapc.instance'):
        yield


@pytest.mark.parametrize('tgm_var,window_selector,expected_machine,expected_group,expected_line,expect_found_in_context', [
    (None, None, None, None, None, False),
    (None, '', None, None, None, False),
    (None, 'TEST.USER2.ALL', 'TEST', 'USER2', 'ALL', True),
    ('LHC', None, 'LHC', 'USER', 'ALL', False),
    ('LHC', '', 'LHC', 'USER', 'ALL', False),
    ('LHC', 'TEST.USER2.ALL', 'TEST', 'USER2', 'ALL', True),
    ('SPS', None, 'SPS', 'USER', 'ALL', False),
    ('SPS', '', 'SPS', 'USER', 'ALL', False),
    ('SPS', 'TEST.USER2.ALL', 'TEST', 'USER2', 'ALL', True),
])
@mock.patch('comrad.CApplication.instance')
def test_get_telegram_info(app, tgm_var, window_selector, expect_found_in_context, expected_group, expected_line, expected_machine):
    app.return_value.main_window.window_context.selector = window_selector
    if tgm_var:
        os.environ['PLS_TELEGRAM'] = tgm_var
    assert get_telegram_info() == TelegramInfo(machine=expected_machine,
                                               group=expected_group,
                                               line=expected_line,
                                               found_in_context=expect_found_in_context)


@pytest.mark.parametrize('input,expected_show_bar,expected_supercycle,expected_show_domain,expected_show_time,'
                         'expected_show_start,expected_show_user,expected_show_lsa,expected_show_tz,'
                         'expected_microseconds,expected_heartbeat,expected_utc,expected_sel', [
                             (None, False, True, True, True, True, True, True, False, False, True, False, True),
                             ({'show_bar': '1'}, True, True, True, True, True, True, True, False, False, True, False, True),
                             ({'show_sel': '1'}, False, True, True, True, True, True, True, False, False, True, False, True),
                             ({'supercycle': '1'}, False, True, True, True, True, True, True, False, False, True, False, True),
                             ({'show_domain': '1'}, False, True, True, True, True, True, True, False, False, True, False, True),
                             ({'show_time': '1'}, False, True, True, True, True, True, True, False, False, True, False, True),
                             ({'show_start': '1'}, False, True, True, True, True, True, True, False, False, True, False, True),
                             ({'show_user': '1'}, False, True, True, True, True, True, True, False, False, True, False, True),
                             ({'show_lsa': '1'}, False, True, True, True, True, True, True, False, False, True, False, True),
                             ({'show_tz': '1'}, False, True, True, True, True, True, True, True, False, True, False, True),
                             ({'microseconds': '1'}, False, True, True, True, True, True, True, False, True, True, False, True),
                             ({'heartbeat': '1'}, False, True, True, True, True, True, True, False, False, True, False, True),
                             ({'utc': '1'}, False, True, True, True, True, True, True, False, False, True, True, True),
                             ({'show_bar': '0'}, False, True, True, True, True, True, True, False, False, True, False, True),
                             ({'supercycle': '0'}, False, False, True, True, True, True, True, False, False, True, False, True),
                             ({'show_domain': '0'}, False, True, False, True, True, True, True, False, False, True, False, True),
                             ({'show_time': '0'}, False, True, True, False, True, True, True, False, False, True, False, True),
                             ({'show_start': '0'}, False, True, True, True, False, True, True, False, False, True, False, True),
                             ({'show_user': '0'}, False, True, True, True, True, False, True, False, False, True, False, True),
                             ({'show_lsa': '0'}, False, True, True, True, True, True, False, False, False, True, False, True),
                             ({'show_tz': '0'}, False, True, True, True, True, True, True, False, False, True, False, True),
                             ({'show_sel': '0'}, False, True, True, True, True, True, True, False, False, True, False, False),
                             ({'microseconds': '0'}, False, True, True, True, True, True, True, False, False, True, False, True),
                             ({'heartbeat': '0'}, False, True, True, True, True, True, True, False, False, False, False, True),
                             ({'utc': '0'}, False, True, True, True, True, True, True, False, False, True, False, True),
                             ({'show_bar': '1', 'show_lsa': '1'}, True, True, True, True, True, True, True, False, False, True, False, True),
                             ({'show_bar': '1', 'show_lsa': '0'}, True, True, True, True, True, True, False, False, False, True, False, True),
                             ({'show_bar': '0', 'show_lsa': '1'}, False, True, True, True, True, True, True, False, False, True, False, True),
                             ({'show_bar': '0', 'show_lsa': '0'}, False, True, True, True, True, True, False, False, False, True, False, True),
                             ({'show_bar': 1, 'show_lsa': 1}, False, True, True, True, True, True, True, False, False, True, False, True),
                             ({'show_bar': '1', 'show_lsa': 0}, True, True, True, True, True, True, True, False, False, True, False, True),
                             ({'show_bar': 0, 'show_lsa': '0'}, False, True, True, True, True, True, False, False, False, True, False, True),
                             ({'show_bar': 0, 'show_lsa': 0}, False, True, True, True, True, True, True, False, False, True, False, True),
                             ({'show_bar': '', 'show_lsa': ''}, False, True, True, True, True, True, True, False, False, True, False, True),
                             ({'show_bar': 'unused', 'show_lsa': 'unused'}, False, True, True, True, True, True, True, False, False, True, False, True),
                             ({'unused': 'unused'}, False, True, True, True, True, True, True, False, False, True, False, True),
                             ({'show_bar': '='}, False, True, True, True, True, True, True, False, False, True, False, True),
                         ])
def test_config_parse(input, expected_heartbeat, expected_microseconds, expected_show_bar, expected_show_domain,
                      expected_show_lsa, expected_show_start, expected_show_time, expected_show_tz, expected_show_user,
                      expected_supercycle, expected_utc, expected_sel):
    config = PLSToolbarConfig.parse(input)
    assert config.heartbeat == expected_heartbeat
    assert config.microseconds == expected_microseconds
    assert config.show_bar == expected_show_bar
    assert config.show_domain == expected_show_domain
    assert config.show_lsa == expected_show_lsa
    assert config.show_start == expected_show_start
    assert config.show_time == expected_show_time
    assert config.show_tz == expected_show_tz
    assert config.show_user == expected_show_user
    assert config.supercycle == expected_supercycle
    assert config.utc == expected_utc
    assert config.show_sel == expected_sel


@pytest.mark.parametrize('config,expect_bar_exists,expect_showing_domain,expect_showing_time,expect_showing_start,'
                         'expect_showing_user,expect_showing_lsa,expect_render_supercycle,expect_us,expect_tz,'
                         'expect_heartbeat,expected_displayed_timezone', [
                             (None, False, None, None, None, None, None, None, None, None, None, None),
                             ({}, False, None, None, None, None, None, None, None, None, None, None),
                             ({'show_bar': '1'}, True, True, True, True, True, True, True, False, False, True, TimingBar.TimeZone.LOCAL),
                             ({'show_bar': '1', 'utc': '0'}, True, True, True, True, True, True, True, False, False, True, TimingBar.TimeZone.LOCAL),
                             ({'show_bar': '1', 'utc': '1'}, True, True, True, True, True, True, True, False, False, True, TimingBar.TimeZone.UTC),
                             ({'show_bar': '1', 'show_domain': '0'}, True, False, True, True, True, True, True, False, False, True, TimingBar.TimeZone.LOCAL),
                             ({'show_bar': '1', 'show_time': '0'}, True, True, False, True, True, True, True, False, False, True, TimingBar.TimeZone.LOCAL),
                             ({'show_bar': '1', 'show_domain': '0', 'show_time': '0'}, True, False, False, True, True, True, True, False, False, True, TimingBar.TimeZone.LOCAL),
                             ({'show_bar': '1', 'show_lsa': '0'}, True, True, True, True, True, False, True, False, False, True, TimingBar.TimeZone.LOCAL),
                             ({'show_bar': '1', 'show_user': '0'}, True, True, True, True, False, True, True, False, False, True, TimingBar.TimeZone.LOCAL),
                             ({'show_bar': '1', 'supercycle': '0'}, True, True, True, True, True, True, False, False, False, True, TimingBar.TimeZone.LOCAL),
                             ({'show_bar': '1', 'microseconds': '1'}, True, True, True, True, True, True, True, True, False, True, TimingBar.TimeZone.LOCAL),
                             ({'show_bar': '1', 'show_tz': '1'}, True, True, True, True, True, True, True, False, True, True, TimingBar.TimeZone.LOCAL),
                             ({'show_bar': '1', 'heartbeat': '0'}, True, True, True, True, True, True, True, False, False, False, TimingBar.TimeZone.LOCAL),
                             ({'show_bar': '1', 'show_tz': '1', 'utc': '1'}, True, True, True, True, True, True, True, False, True, True, TimingBar.TimeZone.UTC),
                         ])
def test_toolbar_widget_initialize_with_config(config, expect_bar_exists, expected_displayed_timezone, expect_heartbeat,
                                               expect_render_supercycle, expect_showing_domain, expect_showing_lsa,
                                               expect_showing_start, expect_showing_time, expect_showing_user,
                                               expect_tz, expect_us, qtbot: QtBot):
    QApplication.instance().main_window.ui.navbar = QToolBar()
    widget = PLSToolbarWidget(config=config)
    qtbot.add_widget(widget)
    timing_bars: List[TimingBar] = [w for w in widget.children() if isinstance(w, TimingBar)]
    if not expect_bar_exists:
        assert len(timing_bars) == 0
        return

    assert len(timing_bars) == 1
    bar = timing_bars[0]
    assert bar.displayedTimeZone == expected_displayed_timezone
    assert bar.indicateHeartbeat == expect_heartbeat
    assert bar.renderSuperCycle == expect_render_supercycle
    assert bool(bar.labels & TimingBar.Labels.TIMING_DOMAIN) == expect_showing_domain
    assert bool(bar.labels & TimingBar.Labels.LSA_CYCLE_NAME) == expect_showing_lsa
    assert bool(bar.labels & TimingBar.Labels.CYCLE_START) == expect_showing_start
    assert bool(bar.labels & TimingBar.Labels.DATETIME) == expect_showing_time
    assert bool(bar.labels & TimingBar.Labels.USER) == expect_showing_user
    assert bar.showTimeZone == expect_tz
    assert bar.showMicroSeconds == expect_us


@pytest.mark.parametrize('config,expect_bar_exists,expect_showing_domain,expect_showing_time,expect_showing_start,'
                         'expect_showing_user,expect_showing_lsa,expect_render_supercycle,expect_us,expect_tz,'
                         'expect_heartbeat,expected_displayed_timezone', [
                             (None, False, None, None, None, None, None, None, None, None, None, None),
                             ({}, False, None, None, None, None, None, None, None, None, None, None),
                             ({'show_bar': '1'}, True, True, True, True, True, True, True, False, False, True, TimingBar.TimeZone.LOCAL),
                             ({'show_bar': '1', 'utc': '0'}, True, True, True, True, True, True, True, False, False, True, TimingBar.TimeZone.LOCAL),
                             ({'show_bar': '1', 'utc': '1'}, True, True, True, True, True, True, True, False, False, True, TimingBar.TimeZone.UTC),
                             ({'show_bar': '1', 'show_domain': '0'}, True, False, True, True, True, True, True, False, False, True, TimingBar.TimeZone.LOCAL),
                             ({'show_bar': '1', 'show_time': '0'}, True, True, False, True, True, True, True, False, False, True, TimingBar.TimeZone.LOCAL),
                             ({'show_bar': '1', 'show_domain': '0', 'show_time': '0'}, True, False, False, True, True, True, True, False, False, True, TimingBar.TimeZone.LOCAL),
                             ({'show_bar': '1', 'show_lsa': '0'}, True, True, True, True, True, False, True, False, False, True, TimingBar.TimeZone.LOCAL),
                             ({'show_bar': '1', 'show_user': '0'}, True, True, True, True, False, True, True, False, False, True, TimingBar.TimeZone.LOCAL),
                             ({'show_bar': '1', 'supercycle': '0'}, True, True, True, True, True, True, False, False, False, True, TimingBar.TimeZone.LOCAL),
                             ({'show_bar': '1', 'microseconds': '1'}, True, True, True, True, True, True, True, True, False, True, TimingBar.TimeZone.LOCAL),
                             ({'show_bar': '1', 'show_tz': '1'}, True, True, True, True, True, True, True, False, True, True, TimingBar.TimeZone.LOCAL),
                             ({'show_bar': '1', 'heartbeat': '0'}, True, True, True, True, True, True, True, False, False, False, TimingBar.TimeZone.LOCAL),
                             ({'show_bar': '1', 'show_tz': '1', 'utc': '1'}, True, True, True, True, True, True, True, False, True, True, TimingBar.TimeZone.UTC),
                         ])
def test_toolbar_widget_update_view_from_config(config, expect_bar_exists, expected_displayed_timezone, expect_heartbeat,
                                                expect_render_supercycle, expect_showing_domain, expect_showing_lsa,
                                                expect_showing_start, expect_showing_time, expect_showing_user,
                                                expect_tz, expect_us, qtbot: QtBot):
    QApplication.instance().main_window.ui.navbar = QToolBar()
    widget = PLSToolbarWidget()
    qtbot.add_widget(widget)
    widget.config = PLSToolbarConfig.parse(config)
    timing_bars: List[TimingBar] = [w for w in widget.children() if isinstance(w, TimingBar)]
    if not expect_bar_exists:
        assert len(timing_bars) == 0
        return

    assert len(timing_bars) == 1
    bar = timing_bars[0]
    assert bar.displayedTimeZone == expected_displayed_timezone
    assert bar.indicateHeartbeat == expect_heartbeat
    assert bar.renderSuperCycle == expect_render_supercycle
    assert bool(bar.labels & TimingBar.Labels.TIMING_DOMAIN) == expect_showing_domain
    assert bool(bar.labels & TimingBar.Labels.LSA_CYCLE_NAME) == expect_showing_lsa
    assert bool(bar.labels & TimingBar.Labels.CYCLE_START) == expect_showing_start
    assert bool(bar.labels & TimingBar.Labels.DATETIME) == expect_showing_time
    assert bool(bar.labels & TimingBar.Labels.USER) == expect_showing_user
    assert bar.showTimeZone == expect_tz
    assert bar.showMicroSeconds == expect_us


@pytest.mark.parametrize('tgm_var', [None, 'LHC', 'ADE', 'SCT', 'PSB', 'FCT'])
@pytest.mark.parametrize('pls_config', [
    None,
    (TimingBarDomain.LHC, None),
    (TimingBarDomain.LEI, None),
    (TimingBarDomain.PSB, None),
    (TimingBarDomain.LHC, 'USER1'),
    (TimingBarDomain.LEI, 'USER1'),
    (TimingBarDomain.PSB, 'USER1'),
])
@mock.patch('comrad.app.plugins.toolbar.pls_plugin.get_bar_config_for_current_selector')
@mock.patch('comrad.app.plugins.toolbar.pls_plugin.TimingBarModel')
@mock.patch('comrad.app.plugins.toolbar.pls_plugin.TimingBar._connect_model')
def test_toolbar_widget_bar_always_uses_pyjapc_singleton(_, TimingBarModel, get_bar_config_for_current_selector, pls_config, tgm_var, qtbot: QtBot):
    if tgm_var:
        os.environ['PLS_TELEGRAM'] = tgm_var
    from comrad.data.pyjapc_patch import CPyJapc
    pyjapc_instance = CPyJapc.instance()
    get_bar_config_for_current_selector.return_value = pls_config
    QApplication.instance().main_window.ui.navbar = QToolBar()
    widget = PLSToolbarWidget()
    qtbot.add_widget(widget)
    TimingBarModel.reset_mock()
    widget.config = PLSToolbarConfig(show_bar=True)
    try:
        TimingBarModel.assert_called_once_with(japc=pyjapc_instance)
    except AssertionError:
        TimingBarModel.assert_called_once_with(japc=pyjapc_instance, domain=mock.ANY)


@pytest.mark.parametrize('tgm_var,expected_original_domain', [
    (None, DEFAULT_DOMAIN),
    ('LHC', TimingBarDomain.LHC),
    ('ADE', TimingBarDomain.ADE),
    ('SCT', DEFAULT_DOMAIN),
    ('PSB', TimingBarDomain.PSB),
    ('FCT', DEFAULT_DOMAIN),
])
@pytest.mark.parametrize('initial_domain,expected_initial_domain', [
    (DEFAULT_DOMAIN, DEFAULT_DOMAIN),
    (TimingBarDomain.LEI, TimingBarDomain.LEI),
])
@pytest.mark.parametrize('show_bar', [True, False])
@pytest.mark.parametrize('selector,expected_highlighted_user,expected_domain', [
    ('ADE.USER.ALL', None, TimingBarDomain.ADE),
    ('ADE.USER.ADE', 'ADE', TimingBarDomain.ADE),
    ('CPS.USER.AD', 'AD', TimingBarDomain.CPS),
    ('CPS.USER.MD1', 'MD1', TimingBarDomain.CPS),
    ('CPS.USER.MD2', 'MD2', TimingBarDomain.CPS),
    ('CPS.USER.MD3', 'MD3', TimingBarDomain.CPS),
    ('CPS.USER.MD4', 'MD4', TimingBarDomain.CPS),
    ('CPS.USER.MD5', 'MD5', TimingBarDomain.CPS),
    ('CPS.USER.MD6', 'MD6', TimingBarDomain.CPS),
    ('CPS.USER.MD7', 'MD7', TimingBarDomain.CPS),
    ('CPS.USER.MD8', 'MD8', TimingBarDomain.CPS),
    ('CPS.USER.MD9', 'MD9', TimingBarDomain.CPS),
    ('CPS.USER.MD10', 'MD10', TimingBarDomain.CPS),
    ('CPS.USER.SFTPRO1', 'SFTPRO1', TimingBarDomain.CPS),
    ('CPS.USER.SFTPRO2', 'SFTPRO2', TimingBarDomain.CPS),
    ('CPS.USER.SFTPRO3', 'SFTPRO3', TimingBarDomain.CPS),
    ('CPS.USER.ION1', 'ION1', TimingBarDomain.CPS),
    ('CPS.USER.ION2', 'ION2', TimingBarDomain.CPS),
    ('CPS.USER.ION3', 'ION3', TimingBarDomain.CPS),
    ('CPS.USER.LHC1', 'LHC1', TimingBarDomain.CPS),
    ('CPS.USER.LHC2', 'LHC2', TimingBarDomain.CPS),
    ('CPS.USER.LHC3', 'LHC3', TimingBarDomain.CPS),
    ('CPS.USER.LHC4', 'LHC4', TimingBarDomain.CPS),
    ('CPS.USER.LHC5', 'LHC5', TimingBarDomain.CPS),
    ('CPS.USER.LHCIND1', 'LHCIND1', TimingBarDomain.CPS),
    ('CPS.USER.LHCIND2', 'LHCIND2', TimingBarDomain.CPS),
    ('CPS.USER.LHCIND3', 'LHCIND3', TimingBarDomain.CPS),
    ('CPS.USER.TOF', 'TOF', TimingBarDomain.CPS),
    ('CPS.USER.ZERO', 'ZERO', TimingBarDomain.CPS),
    ('CPS.USER.EAST1', 'EAST1', TimingBarDomain.CPS),
    ('CPS.USER.EAST2', 'EAST2', TimingBarDomain.CPS),
    ('CPS.USER.EAST3', 'EAST3', TimingBarDomain.CPS),
    ('CPS.USER.EAST4', 'EAST4', TimingBarDomain.CPS),
    ('CPS.USER.ALL', None, TimingBarDomain.CPS),
    ('FCT.USER.ALL', None, DEFAULT_DOMAIN),  # Domain unknown, bar remains in initial state
    ('LEI.USER.AMD', 'AMD', TimingBarDomain.LEI),
    ('LEI.USER.AMDEC', 'AMDEC', TimingBarDomain.LEI),
    ('LEI.USER.AMDNOM', 'AMDNOM', TimingBarDomain.LEI),
    ('LEI.USER.AMDOPTIC', 'AMDOPTIC', TimingBarDomain.LEI),
    ('LEI.USER.AMDRF', 'AMDRF', TimingBarDomain.LEI),
    ('LEI.USER.ANOMINAL', 'ANOMINAL', TimingBarDomain.LEI),
    ('LEI.USER.BIOMD', 'BIOMD', TimingBarDomain.LEI),
    ('LEI.USER.LIN3MEAS', 'LIN3MEAS', TimingBarDomain.LEI),
    ('LEI.USER.MD1', 'MD1', TimingBarDomain.LEI),
    ('LEI.USER.MD2', 'MD2', TimingBarDomain.LEI),
    ('LEI.USER.MD3', 'MD3', TimingBarDomain.LEI),
    ('LEI.USER.MD4', 'MD4', TimingBarDomain.LEI),
    ('LEI.USER.MD5', 'MD5', TimingBarDomain.LEI),
    ('LEI.USER.MD6', 'MD6', TimingBarDomain.LEI),
    ('LEI.USER.MD7', 'MD7', TimingBarDomain.LEI),
    ('LEI.USER.MD8', 'MD8', TimingBarDomain.LEI),
    ('LEI.USER.MDEARLY', 'MDEARLY', TimingBarDomain.LEI),
    ('LEI.USER.MDEC', 'MDEC', TimingBarDomain.LEI),
    ('LEI.USER.MDNOM', 'MDNOM', TimingBarDomain.LEI),
    ('LEI.USER.MDOPTIC', 'MDOPTIC', TimingBarDomain.LEI),
    ('LEI.USER.MDRF', 'MDRF', TimingBarDomain.LEI),
    ('LEI.USER.MD_100NS', 'MD_100NS', TimingBarDomain.LEI),
    ('LEI.USER.MD_75NS', 'MD_75NS', TimingBarDomain.LEI),
    ('LEI.USER.FL_IN_MD', 'FL_IN_MD', TimingBarDomain.LEI),
    ('LEI.USER.FL_IN_SU', 'FL_IN_SU', TimingBarDomain.LEI),
    ('LEI.USER.FL_NO_MD', 'FL_NO_MD', TimingBarDomain.LEI),
    ('LEI.USER.POLARITY', 'POLARITY', TimingBarDomain.LEI),
    ('LEI.USER.L3_MONIT', 'L3_MONIT', TimingBarDomain.LEI),
    ('LEI.USER.ZERO', 'ZERO', TimingBarDomain.LEI),
    ('LEI.USER.EARLY', 'EARLY', TimingBarDomain.LEI),
    ('LEI.USER.NOMINAL', 'NOMINAL', TimingBarDomain.LEI),
    ('LEI.USER.NOM_75NS', 'NOM_75NS', TimingBarDomain.LEI),
    ('LEI.USER.ALL', None, TimingBarDomain.LEI),
    ('LHC.USER.ALL', None, TimingBarDomain.LHC),
    ('LHC.USER.LHC', 'LHC', TimingBarDomain.LHC),
    ('LNA.USER.PBMD1', 'PBMD1', TimingBarDomain.LNA),
    ('LNA.USER.PBMD2', 'PBMD2', TimingBarDomain.LNA),
    ('LNA.USER.PBMD3', 'PBMD3', TimingBarDomain.LNA),
    ('LNA.USER.PBMDEC', 'PBMDEC', TimingBarDomain.LNA),
    ('LNA.USER.PBMDOPT', 'PBMDOPT', TimingBarDomain.LNA),
    ('LNA.USER.PBMDRF', 'PBMDRF', TimingBarDomain.LNA),
    ('LNA.USER.PBPRD1', 'PBPRD1', TimingBarDomain.LNA),
    ('LNA.USER.PBPRD2', 'PBPRD2', TimingBarDomain.LNA),
    ('LNA.USER.PMD1', 'PMD1', TimingBarDomain.LNA),
    ('LNA.USER.PMD2', 'PMD2', TimingBarDomain.LNA),
    ('LNA.USER.PMD3', 'PMD3', TimingBarDomain.LNA),
    ('LNA.USER.PMDEC', 'PMDEC', TimingBarDomain.LNA),
    ('LNA.USER.PMDOPT', 'PMDOPT', TimingBarDomain.LNA),
    ('LNA.USER.PMDRF', 'PMDRF', TimingBarDomain.LNA),
    ('LNA.USER.PPROD1', 'PPROD1', TimingBarDomain.LNA),
    ('LNA.USER.PPROD2', 'PPROD2', TimingBarDomain.LNA),
    ('LNA.USER.HMMD1', 'HMMD1', TimingBarDomain.LNA),
    ('LNA.USER.HMMD2', 'HMMD2', TimingBarDomain.LNA),
    ('LNA.USER.HMMDEC', 'HMMDEC', TimingBarDomain.LNA),
    ('LNA.USER.HMMDOPT', 'HMMDOPT', TimingBarDomain.LNA),
    ('LNA.USER.HMMDRF', 'HMMDRF', TimingBarDomain.LNA),
    ('LNA.USER.HMPROD1', 'HMPROD1', TimingBarDomain.LNA),
    ('LNA.USER.HMPROD2', 'HMPROD2', TimingBarDomain.LNA),
    ('LNA.USER.ZERO', 'ZERO', TimingBarDomain.LNA),
    ('LNA.USER.ALL', None, TimingBarDomain.LNA),
    ('PSB.USER.AD', 'AD', TimingBarDomain.PSB),
    ('PSB.USER.MD1', 'MD1', TimingBarDomain.PSB),
    ('PSB.USER.MD2', 'MD2', TimingBarDomain.PSB),
    ('PSB.USER.MD3', 'MD3', TimingBarDomain.PSB),
    ('PSB.USER.MD4', 'MD4', TimingBarDomain.PSB),
    ('PSB.USER.MD5', 'MD5', TimingBarDomain.PSB),
    ('PSB.USER.M6', 'M6', TimingBarDomain.PSB),
    ('PSB.USER.MD7', 'MD7', TimingBarDomain.PSB),
    ('PSB.USER.MD8', 'MD8', TimingBarDomain.PSB),
    ('PSB.USER.MD9', 'MD9', TimingBarDomain.PSB),
    ('PSB.USER.MD10', 'MD10', TimingBarDomain.PSB),
    ('PSB.USER.SFTPRO1', 'SFTPRO1', TimingBarDomain.PSB),
    ('PSB.USER.SFTPRO2', 'SFTPRO2', TimingBarDomain.PSB),
    ('PSB.USER.LHC1A', 'LHC1A', TimingBarDomain.PSB),
    ('PSB.USER.LHC1B', 'LHC1B', TimingBarDomain.PSB),
    ('PSB.USER.LHC2A', 'LHC2A', TimingBarDomain.PSB),
    ('PSB.USER.LHC2B', 'LHC2B', TimingBarDomain.PSB),
    ('PSB.USER.LHC3', 'LHC3', TimingBarDomain.PSB),
    ('PSB.USER.LHC4', 'LHC4', TimingBarDomain.PSB),
    ('PSB.USER.LHC5', 'LHC5', TimingBarDomain.PSB),
    ('PSB.USER.LHCIND1', 'LHCIND1', TimingBarDomain.PSB),
    ('PSB.USER.LHCIND2', 'LHCIND2', TimingBarDomain.PSB),
    ('PSB.USER.LHCIND3', 'LHCIND3', TimingBarDomain.PSB),
    ('PSB.USER.LHCPILOT', 'LHCPILOT', TimingBarDomain.PSB),
    ('PSB.USER.STAGISO', 'STAGISO', TimingBarDomain.PSB),
    ('PSB.USER.TOF', 'TOF', TimingBarDomain.PSB),
    ('PSB.USER.ZERO', 'ZERO', TimingBarDomain.PSB),
    ('PSB.USER.EAST1', 'EAST1', TimingBarDomain.PSB),
    ('PSB.USER.EAST2', 'EAST2', TimingBarDomain.PSB),
    ('PSB.USER.EAST3', 'EAST3', TimingBarDomain.PSB),
    ('PSB.USER.NORMGPS', 'NORMGPS', TimingBarDomain.PSB),
    ('PSB.USER.NORMHRS', 'NORMHRS', TimingBarDomain.PSB),
    ('PSB.USER.ALL', None, TimingBarDomain.PSB),
    ('SCT.USER.SETUP', None, DEFAULT_DOMAIN),  # Domain unknown, bar remains in initial state
    ('SCT.USER.ALL', None, DEFAULT_DOMAIN),  # Domain unknown, bar remains in initial state
    ('SPS.USER.AWAKE1', 'AWAKE1', TimingBarDomain.SPS),
    ('SPS.USER.MD1', 'MD1', TimingBarDomain.SPS),
    ('SPS.USER.MD2', 'MD2', TimingBarDomain.SPS),
    ('SPS.USER.MD3', 'MD3', TimingBarDomain.SPS),
    ('SPS.USER.MD4', 'MD4', TimingBarDomain.SPS),
    ('SPS.USER.MD5', 'MD5', TimingBarDomain.SPS),
    ('SPS.USER.SFTION1', 'SFTION1', TimingBarDomain.SPS),
    ('SPS.USER.SFTION2', 'SFTION2', TimingBarDomain.SPS),
    ('SPS.USER.SFTION3', 'SFTION3', TimingBarDomain.SPS),
    ('SPS.USER.SFTION4', 'SFTION4', TimingBarDomain.SPS),
    ('SPS.USER.SFTPRO1', 'SFTPRO1', TimingBarDomain.SPS),
    ('SPS.USER.SFTPRO2', 'SFTPRO2', TimingBarDomain.SPS),
    ('SPS.USER.SFTSHIP', 'SFTSHIP', TimingBarDomain.SPS),
    ('SPS.USER.HIRADMT1', 'HIRADMT1', TimingBarDomain.SPS),
    ('SPS.USER.HIRADMT2', 'HIRADMT2', TimingBarDomain.SPS),
    ('SPS.USER.LHC1', 'LHC1', TimingBarDomain.SPS),
    ('SPS.USER.LHC2', 'LHC2', TimingBarDomain.SPS),
    ('SPS.USER.LHC3', 'LHC3', TimingBarDomain.SPS),
    ('SPS.USER.LHC4', 'LHC4', TimingBarDomain.SPS),
    ('SPS.USER.LHC25NS', 'LHC25NS', TimingBarDomain.SPS),
    ('SPS.USER.LHC50NS', 'LHC50NS', TimingBarDomain.SPS),
    ('SPS.USER.LHCINDIV', 'LHCINDIV', TimingBarDomain.SPS),
    ('SPS.USER.LHCION1', 'LHCION1', TimingBarDomain.SPS),
    ('SPS.USER.LHCION2', 'LHCION2', TimingBarDomain.SPS),
    ('SPS.USER.LHCION3', 'LHCION3', TimingBarDomain.SPS),
    ('SPS.USER.LHCION4', 'LHCION4', TimingBarDomain.SPS),
    ('SPS.USER.LHCMD1', 'LHCMD1', TimingBarDomain.SPS),
    ('SPS.USER.LHCMD2', 'LHCMD2', TimingBarDomain.SPS),
    ('SPS.USER.LHCMD3', 'LHCMD3', TimingBarDomain.SPS),
    ('SPS.USER.LHCMD4', 'LHCMD4', TimingBarDomain.SPS),
    ('SPS.USER.LHCPILOT', 'LHCPILOT', TimingBarDomain.SPS),
    ('SPS.USER.ZERO', 'ZERO', TimingBarDomain.SPS),
    ('SPS.USER.ALL', None, TimingBarDomain.SPS),
])
def test_toolbar_widget_update_view_on_selector_change_from_none_selector(qtbot: QtBot, show_bar, selector, expected_domain,
                                                                          expected_highlighted_user, tgm_var, expected_original_domain,
                                                                          initial_domain, expected_initial_domain):
    if tgm_var:
        os.environ['PLS_TELEGRAM'] = tgm_var
    QApplication.instance().main_window.ui.navbar = QToolBar()
    widget = PLSToolbarWidget()
    qtbot.add_widget(widget)
    widget.config = PLSToolbarConfig(show_bar=show_bar)
    timing_bars: List[TimingBar] = [w for w in widget.children() if isinstance(w, TimingBar)]
    if not show_bar:
        assert len(timing_bars) == 0
    else:
        assert len(timing_bars) == 1
        bar = timing_bars[0]
        assert bar.model.domain == expected_original_domain
        bar.model.domain = initial_domain

        assert bar.model.domain == expected_initial_domain
        assert bar.highlightedUser is None

    cast(CApplication, CApplication.instance()).main_window.window_context.selector = selector

    if not show_bar:
        timing_bars = [w for w in widget.children() if isinstance(w, TimingBar)]
        assert len(timing_bars) == 0
        return

    assert bar.model.domain == expected_domain
    assert bar.highlightedUser == expected_highlighted_user


@pytest.mark.parametrize('tgm_var,expected_new_domain,initial_selector,expected_initial_domain,expected_initial_user', [
    (None, DEFAULT_DOMAIN, None, DEFAULT_DOMAIN, None),
    ('LEI', TimingBarDomain.LEI, None, TimingBarDomain.LEI, None),
    ('CPS', TimingBarDomain.CPS, None, TimingBarDomain.CPS, None),
    ('ADE', TimingBarDomain.ADE, None, TimingBarDomain.ADE, None),
    ('SPS', TimingBarDomain.SPS, None, TimingBarDomain.SPS, None),
    ('LNA', TimingBarDomain.LNA, None, TimingBarDomain.LNA, None),
    ('LHC', TimingBarDomain.LHC, None, TimingBarDomain.LHC, None),
    ('PSB', TimingBarDomain.PSB, None, TimingBarDomain.PSB, None),
    ('SCT', DEFAULT_DOMAIN, None, DEFAULT_DOMAIN, None),
    ('FCT', DEFAULT_DOMAIN, None, DEFAULT_DOMAIN, None),
    (None, DEFAULT_DOMAIN, 'LEI.USER.MD1', TimingBarDomain.LEI, 'MD1'),
    ('LEI', TimingBarDomain.LEI, 'LEI.USER.MD1', TimingBarDomain.LEI, 'MD1'),
    ('CPS', TimingBarDomain.CPS, 'LEI.USER.MD1', TimingBarDomain.LEI, 'MD1'),
    ('ADE', TimingBarDomain.ADE, 'LEI.USER.MD1', TimingBarDomain.LEI, 'MD1'),
    ('SPS', TimingBarDomain.SPS, 'LEI.USER.MD1', TimingBarDomain.LEI, 'MD1'),
    ('LNA', TimingBarDomain.LNA, 'LEI.USER.MD1', TimingBarDomain.LEI, 'MD1'),
    ('LHC', TimingBarDomain.LHC, 'LEI.USER.MD1', TimingBarDomain.LEI, 'MD1'),
    ('PSB', TimingBarDomain.PSB, 'LEI.USER.MD1', TimingBarDomain.LEI, 'MD1'),
    ('SCT', DEFAULT_DOMAIN, 'LEI.USER.MD1', TimingBarDomain.LEI, 'MD1'),
    ('FCT', DEFAULT_DOMAIN, 'LEI.USER.MD1', TimingBarDomain.LEI, 'MD1'),
    (None, DEFAULT_DOMAIN, 'PSB.USER.ALL', TimingBarDomain.PSB, None),
    ('LEI', TimingBarDomain.LEI, 'PSB.USER.ALL', TimingBarDomain.PSB, None),
    ('CPS', TimingBarDomain.CPS, 'PSB.USER.ALL', TimingBarDomain.PSB, None),
    ('ADE', TimingBarDomain.ADE, 'PSB.USER.ALL', TimingBarDomain.PSB, None),
    ('SPS', TimingBarDomain.SPS, 'PSB.USER.ALL', TimingBarDomain.PSB, None),
    ('LNA', TimingBarDomain.LNA, 'PSB.USER.ALL', TimingBarDomain.PSB, None),
    ('LHC', TimingBarDomain.LHC, 'PSB.USER.ALL', TimingBarDomain.PSB, None),
    ('PSB', TimingBarDomain.PSB, 'PSB.USER.ALL', TimingBarDomain.PSB, None),
    ('SCT', DEFAULT_DOMAIN, 'PSB.USER.ALL', TimingBarDomain.PSB, None),
    ('FCT', DEFAULT_DOMAIN, 'PSB.USER.ALL', TimingBarDomain.PSB, None),
])
def test_toolbar_widget_update_view_on_selector_change_to_none_selector(qtbot: QtBot, initial_selector, expected_initial_domain,
                                                                        expected_initial_user, tgm_var, expected_new_domain):
    if tgm_var:
        os.environ['PLS_TELEGRAM'] = tgm_var
    QApplication.instance().main_window.ui.navbar = QToolBar()
    widget = PLSToolbarWidget()
    qtbot.add_widget(widget)
    widget.config = PLSToolbarConfig(show_bar=True)
    timing_bars: List[TimingBar] = [w for w in widget.children() if isinstance(w, TimingBar)]
    assert len(timing_bars) == 1
    bar = timing_bars[0]
    cast(CApplication, CApplication.instance()).main_window.window_context.selector = initial_selector
    assert bar.model.domain == expected_initial_domain
    assert bar.highlightedUser == expected_initial_user
    cast(CApplication, CApplication.instance()).main_window.window_context.selector = None
    assert bar.model.domain == expected_new_domain
    assert bar.highlightedUser is None


def test_toolbar_widget_adapts_bar_size_to_size_hint_on_new_data(qtbot: QtBot):
    QApplication.instance().main_window.ui.navbar = QToolBar()
    widget = PLSToolbarWidget()
    qtbot.add_widget(widget)
    widget.config = PLSToolbarConfig(show_bar=True, show_user=True, show_lsa=True)
    timing_bars: List[TimingBar] = [w for w in widget.children() if isinstance(w, TimingBar)]
    assert len(timing_bars) == 1
    bar = timing_bars[0]
    widget.show()
    time = datetime.now()
    largest_width = widget.sizeHint().width()
    bar.model._last_info = TimingUpdate(timestamp=time, offset=0, user='SHORT', lsa_name='short')
    bar.model.timingUpdateReceived.emit(True)
    qtbot.wait(1)
    assert widget.sizeHint().width() > largest_width
    largest_width = widget.sizeHint().width()
    bar.model._last_info = TimingUpdate(timestamp=time, offset=0, user='BITLONGER', lsa_name='bitlonger')
    bar.model.timingUpdateReceived.emit(True)
    qtbot.wait(1)
    assert widget.sizeHint().width() > largest_width
    largest_width = widget.sizeHint().width()
    bar.model._last_info = TimingUpdate(timestamp=time, offset=0, user='EVEN_LONGER', lsa_name='even-longer')
    bar.model.timingUpdateReceived.emit(True)
    qtbot.wait(1)
    assert widget.sizeHint().width() > largest_width
    largest_width = widget.sizeHint().width()
    bar.model._last_info = TimingUpdate(timestamp=time, offset=0, user='SHORT', lsa_name='short')
    bar.model.timingUpdateReceived.emit(True)
    qtbot.wait(1)
    assert widget.sizeHint().width() == largest_width
    bar.model._last_info = TimingUpdate(timestamp=time, offset=0, user='BITLONGER', lsa_name='bitlonger')
    bar.model.timingUpdateReceived.emit(True)
    qtbot.wait(1)
    assert widget.sizeHint().width() == largest_width
    bar.model._last_info = TimingUpdate(timestamp=time, offset=0, user='EVEN_LONGER', lsa_name='even-longer')
    bar.model.timingUpdateReceived.emit(True)
    qtbot.wait(1)
    assert widget.sizeHint().width() == largest_width


def test_toolbar_widget_adapts_bar_size_to_size_hint_on_initial_error(qtbot: QtBot):
    QApplication.instance().main_window.ui.navbar = QToolBar()
    widget = PLSToolbarWidget()
    qtbot.add_widget(widget)
    widget.config = PLSToolbarConfig(show_bar=True, show_user=True, show_lsa=True)
    timing_bars: List[TimingBar] = [w for w in widget.children() if isinstance(w, TimingBar)]
    assert len(timing_bars) == 1
    bar = timing_bars[0]
    widget.show()
    largest_width = widget.sizeHint().width()
    bar.model.timingErrorReceived.emit('Sample error')
    qtbot.wait(1)
    assert widget.sizeHint().width() > largest_width
    largest_width = widget.sizeHint().width()
    bar.model.timingErrorReceived.emit('Another longer error')
    qtbot.wait(1)
    assert widget.sizeHint().width() == largest_width


def test_toolbar_widget_adapts_bar_size_to_size_hint_on_error_after_longer_data(qtbot: QtBot):
    QApplication.instance().main_window.ui.navbar = QToolBar()
    widget = PLSToolbarWidget()
    qtbot.add_widget(widget)
    widget.config = PLSToolbarConfig(show_bar=True, show_user=True, show_lsa=True)
    timing_bars: List[TimingBar] = [w for w in widget.children() if isinstance(w, TimingBar)]
    assert len(timing_bars) == 1
    bar = timing_bars[0]
    widget.show()
    time = datetime.now()
    largest_width = widget.sizeHint().width()
    bar.model._last_info = TimingUpdate(timestamp=time, offset=0, user='SUPER_DUPER_LONG', lsa_name='SUPER_DUPER_LONG')
    bar.model.timingUpdateReceived.emit(True)
    qtbot.wait(1)
    assert widget.sizeHint().width() > largest_width
    largest_width = widget.sizeHint().width()
    bar.model.timingErrorReceived.emit('Sample error')
    qtbot.wait(1)
    assert widget.sizeHint().width() == largest_width
    bar.model.timingErrorReceived.emit('Another longer error')
    qtbot.wait(1)
    assert widget.sizeHint().width() == largest_width


def test_toolbar_widget_adapts_bar_size_to_size_hint_on_error_after_shorter_data(qtbot: QtBot):
    QApplication.instance().main_window.ui.navbar = QToolBar()
    widget = PLSToolbarWidget()
    qtbot.add_widget(widget)
    widget.config = PLSToolbarConfig(show_bar=True, show_user=False, show_lsa=False, show_time=False)
    timing_bars: List[TimingBar] = [w for w in widget.children() if isinstance(w, TimingBar)]
    assert len(timing_bars) == 1
    bar = timing_bars[0]
    widget.show()
    time = datetime.now()
    largest_width = widget.sizeHint().width()
    bar.model._last_info = TimingUpdate(timestamp=time, offset=0, user='s', lsa_name='s')
    bar.model.timingUpdateReceived.emit(True)
    qtbot.wait(1)
    assert widget.sizeHint().width() < largest_width
    largest_width = widget.sizeHint().width()
    bar.model.timingErrorReceived.emit('Sample error')
    qtbot.wait(1)
    assert widget.sizeHint().width() > largest_width
    largest_width = widget.sizeHint().width()
    bar.model.timingErrorReceived.emit('Another longer error')
    qtbot.wait(1)
    assert widget.sizeHint().width() == largest_width


def test_toolbar_widget_adapts_bar_size_to_size_hint_new_config(qtbot: QtBot):
    QApplication.instance().main_window.ui.navbar = QToolBar()
    widget = PLSToolbarWidget()
    qtbot.add_widget(widget)
    widget.config = PLSToolbarConfig(show_bar=True, show_user=True, show_lsa=True)
    timing_bars: List[TimingBar] = [w for w in widget.children() if isinstance(w, TimingBar)]
    assert len(timing_bars) == 1
    bar = timing_bars[0]
    widget.show()
    time = datetime.now()
    largest_width = widget.sizeHint().width()
    bar.model._last_info = TimingUpdate(timestamp=time, offset=0, user='SUPER_DUPER_LONG', lsa_name='SUPER_DUPER_LONG')
    bar.model.timingUpdateReceived.emit(True)
    qtbot.wait(1)
    assert widget.sizeHint().width() > largest_width
    largest_width = widget.sizeHint().width()
    widget.config = PLSToolbarConfig(show_bar=True, show_user=False, show_lsa=False)
    qtbot.wait(1)
    assert widget.sizeHint().width() < largest_width


@pytest.mark.parametrize('config,expect_bar_exists,expect_showing_domain,expect_showing_time,expect_showing_start,'
                         'expect_showing_user,expect_showing_lsa,expect_render_supercycle,expect_us,expect_tz,'
                         'expect_heartbeat,expect_utc', [
                             (None, False, True, True, True, True, True, True, False, False, True, False),
                             ({}, False, True, True, True, True, True, True, False, False, True, False),
                             ({'show_bar': '1'}, True, True, True, True, True, True, True, False, False, True, False),
                             ({'show_bar': '1', 'utc': '0'}, True, True, True, True, True, True, True, False, False, True, False),
                             ({'show_bar': '1', 'utc': '1'}, True, True, True, True, True, True, True, False, False, True, True),
                             ({'show_bar': '1', 'show_domain': '0'}, True, False, True, True, True, True, True, False, False, True, False),
                             ({'show_bar': '1', 'show_time': '0'}, True, True, False, True, True, True, True, False, False, True, False),
                             ({'show_bar': '1', 'show_domain': '0', 'show_time': '0'}, True, False, False, True, True, True, True, False, False, True, False),
                             ({'show_bar': '1', 'show_lsa': '0'}, True, True, True, True, True, False, True, False, False, True, False),
                             ({'show_bar': '1', 'show_user': '0'}, True, True, True, True, False, True, True, False, False, True, False),
                             ({'show_bar': '1', 'supercycle': '0'}, True, True, True, True, True, True, False, False, False, True, False),
                             ({'show_bar': '1', 'microseconds': '1'}, True, True, True, True, True, True, True, True, False, True, False),
                             ({'show_bar': '1', 'show_tz': '1'}, True, True, True, True, True, True, True, False, True, True, False),
                             ({'show_bar': '1', 'heartbeat': '0'}, True, True, True, True, True, True, True, False, False, False, False),
                             ({'show_bar': '1', 'show_tz': '1', 'utc': '1'}, True, True, True, True, True, True, True, False, True, True, True),
                         ])
def test_pls_plugin_create_widget(config, expect_bar_exists, expect_heartbeat,
                                  expect_render_supercycle, expect_showing_domain, expect_showing_lsa,
                                  expect_showing_start, expect_showing_time, expect_showing_user,
                                  expect_tz, expect_us, expect_utc, qtbot: QtBot):
    QApplication.instance().main_window.ui.navbar = QToolBar()
    widget = PLSToolbarWidget(config=config)
    qtbot.add_widget(widget)
    assert widget.config.show_bar == expect_bar_exists
    assert widget.config.utc == expect_utc
    assert widget.config.heartbeat == expect_heartbeat
    assert widget.config.microseconds == expect_us
    assert widget.config.supercycle == expect_render_supercycle
    assert widget.config.show_domain == expect_showing_domain
    assert widget.config.show_user == expect_showing_user
    assert widget.config.show_lsa == expect_showing_lsa
    assert widget.config.show_tz == expect_tz
    assert widget.config.show_start == expect_showing_start
    assert widget.config.show_time == expect_showing_time
