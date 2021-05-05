import logging
import pytest
from unittest import mock
from logging import LogRecord
from typing import List, cast, Optional
from _pytest.logging import LogCaptureFixture


@pytest.fixture(autouse=True)
def patch_app_singleton(monkeypatch):

    class FakeApp(mock.MagicMock):

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            print('Instantiating fake app instance')
            from comrad.rbac import CRbaState, CRbaStartupLoginPolicy
            self.rbac = CRbaState(startup_policy=CRbaStartupLoginPolicy.NO_LOGIN)
            self.use_inca = False
            self.jvm_flags = {}

        processEvents = mock.Mock()  # Required for pytest-qt to operate properly
        on_control_error = mock.Mock()  # Required for japc_plugin to instantiate
        aboutToQuit = mock.Mock()
        main_window = mock.MagicMock()

    test_app = FakeApp()

    from comrad.data.context import CContext
    test_app.main_window.context_view = test_app.main_window.window_context = CContext()
    test_app.main_window.context_ready = True

    def fake_app() -> FakeApp:
        return test_app

    # Patch all variants that can be used to access application singleton
    import comrad.app.application
    monkeypatch.setattr(comrad.app.application.CApplication, 'instance', fake_app)

    import qtpy.QtCore
    monkeypatch.setattr(qtpy.QtCore.QCoreApplication, 'instance', fake_app)
    # With queued connections the tested logic is asynchronous and even qtbot.wait_signal struggles with that
    # So the simplest way is to force all queued connections to be direct.
    qtpy.QtCore.Qt.QueuedConnection = qtpy.QtCore.Qt.DirectConnection

    import qtpy.QtGui
    monkeypatch.setattr(qtpy.QtGui.QGuiApplication, 'instance', fake_app)

    import qtpy.QtWidgets
    monkeypatch.setattr(qtpy.QtWidgets.QApplication, 'instance', fake_app)


@pytest.fixture
def log_capture(caplog: LogCaptureFixture):

    # Make sure all records are being captured
    logging.getLogger().setLevel(logging.DEBUG)

    def wrapper(level: int, logger_name: Optional[str] = None, logger_module: Optional[str] = None):

        def satisfies_condition(r: LogRecord) -> bool:
            if logger_name:
                return r.name == logger_name
            elif logger_module:
                return r.module == logger_module
            else:
                return True

        return [r.getMessage() for r in cast(List[LogRecord], caplog.records) if
                r.levelno == level and satisfies_condition(r)]

    return wrapper
