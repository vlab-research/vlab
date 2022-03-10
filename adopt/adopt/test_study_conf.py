from .study_conf import DestinationRecruitmentExperiment, get_campaign_names


def test_get_campaign_names_gets_base_when_not_experiment():
    assert get_campaign_names("foo-bar", None) == ["foo-bar"]


def test_get_campaign_names_gets_versions_of_base_when_experiment():
    re = DestinationRecruitmentExperiment(arms=3, creative_mapping={})
    assert get_campaign_names("foo-bar", re) == ["foo-bar-1", "foo-bar-2", "foo-bar-3"]
