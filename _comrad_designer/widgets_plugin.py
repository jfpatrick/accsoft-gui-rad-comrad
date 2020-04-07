"""
Plugins for Qt Designer that are visible ComRAD widgets.
"""

# Do not crash Qt Designer on Ctrl+C
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

import functools
import accwidgets.property_edit.designer
import accwidgets.led.designer
from pathlib import Path
from typing import List
from qtpy.QtWidgets import QAction, QWidget

# Has to be above first main comrad package import
from _comrad_designer.log_config import setup_logging
setup_logging()

# from pydm.widgets.tab_bar_qtplugin import TabWidgetPlugin as PyDMTabWidgetPlugin
from pydm.widgets.qtplugin_extensions import PyDMExtension
from accwidgets.property_edit.designer.designer_extensions import PropertyFieldExtension
from comrad import (CScrollingPlot, CCyclicPlot, CStaticPlot, CValueAggregator, CCommandButton, CScaleIndicator, CLogDisplay,
                    CEnumComboBox, CSlider, CSpinBox, CLabel, CByteIndicator, CLineEdit, CTemplateRepeater,
                    CEmbeddedDisplay, CShellCommand, CRelatedDisplayButton, CPushButton, CEnumButton, CCheckBox,
                    CPropertyEdit, CLed, CContextFrame)
from comrad.icons import icon
from _comrad_designer.utils import qtplugin_factory
from _comrad_designer.rules_editor import RulesEditor
from _comrad_designer.graphs import CPlottingItemEditorExtension, CLayerEditorExtension


class _RulesExtension(PyDMExtension):

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


_load_icon = functools.partial(icon, file_path=__file__)


_BASE_EXTENSIONS = [_RulesExtension]
_PLOT_EXTENSIONS = [CPlottingItemEditorExtension, CLayerEditorExtension]


# Currently the groups are made so that new widgets blend into the standard PyQt widgets
_COMRAD_GROUP_CONTAINER = 'Containers'  # 'ComRAD Container Widgets'
_COMRAD_GROUP_DISPLAY = 'Display Widgets'  # 'ComRAD Display Widgets'
_COMRAD_GROUP_INPUT = 'Input Widgets'  # 'ComRAD Input Widgets'
_COMRAD_GROUP_PLOT = 'Charts'  # 'ComRAD Plot Widgets'
_COMRAD_GROUP_BUTTONS = 'Buttons'
_COMRAD_GROUP_ITEM_VIEWS = 'Item Widgets (Item-Based)'
_COMRAD_GROUP_VIRTUAL = 'Invisible Widgets'


# Buttons
_CCheckbox = qtplugin_factory(CCheckBox, group=_COMRAD_GROUP_BUTTONS, icon=_load_icon('checkbox'), extensions=_BASE_EXTENSIONS)


_CEnumButton = qtplugin_factory(CEnumButton, group=_COMRAD_GROUP_BUTTONS, icon=_load_icon('enum_btn'), extensions=_BASE_EXTENSIONS)
_CPushButton = qtplugin_factory(CPushButton, group=_COMRAD_GROUP_BUTTONS, icon=_load_icon('push_btn'), extensions=_BASE_EXTENSIONS)
_CCommandButton = qtplugin_factory(CCommandButton, group=_COMRAD_GROUP_BUTTONS, icon=_load_icon('cmd_btn'))
_CRelatedDisplayButton = qtplugin_factory(CRelatedDisplayButton, group=_COMRAD_GROUP_BUTTONS, icon=_load_icon('related_display'))
_CShellCommand = qtplugin_factory(CShellCommand, group=_COMRAD_GROUP_BUTTONS, icon=_load_icon('shell_cmd'))
# _CToggleButton = qtplugin_factory(CToggleButton, group=_COMRAD_GROUP_BUTTONS, icon=load_icon('toggle'), extensions=_BASE_EXTENSIONS)

# Item Widgets
# TODO: Uncomment when useful
# _CWaveformTable = qtplugin_factory(CWaveFormTable, group=_COMRAD_GROUP_ITEM_VIEWS, icon=_load_icon('waveform_table'), extensions=_BASE_EXTENSIONS)

# Containers
# TODO: What is CFrame useful for?
# _CFrame = qtplugin_factory(CFrame, group=_COMRAD_GROUP_CONTAINER, icon=load_icon('frame'), is_container=True, extensions=_BASE_EXTENSIONS)
_CEmbeddedDisplay = qtplugin_factory(CEmbeddedDisplay, group=_COMRAD_GROUP_CONTAINER, icon=_load_icon('embedded_display'))
_CTemplateRepeater = qtplugin_factory(CTemplateRepeater, group=_COMRAD_GROUP_CONTAINER, icon=_load_icon('template_repeater'))
_CContextFrame = qtplugin_factory(CContextFrame, group=_COMRAD_GROUP_CONTAINER, icon=_load_icon('context_frame'), is_container=True)

# Input Widgets
_CEnumComboBox = qtplugin_factory(CEnumComboBox, group=_COMRAD_GROUP_INPUT, icon=_load_icon('combobox'), extensions=_BASE_EXTENSIONS)
_CLineEdit = qtplugin_factory(CLineEdit, group=_COMRAD_GROUP_INPUT, icon=_load_icon('line_edit'), extensions=_BASE_EXTENSIONS)
_CSlider = qtplugin_factory(CSlider, group=_COMRAD_GROUP_INPUT, icon=_load_icon('slider'), extensions=_BASE_EXTENSIONS)
_CSpinbox = qtplugin_factory(CSpinBox, group=_COMRAD_GROUP_INPUT, icon=_load_icon('spinbox'), extensions=_BASE_EXTENSIONS)
_CPropertyEdit = qtplugin_factory(CPropertyEdit,
                                  group=_COMRAD_GROUP_INPUT,
                                  icon=icon('PropertyEdit', file_path=Path(accwidgets.property_edit.designer.__file__)),
                                  extensions=[PropertyFieldExtension, *_BASE_EXTENSIONS])

# Display Widgets
_CLabel = qtplugin_factory(CLabel, group=_COMRAD_GROUP_DISPLAY, icon=_load_icon('label'), extensions=_BASE_EXTENSIONS)
_CByteIndicator = qtplugin_factory(CByteIndicator, group=_COMRAD_GROUP_DISPLAY, icon=_load_icon('byte_indicator'), extensions=_BASE_EXTENSIONS)
# TODO: Uncomment when useful
# _CImageView = qtplugin_factory(CImageView, group=_COMRAD_GROUP_DISPLAY, icon=_load_icon('image_view'), extensions=_BASE_EXTENSIONS)
_CLogDisplay = qtplugin_factory(CLogDisplay, group=_COMRAD_GROUP_DISPLAY, icon=_load_icon('log_viewer'), extensions=_BASE_EXTENSIONS)
_CScaleIndicator = qtplugin_factory(CScaleIndicator, group=_COMRAD_GROUP_DISPLAY, icon=_load_icon('scale_indicator'), extensions=_BASE_EXTENSIONS)
_CEnumLed = qtplugin_factory(CLed, group=_COMRAD_GROUP_DISPLAY, icon=icon('Led', file_path=Path(accwidgets.led.designer.__file__)), extensions=_BASE_EXTENSIONS)

# Charts
_CScrollingPlot = qtplugin_factory(CScrollingPlot, group=_COMRAD_GROUP_PLOT, icon=_load_icon('graph_scrolling_plot'), extensions=_PLOT_EXTENSIONS)
_CCyclicPlot = qtplugin_factory(CCyclicPlot, group=_COMRAD_GROUP_PLOT, icon=_load_icon('graph_sliding_plot'), extensions=_PLOT_EXTENSIONS)
_CStaticPlot = qtplugin_factory(CStaticPlot, group=_COMRAD_GROUP_PLOT, icon=_load_icon('graph_static_plot'), extensions=_PLOT_EXTENSIONS)

# Invisible
_CValueAggregator = qtplugin_factory(CValueAggregator, group=_COMRAD_GROUP_VIRTUAL, icon=_load_icon('calc'))


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
#         self._group = _COMRAD_GROUP_CONTAINER
#
#     def icon(self):
#         return load_icon('tab_widget')
#
#
# TabWidget = TabWidgetPlugin(extensions=_BASE_EXTENSIONS)
#
# # This has to be removed, otherwise it will also appear in Qt Designer
# del PyDMTabWidgetPlugin
