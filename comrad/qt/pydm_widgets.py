# This file provides overriding of the standard PyDM classes in order to bring them to the same naming
# convention as native ComRAD widgets. This is both useful for consistency in Qt Designer widget list
# and when instantiating them from code.

import logging
import numpy as np
from pydm.widgets.waveformtable import PyDMWaveformTable
from pydm.widgets.scale import PyDMScaleIndicator
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
# from pydm.widgets.tab_bar import PyDMTabWidget
from qtpy.QtWidgets import QWidget
from qtpy.QtCore import Slot
from qtpy.QtGui import QIcon
from .value_transform import ValueTransformer
from .rules import ColorRulesMixin, WidgetRulesMixin
from typing import List, Tuple, Union, Optional


class CWaveFormTable(WidgetRulesMixin, PyDMWaveformTable):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
        """
        A :class:`qtpy.QTableWidget` with support for CS Channels.

        Values of the array are displayed in the selected number of columns.
        The number of rows is determined by the size of the waveform.
        It is possible to define the labels of each row and column.

        Args:
            parent: The parent widget for the table.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        WidgetRulesMixin.__init__(self)
        PyDMWaveformTable.__init__(self, parent=parent, init_channel=init_channel, **kwargs)


class CLabel(ColorRulesMixin, ValueTransformer, PyDMLabel):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
        """
        A :class:`qtpy.QLabel` with support for setting the text via a CS Channel, or
        through the Rules system.

        **Note!:** If a :class:`CLabel` is configured to use a :attr:`channel`, and also with a rule
        which changes the :meth:`QLabel.text` property, the behavior is undefined. Use either
        the :attr:`channel` *or* a :attr:`QLabel.text` rule, but not both.

        Args:
            parent: The parent widget for the label.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        ColorRulesMixin.__init__(self)
        PyDMLabel.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        ValueTransformer.__init__(self)

    def setNum(self, new_val: Union[float, int]):
        """
        Callback transforms the directly set numeric value through the :attr:`ValueTransformer.valueTransformation`
        code before displaying it in a standard way.

        Args:
            new_val: The new value from the channel. The type depends on the channel.
        """
        self.value_changed(new_val)

    def set_color(self, val: str):
        """Overridden method of :class:`ColorRulesMixin`.

        Args:
            val: The new value of the color."""
        super().set_color(val)
        # color = self._default_color if val is None else QColor(val)
        # palette = self.palette()
        # palette.setColor(self.foregroundRole(), color)
        # self.setPalette(palette)
        # We can't use palettes here because custom stylesheet passed via CLI will override it...
        # TODO: Also check QSS dynamic properties and polish/unpolish. But that means we need to parse rules and preset stylesheet before
        self.setStyleSheet(f'color: {val}' if val else None)


# TODO: Expose frame? What is it used for?
# class CFrame(PyDMFrame):
#     pass


class CByteIndicator(WidgetRulesMixin, ValueTransformer, PyDMByteIndicator):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
        """
        Widget for graphical representation of bits from an integer number
        with support for Channels from CS.

        Args:
            parent: The parent widget for the indicator.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        WidgetRulesMixin.__init__(self)
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

        :class:`PyDMByteIndicator` expects int value. So we construct int from the bit mask expressed by the list.

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


class CCheckBox(WidgetRulesMixin, ValueTransformer, PyDMCheckbox):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
        """
        A :class:`qtpy.QCheckbox` with support for Channels from the control system.

        Args:
            parent: The parent widget for the checkbox.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        WidgetRulesMixin.__init__(self)
        PyDMCheckbox.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        ValueTransformer.__init__(self)


class CEmbeddedDisplay(PyDMEmbeddedDisplay):

    def __init__(self, parent: Optional[QWidget] = None, **kwargs):
        """
        A :class:`qtpy.QFrame` capable of rendering a Display.

        Args:
            parent: The parent widget for the display.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        super().__init__(parent=parent, **kwargs)


class CEnumButton(WidgetRulesMixin, ValueTransformer, PyDMEnumButton):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
        """
        A :class:`qtpy.QWidget` that renders buttons for every option of Enum Items.
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
        WidgetRulesMixin.__init__(self)
        PyDMEnumButton.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        ValueTransformer.__init__(self)


class CEnumComboBox(WidgetRulesMixin, ValueTransformer, PyDMEnumComboBox):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
        """
        A :class:`qtpy.QComboBox` with support for Channels from the control system.

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
        WidgetRulesMixin.__init__(self)
        PyDMEnumComboBox.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        ValueTransformer.__init__(self)


class CImageView(WidgetRulesMixin, PyDMImageView):

    def __init__(self,
                 parent: Optional[QWidget] = None,
                 image_channel: Optional[str] = None,
                 width_channel: Optional[str] = None,
                 **kwargs):
        """
        A :class:`pyqtgraph.ImageView` subclass with support for CS Channels.

        If there is no :attr:`widthChannel` it is possible to define the width of
        the image with the :attr:`width` property.

        The :attr:`normalizeData` property defines if the colors of the images are
        relative to the :attr:`colorMapMin` and :attr:`colorMapMax` property or to
        the minimum and maximum values of the image.

        Use the :attr:`newImageSignal` to hook up to a signal that is emitted when a new
        image is rendered in the widget.

        Args:
            parent: The parent widget for the image view.
            image_channel: The channel to be used by the widget for the image data.
            width_channel: The channel to be used by the widget to receive the image width information.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        WidgetRulesMixin.__init__(self)
        PyDMImageView.__init__(self, parent=parent, image_channel=image_channel, width_channel=width_channel, **kwargs)

    def default_rule_channel(self) -> str:
        return self.imageChannel


class CLineEdit(ColorRulesMixin, ValueTransformer, PyDMLineEdit):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
        """

        A :class:`qtpy.QLineEdit` (writable text field) with support for CS Channels.
        This widget offers an unit conversion menu when users Right Click
        into it.

        Args:
            parent: The parent widget for the line edit.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        ColorRulesMixin.__init__(self)
        PyDMLineEdit.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        ValueTransformer.__init__(self)

    def set_color(self, val: str):
        """Overridden method of :class:`ColorRulesMixin`.

        Args:
            val: The new value of the color."""
        super().set_color(val)
        self.setStyleSheet(f'background-color: {val}' if val else None)
        # TODO: Calculate color and choose appropriate text color by the contrast ratio


class CLogDisplay(PyDMLogDisplay):

    def __init__(self,
                 parent: Optional[QWidget] = None,
                 log_name: Optional[str] = None,
                 level: int = logging.NOTSET,
                 **kwargs):
        """
        Standard display for Log Output.

        This widget handles instantiating a ``GuiHandler`` and displaying log
        messages to a :class:`qtpy.QPlainTextEdit`. The level of the log can be changed from
        inside the widget itself, allowing users to select from any of the levels specified by the widget.

        Args:
            parent: The parent widget for the log display.
            log_name: Name of log to display in widget.
            level: Initial level of log display.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        super().__init__(parent=parent, logname=log_name, level=level, **kwargs)


class CPushButton(WidgetRulesMixin, PyDMPushButton):

    def __init__(self,
                 parent: Optional[QWidget] = None,
                 label: Optional[str] = None,
                 icon: Optional[QIcon] = None,
                 press_value: Union[str, int, float, None] = None,
                 relative: bool = False,
                 init_channel: Optional[str] = None,
                 **kwargs):
        """
        Basic PushButton to send a fixed value.

        This type is meant to hold a specific value, and send that value
        to a channel when it is clicked. It works in two different modes of operation:

            1. A fixed value can be given to the :attr:`.pressValue` attribute. Whenever the
               button is clicked a signal containing this value will be sent to the connected channel.
               This is the default behavior of the button.
            2. However, if the :attr:`.relativeChange` is set to ``True``, the fixed value will be added
               to the current value of the channel. This means that the button will increment a channel by
               a fixed amount with every click, a consistent relative move.

        Args:
            parent: The parent widget for the button.
            label: String to place on button.
            icon: An icon to display on the button.
            press_value: Value to be sent when the button is clicked.
            relative: Choice to have the button perform a relative put, instead of always setting to an absolute value.
            init_channel: ID of channel to manipulate.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        WidgetRulesMixin.__init__(self)
        PyDMPushButton.__init__(self, parent=parent,
                                label=label,
                                icon=icon,
                                pressValue=press_value,
                                relative=relative,
                                init_channel=init_channel,
                                **kwargs)


class CRelatedDisplayButton(PyDMRelatedDisplayButton):

    def __init__(self, parent: Optional[QWidget] = None, filename: Optional[str] = None, **kwargs):
        """
        A :class:`qtpy.QPushButton` capable of opening a new :class:`pydm.Display` at the same of at a new window.

        Args:
            parent: The parent widget for the button.
            filename: The file to be opened.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        super().__init__(parent=parent, filename=filename, **kwargs)


class CShellCommand(PyDMShellCommand):

    def __init__(self, parent: Optional[QWidget] = None, command: Optional[str] = None, **kwargs):
        """
        A :class:`qtpy.QPushButton` capable of executing shell commands.

        Args:
            parent: The parent widget for the button.
            command: Command to execute.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        super().__init__(parent=parent, command=command, **kwargs)


class CSlider(WidgetRulesMixin, ValueTransformer, PyDMSlider):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
        """
        A :class:`qtpy.QSlider` with support for Channels and more from the control system.

        Args:
            parent: The parent widget for the slider.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        WidgetRulesMixin.__init__(self)
        PyDMSlider.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        ValueTransformer.__init__(self)


class CSpinBox(WidgetRulesMixin, ValueTransformer, PyDMSpinbox):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
        """
        A :class:`qtpy.QDoubleSpinBox` with support for Channels and more from the control system.

        Args:
            parent: The parent widget for the spinbox.
            init_channel: The channel to be used by the widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        WidgetRulesMixin.__init__(self)
        PyDMSpinbox.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        ValueTransformer.__init__(self)


class CScaleIndicator(WidgetRulesMixin, ValueTransformer, PyDMScaleIndicator):

    def __init__(self, parent: Optional[QWidget] = None, init_channel: Optional[str] = None, **kwargs):
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
        WidgetRulesMixin.__init__(self)
        PyDMScaleIndicator.__init__(self, parent=parent, init_channel=init_channel, **kwargs)
        ValueTransformer.__init__(self)


class CTemplateRepeater(PyDMTemplateRepeater):

    def __init__(self, parent: Optional[QWidget] = None, **kwargs):
        """
        Takes takes a template display with macro variables, and a JSON
        file (or a list of dictionaries) with a list of values to use to fill in
        the macro variables, then creates a layout with one instance of the
        template for each item in the list.

        It can be very convenient if you have displays that repeat the same set of
        widgets over and over - for instance, if you have a standard set of
        controls for a magnet, and want to build a display with a list of controls
        for every magnet, the Template Repeater lets you do that with a minimum
        amount of work: just build a template for a single magnet, and a JSON list
        with the data that describes all of the magnets.

        Args:
            parent: The parent of this widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        super().__init__(parent=parent, **kwargs)


# TODO: Do we need this widget?
# class CTabWidget(PyDMTabWidget):
#     pass
