from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker
from typing import Any, Optional

class AdAccountActivity(AbstractCrudObject):
    def __init__(self, fbid: Optional[Any] = ..., parent_id: Optional[Any] = ..., api: Optional[Any] = ...) -> None: ...
    class Field(AbstractObject.Field):
        created_by: str = ...
        created_time: str = ...
        credit_new: str = ...
        credit_old: str = ...
        currency_new: str = ...
        currency_old: str = ...
        daily_spend_limit_new: str = ...
        daily_spend_limit_old: str = ...
        event_time: str = ...
        event_type: str = ...
        funding_id_new: str = ...
        funding_id_old: str = ...
        grace_period_time_new: str = ...
        grace_period_time_old: str = ...
        id: str = ...
        manager_id_new: str = ...
        manager_id_old: str = ...
        name_new: str = ...
        name_old: str = ...
        spend_cap_new: str = ...
        spend_cap_old: str = ...
        status_new: str = ...
        status_old: str = ...
        terms_new: str = ...
        terms_old: str = ...
        tier_new: str = ...
        tier_old: str = ...
        time_updated_new: str = ...
        time_updated_old: str = ...
    def api_get(self, fields: Optional[Any] = ..., params: Optional[Any] = ..., batch: Optional[Any] = ..., success: Optional[Any] = ..., failure: Optional[Any] = ..., pending: bool = ...): ...