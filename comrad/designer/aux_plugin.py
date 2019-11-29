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
  <header>comrad.qt.pydm_widgets</header>
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
  <header>comrad.qt.pydm_widgets</header>
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
from comrad.qt.pydm_widgets import (PyDMLabel, PyDMCheckbox, PyDMEnumButton, PyDMPushButton, PyDMRelatedDisplayButton,
                                    PyDMShellCommand, PyDMWaveformTable, PyDMEmbeddedDisplay,
                                    PyDMTemplateRepeater, PyDMEnumComboBox, PyDMLineEdit, PyDMSlider, PyDMSpinbox,
                                    PyDMByteIndicator, PyDMImageView, PyDMLogDisplay, PyDMScaleIndicator)
from comrad.designer.utils import qtplugin_factory


# This is a special category name hardcoded into Qt Designer (not by me, but by Qt)
# Category with this name will not appear in the widget box
# In Qt sources you can find it in qttools/src/designer/src/components/widgetbox/widgetboxtreewidget.cpp
# Declared on line 70 and used on lines 613, 630
_COMRAD_GROUP_HIDDEN_ITEMS = '[invisible]'


# pylint: disable=invalid-name
PyDMLabel_ = qtplugin_factory(PyDMLabel, group=_COMRAD_GROUP_HIDDEN_ITEMS)
PyDMCheckbox_ = qtplugin_factory(PyDMCheckbox, group=_COMRAD_GROUP_HIDDEN_ITEMS)
PyDMEnumButton_ = qtplugin_factory(PyDMEnumButton, group=_COMRAD_GROUP_HIDDEN_ITEMS)
PyDMPushButton_ = qtplugin_factory(PyDMPushButton, group=_COMRAD_GROUP_HIDDEN_ITEMS)
PyDMRelatedDisplayButton_ = qtplugin_factory(PyDMRelatedDisplayButton, group=_COMRAD_GROUP_HIDDEN_ITEMS)
PyDMShellCommand_ = qtplugin_factory(PyDMShellCommand, group=_COMRAD_GROUP_HIDDEN_ITEMS)
PyDMWaveformTable_ = qtplugin_factory(PyDMWaveformTable, group=_COMRAD_GROUP_HIDDEN_ITEMS)
# TODO: Uncomment if CFrame is needed
# PyDMFrame_ = qtplugin_factory(PyDMFrame, group=_COMRAD_GROUP_HIDDEN_ITEMS)
PyDMEmbeddedDisplay_ = qtplugin_factory(PyDMEmbeddedDisplay, group=_COMRAD_GROUP_HIDDEN_ITEMS)
PyDMTemplateRepeater_ = qtplugin_factory(PyDMTemplateRepeater, group=_COMRAD_GROUP_HIDDEN_ITEMS)
PyDMEnumComboBox_ = qtplugin_factory(PyDMEnumComboBox, group=_COMRAD_GROUP_HIDDEN_ITEMS)
PyDMLineEdit_ = qtplugin_factory(PyDMLineEdit, group=_COMRAD_GROUP_HIDDEN_ITEMS)
PyDMSlider_ = qtplugin_factory(PyDMSlider, group=_COMRAD_GROUP_HIDDEN_ITEMS)
PyDMSpinbox_ = qtplugin_factory(PyDMSpinbox, group=_COMRAD_GROUP_HIDDEN_ITEMS)
PyDMByteIndicator_ = qtplugin_factory(PyDMByteIndicator, group=_COMRAD_GROUP_HIDDEN_ITEMS)
PyDMImageView_ = qtplugin_factory(PyDMImageView, group=_COMRAD_GROUP_HIDDEN_ITEMS)
PyDMLogDisplay_ = qtplugin_factory(PyDMLogDisplay, group=_COMRAD_GROUP_HIDDEN_ITEMS)
PyDMScaleIndicator_ = qtplugin_factory(PyDMScaleIndicator, group=_COMRAD_GROUP_HIDDEN_ITEMS)
# PyDMTabWidget_ = qtplugin_factory(PyDMTabWidget, group=_COMRAD_GROUP_HIDDEN_ITEMS)
