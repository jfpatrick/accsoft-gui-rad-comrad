"""
Plugins for Qt Designer that are visible ComRAD widgets.
"""
import functools
from qtpy.QtWidgets import QAction
# from pydm.widgets.tab_bar_qtplugin import TabWidgetPlugin as PyDMTabWidgetPlugin
from pydm.widgets.qtplugin_extensions import RulesExtension, PyDMExtension
from comrad.utils import icon
from comrad.designer.utils import qtplugin_factory
from comrad.designer.rules_editor import NewRulesEditor as RulesEditor
from comrad.qt.cern_widgets.graph import CScrollingPlot, CSlidingPlot, CPlottingItemEditorExtension
from comrad.qt.widgets import CValueAggregator, CCommandButton
from comrad.qt.pydm_widgets import (CScaleIndicator, CLogDisplay, CImageView, CEnumComboBox, CSlider,
                                    CSpinBox, CLabel, CByteIndicator, CLineEdit, CTemplateRepeater,
                                    CEmbeddedDisplay, CShellCommand, CRelatedDisplayButton, CPushButton, CEnumButton,
                                    CWaveFormTable, CCheckBox)
import comrad


class RulesExtension(PyDMExtension):
    def __init__(self, widget):
        super(RulesExtension, self).__init__(widget)
        self.widget = widget
        self.edit_rules_action = QAction("Edit Rules...", self.widget)
        self.edit_rules_action.triggered.connect(self.edit_rules)

    def edit_rules(self, state):
        edit_rules_dialog = RulesEditor(self.widget, parent=None)
        edit_rules_dialog.exec_()

    def actions(self):
        return [self.edit_rules_action]


load_icon = functools.partial(icon, file_path=__file__)  # pylint: disable=invalid-name


print('\n\n'
      ' ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n'
      ' *** Welcome to ComRAD Designer! ***\n'
      ' ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n'
      f' ComRAD widgets version: {comrad.__version__}\n'
      f' Support: {comrad.__author__}\n'
      ' Project page: https://wikis.cern.ch/display/ACCPY/Rapid+Application+Development\n'
      '\n')

_BASE_EXTENSIONS = [RulesExtension]
_PLOT_EXTENSIONS = [CPlottingItemEditorExtension]

# Currently the groups are made so that new widgets blend into the standard PyQt widgets
_COMRAD_GROUP_CONTAINER = 'Containers'  # 'ComRAD Container Widgets'
_COMRAD_GROUP_DISPLAY = 'Display Widgets'  # 'ComRAD Display Widgets'
_COMRAD_GROUP_INPUT = 'Input Widgets'  # 'ComRAD Input Widgets'
_COMRAD_GROUP_PLOT = 'Charts'  # 'ComRAD Plot Widgets'
_COMRAD_GROUP_BUTTONS = 'Buttons'
_COMRAD_GROUP_ITEM_VIEWS = 'Item Widgets (Item-Based)'
_COMRAD_GROUP_VIRTUAL = 'Invisible Widgets'


# Buttons
Checkbox = qtplugin_factory(CCheckBox, group=_COMRAD_GROUP_BUTTONS, icon=load_icon('checkbox'), extensions=_BASE_EXTENSIONS)


EnumButton = qtplugin_factory(CEnumButton, group=_COMRAD_GROUP_BUTTONS, icon=load_icon('enum_btn'), extensions=_BASE_EXTENSIONS)
PushButton = qtplugin_factory(CPushButton, group=_COMRAD_GROUP_BUTTONS, icon=load_icon('push_btn'), extensions=_BASE_EXTENSIONS)
CommandButton = qtplugin_factory(CCommandButton, group=_COMRAD_GROUP_BUTTONS, icon=load_icon('push_btn'))
RelatedDisplayButton = qtplugin_factory(CRelatedDisplayButton, group=_COMRAD_GROUP_BUTTONS, icon=load_icon('related_display'))
ShellCommand = qtplugin_factory(CShellCommand, group=_COMRAD_GROUP_BUTTONS, icon=load_icon('shell_cmd'))
# ToggleButton = qtplugin_factory(CToggleButton, group=_COMRAD_GROUP_BUTTONS, icon=load_icon('toggle'), extensions=_BASE_EXTENSIONS)

# Item Widgets
WaveformTable = qtplugin_factory(CWaveFormTable, group=_COMRAD_GROUP_ITEM_VIEWS, icon=load_icon('waveform_table'), extensions=_BASE_EXTENSIONS)

# Containers
# TODO: What is CFrame useful for?
# Frame = qtplugin_factory(CFrame, group=_COMRAD_GROUP_CONTAINER, icon=load_icon('frame'), is_container=True, extensions=_BASE_EXTENSIONS)
EmbeddedDisplay = qtplugin_factory(CEmbeddedDisplay, group=_COMRAD_GROUP_CONTAINER, icon=load_icon('embedded_display'))
TemplateRepeater = qtplugin_factory(CTemplateRepeater, group=_COMRAD_GROUP_CONTAINER, icon=load_icon('template_repeater'))

# Input Widgets
EnumComboBox = qtplugin_factory(CEnumComboBox, group=_COMRAD_GROUP_INPUT, icon=load_icon('combobox'), extensions=_BASE_EXTENSIONS)
LineEdit = qtplugin_factory(CLineEdit, group=_COMRAD_GROUP_INPUT, icon=load_icon('line_edit'), extensions=_BASE_EXTENSIONS)
Slider = qtplugin_factory(CSlider, group=_COMRAD_GROUP_INPUT, icon=load_icon('slider'), extensions=_BASE_EXTENSIONS)
Spinbox = qtplugin_factory(CSpinBox, group=_COMRAD_GROUP_INPUT, icon=load_icon('spinbox'), extensions=_BASE_EXTENSIONS)

# Display Widgets
Label = qtplugin_factory(CLabel, group=_COMRAD_GROUP_DISPLAY, icon=load_icon('label'), extensions=_BASE_EXTENSIONS)
ByteIndicator = qtplugin_factory(CByteIndicator, group=_COMRAD_GROUP_DISPLAY, icon=load_icon('byte_indicator'), extensions=_BASE_EXTENSIONS)
ImageView = qtplugin_factory(CImageView, group=_COMRAD_GROUP_DISPLAY, icon=load_icon('image_view'), extensions=_BASE_EXTENSIONS)
LogDisplay = qtplugin_factory(CLogDisplay, group=_COMRAD_GROUP_DISPLAY, icon=load_icon('log_viewer'), extensions=_BASE_EXTENSIONS)
ScaleIndicator = qtplugin_factory(CScaleIndicator, group=_COMRAD_GROUP_DISPLAY, icon=load_icon('scale_indicator'), extensions=_BASE_EXTENSIONS)

# Charts
ScrollingPlot = qtplugin_factory(CScrollingPlot, group=_COMRAD_GROUP_PLOT, icon=load_icon('graph_scrolling_plot'), extensions=_PLOT_EXTENSIONS)
SlidingPlot = qtplugin_factory(CSlidingPlot, group=_COMRAD_GROUP_PLOT, icon=load_icon('graph_sliding_plot'), extensions=_PLOT_EXTENSIONS)

# Invisible
ValueAggregator = qtplugin_factory(CValueAggregator, group=_COMRAD_GROUP_VIRTUAL, icon=load_icon('calc'))


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
# TabWidget = TabWidgetPlugin(extensions=_BASE_EXTENSIONS)  # pylint: disable=invalid-name
#
# # This has to be removed, otherwise it will also appear in Qt Designer
# del PyDMTabWidgetPlugin
