"""Tests for mongodb encoders"""
import pytest
from bson.decimal128 import Decimal128
from decimal import Decimal
from enum import Enum

from pydantic_odm.encoders import mongodb as mongodb_encoders

pytestmark = pytest.mark.asyncio


class UserTypesEnum(Enum):
    """Example user enum"""

    Admin = "admin"
    Manager = "manager"
    Author = "author"
    Reader = "reader"


class AbstractMongoDBEncoderTestCase:
    async def test_abstract_cls(self):
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            mongodb_encoders.AbstractMongoDBEncoder()

    async def test_abstract__call__(self):
        encoder = mongodb_encoders.AbstractMongoDBEncoder
        assert getattr(encoder.__call__, "__isabstractmethod__") is True


class EncodeEnumTestCase:
    @pytest.mark.parametrize(
        "data, expected",
        [
            pytest.param(
                {"username": "test", "type": UserTypesEnum.Admin},
                {"username": "test", "type": UserTypesEnum.Admin.value},
                id="simple_dict",
            ),
            pytest.param(
                [
                    {"username": "test", "type": UserTypesEnum.Admin},
                    {"username": "test", "type": UserTypesEnum.Manager},
                ],
                [
                    {"username": "test", "type": UserTypesEnum.Admin.value},
                    {"username": "test", "type": UserTypesEnum.Manager.value},
                ],
                id="simple_list",
            ),
            pytest.param(
                {
                    "title": "test",
                    "author": {"username": "test", "type": UserTypesEnum.Admin},
                },
                {
                    "title": "test",
                    "author": {"username": "test", "type": UserTypesEnum.Admin.value},
                },
                id="nested",
            ),
            pytest.param(
                {
                    "title": "test",
                    "contributors": [
                        {"username": "test", "type": UserTypesEnum.Admin},
                        {"username": "test", "type": UserTypesEnum.Manager.value},
                    ],
                },
                {
                    "title": "test",
                    "contributors": [
                        {"username": "test", "type": UserTypesEnum.Admin.value},
                        {"username": "test", "type": UserTypesEnum.Manager.value},
                    ],
                },
                id="list_in_nested",
            ),
        ],
    )
    async def test__convert_enums(self, data, expected):
        assert mongodb_encoders._convert_enums(data) == expected


class BaseMongoDBEncoderTestCase:
    @pytest.mark.parametrize(
        "data, expected",
        [
            pytest.param(
                {"username": "test", "type": UserTypesEnum.Admin},
                {"username": "test", "type": UserTypesEnum.Admin.value},
                id="simple",
            ),
            pytest.param(
                {
                    "title": "test",
                    "author": {"username": "test", "type": UserTypesEnum.Admin},
                    "contributors": [
                        {"username": "test", "type": UserTypesEnum.Manager},
                        {"username": "test", "type": UserTypesEnum.Reader},
                    ],
                },
                {
                    "title": "test",
                    "author": {"username": "test", "type": UserTypesEnum.Admin.value},
                    "contributors": [
                        {"username": "test", "type": UserTypesEnum.Manager.value},
                        {"username": "test", "type": UserTypesEnum.Reader.value},
                    ],
                },
                id="nested",
            ),
        ],
    )
    async def test_encode(self, data, expected):
        encoder = mongodb_encoders.BaseMongoDBEncoder()
        assert encoder(data) == expected
