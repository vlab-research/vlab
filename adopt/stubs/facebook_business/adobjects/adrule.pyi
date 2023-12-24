from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class AdRule(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        account_id: str
        created_by: str
        created_time: str
        evaluation_spec: str
        execution_spec: str
        id: str
        name: str
        schedule_spec: str
        status: str
        updated_time: str
        ui_creation_source: str
    class Status:
        deleted: str
        disabled: str
        enabled: str
        has_issues: str
    class UiCreationSource:
        am_account_overview_recommendations: str
        am_activity_history_table: str
        am_ad_object_name_card: str
        am_amfe_l3_recommendation: str
        am_autoflow_guidance_card: str
        am_auto_apply_widget: str
        am_editor_card: str
        am_info_card: str
        am_name_cell_dropdown: str
        am_optimization_tip_guidance_card: str
        am_performance_summary: str
        am_rule_landing_page_banner: str
        am_syd_resolution_flow: str
        am_syd_resolution_flow_modal: str
        am_table_delivery_column_popover: str
        am_table_toggle_popover: str
        am_toolbar_create_rule_dropdown: str
        pe_campaign_structure_menu: str
        pe_editor_card: str
        pe_info_card: str
        pe_toolbar_create_rule_dropdown: str
        rules_management_page_action_dropdown: str
        rules_management_page_rule_group: str
        rules_management_page_rule_name: str
        rules_management_page_top_nav: str
        rules_view_active_rules_dialog: str
        rule_creation_success_dialog: str
        rule_syd_redirect: str
        rule_templates_dialog: str
    @classmethod
    def get_endpoint(cls): ...
    def api_create(self, parent_id, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_delete(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_update(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_execute(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_history(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_preview(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
