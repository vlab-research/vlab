from _typeshed import Incomplete
from facebook_business.adobjects.abstractcrudobject import AbstractCrudObject as AbstractCrudObject
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject
from facebook_business.adobjects.objectparser import ObjectParser as ObjectParser
from facebook_business.api import FacebookRequest as FacebookRequest
from facebook_business.typechecker import TypeChecker as TypeChecker

class PageCallToAction(AbstractCrudObject):
    def __init__(self, fbid: Incomplete | None = None, parent_id: Incomplete | None = None, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        android_app: str
        android_deeplink: str
        android_destination_type: str
        android_package_name: str
        android_url: str
        created_time: str
        email_address: str
        field_from: str
        id: str
        intl_number_with_plus: str
        iphone_app: str
        iphone_deeplink: str
        iphone_destination_type: str
        iphone_url: str
        status: str
        type: str
        updated_time: str
        web_destination_type: str
        web_url: str
    class AndroidDestinationType:
        app_deeplink: str
        become_a_volunteer: str
        email: str
        facebook_app: str
        follow: str
        marketplace_inventory_page: str
        menu_on_facebook: str
        messenger: str
        mini_shop: str
        mobile_center: str
        none: str
        phone_call: str
        shop_on_facebook: str
        website: str
    class IphoneDestinationType:
        app_deeplink: str
        become_a_volunteer: str
        email: str
        facebook_app: str
        follow: str
        marketplace_inventory_page: str
        menu_on_facebook: str
        messenger: str
        mini_shop: str
        none: str
        phone_call: str
        shop_on_facebook: str
        website: str
    class Type:
        become_a_volunteer: str
        book_appointment: str
        book_now: str
        buy_tickets: str
        call_now: str
        charity_donate: str
        check_in: str
        contact_us: str
        donate_now: str
        email: str
        follow_page: str
        get_directions: str
        get_offer: str
        get_offer_view: str
        interested: str
        learn_more: str
        listen: str
        local_dev_platform: str
        message: str
        mobile_center: str
        open_app: str
        order_food: str
        play_music: str
        play_now: str
        purchase_gift_cards: str
        request_appointment: str
        request_quote: str
        shop_now: str
        shop_on_facebook: str
        sign_up: str
        view_inventory: str
        view_menu: str
        view_shop: str
        visit_group: str
        watch_now: str
        woodhenge_support: str
    class WebDestinationType:
        become_a_volunteer: str
        become_supporter: str
        email: str
        follow: str
        messenger: str
        mobile_center: str
        none: str
        shop_on_facebook: str
        website: str
    def api_delete(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_get(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
    def api_update(self, fields: Incomplete | None = None, params: Incomplete | None = None, batch: Incomplete | None = None, success: Incomplete | None = None, failure: Incomplete | None = None, pending: bool = False): ...
