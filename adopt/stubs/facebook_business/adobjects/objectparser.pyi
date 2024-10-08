from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.exceptions import FacebookBadObjectError as FacebookBadObjectError

class ObjectParser:
    def __init__(self, api: Incomplete | None = None, target_class: Incomplete | None = None, reuse_object: Incomplete | None = None, custom_parse_method: Incomplete | None = None) -> None: ...
    def parse_single(self, response, override_target_class: Incomplete | None = None): ...
    def parse_multiple(self, response): ...
