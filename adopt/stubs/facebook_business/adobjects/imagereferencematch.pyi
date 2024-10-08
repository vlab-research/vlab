from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class ImageReferenceMatch(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        conflicting_countries: str
        country_resolution_history: str
        creation_time: str
        current_conflict_resolved_countries: str
        displayed_match_state: str
        dispute_form_data_entries_with_translations: str
        expiration_time: str
        id: str
        match_state: str
        matched_reference_copyright: str
        matched_reference_owner: str
        modification_history: str
        reference_copyright: str
        reference_owner: str
        rejection_form_data_entries_with_translations: str
        resolution_reason: str
        update_time: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
