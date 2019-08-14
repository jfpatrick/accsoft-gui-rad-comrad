import comrad

print('\n\n'
      ' ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n'
      ' *** Welcome to ComRAD Designer! ***\n'
      ' ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n'
      f' ComRAD widgets version: {comrad.__version__}\n'
      f' Support: {comrad.__author__}\n'
      ' Project page: https://wikis.cern.ch/display/ACCPY/Rapid+Application+Development\n'
      '\n')

from typing import List
from qtpy.QtGui import QIcon, QPixmap
from comrad.qt.cern_widgets import *
from comrad.qt.pydm_widgets import *
import os

from pydm.widgets.qtplugin_extensions import (RulesExtension, WaveformCurveEditorExtension,
                                              TimeCurveEditorExtension,
                                              ScatterCurveEditorExtension)
from pydm.widgets.tab_bar_qtplugin import TabWidgetPlugin as PyDMTabWidgetPlugin
from comrad.designer.utils import qtplugin_factory

_BASE_EXTENSIONS = [RulesExtension]

# Currently the groups are made so that new widgets blend into the standard PyQt widgets
_COMRAD_GROUP_CONTAINER = 'Containers' #'ComRAD Container Widgets'
_COMRAD_GROUP_DISPLAY = 'Display Widgets' #'ComRAD Display Widgets'
_COMRAD_GROUP_INPUT = 'Input Widgets' #'ComRAD Input Widgets'
_COMRAD_GROUP_PLOT = 'Charts' #'ComRAD Plot Widgets'
_COMRAD_GROUP_BUTTONS = 'Buttons'
_COMRAD_GROUP_ITEM_VIEWS = 'Item Widgets (Item-Based)'
_COMRAD_GROUP_VIRTUAL = 'Invisible Widgets'


def icon(name: str) -> QIcon:
    curr_dir = os.path.abspath(os.path.dirname(__file__))
    icon_path = os.path.join(curr_dir, 'icons', f'{name}.ico')

    if not os.path.isfile(icon_path):
        print(f'Warning: Icon "{name}" cannot be found at {str(icon_path)}')
    px = QPixmap(icon_path)
    return QIcon(px)


# Buttons
Checkbox = qtplugin_factory(CCheckBox, group=_COMRAD_GROUP_BUTTONS, icon=icon('checkbox'), extensions=_BASE_EXTENSIONS, on_widget_create=lambda w: w.setText('RAD CheckBox'))

def enum_btn_init(w: CEnumButton):
    w.items = ['RAD Item 1', 'RAD Item 2', 'RAD Item ...']

def toggle_btn_init(w: CToggleButton):
    w.setUncheckedText('RAD Toggle Released')
    w.setCheckedText('RAD Toggle Pressed')

EnumButton = qtplugin_factory(CEnumButton, group=_COMRAD_GROUP_BUTTONS, icon=icon('enum_btn'), extensions=_BASE_EXTENSIONS, on_widget_create=enum_btn_init)
PushButton = qtplugin_factory(CPushButton, group=_COMRAD_GROUP_BUTTONS, icon=icon('push_btn'), extensions=_BASE_EXTENSIONS, on_widget_create=lambda w: w.setText('RAD PushButton'))
RelatedDisplayButton = qtplugin_factory(CRelatedDisplayButton, group=_COMRAD_GROUP_BUTTONS, icon=icon('related_display'), extensions=_BASE_EXTENSIONS)
ShellCommand = qtplugin_factory(CShellCommand, group=_COMRAD_GROUP_BUTTONS, icon=icon('shell_cmd'), extensions=_BASE_EXTENSIONS)
ToggleButton = qtplugin_factory(CToggleButton, group=_COMRAD_GROUP_BUTTONS, icon=icon('toggle'), extensions=_BASE_EXTENSIONS, on_widget_create=toggle_btn_init)

# Item Widgets
WaveformTable = qtplugin_factory(CWaveFormTable, group=_COMRAD_GROUP_ITEM_VIEWS, icon=icon('waveform_table'), extensions=_BASE_EXTENSIONS)

# Containers
Frame = qtplugin_factory(CFrame, group=_COMRAD_GROUP_CONTAINER, icon=icon('frame'), is_container=True, extensions=_BASE_EXTENSIONS)
EmbeddedDisplay = qtplugin_factory(CEmbeddedDisplay, group=_COMRAD_GROUP_CONTAINER, icon=icon('embedded_display'), extensions=_BASE_EXTENSIONS)
TemplateRepeater = qtplugin_factory(CTemplateRepeater, group=_COMRAD_GROUP_CONTAINER, icon=icon('template_repeater'), extensions=_BASE_EXTENSIONS)

# Input Widgets
EnumComboBox = qtplugin_factory(CEnumComboBox, group=_COMRAD_GROUP_INPUT, icon=icon('combobox'), extensions=_BASE_EXTENSIONS)
LineEdit = qtplugin_factory(CLineEdit, group=_COMRAD_GROUP_INPUT, icon=icon('line_edit'), extensions=_BASE_EXTENSIONS)
Slider = qtplugin_factory(CSlider, group=_COMRAD_GROUP_INPUT, icon=icon('slider'), extensions=_BASE_EXTENSIONS)
Spinbox = qtplugin_factory(CSpinBox, group=_COMRAD_GROUP_INPUT, icon=icon('spinbox'), extensions=_BASE_EXTENSIONS)

# Display Widgets
Label = qtplugin_factory(CLabel, group=_COMRAD_GROUP_DISPLAY, icon=icon('label'), extensions=_BASE_EXTENSIONS, on_widget_create=lambda w: w.setText('RAD TextLabel'))
ByteIndicator = qtplugin_factory(CByteIndicator, group=_COMRAD_GROUP_DISPLAY, icon=icon('byte_indicator'), extensions=_BASE_EXTENSIONS)
ImageView = qtplugin_factory(CImageView, group=_COMRAD_GROUP_DISPLAY, icon=icon('image_view'), extensions=_BASE_EXTENSIONS)
LogDisplay = qtplugin_factory(CLogDisplay, group=_COMRAD_GROUP_DISPLAY, icon=icon('log_viewer'), extensions=_BASE_EXTENSIONS)
ScaleIndicator = qtplugin_factory(CScaleIndicator, group=_COMRAD_GROUP_DISPLAY, icon=icon('scale_indicator'), extensions=_BASE_EXTENSIONS)

# Charts
TimePlot = qtplugin_factory(CTimePlot, group=_COMRAD_GROUP_PLOT, icon=icon('time_plot'), extensions=[TimeCurveEditorExtension, RulesExtension])
WaveformPlot = qtplugin_factory(CWaveFormPlot, group=_COMRAD_GROUP_PLOT, icon=icon('waveform_plot'), extensions=[WaveformCurveEditorExtension,
                                                                                   RulesExtension])
ScatterPlot = qtplugin_factory(CScatterPlot, group=_COMRAD_GROUP_PLOT, icon=icon('scatter_plot'), extensions=[ScatterCurveEditorExtension,
                                                                                 RulesExtension])
AccPlot = qtplugin_factory(CAccPlot, group=_COMRAD_GROUP_PLOT, icon=icon('scatter_plot'), extensions=_BASE_EXTENSIONS)

# Invisible
ValueAggregator = qtplugin_factory(CValueAggregator, group=_COMRAD_GROUP_VIRTUAL, icon=icon('calc'))

# Tab Widget plugin
class TabWidgetPlugin(PyDMTabWidgetPlugin):
    """Qt Designer Plugin for CTabWidget"""
    TabClass = CTabWidget

    def __init__(self, extensions: List[RulesExtension] = None):
        # Overrides the hardcoded gorup of TabWidgetPlugin to the custom one
        # This needs to be done via init, because event with the change to PyDMTabWidgetPlugin,
        # group appeared to be unchanged.
        super().__init__(extensions=extensions)
        self._group = _COMRAD_GROUP_CONTAINER

    def icon(self):
        return icon('tab_widget')

TabWidget = TabWidgetPlugin(extensions=_BASE_EXTENSIONS)

# This has to be removed, otherwise it will also appear in Qt Designer
del PyDMTabWidgetPlugin
