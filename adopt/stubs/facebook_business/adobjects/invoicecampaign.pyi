from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from typing import Any, Optional

class InvoiceCampaign(AbstractObject):
    def __init__(self, api: Optional[Any] = ...) -> None: ...
    class Field(AbstractObject.Field):
        ad_account_id: str = ...
        billed_amount_details: str = ...
        campaign_id: str = ...
        campaign_name: str = ...
        clicks: str = ...
        conversions: str = ...
        impressions: str = ...
        tags: str = ...
