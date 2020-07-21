"""Database connector module"""
from __future__ import annotations

from motor import motor_asyncio
from typing import Any, Dict, Type


class MongoDBManager:
    """
    Singleton class for create main interface for working on many Mongo
    database connections from one place.

    Setting signature::
        {
            'connection_alias': {
                'SETTING_NAME': 'SETTINGS_VALUE'
            }
        }

    Very minimal connection configuration (Not recomended)::

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

    settings: Dict[str, Dict[str, Any]] = {}
    connections: Dict[str, motor_asyncio.AsyncIOMotorClient] = {}
    databases: Dict[str, motor_asyncio.AsyncIOMotorDatabase] = {}

    def __init__(self):
        raise TypeError('This is singleton object')

    def __class_getitem__(cls, item):
        return cls.databases.get(item, None)

    @classmethod
    async def init_connections(
        cls, settings: Dict[str, Dict[str, Any]]
    ) -> Type[MongoDBManager]:
        """Create connections to Mongo databases"""
        cls.settings = settings

        for alias, configuration in cls.settings.items():
            connection_params = {
                'username': configuration.get('USERNAME'),
                'password': configuration.get('PASSWORD'),
                'host': configuration.get('HOST'),
                'port': configuration.get('PORT'),
                'authSource': configuration.get('AUTH_SOURCE', ''),
            }
            auth_mech = configuration.get('AUTH_MECHANISM')
            if auth_mech:
                connection_params['authMechanism'] = auth_mech
            client = motor_asyncio.AsyncIOMotorClient(**connection_params)
            db_name = configuration.get('NAME', alias)
            cls.connections[alias] = client
            db = client[db_name]
            cls.databases[alias] = db
        return cls
