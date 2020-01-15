import logging
from typing import Optional
from qtpy.QtWidgets import QWidget
from pydm.widgets.logdisplay import PyDMLogDisplay
# from pydm.widgets.waveformtable import PyDMWaveformTable


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


class CLogDisplay(PyDMLogDisplay):

    def __init__(self,
                 parent: Optional[QWidget] = None,
                 log_name: Optional[str] = None,
                 level: int = logging.NOTSET,
                 **kwargs):
        """
        Standard display for log output.

        This widget handles instantiating a ``GuiHandler`` and displaying log
        messages to a :class:`PyQt5.QtWidgets.QPlainTextEdit`. The level of the log can be changed from
        inside the widget itself, allowing users to select from any of the levels specified by the widget.

        Args:
            parent: The parent widget for the log display.
            log_name: Name of log to display in widget.
            level: Initial level of log display.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        super().__init__(parent=parent, logname=log_name, level=level, **kwargs)
