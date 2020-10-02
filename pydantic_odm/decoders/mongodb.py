"""MongoDB decoders"""
from __future__ import annotations

import abc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic.typing import DictStrAny


class AbstractMongoDBDecoder(abc.ABC):
    """Abstract MongoDB decoder"""

    @abc.abstractmethod
    def __call__(self, data: "DictStrAny") -> "DictStrAny":
        """Main mongodb encoder func"""
        raise NotImplementedError()


class BaseMongoDBDecoder(AbstractMongoDBDecoder):
    """Base MongoDB decoder"""

    def __call__(self, data: "DictStrAny") -> "DictStrAny":
        """
        Decode mongodb document.

        Rename field `_id` to `id`.
        """
        data = data.copy()
        data.pop("id", None)
        document_id = data.pop("_id", None)
        decoded_data = {"id": document_id}
        for k, v in data.items():
            if isinstance(v, list):
                v_list = []
                for item in v:
                    if isinstance(item, dict):
                        item = self.__call__(item)
                    v_list.append(item)
                decoded_data[k] = v_list
            elif isinstance(v, dict):
                decoded_data[k] = self.__call__(v)
            else:
                decoded_data[k] = v
        return decoded_data
