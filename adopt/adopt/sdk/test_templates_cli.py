"""Tests for the `vlab template` command group.

No database and no network: the group talks to Meta directly rather than to the
vlab server, so unlike `test_cli.py` there is no FastAPI app to drive. The mock
boundary is the same one `authoring/test_templates.py` and
`server/test_meta.py` use -- `FacebookAdsApi.call` -- and `plan` /
`check-targeting --spec` need no boundary at all, because planning is pure.

What is asserted here is the CLI's own contract, not the library's: dry run is
the default, a write needs `--create` or `--yes`, an unknown key in a spec is
an error rather than a silent drop, image paths resolve relative to the spec,
`--json` is machine-readable, and a Meta rejection exits 1 with a message
instead of a traceback.
"""

from __future__ import annotations

import json
from typing import List
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from facebook_business.api import FacebookAdsApi

from ..authoring.test_templates import _as_meta_returns_it, _Graph
from .cli import cli

PAGE = "1855355231229529"
ACCOUNT = "act_1342820622846299"

SPEC = """
account: act_1342820622846299
name: VL Pulse Nigeria
properties: [genders, age_min, age_max, geo_locations]
adsets:
  - name: Kwara - Men
    kind: messenger
    targeting:
      genders: [1]
      age_min: 18
      age_max: 65
      geo_locations:
        regions: [{key: "2619", name: Kwara, country: "NG"}]
        location_types: [home, recent]
ads:
  - name: vlpulse-ng-1
    kind: messenger
    page_id: "1855355231229529"
    message: Tell us what you think.
    headline: Chat with us
    image_hash: 7fabd5c7072f2242195f6f5dbbfb512c
"""


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def spec(tmp_path):
    path = tmp_path / "spec.yaml"
    path.write_text(SPEC, encoding="utf8")
    return str(path)


@pytest.fixture(autouse=True)
def token(monkeypatch):
    """A token in the environment, so tests exercise the ordinary path.

    Set for every test rather than per-test: the interesting assertion is that
    a MISSING token is a clean message, and that is one test which unsets it.
    """
    monkeypatch.setenv("FACEBOOK_ACCESS_TOKEN", "TEST-TOKEN")
    monkeypatch.setenv("FACEBOOK_APP_ID", "app-id")
    monkeypatch.setenv("FACEBOOK_APP_SECRET", "app-secret")


def _graph(**bodies):
    g = _Graph(bodies)

    def _call(api_self, method, path, params=None, files=None, **kwargs):
        return g(api_self, method, path, params=params, files=files, **kwargs)

    return patch.object(FacebookAdsApi, "call", _call), g


def _run(runner, args: List[str], **kw):
    return runner.invoke(cli, args, obj={}, **kw)


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------


def test_plan_is_pure_and_needs_no_token(runner, spec, monkeypatch):
    """Planning touches nothing, so it must work with no credentials at all.

    That is what makes it usable in review and in CI on a machine that has no
    business holding a Facebook token.
    """
    monkeypatch.delenv("FACEBOOK_ACCESS_TOKEN", raising=False)
    with patch.object(
        FacebookAdsApi, "call", side_effect=AssertionError("plan hit the network")
    ):
        result = _run(runner, ["template", "plan", spec])

    assert result.exit_code == 0, result.output
    assert "DRY RUN" in result.output
    assert "Templates - VL Pulse Nigeria" in result.output


def test_plan_json_is_the_plan(runner, spec):
    result = _run(runner, ["template", "plan", spec, "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["campaign_name"] == "Templates - VL Pulse Nigeria"
    assert [c["node"] for c in payload["creates"]] == [
        "campaign",
        "adset",
        "creative",
        "ad",
    ]
    assert all(
        c["params"].get("status") == "PAUSED"
        for c in payload["creates"]
        if c["node"] in ("campaign", "adset", "ad")
    )


def test_an_unknown_spec_key_is_an_error_not_a_silent_drop(runner, tmp_path):
    """A misspelled optional key that is quietly ignored produces a template
    that is subtly not the one you wrote, on someone's ad account, with nothing
    saying so.
    """
    path = tmp_path / "spec.yaml"
    path.write_text(SPEC.replace("    kind: messenger", "    kimd: messenger"), "utf8")
    result = _run(runner, ["template", "plan", str(path)])
    assert result.exit_code != 0
    assert "unknown key(s) ['kimd']" in result.output


def test_an_unknown_top_level_key_is_an_error(runner, tmp_path):
    path = tmp_path / "spec.yaml"
    path.write_text(SPEC + "\nbudget: 100\n", "utf8")
    result = _run(runner, ["template", "plan", str(path)])
    assert result.exit_code != 0
    assert "unknown top-level key(s) ['budget']" in result.output


def test_malformed_yaml_is_a_message_not_a_traceback(runner, tmp_path):
    """`yaml.YAMLError` is neither ValueError nor OSError, so it walks past
    `VlabGroup.invoke`. The same bug was found on `study.yaml` in review.
    """
    path = tmp_path / "spec.yaml"
    path.write_text("account: [unclosed\n", "utf8")
    result = _run(runner, ["template", "plan", str(path)])
    assert result.exit_code != 0
    assert "not valid YAML" in result.output
    assert "Traceback" not in result.output


def test_a_library_refusal_reaches_the_user_as_one_line(runner, tmp_path):
    """`TemplateError` is not in `cli.USER_ERRORS`; `TemplateGroup` catches it."""
    path = tmp_path / "spec.yaml"
    path.write_text(
        SPEC.replace("age_min: 18", "age_min: 18\n").replace(
            "properties: [genders, age_min, age_max, geo_locations]",
            "properties: [genders, publisher_platforms]",
        ),
        "utf8",
    )
    result = _run(runner, ["template", "plan", str(path)])
    assert result.exit_code != 0
    assert "publisher_platforms" in result.output
    assert "Traceback" not in result.output


def test_an_image_path_is_relative_to_the_spec_not_the_shell(runner, tmp_path):
    """A spec committed next to its images has to work from any directory."""
    (tmp_path / "ad.png").write_bytes(b"x")
    path = tmp_path / "spec.yaml"
    path.write_text(
        SPEC.replace(
            "    image_hash: 7fabd5c7072f2242195f6f5dbbfb512c", "    image: ./ad.png"
        ),
        "utf8",
    )
    with runner.isolated_filesystem():
        result = _run(runner, ["template", "plan", str(path), "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    image = next(c for c in payload["creates"] if c["node"] == "image")
    assert image["source"] == str(tmp_path / "ad.png")


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


def test_create_refuses_without_the_confirmation_flag(runner, spec):
    """Dry run is the default, everywhere. The plan is still printed, so the
    refusal is informative rather than merely obstructive.
    """
    with patch.object(
        FacebookAdsApi, "call", side_effect=AssertionError("wrote without --create")
    ):
        result = _run(runner, ["template", "create", spec])
    assert result.exit_code != 0
    assert "Refusing to create without --create" in result.output
    assert "Templates - VL Pulse Nigeria" in result.output


def test_create_applies_the_plan_and_reports_the_ids(runner, spec):
    sent = json.loads(_run(runner, ["template", "plan", spec, "--json"]).output)
    creative_params = next(
        c["params"] for c in sent["creates"] if c["node"] == "creative"
    )

    patcher, g = _graph(
        **{
            "GET campaigns": [{"data": []}],
            "POST campaigns": [{"id": "C1"}],
            "POST adsets": [{"id": "A1"}],
            "POST adcreatives": [{"id": "CR1"}],
            "POST ads": [{"id": "AD1"}],
            "GET CR1": [_as_meta_returns_it(creative_params, "CR1")],
        }
    )
    with patcher:
        result = _run(runner, ["template", "create", spec, "--create"])

    assert result.exit_code == 0, result.output
    assert "campaign  C1  PAUSED" in result.output
    assert "vlab template delete C1" in result.output


def test_create_json_carries_the_template_blob_for_a_creatives_conf(runner, spec):
    creative_params = next(
        c["params"]
        for c in json.loads(_run(runner, ["template", "plan", spec, "--json"]).output)[
            "creates"
        ]
        if c["node"] == "creative"
    )
    patcher, _ = _graph(
        **{
            "GET campaigns": [{"data": []}],
            "POST campaigns": [{"id": "C1"}],
            "POST adsets": [{"id": "A1"}],
            "POST adcreatives": [{"id": "CR1"}],
            "POST ads": [{"id": "AD1"}],
            "GET CR1": [_as_meta_returns_it(creative_params, "CR1")],
        }
    )
    with patcher:
        result = _run(runner, ["template", "create", spec, "--yes", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    template = payload["ads"][0]["template"]
    assert template["actor_id"] == PAGE
    assert template["object_story_spec"]["page_id"] == PAGE


def test_a_taken_campaign_name_exits_one_with_a_message(runner, spec):
    patcher, g = _graph(
        **{
            "GET campaigns": [
                {"data": [{"id": "OLD", "name": "Templates - VL Pulse Nigeria"}]}
            ]
        }
    )
    with patcher:
        result = _run(runner, ["template", "create", spec, "--create"])

    assert result.exit_code == 1
    assert "already exists" in result.output
    assert "Traceback" not in result.output
    assert [c for c in g.calls if c["method"] == "POST"] == []


def test_a_missing_token_is_a_message_naming_the_variable(runner, spec, monkeypatch):
    monkeypatch.delenv("FACEBOOK_ACCESS_TOKEN", raising=False)
    result = _run(runner, ["template", "create", spec, "--create"])
    assert result.exit_code != 0
    assert "FACEBOOK_ACCESS_TOKEN" in result.output


def test_a_token_without_an_app_secret_warns_about_appsecret_proof(
    runner, spec, monkeypatch
):
    monkeypatch.delenv("FACEBOOK_APP_SECRET", raising=False)
    monkeypatch.delenv("FACEBOOK_APP_ID", raising=False)
    patcher, _ = _graph(**{"GET campaigns": [{"data": []}]})
    with patcher:
        result = _run(
            runner,
            ["template", "create", spec, "--create"],
            catch_exceptions=True,
        )
    assert "appsecret_proof" in result.output


# ---------------------------------------------------------------------------
# creative
# ---------------------------------------------------------------------------


CREATIVE_ARGS = [
    "template",
    "creative",
    "--account",
    ACCOUNT,
    "--campaign",
    "C1",
    "--adset",
    "A1",
    "--name",
    "vlpulse-ng-1",
    "--page-id",
    PAGE,
    "--message",
    "Tell us what you think.",
    "--image-hash",
    "abc123",
]


def test_creative_adds_one_paused_ad_to_a_marked_campaign(runner):
    patcher, g = _graph(
        **{
            "GET C1": [{"id": "C1", "name": "Templates - Existing"}],
            "POST adcreatives": [{"id": "CR9"}],
            "POST ads": [{"id": "AD9"}],
            "GET CR9": [
                {"id": "CR9", "actor_id": PAGE, "object_story_spec": {"page_id": PAGE}}
            ],
        }
    )
    with patcher:
        result = _run(runner, CREATIVE_ARGS + ["--create"])

    assert result.exit_code == 0, result.output
    assert "ad      AD9" in result.output
    assert g.posted("ads")[0]["status"] == "PAUSED"


def test_creative_refuses_a_campaign_without_the_template_marker(runner):
    """The only thing between this command and a paused ad inside a live
    study's campaign.
    """
    patcher, g = _graph(**{"GET C1": [{"id": "C1", "name": "vlab-hpv-nigeria"}]})
    with patcher:
        result = _run(runner, CREATIVE_ARGS + ["--create"])

    assert result.exit_code == 1
    assert "does not start with" in result.output
    assert [c for c in g.calls if c["method"] == "POST"] == []


def test_creative_dry_runs_by_default(runner):
    with patch.object(
        FacebookAdsApi, "call", side_effect=AssertionError("wrote without --create")
    ):
        result = _run(runner, CREATIVE_ARGS)
    assert result.exit_code != 0
    assert "Refusing to create" in result.output


def test_a_web_creative_without_a_link_is_refused_before_any_network(runner):
    with patch.object(
        FacebookAdsApi, "call", side_effect=AssertionError("hit the network")
    ):
        result = _run(runner, CREATIVE_ARGS + ["--kind", "web", "--create"])
    assert result.exit_code != 0
    assert "needs a link" in result.output


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_delete_asks_before_it_deletes(runner):
    with patch.object(
        FacebookAdsApi, "call", side_effect=AssertionError("deleted without asking")
    ):
        result = _run(runner, ["template", "delete", "C9"], input="n\n")
    assert result.exit_code != 0


def test_delete_removes_a_paused_marked_campaign(runner):
    patcher, g = _graph(
        **{
            "GET C9": [
                {"id": "C9", "name": "Templates - X", "effective_status": "PAUSED"}
            ]
        }
    )
    with patcher:
        result = _run(runner, ["template", "delete", "C9", "--yes"])
    assert result.exit_code == 0, result.output
    assert [c["method"] for c in g.calls] == ["GET", "DELETE"]


def test_delete_refuses_an_unmarked_campaign_even_with_yes(runner):
    patcher, g = _graph(**{"GET C9": [{"id": "C9", "name": "vlab-live-study"}]})
    with patcher:
        result = _run(runner, ["template", "delete", "C9", "--yes", "--force"])
    assert result.exit_code == 1
    assert "does not start with" in result.output
    assert [c for c in g.calls if c["method"] == "DELETE"] == []


# ---------------------------------------------------------------------------
# check-targeting
# ---------------------------------------------------------------------------


def test_check_targeting_reads_and_creates_nothing(runner, tmp_path):
    t = tmp_path / "t.json"
    t.write_text(json.dumps({"genders": [1], "age_min": 18}), "utf8")
    patcher, g = _graph(
        **{"GET reachestimate": [{"data": {"users_lower_bound": 900000}}]}
    )
    with patcher:
        result = _run(
            runner,
            [
                "template",
                "check-targeting",
                "--account",
                ACCOUNT,
                "--targeting",
                f"@{t}",
            ],
        )
    assert result.exit_code == 0, result.output
    assert "users_lower_bound" in result.output
    assert [c["method"] for c in g.calls] == ["GET"]


def test_check_targeting_over_a_spec_checks_every_adset(runner, spec):
    patcher, g = _graph(**{"GET reachestimate": [{"data": {"users_lower_bound": 1}}]})
    with patcher:
        result = _run(
            runner,
            ["template", "check-targeting", "--account", ACCOUNT, "--spec", spec],
        )
    assert result.exit_code == 0, result.output
    assert "Kwara - Men" in result.output


def test_check_targeting_exits_one_when_meta_rejects_the_spec(runner, tmp_path):
    """A Meta rejection IS the answer, so it is reported per ad set and the
    command exits 1 -- which is what makes it usable in a `&&` chain.
    """
    t = tmp_path / "t.json"
    t.write_text(
        json.dumps({"geo_locations": {"regions": [{"key": "999999"}]}}), "utf8"
    )

    from facebook_business.exceptions import FacebookRequestError

    error = FacebookRequestError(
        message="Call was not successful",
        request_context={},
        http_status=400,
        http_headers={},
        body='{"error": {"message": "Invalid region key", "code": 100}}',
    )
    patcher, _ = _graph(**{"GET reachestimate": [error]})
    with patcher:
        result = _run(
            runner,
            [
                "template",
                "check-targeting",
                "--account",
                ACCOUNT,
                "--targeting",
                f"@{t}",
            ],
        )
    assert result.exit_code == 1
    assert "FAILED" in result.output


def test_check_targeting_needs_exactly_one_input(runner, spec):
    result = _run(
        runner,
        [
            "template",
            "check-targeting",
            "--account",
            ACCOUNT,
            "--targeting",
            "{}",
            "--spec",
            spec,
        ],
    )
    assert result.exit_code != 0
    assert "exactly one" in result.output


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_the_group_is_registered_on_the_real_cli():
    """`cli.py`'s share of this feature is one import line; this is what it buys."""
    assert "template" in cli.commands
    assert set(cli.commands["template"].commands) == {
        "plan",
        "create",
        "creative",
        "delete",
        "check-targeting",
    }


def test_importing_templates_cli_first_still_registers_the_group():
    """Both import orders work, which is the price of the one-line registration.

    `cli.py` imports this module at the bottom and this module imports `cli`
    from it; the import is `from . import templates_cli`, which binds a module
    object rather than reaching for an attribute of a half-initialised module,
    so neither order breaks.
    """
    import importlib
    import sys

    for name in [
        n for n in sys.modules if n.endswith(("sdk.cli", "sdk.templates_cli"))
    ]:
        del sys.modules[name]

    templates_cli = importlib.import_module("adopt.sdk.templates_cli")
    reloaded = importlib.import_module("adopt.sdk.cli")
    assert "template" in reloaded.cli.commands
    assert templates_cli.template is reloaded.cli.commands["template"]
