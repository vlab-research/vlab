from datetime import datetime, timezone
from typing import Any, Dict, NamedTuple, Optional, Tuple

import requests

from .state import FacebookState, call

Provenance = Dict[str, Any]


class Instruction(NamedTuple):
    node: str
    action: str
    params: Dict[str, Any]
    id: Optional[str] = None

    # What this instruction is *for*, in vlab's own vocabulary, as opposed to
    # `params`, which is what Facebook is told. Only ad creates carry it, and
    # only so the imperative shell can write the ad -> stratum mapping row once
    # Facebook returns the new id. Optional and defaulted so that every
    # existing construction site -- campaigns, adsets, audiences, updates,
    # deletes -- is unchanged.
    #
    # Carried on the instruction rather than recomputed after the fact because
    # the mapping has to be joined to the ad that was actually created, and
    # `_diff` is the only place that knows which ads those are. Generating the
    # instruction stays pure; the write happens in run_instructions.
    provenance: Optional[Provenance] = None


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


def created_id(res: Any) -> Optional[str]:
    """The id of a freshly created Graph object, or None if we can't find one.

    The SDK's create_* methods hand back an AbstractCrudObject whose `id` is
    populated from the response. Not every node type is guaranteed to do so,
    and `call` is generic, so this stays defensive: a missing id must not blow
    up the reconciliation run that just successfully created an ad. The caller
    treats None as "nothing to record" and the absence shows up as an unmapped
    ad downstream, which is a counted, visible failure rather than a crash.
    """
    if res is None:
        return None

    try:
        id_ = res["id"]
    except (KeyError, TypeError, IndexError):
        try:
            id_ = res.get_id()
        except AttributeError:
            return None

    return str(id_) if id_ is not None else None


def add_users_to_custom_audience(token, aud_id, params):
    # TOOD: get the base url from somewhere!
    url = f"https://graph.facebook.com/v20.0/{aud_id}/users?access_token={token}"
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
    def __init__(self, state: FacebookState):
        self.state = state
        self.account = state.account

        self.objects = {
            "adset": getter("adset", state, "adsets"),
            "ad": getter("ad", state, "ads"),
            "campaign": getter("campaign", state, "campaigns"),
            "custom_audience": getter("custom_audience", state, "custom_audiences"),
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

    def execute(self, instruction: Instruction) -> Tuple[Dict[str, Any], Optional[str]]:
        """Run one instruction. Returns (report, created_id).

        `created_id` is the id Facebook assigned to a newly created object, and
        None for every other action. It used to be dropped on the floor; it is
        the only moment at which vlab learns the ad id it needs in order to own
        the ad -> stratum join, and there is no way to recover it afterwards
        that does not go back to the Graph API.
        """
        if instruction.action == "update":
            obj = self.get_object(instruction.node, instruction.id)
            call(obj.api_update, params=instruction.params, fields=[])
            return report(instruction), None

        if instruction.action == "delete":
            obj = self.get_object(instruction.node, instruction.id)
            call(obj.api_delete)
            return report(instruction), None

        if instruction.action == "create":
            create = self.get_create(instruction.node)
            res = call(create, params=instruction.params, fields=[])
            return report(instruction), created_id(res)

        if instruction.action == "add_users":
            # special case, node-edge
            # think about how to make this more general
            aud = self.get_object(instruction.node, instruction.id)

            call(aud.create_users_replace, params=instruction.params, fields=[])

            return report(instruction), None

        raise InstructionError(
            f"action: {instruction.action} not a valid instruction action"
        )
