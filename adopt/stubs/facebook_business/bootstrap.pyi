from facebook_business.adobjects import *
from _typeshed import Incomplete
from facebook_business.api import FacebookAdsApi as FacebookAdsApi
from facebook_business.exceptions import FacebookError as FacebookError
from facebook_business.session import FacebookSession as FacebookSession

this_dir: Incomplete
repo_dir: Incomplete

class Authentication:
    @property
    def is_authenticated(cls): ...
    @classmethod
    def load_config(cls): ...
    @classmethod
    def auth(cls): ...

def auth(): ...
