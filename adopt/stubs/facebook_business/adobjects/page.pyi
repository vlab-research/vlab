from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class Page(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        about: str
        access_token: str
        ad_campaign: str
        affiliation: str
        app_id: str
        artists_we_like: str
        attire: str
        awards: str
        band_interests: str
        band_members: str
        best_page: str
        bio: str
        birthday: str
        booking_agent: str
        built: str
        business: str
        can_checkin: str
        can_post: str
        category: str
        category_list: str
        checkins: str
        company_overview: str
        connected_instagram_account: str
        connected_page_backed_instagram_account: str
        contact_address: str
        copyright_whitelisted_ig_partners: str
        country_page_likes: str
        cover: str
        culinary_team: str
        current_location: str
        delivery_and_pickup_option_info: str
        description: str
        description_html: str
        differently_open_offerings: str
        directed_by: str
        display_subtext: str
        displayed_message_response_time: str
        does_viewer_have_page_permission_link_ig: str
        emails: str
        engagement: str
        fan_count: str
        featured_video: str
        features: str
        followers_count: str
        food_styles: str
        founded: str
        general_info: str
        general_manager: str
        genre: str
        global_brand_page_name: str
        global_brand_root_id: str
        has_added_app: str
        has_lead_access: str
        has_transitioned_to_new_page_experience: str
        has_whatsapp_business_number: str
        has_whatsapp_enterprise_number_using_cloud_api: str
        has_whatsapp_number: str
        hometown: str
        hours: str
        id: str
        impressum: str
        influences: str
        instagram_business_account: str
        is_always_open: str
        is_chain: str
        is_community_page: str
        is_eligible_for_branded_content: str
        is_eligible_for_disable_connect_ig_btn_for_non_page_admin_am_web: str
        is_messenger_bot_get_started_enabled: str
        is_messenger_platform_bot: str
        is_owned: str
        is_permanently_closed: str
        is_published: str
        is_unclaimed: str
        is_verified: str
        is_webhooks_subscribed: str
        keywords: str
        leadgen_tos_acceptance_time: str
        leadgen_tos_accepted: str
        leadgen_tos_accepting_user: str
        link: str
        location: str
        members: str
        merchant_id: str
        merchant_review_status: str
        messaging_feature_status: str
        messenger_ads_default_icebreakers: str
        messenger_ads_default_quick_replies: str
        messenger_ads_quick_replies_type: str
        mini_shop_storefront: str
        mission: str
        mpg: str
        name: str
        name_with_location_descriptor: str
        network: str
        new_like_count: str
        offer_eligible: str
        overall_star_rating: str
        owner_business: str
        page_about_story: str
        page_token: str
        parent_page: str
        parking: str
        payment_options: str
        personal_info: str
        personal_interests: str
        pharma_safety_info: str
        phone: str
        pickup_options: str
        place_type: str
        plot_outline: str
        preferred_audience: str
        press_contact: str
        price_range: str
        privacy_info_url: str
        produced_by: str
        products: str
        promotion_eligible: str
        promotion_ineligible_reason: str
        public_transit: str
        rating_count: str
        recipient: str
        record_label: str
        release_date: str
        restaurant_services: str
        restaurant_specialties: str
        schedule: str
        screenplay_by: str
        season: str
        single_line_address: str
        starring: str
        start_info: str
        store_code: str
        store_location_descriptor: str
        store_number: str
        studio: str
        supports_donate_button_in_live_video: str
        talking_about_count: str
        temporary_status: str
        unread_message_count: str
        unread_notif_count: str
        unseen_message_count: str
        user_access_expire_time: str
        username: str
        verification_status: str
        voip_info: str
        website: str
        were_here_count: str
        whatsapp_number: str
        written_by: str
    class Attire:
        casual: str
        dressy: str
        unspecified: str
    class FoodStyles:
        afghani: str
        american_new_: str
        american_traditional_: str
        asian_fusion: str
        barbeque: str
        brazilian: str
        breakfast: str
        british: str
        brunch: str
        buffets: str
        burgers: str
        burmese: str
        cajun_creole: str
        caribbean: str
        chinese: str
        creperies: str
        cuban: str
        delis: str
        diners: str
        ethiopian: str
        fast_food: str
        filipino: str
        fondue: str
        food_stands: str
        french: str
        german: str
        greek_and_mediterranean: str
        hawaiian: str
        himalayan_nepalese: str
        hot_dogs: str
        indian_pakistani: str
        irish: str
        italian: str
        japanese: str
        korean: str
        latin_american: str
        mexican: str
        middle_eastern: str
        moroccan: str
        pizza: str
        russian: str
        sandwiches: str
        seafood: str
        singaporean: str
        soul_food: str
        southern: str
        spanish_basque: str
        steakhouses: str
        sushi_bars: str
        taiwanese: str
        tapas_bars: str
        tex_mex: str
        thai: str
        turkish: str
        vegan: str
        vegetarian: str
        vietnamese: str
    class PickupOptions:
        curbside: str
        in_store: str
        other: str
    class TemporaryStatus:
        differently_open: str
        no_data: str
        operating_as_usual: str
        temporarily_closed: str
    class PermittedTasks:
        advertise: str
        analyze: str
        cashier_role: str
        create_content: str
        manage: str
        manage_jobs: str
        manage_leads: str
        messaging: str
        moderate: str
        moderate_community: str
        pages_messaging: str
        pages_messaging_subscriptions: str
        profile_plus_advertise: str
        profile_plus_analyze: str
        profile_plus_create_content: str
        profile_plus_facebook_access: str
        profile_plus_full_control: str
        profile_plus_manage: str
        profile_plus_manage_leads: str
        profile_plus_messaging: str
        profile_plus_moderate: str
        profile_plus_moderate_delegate_community: str
        profile_plus_revenue: str
        read_page_mailboxes: str
        view_monetization_insights: str
    class Tasks:
        advertise: str
        analyze: str
        cashier_role: str
        create_content: str
        manage: str
        manage_jobs: str
        manage_leads: str
        messaging: str
        moderate: str
        moderate_community: str
        pages_messaging: str
        pages_messaging_subscriptions: str
        profile_plus_advertise: str
        profile_plus_analyze: str
        profile_plus_create_content: str
        profile_plus_facebook_access: str
        profile_plus_full_control: str
        profile_plus_manage: str
        profile_plus_manage_leads: str
        profile_plus_messaging: str
        profile_plus_moderate: str
        profile_plus_moderate_delegate_community: str
        profile_plus_revenue: str
        read_page_mailboxes: str
        view_monetization_insights: str
    class Alignment:
        left: str
        right: str
    class EntryPointIcon:
        chat_angular_icon: str
        chat_round_icon: str
        messenger_icon: str
        none: str
    class EntryPointLabel:
        ask_us: str
        chat: str
        help: str
        none: str
    class GreetingDialogDisplay:
        hide: str
        show: str
        welcome_message: str
    class GuestChatMode:
        disabled: str
        enabled: str
    class MobileChatDisplay:
        app_switch: str
        chat_tab: str
    class BackdatedTimeGranularity:
        day: str
        hour: str
        min: str
        month: str
        none: str
        year: str
    class Formatting:
        markdown: str
        plaintext: str
    class PlaceAttachmentSetting:
        value_1: str
        value_2: str
    class PostSurfacesBlacklist:
        value_1: str
        value_2: str
        value_3: str
        value_4: str
        value_5: str
    class PostingToRedspace:
        disabled: str
        enabled: str
    class TargetSurface:
        story: str
        timeline: str
    class UnpublishedContentType:
        ads_post: str
        draft: str
        inline_created: str
        published: str
        reviewable_branded_content: str
        scheduled: str
        scheduled_recurring: str
    class MessagingType:
        message_tag: str
        response: str
        update: str
    class NotificationType:
        no_push: str
        regular: str
        silent_push: str
    class SenderAction:
        mark_seen: str
        react: str
        typing_off: str
        typing_on: str
        unreact: str
    class SuggestionAction:
        accept: str
        dismiss: str
        impression: str
    class Platform:
        instagram: str
        messenger: str
    class Model:
        arabic: str
        chinese: str
        croatian: str
        custom: str
        danish: str
        dutch: str
        english: str
        french_standard: str
        georgian: str
        german_standard: str
        greek: str
        hebrew: str
        hungarian: str
        irish: str
        italian_standard: str
        korean: str
        norwegian_bokmal: str
        polish: str
        portuguese: str
        romanian: str
        spanish: str
        swedish: str
        vietnamese: str
    class DeveloperAction:
        enable_followup_message: str
    class SubscribedFields:
        affiliation: str
        attire: str
        awards: str
        bio: str
        birthday: str
        category: str
        checkins: str
        company_overview: str
        conversations: str
        culinary_team: str
        current_location: str
        description: str
        email: str
        feature_access_list: str
        feed: str
        founded: str
        general_info: str
        general_manager: str
        group_feed: str
        hometown: str
        hours: str
        inbox_labels: str
        invalid_topic_placeholder: str
        invoice_access_bank_slip_events: str
        invoice_access_invoice_change: str
        invoice_access_invoice_draft_change: str
        invoice_access_onboarding_status_active: str
        leadgen: str
        leadgen_fat: str
        live_videos: str
        local_delivery: str
        location: str
        mcom_invoice_change: str
        members: str
        mention: str
        merchant_review: str
        message_context: str
        message_deliveries: str
        message_echoes: str
        message_mention: str
        message_reactions: str
        message_reads: str
        messages: str
        messaging_account_linking: str
        messaging_appointments: str
        messaging_checkout_updates: str
        messaging_customer_information: str
        messaging_direct_sends: str
        messaging_fblogin_account_linking: str
        messaging_feedback: str
        messaging_game_plays: str
        messaging_handovers: str
        messaging_in_thread_lead_form_submit: str
        messaging_optins: str
        messaging_optouts: str
        messaging_payments: str
        messaging_policy_enforcement: str
        messaging_postbacks: str
        messaging_pre_checkouts: str
        messaging_referrals: str
        mission: str
        name: str
        otp_verification: str
        page_about_story: str
        page_change_proposal: str
        page_upcoming_change: str
        parking: str
        payment_options: str
        personal_info: str
        personal_interests: str
        phone: str
        picture: str
        price_range: str
        product_review: str
        products: str
        public_transit: str
        publisher_subscriptions: str
        ratings: str
        registration: str
        send_cart: str
        standby: str
        user_action: str
        video_text_question_responses: str
        videos: str
        website: str
    @classmethod
    def get_endpoint(cls): ...
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_update(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_ab_tests(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_ab_test(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_acknowledge_order(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_ads_posts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def delete_agencies(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_agencies(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_agency(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_albums(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_ar_experience(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def delete_assigned_users(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_assigned_users(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_assigned_user(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def delete_blocked(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_blocked(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_blocked(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_business_datum(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_business_projects(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_call_to_actions(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_canvas_elements(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_canvas_element(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_canvases(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_canvase(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_chat_plugin(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_chat_plugin(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_commerce_eligibility(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_commerce_merchant_settings(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_commerce_orders(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_commerce_payouts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_commerce_transactions(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_conversations(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_copyright_manual_claim(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_crosspost_whitelisted_pages(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_custom_labels(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_custom_label(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def delete_custom_user_settings(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_custom_user_settings(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_custom_user_setting(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_dataset(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_events(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_extend_thread_control(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_fantasy_games(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_feed(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_feed(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_global_brand_children(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_groups(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_image_copyrights(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_image_copyright(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_indexed_videos(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_insights(self, fields: Incomplete | None = None, params: Incomplete | None = None, is_async: bool = False, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_instagram_accounts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_instant_articles_stats(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_lead_gen_forms(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_lead_gen_form(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_likes(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_live_videos(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_live_video(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def delete_locations(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_locations(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_location(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_media_fingerprints(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_media_fingerprint(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_message_attachment(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_message(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_messaging_feature_review(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_messenger_lead_forms(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_messenger_lead_form(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def delete_messenger_profile(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_messenger_profile(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_messenger_profile(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_nlp_config(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_notification_message_tokens(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_notification_messages_dev_support(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_page_backed_instagram_accounts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_page_backed_instagram_account(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_page_whatsapp_number_verification(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_pass_thread_control(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_pass_thread_metadatum(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_personas(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_persona(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_photo_story(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_photos(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_photo(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_picture(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_picture(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_posts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_product_catalogs(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_published_posts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_ratings(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_release_thread_control(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_request_thread_control(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_roles(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_rtb_dynamic_posts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_scheduled_posts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_secondary_receivers(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_settings(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_setting(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_shop_setup_status(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_stories(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def delete_subscribed_apps(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_subscribed_apps(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_subscribed_app(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_tabs(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_tagged(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_take_thread_control(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_thread_owner(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_threads(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_unlink_account(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_video_copyright_rules(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_video_copyright_rule(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_video_copyright(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_video_lists(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_video_reels(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_video_reel(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_video_story(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_videos(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_video(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_visitor_posts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def delete_welcome_message_flows(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_welcome_message_flows(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_welcome_message_flow(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
