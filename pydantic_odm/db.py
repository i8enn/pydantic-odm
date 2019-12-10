"""Database connector module"""
from __future__ import annotations

from typing import Any, Dict, Type

from motor import motor_asyncio


class MongoDBManager:
    """
    Singleton class for create main interface for working on many Mongo
    database connections from one place.

    Usage:
    On startup application execute initial connect.

    def startup():
        MongoDBManager.initial_connections(
            username='mongo_user',
            password='mongo_password',
            host='localhost',
            port=27017
        )

    Get collection in all place in your code:
    from pydantic_odm.db import MongoDBManager
    ...
    any_collections = MongoDBManager.default.any_collections
    """

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
            client = motor_asyncio.AsyncIOMotorClient(
                username=configuration.get('USERNAME'),
                password=configuration.get('PASSWORD'),
                host=configuration.get('HOST', 'localhost'),
                port=configuration.get('PORT', 27017),
                authSource=configuration.get('AUTH_SOURCE', 'admin'),
                authMechanism=configuration.get('AUTH_MEC', 'SCRAM-SHA-256'),
            )
            db_name = configuration.get('NAME', alias)
            cls.connections[alias] = client
            db = client[db_name]
            cls.databases[alias] = db
        return cls
