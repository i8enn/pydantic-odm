"""Tests for pydantic models mixins"""
import re
from datetime import datetime
from typing import List, Optional

import pytest
from bson import ObjectId
from motor import motor_asyncio
from pydantic import BaseModel
from pymongo.collection import ReturnDocument

from pydantic_odm import mixins

pytestmark = pytest.mark.asyncio


class ExampleModel(mixins.DBPydanticMixin):
    title: str
    created: datetime
    age: int

    class Config:
        database = 'default'
        collection = 'test_collection'


class ExampleEmbeddedModel(mixins.BaseDBMixin):
    title: str
    timestamp: datetime
    parent: Optional[List[mixins.BaseDBMixin]] = list()


class ExampleNestedModel(mixins.DBPydanticMixin):
    username: str
    info: ExampleModel = None
    comments: Optional[List[ExampleEmbeddedModel]]

    class Config:
        database = 'default'
        collection = 'test_example_nested'


class ExampleModelInUpdate(BaseModel):
    """Scheme (serializer) for update example model"""

    title: Optional[str]
    created: Optional[datetime]
    age: Optional[int]


class TestBaseDBMixin(mixins.BaseDBMixin):
    async def test__update_model_from__doc(self):
        example_model = ExampleEmbeddedModel(
            title='Test comment #1', timestamp=datetime.now()
        )
        example_model._doc = {'title': 'Test comment #1'}
        example_model._update_model_from__doc()
        assert example_model._doc == example_model.dict()

        # Nested model
        nested_model = ExampleNestedModel(username='test_user')
        nested_model._doc = {
            'username': 'new_test_user',
            'comments': [
                {'title': 'Newest title from db', 'timestamp': example_model.timestamp,}
            ],
        }
        nested_model._update_model_from__doc()
        assert nested_model._doc == nested_model.dict()
        assert nested_model.comments[0] == example_model


class TestDBPydanticMixin:
    async def test_exclude__doc_from_dict(self):
        example_model = ExampleModel(title='test', created=datetime.now(), age=10)
        example_model._doc = {
            'title': example_model.title,
            'created': example_model.created,
            'age': example_model.age,
        }
        example_model_as_dict = example_model.dict()
        assert '_doc' not in example_model_as_dict.keys()
        assert example_model_as_dict == example_model._doc

    async def test_jsonable_model(self, init_test_db):
        example_model = ExampleModel(title='test', created=datetime.now(), age=10)
        example_model._id = ObjectId()
        assert isinstance(example_model._id, ObjectId)
        assert example_model.json()

    async def test_get_collection(self, init_test_db, monkeypatch):
        col = await ExampleModel.get_collection()
        assert isinstance(col, motor_asyncio.AsyncIOMotorCollection)

    async def test_get_collection_in_unconfigured_config(
        self, init_test_db, monkeypatch
    ):
        monkeypatch.delattr(ExampleModel.Config, 'database')
        monkeypatch.delattr(ExampleModel.Config, 'collection')
        raise_msg = 'Collection or db_name is not configured in Config class'
        with pytest.raises(ValueError, match=raise_msg):
            _ = await ExampleModel.get_collection()

        monkeypatch.undo()

    async def test_get_collection_with_unconfigured_db(self, init_test_db, monkeypatch):
        db_name = 'unconfigured'
        monkeypatch.setattr(ExampleModel.Config, 'database', db_name)
        raise_msg = '"%s" is not found in MongoDBManager.database' % db_name
        with pytest.raises(ValueError, match=raise_msg):
            _ = await ExampleModel.get_collection()
        monkeypatch.undo()

    async def test_save_model_with_new_doc(self, init_test_db):
        model_data = {'title': 'Test title', 'created': datetime.now(), 'age': 10}
        exmpl_model = ExampleModel(**model_data)
        assert exmpl_model
        assert exmpl_model.title == model_data['title']
        assert exmpl_model.created == model_data['created']
        assert exmpl_model.age == model_data['age']

        assert not exmpl_model._id
        assert not exmpl_model._doc
        await exmpl_model.save()
        assert exmpl_model
        doc = exmpl_model._doc
        assert doc.get('_id') == exmpl_model._id
        assert doc.get('title') == exmpl_model.title
        assert doc.get('created') == exmpl_model.created
        assert doc.get('age') == exmpl_model.age

    async def test_save_model_with_created_doc(self, init_test_db):
        model_data = {'title': 'Test title', 'created': datetime.now(), 'age': 10}
        exmpl_model = ExampleModel(**model_data)
        await exmpl_model.save()
        assert exmpl_model
        id = exmpl_model._id

        new_title = 'New test title'
        exmpl_model.title = new_title
        await exmpl_model.save()
        assert exmpl_model.title == new_title
        assert exmpl_model._doc.get('title') == new_title
        assert exmpl_model._doc.get('_id') == exmpl_model._id
        assert exmpl_model._id == id

    async def test_save_nested_model(self, init_test_db):
        model_data = {'title': 'Test title', 'created': datetime.now(), 'age': 10}
        exmpl_model = ExampleModel(**model_data)
        assert exmpl_model

        nested_model = ExampleNestedModel(username='test', info=exmpl_model)
        assert nested_model
        assert nested_model.info == exmpl_model

        await nested_model.save()

        doc = nested_model._doc
        assert doc.get('username') == 'test'
        assert doc.get('info') == model_data

    async def test_create(self, init_test_db):
        model_data = {'title': 'Test title', 'created': datetime.now(), 'age': 10}
        # With dict
        model = await ExampleModel.create(model_data)
        assert model
        assert model._id
        assert model._doc.keys() == model.dict().keys()
        assert model.title == model_data['title']
        assert model.created == model_data['created']
        assert model.age == model_data['age']

        # With pydantic model
        model = await ExampleModel.create(ExampleModelInUpdate.parse_obj(model_data))
        assert model
        assert model._id
        assert model._doc.keys() == model.dict().keys()
        assert model.title == model_data['title']
        assert model.created == model_data['created']
        assert model.age == model_data['age']

    async def test_count(self, init_test_db):
        models = [
            ExampleModel(title='Model #%d' % i, created=datetime.now(), age=i)
            for i in range(1, 6)
        ]
        await ExampleModel.bulk_create(models[0:3])
        assert await ExampleModel.count() == 3
        await ExampleModel.bulk_create(models[3::])
        assert await ExampleModel.count() == 5

    async def test_find_one(self, init_test_db):
        model_data = {
            'title': 'Test title',
            'created': datetime.utcnow().isoformat(),
            'age': 10,
        }
        exmpl_model = ExampleModel(**model_data)
        await exmpl_model.save()

        result = await ExampleModel.find_one({'_id': exmpl_model._id})
        assert result

        assert result._id
        assert result._doc.keys() == exmpl_model.dict().keys()
        assert exmpl_model.title == result.title
        assert exmpl_model.created.date() == result.created.date()
        assert exmpl_model.age == result.age

    async def test_find_one_with_empty_result(self, init_test_db):
        result = await ExampleModel.find_one({'_id': 'undefined_id'})
        assert not result

    async def test_bulk_create(self, init_test_db):
        models = [
            ExampleModel(title='Model #%d' % i, created=datetime.now(), age=i)
            for i in range(1, 5)
        ]
        # With model
        saved_models = await ExampleModel.bulk_create(models)
        assert saved_models
        for model in saved_models:
            assert isinstance(model, ExampleModel)
            assert model._id
            assert model._doc == model.dict()
        # With dict
        saved_models = await ExampleModel.bulk_create([d.dict() for d in models])
        assert saved_models
        for model in saved_models:
            assert isinstance(model, ExampleModel)
            assert model._id
            assert model._doc == model.dict()

    async def test_find_many(self, init_test_db):
        models = [
            ExampleModel(title='Model #%d' % i, created=datetime.now(), age=i)
            for i in range(1, 5)
        ]
        await ExampleModel.bulk_create(models)

        query = {'title': {'$regex': re.compile('[0-3]', re.IGNORECASE)}}
        result = await ExampleModel.find_many(query)
        assert result
        assert len(result) == 3

        for document in result:
            assert isinstance(document, ExampleModel)
            assert document._id
            assert document._doc == document.dict()

    async def test_update(self, init_test_db):
        model_data = {
            'title': 'Test title',
            'created': datetime.utcnow().isoformat(),
            'age': 10,
        }
        example_model = ExampleModel(**model_data)
        await example_model.save()
        assert example_model

        update_data = {'title': 'New Test Title', 'age': None}
        updated_model = await example_model.update(update_data)
        assert updated_model.title == update_data['title']
        assert updated_model.age == update_data['age']
        assert updated_model.created == example_model.created

        update_data = {'title': 'Title from Pydantic'}
        pydantic_updated_data = ExampleModelInUpdate.parse_obj(update_data)
        old_updated_model = updated_model
        updated_model = await example_model.update(pydantic_updated_data)
        assert updated_model.title == update_data['title']
        assert updated_model.age == old_updated_model.age
        assert updated_model.created == old_updated_model.created

        # Without model._id
        example_model._id = None
        raise_msg = 'Not found _id in current model instance'
        with pytest.raises(ValueError, match=raise_msg):
            await example_model.reload()

    async def test_reload_model(self, init_test_db):
        model_data = {
            'title': 'Test title',
            'created': datetime.utcnow().isoformat(),
            'age': 10,
        }
        example_model = ExampleModel(**model_data)
        await example_model.save()

        # Change document in db without model
        collection = await example_model.get_collection()
        new_example_model = await collection.find_one_and_update(
            {'_id': example_model._id},
            {'$set': {'title': 'New test title'}},
            return_document=ReturnDocument.AFTER,
        )
        assert new_example_model
        assert example_model.title != new_example_model['title']

        reloaded_model = await example_model.reload()
        assert reloaded_model == example_model
        assert reloaded_model.title == new_example_model['title']

        # Without model._id
        example_model._id = None
        raise_msg = 'Not found _id in current model instance'
        with pytest.raises(ValueError, match=raise_msg):
            await example_model.reload()

    async def test_delete(self, init_test_db):
        model_data = {
            'title': 'Test title',
            'created': datetime.utcnow().isoformat(),
            'age': 10,
        }
        example_model = ExampleModel(**model_data)
        await example_model.save()

        await example_model.delete()

        assert not example_model._doc
        assert not await example_model.find_one({'_id': example_model._id})

        # Without model._id
        example_model._id = None
        raise_msg = 'Not found _id in current model instance'
        with pytest.raises(ValueError, match=raise_msg):
            await example_model.reload()
