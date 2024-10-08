from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class ProductFeed(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        country: str
        created_time: str
        default_currency: str
        deletion_enabled: str
        delimiter: str
        encoding: str
        file_name: str
        id: str
        ingestion_source_type: str
        item_sub_type: str
        latest_upload: str
        migrated_from_feed_id: str
        name: str
        override_type: str
        primary_feeds: str
        product_count: str
        quoted_fields_mode: str
        schedule: str
        supplementary_feeds: str
        update_schedule: str
        feed_type: str
        override_value: str
        primary_feed_ids: str
        rules: str
        selected_override_fields: str
    class Delimiter:
        autodetect: str
        bar: str
        comma: str
        semicolon: str
        tab: str
        tilde: str
    class IngestionSourceType:
        primary_feed: str
        supplementary_feed: str
    class QuotedFieldsMode:
        autodetect: str
        off: str
        on: str
    class Encoding:
        autodetect: str
        latin1: str
        utf16be: str
        utf16le: str
        utf32be: str
        utf32le: str
        utf8: str
    class FeedType:
        automotive_model: str
        destination: str
        flight: str
        home_listing: str
        hotel: str
        hotel_room: str
        local_inventory: str
        media_title: str
        offer: str
        products: str
        transactable_items: str
        vehicles: str
        vehicle_offer: str
    class ItemSubType:
        appliances: str
        baby_feeding: str
        baby_transport: str
        beauty: str
        bedding: str
        cameras: str
        cell_phones_and_smart_watches: str
        cleaning_supplies: str
        clothing: str
        clothing_accessories: str
        computers_and_tablets: str
        diapering_and_potty_training: str
        electronics_accessories: str
        furniture: str
        health: str
        home_goods: str
        jewelry: str
        nursery: str
        printers_and_scanners: str
        projectors: str
        shoes_and_footwear: str
        software: str
        toys: str
        tvs_and_monitors: str
        video_game_consoles_and_video_games: str
        watches: str
    class OverrideType:
        batch_api_language_or_country: str
        catalog_segment_customize_default: str
        country: str
        language: str
        language_and_country: str
        local: str
        smart_pixel_language_or_country: str
        version: str
    @classmethod
    def get_endpoint(cls): ...
    def api_create(self, parent_id, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_delete(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_update(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_automotive_models(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_destinations(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_flights(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_home_listings(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_hotels(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_media_titles(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_products(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_rules(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_rule(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_supplementary_feed_assoc(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_upload_schedules(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_upload_schedule(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_uploads(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_upload(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_vehicle_offers(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_vehicles(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
