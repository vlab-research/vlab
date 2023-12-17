from dataclasses import asdict
from itertools import product
from test.dbfix import _reset_db
from test.dbfix import cnf as db_conf

from .campaign_queries import (create_campaign_confs,
                                    create_campaign_for_user,
                                    get_campaigns_for_user)

from .configuration import (TargetingConf, format_group_product,
                            parse_kv_sheet, parse_row_sheet, read_share_lookup,
                            respondent_audience_name)
from .db import _connect, execute
from .marketing import dict_from_nested_type
from .study_conf import (AppDestination, AudienceConf, CreativeConf,
                         FlyMessengerDestination, GeneralConf,
                         PipelineRecruitmentExperiment, StratumConf)


def create_user(email):
    q = """
    insert into users(id) values(%s) on conflict do nothing
    """
    execute(db_conf, q, [email])

    q = """
    insert into credentials(user_id, entity, key, details) values(
      %s,
      'facebook_ad_user',
      'default',
      '{"access_token": "foo"}'
    )
    """
    execute(db_conf, q, [email])


def test_make_study():
    _reset_db()

    config_file = "test/example_ads_conf_fly.xlsx"
    user = "foo@email"

    create_user(user)

    config = parse_kv_sheet(config_file, "general", GeneralConf)

    CAMPAIGN = config.name

    create_campaign_for_user(user, CAMPAIGN, db_conf, "default")
    CAMPAIGNID = next(
        c["id"] for c in get_campaigns_for_user(user, db_conf) if c["name"] == CAMPAIGN
    )

    create_campaign_confs(CAMPAIGNID, "general", config.dict(), db_conf)

    destination = parse_kv_sheet(config_file, "destination", FlyMessengerDestination)
    create_campaign_confs(CAMPAIGNID, "destinations", [destination.dict()], db_conf)

    recruitment = parse_kv_sheet(
        config_file, "recruitment_pipeline_experiment", PipelineRecruitmentExperiment
    )

    create_campaign_confs(CAMPAIGNID, "recruitment", recruitment.dict(), db_conf)

    audiences = [
        {
            "name": respondent_audience_name(config),
            "subtype": "CUSTOM",
        },
    ]

    audience_confs = [AudienceConf(**c) for c in audiences]

    confs = [a.dict() for a in audience_confs]
    create_campaign_confs(CAMPAIGNID, "audiences", confs, db_conf)

    creative_confs = parse_row_sheet(config_file, "creative", CreativeConf)
    confs = [a.dict() for a in creative_confs]
    # print(creative_confs)
    create_campaign_confs(CAMPAIGNID, "creatives", confs, db_conf)

    # destination, creative_confs, config
    def make_stratum(id_, quota, c):
        return {
            "id": id_,
            "metadata": c["metadata"],
            "facebook_targeting": c["facebook_targeting"],
            "creatives": [t.name for t in creative_confs],
            "audiences": c["audiences"],
            "excluded_audiences": [
                *c["excluded_audiences"],
                respondent_audience_name(config),
            ],
            "quota": float(quota),
            "question_targeting": c["question_targeting"],
        }

    a = {"levels": [{"name": "18", "params": {"age_max": 24, "age_min": 18}}]}

    g = {
        "levels": [
            {"name": "2", "params": {"genders": [2]}},
            {"name": "1", "params": {"genders": [1]}},
        ]
    }

    l = {
        "levels": [
            {
                "name": "US",
                "params": {
                    "geo_locations": {
                        "countries": ["US"],
                        "location_types": ["home", "recent"],
                    }
                },
            }
        ]
    }

    variables = [
        {"name": "age", "source": "facebook", "conf": a},
        {"name": "gender", "source": "facebook", "conf": g},
        {"name": "location", "source": "facebook", "conf": l},
    ]

    targeting = parse_kv_sheet(config_file, "targeting", TargetingConf)

    share = read_share_lookup(
        config_file, targeting.distribution_vars, "targeting_distribution"
    )

    groups = product(
        *[[(v["name"], v["source"], l) for l in v["conf"]["levels"]] for v in variables]
    )

    base_targeting = {}

    if isinstance(destination, AppDestination):
        base_targeting = {
            "app_install_state": destination.app_install_state,
            "user_device": destination.user_device,
            "user_os": destination.user_os,
        }

    finish_filter = {
        "op": "greater_than",
        "vars": [
            {"type": "variable", "value": "highest_segment"},
            {"type": "constant", "value": 4},
        ],
    }

    groups = [
        format_group_product(g, share, base_targeting, finish_filter) for g in groups
    ]

    strata = [make_stratum(*g) for g in groups]

    strata_data = [StratumConf(**c).dict() for c in strata]

    create_campaign_confs(CAMPAIGNID, "strata", strata_data, db_conf)

    import os

    os.environ["CHATBASE_DATABASE"] = "test"
    os.environ["CHATBASE_USER"] = "root"
    os.environ["CHATBASE_HOST"] = "localhost"
    os.environ["CHATBASE_PORT"] = "5433"

    os.environ["FACEBOOK_APP_ID"] = "123"
    os.environ["FACEBOOK_APP_SECRET"] = "123"

    from environs import Env

    from .malaria import load_basics

    env = Env()

    study, state = load_basics(CAMPAIGNID, db_conf, env)

    assert study.destinations[0].name == "fly"
    assert study.creatives[0].destination == "fly"
    assert isinstance(study.recruitment, PipelineRecruitmentExperiment)
    assert study.recruitment.arms == 2
