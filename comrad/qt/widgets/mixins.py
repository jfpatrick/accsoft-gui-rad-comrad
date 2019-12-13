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
            logger.warning(f'alarmSensitiveBorder property is disabled in ComRAD')

    @Property(bool, designable=False)
    def alarmSensitiveContent(self) -> bool:
        return False

    @alarmSensitiveContent.setter  # type: ignore
    def alarmSensitiveContent(self, _: bool):
        if not is_qt_designer():
            logger.warning(f'alarmSensitiveContent property is disabled in ComRAD')


class NoPVTextFormatterMixin:

    @Property(bool, designable=False)
    def precisionFromPV(self) -> bool:
        return False

    @precisionFromPV.setter  # type: ignore
    def precisionFromPV(self, _: bool):
        if not is_qt_designer():
            logger.warning(f'precisionFromPV property is disabled in ComRAD')

    # TODO: We should enable showUnits, when unit support is implemented on the CS level
    @Property(bool, designable=False)
    def showUnits(self) -> bool:
        return False

    @showUnits.setter  # type: ignore
    def showUnits(self, _: bool):
        if not is_qt_designer():
            logger.warning(f'showUnits property is disabled in ComRAD')
