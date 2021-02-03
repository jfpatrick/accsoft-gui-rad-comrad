"""
Plugins for Qt Designer that are visible ComRAD widgets.
"""

# Do not crash Qt Designer on Ctrl+C
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

import accwidgets.property_edit.designer
import accwidgets.led.designer
import accwidgets.log_console.designer
from pathlib import Path
from typing import List
from qtpy.QtWidgets import QAction, QWidget

# Has to be above first main comrad package import
from _comrad_designer.log_config import setup_logging
setup_logging()

# from pydm.widgets.tab_bar_qtplugin import TabWidgetPlugin as PyDMTabWidgetPlugin
from accwidgets.property_edit.designer.designer_extensions import PropertyFieldExtension
from accwidgets._designer_base import WidgetsTaskMenuExtension
from comrad import (CScrollingPlot, CCyclicPlot, CStaticPlot, CValueAggregator, CCommandButton, CScaleIndicator,
                    CEnumComboBox, CSlider, CSpinBox, CLabel, CByteIndicator, CLineEdit, CTemplateRepeater,
                    CEmbeddedDisplay, CShellCommand, CRelatedDisplayButton, CPushButton, CEnumButton, CCheckBox,
                    CPropertyEdit, CLed, CContextFrame, CLogConsole)
from comrad.icons import icon
from _comrad_designer.utils import qtplugin_factory, CWidgetBoxGroup
from _comrad_designer.rules_editor import RulesEditor
from _comrad_designer.graphs import CPlottingItemEditorExtension, CLayerEditorExtension
from _comrad_designer.log_console import CLogConsoleLoggersEditorExtension


class _RulesExtension(WidgetsTaskMenuExtension):

    def __init__(self, widget: QWidget):
        """
        Rules extension creates a task menu entry to open a rules editor dialog.

        Args:
            widget: Widget to apply the extension to.
        """
        super().__init__(widget)
        self._action = QAction('Edit Rules...', self.widget)
        self._action.triggered.connect(self._edit_rules)

    def actions(self) -> List[QAction]:
        """List of all actions exposed by the extension."""
        return [self._action]

    def _edit_rules(self):
        RulesEditor(widget=self.widget, parent=None).exec_()


_BASE_EXTENSIONS = [_RulesExtension]
_PLOT_EXTENSIONS = [CPlottingItemEditorExtension, CLayerEditorExtension]


# Buttons
_CCheckbox = qtplugin_factory(CCheckBox, group=CWidgetBoxGroup.BUTTONS, extensions=_BASE_EXTENSIONS)


_CEnumButton = qtplugin_factory(CEnumButton, group=CWidgetBoxGroup.BUTTONS, extensions=_BASE_EXTENSIONS)
_CPushButton = qtplugin_factory(CPushButton, group=CWidgetBoxGroup.BUTTONS, extensions=_BASE_EXTENSIONS)
_CCommandButton = qtplugin_factory(CCommandButton, group=CWidgetBoxGroup.BUTTONS)
_CRelatedDisplayButton = qtplugin_factory(CRelatedDisplayButton, group=CWidgetBoxGroup.BUTTONS)
_CShellCommand = qtplugin_factory(CShellCommand, group=CWidgetBoxGroup.BUTTONS)
# _CToggleButton = qtplugin_factory(CToggleButton, group=CWidgetBoxGroup.BUTTONS, extensions=_BASE_EXTENSIONS)

# Item Widgets
# TODO: Uncomment when useful
# _CWaveformTable = qtplugin_factory(CWaveFormTable, group=CWidgetBoxGroup.ITEM_WIDGETS, extensions=_BASE_EXTENSIONS)

# Containers
# TODO: What is CFrame useful for?
# _CFrame = qtplugin_factory(CFrame, group=CWidgetBoxGroup.CONTAINERS, is_container=True, extensions=_BASE_EXTENSIONS)
_CEmbeddedDisplay = qtplugin_factory(CEmbeddedDisplay, group=CWidgetBoxGroup.CONTAINERS)
_CTemplateRepeater = qtplugin_factory(CTemplateRepeater, group=CWidgetBoxGroup.CONTAINERS)
_CContextFrame = qtplugin_factory(CContextFrame, group=CWidgetBoxGroup.CONTAINERS, is_container=True)

# Input Widgets
_CEnumComboBox = qtplugin_factory(CEnumComboBox, group=CWidgetBoxGroup.INPUTS, extensions=_BASE_EXTENSIONS)
_CLineEdit = qtplugin_factory(CLineEdit, group=CWidgetBoxGroup.INPUTS, extensions=_BASE_EXTENSIONS)
_CSlider = qtplugin_factory(CSlider, group=CWidgetBoxGroup.INPUTS, extensions=_BASE_EXTENSIONS)
_CSpinbox = qtplugin_factory(CSpinBox, group=CWidgetBoxGroup.INPUTS, extensions=_BASE_EXTENSIONS)
_CPropertyEdit = qtplugin_factory(CPropertyEdit,
                                  group=CWidgetBoxGroup.INPUTS,
                                  icon=icon('PropertyEdit', file_path=Path(accwidgets.property_edit.designer.__file__)),
                                  extensions=[PropertyFieldExtension, *_BASE_EXTENSIONS])

# Display Widgets
_CLabel = qtplugin_factory(CLabel, group=CWidgetBoxGroup.INDICATORS, extensions=_BASE_EXTENSIONS)
_CByteIndicator = qtplugin_factory(CByteIndicator, group=CWidgetBoxGroup.INDICATORS, extensions=_BASE_EXTENSIONS)
# TODO: Uncomment when useful
# _CImageView = qtplugin_factory(CImageView, group=CWidgetBoxGroup.INDICATORS, extensions=_BASE_EXTENSIONS)
_CLogConsole = qtplugin_factory(CLogConsole,
                                group=CWidgetBoxGroup.INDICATORS,
                                icon=icon('LogConsole', file_path=Path(accwidgets.log_console.designer.__file__)),
                                extensions=[CLogConsoleLoggersEditorExtension])
_CScaleIndicator = qtplugin_factory(CScaleIndicator, group=CWidgetBoxGroup.INDICATORS, extensions=_BASE_EXTENSIONS)
_CEnumLed = qtplugin_factory(CLed,
                             group=CWidgetBoxGroup.INDICATORS,
                             icon=icon('Led', file_path=Path(accwidgets.led.designer.__file__)),
                             extensions=_BASE_EXTENSIONS)

# Charts
_CScrollingPlot = qtplugin_factory(CScrollingPlot,
                                   group=CWidgetBoxGroup.CHARTS,
                                   icon=icon('ScrollingPlotWidget', file_path=Path(accwidgets.graph.designer.__file__)),
                                   extensions=_PLOT_EXTENSIONS)
_CCyclicPlot = qtplugin_factory(CCyclicPlot,
                                group=CWidgetBoxGroup.CHARTS,
                                icon=icon('CyclicPlotWidget', file_path=Path(accwidgets.graph.designer.__file__)),
                                extensions=_PLOT_EXTENSIONS)
_CStaticPlot = qtplugin_factory(CStaticPlot,
                                group=CWidgetBoxGroup.CHARTS,
                                icon=icon('StaticPlotWidget', file_path=Path(accwidgets.graph.designer.__file__)),
                                extensions=_PLOT_EXTENSIONS)

# Invisible
_CValueAggregator = qtplugin_factory(CValueAggregator, group=CWidgetBoxGroup.VIRTUAL)


# # Tab Widget plugin
# TODO: Figure out what it's used for and if we need it
# class TabWidgetPlugin(PyDMTabWidgetPlugin):
#     """Qt Designer Plugin for CTabWidget"""
#     TabClass = CTabWidget
#
#     def __init__(self, extensions: Optional[List[RulesExtension]] = None):
#         # Overrides the hardcoded gorup of TabWidgetPlugin to the custom one
#         # This needs to be done via init, because event with the change to PyDMTabWidgetPlugin,
#         # group appeared to be unchanged.
#         super().__init__(extensions=extensions)
#         self._group = WidgetBoxGroup.CONTAINERS
#
#
# TabWidget = TabWidgetPlugin(extensions=_BASE_EXTENSIONS)
#
# # This has to be removed, otherwise it will also appear in Qt Designer
# del PyDMTabWidgetPlugin
