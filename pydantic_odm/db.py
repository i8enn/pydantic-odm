"""Database connector module"""
from __future__ import annotations

from asyncio import AbstractEventLoop, get_running_loop
from motor import motor_asyncio
from threading import Lock
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

if TYPE_CHECKING:
    from pydantic.typing import DictStrAny

    DatabaseSettingsType = Dict[str, Dict[str, Any]]


class MongoDBManagerMeta(type):
    """MongoDBManager metaclass for implement singleton behavior"""

    # Main mongodb manager instance (for singleton implementation)
    _instance: Optional[MongoDBManager] = None

    # Lock for thread-save
    _lock: Lock = Lock()

    def __call__(
        cls, *args: Tuple[Any], **kwargs: DictStrAny
    ) -> Optional[MongoDBManager]:
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__call__(*args, **kwargs)
        return cls._instance


class MongoDBManager(metaclass=MongoDBManagerMeta):
    """
    Singleton class for create main interface for working on many Mongo
    database connections from one place.

    Setting signature::
        {
            'connection_alias': {
                'SETTING_NAME': 'SETTINGS_VALUE'
            }
        }

    Very minimal connection configuration (Not recommended)::

        'minimal': {}

    .. note:: connection to 'minimal' Mongo database on mongodb://localhost:27017

    Minimal connection configuration::

        'minimal': {
            'NAME': 'mongo-db-name'
        }

    Full connection configuration::

        'full_configuration': {
            'NAME': 'mongo-db-name',
            'HOST': 'mongodb://localhost',
            'PORT': 27017,
            'USERNAME': 'mongo_user',
            'PASSWORD': 'mongo_password',
            'AUTHENTICATION_SOURCE': 'admin',
            'AUTH-MECHANISM': 'SCRAM-SHA-256'
        }

    Connection params description:
        - `NAME`: (str) Mongo database name for connection. If not setup - using configuration alias.
        - `HOST`: (str) Mongo hostname. Configured by default as in PyMongo (`localhost`).
        - `PORT`: (int) Mongo port. Configured by default as in PyMongo (27017).
        - `USERNAME`: (str) Mongo administration username. Default - empty.
        - `PASSWORD`: (str) Mongo administration password. Default - empty.
        - `AUTHENTICATION_SOURCE`: (str) Mongo database name for authentication
           source. Configured by default as in PyMongo ('admin')
        - `AUTH-MECHANISM`: (str) Mongo authentication mechanism. If not setup -
          PyMongo automatically selects a mechanism depending on the version of
          MongoDB (See https://api.mongodb.com/python/current/examples/authentication.html#default-authentication-mechanism)


    Usage::

    On startup application execute initial connect.

        def startup():
            MongoDBManager.initial_connections({
                'default': {
                    'NAME': 'mongo-db-name',
                    'HOST': 'mongodb://localhost',
                    'PORT': 27017,
                    'USERNAME': 'mongo_user',
                    'PASSWORD': 'mongo_password',
                    'AUTHENTICATION_SOURCE': 'admin',
                    'AUTH-MECHANISM': 'SCRAM-SHA-256'
                },
                'minimal_configured_db': {
                    'NAME': 'mongo-db-name'
                }
            })

    Get collection in all place in your code:
    from pydantic_odm.db import MongoDBManager
    ...
    any_collections = MongoDBManager.default.any_collections
    """  # noqa: E501

    # Event loop for passing to MotorClient
    _loop: AbstractEventLoop

    # Passed settings
    settings: DatabaseSettingsType
    # Created connections
    connections: Dict[str, motor_asyncio.AsyncIOMotorClient] = {}
    # Configured databases
    databases: Dict[str, motor_asyncio.AsyncIOMotorDatabase] = {}
    # Init database flag
    is_init: bool = False

    def __init__(
        self, database_settings: DatabaseSettingsType, loop: AbstractEventLoop = None
    ):
        self.settings = database_settings or {}
        if not loop:
            loop = get_running_loop()
        self._loop = loop

    def __getitem__(self, item: str) -> Optional[motor_asyncio.AsyncIOMotorDatabase]:
        return self.databases.get(item, None)

    async def init_connections(self) -> MongoDBManager:
        """Create connections to Mongo databases"""
        if self.is_init:
            return self

        if not self.settings:
            raise RuntimeError("Not found database configurations in MongoDBManager")

        for alias, configuration in self.settings.items():
            connection_params = {
                "username": configuration.get("USERNAME"),
                "password": configuration.get("PASSWORD"),
                "host": configuration.get("HOST"),
                "port": configuration.get("PORT"),
                "authSource": configuration.get("AUTH_SOURCE", ""),
            }
            if "OPTIONAL_PARAMETERS" in configuration:
                connection_params.update(**configuration["OPTIONAL_PARAMETERS"])
            auth_mech = configuration.get("AUTH_MECHANISM")
            if auth_mech:
                connection_params["authMechanism"] = auth_mech
            connection_params["io_loop"] = self._loop
            client = motor_asyncio.AsyncIOMotorClient(**connection_params)
            db_name = configuration.get("NAME", alias)
            self.connections[alias] = client
            db = client[db_name]
            self.databases[alias] = db

        self.is_init = True

        return self


def get_db_manager() -> Optional[MongoDBManager]:
    """Return initialized singleton mongodb manager"""
    return MongoDBManager._instance
