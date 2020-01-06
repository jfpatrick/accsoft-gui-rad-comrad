import pytest


@pytest.fixture(autouse=True)
def patch_app_singleton(monkeypatch):

    class FakeApp:

        def __init__(self):
            print(f'Instantiating fake app instance')
            from comrad.rbac import RBACState, RBACStartupLoginPolicy
            self.rbac = RBACState()
            self.rbac.startup_login_policy = RBACStartupLoginPolicy.NO_LOGIN
            self.use_inca = False
            self.jvm_flags = {}

        def on_control_error(self, *args, **kwargs):
            pass

    test_app = FakeApp()

    def fake_app() -> FakeApp:
        return test_app

    import comrad.app.application

    monkeypatch.setattr(comrad.app.application.CApplication, 'instance', fake_app)
