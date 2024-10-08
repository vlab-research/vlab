from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class CloudbridgeDatasetStatus(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        app_redacted_event: str
        app_sensitive_params: str
        app_unverified_event: str
        has_app_associated: str
        is_app_prohibited: str
        is_dataset: str
