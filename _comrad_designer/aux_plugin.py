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
from _comrad_designer.logging import setup_logging
setup_logging()

from pydm.widgets import (PyDMLabel, PyDMCheckbox, PyDMPushButton,
                          PyDMRelatedDisplayButton, PyDMShellCommand,
                          PyDMEmbeddedDisplay, PyDMTemplateRepeater, PyDMEnumComboBox, PyDMLineEdit,
                          PyDMSlider, PyDMSpinbox, PyDMByteIndicator,
                          PyDMScaleIndicator)
from pydm.widgets.logdisplay import PyDMLogDisplay
from pydm.widgets.enum_button import PyDMEnumButton
from accwidgets.graph import ScrollingPlotWidget, CyclicPlotWidget
from _comrad_designer.utils import qtplugin_factory


# This is a special category name hardcoded into Qt Designer (not by me, but by Qt)
# Category with this name will not appear in the widget box
# In Qt sources you can find it in qttools/src/designer/src/components/widgetbox/widgetboxtreewidget.cpp
# Declared on line 70 and used on lines 613, 630
_COMRAD_GROUP_HIDDEN_ITEMS = '[invisible]'


_PyDMLabel = qtplugin_factory(PyDMLabel, group=_COMRAD_GROUP_HIDDEN_ITEMS)
_PyDMCheckbox = qtplugin_factory(PyDMCheckbox, group=_COMRAD_GROUP_HIDDEN_ITEMS)
_PyDMEnumButton = qtplugin_factory(PyDMEnumButton, group=_COMRAD_GROUP_HIDDEN_ITEMS)
_PyDMPushButton = qtplugin_factory(PyDMPushButton, group=_COMRAD_GROUP_HIDDEN_ITEMS)
_PyDMRelatedDisplayButton = qtplugin_factory(PyDMRelatedDisplayButton, group=_COMRAD_GROUP_HIDDEN_ITEMS)
_PyDMShellCommand = qtplugin_factory(PyDMShellCommand, group=_COMRAD_GROUP_HIDDEN_ITEMS)
# _PyDMWaveformTable = qtplugin_factory(PyDMWaveformTable, group=_COMRAD_GROUP_HIDDEN_ITEMS)
# TODO: Uncomment if CFrame is needed
# _PyDMFrame = qtplugin_factory(PyDMFrame, group=_COMRAD_GROUP_HIDDEN_ITEMS)
_PyDMEmbeddedDisplay = qtplugin_factory(PyDMEmbeddedDisplay, group=_COMRAD_GROUP_HIDDEN_ITEMS)
_PyDMTemplateRepeater = qtplugin_factory(PyDMTemplateRepeater, group=_COMRAD_GROUP_HIDDEN_ITEMS)
_PyDMEnumComboBox = qtplugin_factory(PyDMEnumComboBox, group=_COMRAD_GROUP_HIDDEN_ITEMS)
_PyDMLineEdit = qtplugin_factory(PyDMLineEdit, group=_COMRAD_GROUP_HIDDEN_ITEMS)
_PyDMSlider = qtplugin_factory(PyDMSlider, group=_COMRAD_GROUP_HIDDEN_ITEMS)
_PyDMSpinbox = qtplugin_factory(PyDMSpinbox, group=_COMRAD_GROUP_HIDDEN_ITEMS)
_PyDMByteIndicator = qtplugin_factory(PyDMByteIndicator, group=_COMRAD_GROUP_HIDDEN_ITEMS)
# _PyDMImageView = qtplugin_factory(PyDMImageView, group=_COMRAD_GROUP_HIDDEN_ITEMS)
_PyDMLogDisplay = qtplugin_factory(PyDMLogDisplay, group=_COMRAD_GROUP_HIDDEN_ITEMS)
_PyDMScaleIndicator = qtplugin_factory(PyDMScaleIndicator, group=_COMRAD_GROUP_HIDDEN_ITEMS)
# _PyDMTabWidget = qtplugin_factory(PyDMTabWidget, group=_COMRAD_GROUP_HIDDEN_ITEMS)

_AccScrollingPlot = qtplugin_factory(ScrollingPlotWidget, group=_COMRAD_GROUP_HIDDEN_ITEMS)
_AccCyclicPlot = qtplugin_factory(CyclicPlotWidget, group=_COMRAD_GROUP_HIDDEN_ITEMS)
