# This file provides overriding of the standard PyDM classes in order to bring them to the same naming
# convention as native ComRAD widgets. This is both useful for consistency in Qt Designer widget list
# and when instantiating them from code.

from pydm.widgets.waveformtable import PyDMWaveformTable
from pydm.widgets.scale import PyDMScaleIndicator
from pydm.widgets.timeplot import PyDMTimePlot
from pydm.widgets.waveformplot import PyDMWaveformPlot
from pydm.widgets.scatterplot import PyDMScatterPlot
from pydm.widgets.template_repeater import PyDMTemplateRepeater
from pydm.widgets.image import PyDMImageView
from pydm.widgets.label import PyDMLabel
from pydm.widgets.line_edit import PyDMLineEdit
from pydm.widgets.logdisplay import PyDMLogDisplay
from pydm.widgets.pushbutton import PyDMPushButton
from pydm.widgets.related_display_button import PyDMRelatedDisplayButton
from pydm.widgets.shell_command import PyDMShellCommand
from pydm.widgets.slider import PyDMSlider
from pydm.widgets.spinbox import PyDMSpinbox
from pydm.widgets.embedded_display import PyDMEmbeddedDisplay
from pydm.widgets.enum_button import PyDMEnumButton
from pydm.widgets.enum_combo_box import PyDMEnumComboBox
from pydm.widgets.byte import PyDMByteIndicator
from pydm.widgets.checkbox import PyDMCheckbox
from pydm.widgets.tab_bar import PyDMTabWidget


class CWaveFormTable(PyDMWaveformTable):
    pass


class CLabel(PyDMLabel):
    pass


class CTimePlot(PyDMTimePlot):
    pass


class CWaveFormPlot(PyDMWaveformPlot):
    pass


class CScatterPlot(PyDMScatterPlot):
    pass


class CByteIndicator(PyDMByteIndicator):
    pass


class CCheckBox(PyDMCheckbox):
    pass


class CEmbeddedDisplay(PyDMEmbeddedDisplay):
    pass


class CEnumButton(PyDMEnumButton):
    pass


class CEnumComboBox(PyDMEnumComboBox):
    pass


class CImageView(PyDMImageView):
    pass


class CLineEdit(PyDMLineEdit):
    pass


class CLogDisplay(PyDMLogDisplay):
    pass


class CPushButton(PyDMPushButton):
    pass


class CRelatedDisplayButton(PyDMRelatedDisplayButton):
    pass


class CShellCommand(PyDMShellCommand):
    pass


class CSlider(PyDMSlider):
    pass


class CSpinBox(PyDMSpinbox):
    pass


class CScaleIndicator(PyDMScaleIndicator):
    pass


class CTemplateRepeater(PyDMTemplateRepeater):
    pass


class CTabWidget(PyDMTabWidget):
    pass