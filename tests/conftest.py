import pytest
from unittest import mock


@pytest.fixture(autouse=True)
def patch_app_singleton(monkeypatch):

    class FakeApp:

        def __init__(self):
            print(f'Instantiating fake app instance')
            from comrad.rbac import CRBACState, CRBACStartupLoginPolicy
            self.rbac = CRBACState()
            self.rbac.startup_login_policy = CRBACStartupLoginPolicy.NO_LOGIN
            self.use_inca = False
            self.jvm_flags = {}

        processEvents = mock.MagicMock()  # Required for pytest-qt to operate properly
        on_control_error = mock.MagicMock()  # Required for japc_plugin to instantiate
        aboutToQuit = mock.MagicMock()

    test_app = FakeApp()

    def fake_app() -> FakeApp:
        return test_app

    # Patch all variants that can be used to access application singleton
    import comrad.app.application
    monkeypatch.setattr(comrad.app.application.CApplication, 'instance', fake_app)

    import qtpy.QtCore
    monkeypatch.setattr(qtpy.QtCore.QCoreApplication, 'instance', fake_app)

    import qtpy.QtGui
    monkeypatch.setattr(qtpy.QtGui.QGuiApplication, 'instance', fake_app)

    import qtpy.QtWidgets
    monkeypatch.setattr(qtpy.QtWidgets.QApplication, 'instance', fake_app)
