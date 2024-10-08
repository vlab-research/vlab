from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class AdContract(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        account_id: str
        account_mgr_fbid: str
        account_mgr_name: str
        adops_person_name: str
        advertiser_address_fbid: str
        advertiser_fbid: str
        advertiser_name: str
        agency_discount: str
        agency_name: str
        bill_to_address_fbid: str
        bill_to_fbid: str
        campaign_name: str
        created_by: str
        created_date: str
        customer_io: str
        io_number: str
        io_terms: str
        io_type: str
        last_updated_by: str
        last_updated_date: str
        max_end_date: str
        mdc_fbid: str
        media_plan_number: str
        min_start_date: str
        msa_contract: str
        payment_terms: str
        rev_hold_flag: str
        rev_hold_released_by: str
        rev_hold_released_on: str
        salesrep_fbid: str
        salesrep_name: str
        sold_to_address_fbid: str
        sold_to_fbid: str
        status: str
        subvertical: str
        thirdparty_billed: str
        thirdparty_uid: str
        thirdparty_url: str
        vat_country: str
        version: str
        vertical: str
