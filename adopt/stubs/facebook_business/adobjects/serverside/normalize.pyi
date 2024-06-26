from _typeshed import Incomplete

location_excluded_chars: Incomplete
isocode_included_chars: Incomplete
email_pattern: Incomplete
md5_pattern: Incomplete
sha256_pattern: Incomplete
year_pattern: Incomplete

class Normalize:
    @staticmethod
    def normalize_field(field, data): ...
    @staticmethod
    def normalize_field_skip_hashing(field, data): ...
    @staticmethod
    def normalize(field, data, hash_field): ...
    @staticmethod
    def validate_email(email): ...
    @staticmethod
    def is_already_hashed(data): ...
    @staticmethod
    def hash_sha_256(input): ...
    @staticmethod
    def get_international_number(phone_number): ...
    @staticmethod
    def is_valid_country_code(country_code): ...
