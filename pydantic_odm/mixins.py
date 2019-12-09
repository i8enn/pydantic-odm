"""Mixins for pydantic models"""
from __future__ import annotations

from typing import List, Dict, Union, TYPE_CHECKING, Any, AbstractSet

from motor import motor_asyncio
from bson import ObjectId
from pydantic import BaseModel
from pymongo.collection import Collection, ReturnDocument

from .types import ObjectIdStr
from .db import MongoDBManager

if TYPE_CHECKING:
    IntStr = Union[int, str]
    AbstractSetIntStr = AbstractSet[IntStr]
    DictAny = Dict[Any, Any]
    DictStrAny = Dict[str, Any]
    DictIntStrAny = Dict[IntStr, Any]


class DBPydanticMixin(BaseModel):
    """Help class for communicate of Pydantic model and MongoDB"""
    _id: ObjectIdStr = None
    _doc: Dict = None

    class Config:
        # DB
        collection: str = None
        database: str = None
        json_encoders = {
            ObjectId: lambda v: ObjectIdStr(v)
        }

    def __setattr__(self, key, value):
        if key not in ['_id', '_doc']:
            return super(DBPydanticMixin, self).__setattr__(key, value)
        self.__dict__[key] = value
        return value

    def dict(
        self,
        *,
        include: Union[AbstractSetIntStr, DictIntStrAny] = None,
        exclude: Union[AbstractSetIntStr, DictIntStrAny] = None,
        by_alias: bool = False,
        skip_defaults: bool = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False
    ) -> DictStrAny:
        return super(DBPydanticMixin, self).dict(exclude={'_doc'})

    @classmethod
    async def get_collection(cls) -> Collection:
        db_name = getattr(cls.Config, 'database', None)
        collection_name = getattr(cls.Config, 'collection', None)
        if not db_name or not collection_name:
            raise ValueError(
                'Collection or db_name is not configured in Config class'
            )
        db = MongoDBManager[db_name]
        if not db:
            raise ValueError(
                '"%s" is not found in MongoDBManager.databases' % db_name
            )

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
        collection = await cls.get_collection()
        return await collection.count_documents(query)

    @classmethod
    async def find_one(cls, query: Dict) -> DBPydanticMixin:
        """Find and return model from db by pymongo query"""
        collection = await cls.get_collection()
        result = await collection.find_one(query)
        if result:
            model = cls.parse_obj(result)
            model._doc = result
            model._id = result['_id']
            return model
        return result

    @classmethod
    async def find_many(
            cls,
            query: Dict[str, Dict[str, Any]],
            return_cursor: bool = False
    ) -> Union[List[DBPydanticMixin], motor_asyncio.AsyncIOMotorCursor]:
        """
        Find documents by query and return list of model instances
        or query cursor
        """
        collection = await cls.get_collection()
        cursor = collection.find(query)
        if return_cursor:
            return cursor

        documents = []
        async for _doc in cursor:
            document = cls.parse_obj(_doc)
            document._id = _doc['_id']
            document._doc = _doc
            documents.append(document)
        return documents

    @classmethod
    async def bulk_create(
            cls,
            documents: Union[List[BaseModel], List[Dict]],
    ) -> List[DBPydanticMixin]:
        """Create many documents"""
        collection = await cls.get_collection()
        if not documents:
            return []
        if isinstance(documents[0], BaseModel):
            documents = [d.dict() for d in documents]

        result = await collection.insert_many(documents)
        inserted_ids = result.inserted_ids
        inserted_documents = []
        for i, document_id in enumerate(inserted_ids):
            document = cls.parse_obj(documents[i])
            document._id = document_id
            document._doc = documents[i]
            inserted_documents.append(document)
        return inserted_documents

    def _update_model_from__doc(self) -> DBPydanticMixin:
        """
        Update model fields from _doc dictionary
        (projection of a document from DB)
        """
        for field in self.__fields__.keys():
            setattr(self, field, self._doc.get(field))
        return self

    async def reload(self) -> DBPydanticMixin:
        """Reload model data from MongoDB (get new document from db)"""
        collection = await self.get_collection()
        if not self._id:
            raise ValueError('Not found _id in current model instance')
        _doc = await collection.find_one({'_id': self._id})
        if _doc:
            self._doc = _doc
            self._update_model_from__doc()
        return self

    async def update(
            self,
            fields: Union[BaseModel, Dict],
    ) -> DBPydanticMixin:
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
        _doc = await collection.find_one_and_update(
            {'_id': self._id},
            {'$set': fields},
            return_document=ReturnDocument.AFTER
        )
        if _doc:
            self._doc.update(_doc)
            self._update_model_from__doc()
        return self

    async def save(self) -> DBPydanticMixin:
        collection = await self.get_collection()
        if not self._id:
            instance = await collection.insert_one(self.dict())
            if instance:
                self._id = instance.inserted_id
                self._doc = {
                    '_id': self._id,
                    **self.dict()
                }
        else:
            updated = {}
            for field, value in self.dict().items():
                if self._doc.get(field) != value:
                    updated[field] = value
            if updated:
                instance = await collection.update_one(
                    {'_id': self._id},
                    {'$set': updated}
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
