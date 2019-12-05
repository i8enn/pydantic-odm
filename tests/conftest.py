"""Main conftest"""
import pytest

from pydantic_odm.db import MongoDBManager

from .db import DATABASE_SETTING

pytestmark = pytest.mark.asyncio


@pytest.fixture()
async def init_test_db():
    dbm = await MongoDBManager.init_connections(DATABASE_SETTING)
    yield dbm
    for db in dbm.databases.values():
        await db.client.drop_database(db)
