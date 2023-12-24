from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class LocalServiceBusiness(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        address: str
        applinks: str
        availability: str
        brand: str
        category: str
        category_specific_fields: str
        condition: str
        cuisine_type: str
        currency: str
        custom_label_0: str
        custom_label_1: str
        custom_label_2: str
        custom_label_3: str
        custom_label_4: str
        custom_number_0: str
        custom_number_1: str
        custom_number_2: str
        custom_number_3: str
        custom_number_4: str
        description: str
        expiration_date: str
        gtin: str
        id: str
        image_fetch_status: str
        images: str
        local_info: str
        local_service_business_id: str
        main_local_info: str
        phone: str
        price: str
        price_range: str
        retailer_category: str
        sanitized_images: str
        size: str
        title: str
        unit_price: str
        url: str
        vendor_id: str
        visibility: str
    class Availability:
        available_for_order: str
        discontinued: str
        in_stock: str
        mark_as_sold: str
        out_of_stock: str
        pending: str
        preorder: str
    class Condition:
        pc_cpo: str
        pc_new: str
        pc_open_box_new: str
        pc_refurbished: str
        pc_used: str
        pc_used_fair: str
        pc_used_good: str
        pc_used_like_new: str
    class ImageFetchStatus:
        direct_upload: str
        fetched: str
        fetch_failed: str
        no_status: str
        outdated: str
        partial_fetch: str
    class Visibility:
        published: str
        staging: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_channels_to_integrity_status(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
