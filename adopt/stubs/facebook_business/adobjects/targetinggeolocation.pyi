from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class TargetingGeoLocation(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        cities: str
        countries: str
        country_groups: str
        custom_locations: str
        electoral_districts: str
        geo_markets: str
        large_geo_areas: str
        location_cluster_ids: str
        location_expansion: str
        location_types: str
        medium_geo_areas: str
        metro_areas: str
        neighborhoods: str
        places: str
        political_districts: str
        regions: str
        small_geo_areas: str
        subcities: str
        subneighborhoods: str
        zips: str
