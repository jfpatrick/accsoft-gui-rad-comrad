import logging
import weakref
from abc import abstractmethod
from typing import Optional, Dict, Any, TypeVar, cast, Union
from qtpy.QtCore import QObject, Signal, QEvent
from qtpy.QtWidgets import QWidget
from qtpy.QtDesigner import QDesignerFormWindowInterface
from pydm.utilities import is_qt_designer
from pydm import config
from comrad.generics import GenericQObjectMeta


logger = logging.getLogger(__name__)


T = TypeVar('T', bound='CContext')


class CContext(QObject):

    selectorChanged = Signal()
    """Notification when :attr:`selector` attribute has been updated."""

    dataFiltersChanged = Signal()
    """Notification when :attr:`data_filters` attribute has been updated."""

    wildcardsChanged = Signal()
    """Notification when :attr:`wildcards` attribute has been updated."""

    inheritanceChanged = Signal()
    """Notification when :attr:`inherit_parent_selector` or :attr:`inherit_parent_data_filters` have been updated."""

    def __init__(self,
                 parent: Optional[QObject] = None,
                 selector: Optional[str] = None,
                 data_filters: Optional[Dict[str, Any]] = None,
                 wildcards: Optional[Dict[str, Any]] = None):
        """
        Context that can be used to group several widgets/connections together with the same parameters.

        Args:
            selector: Cycle selector that should be applied to the widgets.
            data_filters: Data filters for expert applications that can set FESA data filters when directly working through RDA.
            wildcards: Any macro substitutions that need to be done dynamically at runtime.
        """
        super().__init__(parent)
        self._selector = selector or None  # Avoid empty string
        self._data_filters = data_filters or None  # Avoid empty dict
        self._wildcards = wildcards or None  # Avoid empty dict
        self._inherit_parent_selector: bool = True
        self._inherit_parent_data_filters: bool = True

    def _set_selector(self, new_val: Optional[str]):
        new_val = new_val or None  # Avoid empty string
        if new_val != self._selector:
            self._selector = new_val
            self.selectorChanged.emit()

    selector = property(fget=lambda self: self._selector, fset=_set_selector)
    """Cycle selector that should be applied to the widgets."""

    def _set_data_filters(self, new_val: Optional[Dict[str, Any]]):
        new_val = new_val or None  # Avoid empty dict
        if new_val != self._data_filters:
            self._data_filters = new_val
            self.dataFiltersChanged.emit()

    data_filters = property(fget=lambda self: self._data_filters, fset=_set_data_filters)
    """Data filters for expert applications that can set FESA data filters when directly working through RDA."""

    def _set_wildcards(self, new_val: Optional[Dict[str, Any]]):
        new_val = new_val or None  # Avoid empty dict
        if new_val != self._wildcards:
            self._wildcards = new_val
            self.wildcardsChanged.emit()

    wildcards = property(fget=lambda self: self._wildcards, fset=_set_wildcards)
    """Any macro substitutions that need to be done dynamically at runtime."""

    def _set_inherit_parent_selector(self, new_val: bool):
        if new_val != self._inherit_parent_selector:
            self._inherit_parent_selector = new_val
            self.inheritanceChanged.emit()

    inherit_parent_selector = property(fget=lambda self: self._inherit_parent_selector, fset=_set_inherit_parent_selector)
    """
    Inherit the parent selector when in this context it's set to ``None``. When set to ``False``, ``None`` selector
    in this context will literally mean "do not use any selector".
    """

    def _set_inherit_parent_data_filters(self, new_val: bool):
        if new_val != self._inherit_parent_data_filters:
            self._inherit_parent_data_filters = new_val
            self.inheritanceChanged.emit()

    inherit_parent_data_filters = property(fget=lambda self: self._inherit_parent_data_filters, fset=_set_inherit_parent_data_filters)
    """
    Inherit the parent data filters when in this context it's set to ``None``. When set to ``False``, ``None``
    data filters in this context will literally mean "do not use any data filters". If parent data filters are
    inherited and local filters also exist, then the two dictionaries will be merged giving the priority to
    local filters.
    """

    def merged(self, parent: Optional['CContext']) -> 'CContext':
        """
        Merge context with parent context producing a view that represents cumulative settings.
        These context can define only parts of information, e.g. one defining data filters, another defining a selector,
        or both defining data filters but differently.

        Args:
             parent: Parent context at the next parent context provider. If a widget is enclosed inside CContextFrame
                     its context will provide a combined view already. If not, the next parent context will be window
                     context, which is root.
        Returns:
            A new context with the combined parameters.
        """
        if parent is None:
            return self.from_existing_replacing(self)

        selector = parent.selector if self.inherit_parent_selector and self.selector is None else self.selector
        data_filters = self.data_filters if not self.inherit_parent_data_filters else {**(parent.data_filters or {}),
                                                                                       **(self.data_filters or {})}
        wildcards = {**(parent.wildcards or {}), **(self.wildcards or {})}
        return self.from_existing_replacing(self, selector=selector, data_filters=data_filters, wildcards=wildcards)

    @classmethod
    def from_existing_replacing(cls, another: T, **kwargs) -> T:
        """
        Creates a clone of the object with changed attributes

        Args:
            another: The prototype object to create from.
            kwargs: Arguments that should be passed into :meth:`__init__` method overriding the prototype's values.

        Returns:
            Cloned object.
        """
        new_kwargs = {
            'selector': another.selector,
            'data_filters': another.data_filters,
            'wildcards': another.wildcards,
        }
        new_kwargs.update(kwargs)
        obj = cls(**new_kwargs)
        obj.inherit_parent_data_filters = another.inherit_parent_data_filters
        obj.inherit_parent_selector = another.inherit_parent_selector
        return obj

    @classmethod
    def to_string_suffix(cls, data_filters: Optional[Dict[str, Any]], selector: Optional[str]) -> str:
        """
        Common way of adding context information into string addresses.

        Args:
            data_filters: Data filters to include. If specified, they will override selector.
            selector: Selector to include in the suffix. Will be overridden by data filters.

        Returns:
            A formatter suffix suitable for appending to the address string for internal purposes.
        """
        addr = ''
        if data_filters:
            addr += '?'
            addr += '&'.join((f'{k}={v}' for k, v in data_filters.items()))
        elif selector:
            addr += '@'
            addr += selector
        return addr

    def __eq__(self, other: object) -> bool:
        if other is None or type(other) != type(self):
            return False
        other_ctx = cast(CContext, other)
        return (self.inherit_parent_data_filters == other_ctx.inherit_parent_data_filters
                and self.inherit_parent_selector == other_ctx.inherit_parent_selector
                and self._selector == other_ctx._selector
                and self._wildcards == other_ctx._wildcards
                and self._data_filters == other_ctx._data_filters)

    def __repr__(self):
        orig = super().__repr__()
        return (f'{orig[:-1]} selector={self.selector}; data_filters={self.data_filters}; wildcards={self.wildcards} '
                f'| inherits: data_filters={str(self.inherit_parent_data_filters)};'
                f' selector={str(self.inherit_parent_selector)}>')


class CContextProvider(metaclass=GenericQObjectMeta):
    """Protocol for conforming context providers that participate in the :class:`CContext` supply chain."""

    contextUpdated: Signal = None
    """
    Signal to communicate to children that context need to be updated and possibly connections need
    to be re-established. This is just a placeholder. Subclasses must implement the actual signal.
    """

    @property
    @abstractmethod
    def context_ready(self) -> bool:
        """
        Context has been prepared and is ready to be used.

        If this method returns ``False``, widgets that are relying on the context from this provider,
        should not try to connect to the control system, as those connections may fail or will need to
        be dropped in favor of new connections with the updated context.
        """
        pass

    @abstractmethod
    def get_context_view(self) -> CContext:
        """
        Combined view of the local context and all the contexts of the parent context providers.
        """
        pass


__designer_window_stub = None


def get_designer_window_stub() -> Union[QWidget, CContextProvider]:
    global __designer_window_stub
    if not __designer_window_stub:
        class CDesignerWindowStub(QWidget, CContextProvider):

            contextUpdated = Signal()

            def __init__(self):
                QWidget.__init__(self)
                CContextProvider.__init__(self)
                self._local_context = CContext()

            def get_context_view(self) -> CContext:
                return self._local_context

            @property
            def context_ready(self) -> bool:
                return True

        __designer_window_stub = CDesignerWindowStub()

    return __designer_window_stub


def find_context_provider(widget: QWidget) -> Union[QWidget, CContextProvider, None]:
    """Finds next context provider in the context supply chain that supplies the context view directly to the
    given widget.

    Args:
        widget: Widget receiving the context view.

    Returns:
        Provider supplying the context view. It can be either Main Window for global window context, or CContextFrame
        for localized contexts. If neither exists, e.g. when using Qt Designer, ``None`` will be returned.
    """
    parent = widget.parentWidget()
    # Checking against CContextProvider here is insufficient
    # Because of monkey-patching, PyDMMainWindow will produce false-negative on such check
    if parent is None or hasattr(parent, 'get_context_view'):
        return parent
    elif is_qt_designer() and config.DESIGNER_ONLINE and isinstance(parent, QDesignerFormWindowInterface):
        # In Qt Designer, we'll never reach state of "context_ready", therefore
        # online designer will never get connected.
        return get_designer_window_stub()
    else:
        return find_context_provider(parent)


class CContextTrackingDelegate(QObject):

    CONTEXT_CHANGED_SLOT = 'context_changed'

    def __init__(self, parent: Optional[QObject] = None):
        """
        Delegate that helps to start and stop watching context changes whenever widget is added or removed from the
        view hierarchy.

        Args:
            parent: Parent owner of this object.
        """
        super().__init__(parent)
        self._prev_context_provider: Optional[weakref.ReferenceType] = None

    @property
    def context_ready(self) -> bool:
        """If context provider is connected."""
        if self._prev_context_provider is None:
            return False
        context_provider = self._prev_context_provider()
        if not context_provider:
            return False
        return context_provider.context_ready

    def eventFilter(self, obj: QWidget, event: QEvent) -> bool:
        # Note! ParentChange does not fire when widgets are instantiated from the UI file
        if event.type() in (QEvent.ParentChange,
                            QEvent.ShowToParent,
                            QEvent.WindowActivate,
                            QEvent.Polish,
                            QEvent.PolishRequest,  # The only sensible type for CValueAggregator, as it's hidden in runtime
                            ):
            if not callable(getattr(obj, self.CONTEXT_CHANGED_SLOT, None)):
                logger.exception(f'Cannot use CContextTrackingDelegate on an unsupported widget {obj}')
                return False

            if self._prev_context_provider is None:
                # Only in certain cases we can be sure that it's a new parent
                # Because on ShowToParent, which can happen after ParentChange, this will be
                # a repetition.
                logger.debug(f'Detected new parent for {obj}: {obj.parent()}')

            next_context_provider = find_context_provider(obj)
            prev_context_provider = self._prev_context_provider() if self._prev_context_provider is not None else None
            if prev_context_provider != next_context_provider:
                logger.debug(f'{obj}: changed context provider from {prev_context_provider} to {next_context_provider}')

                # import traceback
                # import sys
                # traceback.print_stack(file=sys.stdout)

                self._disconnect_previous_context_provider(obj)

                if next_context_provider is not None:
                    self._prev_context_provider = weakref.ref(next_context_provider)
                    logger.debug(f'{obj}: subscribing to context provider {next_context_provider}')
                    next_context_provider.contextUpdated.connect(getattr(obj, self.CONTEXT_CHANGED_SLOT))
                else:
                    self._prev_context_provider = None
                    logger.debug(f"{obj}: not subscribing to context provider, since it's not found")
                obj.context_changed()
        return super().eventFilter(obj, event)

    def _disconnect_previous_context_provider(self, obj: QWidget):
        if not self._prev_context_provider:
            return

        context_provider = self._prev_context_provider()
        if context_provider:
            logger.debug(f'{obj}: unsubscribing from context provider {context_provider}')
            try:
                context_provider.contextUpdated.disconnect(getattr(obj, self.CONTEXT_CHANGED_SLOT))
            except TypeError:
                pass
        else:
            logger.debug(f"{obj}: not unsubscribing from context provider, since it's not found")

        self._prev_context_provider = None
