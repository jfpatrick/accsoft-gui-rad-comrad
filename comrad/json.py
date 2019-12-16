import logging
from abc import ABCMeta, abstractmethod
from typing import Dict, Any, TypeVar, Type, cast
from json import JSONEncoder
from enum import Enum


logger = logging.getLogger(__name__)


_T = TypeVar('_T', bound='JSONSerializable')


class JSONDeserializeError(ValueError):
    """Custom error when JSON deserialization fails (not due to bad JSON syntax but rather unexpected composition)."""
    pass


class JSONSerializable(metaclass=ABCMeta):
    """Instances of this class are able to be serialized into JSON string and also deserialized from it."""

    @classmethod
    @abstractmethod
    def from_json(cls: Type[_T], contents: Dict[str, Any]) -> _T:
        """
        Factory to construct the rule from JSON.

        Args:
            contents: JSON dictionary that has been parsed by `json.loads`.

        Returns:
            New object.

        Raises:
            JSONDeserializeError: when parsing fails.
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
    """
    Custom encoder that detects :class:`JSONSerializable` objects and
    serializes them to JSON string appropriately.
    """

    def default(self, o: object) -> Dict[str, Any]:
        if isinstance(o, JSONSerializable):
            logger.debug(f'Encoding serializable ComRAD object: {o}')
            return cast(JSONSerializable, o).to_json()
        elif isinstance(o, Enum):
            return cast(Enum, o).value
        return JSONEncoder.default(self, o)
