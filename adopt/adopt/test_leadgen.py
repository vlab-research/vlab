import pytest

from .leadgen import extract_lead_data, LeadData, TRACKING_PARAM_KEYS


def test_extract_lead_data_separates_metadata_from_responses():
    lead_response = {
        "id": "lead123",
        "created_time": "2024-01-15T10:30:00+0000",
        "field_data": [
            {"name": "stratum_id", "values": ["stratum1"]},
            {"name": "study_id", "values": ["study123"]},
            {"name": "email", "values": ["user@example.com"]},
            {"name": "phone", "values": ["555-1234"]},
        ]
    }

    lead = extract_lead_data(lead_response)

    assert lead.lead_id == "lead123"
    assert lead.stratum_id == "stratum1"
    assert lead.study_id == "study123"
    assert lead.metadata == {
        "stratum_id": "stratum1",
        "study_id": "study123",
    }
    assert lead.user_responses == {
        "email": "user@example.com",
        "phone": "555-1234",
    }


def test_extract_lead_data_handles_additional_metadata_keys():
    lead_response = {
        "id": "lead123",
        "created_time": "2024-01-15T10:30:00+0000",
        "field_data": [
            {"name": "stratum_id", "values": ["stratum1"]},
            {"name": "custom_tag", "values": ["value1"]},
            {"name": "email", "values": ["user@example.com"]},
        ]
    }

    lead = extract_lead_data(lead_response, additional_metadata_keys={"custom_tag"})

    assert lead.metadata == {
        "stratum_id": "stratum1",
        "custom_tag": "value1",
    }
    assert lead.user_responses == {
        "email": "user@example.com",
    }


def test_extract_lead_data_joins_multiple_values():
    lead_response = {
        "id": "lead123",
        "created_time": "2024-01-15T10:30:00+0000",
        "field_data": [
            {"name": "interests", "values": ["sports", "music", "art"]},
        ]
    }

    lead = extract_lead_data(lead_response)

    assert lead.user_responses["interests"] == "sports, music, art"


def test_extract_lead_data_handles_missing_tracking_params():
    lead_response = {
        "id": "lead123",
        "created_time": "2024-01-15T10:30:00+0000",
        "field_data": [
            {"name": "email", "values": ["user@example.com"]},
        ]
    }

    lead = extract_lead_data(lead_response)

    assert lead.stratum_id is None
    assert lead.study_id is None
    assert lead.campaign_name is None
    assert lead.metadata == {}
    assert lead.user_responses == {
        "email": "user@example.com",
    }


def test_extract_lead_data_handles_all_tracking_params():
    lead_response = {
        "id": "lead123",
        "created_time": "2024-01-15T10:30:00+0000",
        "field_data": [
            {"name": "stratum_id", "values": ["stratum1"]},
            {"name": "study_id", "values": ["study123"]},
            {"name": "campaign_name", "values": ["campaign1"]},
            {"name": "gender", "values": ["female"]},
            {"name": "age", "values": ["18-24"]},
            {"name": "email", "values": ["user@example.com"]},
        ]
    }

    lead = extract_lead_data(lead_response, additional_metadata_keys={"gender", "age"})

    assert lead.stratum_id == "stratum1"
    assert lead.study_id == "study123"
    assert lead.campaign_name == "campaign1"
    assert lead.metadata == {
        "stratum_id": "stratum1",
        "study_id": "study123",
        "campaign_name": "campaign1",
        "gender": "female",
        "age": "18-24",
    }
    assert lead.user_responses == {
        "email": "user@example.com",
    }
