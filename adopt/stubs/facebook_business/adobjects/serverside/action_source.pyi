from enum import Enum

class ActionSource(Enum):
    EMAIL: str
    WEBSITE: str
    APP: str
    PHONE_CALL: str
    CHAT: str
    PHYSICAL_STORE: str
    SYSTEM_GENERATED: str
    BUSINESS_MESSAGING: str
    OTHER: str
