from _typeshed import Incomplete
from collections.abc import Generator
from facebook_business import apiconfig as apiconfig
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.exceptions import FacebookBadObjectError as FacebookBadObjectError, FacebookBadParameterError as FacebookBadParameterError, FacebookRequestError as FacebookRequestError, FacebookUnavailablePropertyException as FacebookUnavailablePropertyException
from facebook_business.session import FacebookSession as FacebookSession
from facebook_business.typechecker import TypeChecker as TypeChecker
from facebook_business.utils import api_utils as api_utils, urls as urls

class FacebookResponse:
    def __init__(self, body: Incomplete | None = None, http_status: Incomplete | None = None, headers: Incomplete | None = None, call: Incomplete | None = None) -> None: ...
    def body(self): ...
    def json(self): ...
    def headers(self): ...
    def etag(self): ...
    def status(self): ...
    def is_success(self): ...
    def is_failure(self): ...
    def error(self): ...

class FacebookAdsApi:
    SDK_VERSION: Incomplete
    API_VERSION: Incomplete
    HTTP_METHOD_GET: str
    HTTP_METHOD_POST: str
    HTTP_METHOD_DELETE: str
    HTTP_DEFAULT_HEADERS: Incomplete
    def __init__(self, session, api_version: Incomplete | None = None, enable_debug_logger: bool = False) -> None: ...
    def get_num_requests_attempted(self): ...
    def get_num_requests_succeeded(self): ...
    @classmethod
    def init(cls, app_id: Incomplete | None = None, app_secret: Incomplete | None = None, access_token: Incomplete | None = None, account_id: Incomplete | None = None, api_version: Incomplete | None = None, proxies: Incomplete | None = None, timeout: Incomplete | None = None, debug: bool = False, crash_log: bool = True): ...
    @classmethod
    def set_default_api(cls, api_instance) -> None: ...
    @classmethod
    def get_default_api(cls): ...
    @classmethod
    def set_default_account_id(cls, account_id) -> None: ...
    @classmethod
    def get_default_account_id(cls): ...
    def call(self, method, path, params: Incomplete | None = None, headers: Incomplete | None = None, files: Incomplete | None = None, url_override: Incomplete | None = None, api_version: Incomplete | None = None): ...
    def new_batch(self): ...

class FacebookAdsApiBatch:
    def __init__(self, api, success: Incomplete | None = None, failure: Incomplete | None = None) -> None: ...
    def __len__(self) -> int: ...
    def add(self, method, relative_path, params: Incomplete | None = None, headers: Incomplete | None = None, files: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, request: Incomplete | None = None): ...
    def add_request(self, request, success: Incomplete | None = None, failure: Incomplete | None = None): ...
    def execute(self): ...

class FacebookRequest:
    def __init__(self, node_id, method, endpoint, api: Incomplete | None = None, param_checker=..., target_class: Incomplete | None = None, api_type: Incomplete | None = None, allow_file_upload: bool = False, response_parser: Incomplete | None = None, include_summary: bool = True, api_version: Incomplete | None = None) -> None: ...
    def add_file(self, file_path): ...
    def add_files(self, files): ...
    def add_field(self, field): ...
    def add_fields(self, fields): ...
    def add_param(self, key, value): ...
    def add_params(self, params): ...
    def get_fields(self): ...
    def get_params(self): ...
    def execute(self): ...
    def add_to_batch(self, batch, success: Incomplete | None = None, failure: Incomplete | None = None) -> None: ...

class Cursor:
    params: Incomplete
    def __init__(self, source_object: Incomplete | None = None, target_objects_class: Incomplete | None = None, fields: Incomplete | None = None, params: Incomplete | None = None, include_summary: bool = True, api: Incomplete | None = None, node_id: Incomplete | None = None, endpoint: Incomplete | None = None, object_parser: Incomplete | None = None) -> None: ...
    def __len__(self) -> int: ...
    def __iter__(self): ...
    def __next__(self): ...
    next = __next__
    def __getitem__(self, index): ...
    def headers(self): ...
    def total(self): ...
    def summary(self): ...
    def load_next_page(self): ...
    def get_one(self): ...
    def build_objects_from_response(self, response): ...

def open_files(files) -> Generator[Incomplete, None, None]: ...
