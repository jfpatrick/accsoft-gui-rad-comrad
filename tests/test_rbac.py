import pytest
import os
import pyrbac
from pathlib import Path
from typing import List
from freezegun import freeze_time
from datetime import datetime
from pytestqt.qtbot import QtBot
from unittest import mock
from qtpy.QtWidgets import QFormLayout, QLabel, QDialogButtonBox
from qtpy.QtGui import QPalette, QBrush, QColor, QKeyEvent
from qtpy.QtCore import Qt, QVariant, QEvent
from comrad.rbac import CRBACRole, CRBACState, CRBACLoginStatus, CRBACToken
from comrad.rbac.token_dialog import RbaTokenDialog
from comrad.rbac.role_picker import RbaRolePicker


def teardown_function():
    # Clean-up all pyrbac environment variables
    for var in ['RBAC_PKEY', 'RBAC_ENV', 'RBAC_APPLICATION_NAME']:
        try:
            del os.environ[var]
        except KeyError:
            pass


@pytest.fixture
def make_token():
    def _builder(valid: bool,
                 loc_auth_reqd: bool,
                 roles: List[CRBACRole],
                 auth_timestamp: datetime,
                 expiration_timestamp: datetime):
        token = mock.MagicMock()
        token.username = 'TEST_USERNAME'
        token.user_full_name = 'TEST_FULL_NAME'
        token.user_email = 'TEST_EMAIL'
        token.account_type = 'TEST_ACCOUNT'
        token.valid = valid
        token.auth_timestamp = auth_timestamp
        token.expiration_timestamp = expiration_timestamp
        token.roles = roles
        token.app_name = 'TEST_APP'
        token.location.name = 'TEST_LOC'
        token.location.address = '10.10.255.255'
        token.location.auth_required = loc_auth_reqd
        token.serial_id = '0xd0gf00d'
        return token
    return _builder


@freeze_time('2020-01-01 12:55:22')
@pytest.mark.parametrize('valid,valid_str', [
    (True, 'true'),
    (False, 'false'),
])
@pytest.mark.parametrize('loc_auth,loc_auth_str', [
    (True, 'true'),
    (False, 'false'),
])
@pytest.mark.parametrize('roles,roles_str', [
    ([
        CRBACRole(name='Role1'),
        CRBACRole(name='Role2', lifetime=10),
        CRBACRole(name='Role3', active=True),
        CRBACRole(name='Role4', lifetime=10, active=True),
        CRBACRole(name='MCS-Role1'),
        CRBACRole(name='MCS-Role2', lifetime=20),
        CRBACRole(name='MCS-Role3', active=True),
        CRBACRole(name='MCS-Role4', lifetime=20, active=True),
    ], 'MCS-Role3 [critical=true; lifetime=-1]\n'
       'MCS-Role4 [critical=true; lifetime=20]\n'
       'Role3 [critical=false; lifetime=-1]\n'
       'Role4 [critical=false; lifetime=10]'),
    ([
        CRBACRole(name='Role1'),
        CRBACRole(name='Role2', lifetime=10),
        CRBACRole(name='MCS-Role1'),
        CRBACRole(name='MCS-Role2', lifetime=20),
    ], ''),
    ([], ''),
])
def test_token_dialog_displays_data(qtbot: QtBot, make_token, valid, valid_str, loc_auth, loc_auth_str, roles, roles_str):
    token = make_token(valid=valid,
                       loc_auth_reqd=loc_auth,
                       roles=roles,
                       auth_timestamp=datetime(2020, 1, 1, 12, 53, 23),
                       expiration_timestamp=datetime(2020, 1, 1, 13, 0, 0))
    dialog = RbaTokenDialog(token=token)
    qtbot.add_widget(dialog)
    assert dialog.form.itemAt(0, QFormLayout.LabelRole).widget().text() == 'User Name'
    assert dialog.form.itemAt(0, QFormLayout.FieldRole).widget().text() == 'TEST_USERNAME [TEST_FULL_NAME, TEST_EMAIL]'
    assert dialog.form.itemAt(1, QFormLayout.LabelRole).widget().text() == 'Account Type'
    assert dialog.form.itemAt(1, QFormLayout.FieldRole).widget().text() == 'TEST_ACCOUNT'
    assert dialog.form.itemAt(2, QFormLayout.LabelRole).widget().text() == 'Is Valid ?'
    assert dialog.form.itemAt(2, QFormLayout.FieldRole).widget().text() == valid_str
    assert dialog.form.itemAt(3, QFormLayout.LabelRole).widget().text() == 'Start Time'
    assert dialog.form.itemAt(3, QFormLayout.FieldRole).widget().text() == '2020-01-01 12:53:23 (About 1 min. 59 sec. ago)'
    assert dialog.form.itemAt(4, QFormLayout.LabelRole).widget().text() == 'Expiration Time'
    assert dialog.form.itemAt(4, QFormLayout.FieldRole).widget().text() == '2020-01-01 13:00:00 (About 4 min. 38 sec. from now)'
    assert dialog.form.itemAt(5, QFormLayout.LabelRole).widget().text() == 'Roles'
    assert dialog.form.itemAt(5, QFormLayout.FieldRole).widget().text() == roles_str
    assert dialog.form.itemAt(6, QFormLayout.LabelRole).widget().text() == 'Application'
    assert dialog.form.itemAt(6, QFormLayout.FieldRole).widget().text() == 'TEST_APP'
    assert dialog.form.itemAt(7, QFormLayout.LabelRole).widget().text() == 'Location'
    assert dialog.form.itemAt(7, QFormLayout.FieldRole).widget().text() == f'TEST_LOC [address=10.10.255.255; auth-reqd={loc_auth_str}]'
    assert dialog.form.itemAt(8, QFormLayout.LabelRole).widget().text() == 'Serial ID'
    assert dialog.form.itemAt(8, QFormLayout.FieldRole).widget().text() == '0xd0gf00d'


@pytest.mark.parametrize(f'valid,expected_color', [
    (True, '#66ff66'),
    (False, '#ff5050'),
])
def test_token_dialog_colors_validity(qtbot: QtBot, make_token, valid, expected_color):
    token = make_token(valid=valid,
                       loc_auth_reqd=False,
                       roles=[],
                       auth_timestamp=datetime.now(),
                       expiration_timestamp=datetime.now())
    dialog = RbaTokenDialog(token=token)
    qtbot.add_widget(dialog)
    assert dialog.form.itemAt(2, QFormLayout.FieldRole).widget().palette().color(QPalette.Background).name() == expected_color


@freeze_time('2020-01-01 12:55:22')
@pytest.mark.parametrize('expiration_time,expected_label,expected_color', [
    (datetime(2020, 1, 1, 13, 0, 0), '2020-01-01 13:00:00 (About 4 min. 38 sec. from now)', None),
    (datetime(2020, 1, 2, 13, 0, 0), '2020-01-02 13:00:00 (About 1 day 4 min. 38 sec. from now)', None),
    (datetime(2020, 1, 2, 12, 55, 22), '2020-01-02 12:55:22 (About 1 day from now)', None),
    (datetime(2020, 7, 1, 13, 0, 0), '2020-07-01 13:00:00 (About 182 days 4 min. 38 sec. from now)', None),
    (datetime(2021, 1, 1, 13, 0, 0), '2021-01-01 13:00:00 (About 366 days 4 min. 38 sec. from now)', None),
    (datetime(2020, 1, 1, 12, 53, 25), '2020-01-01 12:53:25 (About 1 min. 57 sec. ago)', '#ff5050'),
    (datetime(2019, 12, 31, 12, 53, 25), '2019-12-31 12:53:25 (About 1 day 1 min. 57 sec. ago)', '#ff5050'),
    (datetime(2019, 12, 31, 12, 55, 22), '2019-12-31 12:55:22 (About 1 day ago)', '#ff5050'),
    (datetime(2019, 6, 30, 12, 53, 25), '2019-06-30 12:53:25 (About 185 days 1 min. 57 sec. ago)', '#ff5050'),
    (datetime(2019, 1, 1, 12, 53, 25), '2019-01-01 12:53:25 (About 365 days 1 min. 57 sec. ago)', '#ff5050'),
    (datetime(2020, 1, 1, 12, 55, 22), '2020-01-01 12:55:22 (About now)', None),
])
def test_token_dialog_expiration(qtbot: QtBot, make_token, expiration_time, expected_color, expected_label):
    token = make_token(valid=True,
                       loc_auth_reqd=False,
                       roles=[],
                       auth_timestamp=datetime(2020, 1, 1, 12, 53, 23),
                       expiration_timestamp=expiration_time)
    dialog = RbaTokenDialog(token=token)
    qtbot.add_widget(dialog)
    label: QLabel = dialog.form.itemAt(4, QFormLayout.FieldRole).widget()
    assert label.text() == expected_label
    if expected_color is None:
        assert label.styleSheet() == ''
    else:
        assert label.styleSheet() == f'color: {expected_color}'


@pytest.mark.parametrize('roles,mcs_only,visible_roles', [
    ([
        CRBACRole(name='Role1'),
        CRBACRole(name='Role2', lifetime=10),
        CRBACRole(name='Role3', active=True),
        CRBACRole(name='Role4', lifetime=10, active=True),
        CRBACRole(name='MCS-Role1'),
        CRBACRole(name='MCS-Role2', lifetime=20),
        CRBACRole(name='MCS-Role3', active=True),
        CRBACRole(name='MCS-Role4', lifetime=20),
    ], True, [
        # Role name, is checked, color (or None for default)
        ('MCS-Role1', False, Qt.red),
        ('MCS-Role2', False, Qt.red),
        ('MCS-Role3', True, Qt.red),
        ('MCS-Role4', False, Qt.red),
    ]),
    ([
        CRBACRole(name='Role1'),
        CRBACRole(name='Role2', lifetime=10),
        CRBACRole(name='Role3', active=True),
        CRBACRole(name='Role4', lifetime=10, active=True),
        CRBACRole(name='MCS-Role1'),
        CRBACRole(name='MCS-Role2', lifetime=20),
        CRBACRole(name='MCS-Role3', active=True),
        CRBACRole(name='MCS-Role4', lifetime=20),
    ], False, [
        # Role name, is checked, color (or None for default)
        ('MCS-Role1', False, Qt.red),
        ('MCS-Role2', False, Qt.red),
        ('MCS-Role3', True, Qt.red),
        ('MCS-Role4', False, Qt.red),
        ('Role1', False, None),
        ('Role2', False, None),
        ('Role3', True, None),
        ('Role4', True, None),
    ]),
    ([
        CRBACRole(name='Role3', active=True),
        CRBACRole(name='Role4', lifetime=10, active=True),
    ], True, []),
    ([
        CRBACRole(name='Role3', active=True),
        CRBACRole(name='Role4', lifetime=10, active=True),
    ], False, [
        # Role name, is checked, color (or None for default)
        ('Role3', True, None),
        ('Role4', True, None),
    ]),
    ([
        CRBACRole(name='Role1'),
        CRBACRole(name='Role2', lifetime=10),
        CRBACRole(name='MCS-Role1'),
        CRBACRole(name='MCS-Role2', lifetime=20),
    ], True, [
        # Role name, is checked, color (or None for default)
        ('MCS-Role1', False, Qt.red),
        ('MCS-Role2', False, Qt.red),
    ]),
    ([
        CRBACRole(name='Role1'),
        CRBACRole(name='Role2', lifetime=10),
        CRBACRole(name='MCS-Role1'),
        CRBACRole(name='MCS-Role2', lifetime=20),
    ], False, [
        # Role name, is checked, color (or None for default)
        ('MCS-Role1', False, Qt.red),
        ('MCS-Role2', False, Qt.red),
        ('Role1', False, None),
        ('Role2', False, None),
    ]),
    ([], True, []),
    ([], False, []),
])
def test_role_picker_displays_sorted_roles(qtbot: QtBot, roles, mcs_only, visible_roles):
    dialog = RbaRolePicker(roles=roles)
    qtbot.add_widget(dialog)
    dialog.mcs_checkbox.setChecked(mcs_only)
    assert dialog.btn_clear_all.isHidden() == mcs_only
    assert dialog.btn_select_all.isHidden() == mcs_only
    model = dialog.role_view.model()
    assert model.rowCount() == len(visible_roles)
    for i, visible_role in enumerate(visible_roles):
        idx = model.index(i, 0)
        name, checked, color = visible_role
        assert model.data(idx, Qt.DisplayRole) == name
        assert model.data(idx, Qt.CheckStateRole) == (Qt.Checked if checked else Qt.Unchecked)
        assert model.data(idx, Qt.ForegroundRole) == (QVariant() if color is None else QBrush(QColor(color)))


@pytest.mark.parametrize('init_roles,clicked_row,in_mcs_mode,final_roles', [
    ([
        CRBACRole(name='A1'),
        CRBACRole(name='MCS-A3'),
        CRBACRole(name='X2'),
    ], 0, False, [
        ('A1', True),
        ('MCS-A3', False),
        ('X2', False),
    ]),
    ([
        CRBACRole(name='A1'),
        CRBACRole(name='MCS-A3'),
        CRBACRole(name='MCS-A4'),
        CRBACRole(name='X2'),
    ], 1, False, [
        ('A1', False),
        ('MCS-A3', True),
        ('MCS-A4', False),
        ('X2', False),
    ]),
    ([
        CRBACRole(name='A1'),
        CRBACRole(name='MCS-A3'),
        CRBACRole(name='MCS-A4'),
        CRBACRole(name='X2'),
    ], 0, True, [
        ('A1', False),
        ('MCS-A3', True),
        ('MCS-A4', False),
        ('X2', False),
    ]),
    ([
        CRBACRole(name='A1', active=True),
        CRBACRole(name='MCS-A3'),
        CRBACRole(name='MCS-A4'),
        CRBACRole(name='X2', active=True),
    ], 1, False, [
        ('A1', True),
        ('MCS-A3', True),
        ('MCS-A4', False),
        ('X2', True),
    ]),
    ([
        CRBACRole(name='A1', active=True),
        CRBACRole(name='MCS-A3'),
        CRBACRole(name='MCS-A4'),
        CRBACRole(name='X2', active=True),
    ], 0, True, [
        ('A1', True),
        ('MCS-A3', True),
        ('MCS-A4', False),
        ('X2', True),
    ]),
    ([
        CRBACRole(name='A1'),
        CRBACRole(name='MCS-A3', active=True),
        CRBACRole(name='MCS-A4'),
        CRBACRole(name='X2'),
    ], 2, False, [
        ('A1', False),
        ('MCS-A3', False),
        ('MCS-A4', True),
        ('X2', False),
    ]),
    ([
        CRBACRole(name='A1'),
        CRBACRole(name='MCS-A3', active=True),
        CRBACRole(name='MCS-A4'),
        CRBACRole(name='X2'),
    ], 1, True, [
        ('A1', False),
        ('MCS-A3', False),
        ('MCS-A4', True),
        ('X2', False),
    ]),
    ([
        CRBACRole(name='A1', active=True),
        CRBACRole(name='MCS-A3', active=True),
        CRBACRole(name='MCS-A4'),
        CRBACRole(name='X2', active=True),
    ], 2, False, [
        ('A1', True),
        ('MCS-A3', False),
        ('MCS-A4', True),
        ('X2', True),
    ]),
    ([
        CRBACRole(name='A1', active=True),
        CRBACRole(name='MCS-A3', active=True),
        CRBACRole(name='MCS-A4'),
        CRBACRole(name='X2', active=True),
    ], 1, True, [
        ('A1', True),
        ('MCS-A3', False),
        ('MCS-A4', True),
        ('X2', True),
    ]),
    ([
        CRBACRole(name='A1', active=True),
        CRBACRole(name='MCS-A3'),
        CRBACRole(name='X2'),
    ], 2, False, [
        ('A1', True),
        ('MCS-A3', False),
        ('X2', True),
    ]),
    ([
        CRBACRole(name='A1', active=True),
        CRBACRole(name='MCS-A3'),
        CRBACRole(name='X2'),
    ], 0, False, [
        ('A1', False),
        ('MCS-A3', False),
        ('X2', False),
    ]),
])
def test_role_picker_allows_only_one_mcs_role(qtbot: QtBot, init_roles, clicked_row, in_mcs_mode, final_roles):
    dialog = RbaRolePicker(roles=init_roles)
    qtbot.add_widget(dialog)
    model = dialog.role_view.model()

    if in_mcs_mode:
        dialog.mcs_checkbox.setChecked(True)

    index = model.index(clicked_row, 0)
    check_state = index.data(Qt.CheckStateRole)
    model.setData(index, Qt.Unchecked if check_state == Qt.Checked else Qt.Checked, Qt.CheckStateRole)

    if in_mcs_mode:
        dialog.mcs_checkbox.setChecked(False)

    assert model.rowCount() == len(final_roles)
    for i, visible_role in enumerate(final_roles):
        idx = model.index(i, 0)
        name, checked = visible_role
        assert model.data(idx, Qt.DisplayRole) == name
        assert model.data(idx, Qt.CheckStateRole) == (Qt.Checked if checked else Qt.Unchecked)


@pytest.mark.parametrize('init_roles,final_roles', [
    ([
        CRBACRole(name='A1'),
        CRBACRole(name='MCS-A3'),
        CRBACRole(name='X2'),
    ], [
        ('A1', True),
        ('MCS-A3', False),
        ('X2', True),
    ]),
    ([
        CRBACRole(name='A1', active=True),
        CRBACRole(name='MCS-A3', active=True),
        CRBACRole(name='X2'),
    ], [
        ('A1', True),
        ('MCS-A3', True),
        ('X2', True),
    ]),
    ([
        CRBACRole(name='A1'),
        CRBACRole(name='MCS-A3'),
        CRBACRole(name='MCS-A4'),
        CRBACRole(name='X2'),
    ], [
        ('A1', True),
        ('MCS-A3', False),
        ('MCS-A4', False),
        ('X2', True),
    ]),
    ([
        CRBACRole(name='A1'),
        CRBACRole(name='MCS-A3'),
        CRBACRole(name='MCS-A4', active=True),
        CRBACRole(name='X2', active=True),
    ], [
        ('A1', True),
        ('MCS-A3', False),
        ('MCS-A4', True),
        ('X2', True),
    ]),
])
def test_role_picker_select_all(qtbot: QtBot, init_roles, final_roles):
    dialog = RbaRolePicker(roles=init_roles)
    qtbot.add_widget(dialog)
    model = dialog.role_view.model()

    dialog.btn_select_all.click()

    assert model.rowCount() == len(final_roles)
    for i, visible_role in enumerate(final_roles):
        idx = model.index(i, 0)
        name, checked = visible_role
        assert model.data(idx, Qt.DisplayRole) == name
        assert model.data(idx, Qt.CheckStateRole) == (Qt.Checked if checked else Qt.Unchecked)


@pytest.mark.parametrize('init_roles,final_roles', [
    ([
        CRBACRole(name='A1'),
        CRBACRole(name='MCS-A3'),
        CRBACRole(name='X2'),
    ], [
        ('A1', False),
        ('MCS-A3', False),
        ('X2', False),
    ]),
    ([
        CRBACRole(name='A1', active=True),
        CRBACRole(name='MCS-A3', active=True),
        CRBACRole(name='X2', active=True),
    ], [
        ('A1', False),
        ('MCS-A3', False),
        ('X2', False),
    ]),
    ([
        CRBACRole(name='A1', active=True),
        CRBACRole(name='MCS-A3', active=True),
        CRBACRole(name='X2'),
    ], [
        ('A1', False),
        ('MCS-A3', False),
        ('X2', False),
    ]),
    ([
        CRBACRole(name='A1'),
        CRBACRole(name='MCS-A3'),
        CRBACRole(name='MCS-A4'),
        CRBACRole(name='X2'),
    ], [
        ('A1', False),
        ('MCS-A3', False),
        ('MCS-A4', False),
        ('X2', False),
    ]),
    ([
        CRBACRole(name='A1'),
        CRBACRole(name='MCS-A3'),
        CRBACRole(name='MCS-A4', active=True),
        CRBACRole(name='X2', active=True),
    ], [
        ('A1', False),
        ('MCS-A3', False),
        ('MCS-A4', False),
        ('X2', False),
    ]),
])
def test_role_picker_clear_all(qtbot: QtBot, init_roles, final_roles):
    dialog = RbaRolePicker(roles=init_roles)
    qtbot.add_widget(dialog)
    model = dialog.role_view.model()

    dialog.btn_clear_all.click()

    assert model.rowCount() == len(final_roles)
    for i, visible_role in enumerate(final_roles):
        idx = model.index(i, 0)
        name, checked = visible_role
        assert model.data(idx, Qt.DisplayRole) == name
        assert model.data(idx, Qt.CheckStateRole) == (Qt.Checked if checked else Qt.Unchecked)


@pytest.mark.parametrize('force,reacts_to_escape,std_buttons', [
    (True, False, [QDialogButtonBox.Apply]),
    (False, True, [QDialogButtonBox.Cancel, QDialogButtonBox.Apply]),
])
@mock.patch('qtpy.QtWidgets.QDialog.keyPressEvent')
def test_role_picker_force_select(keyPressEvent, qtbot: QtBot, force, reacts_to_escape, std_buttons):
    dialog = RbaRolePicker(roles=[], force_select=force)
    qtbot.add_widget(dialog)
    assert len(dialog.btn_box.buttons()) == len(std_buttons)
    for i, btn_type in enumerate(std_buttons):
        assert dialog.btn_box.buttons()[i] == dialog.btn_box.button(btn_type)

    ev = QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier)
    dialog.keyPressEvent(ev)
    if reacts_to_escape:
        keyPressEvent.assert_called_once_with(ev)
    else:
        keyPressEvent.assert_not_called()


@pytest.mark.parametrize('selected_roles,expected_roles', [
    (None, [
        CRBACRole(name='Role1', active=True),
        CRBACRole(name='Role2', active=True),
        CRBACRole(name='Role3', active=True),
        CRBACRole(name='MCS-Role1', active=False),
        CRBACRole(name='MCS-Role2', active=False),
    ]),
    ([], [
        CRBACRole(name='Role1', active=False),
        CRBACRole(name='Role2', active=False),
        CRBACRole(name='Role3', active=False),
        CRBACRole(name='MCS-Role1', active=False),
        CRBACRole(name='MCS-Role2', active=False),
    ]),
    (['Role1'], [
        CRBACRole(name='Role1', active=True),
        CRBACRole(name='Role2', active=False),
        CRBACRole(name='Role3', active=False),
        CRBACRole(name='MCS-Role1', active=False),
        CRBACRole(name='MCS-Role2', active=False),
    ]),
    (['Role1', 'Role2', 'MCS-Role1'], [
        CRBACRole(name='Role1', active=True),
        CRBACRole(name='Role2', active=True),
        CRBACRole(name='Role3', active=False),
        CRBACRole(name='MCS-Role1', active=True),
        CRBACRole(name='MCS-Role2', active=False),
    ]),
])
@mock.patch('comrad.rbac.rbac.AuthenticationClient')
def test_rbac_explicit_login_no_role_picker(AuthenticationClient, selected_roles, expected_roles):
    auth_client = mock.MagicMock()
    AuthenticationClient.create.return_value = auth_client

    def explicit_login(user, __, roles_callback):
        picked_roles = roles_callback(['Role1', 'Role2', 'Role3', 'MCS-Role1', 'MCS-Role2'])
        token = mock.MagicMock()
        token.get_user_name.return_value = user
        token.get_roles.return_value = picked_roles
        return token

    auth_client.login_explicit.side_effect = explicit_login

    rbac = CRBACState()
    assert rbac.status == CRBACLoginStatus.LOGGED_OUT
    rbac.login_by_credentials(user='TEST_USER', password='TEST_PASS', preselected_roles=selected_roles)
    assert rbac.status == CRBACLoginStatus.LOGGED_IN_BY_CREDENTIALS
    assert rbac.token is not None
    assert rbac.user == 'TEST_USER'
    assert rbac.token.roles == expected_roles


@pytest.mark.parametrize('selected_roles,expected_roles', [
    ([], [
        CRBACRole(name='Role1', active=False),
        CRBACRole(name='Role2', active=False),
        CRBACRole(name='Role3', active=False),
        CRBACRole(name='MCS-Role1', active=False),
        CRBACRole(name='MCS-Role2', active=False),
    ]),
    (['Role1'], [
        CRBACRole(name='Role1', active=True),
        CRBACRole(name='Role2', active=False),
        CRBACRole(name='Role3', active=False),
        CRBACRole(name='MCS-Role1', active=False),
        CRBACRole(name='MCS-Role2', active=False),
    ]),
    (['Role1', 'Role2', 'MCS-Role1'], [
        CRBACRole(name='Role1', active=True),
        CRBACRole(name='Role2', active=True),
        CRBACRole(name='Role3', active=False),
        CRBACRole(name='MCS-Role1', active=True),
        CRBACRole(name='MCS-Role2', active=False),
    ]),
])
@mock.patch('comrad.rbac.rbac.RbaRolePicker')
@mock.patch('comrad.rbac.rbac.AuthenticationClient')
def test_rbac_explicit_login_with_role_picker(AuthenticationClient, RbaRolePicker, selected_roles, expected_roles):

    def do_interactive_selection(callback):
        callback(selected_roles=selected_roles, role_picker=mock.MagicMock())

    RbaRolePicker.roles_selected.connect.side_effect = do_interactive_selection

    auth_client = mock.MagicMock()
    AuthenticationClient.create.return_value = auth_client

    def explicit_login(user, __, roles_callback):
        picked_roles = roles_callback(['Role1', 'Role2', 'Role3', 'MCS-Role1', 'MCS-Role2'])
        token = mock.MagicMock()
        token.get_user_name.return_value = user
        token.get_roles.return_value = picked_roles
        return token

    auth_client.login_explicit.side_effect = explicit_login

    rbac = CRBACState()
    assert rbac.status == CRBACLoginStatus.LOGGED_OUT
    rbac.login_by_credentials(user='TEST_USER', password='TEST_PASS', select_roles=True)
    assert rbac.status == CRBACLoginStatus.LOGGED_IN_BY_CREDENTIALS
    assert rbac.token is not None
    assert rbac.user == 'TEST_USER'
    assert rbac.token.roles == expected_roles


@pytest.mark.parametrize('selected_roles,expected_roles', [
    (None, [
        CRBACRole(name='Role1', active=True),
        CRBACRole(name='Role2', active=True),
        CRBACRole(name='Role3', active=True),
        CRBACRole(name='MCS-Role1', active=False),
        CRBACRole(name='MCS-Role2', active=False),
    ]),
    ([], [
        CRBACRole(name='Role1', active=False),
        CRBACRole(name='Role2', active=False),
        CRBACRole(name='Role3', active=False),
        CRBACRole(name='MCS-Role1', active=False),
        CRBACRole(name='MCS-Role2', active=False),
    ]),
    (['Role1'], [
        CRBACRole(name='Role1', active=True),
        CRBACRole(name='Role2', active=False),
        CRBACRole(name='Role3', active=False),
        CRBACRole(name='MCS-Role1', active=False),
        CRBACRole(name='MCS-Role2', active=False),
    ]),
    (['Role1', 'Role2', 'MCS-Role1'], [
        CRBACRole(name='Role1', active=True),
        CRBACRole(name='Role2', active=True),
        CRBACRole(name='Role3', active=False),
        CRBACRole(name='MCS-Role1', active=True),
        CRBACRole(name='MCS-Role2', active=False),
    ]),
])
@mock.patch('comrad.rbac.rbac.AuthenticationClient')
def test_rbac_location_login_no_role_picker(AuthenticationClient, selected_roles, expected_roles):
    auth_client = mock.MagicMock()
    AuthenticationClient.create.return_value = auth_client

    def location_login(roles_callback):
        picked_roles = roles_callback(['Role1', 'Role2', 'Role3', 'MCS-Role1', 'MCS-Role2'])
        token = mock.MagicMock()
        token.get_user_name.return_value = 'TEST_USER'
        token.get_roles.return_value = picked_roles
        return token

    auth_client.login_location.side_effect = location_login

    rbac = CRBACState()
    assert rbac.status == CRBACLoginStatus.LOGGED_OUT
    rbac.login_by_location(preselected_roles=selected_roles)
    assert rbac.status == CRBACLoginStatus.LOGGED_IN_BY_LOCATION
    assert rbac.token is not None
    assert rbac.user == 'TEST_USER'
    assert rbac.token.roles == expected_roles


@pytest.mark.parametrize('selected_roles,expected_roles', [
    ([], [
        CRBACRole(name='Role1', active=False),
        CRBACRole(name='Role2', active=False),
        CRBACRole(name='Role3', active=False),
        CRBACRole(name='MCS-Role1', active=False),
        CRBACRole(name='MCS-Role2', active=False),
    ]),
    (['Role1'], [
        CRBACRole(name='Role1', active=True),
        CRBACRole(name='Role2', active=False),
        CRBACRole(name='Role3', active=False),
        CRBACRole(name='MCS-Role1', active=False),
        CRBACRole(name='MCS-Role2', active=False),
    ]),
    (['Role1', 'Role2', 'MCS-Role1'], [
        CRBACRole(name='Role1', active=True),
        CRBACRole(name='Role2', active=True),
        CRBACRole(name='Role3', active=False),
        CRBACRole(name='MCS-Role1', active=True),
        CRBACRole(name='MCS-Role2', active=False),
    ]),
])
@mock.patch('comrad.rbac.rbac.RbaRolePicker')
@mock.patch('comrad.rbac.rbac.AuthenticationClient')
def test_rbac_location_login_with_role_picker(AuthenticationClient, RbaRolePicker, selected_roles, expected_roles):

    def do_interactive_selection(callback):
        callback(selected_roles=selected_roles, role_picker=mock.MagicMock())

    RbaRolePicker.roles_selected.connect.side_effect = do_interactive_selection

    auth_client = mock.MagicMock()
    AuthenticationClient.create.return_value = auth_client

    def location_login(roles_callback):
        picked_roles = roles_callback(['Role1', 'Role2', 'Role3', 'MCS-Role1', 'MCS-Role2'])
        token = mock.MagicMock()
        token.get_user_name.return_value = 'TEST_USER'
        token.get_roles.return_value = picked_roles
        return token

    auth_client.login_location.side_effect = location_login

    rbac = CRBACState()
    assert rbac.status == CRBACLoginStatus.LOGGED_OUT
    rbac.login_by_location(preselected_roles=selected_roles)
    assert rbac.status == CRBACLoginStatus.LOGGED_IN_BY_LOCATION
    assert rbac.token is not None
    assert rbac.user == 'TEST_USER'
    assert rbac.token.roles == expected_roles


@pytest.mark.parametrize('connect_signal,expected_user,expected_status,method_call,kwargs,encoded', [
    (True, None, CRBACLoginStatus.LOGGED_IN_BY_LOCATION, 'login_by_location', {}, [1, 2, 3]),
    (False, 'LOC_USER', CRBACLoginStatus.LOGGED_IN_BY_LOCATION, 'login_by_location', {}, None),
    (True, None, CRBACLoginStatus.LOGGED_IN_BY_CREDENTIALS, 'login_by_credentials', {'user': 'TEST_USER', 'password': '123'}, [4, 5, 6]),
    (False, 'TEST_USER', CRBACLoginStatus.LOGGED_IN_BY_CREDENTIALS, 'login_by_credentials', {'user': 'TEST_USER', 'password': '123'}, None),
])
@mock.patch('comrad.rbac.rbac.AuthenticationClient')
def test_rbac_syncs_rbac_token(AuthenticationClient, qtbot: QtBot, connect_signal, expected_status, expected_user, method_call, kwargs, encoded):
    auth_client = mock.MagicMock()
    AuthenticationClient.create.return_value = auth_client
    exp_token = mock.MagicMock()
    exp_token.get_user_name.return_value = kwargs.get('user')
    exp_token.get_encoded.return_value = [4, 5, 6]
    loc_token = mock.MagicMock()
    loc_token.get_user_name.return_value = 'LOC_USER'
    loc_token.get_encoded.return_value = [1, 2, 3]
    auth_client.login_location.return_value = loc_token
    auth_client.login_explicit.return_value = exp_token

    rbac = CRBACState()
    assert rbac.status == CRBACLoginStatus.LOGGED_OUT

    if connect_signal:
        with qtbot.wait_signal(rbac.rbac_token_changed) as blocker:
            getattr(rbac, method_call)(**kwargs)
        assert blocker.args == [encoded, expected_status.value]
        # These values are assumed to be set separately by Java, when token is accepted
        assert rbac.status == CRBACLoginStatus.LOGGED_OUT
        assert rbac.user is None
    else:
        getattr(rbac, method_call)(**kwargs)
        assert rbac.status == expected_status
        assert rbac.user == expected_user


@pytest.mark.parametrize('rbac_env,key_filename', [
    (None, 'rba-bundled-pub-key.txt'),
    ('PRO', 'rba-bundled-pub-key.txt'),
    ('DEV', 'rba-bundled-int-pub-key.txt'),
    ('TEST', 'rba-bundled-test-pub-key.txt'),
    ('INT', 'rba-bundled-int-pub-key.txt'),
])
@mock.patch('comrad.rbac.rbac.AuthenticationClient')
def test_rbac_bundles_key(AuthenticationClient, rbac_env, key_filename):

    def key_error():
        if os.environ.get('RBAC_PKEY') is None:
            raise RuntimeError("Can't find the public key")
        return mock.MagicMock()

    AuthenticationClient.create.side_effect = key_error
    assert os.environ.get('RBAC_PKEY') is None
    assert os.environ.get('RBAC_ENV') is None
    rbac = CRBACState(rbac_env=rbac_env)
    # Public key must be resolved lazily
    assert os.environ.get('RBAC_PKEY') is None
    assert os.environ.get('RBAC_ENV') is None
    rbac.login_by_location()
    import comrad.rbac
    assert os.environ['RBAC_PKEY'] == str(Path(comrad.rbac.__file__).parent / key_filename)


@mock.patch('comrad.rbac.rbac.AuthenticationClient')
def test_rbac_key_not_found(AuthenticationClient):

    def key_error():
        if os.environ.get('RBAC_PKEY') is None:
            raise RuntimeError("Can't find the public key")
        return mock.MagicMock()

    AuthenticationClient.create.side_effect = key_error
    assert os.environ.get('RBAC_PKEY') is None
    assert os.environ.get('RBAC_ENV') is None
    rbac = CRBACState(rbac_env='NOT_EXISTING')
    # Public key must be resolved lazily
    assert os.environ.get('RBAC_PKEY') is None
    assert os.environ.get('RBAC_ENV') is None
    with pytest.raises(ValueError, match=r'Unrecognized RBAC environment name: NOT_EXISTING'):
        rbac.login_by_location()


@pytest.mark.parametrize(f'name,critical', [
    ('AAA', False),
    ('XXX', False),
    ('MCS-', True),
    ('mcs-', False),
    ('MCS-smth', True),
    ('mcs-smth', False),
    ('AAA-MCS-XXX', False),
])
def test_rbac_role_critical(name, critical):
    assert CRBACRole(name=name).is_critical == critical


@pytest.mark.parametrize('second_obj_type,equal_by_type', [
    (CRBACRole, True),
    (mock.MagicMock, False),
])
@pytest.mark.parametrize('lifetime1', [None, -1, 0, 10])
@pytest.mark.parametrize('lifetime2', [None, -1, 0, 10])
@pytest.mark.parametrize('active1', [True, False])
@pytest.mark.parametrize('active2', [True, False])
@pytest.mark.parametrize('name1,name2,equal_by_name', [
    ('AAA', None, False),
    ('AAA', '', False),
    ('AAA', 'AAA-', False),
    ('AAA', 'MCS-AAA', False),
    ('AAA', 'AAA', True),
    ('AAA', 'aaa', False),
])
def test_rbac_role_equality(second_obj_type, equal_by_name, equal_by_type,
                            lifetime1, lifetime2, active1, active2, name1, name2):
    role1 = CRBACRole(name=name1, lifetime=lifetime1, active=active1)
    role2 = second_obj_type(name=name2, lifetime=lifetime2, active=active2)
    assert (role1 == role2) == (equal_by_type and equal_by_name)


@pytest.mark.parametrize('src_acc_type,expected_acc_str', [
    (pyrbac.AccountType.AT_PRIMARY, 'Primary'),
    (pyrbac.AccountType.AT_SECONDARY, 'Secondary'),
    (pyrbac.AccountType.AT_SERVICE, 'Service'),
    (pyrbac.AccountType.AT_UNKNOWN, 'Unknown'),
])
@pytest.mark.parametrize('src_is_expired,expected_valid', [
    (True, False),
    (False, True),
])
@pytest.mark.parametrize('empty', [True, False])
@pytest.mark.parametrize('loc_auth_required', [True, False])
@pytest.mark.parametrize('src_lifetimes,expected_lifetimes', [
    (None, [-1, -1, -1, -1, -1, -1, -1, -1]),  # Assume extra_fields == None for this
    ([], [-1, -1, -1, -1, -1, -1, -1, -1]),
    ([1, 2, 3, 4], [1, 2, -1, -1, 3, 4, -1, -1]),
])
def test_token_info(src_acc_type, expected_acc_str, src_is_expired, expected_valid, empty, loc_auth_required,
                    src_lifetimes, expected_lifetimes):
    ll_token = mock.MagicMock()
    ll_token.get_user_name.return_value = 'TEST_USERNAME'
    ll_token.get_full_name.return_value = 'TEST_FULL_NAME'
    ll_token.get_user_email.return_value = 'TEST_EMAIL'
    ll_token.get_account_type.return_value = src_acc_type
    ll_token.is_token_expired.return_value = src_is_expired
    ll_token.empty.return_value = empty
    ll_token.get_authentication_time.return_value = datetime(2020, 1, 1, 12, 53, 23).timestamp()
    ll_token.get_expiration_time.return_value = datetime(2020, 1, 1, 13, 0, 0).timestamp()
    ll_token.get_roles.return_value = ['Role1', 'Role2', 'MCS-Role1', 'MCS-Role2']
    if src_lifetimes is None:
        ll_token.get_extra_fields.return_value = None
    else:
        ll_token.get_extra_fields.return_value.get_roles_lifetime.return_value = src_lifetimes
    ll_token.get_application_name.return_value = 'TEST_APP'
    ll_token.get_location_name.return_value = 'TEST_LOC'
    ll_token.get_location_address.return_value = [-246, -246, -1, -1]
    ll_token.is_location_auth_required.return_value = loc_auth_required
    ll_token.get_serial_id.return_value = 195948557

    all_roles = ['Role1',
                 'Role2',
                 'Role3',
                 'Role4',
                 'MCS-Role1',
                 'MCS-Role2',
                 'MCS-Role3',
                 'MCS-Role4']
    active_roles = [True, True, False, False, True, True, False, False]

    token = CRBACToken(original_token=ll_token, available_roles=all_roles)
    assert token.username == 'TEST_USERNAME'
    assert token.user_email == 'TEST_EMAIL'
    assert token.user_full_name == 'TEST_FULL_NAME'
    assert token.account_type == expected_acc_str
    assert token.valid == expected_valid
    assert token.empty == empty
    assert token.auth_timestamp == datetime(2020, 1, 1, 12, 53, 23)
    assert token.expiration_timestamp == datetime(2020, 1, 1, 13, 0, 0)
    assert token.roles == [CRBACRole(name=name, lifetime=lifetime, active=active)
                           for name, lifetime, active in zip(all_roles, expected_lifetimes, active_roles)]
    assert token.app_name == 'TEST_APP'
    assert token.location is not None
    assert token.location.name == 'TEST_LOC'
    assert token.location.address == '10.10.255.255'
    assert token.location.auth_required == loc_auth_required
    assert token.serial_id == '0xbadf00d'
