"""Mixins for pydantic models"""
from __future__ import annotations

import abc
from bson import ObjectId
from motor import motor_asyncio
from pydantic import BaseModel
from pymongo.collection import Collection, ReturnDocument
from typing import TYPE_CHECKING, Any, List, Optional, Union, cast

from .db import get_db_manager
from .decoders.mongodb import AbstractMongoDBDecoder, BaseMongoDBDecoder
from .encoders.mongodb import AbstractMongoDBEncoder, BaseMongoDBEncoder
from .types import ObjectIdStr

if TYPE_CHECKING:
    from pydantic.typing import MappingIntStrAny  # isort: skip
    from pydantic.typing import AbstractSetIntStr, DictAny, DictIntStrAny, DictStrAny


class BaseDBMixin(BaseModel, abc.ABC):
    """Base class for Pydantic mixins"""

    id: Optional[ObjectIdStr] = None

    # Read-only (for public) field for store MongoDB id
    _doc: "DictAny" = {}

    # Encoders and decoders
    _mongodb_encoder: AbstractMongoDBEncoder = BaseMongoDBEncoder()
    _mongo_decoder: AbstractMongoDBDecoder = BaseMongoDBDecoder()

    class Config:
        allow_population_by_field_name = True
        json_encoders: "DictAny" = {ObjectId: lambda v: ObjectIdStr(v)}

    def __setattr__(self, key: Any, value: Any) -> Any:
        if key not in ["_doc"]:
            return super(BaseDBMixin, self).__setattr__(key, value)
        self.__dict__[key] = value
        return value

    @classmethod
    def _decode_mongo_documents(cls, document: "DictStrAny") -> "DictStrAny":
        """Decode and return MongoDB documents"""
        return cls._mongo_decoder(document)

    @classmethod
    def _encode_dict_to_mongo(cls, data: "DictStrAny") -> "DictStrAny":
        """Encode any dict to mongo query"""
        return cls._mongodb_encoder(data)

    def _encode_model_to_mongo(
        self,
        include: Union["AbstractSetIntStr", "DictIntStrAny"] = None,
        exclude: Union["AbstractSetIntStr", "DictIntStrAny"] = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> DictStrAny:
        """Encode model to mongo query like pydantic.dict()"""
        model_as_dict = self.dict(
            include=include,
            exclude=exclude,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )
        return self._mongodb_encoder(model_as_dict)

    def dict(
        self,
        *,
        include: Union["AbstractSetIntStr", "MappingIntStrAny"] = None,
        exclude: Union["AbstractSetIntStr", "MappingIntStrAny"] = None,
        by_alias: bool = False,
        skip_defaults: bool = None,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> DictStrAny:
        # Remove internal fields from serialized result
        if not exclude:
            exclude = {"_doc"}
        else:
            exclude = {"_doc", *exclude}

        return super(BaseDBMixin, self).dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )

    def _update_model_from__doc(self) -> BaseDBMixin:
        """
        Update model fields from _doc dictionary
        (projection of a document from DB)
        """
        new_obj = self.parse_obj(self._doc)
        new_obj.id = self._doc.get("id")
        for k, field in new_obj.__fields__.items():
            field_default = getattr(field, "default", None)
            self.__dict__[k] = getattr(new_obj, k, field_default)
        return new_obj


class DBPydanticMixin(BaseDBMixin):
    """Help class for communicate of Pydantic model and MongoDB"""

    class Config:
        # DB
        collection: Optional[str] = None
        database: Optional[str] = None

    @classmethod
    async def get_collection(cls) -> Collection:
        db_name = getattr(cls.Config, "database", None)
        collection_name = getattr(cls.Config, "collection", None)
        if not db_name or not collection_name:
            raise ValueError("Collection or db_name is not configured in Config class")
        db_manager = get_db_manager()
        if not db_manager:
            raise RuntimeError("MongoDBManager not initialized")
        db = db_manager[db_name]
        if not db:
            raise ValueError('"%s" is not found in MongoDBManager.databases' % db_name)

        collection = db[collection_name]
        if not collection:
            collection = await db.create_collection(collection_name)
        return collection

    @staticmethod
    async def pre_save_validation(
        data: Union["DictAny", List["DictAny"]], many: bool = False
    ) -> Union["DictAny", List["DictAny"]]:
        """
        Async validation before save data to DB

        For use this method - override him in your model.
        You can also serializing data by returning a modified
        data dictionary (but I don't recommend).

        "many" flag will inform you about a mass operation.

        Called before:
            - create (with save)
            - update
            - save
            - bulk create
            - bulk update

        Usage example:

            class YourModel(DBPydanticMixin):
                other_model_id: ObjectIdStr

                async def validation(
                        data: Union["DictAny", List["DictAny"]], many: bool = False
                ) -> Union["DictAny", List["DictAny"]]:
                    other_model = await OtherModel.find_one({
                        '_id': data.get('other_model_id')
                    })
                    if not other_model:
                        raise TypeError(f'Other model with `{id}` id not found')
                    return data
        """
        return data

    @classmethod
    async def create(cls, fields: Union["DictAny", BaseModel]) -> DBPydanticMixin:
        """Create document by dict or pydantic model"""
        if isinstance(fields, BaseModel):
            fields = fields.dict(exclude_unset=True)
        document = cls.parse_obj(fields)
        await document.save()
        return document

    @classmethod
    async def count(cls, query: DictStrAny = None) -> int:
        """Return count by query or all documents in collection"""
        if not query:
            query = {}
        query = cls._encode_dict_to_mongo(query)
        collection = await cls.get_collection()
        return await collection.count_documents(query)

    @classmethod
    async def find_one(cls, query: DictStrAny) -> DBPydanticMixin:
        """Find and return model from db by pymongo query"""
        collection = await cls.get_collection()
        query = cls._encode_dict_to_mongo(query)
        result = await collection.find_one(query)
        if result:
            result = cls._decode_mongo_documents(result)
            model = cls.parse_obj(result)
            document_id = result.get("id")
            model._doc = result
            model.id = document_id
            return model
        return result

    @classmethod
    async def find_many(
        cls, query: "DictStrAny", return_cursor: bool = False
    ) -> Union[List[DBPydanticMixin], motor_asyncio.AsyncIOMotorCursor]:
        """
        Find documents by query and return list of model instances
        or query cursor
        """
        collection = await cls.get_collection()
        query = cls._encode_dict_to_mongo(query)
        cursor = collection.find(query)
        if return_cursor:
            return cursor

        documents = []
        async for _doc in cursor:
            _doc = cls._decode_mongo_documents(_doc)
            document = cls.parse_obj(_doc)
            document._doc = _doc
            documents.append(document)
        return documents

    @classmethod
    async def update_many(
        cls, query: "DictStrAny", fields: "DictAny", return_cursor: bool = False,
    ) -> Union[List[DBPydanticMixin], motor_asyncio.AsyncIOMotorCursor]:
        """
        Find and update documents by query
        """
        await cls.pre_save_validation(fields, many=True)
        collection = await cls.get_collection()
        query = cls._encode_dict_to_mongo(query)
        await collection.update_many(query, fields)
        return await cls.find_many(query, return_cursor)

    @classmethod
    async def bulk_create(
        cls, documents: Union[List[BaseModel], List["DictAny"]],
    ) -> List[DBPydanticMixin]:
        """Create many documents"""
        collection = await cls.get_collection()

        if not documents:
            return []

        if isinstance(documents[0], BaseModel):
            documents = [
                cls._encode_dict_to_mongo(d.dict())
                for d in cast(List[BaseModel], documents)  # noqa: types
            ]

        documents = cast(List["DictAny"], documents)  # noqa: types
        await cls.pre_save_validation(documents, many=True)

        result = await collection.insert_many(documents)
        inserted_ids = result.inserted_ids
        inserted_documents = []
        for i, document_id in enumerate(inserted_ids):
            document = cls.parse_obj(documents[i])
            document.id = document_id
            document._doc = cls._decode_mongo_documents(documents[i])
            inserted_documents.append(document)
        return inserted_documents

    async def reload(self) -> DBPydanticMixin:
        """Reload model data from MongoDB (get new document from db)"""
        collection = await self.get_collection()
        if not self.id:
            raise ValueError("Not found id in current model instance")
        _doc = await collection.find_one({"_id": self.id})
        if _doc:
            self._doc = self._decode_mongo_documents(_doc)
            self._update_model_from__doc()
        return self

    async def update(self, fields: Union[BaseModel, "DictAny"],) -> DBPydanticMixin:
        """
        Update Mongo document and pydantic instance.

        Parameters:
            - `fields`: updating fields (Pydantic model or dict)
        """
        if isinstance(fields, BaseModel):
            fields = fields.dict(exclude_unset=True)
        await self.pre_save_validation(fields)
        collection = await self.get_collection()
        if not self.id:
            raise ValueError("Not found id in current model instance")
        fields = self._encode_dict_to_mongo(fields)
        _doc = await collection.find_one_and_update(
            {"_id": self.id}, {"$set": fields}, return_document=ReturnDocument.AFTER
        )
        if _doc:
            self._doc.update(self._decode_mongo_documents(_doc))
            self._update_model_from__doc()
        return self

    async def save(self) -> DBPydanticMixin:
        collection = await self.get_collection()
        if not self.id:
            data = self._encode_model_to_mongo()
            await self.pre_save_validation(data)
            instance = await collection.insert_one(data)
            if instance:
                self.id = instance.inserted_id
                self._doc = {"id": self.id, **self.dict()}
        else:
            updated = {}
            data = self._encode_model_to_mongo(exclude={"id"})
            await self.pre_save_validation(data)
            for field, value in data.items():
                if self._doc.get(field) != value:
                    updated[field] = value
            if updated:
                instance = await collection.update_one(
                    {"_id": self.id}, {"$set": updated}
                )
                if instance:
                    self._doc.update(updated)
        return self

    async def delete(self) -> int:
        """Delete document from db"""
        collection = await self.get_collection()
        if not self.id:
            raise ValueError("Not found id in current model instance")
        result = await collection.delete_one({"_id": self.id})
        self._doc = {}
        return result.deleted_count
