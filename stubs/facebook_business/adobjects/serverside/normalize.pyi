from typing import Any

location_excluded_chars: Any
isocode_included_chars: Any
email_pattern: Any
md5_pattern: Any
sha256_pattern: Any

class Normalize:
    @staticmethod
    def normalize_field(field: Any, data: Any): ...
    @staticmethod
    def validate_email(email: Any): ...
    @staticmethod
    def is_already_hashed(data: Any): ...
    @staticmethod
    def is_international_number(phone_number: Any): ...
    @staticmethod
    def is_valid_country_code(country_code: Any): ...
