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
