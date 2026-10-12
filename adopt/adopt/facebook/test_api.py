import json
from unittest.mock import Mock, patch

import pytest
from facebook_business.exceptions import FacebookRequestError

from .api import FAIL_FAST, call, fail_fast, fatal_code, is_rate_limit


def _graph_error(code, subcode=None, user_msg=None):
    body = {"error": {"message": "Call was not successful", "code": code}}
    if subcode is not None:
        body["error"]["error_subcode"] = subcode
    if user_msg is not None:
        body["error"]["error_user_msg"] = user_msg
    return FacebookRequestError(
        "Call was not successful", {}, 400, {}, json.dumps(body)
    )


def test_rate_limit_is_retryable_by_default():
    assert fatal_code(_graph_error(17)) is False


def test_an_unknown_code_is_fatal_by_default():
    assert fatal_code(_graph_error(100)) is True


def test_fail_fast_makes_every_error_fatal():
    with fail_fast():
        assert fatal_code(_graph_error(17)) is True
        assert fatal_code(_graph_error(2)) is True


def test_fail_fast_is_scoped_to_its_block():
    assert FAIL_FAST.get() is False
    with fail_fast():
        assert FAIL_FAST.get() is True
    assert FAIL_FAST.get() is False


def test_call_raises_immediately_under_fail_fast_instead_of_sleeping():
    fn = Mock(side_effect=_graph_error(17, 2446079))

    with patch("time.sleep") as sleep, fail_fast():
        with pytest.raises(FacebookRequestError):
            call(fn)

    assert fn.call_count == 1
    sleep.assert_not_called()


def test_call_sleeps_and_retries_a_rate_limit_without_fail_fast():
    fn = Mock(side_effect=[_graph_error(17), "ok"])

    with patch("time.sleep") as sleep:
        assert call(fn) == "ok"

    assert fn.call_count == 2
    sleep.assert_called_once()


def test_is_rate_limit_matches_code_17_only():
    assert is_rate_limit(_graph_error(17, 2446079, "Please wait a bit"))
    assert not is_rate_limit(_graph_error(80004))


BUC = {"1342820622846299": [{"type": "ads_management", "call_count": 12, "estimated_time_to_regain_access": 0}]}


def _usage_api(status, body, headers):
    from facebook_business.session import FacebookSession

    from .api import UsageLoggingApi

    api = UsageLoggingApi(FacebookSession(None, None, "token"))
    response = Mock(text=body, headers=headers, status_code=status)
    api._session.requests.request = Mock(return_value=response)
    return api


def _usage_records(caplog):
    return [
        json.loads(r.getMessage().split(" ", 1)[1])
        for r in caplog.records
        if r.name == "adopt.facebook.usage"
    ]


def test_usage_is_logged_for_a_successful_call(caplog):
    caplog.set_level("INFO", logger="adopt.facebook.usage")
    api = _usage_api(200, "{}", {"X-Business-Use-Case-Usage": json.dumps(BUC)})

    api.call("GET", ("120253893206290150", "adsets"))

    [record] = _usage_records(caplog)
    assert record["path"] == "/120253893206290150/adsets"
    assert record["buc"] == BUC
    assert "error_code" not in record


def test_usage_is_logged_for_a_throttled_call(caplog):
    caplog.set_level("INFO", logger="adopt.facebook.usage")
    body = json.dumps({"error": {"message": "User request limit reached", "code": 17}})
    api = _usage_api(400, body, {"x-business-use-case-usage": json.dumps(BUC)})

    with pytest.raises(FacebookRequestError):
        api.call("GET", ("120253893206290150", "adsets"))

    [record] = _usage_records(caplog)
    assert record["error_code"] == 17
    assert record["buc"] == BUC


def test_usage_log_drops_the_query_string_of_a_paging_url(caplog):
    caplog.set_level("INFO", logger="adopt.facebook.usage")
    api = _usage_api(200, "{}", {})

    api.call("GET", "https://graph.facebook.com/v22.0/123/ads?access_token=SECRET&after=x")

    [record] = _usage_records(caplog)
    assert record["path"] == "/v22.0/123/ads"
    assert "SECRET" not in caplog.text
