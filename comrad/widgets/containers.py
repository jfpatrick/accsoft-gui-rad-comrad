# This file provides overriding of the standard PyDM classes in order to bring them to the same naming
# convention as native ComRAD widgets. This is both useful for consistency in Qt Designer widget list
# and when instantiating them from code.

import logging
from typing import Optional
from pydm.widgets.template_repeater import PyDMTemplateRepeater
from pydm.widgets.embedded_display import PyDMEmbeddedDisplay
from pydm import Display as PyDMDisplay
# from pydm import data_plugins
# from pydm.widgets.tab_bar import PyDMTabWidget
from qtpy.QtWidgets import QWidget


logger = logging.getLogger(__name__)


class CEmbeddedDisplay(PyDMEmbeddedDisplay):

    def __init__(self, parent: Optional[QWidget] = None, **kwargs):
        """
        A :class:`qtpy.QFrame` capable of rendering a :class:`comrad.CDisplay`.

        Args:
            parent: The parent widget for the display.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        super().__init__(parent=parent, **kwargs)


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
        for every magnet, the :class:`CTemplateRepeater` lets you do that with a minimum
        amount of work: just build a template for a single magnet, and a JSON list
        with the data that describes all of the magnets.

        Args:
            parent: The parent of this widget.
            **kwargs: Any future extras that need to be passed down to PyDM.
        """
        super().__init__(parent=parent, **kwargs)


# We can't subclass PyDMDisplay at this point, because load_py_file will try to look for any PyDMDisplay subclasses and
# load them which will break the logic when constructing displays in code, because more than one subclass will be found
# by the loader (CDisplay and user-defined subclass).
CDisplay = PyDMDisplay
"""Display is your dashboard and/or window unit.

Displays are the widgets that get integrated inside runtime application and can occupy the whole window, or
be integrated inside another display using CEmbeddedDisplay.
"""


# TODO: Do we need this widget?
# class CTabWidget(PyDMTabWidget):
#     pass
