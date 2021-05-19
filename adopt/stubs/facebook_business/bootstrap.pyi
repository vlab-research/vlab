from facebook_business.adobjects import *
from facebook_business.api import FacebookAdsApi as FacebookAdsApi
from facebook_business.exceptions import FacebookError as FacebookError
from facebook_business.session import FacebookSession as FacebookSession
from typing import Any

this_dir: Any
repo_dir: Any

class Authentication:
    @property
    def is_authenticated(cls): ...
    @classmethod
    def load_config(cls): ...
    @classmethod
    def auth(cls): ...

def auth(): ...
