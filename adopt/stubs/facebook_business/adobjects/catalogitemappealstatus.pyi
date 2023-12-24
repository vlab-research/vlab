from _typeshed import Incomplete
from facebook_business.adobjects.abstractobject import AbstractObject as AbstractObject

class CatalogItemAppealStatus(AbstractObject):
    def __init__(self, api: Incomplete | None = None) -> None: ...
    class Field(AbstractObject.Field):
        handle: str
        item_id: str
        status: str
        use_cases: str
    class Status:
        this_item_cannot_be_appealed_as_it_is_either_approved_or_already_has_an_appeal: str
        this_item_is_not_rejected_for_any_of_channels: str
        we_ve_encountered_unexpected_error_while_processing_this_request_please_try_again_later_: str
        you_ve_reached_the_maximum_number_of_item_requests_you_can_make_this_week_you_ll_be_able_to_request_item_reviews_again_within_the_next_7_days_: str
        your_request_was_received_see_information_below_to_learn_more_: str
