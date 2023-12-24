from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class FlexibleTargeting(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        behaviors: str
        college_years: str
        connections: str
        custom_audiences: str
        education_majors: str
        education_schools: str
        education_statuses: str
        ethnic_affinity: str
        family_statuses: str
        friends_of_connections: str
        generation: str
        home_ownership: str
        home_type: str
        home_value: str
        household_composition: str
        income: str
        industries: str
        interested_in: str
        interests: str
        life_events: str
        moms: str
        net_worth: str
        office_type: str
        politics: str
        relationship_statuses: str
        user_adclusters: str
        work_employers: str
        work_positions: str
