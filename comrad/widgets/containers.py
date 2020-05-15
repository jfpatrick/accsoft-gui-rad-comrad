# This file provides overriding of the standard PyDM classes in order to bring them to the same naming
# convention as native ComRAD widgets. This is both useful for consistency in Qt Designer widget list
# and when instantiating them from code.

import logging
from typing import Optional, Dict, Any
from qtpy.QtWidgets import QWidget, QFrame
from qtpy.QtCore import Signal, Slot, Property
from pydm.widgets.template_repeater import PyDMTemplateRepeater
from pydm.widgets.embedded_display import PyDMEmbeddedDisplay
from pydm import Display as PyDMDisplay
# from pydm import data_plugins
# from pydm.widgets.tab_bar import PyDMTabWidget
from comrad.data.context import CContext, CContextProvider, find_context_provider, CContextTrackingDelegate
from comrad.widgets.widget import common_widget_repr


logger = logging.getLogger(__name__)


class CEmbeddedDisplay(PyDMEmbeddedDisplay):

    def __init__(self, parent: Optional[QWidget] = None, **kwargs):
        """
        A :class:`~PyQt5.QtWidgets.QFrame` capable of rendering a :class:`CDisplay`.

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
be integrated inside another display using :class:`CEmbeddedDisplay`.
"""


class CContextFrame(QFrame, CContextProvider):

    contextUpdated = Signal()
    """Signal to communicate to children that context needs to be updated and possibly connections need to be re-established."""

    def __init__(self, parent: Optional[QWidget] = None, context: Optional[CContext] = None):
        """
        This widget allows to update its child widgets with a new context by redefining macro variables, or
        cycle selector or data filters on the fly..

        Use-cases could be:

         * Dynamic selection of the device or property.
         * Dynamic selection of the cycle / timing user.
         * Dynamic selection of the data filter.

        **Note!** This widget does not support dynamic movement between different parents. That is, if you add
        it to view hierarchy, display it, and then decide to move via :meth:`~QWidget.setParent`, the logic will break.
        """
        QFrame.__init__(self, parent)
        CContextProvider.__init__(self)
        self._local_context = context or CContext()
        self._local_context.wildcardsChanged.connect(self.contextUpdated.emit)
        self._local_context.selectorChanged.connect(self.contextUpdated.emit)
        self._local_context.dataFiltersChanged.connect(self.contextUpdated.emit)
        self._local_context.inheritanceChanged.connect(self.contextUpdated.emit)
        self._context_tracker = CContextTrackingDelegate(self)
        logger.debug(f'{self}: Installing new context tracking event handler: {self._context_tracker}')
        self.installEventFilter(self._context_tracker)

    def _get_inherit_selector(self) -> bool:
        return self._local_context.inherit_parent_selector

    def _set_inherit_selector(self, new_val: bool):
        self._local_context.inherit_parent_selector = new_val

    inheritSelector: bool = Property(bool, _get_inherit_selector, _set_inherit_selector)
    """
    Inherit the parent context selector when local context selector is set to ``None``. When this property is set to
    ``False``, ``None`` selector in the local context will literally mean "do not use any selector".
    """

    def _get_inherit_data_filters(self) -> bool:
        return self._local_context.inherit_parent_data_filters

    def _set_inherit_data_filters(self, new_val: bool):
        self._local_context.inherit_parent_data_filters = new_val

    inheritDataFilters: bool = Property(bool, _get_inherit_data_filters, _set_inherit_data_filters)
    """
    Inherit the parent context data filters when the ones of the local context are set to ``None``. When this
    property is set to ``False``, ``None`` data filters of the local context will literally mean "do not use any
    data filters". If both parent and local contexts have data filters defined, they will be merged giving the
    priority to local filters.
    """

    def _get_selector(self) -> Optional[str]:
        return self._local_context.selector

    def _set_selector(self, new_val: Optional[str]):
        self._local_context.selector = new_val

    selector: Optional[str] = Property(str, _get_selector, _set_selector)
    """
    Property giving access to the selector of the owned context. This is useful for setting the selector inside the
    ComRAD Designer.
    """
    # TODO: Open up data filters and wildcards (similar to selector) later when proven useful.

    @Slot(dict)
    def updateWildcards(self, wildcards: Dict[str, Any]):
        """
        Slot to connect to, so that all child widgets of the container receive new macro variable definitions.

        Args:
            macros: Dictionary with one or more redefined macro variables and their values.
        """
        logger.debug(f'{self} received new wildcards: {wildcards}')
        self._local_context.wildcards = wildcards

    @Slot(str)
    def updateSelector(self, selector: str):
        """
        Slot to connect to, so that all child widgets of the container work on the given selector.

        Args:
            selector: New cycle selector for all child widgets.
        """
        logger.debug(f'{self} received new selector: {selector}')
        self._local_context.selector = selector

    @Slot(dict)
    def updateDataFilters(self, data_filters: Dict[str, Any]):
        """
        Slot to connect to, so that all child widgets of the container work on the given data filters.

        Args:
            selector: New cycle selector for all child widgets.
        """
        logger.debug(f'{self} received new data filters: {data_filters}')
        self._local_context.data_filters = data_filters

    def context_changed(self):
        """
        Slot that receives a new context from the context provider, (e.g. when widgets are grouped inside a container).
        This slot helps propagating the event from several levels of the :class:`CContextFrame` that change their
        properties into widgets down the hierarchy.

        This slot will automatically get connected by the parent :class:`CContextFrame`.
        """
        logger.debug(f'{self} propagating the parent context change event to children')
        self.contextUpdated.emit()

    def get_context_view(self):
        """
        Combined view of the local context and all the contexts of the parent context providers.
        """
        context_provider = find_context_provider(self)
        if not context_provider:
            return self._local_context.merged(None)
        else:
            return self._local_context.merged(context_provider.get_context_view())

    @property
    def context_ready(self) -> bool:
        return self._context_tracker.context_ready

    __repr__ = common_widget_repr


# TODO: Do we need this widget?
# class CTabWidget(PyDMTabWidget):
#     pass
