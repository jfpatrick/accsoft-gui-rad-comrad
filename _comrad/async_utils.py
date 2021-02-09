import asyncio
import logging
from typing import Optional
from qtpy.QtGui import QGuiApplication
from qasync import QEventLoop


logger = logging.getLogger(__name__)


def install_asyncio_event_loop(app: Optional[QGuiApplication] = None):
    if isinstance(asyncio.get_event_loop(), QEventLoop):
        return

    if app is None:
        app = QGuiApplication.instance()

    logger.debug(f'Setting asyncio event loop to Qt event loop of "{app.applicationName()}"')
    event_loop = QEventLoop(app)
    asyncio.set_event_loop(event_loop)
