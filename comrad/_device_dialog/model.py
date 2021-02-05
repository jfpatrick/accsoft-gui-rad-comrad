import logging
import operator
from asyncio import ensure_future, Future
from copy import copy
from dataclasses import dataclass, field
from abc import ABCMeta, abstractmethod
from typing import Union, Optional, List, Generic, TypeVar
from qtpy.QtCore import QStringListModel, Signal, QModelIndex, Slot, QObject
from pyccda import AsyncAPI as CCDA
from comrad.data.addr import ControlEndpointAddress
from comrad.generics import GenericQObjectMeta


logger = logging.getLogger(__name__)


_T = TypeVar('_T')


@dataclass
class Item(Generic[_T], metaclass=ABCMeta):
    name: str
    children: List[_T] = field(default_factory=list)
    selected_child: int = -1


class NestedListSubItem(Item[str]):
    pass


class NestedListRootItem(Item[NestedListSubItem]):
    pass


class AbstractNestedStringListModel(QStringListModel, metaclass=GenericQObjectMeta):

    root_items_changed = Signal(list, QModelIndex)
    intermediate_items_changed = Signal(list, QModelIndex)
    leafs_changed = Signal(list, QModelIndex)
    result_changed = Signal(str)

    def __init__(self, require_full_selection: bool, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._require_full_selection = require_full_selection
        self._items: List[NestedListRootItem] = []
        self._selected_root: int = -1
        self._selected_intermediate_node: int = -1
        self._selected_leaf: int = -1

    @Slot(QModelIndex)
    @Slot(int)
    def root_item_selection_changed(self, index: Union[int, QModelIndex]):
        idx: int = index.row() if isinstance(index, QModelIndex) else index
        if idx < 0:
            logger.warning('In Device Selector, an invalid root item is selected. This should not happen!')
            return

        self._selected_root = idx
        item = self._items[self._selected_root]
        self._selected_intermediate_node = item.selected_child
        if self._require_full_selection and self._selected_intermediate_node < 0:
            item.selected_child = self._selected_intermediate_node = 0
        self.intermediate_items_changed.emit(self._map_intermediate_items(item), self._row_index(self._selected_intermediate_node))

        if self._selected_intermediate_node >= 0:
            sub_item = item.children[self._selected_intermediate_node]
            self._selected_leaf = sub_item.selected_child
            if self._require_full_selection and self._selected_leaf < 0:
                sub_item.selected_child = self._selected_leaf = 0
            self.leafs_changed.emit(self._map_leaf_items(sub_item), self._row_index(self._selected_leaf))
        else:
            self._selected_leaf = -1
            self.leafs_changed.emit([], self._row_index(self._selected_leaf))
        self.result_changed.emit(self.result)

    @Slot(QModelIndex)
    @Slot(int)
    def intermediate_item_selection_changed(self, index: Union[int, QModelIndex]):
        idx: int = index.row() if isinstance(index, QModelIndex) else index
        self._selected_intermediate_node = idx if self._require_full_selection else idx - 1

        if self._selected_root < 0:
            logger.warning('In Device Selector, an intermediate item is selected while root is undefined. This should not happen!')
            return

        item = self._items[self._selected_root]
        item.selected_child = self._selected_intermediate_node
        if self._selected_intermediate_node >= 0:
            sub_item = item.children[self._selected_intermediate_node]
            self._selected_leaf = sub_item.selected_child
            if self._require_full_selection and self._selected_leaf < 0:
                sub_item.selected_child = self._selected_leaf = 0
            self.leafs_changed.emit(self._map_leaf_items(sub_item), self._row_index(self._selected_leaf))
        else:
            self._selected_leaf = -1
            self.leafs_changed.emit([], self._row_index(self._selected_leaf))
        self.result_changed.emit(self.result)

    @Slot(QModelIndex)
    @Slot(int)
    def leaf_selection_changed(self, index: Union[int, QModelIndex]):
        idx: int = index.row() if isinstance(index, QModelIndex) else index
        self._selected_leaf = idx if self._require_full_selection else idx - 1
        if self._selected_root < 0:
            logger.warning('In Device Selector, a leaf item is selected while root is undefined. This should not happen!')
            return

        item = self._items[self._selected_root]
        sub_item = item.children[self._selected_intermediate_node]
        sub_item.selected_child = self._selected_leaf
        self.result_changed.emit(self.result)

    def set_data(self, value: List[NestedListRootItem]):
        self._items = value
        self._selected_root = self._selected_leaf = self._selected_intermediate_node = (0 if self._require_full_selection
                                                                                        else -1)
        self.root_items_changed.emit(self._map_root_items(self._items), self._row_index(0 if self._require_full_selection else -2))
        self.intermediate_items_changed.emit([], self._row_index(0 if self._require_full_selection else -1))
        self.leafs_changed.emit([], self._row_index(0 if self._require_full_selection else -1))
        self.result_changed.emit(self.result)

        if self._require_full_selection:
            # Just to populate sub-lists, as we just set them to empty QStringList() before...
            self.root_item_selection_changed.emit(self._selected_root)

    @property
    @abstractmethod
    def result(self) -> str:
        pass

    def _row_index(self, row: int) -> QModelIndex:
        return self.createIndex(row if self._require_full_selection else row + 1, 0)

    def _map_root_items(self, items: List[NestedListRootItem]) -> List[str]:
        return list(map(operator.attrgetter('name'), items))

    def _map_intermediate_items(self, item: NestedListRootItem) -> List[str]:
        names: List[str] = []
        if not self._require_full_selection:
            names.append('-')
        names.extend(map(operator.attrgetter('name'), item.children))
        return names

    def _map_leaf_items(self, item: NestedListSubItem) -> List[str]:
        names = copy(item.children)
        if not self._require_full_selection:
            names.insert(0, '-')
        return names


class DeviceListModel(AbstractNestedStringListModel):

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(require_full_selection=False, parent=parent)

    def select_device(self, index: int):
        self.root_items_changed.emit(self._map_root_items(self._items), self.createIndex(index, 0))
        self.root_item_selection_changed(index)

    @property
    def result(self) -> str:
        if self._selected_root < 0 or self._selected_root >= len(self._items):
            return ''
        item = self._items[self._selected_root]
        result = ControlEndpointAddress(device=item.name, prop='')
        if self._selected_intermediate_node >= 0:
            sub_item = item.children[self._selected_intermediate_node]
            result.property = sub_item.name
            if self._selected_leaf >= 0:
                result.field = sub_item.children[self._selected_leaf]

        return str(result)


_ccda: Optional[CCDA] = None


def get_ccda() -> CCDA:
    global _ccda
    if _ccda is None:
        _ccda = CCDA()
    return _ccda


async def _look_up_ccda(device_name: str, searched_prop: Optional[str], searched_field: Optional[str]):

    device_pages = await get_ccda().Device.search('name==*{dev}*'.format(dev=device_name))

    def map_result(dev: CCDA.Device, dev_class: CCDA.DeviceClass) -> NestedListRootItem:
        dev_obj = NestedListRootItem(name=dev.name)

        for idx, prop in enumerate(sorted(dev_class.device_class_properties, key=operator.attrgetter('name'))):
            fields = sorted((field.name for field in prop.data_fields))
            try:
                selected_field = fields.index(searched_field) if searched_field is not None else -1
            except ValueError:
                selected_field = -1
            child = NestedListSubItem(name=prop.name, children=fields, selected_child=selected_field)
            if searched_prop is not None and prop.name == searched_prop:
                dev_obj.selected_child = idx
            dev_obj.children.append(child)

        return dev_obj

    return [map_result(dev=device, dev_class=await device.device_class())
            async for device in device_pages]


def look_up_ccda(device_name: str, searched_prop: Optional[str], searched_field: Optional[str]) -> Future:
    return ensure_future(_look_up_ccda(device_name, searched_prop, searched_field))
