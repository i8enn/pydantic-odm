"""Tests for pydantic models types"""
import pytest
from bson import ObjectId
from datetime import datetime, timedelta
from pydantic import BaseModel, ValidationError

from pydantic_odm import types

pytestmark = pytest.mark.asyncio


class SchemeForTestDateTimeRange(BaseModel):
    """Scheme for test datetime range"""

    created: types.DateTimeRange = None


class SchemeForTestObjectIdStr(BaseModel):
    """Scheme for test object id str type"""

    uid: types.ObjectIdStr = None


class TestObjectIdStr:
    async def test_create(self):
        model = SchemeForTestObjectIdStr
        uid = ObjectId()

        obj = model(uid=str(uid))
        assert obj.uid == str(uid)

    async def test_validator(self):
        # Invalid ObjectID str
        model = SchemeForTestObjectIdStr
        uid = 'saidfojdsioafjaosidfj'
        raise_msg = 'Not a valid ObjectId'
        with pytest.raises(ValidationError, match=raise_msg):
            model(uid=uid)


class TestDateTimeRange:
    async def test_create(self):
        model = SchemeForTestDateTimeRange
        gte = datetime.now()
        lte = datetime.now() + timedelta(days=1)

        obj = model(created=[gte, lte])
        assert obj.created.gte == gte
        assert obj.created.lte == lte

    async def test_optional(self):
        model = SchemeForTestDateTimeRange
        gte = datetime.now()
        lte = datetime.now() + timedelta(days=1)

        obj = model(created=[gte, None])
        assert obj.created.gte == gte
        assert obj.created.lte is None

        obj = model(created=[None, lte])
        assert obj.created.gte is None
        assert obj.created.lte == lte

        obj = model(created=[None, None])
        assert obj.created.gte is None
        assert obj.created.lte is None

    async def test_validator(self):
        model = SchemeForTestDateTimeRange

        # gte > lte
        gte = datetime.now() + timedelta(milliseconds=1)
        lte = datetime.now()
        raise_msg = 'Make sure the borders do not cross'
        with pytest.raises(ValidationError, match=raise_msg):
            model(created=[gte, lte])

        # lte < gte
        gte = datetime.now()
        lte = datetime.now() - timedelta(milliseconds=1)
        raise_msg = 'Make sure the borders do not cross'
        with pytest.raises(ValidationError, match=raise_msg):
            model(created=[gte, lte])
