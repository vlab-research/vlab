from _typeshed import Incomplete
from facebook_business.exceptions import FacebookBadObjectError as FacebookBadObjectError

class CustomAudienceMixin:
    class Schema:
        uid: str
        email_hash: str
        phone_hash: str
        mobile_advertiser_id: str
        class MultiKeySchema:
            extern_id: str
            email: str
            phone: str
            gen: str
            doby: str
            dobm: str
            dobd: str
            ln: str
            fn: str
            fi: str
            ct: str
            st: str
            zip: str
            madid: str
            country: str
            appuid: str
    @classmethod
    def format_params(cls, schema, users, is_raw: bool = False, app_ids: Incomplete | None = None, pre_hashed: Incomplete | None = None, session: Incomplete | None = None): ...
    @classmethod
    def normalize_key(cls, key_name, key_value: Incomplete | None = None): ...
    def add_users(self, schema, users, is_raw: bool = False, app_ids: Incomplete | None = None, pre_hashed: Incomplete | None = None, session: Incomplete | None = None): ...
    def remove_users(self, schema, users, is_raw: bool = False, app_ids: Incomplete | None = None, pre_hashed: Incomplete | None = None, session: Incomplete | None = None): ...
    def share_audience(self, account_ids): ...
    def unshare_audience(self, account_ids): ...
