import json
import operator
from typing import Optional, Union
from datetime import datetime, timedelta
from pathlib import Path
from qtpy import uic
from qtpy.QtWidgets import QDialog, QDialogButtonBox, QWidget, QFormLayout, QLabel
from comrad.rbac import CRBACToken


class RbaTokenDialog(QDialog):

    def __init__(self, token: CRBACToken, parent: Optional[QWidget] = None):
        """
        Dialog to select user roles.

        Args:
            token: Token that contains the information.
            parent: Parent widget to own this object.
        """
        super().__init__(parent)

        # For IDE support, assign types to dynamically created items from the *.ui file
        self.btn_box: QDialogButtonBox = None
        self.form: QFormLayout = None

        uic.loadUi(Path(__file__).parent / 'token_dialog.ui', self)

        self.btn_box.rejected.connect(self.close)

        form = self.form

        def add_form_row(title: str, content: Union[str, QLabel]):
            lbl_title = QLabel(title)
            font = lbl_title.font()
            font.setBold(True)
            lbl_title.setFont(font)
            if isinstance(content, str):
                content = QLabel(content)
            form.addRow(lbl_title, content)

        add_form_row('User Name', f'{token.username} [{token.user_full_name}, '
                                  f'{token.user_email}]')
        add_form_row('Account Type', token.account_type)
        valid_lbl = QLabel(json.dumps(token.valid))
        valid_lbl.setStyleSheet(f'background-color: {_COLOR_GREEN if token.valid else _COLOR_RED}')
        add_form_row('Is Valid ?', valid_lbl)
        add_form_row('Start Time', _create_date_label(token.auth_timestamp))
        add_form_row('Expiration Time', _create_date_label(token.expiration_timestamp, past_color=_COLOR_RED))

        roles = [f'{role.name} [critical={json.dumps(role.is_critical)}; lifetime={role.lifetime}]'
                 for role in sorted(filter(operator.attrgetter('active'), token.roles), key=operator.attrgetter('name'))]
        add_form_row('Roles', '\n'.join(roles))

        add_form_row('Application', token.app_name)
        add_form_row('Location', f'{token.location.name} ['
                                 f'address={token.location.address}; '  # Assuming IPv4 here (it's also coming negative, needs bias)
                                 f'auth-reqd={json.dumps(token.location.auth_required)}]')
        add_form_row('Serial ID', token.serial_id)


_COLOR_GREEN = '#66ff66'
_COLOR_RED = '#ff5050'


def _create_date_label(date: datetime, past_color: Optional[str] = None) -> QLabel:
    dt = date - datetime.now()
    lbl = QLabel(f'{date.isoformat(sep=" ")} (About {_format_timedelta(dt)})')
    if past_color is not None and dt < timedelta(0):
        lbl.setStyleSheet(f'color: {past_color}')  # Palette does not work here
    return lbl


def _format_timedelta(td: timedelta) -> str:

    if td == timedelta(0):
        return 'now'

    def multiple(word: str, amount: int) -> str:
        return word + ('' if amount == 1 else 's')

    res = []
    abs_td = abs(td)
    if abs_td.days > 0:
        res.append(f'{abs_td.days} {multiple("day", abs_td.days)}')
    hours, remainder = divmod(abs_td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours > 0:
        res.append(f'{hours} {multiple("hour", hours)}')
    if minutes > 0:
        res.append(f'{minutes} min.')
    if seconds > 0:
        res.append(f'{seconds} sec.')
    if td > timedelta(0):
        res.append('from now')
    else:
        res.append('ago')
    return ' '.join(res)
