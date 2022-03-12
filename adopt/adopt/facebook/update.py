from datetime import datetime, timezone
from typing import Any, Dict, NamedTuple, Optional

import requests

from .state import CampaignState, call


class Instruction(NamedTuple):
    node: str
    action: str
    params: Dict[str, Any]
    id: Optional[str] = None


class InstructionError(BaseException):
    pass


def report(i: Instruction):
    return {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "instruction": {
            "node": i.node,
            "action": i.action,
            "id": i.id,
            "params": i.params,
        },
    }


def add_users_to_custom_audience(token, aud_id, params):
    # TOOD: get the base url from somewhere!
    url = f"https://graph.facebook.com/v11.0/{aud_id}/users?access_token={token}"
    return requests.post(url, json={"payload": params})


def getter(type_, obj, prop):
    """Lazy so that nothing more gets loaded than needed"""

    def _getter(i):
        coll = getattr(obj, prop)
        val = next((a for a in coll if a["id"] == i), None)
        if val is None:
            raise InstructionError(f"Could not find id {i} of type {type_}")
        return val

    return _getter


class GraphUpdater:
    def __init__(self, state: CampaignState):
        self.state = state
        self.account = state.account

        self.objects = {
            "adset": getter("adset", state, "adsets"),
            "ad": getter("ad", state, "ads"),
            "campaign": getter("campaign", state, "campaigns"),
            "custom_audience": getter(
                "custom_audience", state.facebook_state, "custom_audiences"
            ),
        }

        self.creates = {
            "adset": self.account.create_ad_set,
            "adcreative": self.account.create_ad_creative,
            "ad": self.account.create_ad,
            "custom_audience": self.account.create_custom_audience,
            "campaign": self.account.create_campaign,
        }

    def get_create(self, node):
        try:
            return self.creates[node]
        except KeyError:
            raise InstructionError(
                f"Could not find create instruction for node of type {node}"
            )

    def get_object(self, type_, id_):
        return self.objects[type_](id_)

    def execute(self, instruction: Instruction):
        if instruction.action == "update":
            obj = self.get_object(instruction.node, instruction.id)
            call(obj.api_update, params=instruction.params, fields=[])
            return report(instruction)

        if instruction.action == "delete":
            obj = self.get_object(instruction.node, instruction.id)
            call(obj.api_delete)
            return report(instruction)

        if instruction.action == "create":
            create = self.get_create(instruction.node)
            call(create, params=instruction.params, fields=[])
            return report(instruction)

        if instruction.action == "add_users":
            # special case, node-edge
            # think about how to make this more general
            aud = self.get_object(instruction.node, instruction.id)

            call(aud.create_users_replace, params=instruction.params, fields=[])

            return report(instruction)

        raise InstructionError(
            f"action: {instruction.action} not a valid instruction action"
        )
