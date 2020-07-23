"""Encoders for MongoDB"""
import abc
from enum import Enum
from typing import Dict, List, Union


class AbstractMongoDBEncoder(abc.ABC):
    """Abstract MongoDB encoder"""

    @abc.abstractmethod
    def __call__(self, data: Dict) -> Dict:
        """Convert data from pydantic model or dict to dict supported MongoDB"""
        raise NotImplementedError()


def _convert_enums(data: Union[Dict, List]) -> Union[Dict, List]:
    """
    Convert Enum to Enum.value for mongo query

    Note: May be this solution not good
    """
    # Convert in dict
    _data = []
    iterator = enumerate(data)
    append = lambda k, v: _data.append(v)  # noqa: E731
    if isinstance(data, dict):
        iterator = data.items()
        _data = {}
        append = lambda k, v: _data.update({k: v})  # noqa: E731
    # Convert in list
    # Iterate passed data
    for k, v in iterator:
        # Replace enum object to enum value
        if isinstance(v, Enum):
            v = v.value
        # Recursive call if find sequence
        if isinstance(v, (list, dict)):
            v = _convert_enums(v)
        # Update new data with update method (append for list and update for dict)
        append(k, v)
    # Return new data
    return _data


class BaseMongoDBEncoder(AbstractMongoDBEncoder):
    """Base MongoDB encoder"""

    def __call__(self, data: Dict) -> Dict:
        data = _convert_enums(data)
        return data
