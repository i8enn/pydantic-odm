"""Mixins for pydantic models"""
from __future__ import annotations

import abc
from bson import ObjectId
from enum import Enum
from motor import motor_asyncio
from pydantic import BaseModel
from pymongo.collection import Collection, ReturnDocument
from typing import TYPE_CHECKING, AbstractSet, Any, Dict, List, Union

from .db import MongoDBManager
from .types import ObjectIdStr

if TYPE_CHECKING:
    IntStr = Union[int, str]
    AbstractSetIntStr = AbstractSet[IntStr]
    DictAny = Dict[Any, Any]
    DictStrAny = Dict[str, Any]
    DictIntStrAny = Dict[IntStr, Any]


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


class BaseDBMixin(BaseModel, abc.ABC):
    """Base class for Pydantic mixins"""

    # Read-only (for public) field for store MongoDB id
    _id: ObjectIdStr = None
    _doc: Dict = {}

    class Config:
        allow_population_by_field_name = True
        schema_extra = {'id': 'str'}

    def __setattr__(self, key, value):
        if key not in ['_doc', '_id']:
            return super(BaseDBMixin, self).__setattr__(key, value)
        self.__dict__[key] = value
        return value

    @property
    def id(self) -> ObjectIdStr:
        return self._id

    def _update_model_from__doc(self) -> BaseDBMixin:
        """
        Update model fields from _doc dictionary
        (projection of a document from DB)
        """
        new_obj = self.parse_obj(self._doc)
        new_obj._id = self._doc.get('_id')
        for k, v in new_obj.__dict__.items():
            self.__dict__[k] = v
        return new_obj

    @classmethod
    def _convert_id_in_mongo_query(cls, query: Dict) -> Dict:
        _query = {}
        query = _convert_enums(query)
        for k, v in query.items():
            if k == 'id':
                _query['_id'] = v
            elif isinstance(v, dict):
                _query[k] = cls._convert_id_in_mongo_query(v)
            elif isinstance(v, (list, tuple)):
                _query[k] = [cls._convert_id_in_mongo_query(i) for i in v]
            else:
                _query[k] = v
        return _query

    def dict(
        self,
        *,
        include: Union[AbstractSetIntStr, DictIntStrAny] = None,
        exclude: Union[AbstractSetIntStr, DictIntStrAny] = None,
        by_alias: bool = False,
        skip_defaults: bool = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> DictStrAny:
        if not exclude:
            exclude = {'_doc', '_id'}
        else:
            exclude.update({'_doc', '_id'})  # noqa

        d = super(BaseDBMixin, self).dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )

        # Simulating field alias behavior
        if (not self.id and (exclude_none or exclude_defaults)) or 'id' in exclude:
            return d
        d['id'] = self.id
        return d


class DBPydanticMixin(BaseDBMixin):
    """Help class for communicate of Pydantic model and MongoDB"""

    class Config:
        # DB
        collection: str = None
        database: str = None
        json_encoders = {ObjectId: lambda v: ObjectIdStr(v)}

    @classmethod
    async def get_collection(cls) -> Collection:
        db_name = getattr(cls.Config, 'database', None)
        collection_name = getattr(cls.Config, 'collection', None)
        if not db_name or not collection_name:
            raise ValueError('Collection or db_name is not configured in Config class')
        db = MongoDBManager[db_name]
        if not db:
            raise ValueError('"%s" is not found in MongoDBManager.databases' % db_name)

        collection = db[collection_name]
        if not collection:
            collection = await db.create_collection(collection_name)
        return collection

    @classmethod
    async def create(cls, fields: Union[Dict, BaseModel]) -> DBPydanticMixin:
        """Create document by dict or pydantic model"""
        if isinstance(fields, BaseModel):
            fields = fields.dict(exclude_unset=True)
        document = cls.parse_obj(fields)
        await document.save()
        return document

    @classmethod
    async def count(cls, query: Dict = None) -> int:
        """Return count by query or all documents in collection"""
        if not query:
            query = {}
        query = cls._convert_id_in_mongo_query(query)
        collection = await cls.get_collection()
        return await collection.count_documents(query)

    @classmethod
    async def find_one(cls, query: Dict) -> DBPydanticMixin:
        """Find and return model from db by pymongo query"""
        collection = await cls.get_collection()
        query = cls._convert_id_in_mongo_query(query)
        result = await collection.find_one(query)
        if result:
            model = cls.parse_obj(result)
            model._doc = result
            model._id = result['_id']
            return model
        return result

    @classmethod
    async def find_many(
        cls, query: Dict[str, Dict[str, Any]], return_cursor: bool = False
    ) -> Union[List[DBPydanticMixin], motor_asyncio.AsyncIOMotorCursor]:
        """
        Find documents by query and return list of model instances
        or query cursor
        """
        collection = await cls.get_collection()
        query = cls._convert_id_in_mongo_query(query)
        cursor = collection.find(query)
        if return_cursor:
            return cursor

        documents = []
        async for _doc in cursor:
            document = cls.parse_obj(_doc)
            document._id = _doc.get('_id')
            document._doc = _doc
            documents.append(document)
        return documents

    @classmethod
    async def update_many(
        cls,
        query: Dict[str, Any],
        fields: Dict[str, Dict[str, Any]],
        return_cursor: bool = False,
    ) -> Union[List[DBPydanticMixin], motor_asyncio.AsyncIOMotorCursor]:
        """
        Find and update documents by query
        """
        collection = await cls.get_collection()
        query = cls._convert_id_in_mongo_query(query)
        await collection.update_many(query, fields)
        return await cls.find_many(query, return_cursor)

    @classmethod
    async def bulk_create(
        cls, documents: Union[List[BaseModel], List[Dict]],
    ) -> List[DBPydanticMixin]:
        """Create many documents"""
        collection = await cls.get_collection()
        if not documents:
            return []
        if isinstance(documents[0], BaseModel):
            documents = [_convert_enums(d.dict()) for d in documents]

        result = await collection.insert_many(documents)
        inserted_ids = result.inserted_ids
        inserted_documents = []
        for i, document_id in enumerate(inserted_ids):
            document = cls.parse_obj(documents[i])
            document._id = document_id
            document._doc = documents[i]
            inserted_documents.append(document)
        return inserted_documents

    async def reload(self) -> DBPydanticMixin:
        """Reload model data from MongoDB (get new document from db)"""
        collection = await self.get_collection()
        if not self._id:
            raise ValueError('Not found _id in current model instance')
        _doc = await collection.find_one({'_id': self._id})
        _doc.pop('_id')
        if _doc:
            self._doc = _doc
            self._update_model_from__doc()
        return self

    async def update(self, fields: Union[BaseModel, Dict],) -> DBPydanticMixin:
        """
        Update Mongo document and pydantic instance.

        Parameters:
            - `fields`: updating fields (Pydantic model or dict)
        """
        if isinstance(fields, BaseModel):
            fields = fields.dict(exclude_unset=True)
        collection = await self.get_collection()
        if not self._id:
            raise ValueError('Not found _id in current model instance')
        fields = _convert_enums(fields)
        _doc = await collection.find_one_and_update(
            {'_id': self._id}, {'$set': fields}, return_document=ReturnDocument.AFTER
        )
        if _doc:
            self._doc.update(_doc)
            self._update_model_from__doc()
        return self

    async def save(self) -> DBPydanticMixin:
        collection = await self.get_collection()
        if not self._id:
            data = _convert_enums(self.dict())
            instance = await collection.insert_one(data)
            if instance:
                self._id = instance.inserted_id
                self._doc = {'_id': instance.inserted_id, **self.dict(exclude={'id'})}
        else:
            updated = {}
            data = _convert_enums(self.dict(exclude={'id'}))
            for field, value in data.items():
                if self._doc.get(field) != value:
                    updated[field] = value
            if updated:
                instance = await collection.update_one(
                    {'_id': self._id}, {'$set': updated}
                )
                if instance:
                    self._doc.update(updated)
        return self

    async def delete(self) -> int:
        """Delete document from db"""
        collection = await self.get_collection()
        if not self._id:
            raise ValueError('Not found _id in current model instance')
        result = await collection.delete_one({'_id': self._id})
        self._doc = {}
        return result.deleted_count
