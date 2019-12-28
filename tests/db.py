"""Tests for database connector module"""
import importlib

import pytest

from pydantic_odm import db

pytestmark = pytest.mark.asyncio


DATABASE_SETTING = {
    'default': {
        'NAME': 'test_mongo',
        'HOST': 'mongodb://localhost',
        'PORT': 37017,
        'USERNAME': 'mongo_user',
        'PASSWORD': 'mongo_password',
        'AUTHENTICATION_SOURCE': 'admin',
    }
}


class TestMongoDBManager:
    async def test_create_instance(self):
        raise_msg = 'This is singleton object'
        with pytest.raises(TypeError, match=raise_msg):
            db.MongoDBManager()

    async def test_init_connections(self):
        dbm = await db.MongoDBManager.init_connections(DATABASE_SETTING)
        assert dbm == db.MongoDBManager
        assert len(dbm.connections) == 1
        assert dbm.connections['default']
        assert len(dbm.databases) == 1
        assert dbm.databases['default'].name == 'test_mongo'

    async def test_init_connection_with_empty_conf(self):
        importlib.reload(db)
        dbm = await db.MongoDBManager.init_connections({'minimal': {}})
        assert dbm == db.MongoDBManager
        assert len(dbm.connections) == 1
        assert dbm.connections['minimal']
        assert len(dbm.databases) == 1
        assert dbm.databases['minimal'].name == 'minimal'

    async def test_get_db_with_getattr(self):
        importlib.reload(db)
        dbm = await db.MongoDBManager.init_connections(DATABASE_SETTING)
        database = dbm.databases['default']
        assert dbm['default'] == database
