"""Encoders for MongoDB"""
from __future__ import annotations

import abc
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, List, Union, cast

if TYPE_CHECKING:
    from pydantic.typing import DictStrAny


class AbstractMongoDBEncoder(abc.ABC):
    """Abstract MongoDB encoder"""

    @abc.abstractmethod
    def __call__(self, data: "DictStrAny") -> "DictStrAny":
        """Convert data from pydantic model or dict to dict supported MongoDB"""
        raise NotImplementedError()


def _convert_enums(
    data: Union["DictStrAny", List[Any]]
) -> Union["DictStrAny", List[Any]]:
    """
    Convert Enum to Enum.value for mongo query

    Note: May be this solution not good
    """
    # Cast append func type
    append: Callable[[Union[str, int], Any], None]
    # Convert in list
    data = cast(List[Any], data)  # noqa
    _data = []
    iterator = enumerate(data)
    append = lambda k, v: _data.append(v)  # noqa: E731
    # Convert in dict
    if isinstance(data, dict):
        data = cast("DictStrAny", data)
        iterator = data.items()
        _data = {}
        append = lambda k, v: _data.update({k: v})  # noqa: E731
    # Iterate passed data
    for key, value in iterator:
        # Replace enum object to enum value
        if isinstance(value, Enum):
            value = value.value
        # Recursive call if find sequence
        if isinstance(value, (list, dict)):
            value = _convert_enums(value)
        # Update new data with update method (append for list and update for dict)
        append(key, value)
    # Return new data
    return _data


class BaseMongoDBEncoder(AbstractMongoDBEncoder):
    """Base MongoDB encoder"""

    def __call__(self, data: "DictStrAny") -> "DictStrAny":
        data = cast("DictStrAny", _convert_enums(data))
        return data
