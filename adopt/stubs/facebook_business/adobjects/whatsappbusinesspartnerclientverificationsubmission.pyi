from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class WhatsAppBusinessPartnerClientVerificationSubmission(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        client_business_id: str
        id: str
        rejection_reasons: str
        submitted_info: str
        submitted_time: str
        update_time: str
        verification_status: str
    class RejectionReasons:
        address_not_matching: str
        legal_name_not_matching: str
        none: str
        website_not_matching: str
    class VerificationStatus:
        approved: str
        failed: str
        pending: str
        revoked: str
