from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AgencyClientDeclaration(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        agency_representing_client: str
        client_based_in_france: str
        client_city: str
        client_country_code: str
        client_email_address: str
        client_name: str
        client_postal_code: str
        client_province: str
        client_street: str
        client_street2: str
        has_written_mandate_from_advertiser: str
        is_client_paying_invoices: str
