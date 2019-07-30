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
from qtpy.QtWidgets import QWidget
from qtpy.QtGui import QIcon
from typing import Union
from .value_transform import ValueTransformer


class CWaveFormTable(PyDMWaveformTable):
    pass


class CLabel(ValueTransformer, PyDMLabel):

    def __init__(self, parent: QWidget = None, init_channel: str = None, **kwargs):
        """
        A QLabel with support for setting the text via a CS Channel, or
        through the Rules system.

        **Note!:** If a CLabel is configured to use a Channel, and also with a rule
        which changes the 'Text' property, the behavior is undefined.  Use either
        the Channel *or* a text rule, but not both.

        Args:
            parent: The parent widget for the label.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        ValueTransformer.__init__(self)
        PyDMLabel.__init__(self, parent=parent, init_channel=init_channel, **kwargs)


class CTimePlot(PyDMTimePlot):
    pass


class CWaveFormPlot(PyDMWaveformPlot):
    pass


class CScatterPlot(PyDMScatterPlot):
    pass


class CByteIndicator(PyDMByteIndicator):
    pass


class CCheckBox(ValueTransformer, PyDMCheckbox):

    def __init__(self, parent: QWidget = None, init_channel: str = None, **kwargs):
        """
        A QCheckbox with support for Channels from the control system.

        Args:
            parent: The parent widget for the label.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        ValueTransformer.__init__(self)
        PyDMCheckbox.__init__(self, parent=parent, init_channel=init_channel, **kwargs)


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


class CPushButton(ValueTransformer, PyDMPushButton):

    def __init__(self,
                 parent: QWidget = None,
                 label: str = None,
                 icon: QIcon = None,
                 pressValue: Union[int, float, str] = None,
                 relative: bool = False,
                 init_channel: str = None,
                 **kwargs):
        """
        Basic push-button to send a fixed value.

        The `CPushButton` is meant to hold a specific value, and send that value
        to a channel when it is clicked, much like the MessageButton does in EDM.
        The `CPushButton` works in two different modes of operation, first, a
        fixed value can be given to the `.pressValue` attribute, whenever the
        button is clicked a signal containing this value will be sent to the
        connected channel. This is the default behavior of the button. However, if
        the `.relativeChange` is set to True, the fixed value will be added
        to the current value of the channel. This means that the button will
        increment a channel by a fixed amount with every click, a consistent
        relative move.

        Args:
            parent: The parent widget for the label.
            label: String to place on button.
            icon: An Icon to display on the button.
            pressValue: Value to be sent when the button is clicked.
            relative: Choice to have the button perform a relative put, instead of always setting to an absolute value.
            init_channel: ID of channel to manipulate.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        ValueTransformer.__init__(self)
        PyDMPushButton.__init__(self, parent=parent,
                                label=label,
                                icon=icon,
                                pressValue=pressValue,
                                relative=relative,
                                init_channel=init_channel,
                                **kwargs)


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
