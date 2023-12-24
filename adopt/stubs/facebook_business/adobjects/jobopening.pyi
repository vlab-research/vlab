from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class JobOpening(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        address: str
        application_callback_url: str
        created_time: str
        description: str
        errors: str
        external_company_facebook_url: str
        external_company_full_address: str
        external_company_id: str
        external_company_name: str
        external_id: str
        id: str
        job_status: str
        latitude: str
        longitude: str
        offsite_application_url: str
        page: str
        photo: str
        platform_review_status: str
        post: str
        remote_type: str
        review_rejection_reasons: str
        title: str
        type: str
    class JobStatus:
        closed: str
        draft: str
        open: str
        provisional: str
    class PlatformReviewStatus:
        approved: str
        pending: str
        rejected: str
    class ReviewRejectionReasons:
        adult_content: str
        discrimination: str
        drugs: str
        generic_default: str
        illegal: str
        impersonation: str
        misleading: str
        multilevel_marketing: str
        personal_info: str
        sexual: str
    class Type:
        contract: str
        full_time: str
        internship: str
        part_time: str
        volunteer: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
