from abc import ABCMeta, abstractmethod
from typing import Dict, Any, TypeVar, Type, cast
from json import JSONEncoder


_T = TypeVar('_T', bound='JSONSerializable')


class JSONSerializable(metaclass=ABCMeta):

    @classmethod
    @abstractmethod
    def from_json(cls: Type[_T], contents: Dict[str, Any]) -> _T:
        """
        Factory to construct the rule from JSON.

        Args:
            contents: JSON dictionary that has been parsed by `json.loads`.

        Returns:
            New object.
        """
        pass

    @abstractmethod
    def to_json(self) -> Dict[str, Any]:
        """
        Encode the object as JSON.

        Returns:
            JSON dictionary, that can be placed into `json.dumps`.
        """
        pass


class ComRADJSONEncoder(JSONEncoder):

    def default(self, o: object) -> Dict[str, Any]:
        if isinstance(o, JSONSerializable):
            return cast(JSONSerializable, o).to_json()
        return JSONEncoder.default(self, o)
