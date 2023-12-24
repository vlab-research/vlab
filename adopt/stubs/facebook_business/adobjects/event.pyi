from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class Event(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        attending_count: str
        can_guests_invite: str
        category: str
        cover: str
        created_time: str
        declined_count: str
        description: str
        discount_code_enabled: str
        end_time: str
        event_times: str
        guest_list_enabled: str
        id: str
        interested_count: str
        is_canceled: str
        is_draft: str
        is_online: str
        is_page_owned: str
        maybe_count: str
        name: str
        noreply_count: str
        online_event_format: str
        online_event_third_party_url: str
        owner: str
        parent_group: str
        place: str
        registration_setting: str
        scheduled_publish_time: str
        start_time: str
        ticket_setting: str
        ticket_uri: str
        ticket_uri_start_sales_time: str
        ticketing_privacy_uri: str
        ticketing_terms_uri: str
        timezone: str
        type: str
        updated_time: str
    class Category:
        classic_literature: str
        comedy: str
        crafts: str
        dance: str
        drinks: str
        fitness_and_workouts: str
        foods: str
        games: str
        gardening: str
        healthy_living_and_self_care: str
        health_and_medical: str
        home_and_garden: str
        music_and_audio: str
        parties: str
        professional_networking: str
        religions: str
        shopping_event: str
        social_issues: str
        sports: str
        theater: str
        tv_and_movies: str
        visual_arts: str
    class OnlineEventFormat:
        fb_live: str
        messenger_room: str
        none: str
        other: str
        third_party: str
    class Type:
        community: str
        friends: str
        group: str
        private: str
        public: str
        work_company: str
    class EventStateFilter:
        canceled: str
        draft: str
        published: str
        scheduled_draft_for_publication: str
    class TimeFilter:
        past: str
        upcoming: str
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_comments(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_feed(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_live_videos(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def create_live_video(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_photos(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_picture(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_posts(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_roles(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_ticket_tiers(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def get_videos(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
