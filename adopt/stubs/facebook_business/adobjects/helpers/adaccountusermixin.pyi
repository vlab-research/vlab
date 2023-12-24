from _typeshed import Incomplete
from facebook_business.adobjects.adaccount import AdAccount as AdAccount
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.adobjects.page import Page as Page
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class AdAccountUserMixin:
    class Field:
        id: str
        name: str
        permissions: str
        role: str
    class Permission:
        account_admin: int
        admanager_read: int
        admanager_write: int
        billing_read: int
        billing_write: int
        reports: int
    class Role:
        administrator: int
        analyst: int
        manager: int
    @classmethod
    def get_endpoint(cls): ...
    def get_ad_accounts(self, fields: Incomplete | None = None, params: Incomplete | None = None): ...
    def get_ad_account(self, fields: Incomplete | None = None, params: Incomplete | None = None): ...
    def get_pages(self, fields: Incomplete | None = None, params: Incomplete | None = None): ...
