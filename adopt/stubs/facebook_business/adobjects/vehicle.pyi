from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class Vehicle(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        address: str
        applinks: str
        availability: str
        body_style: str
        category_specific_fields: str
        condition: str
        currency: str
        custom_label_0: str
        date_first_on_lot: str
        dealer_communication_channel: str
        dealer_email: str
        dealer_id: str
        dealer_name: str
        dealer_phone: str
        dealer_privacy_policy_url: str
        description: str
        drivetrain: str
        exterior_color: str
        fb_page_id: str
        features: str
        fuel_type: str
        id: str
        image_fetch_status: str
        images: str
        interior_color: str
        legal_disclosure_impressum_url: str
        make: str
        mileage: str
        model: str
        previous_currency: str
        previous_price: str
        price: str
        sale_currency: str
        sale_price: str
        sanitized_images: str
        state_of_vehicle: str
        title: str
        transmission: str
        trim: str
        unit_price: str
        url: str
        vehicle_id: str
        vehicle_registration_plate: str
        vehicle_specifications: str
        vehicle_type: str
        vin: str
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
    class Availability:
        available: str
        not_available: str
        pending: str
    class BodyStyle:
        convertible: str
        coupe: str
        crossover: str
        estate: str
        grandtourer: str
        hatchback: str
        minibus: str
        minivan: str
        mpv: str
        none: str
        other: str
        pickup: str
        roadster: str
        saloon: str
        sedan: str
        small_car: str
        sportscar: str
        supercar: str
        supermini: str
        suv: str
        truck: str
        van: str
        wagon: str
    class Condition:
        excellent: str
        fair: str
        good: str
        none: str
        other: str
        poor: str
        very_good: str
    class Drivetrain:
        awd: str
        four_wd: str
        fwd: str
        none: str
        other: str
        rwd: str
        two_wd: str
    class FuelType:
        diesel: str
        electric: str
        flex: str
        gasoline: str
        hybrid: str
        none: str
        other: str
        petrol: str
        plugin_hybrid: str
    class StateOfVehicle:
        cpo: str
        new: str
        used: str
    class Transmission:
        automatic: str
        manual: str
        none: str
        other: str
    class VehicleType:
        boat: str
        car_truck: str
        commercial: str
        motorcycle: str
        other: str
        powersport: str
        rv_camper: str
        trailer: str
    @classmethod
    def get_endpoint(cls): ...
    def api_create(self, parent_id, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_update(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_augmented_realities_metadata(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_channels_to_integrity_status(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_videos_metadata(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
