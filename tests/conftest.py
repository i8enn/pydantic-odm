"""Main conftest"""
import pytest
from asyncio import get_event_loop_policy

from pydantic_odm.db import MongoDBManager

pytestmark = pytest.mark.asyncio


DATABASE_SETTING = {'default': {'NAME': 'test_mongo', 'PORT': 37017}}


@pytest.yield_fixture(scope='session')
def event_loop():
    loop = get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture()
async def init_test_db(event_loop):
    dbm = await MongoDBManager(DATABASE_SETTING, event_loop).init_connections()
    yield dbm
    for db in dbm.databases.values():
        await db.client.drop_database(db)
