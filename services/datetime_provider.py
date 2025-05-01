from datetime import datetime, timezone

class DatetimeProvider:
    def utc_now(self):
        """
        Returns the current UTC datetime.
        """
        return datetime.now(timezone.utc)