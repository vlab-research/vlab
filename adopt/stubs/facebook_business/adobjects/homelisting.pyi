from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class HomeListing(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        ac_type: str
        additional_fees_description: str
        address: str
        agent_company: str
        agent_email: str
        agent_fb_page_id: str
        agent_name: str
        agent_phone: str
        applinks: str
        area_size: str
        area_unit: str
        availability: str
        category_specific_fields: str
        co_2_emission_rating_eu: str
        currency: str
        days_on_market: str
        description: str
        energy_rating_eu: str
        furnish_type: str
        group_id: str
        heating_type: str
        home_listing_id: str
        id: str
        image_fetch_status: str
        images: str
        laundry_type: str
        listing_type: str
        max_currency: str
        max_price: str
        min_currency: str
        min_price: str
        name: str
        num_baths: str
        num_beds: str
        num_rooms: str
        num_units: str
        parking_type: str
        partner_verification: str
        pet_policy: str
        price: str
        property_type: str
        sanitized_images: str
        unit_price: str
        url: str
        visibility: str
        year_built: str
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
    @classmethod
    def get_endpoint(cls): ...
    def api_create(self, parent_id, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_delete(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_update(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_augmented_realities_metadata(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_channels_to_integrity_status(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_videos_metadata(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
