from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class VehicleOffer(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        amount_currency: str
        amount_percentage: str
        amount_price: str
        amount_qualifier: str
        applinks: str
        availability: str
        body_style: str
        cashback_currency: str
        cashback_price: str
        category_specific_fields: str
        currency: str
        dma_codes: str
        downpayment_currency: str
        downpayment_price: str
        downpayment_qualifier: str
        drivetrain: str
        end_date: str
        end_time: str
        exterior_color: str
        fuel_type: str
        generation: str
        id: str
        image_fetch_status: str
        images: str
        interior_color: str
        interior_upholstery: str
        make: str
        model: str
        offer_description: str
        offer_disclaimer: str
        offer_type: str
        price: str
        sanitized_images: str
        start_date: str
        start_time: str
        term_length: str
        term_qualifier: str
        title: str
        transmission: str
        trim: str
        unit_price: str
        url: str
        vehicle_offer_id: str
        visibility: str
        year: str
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
    def get_augmented_realities_metadata(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_channels_to_integrity_status(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_videos_metadata(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
