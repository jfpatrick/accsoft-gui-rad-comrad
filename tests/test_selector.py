import pytest
from pytestqt.qtbot import QtBot
from typing import Dict, List, Optional
from unittest import mock
from comrad._selector import PLSSelectorDialog, PLSSelectorConfig


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


@mock.patch('comrad._selector._selector.CCDA')
def test_pls_dialog_fetches_ccda_on_show(CCDA, qtbot):
    CCDA.return_value.SelectorDomain.search.return_value = []
    dialog = PLSSelectorDialog(config=PLSSelectorConfig())
    qtbot.add_widget(dialog)
    CCDA.return_value.SelectorDomain.search.assert_not_called()
    dialog.show()
    CCDA.return_value.SelectorDomain.search.assert_called_once()


@mock.patch('comrad._selector._selector.CCDA')
def test_pls_dialog_does_not_fetch_ccda_on_show_repeatedly(CCDA, qtbot):
    CCDA.return_value.SelectorDomain.search.return_value = format_test_data(['TEST.USER.ALL'])
    dialog = PLSSelectorDialog(config=PLSSelectorConfig())
    qtbot.add_widget(dialog)
    CCDA.return_value.SelectorDomain.search.assert_not_called()
    dialog.show()
    CCDA.return_value.SelectorDomain.search.assert_called_once()
    dialog.hide()
    CCDA.return_value.SelectorDomain.search.reset_mock()
    dialog.show()
    CCDA.return_value.SelectorDomain.search.assert_not_called()


@pytest.mark.parametrize('config', [
    PLSSelectorConfig(),
    PLSSelectorConfig.no_selector(),
    PLSSelectorConfig(machine='TEST', group='USER', line='MD1'),
])
@mock.patch('comrad._selector._selector.CCDA')
def test_pls_dialog_populates_comboboxes_with_ccda_data(CCDA, qtbot, config):
    CCDA.return_value.SelectorDomain.search.return_value = format_test_data(['TEST.USER.ALL',
                                                                             'TEST.USER.MD1',
                                                                             'TEST.CUSTOM2.ALL',
                                                                             'TEST.USER.MD2',
                                                                             'TEST.CUSTOM.ALL',
                                                                             'TEST2.USER.ALL'])
    dialog = PLSSelectorDialog(config=config)
    qtbot.add_widget(dialog)
    dialog.show()
    assert dialog.machine_combo.model().stringList() == ['TEST', 'TEST2']
    assert dialog.group_combo.model().stringList() == ['USER', 'CUSTOM', 'CUSTOM2']
    assert dialog.line_combo.model().stringList() == ['ALL', 'MD1', 'MD2']
    dialog.group_combo.setCurrentIndex(1)
    assert dialog.machine_combo.model().stringList() == ['TEST', 'TEST2']
    assert dialog.group_combo.model().stringList() == ['USER', 'CUSTOM', 'CUSTOM2']
    assert dialog.line_combo.model().stringList() == ['ALL']
    dialog.group_combo.setCurrentIndex(0)
    assert dialog.machine_combo.model().stringList() == ['TEST', 'TEST2']
    assert dialog.group_combo.model().stringList() == ['USER', 'CUSTOM', 'CUSTOM2']
    assert dialog.line_combo.model().stringList() == ['ALL', 'MD1', 'MD2']
    dialog.machine_combo.setCurrentIndex(1)
    assert dialog.machine_combo.model().stringList() == ['TEST', 'TEST2']
    assert dialog.group_combo.model().stringList() == ['USER']
    assert dialog.line_combo.model().stringList() == ['ALL']
    dialog.machine_combo.setCurrentIndex(0)
    assert dialog.machine_combo.model().stringList() == ['TEST', 'TEST2']
    assert dialog.group_combo.model().stringList() == ['USER', 'CUSTOM', 'CUSTOM2']
    assert dialog.line_combo.model().stringList() == ['ALL', 'MD1', 'MD2']
    dialog.line_combo.setCurrentIndex(1)
    assert dialog.machine_combo.model().stringList() == ['TEST', 'TEST2']
    assert dialog.group_combo.model().stringList() == ['USER', 'CUSTOM', 'CUSTOM2']
    assert dialog.line_combo.model().stringList() == ['ALL', 'MD1', 'MD2']
    dialog.line_combo.setCurrentIndex(2)
    assert dialog.machine_combo.model().stringList() == ['TEST', 'TEST2']
    assert dialog.group_combo.model().stringList() == ['USER', 'CUSTOM', 'CUSTOM2']
    assert dialog.line_combo.model().stringList() == ['ALL', 'MD1', 'MD2']
    dialog.line_combo.setCurrentIndex(0)
    assert dialog.machine_combo.model().stringList() == ['TEST', 'TEST2']
    assert dialog.group_combo.model().stringList() == ['USER', 'CUSTOM', 'CUSTOM2']
    assert dialog.line_combo.model().stringList() == ['ALL', 'MD1', 'MD2']


@mock.patch('comrad._selector._selector.CCDA')
def test_pls_dialog_checkbox_toggles_all_comboboxes(CCDA, qtbot):
    CCDA.return_value.SelectorDomain.search.return_value = format_test_data(['TEST.USER.ALL'])
    dialog = PLSSelectorDialog(config=PLSSelectorConfig.no_selector())
    qtbot.add_widget(dialog)
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


@pytest.mark.parametrize('config,expected_machine,expected_group,expected_line,expected_enabled', [
    (PLSSelectorConfig.no_selector(), 'TEST', 'USER', 'ALL', False),
    (PLSSelectorConfig(), 'TEST', 'USER', 'ALL', True),
    (PLSSelectorConfig(machine='TEST', group='USER', line='ALL'), 'TEST', 'USER', 'ALL', True),
    (PLSSelectorConfig(machine='TEST', group='USER2', line='ALL'), 'TEST', 'USER2', 'ALL', True),
    (PLSSelectorConfig(machine='TEST', group='USER2', line='MD1'), 'TEST', 'USER2', 'MD1', True),
    (PLSSelectorConfig(machine='TEST2', group='USER', line='ALL'), 'TEST2', 'USER', 'ALL', True),
    (PLSSelectorConfig(machine='TEST2', group='USER3', line='ALL'), 'TEST2', 'USER3', 'ALL', True),
])
@mock.patch('comrad._selector._selector.CCDA')
def test_pls_dialog_preselects_comboboxes_based_on_config(CCDA, qtbot, config, expected_enabled, expected_group, expected_line, expected_machine):
    CCDA.return_value.SelectorDomain.search.return_value = format_test_data(['TEST.USER.ALL',
                                                                             'TEST.USER2.ALL',
                                                                             'TEST.USER2.MD1',
                                                                             'TEST2.USER.ALL',
                                                                             'TEST2.USER3.ALL'])
    dialog = PLSSelectorDialog(config=config)
    qtbot.add_widget(dialog)
    dialog.show()
    assert expected_enabled != dialog.no_selector.isChecked()
    assert expected_enabled == dialog.machine_combo.isEnabled()
    assert expected_enabled == dialog.group_combo.isEnabled()
    assert expected_enabled == dialog.line_combo.isEnabled()
    assert dialog.machine_combo.currentText() == expected_machine
    assert dialog.group_combo.currentText() == expected_group
    assert dialog.line_combo.currentText() == expected_line


@pytest.mark.parametrize('machine,group,line,use_selector,expected_selector', [
    ('TEST', 'USER', 'ALL', False, ''),
    ('TEST', 'USER2', 'ALL', False, ''),
    ('TEST', 'USER', 'ALL', True, 'TEST.USER.ALL'),
    ('TEST', 'USER2', 'ALL', True, 'TEST.USER2.ALL'),
    ('TEST', 'USER2', 'MD1', True, 'TEST.USER2.MD1'),
    ('TEST2', 'USER', 'ALL', True, 'TEST2.USER.ALL'),
    ('TEST2', 'USER3', 'ALL', True, 'TEST2.USER3.ALL'),
])
@mock.patch('comrad._selector._selector.CCDA')
def test_pls_dialog_notifies_selector(CCDA, qtbot: QtBot, expected_selector, machine, group, line, use_selector):
    CCDA.return_value.SelectorDomain.search.return_value = format_test_data(['TEST.USER.ALL',
                                                                             'TEST.USER2.ALL',
                                                                             'TEST.USER2.MD1',
                                                                             'TEST2.USER.ALL',
                                                                             'TEST2.USER3.ALL'])
    dialog = PLSSelectorDialog(config=PLSSelectorConfig.no_selector())
    qtbot.add_widget(dialog)
    dialog.show()
    dialog.machine_combo.setCurrentText(machine)
    dialog.group_combo.setCurrentText(group)
    dialog.line_combo.setCurrentText(line)
    dialog.no_selector.setChecked(not use_selector)
    with qtbot.wait_signal(dialog.selector_selected) as blocker:
        dialog.accept()
    assert blocker.args == [expected_selector]
