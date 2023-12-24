from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class BroadTargetingCategories(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        category_description: str
        id: str
        name: str
        parent_category: str
        path: str
        size_lower_bound: str
        size_upper_bound: str
        source: str
        type: str
        type_name: str
        untranslated_name: str
        untranslated_parent_name: str
    @classmethod
    def get_endpoint(cls): ...
