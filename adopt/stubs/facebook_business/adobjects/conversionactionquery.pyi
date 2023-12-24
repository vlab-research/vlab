from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class ConversionActionQuery(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        field_action_type: str
        application: str
        conversion_id: str
        creative: str
        dataset: str
        event: str
        field_event_creator: str
        event_type: str
        fb_pixel: str
        fb_pixel_event: str
        leadgen: str
        object: str
        field_object_domain: str
        offer: str
        field_offer_creator: str
        offsite_pixel: str
        page: str
        field_page_parent: str
        post: str
        field_post_object: str
        field_post_object_wall: str
        field_post_wall: str
        question: str
        field_question_creator: str
        response: str
        subtype: str
