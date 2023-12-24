from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.api import FacebookAdsApi as FacebookAdsApi
from facebook_business.exceptions import FacebookBadObjectError as FacebookBadObjectError
from facebook_business.session import FacebookSession as FacebookSession

class TargetingSearch(AbstractObject):
    class DemographicSearchClasses:
        demographics: str
        ethnic_affinity: str
        family_statuses: str
        generation: str
        home_ownership: str
        home_type: str
        home_value: str
        household_composition: str
        income: str
        industries: str
        life_events: str
        markets: str
        moms: str
        net_worth: str
        office_type: str
        politics: str
    class TargetingSearchTypes:
        country: str
        education: str
        employer: str
        geolocation: str
        geometadata: str
        interest: str
        interest_suggestion: str
        interest_validate: str
        keyword: str
        locale: str
        major: str
        position: str
        radius_suggestion: str
        targeting_category: str
        zipcode: str
    @classmethod
    def search(cls, params: Incomplete | None = None, api: Incomplete | None = None): ...
