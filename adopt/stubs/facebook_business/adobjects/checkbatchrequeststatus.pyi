from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class CheckBatchRequestStatus(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        errors: str
        errors_total_count: str
        handle: str
        ids_of_invalid_requests: str
        status: str
        warnings: str
        warnings_total_count: str
    class ErrorPriority:
        high: str
        low: str
        medium: str
