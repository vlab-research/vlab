from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class LeadGenAppointmentBookingInfo(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        advertiser_timezone_offset: str
        appointment_durations: str
        appointment_slots_by_day: str
