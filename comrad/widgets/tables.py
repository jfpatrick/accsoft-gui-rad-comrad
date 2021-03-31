import logging
import json
from typing import Optional, List, Dict, cast, TypeVar
from qtpy.QtCore import Property
from qtpy.QtWidgets import QWidget
from qtpy.QtGui import QShowEvent
from pydm.utilities import is_qt_designer
# from pydm.widgets.waveformtable import PyDMWaveformTable
from accwidgets.log_console import (LogConsole, AbstractLogConsoleFormatter, AbstractLogConsoleModel, LogConsoleModel,
                                    LogLevel)


logger = logging.getLogger(__name__)

# TODO: Uncomment when proven useful
# class CWaveFormTable(CWidgetRulesMixin, CCustomizedTooltipMixin, CHideUnusedFeaturesMixin, PyDMWaveformTable):
#
#     def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
#         """
#         A :class:`PyQt5.QTableWidget` with support for CS Channels.
#
#         Values of the array are displayed in the selected number of columns.
#         The number of rows is determined by the size of the waveform.
#         It is possible to define the labels of each row and column.
#
#         Args:
#             parent: The parent widget for the table.
#             init_channel: The channel to be used by the widget.
#             **kwargs: Any future extras that need to be passed down to PyDM.
#         """
#         CWidgetRulesMixin.__init__(self)
#         CCustomizedTooltipMixin.__init__(self)
#         CHideUnusedFeaturesMixin.__init__(self)
#         PyDMWaveformTable.__init__(self, parent=parent, init_channel=init_channel, **kwargs)


_M = TypeVar('_M', bound=AbstractLogConsoleModel)
_F = TypeVar('_F', bound=AbstractLogConsoleFormatter)


class CLogConsole(LogConsole):

    def __init__(self,
                 parent: Optional[QWidget] = None,
                 model: Optional[_M] = None,
                 loggers: Optional[Dict[str, LogLevel]] = None,
                 formatter: Optional[_F] = None):
        """
        Widget to display logs in a HTML-stylized list.

        The last message is always duplicated in a single-line field and the color related to its severity level
        is flashed in that field to attract end-user's attention. The widget has two modes: collapsed and expanded,
        where a full log view is visible or hidden respectively. The single-line field of the last message is visible
        in either mode.

        The mode change can be forbidden by setting the :attr:`collapsible` property to :obj:`False` in cases, when
        hiding parts of the console is undesirable.

        This widget can work with models that define where logs come from and how they are stored. If no custom model
        is provided, the default implementation, :class:`LogConsoleModel` is created that captures Python
        :mod:`logging` output.

        The widget provides a context menu on the right mouse click to:

        - "Freeze"/"unfreeze" the console ("frozen" console becomes static and does not display new logs, until
          "unfrozen")
        - Search for text visible in the console
        - Print visible console logs
        - Configure the display and capturing of the logs in a "Preferences" dialog

        While capturing and storing the logging records is managed by the :attr:`model`, :attr:`formatter` is
        responsible for producing the final string. Default implementation, :class:`LogConsoleFormatter`, can
        show/hide date, time and logger names of individual records. Custom formatters may have completely different
        settings.

        Log severity associated colors are configurable by the user. When such color is used as background rather than
        foreground (e.g. in last message field; or in the main text view, when color is marked as "inverted") the
        foreground text color is chosen automatically between black and white, to have the best contrast, based on the
        background's intensity.

        Args:
            parent: Owning object.
            model: Custom model that should be used with the widget. Model's ownership gets transferred to the widget.
                   If no model is provided, the default implementation, :class:`LogConsoleModel` is used instead.
            loggers: Default loggers and their associated severity levels.
            formatter: Custom implementation of the formatter (see :attr:`formatter`). If no formatter is provided,
                       the default implementation, :class:`LogConsoleFormatter` is used instead.
        """
        if loggers is not None and model is not None:
            raise ValueError("'model' and 'loggers' are mutually exclusive.")
        # Logger levels variable is needed to display an empty dict with the default setup, and not fallback
        # to always showing root and others. It has to come before super init, because properties are being
        # enumerated in the super call, and this variable will be accessed
        self._logger_levels: Dict[str, LogLevel] = {}
        self._loggers_initialized: bool = False
        super().__init__(parent=parent, model=model, formatter=formatter)
        if model is not None:
            self._logger_levels = {**model.selected_logger_levels}
        elif loggers:
            self.loggers = loggers

    def _get_loggers(self) -> Dict[str, LogLevel]:
        if is_qt_designer():
            return self.__pack_designer_levels(self._logger_levels)  # type: ignore  # we want string here for Designer
        return self._logger_levels

    def _set_loggers(self, new_val: Dict[str, LogLevel]):
        if isinstance(new_val, str):  # Can happen inside the Designer or when initializing from *.ui file
            new_val = self._unpack_designer_levels(cast(str, new_val))

        self._logger_levels = new_val
        model = self.model  # type: ignore  # mypy ignores even casts and throws "Cannot determine type of 'model'"
        if model is None:
            # Model is not ready yet. Wait
            return

        if type(model) != LogConsoleModel:  # Do not even allow subclasses
            logger.error(f'Cannot set Python loggers on an unsupported model type "{type(model).__name__}".')
            return

        self._loggers_initialized = True

        logger_objects: List[logging.Logger] = []

        if not new_val:
            logger_objects = self.get_python_logger_levels()
        else:
            for log_name in new_val:
                if log_name == 'root' or log_name == 'ROOT':
                    logger_objects.append(logging.getLogger())
                else:
                    logger_objects.append(logging.getLogger(log_name))

        new_model = LogConsoleModel(buffer_size=model.buffer_size,
                                    visible_levels=model.visible_levels,
                                    loggers=logger_objects,
                                    parent=model.parent(),
                                    level_changes_modify_loggers=model.level_changes_modify_loggers)
        if new_val:
            # Can't enter this in the constructor, so setting it after the fact
            new_model.selected_logger_levels = new_val

        self.model = new_model

    loggers: Dict[str, LogLevel] = Property(str, fget=_get_loggers, fset=_set_loggers, designable=False)
    """Tracked loggers and their associated severity levels."""

    def showEvent(self, event: QShowEvent):
        super().showEvent(event)

        # Allow the loggers to be set up, in case we need to fetch the standard blessed loggers of comrad
        # that were initialized after the initial model has been created
        if not self._loggers_initialized:
            self.loggers = self._logger_levels  # Either empty dict, or whatever was preset in constructor from existing model

    @classmethod
    def get_python_logger_levels(cls) -> List[logging.Logger]:
        """
        Collect all existing Python loggers that match the whitelist of top-level logger names, e.g.
        "comrad", "pyjapc", etc.
        """
        loggers: List[logging.Logger] = [logging.getLogger()]  # Root logger
        try:
            mgr = logging.Logger.manager  # type: ignore
            logging._acquireLock()  # type: ignore
            try:
                for logger in mgr.loggerDict.values():
                    # Only child loggers, and not Placeholder
                    if isinstance(logger, logging.Logger) and cls._default_logger_is_of_interest(logger.name):
                        loggers.append(logger)
            finally:
                logging._releaseLock()  # type: ignore
        except BaseException:  # noqa: B902
            pass
        return loggers

    @classmethod
    def _default_logger_is_of_interest(cls, name: str) -> bool:
        lower_name = name.lower()
        return (lower_name in ('comrad', 'pydm')
                or 'pyjapc' in lower_name
                or 'pyrbac' in lower_name
                or 'pytimber' in lower_name
                or 'pjlsa' in lower_name
                or 'pylogbook' in lower_name
                or 'pyrda' in lower_name
                or lower_name.startswith('papc.'))

    @classmethod
    def _unpack_designer_levels(cls, input: str) -> Dict[str, LogLevel]:
        try:
            contents = json.loads(input)
        except json.JSONDecodeError as ex:
            logger.warning(f'Failed to decode json: {str(ex)}')
            return {}

        if not isinstance(contents, dict):
            logger.warning('Decoded logger levels is not a dictionary')
            return {}

        return {name: LogLevel(level) for name, level in contents.items()}

    @classmethod
    def __pack_designer_levels(cls, input: Dict[str, LogLevel]) -> str:
        return json.dumps({name: level.value for name, level in input.items()})
