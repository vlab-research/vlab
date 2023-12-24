from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class BusinessRoleRequest(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        created_by: str
        created_time: str
        email: str
        expiration_time: str
        expiry_time: str
        finance_role: str
        id: str
        invite_link: str
        ip_role: str
        owner: str
        role: str
        status: str
        updated_by: str
        updated_time: str
    class Role:
        admin: str
        ads_rights_reviewer: str
        value_default: str
        developer: str
        employee: str
        finance_analyst: str
        finance_edit: str
        finance_editor: str
        finance_view: str
        manage: str
        partner_center_admin: str
        partner_center_analyst: str
        partner_center_education: str
        partner_center_marketing: str
        partner_center_operations: str
    def api_delete(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_update(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
