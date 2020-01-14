import logging
from abc import ABCMeta, abstractmethod
from typing import Dict, Any, TypeVar, Type, cast
from json import JSONEncoder
from enum import Enum


logger = logging.getLogger(__name__)


_T = TypeVar('_T', bound='CJSONSerializable')


class CJSONDeserializeError(ValueError):
    """Custom error when JSON deserialization fails (not due to bad JSON syntax but rather unexpected composition)."""
    pass


class CJSONSerializable(metaclass=ABCMeta):
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
            json.JSONDecodeError: invalid JSON format.
            CJSONDeserializeError: when parsing fails due to incorrect object structure.
        """
        pass

    @abstractmethod
    def to_json(self) -> Dict[str, Any]:
        """
        Encode the object as JSON.

        Returns:
            JSON dictionary, that can be placed into :func:`json.dumps`.
        """
        pass


class CJSONEncoder(JSONEncoder):
    """
    Custom encoder that detects :class:`CJSONSerializable` objects and
    serializes them to JSON string appropriately.
    """

    def default(self, o: object) -> Dict[str, Any]:
        if isinstance(o, CJSONSerializable):
            logger.debug(f'Encoding serializable ComRAD object: {o}')
            return cast(CJSONSerializable, o).to_json()
        elif isinstance(o, Enum):
            return cast(Enum, o).value
        return JSONEncoder.default(self, o)
