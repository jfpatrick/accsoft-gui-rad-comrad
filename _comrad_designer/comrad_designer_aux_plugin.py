"""
We need original PyDMPlugins to be loaded into Qt Designer for the sake of correct inheritance resolution
but we don't want to include them into Widget Box, therefore, Qt Designer is expected to have customization
that hides this special group
The reason, how this inclusion affects the workflow, have a look at the *.ui file, that includes, e.g. a single CLabel
widget. If PyDMLabel is not included, you will see in the bottom of the file the following structure:
<customwidgets>
 <customwidget>
  <class>CLabel</class>
  <extends>QLabel</extends>
  <header>comrad.widgets.indicators</header>
 </customwidget>
</customwidgets>

This can cause problems, when PyDM specific features are used, e.g. Enums, which will produce something like
PyDMLabel::ENUM_VALUE in *.ui file. When loading such a file, UI loader will crash saying that PyDMLabel C++ class
is not found.
We need to tell it that this class comes from Python. When both PyDMLabel and CLabel are included amongst plugins,
it results in the following structure:
<customwidgets>
 <customwidget>
  <class>CLabel</class>
  <extends>PyDMLabel</extends>
  <header>comrad.widgets.indicators</header>
  </customwidget>
 <customwidget>
  <class>PyDMLabel</class>
  <extends>QLabel</extends>
  <header>pydm.widgets.label</header>
 </customwidget>
</customwidgets>

Information is not lost, and UI loader will correctly resolve symbols.
As a way of hiding these auxiliary widgets from the user, we group them in a specific category that is not displayed
in widget box.
"""

# Do not crash Qt Designer on Ctrl+C
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

# Has to be above first main comrad package import
from _comrad_designer.log_config import setup_logging
setup_logging()

from pydm.widgets import (PyDMLabel, PyDMCheckbox, PyDMPushButton,
                          PyDMRelatedDisplayButton, PyDMShellCommand,
                          PyDMEmbeddedDisplay, PyDMTemplateRepeater, PyDMEnumComboBox, PyDMLineEdit,
                          PyDMSlider, PyDMSpinbox, PyDMByteIndicator,
                          PyDMScaleIndicator)
from pydm.widgets.logdisplay import PyDMLogDisplay
from pydm.widgets.enum_button import PyDMEnumButton
from accwidgets.graph import ScrollingPlotWidget, CyclicPlotWidget, StaticPlotWidget
from accwidgets.property_edit import PropertyEdit
from accwidgets.log_console import LogConsole
from _comrad_designer.utils import qtplugin_factory, CWidgetBoxGroup


# This is a special category name hardcoded into Qt Designer (not by me, but by Qt)
# Category with this name will not appear in the widget box
# In Qt sources you can find it in qttools/src/designer/src/components/widgetbox/widgetboxtreewidget.cpp
# Declared on line 70 and used on lines 613, 630


_PyDMLabel = qtplugin_factory(PyDMLabel, group=CWidgetBoxGroup.HIDDEN)
_PyDMCheckbox = qtplugin_factory(PyDMCheckbox, group=CWidgetBoxGroup.HIDDEN)
_PyDMEnumButton = qtplugin_factory(PyDMEnumButton, group=CWidgetBoxGroup.HIDDEN)
_PyDMPushButton = qtplugin_factory(PyDMPushButton, group=CWidgetBoxGroup.HIDDEN)
_PyDMRelatedDisplayButton = qtplugin_factory(PyDMRelatedDisplayButton, group=CWidgetBoxGroup.HIDDEN)
_PyDMShellCommand = qtplugin_factory(PyDMShellCommand, group=CWidgetBoxGroup.HIDDEN)
# _PyDMWaveformTable = qtplugin_factory(PyDMWaveformTable, group=CWidgetBoxGroup.HIDDEN)
# TODO: Uncomment if CFrame is needed
# _PyDMFrame = qtplugin_factory(PyDMFrame, group=CWidgetBoxGroup.HIDDEN)
_PyDMEmbeddedDisplay = qtplugin_factory(PyDMEmbeddedDisplay, group=CWidgetBoxGroup.HIDDEN)
_PyDMTemplateRepeater = qtplugin_factory(PyDMTemplateRepeater, group=CWidgetBoxGroup.HIDDEN)
_PyDMEnumComboBox = qtplugin_factory(PyDMEnumComboBox, group=CWidgetBoxGroup.HIDDEN)
_PyDMLineEdit = qtplugin_factory(PyDMLineEdit, group=CWidgetBoxGroup.HIDDEN)
_PyDMSlider = qtplugin_factory(PyDMSlider, group=CWidgetBoxGroup.HIDDEN)
_PyDMSpinbox = qtplugin_factory(PyDMSpinbox, group=CWidgetBoxGroup.HIDDEN)
_PyDMByteIndicator = qtplugin_factory(PyDMByteIndicator, group=CWidgetBoxGroup.HIDDEN)
# _PyDMImageView = qtplugin_factory(PyDMImageView, group=CWidgetBoxGroup.HIDDEN)
_PyDMLogDisplay = qtplugin_factory(PyDMLogDisplay, group=CWidgetBoxGroup.HIDDEN)
_PyDMScaleIndicator = qtplugin_factory(PyDMScaleIndicator, group=CWidgetBoxGroup.HIDDEN)
# _PyDMTabWidget = qtplugin_factory(PyDMTabWidget, group=CWidgetBoxGroup.HIDDEN)

_AccScrollingPlot = qtplugin_factory(ScrollingPlotWidget, group=CWidgetBoxGroup.HIDDEN)
_AccCyclicPlot = qtplugin_factory(CyclicPlotWidget, group=CWidgetBoxGroup.HIDDEN)
_AccStaticPlot = qtplugin_factory(StaticPlotWidget, group=CWidgetBoxGroup.HIDDEN)
_PropertyEdit = qtplugin_factory(PropertyEdit, group=CWidgetBoxGroup.HIDDEN)
_LogConsole = qtplugin_factory(LogConsole, group=CWidgetBoxGroup.HIDDEN)
