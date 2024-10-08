from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class RegionalRegulationIdentities(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        taiwan_finserv_beneficiary: str
        taiwan_finserv_payer: str
