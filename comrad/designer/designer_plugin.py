print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n'
      '*** Welcome to ComRAD Designer! ***\n'
      '~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n'
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
_CERN_GROUP_CONTAINER = 'Containers' #'ComRAD Container Widgets'
_CERN_GROUP_DISPLAY = 'Display Widgets' #'ComRAD Display Widgets'
_CERN_GROUP_INPUT = 'Input Widgets' #'ComRAD Input Widgets'
_CERN_GROUP_PLOT = 'Charts' #'ComRAD Plot Widgets'
_CERN_GROUP_BUTTONS = 'Buttons'
_CERN_GROUP_ITEM_VIEWS = 'Item Widgets (Item-Based)'


def icon(name: str) -> QIcon:
    curr_dir = os.path.abspath(os.path.dirname(__file__))
    icon_path = os.path.join(curr_dir, 'icons', f'{name}.ico')

    if not os.path.isfile(icon_path):
        print(f'Warning: Icon "{name}" cannot be found at {str(icon_path)}')
    px = QPixmap(icon_path)
    return QIcon(px)


# Buttons
Checkbox = qtplugin_factory(CCheckBox, group=_CERN_GROUP_BUTTONS, icon=icon('checkbox'), extensions=_BASE_EXTENSIONS)
EnumButton = qtplugin_factory(CEnumButton, group=_CERN_GROUP_BUTTONS, icon=icon('enum_btn'), extensions=_BASE_EXTENSIONS)
PushButton = qtplugin_factory(CPushButton, group=_CERN_GROUP_BUTTONS, icon=icon('push_btn'), extensions=_BASE_EXTENSIONS)
RelatedDisplayButton = qtplugin_factory(CRelatedDisplayButton, group=_CERN_GROUP_BUTTONS, icon=icon('related_display'), extensions=_BASE_EXTENSIONS)
ShellCommand = qtplugin_factory(CShellCommand, group=_CERN_GROUP_BUTTONS, icon=icon('shell_cmd'), extensions=_BASE_EXTENSIONS)

# Item Widgets
WaveformTable = qtplugin_factory(CWaveFormTable, group=_CERN_GROUP_ITEM_VIEWS, icon=icon('waveform_table'), extensions=_BASE_EXTENSIONS)

# Containers
EmbeddedDisplay = qtplugin_factory(CEmbeddedDisplay, group=_CERN_GROUP_CONTAINER, icon=icon('embedded_display'), extensions=_BASE_EXTENSIONS)
TemplateRepeater = qtplugin_factory(CTemplateRepeater, group=_CERN_GROUP_CONTAINER, icon=icon('template_repeater'), extensions=_BASE_EXTENSIONS)

# Input Widgets
EnumComboBox = qtplugin_factory(CEnumComboBox, group=_CERN_GROUP_INPUT, icon=icon('combobox'), extensions=_BASE_EXTENSIONS)
LineEdit = qtplugin_factory(CLineEdit, group=_CERN_GROUP_INPUT, icon=icon('line_edit'), extensions=_BASE_EXTENSIONS)
Slider = qtplugin_factory(CSlider, group=_CERN_GROUP_INPUT, icon=icon('slider'), extensions=_BASE_EXTENSIONS)
Spinbox = qtplugin_factory(CSpinBox, group=_CERN_GROUP_INPUT, icon=icon('spinbox'), extensions=_BASE_EXTENSIONS)

# Display Widgets
Label = qtplugin_factory(CLabel, group=_CERN_GROUP_DISPLAY, icon=icon('label'), extensions=_BASE_EXTENSIONS)
ByteIndicator = qtplugin_factory(CByteIndicator, group=_CERN_GROUP_DISPLAY, icon=icon('byte_indicator'), extensions=_BASE_EXTENSIONS)
ImageView = qtplugin_factory(CImageView, group=_CERN_GROUP_DISPLAY, icon=icon('image_view'), extensions=_BASE_EXTENSIONS)
LogDisplay = qtplugin_factory(CLogDisplay, group=_CERN_GROUP_DISPLAY, icon=icon('log_viewer'), extensions=_BASE_EXTENSIONS)
ScaleIndicator = qtplugin_factory(CScaleIndicator, group=_CERN_GROUP_DISPLAY, icon=icon('scale_indicator'), extensions=_BASE_EXTENSIONS)

# Charts
TimePlot = qtplugin_factory(CTimePlot, group=_CERN_GROUP_PLOT, icon=icon('time_plot'), extensions=[TimeCurveEditorExtension, RulesExtension])
WaveformPlot = qtplugin_factory(CWaveFormPlot, group=_CERN_GROUP_PLOT, icon=icon('waveform_plot'), extensions=[WaveformCurveEditorExtension,
                                                                                   RulesExtension])
ScatterPlot = qtplugin_factory(CScatterPlot, group=_CERN_GROUP_PLOT, icon=icon('scatter_plot'), extensions=[ScatterCurveEditorExtension,
                                                                                 RulesExtension])

# Tab Widget plugin
class TabWidgetPlugin(PyDMTabWidgetPlugin):
    """Qt Designer Plugin for CTabWidget"""
    TabClass = CTabWidget

    def __init__(self, extensions: List[RulesExtension] = None):
        # Overrides the hardcoded gorup of TabWidgetPlugin to the custom one
        # This needs to be done via init, because event with the change to PyDMTabWidgetPlugin,
        # group appeared to be unchanged.
        super().__init__(extensions=extensions)
        self._group = _CERN_GROUP_CONTAINER

    def icon(self):
        return icon('tab_widget')

TabWidget = TabWidgetPlugin(extensions=_BASE_EXTENSIONS)

# This has to be removed, otherwise it will also appear in Qt Designer
del PyDMTabWidgetPlugin