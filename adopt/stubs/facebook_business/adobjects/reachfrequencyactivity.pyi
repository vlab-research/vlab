from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class ReachFrequencyActivity(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        account_id: str
        campaign_active: str
        campaign_started: str
        creative_uploaded: str
        io_approved: str
        sf_link: str
