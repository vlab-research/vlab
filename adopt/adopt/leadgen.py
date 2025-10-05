"""
Utilities for extracting and processing lead data from Facebook Lead Gen forms.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set


@dataclass
class LeadData:
    """Structured lead data extracted from Facebook API response."""
    lead_id: str
    created_time: str
    stratum_id: Optional[str]
    study_id: Optional[str]
    campaign_name: Optional[str]
    metadata: Dict[str, str]  # All tracking parameters
    user_responses: Dict[str, str]  # User-submitted field data


# Known tracking parameter keys we inject
TRACKING_PARAM_KEYS = {"stratum_id", "study_id", "campaign_name"}


def extract_lead_data(
    lead_response: Dict[str, Any],
    additional_metadata_keys: Optional[Set[str]] = None,
) -> LeadData:
    """
    Extract structured lead data from Facebook API response.

    Args:
        lead_response: Raw lead data from Facebook API
        additional_metadata_keys: Additional keys to treat as metadata
                                 (beyond TRACKING_PARAM_KEYS)

    Returns:
        LeadData with separated metadata and user responses
    """
    all_metadata_keys = TRACKING_PARAM_KEYS.copy()
    if additional_metadata_keys:
        all_metadata_keys.update(additional_metadata_keys)

    # Parse field_data array
    metadata = {}
    user_responses = {}

    for field in lead_response.get("field_data", []):
        name = field["name"]
        values = field["values"]

        # Facebook returns values as list, join if multiple
        value = ", ".join(values) if len(values) > 1 else values[0]

        if name in all_metadata_keys:
            metadata[name] = value
        else:
            user_responses[name] = value

    return LeadData(
        lead_id=lead_response["id"],
        created_time=lead_response["created_time"],
        stratum_id=metadata.get("stratum_id"),
        study_id=metadata.get("study_id"),
        campaign_name=metadata.get("campaign_name"),
        metadata=metadata,
        user_responses=user_responses,
    )


def get_leads_for_form(
    form_id: str,
    api,
    fields: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve all leads for a specific form.

    Args:
        form_id: Facebook Lead Gen Form ID
        api: FacebookAdsApi instance
        fields: Optional list of fields to retrieve

    Returns:
        List of raw lead data dictionaries
    """
    from facebook_business.adobjects.leadgenform import LeadgenForm
    from .facebook.api import call

    form = LeadgenForm(form_id, api=api)

    if fields is None:
        fields = ["id", "created_time", "field_data"]

    leads = call(form.get_leads, fields=fields)
    return [lead.export_all_data() for lead in leads]
