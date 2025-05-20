from datetime import datetime, timezone
from typing import Optional

def parse_datetime(date_str):
    """Converts ISO datetime string to datetime object with timezone"""
    if not date_str:
        return None
    return datetime.fromisoformat(date_str.replace("Z", "+00:00"))

def format_datetime(dt):
    """Formats datetime object to a readable string"""
    if not dt:
        return "Дата не вказана"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    local_dt = dt.astimezone()
    return local_dt.strftime("%Y-%m-%d %H:%M:%S")

def ensure_utc_aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)