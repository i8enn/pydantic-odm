"""Additional scheme pydantic validation errors"""
from pydantic.errors import PydanticValueError


class RangeBorderCrossing(PydanticValueError):
    code = "range.border_crossing"
    msg_template = "Make sure the borders do not cross"


class DatetimeBorderCrossing(RangeBorderCrossing):
    code = "datetime_range.border_crossing"
