"""MongoDB decoders"""
import abc
from typing import Dict


class AbstractMongoDBDecoder(abc.ABC):
    """Abstract MongoDB decoder"""

    @abc.abstractmethod
    def __call__(self, data: Dict) -> Dict:
        """Main mongodb encoder func"""
        raise NotImplementedError()


class BaseMongoDBDecoder(AbstractMongoDBDecoder):
    """Base MongoDB decoder"""

    def __call__(self, data: Dict) -> Dict:
        """
        Decode mongodb document.

        Rename field `_id` to `id`.
        """
        data = data.copy()
        data.pop('id', None)
        id = data.pop('_id', None)
        decoded_data = {'id': id}
        for k, v in data.items():
            if isinstance(v, list):
                v_list = []
                for item in v:
                    v_list.append(self.__call__(item))
                decoded_data[k] = v_list
            elif isinstance(v, dict):
                decoded_data[k] = self.__call__(v)
            else:
                decoded_data[k] = v
        return decoded_data
