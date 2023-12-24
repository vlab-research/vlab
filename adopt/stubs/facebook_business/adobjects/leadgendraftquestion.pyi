from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class LeadGenDraftQuestion(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        conditional_questions_choices: str
        conditional_questions_group_id: str
        dependent_conditional_questions: str
        inline_context: str
        key: str
        label: str
        options: str
        type: str
