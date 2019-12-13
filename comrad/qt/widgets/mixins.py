import logging
from qtpy.QtCore import Property
from pydm.utilities import is_qt_designer


logger = logging.getLogger(__name__)


class HideUnusedFeaturesMixin:

    @Property(bool, designable=False)
    def alarmSensitiveBorder(self) -> bool:
        return False

    @alarmSensitiveBorder.setter  # type: ignore
    def alarmSensitiveBorder(self, _: bool):
        if not is_qt_designer():
            logger.warning(f'alarmSensitiveBorder property is disabled for the {type(self).__name__} widget.')
        return

    @Property(bool, designable=False)
    def alarmSensitiveContent(self) -> bool:
        return False

    @alarmSensitiveContent.setter  # type: ignore
    def alarmSensitiveContent(self, _: bool):
        if not is_qt_designer():
            logger.warning(f'alarmSensitiveContent property is disabled for the {type(self).__name__} widget.')
        return
