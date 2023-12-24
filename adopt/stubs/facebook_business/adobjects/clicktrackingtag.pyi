from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject

class ClickTrackingTag(AbstractCrudObject):
    class Field:
        add_template_param: str
        ad_id: str
        id: str
        url: str
    @classmethod
    def get_endpoint(cls): ...
    def get_node_path(self): ...
    def remote_delete(self, params: Incomplete | None = None): ...
