from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class Recommendation(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        created_time: str
        has_rating: str
        has_review: str
        open_graph_story: str
        rating: str
        recommendation_type: str
        review_text: str
        reviewer: str
