import pytest
import os
from typing import List, Optional, Dict
from unittest import mock
from comrad.app.plugins.toolbar.pls_plugin import PLSSelectorDialog


def format_test_data(ids: List[str]) -> List[mock.MagicMock]:
    res: Dict[str, mock.MagicMock] = {}

    def mock_with_name(name: str, list_arg: Optional[str] = None) -> mock.MagicMock:
        m = mock.MagicMock()
        m.name = name
        if list_arg is not None:
            setattr(m, list_arg, {})
        return m

    for identifier in ids:
        domain, group, line = tuple(identifier.split('.'))
        sample_domain = res.setdefault(domain, mock_with_name(domain, list_arg='selector_groups'))
        sample_group = sample_domain.selector_groups.setdefault(group, mock_with_name(group, list_arg='selector_values'))
        sample_group.selector_values[line] = mock_with_name(line)
    for domain_mock in res.values():
        domain_mock.selector_groups = list(domain_mock.selector_groups.values())
        for group_mock in domain_mock.selector_groups:
            group_mock.selector_values = list(group_mock.selector_values.values())

    return list(res.values())


@pytest.fixture(autouse=True)
def clean_env():
    try:
        del os.environ['PLS_TELEGRAM']
    except KeyError:
        pass


@mock.patch('comrad.app.plugins.toolbar.pls_plugin.CCDA')
def test_fetches_ccda_on_show(CCDA, qtbot):
    CCDA.return_value.SelectorDomain.search.return_value = []
    dialog = PLSSelectorDialog()
    qtbot.addWidget(dialog)
    CCDA.return_value.SelectorDomain.search.assert_not_called()
    dialog.show()
    CCDA.return_value.SelectorDomain.search.assert_called_once()


@mock.patch('comrad.app.plugins.toolbar.pls_plugin.CCDA')
def test_does_not_fetch_ccda_on_show_repeatedly(CCDA, qtbot):
    CCDA.return_value.SelectorDomain.search.return_value = format_test_data(['TEST.USER.ALL'])
    dialog = PLSSelectorDialog()
    qtbot.addWidget(dialog)
    CCDA.return_value.SelectorDomain.search.assert_not_called()
    dialog.show()
    CCDA.return_value.SelectorDomain.search.assert_called_once()
    dialog.hide()
    CCDA.return_value.SelectorDomain.search.reset_mock()
    dialog.show()
    CCDA.return_value.SelectorDomain.search.assert_not_called()


@mock.patch('comrad.app.plugins.toolbar.pls_plugin.CCDA')
def test_populates_comboboxes_with_ccda_data(CCDA, qtbot):
    CCDA.return_value.SelectorDomain.search.return_value = format_test_data(['TEST.USER.ALL',
                                                                             'TEST.USER.MD1',
                                                                             'TEST.USER.MD2',
                                                                             'TEST.CUSTOM.ALL',
                                                                             'TEST2.USER.ALL'])
    dialog = PLSSelectorDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    assert dialog.machine_combo.model().stringList() == ['TEST', 'TEST2']
    assert dialog.group_combo.model().stringList() == ['USER', 'CUSTOM']
    assert dialog.line_combo.model().stringList() == ['ALL', 'MD1', 'MD2']
    dialog.group_combo.setCurrentIndex(1)
    assert dialog.machine_combo.model().stringList() == ['TEST', 'TEST2']
    assert dialog.group_combo.model().stringList() == ['USER', 'CUSTOM']
    assert dialog.line_combo.model().stringList() == ['ALL']
    dialog.group_combo.setCurrentIndex(0)
    assert dialog.machine_combo.model().stringList() == ['TEST', 'TEST2']
    assert dialog.group_combo.model().stringList() == ['USER', 'CUSTOM']
    assert dialog.line_combo.model().stringList() == ['ALL', 'MD1', 'MD2']
    dialog.machine_combo.setCurrentIndex(1)
    assert dialog.machine_combo.model().stringList() == ['TEST', 'TEST2']
    assert dialog.group_combo.model().stringList() == ['USER']
    assert dialog.line_combo.model().stringList() == ['ALL']
    dialog.machine_combo.setCurrentIndex(0)
    assert dialog.machine_combo.model().stringList() == ['TEST', 'TEST2']
    assert dialog.group_combo.model().stringList() == ['USER', 'CUSTOM']
    assert dialog.line_combo.model().stringList() == ['ALL', 'MD1', 'MD2']
    dialog.line_combo.setCurrentIndex(1)
    assert dialog.machine_combo.model().stringList() == ['TEST', 'TEST2']
    assert dialog.group_combo.model().stringList() == ['USER', 'CUSTOM']
    assert dialog.line_combo.model().stringList() == ['ALL', 'MD1', 'MD2']
    dialog.line_combo.setCurrentIndex(2)
    assert dialog.machine_combo.model().stringList() == ['TEST', 'TEST2']
    assert dialog.group_combo.model().stringList() == ['USER', 'CUSTOM']
    assert dialog.line_combo.model().stringList() == ['ALL', 'MD1', 'MD2']
    dialog.line_combo.setCurrentIndex(0)
    assert dialog.machine_combo.model().stringList() == ['TEST', 'TEST2']
    assert dialog.group_combo.model().stringList() == ['USER', 'CUSTOM']
    assert dialog.line_combo.model().stringList() == ['ALL', 'MD1', 'MD2']


@mock.patch('comrad.app.plugins.toolbar.pls_plugin.CCDA')
def test_checkbox_toggles_all_comboboxes(CCDA, qtbot):
    CCDA.return_value.SelectorDomain.search.return_value = format_test_data(['TEST.USER.ALL'])
    dialog = PLSSelectorDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    assert dialog.no_selector.isChecked()
    assert not dialog.machine_combo.isEnabled()
    assert not dialog.group_combo.isEnabled()
    assert not dialog.line_combo.isEnabled()
    assert dialog.machine_combo.model().stringList() == ['TEST']
    assert dialog.group_combo.model().stringList() == ['USER']
    assert dialog.line_combo.model().stringList() == ['ALL']
    dialog.no_selector.setChecked(False)
    assert dialog.machine_combo.isEnabled()
    assert dialog.group_combo.isEnabled()
    assert dialog.line_combo.isEnabled()
    assert dialog.machine_combo.model().stringList() == ['TEST']
    assert dialog.group_combo.model().stringList() == ['USER']
    assert dialog.line_combo.model().stringList() == ['ALL']
    dialog.no_selector.setChecked(True)
    assert not dialog.machine_combo.isEnabled()
    assert not dialog.group_combo.isEnabled()
    assert not dialog.line_combo.isEnabled()
    assert dialog.machine_combo.model().stringList() == ['TEST']
    assert dialog.group_combo.model().stringList() == ['USER']
    assert dialog.line_combo.model().stringList() == ['ALL']


@pytest.mark.parametrize('window_selector,expected_machine,expected_group,expected_line,expected_enabled', [
    (None, 'TEST', 'USER', 'ALL', False),
    ('', 'TEST', 'USER', 'ALL', False),
    ('TEST.USER.ALL', 'TEST', 'USER', 'ALL', True),
    ('TEST.USER2.ALL', 'TEST', 'USER2', 'ALL', True),
    ('TEST.USER2.MD1', 'TEST', 'USER2', 'MD1', True),
    ('TEST2.USER.ALL', 'TEST2', 'USER', 'ALL', True),
    ('TEST2.USER3.ALL', 'TEST2', 'USER3', 'ALL', True),
])
@mock.patch('comrad.CApplication.instance')
@mock.patch('comrad.app.plugins.toolbar.pls_plugin.CCDA')
def test_preselects_comboboxes_based_on_window_context(CCDA, app, qtbot, window_selector, expected_enabled, expected_group, expected_line, expected_machine):
    CCDA.return_value.SelectorDomain.search.return_value = format_test_data(['TEST.USER.ALL',
                                                                             'TEST.USER2.ALL',
                                                                             'TEST.USER2.MD1',
                                                                             'TEST2.USER.ALL',
                                                                             'TEST2.USER3.ALL'])
    app.return_value.main_window.window_context.selector = window_selector
    dialog = PLSSelectorDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    assert expected_enabled != dialog.no_selector.isChecked()
    assert expected_enabled == dialog.machine_combo.isEnabled()
    assert expected_enabled == dialog.group_combo.isEnabled()
    assert expected_enabled == dialog.line_combo.isEnabled()
    assert dialog.machine_combo.currentText() == expected_machine
    assert dialog.group_combo.currentText() == expected_group
    assert dialog.line_combo.currentText() == expected_line


@pytest.mark.parametrize('machine,group,line,use_selector,expected_selector', [
    ('TEST', 'USER', 'ALL', False, None),
    ('TEST', 'USER2', 'ALL', False, None),
    ('TEST', 'USER', 'ALL', True, 'TEST.USER.ALL'),
    ('TEST', 'USER2', 'ALL', True, 'TEST.USER2.ALL'),
    ('TEST', 'USER2', 'MD1', True, 'TEST.USER2.MD1'),
    ('TEST2', 'USER', 'ALL', True, 'TEST2.USER.ALL'),
    ('TEST2', 'USER3', 'ALL', True, 'TEST2.USER3.ALL'),
])
@mock.patch('comrad.CApplication.instance')
@mock.patch('comrad.app.plugins.toolbar.pls_plugin.CCDA')
def test_plugin_saves_context(CCDA, app, qtbot, expected_selector, machine, group, line, use_selector):
    CCDA.return_value.SelectorDomain.search.return_value = format_test_data(['TEST.USER.ALL',
                                                                             'TEST.USER2.ALL',
                                                                             'TEST.USER2.MD1',
                                                                             'TEST2.USER.ALL',
                                                                             'TEST2.USER3.ALL'])
    app.return_value.main_window.window_context.selector = None
    dialog = PLSSelectorDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.machine_combo.setCurrentText(machine)
    dialog.group_combo.setCurrentText(group)
    dialog.line_combo.setCurrentText(line)
    dialog.no_selector.setChecked(not use_selector)
    dialog.accept()
    assert app.return_value.main_window.window_context.selector == expected_selector


@pytest.mark.parametrize('tgm_var,window_selector,expected_machine,expected_group,expected_line,expected_enabled', [
    (None, None, 'TEST', 'USER', 'ALL', False),
    (None, '', 'TEST', 'USER', 'ALL', False),
    (None, 'TEST.USER2.ALL', 'TEST', 'USER2', 'ALL', True),
    ('LHC', None, 'LHC', 'USER', 'ALL', False),
    ('LHC', '', 'LHC', 'USER', 'ALL', False),
    ('LHC', 'TEST.USER2.ALL', 'TEST', 'USER2', 'ALL', True),
    ('SPS', None, 'SPS', 'PARTY', 'SPS', False),
    ('SPS', '', 'SPS', 'PARTY', 'SPS', False),
    ('SPS', 'TEST.USER2.ALL', 'TEST', 'USER2', 'ALL', True),
])
@mock.patch('comrad.CApplication.instance')
@mock.patch('comrad.app.plugins.toolbar.pls_plugin.CCDA')
def test_preselects_comboboxes_based_on_tgm_environment(CCDA, app, qtbot, tgm_var, window_selector, expected_enabled, expected_group, expected_line, expected_machine):
    CCDA.return_value.SelectorDomain.search.return_value = format_test_data(['TEST.USER.ALL',
                                                                             'TEST.USER2.ALL',
                                                                             'LHC.SMTH.SMTH',
                                                                             'LHC.USER.ALL',
                                                                             'SPS.PARTY.SPS'])
    app.return_value.main_window.window_context.selector = window_selector
    if tgm_var:
        os.environ['PLS_TELEGRAM'] = tgm_var
    dialog = PLSSelectorDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    assert expected_enabled != dialog.no_selector.isChecked()
    assert expected_enabled == dialog.machine_combo.isEnabled()
    assert expected_enabled == dialog.group_combo.isEnabled()
    assert expected_enabled == dialog.line_combo.isEnabled()
    assert dialog.machine_combo.currentText() == expected_machine
    assert dialog.group_combo.currentText() == expected_group
    assert dialog.line_combo.currentText() == expected_line
