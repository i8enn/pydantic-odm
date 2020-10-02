"""Tests for MongoDB decoders"""
import bson
import pytest

from pydantic_odm.decoders import mongodb as mongodb_decoders

pytestmark = pytest.mark.asyncio


class AbstractMongoDBDecoderTestCase:
    async def test_abstrct_class(self):
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            mongodb_decoders.AbstractMongoDBDecoder()

    async def test_abstractmethod__call__(self):
        decoder = mongodb_decoders.AbstractMongoDBDecoder
        assert getattr(decoder.__call__, "__isabstractmethod__") is True


class BaseMongoDBDecoderTestCase:
    @pytest.mark.parametrize(
        "data, expected",
        [
            pytest.param(
                {
                    "_id": bson.ObjectId("1f19e462fa9c1eab66db23fb"),
                    "username": "test",
                    "full_name": "Test Object",
                },
                {
                    "id": bson.ObjectId("1f19e462fa9c1eab66db23fb"),
                    "username": "test",
                    "full_name": "Test Object",
                },
                id="simple",
            ),
            pytest.param(
                {
                    "_id": bson.ObjectId("1f19e462fa9c1eab66db23fb"),
                    "title": "Test",
                    "author": {
                        "_id": bson.ObjectId("2f19e462fa9c1eab66db23fb"),
                        "username": "test",
                        "full_name": "Test Object",
                    },
                    "contributors": [
                        {
                            "_id": bson.ObjectId("3f19e462fa9c1eab66db23fb"),
                            "username": "test1",
                            "full_name": "Test Contrib 1",
                        },
                        {
                            "_id": bson.ObjectId("4f19e462fa9c1eab66db23fb"),
                            "username": "test2",
                            "full_name": "Test Contrib 2",
                        },
                    ],
                },
                {
                    "id": bson.ObjectId("1f19e462fa9c1eab66db23fb"),
                    "title": "Test",
                    "author": {
                        "id": bson.ObjectId("2f19e462fa9c1eab66db23fb"),
                        "username": "test",
                        "full_name": "Test Object",
                    },
                    "contributors": [
                        {
                            "id": bson.ObjectId("3f19e462fa9c1eab66db23fb"),
                            "username": "test1",
                            "full_name": "Test Contrib 1",
                        },
                        {
                            "id": bson.ObjectId("4f19e462fa9c1eab66db23fb"),
                            "username": "test2",
                            "full_name": "Test Contrib 2",
                        },
                    ],
                },
                id="nested",
            ),
            pytest.param(
                {
                    '_id': bson.ObjectId('1f19e462fa9c1eab66db23fb'),
                    'username': 'test',
                    'full_name': 'Test Object',
                    'nested': ['A', 'B', 'C']
                },
                {
                    'id': bson.ObjectId('1f19e462fa9c1eab66db23fb'),
                    'username': 'test',
                    'full_name': 'Test Object',
                    'nested': ['A', 'B', 'C']
                },
                id='nested simple types',
            ),
        ],
    )
    async def test_decode_mongodb_document(self, data, expected):
        decoder = mongodb_decoders.BaseMongoDBDecoder()
        assert decoder(data) == expected
