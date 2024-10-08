from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class AudioVisualReferenceMatch(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        audio_conflicting_segments: str
        audio_current_conflict_resolved_segments: str
        audio_segment_resolution_history: str
        conflict_type: str
        conflicting_countries: str
        country_resolution_history: str
        creation_time: str
        current_conflict_resolved_countries: str
        displayed_match_state: str
        dispute_form_data_entries_with_translations: str
        expiration_time: str
        id: str
        is_disputable: str
        match_state: str
        matched_overlap_percentage: str
        matched_owner_match_duration_in_sec: str
        matched_reference_owner: str
        modification_history: str
        num_matches_on_matched_side: str
        num_matches_on_ref_side: str
        ref_owner_match_duration_in_sec: str
        reference_overlap_percentage: str
        reference_owner: str
        rejection_form_data_entries_with_translations: str
        resolution_details: str
        resolution_reason: str
        update_time: str
        views_on_matched_side: str
        visual_conflicting_segments: str
        visual_current_conflict_resolved_segments: str
        visual_segment_resolution_history: str
