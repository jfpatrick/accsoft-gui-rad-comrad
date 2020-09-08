from pytestqt.qtbot import QtBot
from typing import cast
from accwidgets.rbac import RbaButton
from comrad import CApplication
from comrad.app.plugins.toolbar.rbac_plugin import RbaToolbarPlugin


def test_rbac_plugin_widget(qtbot: QtBot):
    app = cast(CApplication, CApplication.instance())
    button = cast(RbaButton, RbaToolbarPlugin().create_widget({}))
    qtbot.add_widget(button)
    assert isinstance(button, RbaButton)
    assert button.model is app.rbac._model
