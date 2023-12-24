from _typeshed import Incomplete
from enum import Enum
from facebook_business.api import FacebookAdsApi as FacebookAdsApi, FacebookRequest as FacebookRequest
from facebook_business.exceptions import FacebookError as FacebookError, FacebookRequestError as FacebookRequestError
from facebook_business.session import FacebookSession as FacebookSession

class Reasons(Enum):
    API: str
    SDK: str

class CrashReporter:
    reporter_instance: Incomplete
    logger: Incomplete
    def __init__(self, app_id, excepthook) -> None: ...
    @classmethod
    def enable(cls) -> None: ...
    @classmethod
    def disable(cls) -> None: ...
    @classmethod
    def enableLogging(cls) -> None: ...
    @classmethod
    def disableLogging(cls) -> None: ...
    @classmethod
    def logging(cls, info) -> None: ...
