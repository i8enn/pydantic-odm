"""Main conftest"""
import pytest

from pydantic_odm.db import MongoDBManager

pytestmark = pytest.mark.asyncio


DATABASE_SETTING = {'default': {'NAME': 'test_mongo', 'PORT': 37017}}


@pytest.fixture()
async def init_test_db():
    dbm = await MongoDBManager.init_connections(DATABASE_SETTING)
    yield dbm
    for db in dbm.databases.values():
        await db.client.drop_database(db)
