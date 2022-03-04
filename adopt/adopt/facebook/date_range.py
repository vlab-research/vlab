from dataclasses import dataclass
from datetime import datetime

epoch = datetime.utcfromtimestamp(0)


def unix_time_millis(dt):
    return int((dt - epoch).total_seconds() * 1000.0)


@dataclass
class DateRange:
    start_date: datetime
    until_date: datetime

    @property
    def start(self):
        return self.start_date.strftime("%Y-%m-%d")

    @property
    def until(self):
        return self.until_date.strftime("%Y-%m-%d")

    @property
    def start_unix(self):
        return unix_time_millis(self.start_date)

    @property
    def until_unix(self):
        return unix_time_millis(self.until_date)
