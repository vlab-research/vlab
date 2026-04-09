from facebook_business.adobjects.customaudience import CustomAudience

from .facebook.state import StateNameError
from .malaria import add_audience_targeting
from .study_conf import StratumConf


def _make_audience(name, id_):
    a = CustomAudience()
    a["name"] = name
    a["id"] = id_
    return a


class MockState:
    def __init__(self, audiences):
        self._audiences = {a["name"]: a for a in audiences}

    def get_audience(self, name):
        if name not in self._audiences:
            raise StateNameError(f"Audience not found with name: {name}")
        return self._audiences[name]


def _make_stratum(facebook_targeting, audiences=None, excluded_audiences=None):
    return StratumConf(
        id="test-stratum",
        quota=1.0,
        creatives=[],
        audiences=audiences or [],
        excluded_audiences=excluded_audiences or [],
        facebook_targeting=facebook_targeting,
        metadata={},
    )


def test_add_audience_targeting_merges_static_excluded_with_dynamic():
    """Static excluded_custom_audiences from facebook_targeting must be preserved
    when dynamic excluded_audiences are resolved and added."""
    static_hpv = {"id": "111", "name": "HPV respondents"}
    state = MockState([_make_audience("Test Respondents", "222")])
    stratum = _make_stratum(
        facebook_targeting={"excluded_custom_audiences": [static_hpv]},
        excluded_audiences=["Test Respondents"],
    )

    targeting = add_audience_targeting(state, stratum)

    assert targeting["excluded_custom_audiences"] == [
        static_hpv,
        {"id": "222"},
    ]


def test_add_audience_targeting_keeps_static_excluded_when_dynamic_not_found():
    """Static exclusions are preserved even when the dynamic audience doesn't
    exist in Facebook yet (not created by update_audience job)."""
    static_hpv = {"id": "111", "name": "HPV respondents"}
    state = MockState([])  # dynamic audience not in Facebook yet
    stratum = _make_stratum(
        facebook_targeting={"excluded_custom_audiences": [static_hpv]},
        excluded_audiences=["Test Respondents"],
    )

    targeting = add_audience_targeting(state, stratum)

    assert targeting["excluded_custom_audiences"] == [static_hpv]


def test_add_audience_targeting_with_no_static_excluded():
    """Works correctly when facebook_targeting has no existing excluded audiences."""
    state = MockState([_make_audience("Test Respondents", "222")])
    stratum = _make_stratum(
        facebook_targeting={},
        excluded_audiences=["Test Respondents"],
    )

    targeting = add_audience_targeting(state, stratum)

    assert targeting["excluded_custom_audiences"] == [{"id": "222"}]
