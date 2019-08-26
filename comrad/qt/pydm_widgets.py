# This file provides overriding of the standard PyDM classes in order to bring them to the same naming
# convention as native ComRAD widgets. This is both useful for consistency in Qt Designer widget list
# and when instantiating them from code.

import numpy as np
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
from pydm.widgets.frame import PyDMFrame
from qtpy.QtWidgets import QWidget
from qtpy.QtCore import Slot
from .value_transform import ValueTransformer
from typing import List, Tuple, Union


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
        PyDMLabel.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        ValueTransformer.__init__(self)

    def setNum(self, new_val: Union[float, int]):
        """
        Callback transforms the directly set numeric value through the valueTransformation code before displaying it in a
        standard way.

        Args:
            new_val: The new value from the channel. The type depends on the channel.
        """
        self.value_changed(new_val)

class CTimePlot(PyDMTimePlot):
    pass


class CWaveFormPlot(PyDMWaveformPlot):
    pass


class CScatterPlot(PyDMScatterPlot):
    pass

class CFrame(PyDMFrame):
    pass


class CByteIndicator(ValueTransformer, PyDMByteIndicator):

    def __init__(self, parent: QWidget = None, init_channel: str = None, **kwargs):
        """
        Widget for graphical representation of bits from an integer number
        with support for Channels from CS.

        Args:
            parent: The parent widget for the indicator.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        PyDMByteIndicator.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        ValueTransformer.__init__(self)

    @Slot(list)
    @Slot(bool)
    @Slot(int)
    @Slot(float)
    @Slot(str)
    @Slot(np.ndarray)
    def channelValueChanged(self, new_val: Union[bool, int, List[Tuple[int, str]]]):
        """
        Slot that accepts types, not natively supported by PyDM
        list: Currently, PyJAPC is expected to convert EnumItemSet into List[Tuple[code, name]].
        bool: Indicator fails to display a single bool value

        PyDMByteIndicator expects int value. So we construct int from the bit mask expressed by the list.

        Args:
            new_val: Incoming value.
        """
        if isinstance(new_val, np.ndarray):
            bit_mask = 0
            row_length, = new_val.shape()
            for (x, y), el in np.ndenumerate(new_val):
                if int(el) != 0:
                    idx = x * row_length + y
                    bit_mask |= 1 << idx
            PyDMByteIndicator.channelValueChanged(self, bit_mask)
        elif isinstance(new_val, list):
            bit_mask = 0
            for val, _ in new_val:
                bit_mask |= val
            PyDMByteIndicator.channelValueChanged(self, bit_mask)
        else:
            # Fallback to the original Byte indicator
            PyDMByteIndicator.channelValueChanged(self, int(new_val))


class CCheckBox(ValueTransformer, PyDMCheckbox):

    def __init__(self, parent: QWidget = None, init_channel: str = None, **kwargs):
        """
        A QCheckbox with support for Channels from the control system.

        Args:
            parent: The parent widget for the checkbox.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        PyDMCheckbox.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        ValueTransformer.__init__(self)


class CEmbeddedDisplay(PyDMEmbeddedDisplay):
    pass


class CEnumButton(ValueTransformer, PyDMEnumButton):

    def __init__(self, parent: QWidget = None, init_channel: str = None, **kwargs):
        """
        A QWidget that renders buttons for every option of Enum Items.
        For now three types of buttons can be rendered:
        - Push Button
        - Radio Button

        Signals:
         - send_value_signal: Emitted when the user changes the value.

        Args:
            parent: The parent widget for the button.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        PyDMEnumButton.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        ValueTransformer.__init__(self)


class CEnumComboBox(ValueTransformer, PyDMEnumComboBox):

    def __init__(self, parent: QWidget = None, init_channel: str = None, **kwargs):
        """
        A QComboBox with support for Channels from the control system.

        Signals:
         - send_value_signal: Emitted when the user changes the value.
         - activated: Emitted when the user chooses an item in the combobox.
         - currentIndexChanged: Emitted when the index is changed in the combobox.
         - highlighted: Emitted when an item in the combobox popup list is highlighted by the user.

        Args:
            parent: The parent widget for the combobox.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        PyDMEnumComboBox.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        ValueTransformer.__init__(self)


class CImageView(PyDMImageView):
    pass


class CLineEdit(ValueTransformer, PyDMLineEdit):

    def __init__(self, parent: QWidget = None, init_channel: str = None, **kwargs):
        """

        A QLineEdit (writable text field) with support for CS Channels.
        This widget offers an unit conversion menu when users Right Click
        into it.

        Args:
            parent: The parent widget for the line edit.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        PyDMLineEdit.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        ValueTransformer.__init__(self)


class CLogDisplay(PyDMLogDisplay):
    pass


class CPushButton(PyDMPushButton):
    pass


class CRelatedDisplayButton(PyDMRelatedDisplayButton):
    pass


class CShellCommand(PyDMShellCommand):
    pass


class CSlider(ValueTransformer, PyDMSlider):

    def __init__(self, parent: QWidget = None, init_channel: str = None, **kwargs):
        """
        A QSlider with support for Channels and more from the control system.

        Args:
            parent: The parent widget for the slider.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        PyDMSlider.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        ValueTransformer.__init__(self)


class CSpinBox(ValueTransformer, PyDMSpinbox):

    def __init__(self, parent: QWidget = None, init_channel: str = None, **kwargs):
        """
        A QDoubleSpinBox with support for Channels and more from the control system.

        Args:
            parent: The parent widget for the spinbox.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        PyDMSpinbox.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        ValueTransformer.__init__(self)


class CScaleIndicator(ValueTransformer, PyDMScaleIndicator):

    def __init__(self, parent: QWidget = None, init_channel: str = None, **kwargs):
        """
        A bar-shaped indicator for scalar value with support for Channels and
        more from the control system.
        Configurable features include indicator type (bar/pointer), scale tick
        marks and orientation (horizontal/vertical).

        Args:
            parent: The parent widget for the indicator.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        PyDMScaleIndicator.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        ValueTransformer.__init__(self)


class CTemplateRepeater(PyDMTemplateRepeater):
    pass


class CTabWidget(PyDMTabWidget):
    pass
