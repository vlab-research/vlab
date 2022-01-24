# everything to do with getting all config for a study.

# one well definted type instead of "Malaria?"


@dataclass(frozen=True)
class Study:
    userinfo: UserInfo
    config: CampaignConf
    db_conf: DBConf
    state: CampaignState
    m: Marketing
    confs: Dict[str, Any]
