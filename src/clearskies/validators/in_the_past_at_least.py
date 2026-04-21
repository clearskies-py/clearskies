from __future__ import annotations

import datetime

from clearskies.validators.timedelta import Timedelta


class InThePastAtLeast(Timedelta):
    """Validates that a date column value is at least a given timedelta in the past."""

    def check_timedelta(self, as_date: datetime.datetime, column_name: str) -> str:
        if as_date > self.utcnow - self.timedelta:
            return f"'{column_name}' must be at least {self.delta_human_friendly()} in the past."
        return ""
