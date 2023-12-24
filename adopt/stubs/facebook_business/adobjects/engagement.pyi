from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class Engagement(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        count: str
        count_string: str
        count_string_with_like: str
        count_string_without_like: str
        social_sentence: str
        social_sentence_with_like: str
        social_sentence_without_like: str
