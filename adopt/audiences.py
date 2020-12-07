import logging
from typing import List

from facebook_business.adobjects.customaudience import CustomAudience

from .clustering import only_target_users
from .facebook.state import CampaignState
from .facebook.update import Instruction
from .marketing import (Audience, add_users_to_audience,
                        create_custom_audience, create_lookalike_audience)


def get_users_for_audience(df, aud: Audience) -> List[str]:
    target = only_target_users(df, aud)
    return target.userid.unique().tolist()


def aud_name(aud: Audience) -> str:
    return f"vlab-managed-audience-{aud.name}"


def lookalike_name(aud: Audience) -> str:
    s = aud.lookalike_spec
    if s is None:
        raise Exception(
            "Cannot get lookalike name aud {aud.name}, missing lookalike_spec!"
        )

    return aud_name(aud) + f"-lookalike-{s.country}-{s.starting_ratio}-{s.ratio}"


def create_lookalike(aud: Audience, source: CustomAudience) -> Instruction:
    name = lookalike_name(aud)
    if aud.lookalike_spec is None:
        raise Exception(
            "Cannot create lookalike from aud {aud.name}, missing lookalike_spec!"
        )

    return create_lookalike_audience(name, aud.lookalike_spec._asdict(), source)


def create_audience(aud: Audience) -> Instruction:
    name = aud_name(aud)
    return create_custom_audience(name, "virtual lab auto-generated audience")


def update_audience(df, aud: Audience, state: CampaignState) -> List[Instruction]:
    # except StateNameError:
    # create_audience(updater, aud)
    # ca = updater.state.get_audience(aud.name)

    ca = state.get_audience(aud.name)
    users = get_users_for_audience(df, aud)

    logging.info(f'Adding {len(users)} users to audience {ca.get("name")}.')

    instructions = add_users_to_audience(state.cnf["PAGE_ID"], ca.get_id(), users)
    return instructions


def get_lookalike(state: CampaignState, aud: Audience) -> CustomAudience:
    return state.get_audience(lookalike_name(aud))
