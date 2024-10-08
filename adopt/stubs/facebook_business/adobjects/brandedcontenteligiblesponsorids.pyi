from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class BrandedContentEligibleSponsorIDs(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        fb_page: str
        ig_account_v2: str
        ig_approval_needed: str
