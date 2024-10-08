from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class LeadGenFormPreviewDetails(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        call_to_action_title: str
        contact_information_text: str
        creatives_overview_default_text: str
        data_privacy_policy_setting_description: str
        default_appointment_scheduling_inline_context: str
        default_disqualified_end_component: str
        default_thank_you_page: str
        disqualified_thank_you_card_transparency_info_text: str
        edit_text: str
        email_inline_context_text: str
        email_messenger_push_opt_in_disclaimer: str
        email_messenger_push_opt_in_transparency_text: str
        form_clarity_description_content: str
        form_clarity_description_title: str
        form_clarity_headline: str
        gated_content_locked_description: str
        gated_content_locked_headline: str
        gated_content_unlocked_description: str
        gated_content_unlocked_headline: str
        how_it_works_section_headers: str
        next_button_text: str
        optional_question_text: str
        personal_info_text: str
        phone_number_inline_context_text: str
        privacy_policy_title_section_title_text: str
        privacy_setting_description: str
        products_section_headers: str
        qualified_thank_you_card_transparency_info_text: str
        review_your_info_text: str
        secure_sharing_text: str
        slide_to_submit_text: str
        social_proof_section_headers: str
        submit_button_text: str
