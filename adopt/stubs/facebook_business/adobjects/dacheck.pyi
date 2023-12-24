from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class DACheck(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        action_uri: str
        description: str
        key: str
        result: str
        title: str
        user_message: str
    class ConnectionMethod:
        all: str
        app: str
        browser: str
        server: str
