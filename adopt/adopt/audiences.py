import logging
from typing import List

import pandas as pd

from .clustering import only_target_users
from .facebook.state import CampaignState
from .facebook.update import Instruction
from .marketing import Audience, AudienceConf, Marketing, add_users_to_audience


def get_users_for_audience(df, aud: AudienceConf) -> List[str]:
    target = only_target_users(df, aud)
    if target is None:
        return []
    return target.userid.unique().tolist()


def update_audience(
    df, pageid, aud: AudienceConf, state: CampaignState
) -> List[Instruction]:
    ca = state.get_audience(aud.name)
    users = get_users_for_audience(df, aud)

    logging.info(f'Adding {len(users)} users to audience {ca.get("name")}.')

    instructions = add_users_to_audience(pageid, ca.get_id(), users)
    return instructions


def hydrate_audience(df: pd.DataFrame, m: Marketing, aud: AudienceConf) -> Audience:
    users = get_users_for_audience(df, aud)

    d = {
        "name": aud.name,
        "subtype": aud.subtype,
        "users": users,
        "pageid": m.cnf["PAGE_ID"],
        "lookalike": aud.lookalike,
    }

    return Audience(**d)


def hydrate_audiences(
    df: pd.DataFrame, m: Marketing, auds: List[AudienceConf]
) -> List[Audience]:
    return [hydrate_audience(df, m, aud) for aud in auds]
