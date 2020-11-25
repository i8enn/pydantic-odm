"""Tests for pydantic models mixins"""
import pytest
import re
from bson import ObjectId
from datetime import datetime, timedelta
from enum import Enum
from motor import motor_asyncio
from pydantic import BaseModel, Field
from pymongo.collection import ReturnDocument
from typing import List, Optional

from pydantic_odm import mixins

pytestmark = pytest.mark.asyncio


class UserTypesEnum(Enum):
    """Example user enum"""

    Admin = "admin"
    Manager = "manager"
    Author = "author"
    Reader = "reader"


class User(mixins.DBPydanticMixin):
    """Example user model"""

    username: str
    created: datetime
    age: Optional[int]
    type: UserTypesEnum = Field(default=UserTypesEnum.Reader)

    class Config:
        database = "default"
        collection = "test_user"


class Comment(mixins.BaseDBMixin):
    """Example comments model (for embed to post)"""

    body: str
    created: datetime
    parent: Optional[List[mixins.BaseDBMixin]] = list()


class Post(mixins.DBPydanticMixin):
    """Example post model"""

    title: str
    body: str
    author: User
    comments: Optional[List[Comment]]

    class Config:
        database = "default"
        collection = "test_post"


class UserSerializer(BaseModel):
    """Scheme (serializer) for update example model"""

    username: Optional[str]
    created: Optional[datetime]
    age: Optional[int]


class BaseDBMixinTestCase:
    @pytest.mark.parametrize(
        "include,exclude,exclude_unset,exclude_defaults,exclude_none,data,expected",
        [
            pytest.param(
                None,
                # Exclude 'id' field for temporary fix
                # of create empty id fields in models
                {"id"},
                False,
                False,
                False,
                {
                    "username": "test",
                    "created": datetime.fromisoformat(
                        datetime.now().date().isoformat()
                    ),
                    "age": 30,
                    "type": UserTypesEnum.Admin,
                },
                {
                    "username": "test",
                    "created": datetime.fromisoformat(
                        datetime.now().date().isoformat()
                    ),
                    "age": 30,
                    "type": UserTypesEnum.Admin.value,
                },
                id="simple",
            ),
            pytest.param(
                None,
                None,
                True,
                True,
                False,
                {
                    "username": "test",
                    "created": datetime.fromisoformat(
                        datetime.now().date().isoformat()
                    ),
                },
                {
                    "username": "test",
                    "created": datetime.fromisoformat(
                        datetime.now().date().isoformat()
                    ),
                },
                id="without_defaults_and_none",
            ),
        ],
    )
    async def test__encode_model_to_mongo(
        self,
        include,
        exclude,
        exclude_unset,
        exclude_defaults,
        exclude_none,
        data,
        expected,
    ):
        user = User.parse_obj(data)
        model_for_mongodb = user._encode_model_to_mongo(
            include, exclude, exclude_unset, exclude_defaults, exclude_none
        )
        assert model_for_mongodb == expected

    @pytest.mark.parametrize(
        "data,expected",
        [
            pytest.param(
                {
                    "username": "test",
                    "created": datetime.fromisoformat(
                        datetime.now().date().isoformat()
                    ),
                    "age": 30,
                    "type": UserTypesEnum.Admin,
                },
                {
                    "username": "test",
                    "created": datetime.fromisoformat(
                        datetime.now().date().isoformat()
                    ),
                    "age": 30,
                    "type": UserTypesEnum.Admin.value,
                },
                id="simple",
            ),
        ],
    )
    async def test__encode_dict_to_mongo(self, data, expected):
        user = User.parse_obj(data)
        # Exclude 'id' field for temporary fix of create empty id fields in models
        model_for_mongodb = user._encode_dict_to_mongo(user.dict(exclude={"id"}))
        assert model_for_mongodb == expected

    async def test__update_model_from__doc(self):
        # Simple model
        user = User(username="test_user", created=datetime.now(), age=10)
        user._doc = {
            "id": ObjectId(),
            "username": "new_test_user",
            "created": user.created + timedelta(days=1),
        }
        user._update_model_from__doc()
        assert user.id == user._doc.get("id")
        assert user.username == user._doc.get("username")
        assert user.created == user._doc.get("created")
        assert user.age == user._doc.get("age")

        # Nested model
        post = Post(title="test_title", body="test_body", author=user)
        post._doc = {
            "id": ObjectId(),
            "title": "new_test_title",
            "body": "new_test_body",
            "author": user._doc,
            "comments": [
                {
                    "id": ObjectId(),
                    "body": "Newest title from db",
                    "created": datetime.now(),
                },
                {
                    "id": ObjectId(),
                    "body": "Newest title from db",
                    "created": datetime.now(),
                },
            ],
        }
        post._update_model_from__doc()
        assert post.id == post._doc.get("id")
        assert post.title == post._doc.get("title")
        assert post.body == post._doc.get("body")
        author_from_doc = post._doc.get("author")
        assert ObjectId(post.author.id) == author_from_doc.get("id")
        assert post.author.username == author_from_doc.get("username")
        assert post.author.created == author_from_doc.get("created")
        assert post.author.age == author_from_doc.get("age")
        # First comment
        comment_from_doc = post._doc.get("comments", [])[0]
        assert isinstance(post.comments[0], Comment)
        assert post.comments[0].body == comment_from_doc.get("body")
        assert post.comments[0].created == comment_from_doc.get("created")
        # Second comment
        comment_from_doc = post._doc.get("comments", [])[1]
        assert isinstance(post.comments[1], Comment)
        assert post.comments[1].body == comment_from_doc.get("body")
        assert post.comments[1].created == comment_from_doc.get("created")

    async def test_exclude__doc_from_dict(self):
        user = User(username="test", created=datetime.now(), age=10)
        user._doc = {
            "username": user.username,
            "created": user.created,
            "age": user.age,
        }
        user_as_dict = user.dict(exclude_defaults=True)
        assert "_doc" not in user_as_dict.keys()
        assert user_as_dict == user._doc

    async def test_convert__id_field_in_dict(self):
        user = User(username="test", created=datetime.now(), age=10)
        user.id = ObjectId()
        assert user.id
        user_as_dict = user.dict(exclude_unset=True)
        assert user_as_dict.get("id") == user.id


class DBPydanticMixinTestCase:
    async def test_jsonable_model(self, init_test_db):
        user = User(username="test", created=datetime.now(), age=10)
        user.id = ObjectId()
        assert isinstance(user.id, ObjectId)
        assert user.json()

    async def test_get_collection(self, init_test_db, monkeypatch):
        col = await User.get_collection()
        assert isinstance(col, motor_asyncio.AsyncIOMotorCollection)

    async def test_get_collection_in_unconfigured_config(
        self, init_test_db, monkeypatch
    ):
        monkeypatch.delattr(User.Config, "database")
        monkeypatch.delattr(User.Config, "collection")
        raise_msg = "Collection or db_name is not configured in Config class"
        with pytest.raises(ValueError, match=raise_msg):
            _ = await User.get_collection()

        monkeypatch.undo()

    async def test_get_collection_with_unconfigured_db(self, init_test_db, monkeypatch):
        db_name = "unconfigured"
        monkeypatch.setattr(User.Config, "database", db_name)
        raise_msg = '"%s" is not found in MongoDBManager.database' % db_name
        with pytest.raises(ValueError, match=raise_msg):
            _ = await User.get_collection()
        monkeypatch.undo()

    async def test_save_model_with_new_doc(self, init_test_db):
        model_data = {"username": "test", "created": datetime.now(), "age": 10}
        user = User(**model_data)
        assert user
        assert user.username == model_data["username"]
        assert user.created == model_data["created"]
        assert user.age == model_data["age"]

        assert not user.id
        assert not user._doc
        await user.save()
        assert user
        doc = user._doc
        assert doc.get("username") == user.username
        assert doc.get("created") == user.created
        assert doc.get("age") == user.age

    async def test_save_model_with_exists_doc(self, init_test_db):
        model_data = {"username": "test", "created": datetime.now(), "age": 10}
        user = User(**model_data)
        await user.save()
        assert user
        old_id = user.id

        new_username = "new_test"
        user.username = new_username
        await user.save()
        assert user.username == new_username
        assert user._doc.get("username") == new_username
        assert user._doc.get("id") == old_id
        assert old_id == user.id

    async def test_save_nested_model(self, init_test_db):
        model_data = {"username": "test", "created": datetime.now(), "age": 10}
        user = User(**model_data)
        assert user

        post = Post(title="test", body="test_body", author=user)
        assert post
        assert post.author == user

        await post.save()

        doc = post._doc
        assert doc.get("title") == post.title
        assert doc.get("body") == post.body
        author_from_doc = doc.get("author", {})
        assert author_from_doc.get("username") == post.author.username
        assert author_from_doc.get("created") == post.author.created
        assert author_from_doc.get("age") == post.author.age

    @pytest.mark.parametrize(
        "model_data",
        [
            {"username": "test", "created": datetime.now(), "age": 10},
            UserSerializer.parse_obj(
                {"username": "test", "created": datetime.now(), "age": 10}
            ),
        ],
        ids=["dict", "pydantic_model"],
    )
    async def test_create(self, init_test_db, model_data):
        model = await User.create(model_data)
        if isinstance(model_data, BaseModel):
            model_data = model_data.dict()
        assert model
        assert model.id
        assert model._doc.get("id") == model.id
        assert model.username == model_data["username"]
        assert model.created == model_data["created"]
        assert model.age == model_data["age"]

    async def test_count(self, init_test_db):
        models = [
            User(username="test_user_#%d" % i, created=datetime.now(), age=i)
            for i in range(1, 6)
        ]
        await User.bulk_create(models[0:3])
        assert await User.count() == 3
        await User.bulk_create(models[3::])
        assert await User.count() == 5

    async def test_find_one(self, init_test_db):
        model_data = {
            "username": "test",
            "created": datetime.utcnow().isoformat(),
            "age": 10,
        }
        user = User(**model_data)
        await user.save()

        result = await User.find_one({"_id": user.id})
        assert result

        assert result.id == user.id
        assert user.username == result.username
        assert user.created.date() == result.created.date()
        assert user.age == result.age

    async def test_find_one_with_empty_result(self, init_test_db):
        result = await User.find_one({"_id": "undefined_id"})
        assert not result

    @pytest.mark.parametrize(
        "models",
        [
            [
                {"username": "test_user_%d" % i, "created": datetime.now(), "age": i}
                for i in range(1, 5)
            ],
            [
                User(username="test_user_%d" % i, created=datetime.now(), age=i)
                for i in range(1, 5)
            ],
        ],
        ids=["dict", "pydantic_model"],
    )
    async def test_bulk_create(self, init_test_db, models):
        saved_models = await User.bulk_create(models)
        assert saved_models
        for model in saved_models:
            assert isinstance(model, User)
            assert model.id == model._doc.get("id")
            assert model.username == model._doc.get("username")
            assert model.created == model._doc.get("created")
            assert model.age == model._doc.get("age")

    async def test_find_many(self, init_test_db):
        models = [
            User(username="test_user_%d" % i, created=datetime.now(), age=i)
            for i in range(1, 5)
        ]
        await User.bulk_create(models)

        query = {"username": {"$regex": re.compile("[0-3]", re.IGNORECASE)}}
        result = await User.find_many(query)
        assert result
        assert len(result) == 3

        for document in result:
            assert isinstance(document, User)
            assert ObjectId(document.id) == document._doc.get("id")
            assert document.username == document._doc.get("username")
            assert document.created == document._doc.get("created")
            assert document.age == document._doc.get("age")

    async def test_update_many(self, init_test_db):
        models = [
            User(username="test_user_%d" % i, created=datetime.now(), age=i)
            for i in range(1, 5)
        ]
        await User.bulk_create(models)

        # Update documents whose age more than 1 and less than 4
        query = {"age": {"$gt": 1, "$lte": 3}}
        fields = {"$set": {"username": "new_user_name"}}
        updated_documents = await User.update_many(query, fields)
        for doc in updated_documents:
            assert 1 < doc.age <= 3
            assert doc.username == "new_user_name"

    async def test_update(self, init_test_db):
        model_data = {
            "username": "test_username",
            "created": datetime.utcnow().isoformat(),
            "age": 10,
        }
        user = User(**model_data)
        await user.save()
        assert user

        update_data = {"username": "new_username", "age": None}
        updated_model = await user.update(update_data)
        assert updated_model.username == update_data["username"]
        assert updated_model.age == update_data["age"]
        assert updated_model.created == user.created

        update_data = {"username": "username_from_pydantic"}
        pydantic_updated_data = UserSerializer.parse_obj(update_data)
        old_updated_model = updated_model
        updated_model = await user.update(pydantic_updated_data)
        assert updated_model.username == update_data["username"]
        assert updated_model.age == old_updated_model.age
        assert updated_model.created == old_updated_model.created

        # Without model.id
        user.id = None
        raise_msg = "Not found id in current model instance"
        with pytest.raises(ValueError, match=raise_msg):
            await user.reload()

    async def test_reload_model(self, init_test_db):
        model_data = {
            "username": "test_user",
            "created": datetime.utcnow().isoformat(),
            "age": 10,
        }
        user = User(**model_data)
        await user.save()

        # Change document in db without model
        collection = await user.get_collection()
        new_user = await collection.find_one_and_update(
            {"_id": user.id},
            {"$set": {"username": "new_username"}},
            return_document=ReturnDocument.AFTER,
        )
        assert new_user
        assert user.username != new_user["username"]

        reloaded_model = await user.reload()
        assert reloaded_model == user
        assert reloaded_model.username == new_user["username"]

        # Without model.id
        user.id = None
        raise_msg = "Not found id in current model instance"
        with pytest.raises(ValueError, match=raise_msg):
            await user.reload()

    async def test_delete(self, init_test_db):
        model_data = {
            "username": "test_user",
            "created": datetime.utcnow().isoformat(),
            "age": 10,
        }
        user = User(**model_data)
        await user.save()

        await user.delete()

        assert not user._doc
        assert not await user.find_one({"_id": user.id})

        # Without model.id
        user.id = None
        raise_msg = "Not found id in current model instance"
        with pytest.raises(ValueError, match=raise_msg):
            await user.reload()

    async def test_bug_serialize_to_json_when_model_is_deeply_nested(self, init_test_db):
        """Failing testcase:
        When you have a BaseDBMixin container model with children that are
        DBPydanticMixin, serializing to json fails after the child objects are saved.
        (eg. then now have an ObjectId)
        """
        class FooThing(mixins.DBPydanticMixin):
            name: str

            class Config:
                database = "default"
                collection = "test_post"

        class SomeContainer(mixins.BaseDBMixin):
            many_things: List[FooThing]

        container = SomeContainer(
            many_things=[FooThing(name="neo"), FooThing(name="morpheus")]
        )
        container.json()

        for thing in container.many_things:
            await thing.save()

        container_2 = SomeContainer(many_things=container.many_things)
        container_2.json()
