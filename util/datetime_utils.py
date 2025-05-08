from datetime import datetime


def parse_datetime(date_str):
    """Converts ISO datetime string to datetime object with timezone"""
    if not date_str:
        return None
    return datetime.fromisoformat(date_str.replace("Z", "+00:00"))

def format_datetime(dt):
    """Formats datetime object to a readable string"""
    if not dt:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")