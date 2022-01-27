import logging
from typing import Optional, Dict, cast
from accwidgets.screenshot import ScreenshotButton, ScreenshotAction, LogbookModel
from pylogbook import NamedServer
from comrad import CApplication
from comrad.app.plugins.common import CToolbarWidgetPlugin


logger = logging.getLogger('comrad.app.plugins.toolbar.screenshot_plugin')


def report_screenshot_problem(error: str):
    logger.warning(error)


class ScreenshotToolbarPlugin(CToolbarWidgetPlugin):
    """Plugin to display screenshot (e-logbook) button in the toolbar."""

    position = CToolbarWidgetPlugin.Position.RIGHT
    plugin_id = 'comrad.screenshot'
    gravity = 998
    enabled = False

    def create_widget(self, config: Optional[Dict[str, str]]):
        config = config or {}
        app = cast(CApplication, CApplication.instance())
        decor = config.get('decor', False)
        if decor == '1':
            decor = True
        server_name = config.get('server', 'PRO')
        try:
            server = getattr(NamedServer, server_name)
        except AttributeError:
            server = NamedServer.PRO
        activities = config.get('activities', None)
        model = LogbookModel(server_url=server,
                             rbac_token=app.rbac.serialized_token)
        model.activities_failed.connect(report_screenshot_problem)
        model.logbook_activities = activities
        widget = ScreenshotButton(action=ScreenshotAction(model=model))
        widget.includeWindowDecorations = decor
        widget.eventFetchFailed.connect(report_screenshot_problem)
        widget.captureFailed.connect(report_screenshot_problem)

        app.rbac.login_succeeded.connect(model.reset_rbac_token)
        app.rbac.logout_finished.connect(model.reset_rbac_token)
        return widget
