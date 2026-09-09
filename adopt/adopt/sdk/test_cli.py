"""Tests for `sdk/cli.py`.

Every command that talks to the server runs against the REAL FastAPI app,
injected as `ctx.obj["client"]`. The only mocks are at the boundaries the app
itself mocks in its own tests: `run_study_opt` / `run_single_instruction` for
optimize (which would otherwise talk to Meta and to a cron's worth of data) and
`FacebookAdsApi.call` for the proxy (the one method that puts bytes on the
wire). Everything between the argv and the database is exercised.

What is being asserted, beyond "it does not crash":

* exit codes, because they are the contract for `&&` and for CI;
* that `push` writes what `diff` said it would, in `PUSH_ORDER`, and skips the
  rest -- an over-eager push appends rows to an append-only table;
* that `push` refuses on validation errors, since a bad write cannot be
  withdrawn;
* that the output says the things a caller will otherwise get wrong: that plan
  writes, that push is append-only, that renaming a stratum deletes an ad set.
"""

import json
import os
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from test.dbfix import _reset_db
from test.dbfix import cnf as db_conf
from unittest.mock import patch

import click
import pytest
import yaml
from click.testing import CliRunner
from fastapi.testclient import TestClient

from ..db import execute, query

os.environ["PG_URL"] = db_conf
os.environ["AUTH0_DOMAIN"] = "_"
os.environ["AUTH0_AUDIENCE"] = "_"
os.environ["API_KEY_DOMAIN"] = "test-domain"
os.environ["API_KEY_AUDIENCE"] = "test-audience"
os.environ["API_KEY_SECRET"] = "api-key-secret"
os.environ["FACEBOOK_APP_ID"] = "test-app-id"
os.environ["FACEBOOK_APP_SECRET"] = "test-app-secret"

from facebook_business.api import FacebookAdsApi  # noqa: E402

from ..server.server import app  # noqa: E402
from .cli import STRATA_COLUMNS, auth_options, cli  # noqa: E402
from .client import VlabClient  # noqa: E402
from .study import StudyFile  # noqa: E402

USER = "test|sdk-cli"
FB_TOKEN = "SECRET-FB-TOKEN-cli"


@pytest.fixture(autouse=True)
def clean_db():
    _reset_db()
    execute(db_conf, "insert into users (id) values (%s)", (USER,))
    yield


@pytest.fixture(autouse=True)
def any_token_is_our_user():
    with patch("adopt.server.auth.verify_token") as m:
        m.return_value = {"sub": USER}
        yield m


@pytest.fixture
def obj():
    """The injected client, wrapping the real app."""
    return {
        "client": VlabClient(
            api_key="token",
            base_url="http://testserver",
            session=TestClient(app, raise_server_exceptions=False),
        )
    }


@pytest.fixture
def org():
    org_id = str(uuid.uuid4())
    execute(db_conf, "insert into orgs (id, name) values (%s, %s)", (org_id, "o"))
    execute(
        db_conf,
        "insert into orgs_lookup (org_id, user_id) values (%s, %s)",
        (org_id, USER),
    )
    return org_id


@pytest.fixture
def runner(tmp_path):
    r = CliRunner()
    with r.isolated_filesystem(temp_dir=tmp_path):
        yield r


def run(runner, obj, *args):
    return runner.invoke(cli, list(args), obj=dict(obj), catch_exceptions=False)


# ---------------------------------------------------------------------------
# Fixtures for a whole study
# ---------------------------------------------------------------------------

MESSENGER = {
    "type": "messenger",
    "name": "main",
    "initial_shortcode": "abc123",
    "welcome_message": "hello",
    "button_text": "Start",
}


def study_dict(org, slug):
    """A complete, valid study. A DEEP COPY every time.

    Several tests below edit what they get back -- a quota, a creative name, a
    deliberate typo -- and `MESSENGER` used to be shared by reference, so
    `test_diff_flags_a_key_no_model_declares` planted `welcom_message` in every
    subsequent test's destinations. That was invisible while the server ran on
    `extra="ignore"` and became eleven failures the moment adopt v0.1.85 made
    an unknown field a 422.
    """
    return deepcopy(_STUDY(org, slug))


def _STUDY(org, slug):
    return {
        "org": org,
        "slug": slug,
        "name": "HPV",
        "general": {
            "name": "HPV",
            "credentials_key": "Facebook",
            "credentials_entity": "facebook",
            "ad_account": "123",
            "opt_window": 48,
        },
        "recruitment": {
            "type": "simple",
            "ad_campaign_name": "hpv",
            "objective": "OUTCOME_ENGAGEMENT",
            "optimization_goal": "LINK_CLICKS",
            "min_budget": 100,
            "budget": 10000,
            "max_sample": 1000,
            "start_date": "2026-01-01T00:00:00",
            "end_date": "2026-03-01T00:00:00",
        },
        "destinations": [MESSENGER],
        "creatives": [
            {"name": "creative-a", "destination": "main", "template": {"actor_id": "1"}}
        ],
        "audiences": [],
        "variables": [],
        "strata": [
            {
                "id": "everyone",
                "quota": 1.0,
                "creatives": ["creative-a"],
                "audiences": [],
                "excluded_audiences": [],
                "facebook_targeting": {"genders": [1]},
                "question_targeting": {
                    "op": "answered",
                    "vars": [{"type": "variable", "value": "finished"}],
                },
                "metadata": {},
            }
        ],
    }


def write_study(path="study.yaml", **overrides):
    data = overrides.pop("data")
    data = {**data, **overrides}
    with open(path, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False)
    return path


# ---------------------------------------------------------------------------
# orgs / studies
# ---------------------------------------------------------------------------


def test_orgs_lists_the_callers_orgs(runner, obj, org):
    res = run(runner, obj, "orgs")

    assert res.exit_code == 0
    assert org in res.output
    assert "1 row(s)." in res.output


def test_orgs_json(runner, obj, org):
    res = run(runner, obj, "orgs", "--json")
    assert json.loads(res.output)["data"] == [{"id": org, "name": "o"}]


def test_studies_lists_slugs(runner, obj, org):
    run(runner, obj, "create", org, "HPV Nigeria")

    res = run(runner, obj, "studies", org)

    assert res.exit_code == 0
    # Slug first: it is the argument every other command takes.
    assert res.output.splitlines()[0].startswith("hpv-nigeria")
    assert "1 row(s)." in res.output


def test_studies_json(runner, obj, org):
    run(runner, obj, "create", org, "HPV Nigeria")

    rows = json.loads(run(runner, obj, "studies", org, "--json").output)["data"]

    assert [r["slug"] for r in rows] == ["hpv-nigeria"]
    assert rows[0]["created"].endswith("+00:00")


def test_studies_takes_the_org_from_the_environment(runner, obj, org, monkeypatch):
    monkeypatch.setenv("VLAB_ORG", org)
    run(runner, obj, "create", org, "HPV Nigeria")

    res = run(runner, obj, "studies")

    assert res.exit_code == 0
    assert "hpv-nigeria" in res.output


def test_studies_without_an_org_says_where_to_get_one(runner, obj, monkeypatch):
    monkeypatch.delenv("VLAB_ORG", raising=False)
    res = runner.invoke(cli, ["studies"], obj=dict(obj))

    assert res.exit_code == 2
    assert "vlab orgs" in res.output


def test_studies_of_a_foreign_org_is_a_clean_error_not_a_traceback(runner, obj, org):
    res = runner.invoke(
        cli, ["studies", str(uuid.uuid4())], obj=dict(obj), catch_exceptions=False
    )

    assert res.exit_code == 1
    assert "Organization not found" in res.output


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


def test_create_prints_the_slug(runner, obj, org):
    res = run(runner, obj, "create", org, "HPV Nigeria")
    assert res.exit_code == 0
    assert "hpv-nigeria" in res.output


def test_create_init_writes_a_valid_skeleton(runner, obj, org):
    res = run(runner, obj, "create", org, "HPV Nigeria", "--init")

    assert res.exit_code == 0
    assert os.path.exists("study.yaml")

    study = StudyFile.load("study.yaml")
    assert study.org == org
    assert study.slug == "hpv-nigeria"

    # And the skeleton it wrote passes the validator it points at.
    assert run(runner, obj, "validate").exit_code == 0


def test_create_refuses_to_overwrite_and_says_the_study_was_still_made(
    runner, obj, org
):
    open("study.yaml", "w").write("org: x\n")
    res = run(runner, obj, "create", org, "HPV", "--init")
    assert res.exit_code == 1
    assert "already exists" in res.output
    assert "slug" in res.output  # the study WAS created; do not lose the slug


def test_create_json(runner, obj, org):
    res = run(runner, obj, "create", org, "HPV", "--json")
    assert json.loads(res.output)["study"]["slug"] == "hpv"


# ---------------------------------------------------------------------------
# pull
# ---------------------------------------------------------------------------


def test_pull_writes_what_the_server_holds(runner, obj, org):
    client = obj["client"]
    slug = client.create_study(org, "HPV")["slug"]
    client.post_conf(org, slug, "destinations", [MESSENGER])

    res = run(runner, obj, "pull", f"{org}/{slug}")

    assert res.exit_code == 0
    study = StudyFile.load("study.yaml")
    assert study.sections["destinations"][0]["name"] == "main"
    assert "never written" in res.output


def test_pull_on_a_fresh_study_writes_a_header_only_file(runner, obj, org):
    slug = obj["client"].create_study(org, "HPV")["slug"]
    res = run(runner, obj, "pull", f"{org}/{slug}")
    assert res.exit_code == 0
    assert StudyFile.load("study.yaml").sections == {}


def test_pull_refuses_to_clobber_local_edits(runner, obj, org):
    slug = obj["client"].create_study(org, "HPV")["slug"]
    open("study.yaml", "w").write("org: mine\n")

    res = run(runner, obj, "pull", f"{org}/{slug}")

    assert res.exit_code == 1
    assert "--force" in res.output
    assert open("study.yaml").read() == "org: mine\n"


def test_a_bad_target_names_both_halves(runner, obj):
    res = run(runner, obj, "pull", "no-slash")
    assert res.exit_code == 2
    assert "<org>/<slug>" in res.output


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


def test_validate_a_good_study_exits_zero(runner, obj, org):
    write_study(data=study_dict(org, "hpv"))
    res = run(runner, obj, "validate")
    assert res.exit_code == 0
    assert "valid" in res.output


def test_validate_always_prints_the_known_gaps(runner, obj, org):
    """What the verdict did NOT cover is exactly what a caller reading 'valid'
    is at risk of over-reading."""
    write_study(data=study_dict(org, "hpv"))
    res = run(runner, obj, "validate")
    assert "known gaps" in res.output.lower()


def test_validate_an_invalid_study_exits_one_and_names_the_code(runner, obj, org):
    data = study_dict(org, "hpv")
    data["strata"][0]["creatives"] = ["nope"]
    write_study(data=data)

    res = run(runner, obj, "validate")

    assert res.exit_code == 1
    assert "stratum.creative_unknown" in res.output
    assert "INVALID" in res.output


def test_warnings_do_not_make_a_study_invalid(runner, obj, org):
    """A study recruiting uniformly is entitled to a thin ref; one not yet
    wired to a survey platform is unfinished rather than broken."""
    data = study_dict(org, "hpv")
    data["strata"][0]["question_targeting"] = {
        "op": "and",
        "vars": [
            {
                "op": "equal",
                "vars": [
                    {"type": "variable", "value": "gender"},
                    {"type": "constant", "value": "men"},
                ],
            }
        ],
    }
    write_study(data=data)

    res = run(runner, obj, "validate")

    assert res.exit_code == 0
    assert "stratum.targeting_variable_unsupplied" in res.output


def test_validate_json(runner, obj, org):
    write_study(data=study_dict(org, "hpv"))
    res = run(runner, obj, "validate", "--json")
    body = json.loads(res.output)
    assert body["data"]["valid"] is True
    assert body["known_gaps"]


def test_validate_remote_asks_the_server_and_agrees_with_local(runner, obj, org):
    """The endpoint is a wrapper over the same pure function, so the two cannot
    disagree -- which is the point of `--remote` being an option rather than
    the default."""
    slug = obj["client"].create_study(org, "HPV")["slug"]
    data = study_dict(org, slug)
    data["strata"][0]["creatives"] = ["nope"]
    write_study(data=data)

    local = run(runner, obj, "validate", "--json")
    remote = run(runner, obj, "validate", "--remote", "--json")

    assert json.loads(local.output)["data"] == json.loads(remote.output)["data"]
    assert remote.exit_code == 1


def test_validate_needs_a_file(runner, obj):
    res = run(runner, obj, "validate")
    assert res.exit_code == 1
    assert "No such file" in res.output


# ---------------------------------------------------------------------------
# diff
# ---------------------------------------------------------------------------


def _push_everything(client, org, slug, data):
    from .study import PUSH_ORDER, SECTION_URL_SEGMENTS

    for name in PUSH_ORDER:
        if name in data:
            client.post_conf(org, slug, SECTION_URL_SEGMENTS[name], data[name])


def test_diff_reports_nothing_to_push_after_a_push(runner, obj, org):
    """The round-trip property, end to end: what was written reads back as
    unchanged. If this ever fails, push appends a row on every run forever."""
    client = obj["client"]
    slug = client.create_study(org, "HPV")["slug"]
    data = study_dict(org, slug)
    write_study(data=data)

    assert run(runner, obj, "push").exit_code == 0
    res = run(runner, obj, "diff")

    assert res.exit_code == 0
    assert "Nothing to push" in res.output


def test_diff_shows_the_changed_leaf_not_just_the_section(runner, obj, org):
    client = obj["client"]
    slug = client.create_study(org, "HPV")["slug"]
    data = study_dict(org, slug)
    _push_everything(client, org, slug, data)

    data["strata"][0]["quota"] = 0.5
    write_study(data=data)

    res = run(runner, obj, "diff")

    assert "~ strata" in res.output
    assert "[0].quota" in res.output
    assert "1.0" in res.output and "0.5" in res.output


def test_a_recruitment_conf_written_before_the_union_was_tagged_reads_as_unchanged(
    runner, obj, org
):
    """The version-skew case, end to end against the real server.

    A file written before adopt v0.1.85 carries no `type`; this server stores
    one, because `model_dump()` now emits it. Without the tolerance in
    `_strip_inferred_tag`, `recruitment` would read as changed forever and
    `push` would append a row to an append-only table on every single run.
    """
    client = obj["client"]
    slug = client.create_study(org, "HPV")["slug"]
    data = study_dict(org, slug)
    del data["recruitment"]["type"]  # a file older than the tag

    _push_everything(client, org, slug, data)

    # The server really did add it -- otherwise this test proves nothing.
    assert client.get_confs(org, slug)["recruitment"]["type"] == "simple"

    write_study(data=data)
    res = run(runner, obj, "diff")

    assert "~ recruitment" not in res.output
    assert "Nothing to push" in res.output


def test_a_recruitment_conf_that_writes_the_tag_also_reads_as_unchanged(
    runner, obj, org
):
    """The other direction: the file the skeleton writes, which carries the
    tag, against the server that also stores it."""
    client = obj["client"]
    slug = client.create_study(org, "HPV")["slug"]
    data = study_dict(org, slug)
    assert data["recruitment"]["type"] == "simple"

    _push_everything(client, org, slug, data)
    write_study(data=data)

    assert "Nothing to push" in run(runner, obj, "diff").output


def test_diff_flags_a_key_no_model_declares(runner, obj, org):
    client = obj["client"]
    slug = client.create_study(org, "HPV")["slug"]
    data = study_dict(org, slug)
    data["destinations"][0]["welcom_message"] = "typo"
    write_study(data=data)

    res = run(runner, obj, "diff")

    assert "welcom_message is not a field" in res.output


def test_diff_reports_a_section_only_on_the_server(runner, obj, org):
    client = obj["client"]
    slug = client.create_study(org, "HPV")["slug"]
    client.post_conf(
        org,
        slug,
        "data-sources",
        [{"name": "fly", "source": "typeform", "credentials_key": "tf"}],
    )
    write_study(data=study_dict(org, slug))

    res = run(runner, obj, "diff")

    assert "? data_sources" in res.output
    assert "no way to remove a section" in res.output


def test_diffs_summary_lists_sections_in_the_order_push_will_write_them(
    runner, obj, org
):
    """Otherwise `diff` and `push` disagree about the same study on the same
    screen -- the summary is read as a preview of the next command."""
    slug = obj["client"].create_study(org, "HPV")["slug"]
    write_study(data=study_dict(org, slug))

    diff_line = [
        line
        for line in run(runner, obj, "diff").output.splitlines()
        if "would be written" in line
    ][0]
    push_lines = [
        line.split()[1]
        for line in run(runner, obj, "push").output.splitlines()
        if line.startswith("wrote ")
    ]

    assert diff_line.split(": ", 1)[1].split(", ") == push_lines


def test_diff_json(runner, obj, org):
    client = obj["client"]
    slug = client.create_study(org, "HPV")["slug"]
    data = study_dict(org, slug)
    _push_everything(client, org, slug, data)
    data["strata"][0]["quota"] = 0.25
    write_study(data=data)

    res = run(runner, obj, "diff", "--json")
    sections = {s["section"]: s for s in json.loads(res.output)["sections"]}

    assert sections["strata"]["status"] == "changed"
    assert sections["strata"]["changes"][0]["path"] == "[0].quota"
    assert sections["general"]["status"] == "unchanged"


# ---------------------------------------------------------------------------
# push
# ---------------------------------------------------------------------------


def _conf_rows(slug):
    return list(
        query(
            db_conf,
            "select conf_type from study_confs sc join studies s on sc.study_id = s.id"
            " where s.slug = %s order by sc.created",
            (slug,),
            as_dict=True,
        )
    )


def test_push_writes_in_the_reference_order(runner, obj, org):
    """destinations before creatives before strata, recruitment last."""
    slug = obj["client"].create_study(org, "HPV")["slug"]
    write_study(data=study_dict(org, slug))

    res = run(runner, obj, "push")

    assert res.exit_code == 0
    written = [r["conf_type"] for r in _conf_rows(slug)]
    assert written == [
        "general",
        "destinations",
        "creatives",
        "audiences",
        "variables",
        "strata",
        "recruitment",
    ]


def test_push_skips_unchanged_sections(runner, obj, org):
    """Re-POSTing an identical section appends a row that changes nothing to a
    table with no delete."""
    client = obj["client"]
    slug = client.create_study(org, "HPV")["slug"]
    data = study_dict(org, slug)
    write_study(data=data)

    run(runner, obj, "push")
    before = len(_conf_rows(slug))

    data["strata"][0]["quota"] = 0.5
    write_study(data=data)
    res = run(runner, obj, "push")

    assert [r["conf_type"] for r in _conf_rows(slug)][before:] == ["strata"]
    assert "wrote strata" in res.output


def test_push_says_the_write_was_append_only(runner, obj, org):
    slug = obj["client"].create_study(org, "HPV")["slug"]
    write_study(data=study_dict(org, slug))
    res = run(runner, obj, "push")
    assert "NEW row" in res.output


def test_push_refuses_on_validation_errors_and_writes_nothing(runner, obj, org):
    slug = obj["client"].create_study(org, "HPV")["slug"]
    data = study_dict(org, slug)
    data["strata"][0]["creatives"] = ["nope"]
    write_study(data=data)

    res = run(runner, obj, "push")

    assert res.exit_code == 1
    assert "stratum.creative_unknown" in res.output
    assert "append-only" in res.output
    assert _conf_rows(slug) == []


def test_force_pushes_anyway(runner, obj, org):
    slug = obj["client"].create_study(org, "HPV")["slug"]
    data = study_dict(org, slug)
    data["strata"][0]["creatives"] = ["nope"]
    write_study(data=data)

    assert run(runner, obj, "push", "--force").exit_code == 0
    assert _conf_rows(slug) != []


def test_push_one_section(runner, obj, org):
    slug = obj["client"].create_study(org, "HPV")["slug"]
    write_study(data=study_dict(org, slug))

    run(runner, obj, "push", "--section", "destinations")

    assert [r["conf_type"] for r in _conf_rows(slug)] == ["destinations"]


def test_push_dry_run_writes_nothing(runner, obj, org):
    slug = obj["client"].create_study(org, "HPV")["slug"]
    write_study(data=study_dict(org, slug))

    res = run(runner, obj, "push", "--dry-run")

    assert "would write general" in res.output
    assert _conf_rows(slug) == []


def test_push_json(runner, obj, org):
    slug = obj["client"].create_study(org, "HPV")["slug"]
    write_study(data=study_dict(org, slug))
    res = run(runner, obj, "push", "--json")
    assert json.loads(res.output)["written"][0] == "general"


def test_pushing_a_second_time_writes_nothing(runner, obj, org):
    slug = obj["client"].create_study(org, "HPV")["slug"]
    write_study(data=study_dict(org, slug))

    run(runner, obj, "push")
    n = len(_conf_rows(slug))
    res = run(runner, obj, "push")

    assert "Nothing to push" in res.output
    assert len(_conf_rows(slug)) == n


# ---------------------------------------------------------------------------
# plan / apply
# ---------------------------------------------------------------------------

INSTRUCTIONS = None


def _instructions():
    from ..facebook.update import Instruction

    return [
        Instruction("campaign", "create", {"name": "hpv"}),
        Instruction("adset", "create", {"name": "everyone"}),
    ]


def test_plan_prints_indices_and_the_side_effect_warning(runner, obj, org):
    slug = obj["client"].create_study(org, "HPV")["slug"]

    with patch("adopt.server.server.run_study_opt") as m:
        m.return_value = _instructions()
        res = run(runner, obj, "plan", f"{org}/{slug}")

    assert res.exit_code == 0
    assert "  0  campaign/create" in res.output
    assert "  1  adset/create" in res.output
    assert "RE-PLAN" in res.output


def test_plan_json(runner, obj, org):
    slug = obj["client"].create_study(org, "HPV")["slug"]
    with patch("adopt.server.server.run_study_opt") as m:
        m.return_value = _instructions()
        res = run(runner, obj, "plan", f"{org}/{slug}", "--json")
    assert json.loads(res.output)[0]["node"] == "campaign"


def test_an_empty_plan_explains_itself(runner, obj, org):
    slug = obj["client"].create_study(org, "HPV")["slug"]
    with patch("adopt.server.server.run_study_opt") as m:
        m.return_value = []
        res = run(runner, obj, "plan", f"{org}/{slug}")
    assert "recruitment window" in res.output


def test_a_plan_failure_carries_the_real_message(runner, obj, org):
    slug = obj["client"].create_study(org, "HPV")["slug"]
    with patch("adopt.server.server.run_study_opt") as m:
        m.side_effect = Exception("Could not find credentials for study id: x")
        res = run(runner, obj, "plan", f"{org}/{slug}")
    assert res.exit_code == 1
    assert "Could not find credentials" in res.output


def test_apply_re_plans_and_posts_the_chosen_instruction(runner, obj, org):
    """The plan is recomputed rather than cached: an instruction list goes
    stale the moment anything is applied."""
    slug = obj["client"].create_study(org, "HPV")["slug"]

    with patch("adopt.server.server.run_study_opt") as plan_m, patch(
        "adopt.server.server.run_single_instruction"
    ) as apply_m:
        plan_m.return_value = _instructions()
        apply_m.return_value = {
            "timestamp": "2026-01-01T00:00:00",
            "instruction": {
                "node": "adset",
                "action": "create",
                "params": {"name": "everyone"},
                "id": None,
            },
        }
        res = run(runner, obj, "apply", f"{org}/{slug}", "1", "--yes")

    assert res.exit_code == 0
    assert plan_m.called
    assert apply_m.call_args[0][3].node == "adset"
    assert "Re-plan" in res.output


def test_apply_without_yes_asks_first(runner, obj, org):
    slug = obj["client"].create_study(org, "HPV")["slug"]

    with patch("adopt.server.server.run_study_opt") as plan_m, patch(
        "adopt.server.server.run_single_instruction"
    ) as apply_m:
        plan_m.return_value = _instructions()
        res = runner.invoke(
            cli, ["apply", f"{org}/{slug}", "0"], obj=dict(obj), input="n\n"
        )

    assert res.exit_code != 0
    assert not apply_m.called


def test_an_index_outside_the_current_plan_says_to_re_plan(runner, obj, org):
    slug = obj["client"].create_study(org, "HPV")["slug"]
    with patch("adopt.server.server.run_study_opt") as m:
        m.return_value = _instructions()
        res = run(runner, obj, "apply", f"{org}/{slug}", "9", "--yes")
    assert res.exit_code == 1
    assert "2 instruction(s)" in res.output


# ---------------------------------------------------------------------------
# errors / current-data / ad-attributions / stats / respondents / costs
# ---------------------------------------------------------------------------


def _study_id(org_id, slug):
    rows = query(
        db_conf,
        "select id from studies where org_id = %s and slug = %s",
        (org_id, slug),
        as_dict=True,
    )
    return str(list(rows)[0]["id"])


def test_errors_prints_the_open_errors(runner, obj, org):
    slug = obj["client"].create_study(org, "HPV")["slug"]
    execute(
        db_conf,
        """
        insert into study_run_events
            (study_id, source, event_type, fingerprint, severity, message)
        values (%s, 'swoosh', 'extraction_failed', 'fp-1', 'error', 'boom')
        """,
        (_study_id(org, slug),),
    )

    res = run(runner, obj, "errors", f"{org}/{slug}")

    assert res.exit_code == 0
    lines = res.output.splitlines()
    # Every study-page table leads with its column names, `errors` included:
    # one rule, one `header=True` on the one renderer.
    assert lines[0] == "severity  source  message  last_seen"
    assert lines[1].startswith("error  swoosh  boom")
    assert "1 row(s)." in res.output


def test_errors_of_a_quiet_study_is_an_empty_table(runner, obj, org):
    """Which is not the same as healthy, and the help text is where that is
    said -- the table has no room for it."""
    slug = obj["client"].create_study(org, "HPV")["slug"]

    res = run(runner, obj, "errors", f"{org}/{slug}")

    assert res.exit_code == 0
    assert "0 row(s)." in res.output


def test_errors_json_is_the_list(runner, obj, org):
    slug = obj["client"].create_study(org, "HPV")["slug"]
    res = run(runner, obj, "errors", f"{org}/{slug}", "--json")
    assert json.loads(res.output)["data"] == []


def test_current_data_prints_one_row_per_variable(runner, obj, org):
    import pandas as pd

    slug = obj["client"].create_study(org, "HPV")["slug"]
    df = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "variable": "age",
                "value": "25",
                "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc),
            },
            {
                "user_id": "u1",
                "variable": "gender",
                "value": "f",
                "timestamp": datetime(2026, 1, 1, tzinfo=timezone.utc),
            },
        ]
    )

    with patch("adopt.server.server.fetch_current_data") as m:
        m.return_value = df
        res = run(runner, obj, "current-data", f"{org}/{slug}")

    assert res.exit_code == 0
    assert res.output.splitlines()[0] == "user_id  variable  value  timestamp"
    # One person, two variables, two rows -- the thing a caller counting
    # respondents off this table will otherwise get wrong.
    assert "2 row(s)." in res.output
    assert "u1  age  25" in res.output


def test_ad_attributions_prints_the_columns_as_a_header(runner, obj, org):
    slug = obj["client"].create_study(org, "HPV")["slug"]
    execute(
        db_conf,
        """
        insert into ad_attributions
            (network, ad_id, study_id, stratum_id, creative_name, shortcode,
             metadata, resolved_from)
        values ('facebook', 'ad-1', %s, 'everyone', 'Smiling', 'mnchweek',
                %s, 'ad_id')
        """,
        (_study_id(org, slug), json.dumps({"gender": "women"})),
    )

    res = run(runner, obj, "ad-attributions", f"{org}/{slug}")

    assert res.exit_code == 0
    lines = res.output.splitlines()
    assert lines[0].startswith("ad_id  network")
    assert "gender" in lines[0]
    # A string cell prints as ITSELF. The hand-rolled loop this replaced ran
    # every value through `short()`, which is `json.dumps` -- so the ad id came
    # out as `"ad-1"`, quotes included, and a researcher copying a column out
    # of this table copied the quotes with it.
    cells = lines[1].split("  ")
    assert cells[0] == "ad-1"
    assert "women" in cells
    assert '"' not in lines[1]
    assert "1 row(s)." in res.output


def test_ad_attributions_csv_writes_the_servers_own_rendering(runner, obj, org):
    """The file is the `.csv` route's body, not this command's rendering of the
    JSON: the two are built from one definition and must not be able to
    disagree."""
    slug = obj["client"].create_study(org, "HPV")["slug"]
    execute(
        db_conf,
        """
        insert into ad_attributions
            (network, ad_id, study_id, stratum_id, creative_name, shortcode,
             metadata, resolved_from)
        values ('facebook', 'ad-1', %s, 'everyone', 'Smiling', 'mnchweek',
                %s, 'ad_id')
        """,
        (_study_id(org, slug), json.dumps({"gender": "women"})),
    )

    res = run(runner, obj, "ad-attributions", f"{org}/{slug}", "--csv", "out.csv")

    assert res.exit_code == 0
    with open("out.csv") as f:
        body = f.read()
    assert body.splitlines()[0].startswith("ad_id,network,")
    assert "ad-1" in body


def test_ad_attributions_csv_to_stdout(runner, obj, org):
    slug = obj["client"].create_study(org, "HPV")["slug"]

    res = run(runner, obj, "ad-attributions", f"{org}/{slug}", "--csv", "-")

    assert res.exit_code == 0
    assert res.output.startswith("ad_id,network,")


def test_ad_attributions_refuses_csv_and_json_together(runner, obj, org):
    slug = obj["client"].create_study(org, "HPV")["slug"]

    res = runner.invoke(
        cli,
        ["ad-attributions", f"{org}/{slug}", "--csv", "-", "--json"],
        obj=dict(obj),
    )

    assert res.exit_code == 2
    assert "two different formats" in res.output


def test_stats_before_any_plan_run_is_a_clean_404_not_a_traceback(runner, obj, org):
    """The 404 that means "no plan has ever run", which is the commonest thing
    a researcher hits on this command."""
    slug = obj["client"].create_study(org, "HPV")["slug"]

    res = run(runner, obj, "stats", f"{org}/{slug}")

    assert res.exit_code == 1
    assert "404" in res.output


def test_respondents_and_costs_print_the_seeded_reports(runner, obj, org):
    from ..campaign_queries import (
        create_cost_over_time_report,
        create_respondents_over_time_report,
    )

    slug = obj["client"].create_study(org, "HPV")["slug"]
    study_id = _study_id(org, slug)
    create_respondents_over_time_report(
        study_id,
        {
            "data": [
                {
                    "datetime": 1767225600000,
                    "totalParticipants": 3,
                    "segments": [{"id": "everyone", "participants": 3}],
                }
            ]
        },
        db_conf,
    )
    create_cost_over_time_report(
        study_id,
        [
            {
                "datetime": 1767225600000,
                "cumulativeSpend": 100.0,
                "cumulativeRespondents": 3,
                "marginalCost": 33.3,
                "newRespondents": 3,
                "dailySpend": 100.0,
            }
        ],
        db_conf,
    )

    res = run(runner, obj, "respondents", f"{org}/{slug}")
    assert res.exit_code == 0
    assert res.output.splitlines()[0] == "datetime  totalParticipants"
    assert "1767225600000" in res.output

    res = run(runner, obj, "costs", f"{org}/{slug}")
    assert res.exit_code == 0
    assert "33.3" in res.output
    assert "1 row(s)." in res.output


def test_respondents_before_any_plan_run_is_an_empty_table(runner, obj, org):
    slug = obj["client"].create_study(org, "HPV")["slug"]

    res = run(runner, obj, "respondents", f"{org}/{slug}")

    assert res.exit_code == 0
    assert "0 row(s)." in res.output


def test_costs_json_carries_the_reports_own_field_names(runner, obj, org):
    """camelCase and all: these are the dashboard's chart fields, and renaming
    them here would produce a payload nothing else on this service uses."""
    from ..campaign_queries import create_cost_over_time_report

    slug = obj["client"].create_study(org, "HPV")["slug"]
    create_cost_over_time_report(
        _study_id(org, slug),
        [
            {
                "datetime": 1767225600000,
                "cumulativeSpend": 100.0,
                "cumulativeRespondents": 3,
                "marginalCost": None,
                "newRespondents": 0,
                "dailySpend": 100.0,
            }
        ],
        db_conf,
    )

    rows = json.loads(run(runner, obj, "costs", f"{org}/{slug}", "--json").output)

    assert rows["data"][0]["cumulativeSpend"] == 100.0
    # Null on a day that gained no respondents, not zero: zero would say the
    # day's respondents were free.
    assert rows["data"][0]["marginalCost"] is None


# ---------------------------------------------------------------------------
# copy-from
# ---------------------------------------------------------------------------


def test_copy_from_copies_every_section_but_general(runner, obj, org):
    client = obj["client"]
    source = client.create_study(org, "Source")["slug"]
    target = client.create_study(org, "Target")["slug"]
    client.post_conf(org, source, "general", _STUDY(org, source)["general"])
    client.post_conf(org, source, "destinations", [MESSENGER])

    res = run(runner, obj, "copy-from", f"{org}/{target}", source)

    assert res.exit_code == 0
    assert "destinations" in res.output
    assert "general" not in res.output
    assert "1 section(s) copied" in res.output
    assert client.get_confs(org, target)["destinations"][0]["name"] == "main"


def test_copy_from_a_source_with_nothing_is_a_clean_error(runner, obj, org):
    client = obj["client"]
    source = client.create_study(org, "Source")["slug"]
    target = client.create_study(org, "Target")["slug"]

    res = run(runner, obj, "copy-from", f"{org}/{target}", source)

    assert res.exit_code == 1
    assert "404" in res.output


# ---------------------------------------------------------------------------
# strata-progress
# ---------------------------------------------------------------------------


def _adopt_report(study_id, details, created=None):
    """A `FACEBOOK_ADOPT` row, as a plan run would have written it.

    Written directly: `vlab strata-progress` is a read, and planning it for
    real would put Meta and the budget optimizer between the fixture and the
    output being asserted.
    """
    if created is None:
        execute(
            db_conf,
            "insert into adopt_reports (study_id, report_type, details)"
            " values (%s, 'FACEBOOK_ADOPT', %s)",
            (study_id, json.dumps(details)),
        )
    else:
        execute(
            db_conf,
            "insert into adopt_reports (study_id, report_type, details, created)"
            " values (%s, 'FACEBOOK_ADOPT', %s, %s)",
            (study_id, json.dumps(details), created),
        )


_STRATUM = {
    "current_participants": 32,
    "expected_participants": 48.75,
    "desired_percentage": 0.5,
    "current_percentage": 0.4,
    "expected_percentage": 0.55,
    "current_budget": 12.5,
    "current_price_per_participant": 1.25,
}


def test_strata_progress_prints_a_row_per_stratum(runner, obj, org):
    study = obj["client"].create_study(org, "HPV")
    _adopt_report(study["id"], {"urban": _STRATUM, "rural": _STRATUM})

    res = run(runner, obj, "strata-progress", f"{org}/{study['slug']}")

    assert res.exit_code == 0
    lines = res.output.splitlines()
    # created, header, two strata.
    assert lines[0].endswith("+00:00")
    # The report's own field names as the header, through the one renderer the
    # study-page tables use. No invented `%desired`: the three share fields are
    # fractions, and a percent sign over `0.5` would be a lie.
    assert lines[1].split() == list(STRATA_COLUMNS)
    assert lines[2].split()[0] == "rural"
    assert "12.5" in lines[2]
    # The share printed as the fraction it is: 0.5, never 50.
    assert lines[2].split()[3] == "0.5"
    assert "1 report(s)." in res.output


def test_strata_progress_history_prints_one_table_per_run(runner, obj, org):
    from datetime import datetime, timedelta, timezone

    study = obj["client"].create_study(org, "HPV")
    now = datetime.now(timezone.utc)
    _adopt_report(
        study["id"], {"s": {**_STRATUM, "current_budget": 1.0}}, now - timedelta(1)
    )
    _adopt_report(study["id"], {"s": {**_STRATUM, "current_budget": 2.0}}, now)

    res = run(
        runner, obj, "strata-progress", f"{org}/{study['slug']}", "--history", "2"
    )

    assert res.exit_code == 0
    assert "2 report(s)." in res.output
    # Newest first, so the budget the optimizer set most recently is the first
    # table -- which is what someone reading a terminal sees without scrolling.
    budgets = [
        line.split()[-2] for line in res.output.splitlines() if line.startswith("s ")
    ]
    assert budgets == ["2.0", "1.0"]


def test_strata_progress_json_is_unrounded(runner, obj, org):
    """Nothing is rounded on either path -- the CLI prints what the route
    returned -- and `--json` is the shape an agent parses."""
    study = obj["client"].create_study(org, "HPV")
    _adopt_report(
        study["id"],
        {"s": {**_STRATUM, "desired_percentage": 0.3334, "current_percentage": 0.3331}},
    )

    res = run(runner, obj, "strata-progress", f"{org}/{study['slug']}", "--json")

    (report,) = json.loads(res.output)
    assert report["strata"][0]["desired_percentage"] == 0.3334
    assert report["strata"][0]["percentage_deviation_from_goal"] < 0.001


def test_strata_progress_before_any_plan_run_is_a_clean_error(runner, obj, org):
    study = obj["client"].create_study(org, "HPV")

    res = runner.invoke(
        cli,
        ["strata-progress", f"{org}/{study['slug']}"],
        obj=dict(obj),
        catch_exceptions=False,
    )

    assert res.exit_code == 1
    assert "No adopt report found" in res.output


# ---------------------------------------------------------------------------
# meta
# ---------------------------------------------------------------------------


def _credential(entity="facebook", key="Facebook", token=FB_TOKEN):
    import orjson

    execute(
        db_conf,
        "insert into credentials (user_id, entity, key, details) values (%s,%s,%s,%s)",
        (USER, entity, key, orjson.dumps({"access_token": token}).decode()),
    )


def test_meta_credentials_lists_names_and_never_tokens(runner, obj, org):
    _credential()
    res = run(runner, obj, "meta", "credentials", "--org", org)
    assert res.exit_code == 0
    assert "Facebook" in res.output
    assert FB_TOKEN not in res.output


def test_meta_adaccounts_goes_through_the_proxy(runner, obj, org):
    _credential()
    with patch.object(FacebookAdsApi, "call") as call:
        call.return_value.json.return_value = {
            "data": [{"id": "act_1", "account_id": "1", "name": "Main"}]
        }
        res = run(runner, obj, "meta", "adaccounts", "--org", org)

    assert res.exit_code == 0
    # The BARE number is what general.ad_account wants, so it is printed first.
    assert res.output.splitlines()[0].startswith("1  act_1  Main")


def test_meta_adsets_json_is_what_extract_targeting_takes(runner, obj, org):
    _credential()
    adset = {"id": "1", "name": "geo-lagos", "targeting": {"genders": [1]}}
    with patch.object(FacebookAdsApi, "call") as call:
        call.return_value.json.return_value = {"data": [adset]}
        res = run(
            runner, obj, "meta", "adsets", "--org", org, "--campaign", "9", "--json"
        )

    body = json.loads(res.output)
    assert body["data"] == [adset]
    assert body["paging"]["truncated"] is False


def test_meta_ads_requires_exactly_one_parent(runner, obj, org):
    _credential()
    res = run(runner, obj, "meta", "ads", "--org", org)
    assert res.exit_code == 2
    assert "exactly one" in res.output


def test_an_ambiguous_credential_is_a_409_naming_them(runner, obj, org):
    """The proxy will not pick: a wrong pick surfaces hours later as an
    unexplained Meta rejection at ad-set create time."""
    _credential(key="Facebook")
    _credential(entity="facebook_ad_user", key="virtual-lab-vlab")

    res = run(runner, obj, "meta", "adaccounts", "--org", org)

    assert res.exit_code == 1
    assert "virtual-lab-vlab" in res.output


def test_a_meta_rejection_keeps_its_code(runner, obj, org):
    """Never a bare 500, and never a bare status either: the SDK renders the
    human sentence and the codes a caller looks up."""
    import orjson
    from facebook_business.exceptions import FacebookRequestError

    _credential()
    error = FacebookRequestError(
        message="Call was not successful",
        request_context={"method": "GET", "path": "https://graph.facebook.com/x"},
        http_status=400,
        http_headers={},
        body=orjson.dumps(
            {
                "error": {
                    "message": "Session has expired.",
                    "code": 190,
                    "type": "OAuth",
                }
            }
        ).decode("utf8"),
    )

    with patch.object(FacebookAdsApi, "call", side_effect=error):
        res = run(runner, obj, "meta", "adaccounts", "--org", org)

    assert res.exit_code == 1
    assert "Session has expired" in res.output
    assert "code=190" in res.output


# ---------------------------------------------------------------------------
# strata
# ---------------------------------------------------------------------------

VARIABLES = [
    {
        "name": "gender",
        "properties": ["genders"],
        "levels": [
            {
                "name": "men",
                "template_campaign": "t",
                "template_adset": "t",
                "facebook_targeting": {"genders": [1]},
                "quota": 0.5,
            },
            {
                "name": "women",
                "template_campaign": "t",
                "template_adset": "t",
                "facebook_targeting": {"genders": [2]},
                "quota": 0.5,
            },
        ],
    }
]


def test_strata_generate_compiles_the_factorial(runner, obj, org):
    data = study_dict(org, "hpv")
    data["variables"] = VARIABLES
    data["strata"] = []
    write_study(data=data)

    res = run(runner, obj, "strata", "generate", "--finish-question", "finished")

    assert res.exit_code == 0
    strata = StudyFile.load("study.yaml").sections["strata"]
    assert [s["id"] for s in strata] == ["gender:men", "gender:women"]
    assert strata[0]["quota"] == 0.5
    assert strata[0]["creatives"] == ["creative-a"]


def test_strata_generate_merges_like_the_dashboards_regenerate(runner, obj, org):
    """Hand-edited creatives/audiences/exclusions survive; targeting, metadata
    and quota are recomputed. `quota` in particular: it is the product of the
    level quotas, so preserving it would mean a changed split could never
    propagate to an existing study."""
    data = study_dict(org, "hpv")
    data["variables"] = VARIABLES
    data["strata"] = [
        {
            "id": "gender:men",
            "quota": 0.9,  # stale: derived, must be recomputed
            "creatives": ["hand-picked"],  # a user edit: must survive
            "audiences": ["mine"],
            "excluded_audiences": ["theirs"],
            "facebook_targeting": {"genders": [99]},  # stale: derived
            "question_targeting": {
                "op": "and",
                "vars": [
                    {"op": "answered", "vars": [{"type": "variable", "value": "q9"}]}
                ],
            },
            "metadata": {"old": "yes"},
        }
    ]
    write_study(data=data)

    res = run(runner, obj, "strata", "generate")

    assert res.exit_code == 0
    strata = {s["id"]: s for s in StudyFile.load("study.yaml").sections["strata"]}
    men = strata["gender:men"]

    assert men["creatives"] == ["hand-picked"]
    assert men["audiences"] == ["mine"]
    assert men["excluded_audiences"] == ["theirs"]
    assert men["quota"] == 0.5
    assert men["facebook_targeting"] == {"genders": [1]}
    assert men["metadata"] == {"gender": "men"}
    # The finish ref was read off the existing stratum's `answered` term.
    assert men["question_targeting"]["vars"][-1]["vars"][0]["value"] == "q9"


def test_strata_generate_warns_that_a_dropped_stratum_deletes_an_ad_set(
    runner, obj, org
):
    data = study_dict(org, "hpv")
    data["variables"] = VARIABLES
    data["strata"] = [
        {
            "id": "gender:nonbinary",
            "quota": 1.0,
            "creatives": [],
            "audiences": [],
            "excluded_audiences": [],
            "facebook_targeting": {},
            "question_targeting": {
                "op": "and",
                "vars": [
                    {"op": "answered", "vars": [{"type": "variable", "value": "q"}]}
                ],
            },
            "metadata": {},
        }
    ]
    write_study(data=data)

    res = run(runner, obj, "strata", "generate")

    assert "gender:nonbinary" in res.output
    assert "deletes those ad sets" in res.output


def test_strata_generate_needs_a_finish_question_from_somewhere(runner, obj, org):
    data = study_dict(org, "hpv")
    data["variables"] = VARIABLES
    data["strata"] = []
    write_study(data=data)

    res = run(runner, obj, "strata", "generate")

    assert res.exit_code == 1
    assert "--finish-question" in res.output


def test_strata_generate_without_variables_says_hand_writing_is_fine(runner, obj, org):
    write_study(data=study_dict(org, "hpv"))
    res = run(runner, obj, "strata", "generate")
    assert res.exit_code == 1
    assert "by hand" in res.output


def test_strata_generate_pushes_nothing(runner, obj, org):
    slug = obj["client"].create_study(org, "HPV")["slug"]
    data = study_dict(org, slug)
    data["variables"] = VARIABLES
    data["strata"] = []
    write_study(data=data)

    run(runner, obj, "strata", "generate", "--finish-question", "finished")

    assert _conf_rows(slug) == []


def test_extract_targeting_from_a_meta_adsets_response(runner, obj):
    """The response goes in unchanged -- that is what the shape is for."""
    body = {
        "data": [
            {
                "id": "1",
                "name": "geo-lagos",
                "targeting": {
                    "geo_locations": {"countries": ["NG"]},
                    "age_min": 18,
                    "genders": [1],
                },
            }
        ],
        "paging": {"after": None, "truncated": False, "pages_fetched": 1},
    }
    open("adsets.json", "w").write(json.dumps(body))

    res = run(
        runner,
        obj,
        "strata",
        "extract-targeting",
        "adsets.json",
        "geo_locations",
        "age_min",
    )

    out = json.loads(res.output)
    assert out["geo_locations"] == {"countries": ["NG"]}
    assert out["age_min"] == 18
    # Forced, always: Advantage+ audience expansion leaks delivery outside a
    # geographic stratum.
    assert out["targeting_automation"] == {"advantage_audience": 0}
    assert "genders" not in out


def test_extract_targeting_picks_by_name(runner, obj):
    body = {
        "data": [
            {"id": "1", "name": "a", "targeting": {"age_min": 18}},
            {"id": "2", "name": "b", "targeting": {"age_min": 25}},
        ]
    }
    open("adsets.json", "w").write(json.dumps(body))

    res = run(
        runner,
        obj,
        "strata",
        "extract-targeting",
        "adsets.json",
        "age_min",
        "--name",
        "b",
    )

    assert json.loads(res.output)["age_min"] == 25


def test_extract_targeting_will_not_guess_between_ad_sets(runner, obj):
    body = {"data": [{"id": "1", "name": "a"}, {"id": "2", "name": "b"}]}
    open("adsets.json", "w").write(json.dumps(body))

    res = run(runner, obj, "strata", "extract-targeting", "adsets.json", "age_min")

    assert res.exit_code == 1
    assert "--name" in res.output


def test_a_missing_property_is_an_error_not_a_default(runner, obj):
    """Silently omitting `geo_locations` would produce a stratum targeting a
    whole country."""
    open("adset.json", "w").write(
        json.dumps({"id": "1", "name": "a", "targeting": {"age_min": 18}})
    )

    res = run(runner, obj, "strata", "extract-targeting", "adset.json", "geo_locations")

    assert res.exit_code == 1
    assert "geo_locations" in res.output


# ---------------------------------------------------------------------------
# keys
# ---------------------------------------------------------------------------


def test_keys_list_is_empty_for_a_fresh_user(runner, obj):
    res = run(runner, obj, "keys", "list")
    assert res.exit_code == 0
    assert "0 key(s)" in res.output


def test_keys_list_shows_scopes_and_expiry(runner, obj):
    from ..server.api_keys import clear_api_key_cache

    clear_api_key_cache()
    obj["client"].request(
        "POST",
        "/users/api-key",
        json={"name": "agent", "scopes": ["studies:write"], "expires_in_days": 30},
    )

    res = run(runner, obj, "keys", "list")

    assert "agent" in res.output
    assert "studies:write" in res.output
    assert "1 key(s)" in res.output


def test_keys_revoke(runner, obj):
    from ..server.api_keys import clear_api_key_cache

    clear_api_key_cache()
    minted = obj["client"]._data("POST", "/users/api-key", json={"name": "agent"})

    res = run(runner, obj, "keys", "revoke", minted["id"], "--yes")

    assert res.exit_code == 0
    assert "30 seconds" in res.output
    clear_api_key_cache()
    assert obj["client"].list_api_keys()["keys"] == []


def test_keys_create_prints_the_token_once_with_a_warning(runner, obj):
    """The token exists in exactly one place ever: this output. If it is not
    obvious that it will not be shown again, it will be lost."""
    from ..server.api_keys import clear_api_key_cache

    clear_api_key_cache()

    res = run(
        runner,
        obj,
        "keys",
        "create",
        "agent",
        "--scope",
        "studies:write",
        "--scope",
        "meta:read",
        "--expires-in-days",
        "30",
    )

    assert res.exit_code == 0, res.output
    assert "shown once" in res.output
    assert "studies:write, meta:read" in res.output

    clear_api_key_cache()
    listed = obj["client"].list_api_keys()["keys"]
    assert [k["name"] for k in listed] == ["agent"]
    assert listed[0]["scopes"] == ["studies:write", "meta:read"]


def test_keys_create_json_is_parseable_and_carries_no_prose(runner, obj):
    """`--json` output is redirected to a file; a warning sentence on stdout
    would end up inside it."""
    from ..server.api_keys import clear_api_key_cache

    clear_api_key_cache()

    res = run(runner, obj, "keys", "create", "agent", "--json")

    body = json.loads(res.output)
    assert body["name"] == "agent"
    assert body["token"]


def test_keys_create_with_no_scope_asks_for_an_unrestricted_key(runner, obj):
    """Not for none. The injected client authenticates as an unrestricted
    session, so this succeeds here; from a scoped key it is a 403, which is the
    behaviour the tool and CLI help both spell out."""
    from ..server.api_keys import clear_api_key_cache

    clear_api_key_cache()

    res = run(runner, obj, "keys", "create", "wide", "--json")

    assert json.loads(res.output)["scopes"] is None


# ---------------------------------------------------------------------------
# accounts
# ---------------------------------------------------------------------------


def _creds_file(runner, payload):
    """A credentials file in the runner's isolated filesystem."""
    with open("creds.json", "w", encoding="utf8") as f:
        json.dump(payload, f)
    return "creds.json"


def test_accounts_add_reads_the_secret_from_a_file_and_lists_it(runner, obj):
    """The secret never appears on a command line -- there is no flag that
    takes one -- so a token stays out of the shell history and out of `ps`."""
    path = _creds_file(runner, {"key": "SECRET-FROM-A-FILE-7c3e"})

    res = run(
        runner,
        obj,
        "accounts",
        "add",
        "tf-main",
        "--type",
        "typeform",
        "--credentials-json",
        path,
    )

    assert res.exit_code == 0, res.output
    assert "SECRET-FROM-A-FILE-7c3e" not in res.output
    assert "credentials_key: tf-main" in res.output

    listed = run(runner, obj, "accounts", "list")
    assert "tf-main" in listed.output
    assert "typeform" in listed.output
    assert "SECRET-FROM-A-FILE-7c3e" not in listed.output


def test_accounts_add_reads_stdin_when_the_path_is_a_dash(runner, obj):
    """So a secret can come out of a password manager through a pipe without
    ever touching the disk."""
    res = runner.invoke(
        cli,
        ["accounts", "add", "fly-main", "--type", "fly", "--credentials-json", "-"],
        obj=dict(obj),
        input=json.dumps({"api_key": "PIPED-SECRET"}),
        catch_exceptions=False,
    )

    assert res.exit_code == 0, res.output
    assert "PIPED-SECRET" not in res.output
    assert obj["client"].list_accounts()[0]["name"] == "fly-main"


def test_accounts_add_says_which_file_is_missing(runner, obj):
    res = run(
        runner,
        obj,
        "accounts",
        "add",
        "x",
        "--type",
        "fly",
        "--credentials-json",
        "nope.json",
    )

    assert res.exit_code == 1
    assert "nope.json" in res.output


def test_accounts_add_rejects_a_file_that_is_not_json(runner, obj):
    with open("creds.json", "w", encoding="utf8") as f:
        f.write("not json")

    res = run(
        runner,
        obj,
        "accounts",
        "add",
        "x",
        "--type",
        "fly",
        "--credentials-json",
        "creds.json",
    )

    assert res.exit_code == 1
    assert "not valid JSON" in res.output


def test_accounts_add_rejects_a_json_document_that_is_not_an_object(runner, obj):
    path = _creds_file(runner, ["key"])

    res = run(
        runner, obj, "accounts", "add", "x", "--type", "fly", "--credentials-json", path
    )

    assert res.exit_code == 1
    assert "object" in res.output


def test_accounts_add_surfaces_the_servers_422_rather_than_a_traceback(runner, obj):
    path = _creds_file(runner, {"keys": "typo"})

    res = run(
        runner,
        obj,
        "accounts",
        "add",
        "x",
        "--type",
        "typeform",
        "--credentials-json",
        path,
    )

    assert res.exit_code == 1
    assert "422" in res.output


def test_accounts_list_filters_by_type(runner, obj):
    obj["client"].create_account("tf", "typeform", {"key": "a"})
    obj["client"].create_account("f", "fly", {"api_key": "b"})

    res = run(runner, obj, "accounts", "list", "--type", "fly")

    assert "1 row(s)" in res.output
    assert "tf" not in res.output


def test_accounts_delete_needs_confirmation_and_then_deletes(runner, obj):
    obj["client"].create_account("tf", "typeform", {"key": "a"})

    res = run(runner, obj, "accounts", "delete", "typeform", "tf", "--yes")

    assert res.exit_code == 0, res.output
    assert obj["client"].list_accounts() == []


def test_accounts_delete_warns_before_asking(runner, obj):
    """The prompt has to say what breaks: nothing checks whether a study names
    this credential, and the failure surfaces at the next reconcile."""
    obj["client"].create_account("tf", "typeform", {"key": "a"})

    res = runner.invoke(
        cli,
        ["accounts", "delete", "typeform", "tf"],
        obj=dict(obj),
        input="n\n",
        catch_exceptions=False,
    )

    assert res.exit_code == 1
    assert "credentials_key" in res.output
    assert len(obj["client"].list_accounts()) == 1


def test_accounts_delete_refuses_json_without_yes(runner, obj):
    """A confirmation prompt goes to stdout, which is what `--json` output is."""
    res = run(runner, obj, "accounts", "delete", "typeform", "tf", "--json")

    assert res.exit_code == 2
    assert "--yes" in res.output


def test_accounts_delete_of_something_absent_is_a_clean_error(runner, obj):
    res = run(runner, obj, "accounts", "delete", "typeform", "nope", "--yes")

    assert res.exit_code == 1
    assert "404" in res.output


def test_the_accounts_help_says_facebook_needs_a_browser(runner, obj):
    res = run(runner, obj, "accounts", "--help")

    assert "OAuth" in res.output
    assert "browser" in res.output


# ---------------------------------------------------------------------------
# The group itself
# ---------------------------------------------------------------------------


def test_no_api_key_says_a_human_has_to_mint_one(runner):
    res = runner.invoke(
        cli, ["keys", "list"], obj={"api_url": "http://x", "api_key": None}
    )
    assert res.exit_code == 1
    assert "VLAB_API_KEY" in res.output
    assert "Auth0" in res.output


def test_the_api_url_defaults_to_production():
    from .client import DEFAULT_API_URL

    assert DEFAULT_API_URL == "https://vlab-study-conf-api.toixo.vlab.digital"


def test_a_push_that_fails_part_way_reports_what_was_already_written(
    runner, obj, org, monkeypatch
):
    """Nine POSTs, no transaction, and `study_confs` has no delete -- so which
    sections landed is the most important thing to say, and in --json mode
    nothing has been printed yet when the failure arrives."""
    from .client import ServerError

    slug = obj["client"].create_study(org, "HPV")["slug"]
    write_study(data=study_dict(org, slug))

    real = obj["client"].post_conf
    calls = []

    def fail_on_creatives(o, s, segment, body):
        if segment == "creatives":
            raise ServerError(500, "boom", "POST", "http://x")
        calls.append(segment)
        return real(o, s, segment, body)

    monkeypatch.setattr(obj["client"], "post_conf", fail_on_creatives)

    res = run(runner, obj, "push")

    assert res.exit_code == 1
    assert "FAILED on creatives" in res.output
    assert "append-only" in res.output
    # general and destinations really did land, and really cannot be withdrawn.
    assert [r["conf_type"] for r in _conf_rows(slug)] == ["general", "destinations"]


def test_a_failed_json_push_still_says_what_landed(runner, obj, org, monkeypatch):
    from .client import ServerError

    slug = obj["client"].create_study(org, "HPV")["slug"]
    write_study(data=study_dict(org, slug))

    real = obj["client"].post_conf

    def fail_on_creatives(o, s, segment, body):
        if segment == "creatives":
            raise ServerError(500, "boom", "POST", "http://x")
        return real(o, s, segment, body)

    monkeypatch.setattr(obj["client"], "post_conf", fail_on_creatives)

    res = run(runner, obj, "push", "--json")

    assert res.exit_code == 1
    body = json.loads(res.output.split("Error:")[0])
    assert body["written"] == ["general", "destinations"]
    assert body["failed"] == "creatives"


# ---------------------------------------------------------------------------
# The findings of the pre-merge review
# ---------------------------------------------------------------------------


def test_create_init_survives_a_name_that_needs_yaml_quoting(runner, obj, org):
    """`create --init` writes the file AFTER the study exists server-side, so a
    file broken by its own name cannot be fixed by re-running -- that is a
    409. `"HPV: Lagos"` used to make the file unparseable."""
    res = run(runner, obj, "create", org, "HPV: Lagos 2026", "--init")

    assert res.exit_code == 0
    assert StudyFile.load("study.yaml").name == "HPV: Lagos 2026"
    assert run(runner, obj, "validate").exit_code == 0


def test_a_malformed_study_file_is_a_message_not_a_traceback(runner, obj):
    open("study.yaml", "w").write("general: {unclosed\n")

    res = run(runner, obj, "validate")

    assert res.exit_code == 1
    assert "Could not parse" in res.output
    assert "Traceback" not in res.output


def test_a_typod_section_name_is_reported_rather_than_silently_nothing(
    runner, obj, org
):
    """The worst outcome available: no route exists for `stratas`, so it is not
    written, not rejected and not missed -- the study just has no strata."""
    data = study_dict(org, "hpv")
    data["stratas"] = data.pop("strata")
    write_study(data=data)

    res = run(runner, obj, "validate")

    assert res.exit_code == 1  # `strata` is now missing, which is an error
    assert "section.unrecognized" in res.output
    assert "stratas" in res.output


def test_diff_names_a_key_that_is_not_a_section_at_all(runner, obj, org):
    client = obj["client"]
    slug = client.create_study(org, "HPV")["slug"]
    data = study_dict(org, slug)
    _push_everything(client, org, slug, data)
    data["stratas"] = []
    write_study(data=data)

    res = run(runner, obj, "diff")

    assert "never written: stratas" in res.output


def test_push_section_does_not_claim_the_study_is_in_sync(runner, obj, org):
    """It said "every section matches the server" while other sections
    differed, which tells CI the study is in sync when it is not."""
    client = obj["client"]
    slug = client.create_study(org, "HPV")["slug"]
    data = study_dict(org, slug)
    _push_everything(client, org, slug, data)

    data["strata"][0]["quota"] = 0.5
    write_study(data=data)

    res = run(runner, obj, "push", "--section", "audiences")

    assert res.exit_code == 0
    assert "every section matches" not in res.output
    assert "Still outstanding elsewhere: strata" in res.output


def test_push_json_reports_outstanding_when_the_filter_leaves_nothing(runner, obj, org):
    client = obj["client"]
    slug = client.create_study(org, "HPV")["slug"]
    data = study_dict(org, slug)
    _push_everything(client, org, slug, data)
    data["strata"][0]["quota"] = 0.5
    write_study(data=data)

    body = json.loads(
        run(runner, obj, "push", "--section", "audiences", "--json").output
    )

    assert body["written"] == []
    assert body["outstanding"] == ["strata"]
    # `skipped` means "unchanged", on this path as on the success path.
    assert "strata" not in body["skipped"]
    assert "audiences" in body["skipped"]


def test_meta_ads_refuses_paging_options_that_cannot_apply(runner, obj, org):
    _credential()
    res = run(runner, obj, "meta", "ads", "--org", org, "--ad", "123", "--limit", "10")
    assert res.exit_code == 2
    assert "one creative" in res.output


def test_a_target_with_too_many_segments_is_a_usage_error(runner, obj):
    """Not a 404 from a percent-encoded slug."""
    res = run(runner, obj, "pull", "org/slug/extra")
    assert res.exit_code == 2
    assert "<org>/<slug>" in res.output


# ---------------------------------------------------------------------------
# Interface claims the module docstring makes
# ---------------------------------------------------------------------------


def test_auth_options_work_after_the_subcommand(runner, obj, org):
    """`vlab push --api-key X` was a usage error while `vlab --api-key X push`
    worked, which is the wrong way round from how anyone types it.

    The injected client makes the key inert here; what is being asserted is
    that the option PARSES, which is the whole of the bug.
    """
    slug = obj["client"].create_study(org, "HPV")["slug"]
    write_study(data=study_dict(org, slug))

    res = run(runner, obj, "push", "--api-key", "X", "--dry-run")

    assert res.exit_code == 0
    assert "would write general" in res.output


def test_a_subcommand_key_beats_the_group_key():
    """The more specific of the two wins. Asserted on the context object rather
    than through a request, so nothing reaches the network."""
    seen = {}

    @click.command()
    @auth_options
    @click.pass_context
    def probe(ctx):
        seen.update(ctx.obj)

    group_obj = {"api_key": "group", "api_url": "group-url"}
    CliRunner().invoke(
        probe, ["--api-key", "sub"], obj=group_obj, catch_exceptions=False
    )

    assert seen["api_key"] == "sub"
    assert seen["api_url"] == "group-url"  # untouched when not given


@pytest.mark.parametrize(
    "args",
    [
        ["pull", "ORG/hpv", "--json"],
        ["strata", "generate", "--json", "--finish-question", "q"],
        ["keys", "revoke", "abc", "--yes", "--json"],
    ],
)
def test_the_three_commands_that_lacked_json_have_it(runner, obj, org, args):
    """The module docstring said every command takes `--json`; three did not."""
    args = [org if a == "ORG/hpv" else a for a in args]
    if args[0] == "pull":
        slug = obj["client"].create_study(org, "HPV")["slug"]
        args[1] = f"{org}/{slug}"
    if args[0] == "strata":
        data = study_dict(org, "hpv")
        data["variables"] = VARIABLES
        data["strata"] = []
        write_study(data=data)

    res = run(runner, obj, *args)

    assert res.exit_code in (0, 1)
    if res.exit_code == 0:
        json.loads(res.output)


def test_apply_json_without_yes_is_a_usage_error(runner, obj, org):
    """The confirmation prints the instruction and a prompt on stdout, which
    would leave `--json` output that is not JSON — and nothing is there to
    answer it. This is the one command that spends money on Meta."""
    slug = obj["client"].create_study(org, "HPV")["slug"]

    with patch("adopt.server.server.run_study_opt") as m:
        m.return_value = _instructions()
        res = run(runner, obj, "apply", f"{org}/{slug}", "0", "--json")

    assert res.exit_code == 2
    assert "--json needs --yes" in res.output


def test_apply_json_with_yes_is_parseable(runner, obj, org):
    slug = obj["client"].create_study(org, "HPV")["slug"]

    with patch("adopt.server.server.run_study_opt") as plan_m, patch(
        "adopt.server.server.run_single_instruction"
    ) as apply_m:
        plan_m.return_value = _instructions()
        apply_m.return_value = {
            "timestamp": "2026-01-01T00:00:00",
            "instruction": {
                "node": "campaign",
                "action": "create",
                "params": {},
                "id": None,
            },
        }
        res = run(runner, obj, "apply", f"{org}/{slug}", "0", "--yes", "--json")

    assert res.exit_code == 0
    json.loads(res.output)


def test_an_unquoted_date_reaches_the_server_as_the_string_it_will_store(
    runner, obj, org
):
    """End to end for the `json_safe` fix, whose point survives its verdict
    changing.

    Before it, `validate` and `diff` saw a `datetime.date` OBJECT, passed, and
    `push` then died inside the JSON encoder as a fake network error -- AFTER
    writing the sections ordered before recruitment, which cannot be withdrawn.
    Now the same value reaches all three as `"2026-06-01"`.

    Until 2026-09-06 that string was itself rejected by pydantic, so this test
    asserted exit 1 and `section.invalid`. `mcp` floors pydantic at 2.8
    (`pyproject.toml`), the lock moved 2.5.2 -> 2.9.2, and 2.9 parses a bare
    date into midnight -- so the push now succeeds and the server stores
    `2026-06-01T00:00:00`. Strictly more permissive; nothing that used to be
    accepted is rejected. What is asserted here is the invariant rather than
    the verdict: whatever `validate` says, `push` sends the same bytes.
    """
    slug = obj["client"].create_study(org, "HPV")["slug"]
    data = study_dict(org, slug)
    data["recruitment"]["start_date"] = __import__("datetime").date(2026, 6, 1)
    write_study(data=data)

    assert run(runner, obj, "validate").exit_code == 0
    res = run(runner, obj, "push")

    assert res.exit_code == 0, res.output
    stored = obj["client"].get_confs(org, slug)["recruitment"]
    assert stored["start_date"] == "2026-06-01T00:00:00"


# ---------------------------------------------------------------------------
# Review fixes on the accounts group
# ---------------------------------------------------------------------------


def test_accounts_add_surfaces_the_shadowing_refusal(runner, obj):
    """The 409 has to reach the terminal as a sentence, not a traceback -- and
    it has to say why, or the researcher will just pick `--force`, which does
    not exist, and then edit the database."""
    execute(
        db_conf,
        "insert into credentials (user_id, entity, key, details) values (%s,%s,%s,%s)",
        (USER, "facebook", "Facebook", '{"access_token": "tok"}'),
    )
    with open("creds.json", "w", encoding="utf8") as f:
        json.dump({"key": "s"}, f)

    res = run(
        runner,
        obj,
        "accounts",
        "add",
        "Facebook",
        "--type",
        "typeform",
        "--credentials-json",
        "creds.json",
    )

    assert res.exit_code == 1
    assert "409" in res.output
    assert "SHADOW" in res.output


def test_accounts_add_does_not_print_the_secret_on_a_validation_failure(runner, obj):
    """A CLI error goes to the terminal and into any CI log that captures it."""
    secret = "SECRET-IN-CLI-OUTPUT-3f9d"
    with open("creds.json", "w", encoding="utf8") as f:
        json.dump({"api_token": secret}, f)

    res = run(
        runner,
        obj,
        "accounts",
        "add",
        "x",
        "--type",
        "alchemer",
        "--credentials-json",
        "creds.json",
    )

    assert res.exit_code == 1
    assert secret not in res.output
    assert "api_token_secret" in res.output


def test_the_accounts_add_help_warns_about_reusing_a_facebook_name(runner, obj):
    res = run(runner, obj, "accounts", "add", "--help")

    assert "DO NOT REUSE A FACEBOOK CREDENTIAL'S NAME" in res.output
    assert "NAMES may not contain" in res.output


def test_the_accounts_help_says_whose_credentials_these_are(runner, obj):
    res = run(runner, obj, "accounts", "--help")

    assert "shared org" in res.output
