from facebook_business.adobjects import agencyclientdeclaration as agencyclientdeclaration
from typing import Any, Optional

class AdAccountMixin:
    class AccountStatus:
        active: int = ...
        disabled: int = ...
        in_grace_period: int = ...
        pending_closure: int = ...
        pending_review: int = ...
        temporarily_unavailable: int = ...
        unsettled: int = ...
    class AgencyClientDeclaration(agencyclientdeclaration.AgencyClientDeclaration.Field): ...
    class Capabilities:
        bulk_account: str = ...
        can_use_reach_and_frequency: str = ...
        direct_sales: str = ...
        view_tags: str = ...
    class TaxIdStatus:
        account_is_personal: int = ...
        offline_vat_validation_failed: int = ...
        unknown: int = ...
        vat_information_required: int = ...
        vat_not_required: int = ...
    @classmethod
    def get_my_account(cls, api: Optional[Any] = ...): ...
    def opt_out_user_from_targeting(self, schema: Any, users: Any, is_raw: bool = ..., app_ids: Optional[Any] = ..., pre_hashed: Optional[Any] = ...): ...
