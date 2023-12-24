from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class LeadgenForm(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        allow_organic_lead: str
        block_display_for_non_targeted_viewer: str
        context_card: str
        created_time: str
        creator: str
        expired_leads_count: str
        follow_up_action_text: str
        follow_up_action_url: str
        id: str
        is_optimized_for_quality: str
        leads_count: str
        legal_content: str
        locale: str
        name: str
        organic_leads_count: str
        page: str
        page_id: str
        privacy_policy_url: str
        question_page_custom_headline: str
        questions: str
        status: str
        thank_you_page: str
        tracking_parameters: str
    class Status:
        active: str
        archived: str
        deleted: str
        draft: str
    class Locale:
        ar_ar: str
        cs_cz: str
        da_dk: str
        de_de: str
        el_gr: str
        en_gb: str
        en_us: str
        es_es: str
        es_la: str
        fi_fi: str
        fr_fr: str
        he_il: str
        hi_in: str
        hu_hu: str
        id_id: str
        it_it: str
        ja_jp: str
        ko_kr: str
        nb_no: str
        nl_nl: str
        pl_pl: str
        pt_br: str
        pt_pt: str
        ro_ro: str
        ru_ru: str
        sv_se: str
        th_th: str
        tr_tr: str
        vi_vn: str
        zh_cn: str
        zh_hk: str
        zh_tw: str
    @classmethod
    def get_endpoint(cls): ...
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_update(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_leads(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_test_leads(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_test_lead(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
