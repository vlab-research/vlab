from datetime import datetime, timezone
from typing import Optional, Dict, Any, NamedTuple
from .state import CampaignState, call


class Instruction(NamedTuple):
    node: str
    action: str
    params: Dict[str, Any]
    id: Optional[str]

class InstructionError(BaseException):
    pass

def report(i: Instruction):
    return {
        'timestamp': datetime.now(tz=timezone.utc).isoformat(),
        'instruction': {
            'node': i.node,
            'action': i.action,
            'id': i.id,
            'params': i.params
        }
    }

class GraphUpdater():
    def __init__(self, state: CampaignState):
        self.account = state.account
        self.objects = {
            'adset': {a['id']: a for a in state.adsets},
            'ad': {a['id']: a for a in state.ads},
            'creative': {c['id']: c for c in state.creatives},
            # custom_audience??
        }

    def get_object(self, type_, id_):
        try:
            return self.objects[type_][id_]
        except KeyError:
            raise InstructionError(f'Could not find id {id_} of type {type_}')

    def execute(self, instruction: Instruction):
        creates = {
            'adset': self.account.create_ad_set,
            'adcreative': self.account.create_ad_creative,
            'ad': self.account.create_ad,
            'custom_audience': self.account.create_custom_audience,
            'campaign': self.account.create_campaign
        }

        # how to update add users...??? Fail.

        if instruction.action == 'update':
            obj = self.get_object(instruction.node, instruction.id)
            call(obj.api_update, instruction.params, [])
            return report(instruction)

        if instruction.action == 'create':
            create = creates[instruction.node]
            call(create, instruction.params, [])
            return report(instruction)

        raise InstructionError(f'action: {instruction.action} not a valid instruction action')
