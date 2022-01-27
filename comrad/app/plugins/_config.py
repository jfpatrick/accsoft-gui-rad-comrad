from collections import defaultdict
from typing import Optional, Dict, Tuple, Iterable, Any, Union, List


class WindowPluginConfigTrie:

    def __init__(self):
        super().__init__()

        def recursive_factory():
            return defaultdict(recursive_factory)

        self.root = defaultdict(recursive_factory)

    def add_val(self, key: str, val: str):
        if not key:
            raise KeyError
        node = self.root
        components = key.split('.')
        last_comp = components.pop()
        for comp in components:
            node = node[comp]
            if not isinstance(node, dict):
                raise KeyError
        node[last_comp] = _split_list_and_strip_quotes(val)

    def get_flat_config(self, prefix: str) -> Optional[Dict[str, str]]:
        if not prefix:
            return None
        node = self.root
        for comp in prefix.split('.'):
            if not comp:
                return None
            node = node[comp]
            if not isinstance(node, dict):
                return None

        def get_next_item(node: Dict[str, Any],
                          key_prefix: Optional[str] = None) -> Iterable[Tuple[str, str]]:
            for node_key, node_val in node.items():
                node_abs_key = node_key if key_prefix is None else '.'.join([key_prefix, node_key])
                if isinstance(node_val, dict):
                    for next_key, next_val in get_next_item(node=node_val, key_prefix=node_abs_key):
                        yield next_key, next_val
                else:
                    yield node_abs_key, node_val

        return dict(list(get_next_item(node))) or None


def _split_list_and_strip_quotes(value: str) -> Union[str, List[str]]:
    res = value.split(',')
    if len(res) == 1:
        return _strip_quotes(value)
    return list(map(_strip_quotes, res))


def _strip_quotes(value: str) -> str:
    if len(value) > 1 and (value[0] == '"' and value[-1] == '"' or value[0] == "'" and value[-1] == "'"):
        return value[1:-1]
    return value
