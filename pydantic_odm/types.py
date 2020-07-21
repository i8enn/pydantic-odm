"""Types for pydantic models"""
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime
from pydantic import BaseModel
from typing import Dict, List, Union

from .errors import DatetimeBorderCrossing


class ObjectIdStr(str):
    """Field for validate string like ObjectId"""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return str(v)
        else:
            try:
                ObjectId(str(v))
            except InvalidId:
                raise ValueError('Not a valid ObjectId')
            return v


class DateTimeRange(BaseModel):
    """
    Datetime range type.

    First elem - lower bound.
    Second elem - upper bound.
    """

    gte: datetime = None
    lte: datetime = None

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Union[List, Dict], values=None):
        """Check border crossing"""
        gte, lte = None, None
        try:
            if isinstance(v, list):
                gte, lte = v
            elif isinstance(v, dict):
                gte = v.get('gte')
                lte = v.get('lte')
        except IndexError:
            return cls(gte=gte, lte=lte)

        if gte and lte:
            if gte > lte or lte < gte:
                raise DatetimeBorderCrossing()

        return cls(gte=gte, lte=lte)
