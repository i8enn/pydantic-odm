"""Tests for database connector module"""
import importlib
import pytest
from asyncio import get_event_loop_policy, get_running_loop
from concurrent import futures

from pydantic_odm import db

from .conftest import DATABASE_SETTING

pytestmark = pytest.mark.asyncio


@pytest.fixture(scope='function')
def reload_db_module():
    importlib.reload(db)  # noqa


@pytest.mark.usefixtures('reload_db_module')
class CreateMongoDBManagerInstanceTestCase:
    async def test_create_instance_with_settings(self):
        dbm = await db.MongoDBManager(DATABASE_SETTING).init_connections()

        assert dbm._instance == dbm
        assert dbm.is_init is True
        assert dbm.connections['default']
        # Check use current loop if not passed specify loop
        assert dbm._loop == get_running_loop()

    async def test_create_instance_with_custom_event_loop(self):
        custom_event_loop = get_event_loop_policy().new_event_loop()
        dbm = db.MongoDBManager(DATABASE_SETTING, loop=custom_event_loop)
        await dbm.init_connections()

        assert id(dbm._loop) == id(custom_event_loop)
        assert dbm.is_init is True
        for connection in dbm.connections.values():
            assert connection.io_loop == custom_event_loop

    async def test_create_instance_with_empty_database_settings(self):
        msg = 'Not found database configurations in MongoDBManager'
        with pytest.raises(RuntimeError, match=msg):
            await db.MongoDBManager({}).init_connections()

    async def test_is_singleton(self, event_loop):
        # First instance
        dbm = await db.MongoDBManager(DATABASE_SETTING, event_loop).init_connections()
        assert dbm._instance == dbm
        # Second instance
        dbm_clone = db.MongoDBManager(DATABASE_SETTING, event_loop)
        assert dbm_clone == dbm
        assert dbm_clone._instance == dbm
        # Third instance after one more import
        re_imported_db = importlib.import_module('pydantic_odm.db', 'pydantic_odm')
        after_import = re_imported_db.MongoDBManager(  # noqa
            DATABASE_SETTING, event_loop
        )
        assert after_import._instance == dbm
        assert after_import == dbm

    async def test_thread_safe_singleton_implementation(self, event_loop):
        with futures.ThreadPoolExecutor() as executor:
            # First thread
            th1 = executor.submit(db.MongoDBManager, DATABASE_SETTING, event_loop)
            # Second thread
            th2 = executor.submit(db.MongoDBManager, DATABASE_SETTING, event_loop)

            dbm1 = th1.result()
            assert dbm1
            dbm2 = th2.result()
            assert dbm2

            # Check created single object and return already existing instance
            assert id(dbm1) == id(dbm2)


@pytest.mark.usefixtures('reload_db_module')
class InitConnectionWithMongoDBManagerTestCase:
    @pytest.mark.parametrize(
        'settings',
        [
            pytest.param(DATABASE_SETTING, id='simple'),
            pytest.param(
                {
                    'default': {
                        'NAME': 'test_mongo',
                        'PORT': 37017,
                        'USERNAME': 'local',
                        'PASSWORD': 'local_pass',
                        'HOST': 'localhost',
                        'AUTH_SOURCE': 'admin',
                        'AUTH_MECHANISM': 'SCRAM-SHA-256',
                    }
                },
                id='full',
            ),
        ],
    )
    async def test_init_connections(self, event_loop, settings):
        dbm = await db.MongoDBManager(settings, event_loop).init_connections()
        assert isinstance(dbm, db.MongoDBManager)
        assert dbm.is_init
        assert len(dbm.connections) == 1
        assert len(dbm.databases) == len(settings.keys())
        for db_alias, db_settings in settings.items():
            assert dbm.connections[db_alias]
            assert dbm.databases[db_alias].name == db_settings.get('NAME', None)

    async def test_init_connection_with_empty_conf(self, event_loop):
        dbm = await db.MongoDBManager({'minimal': {}}, event_loop).init_connections()
        assert isinstance(dbm, db.MongoDBManager)
        assert len(dbm.connections) == 1
        assert dbm.connections['minimal']
        assert len(dbm.databases) == 1
        assert dbm.databases['minimal'].name == 'minimal'

    async def test_get_db_with_getattr(self, event_loop):
        dbm = await db.MongoDBManager(DATABASE_SETTING, event_loop).init_connections()
        database = dbm.databases['default']
        assert dbm['default'] == database


@pytest.mark.usefixtures('reload_db_module')
class GetCurrentDBManagerInstanceTestCase:
    async def test_get_db_manager(self, event_loop):
        dbm = await db.MongoDBManager(DATABASE_SETTING, event_loop).init_connections()
        assert dbm
        assert id(dbm) == id(db.get_db_manager())
