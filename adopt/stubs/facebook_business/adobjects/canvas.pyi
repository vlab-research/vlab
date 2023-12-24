from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class Canvas(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        background_color: str
        body_elements: str
        business_id: str
        canvas_link: str
        collection_hero_image: str
        collection_hero_video: str
        collection_thumbnails: str
        dynamic_setting: str
        element_payload: str
        elements: str
        fb_body_elements: str
        id: str
        is_hidden: str
        is_published: str
        last_editor: str
        linked_documents: str
        name: str
        owner: str
        property_list: str
        source_template: str
        store_url: str
        style_list: str
        tags: str
        ui_property_list: str
        unused_body_elements: str
        update_time: str
        use_retailer_item_ids: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_update(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_previews(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
