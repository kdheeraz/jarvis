from datetime import datetime, timezone

from langchain_core.tools import tool


@tool
def datetime_tool(query: str = "now") -> str:
    """Get the current date, time, or timezone information. Pass 'now' for current datetime."""
    now = datetime.now(timezone.utc)
    return (
        f"Current UTC datetime: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
        f"Date: {now.strftime('%A, %B %d, %Y')}\n"
        f"Time: {now.strftime('%I:%M %p %Z')}\n"
        f"Unix timestamp: {int(now.timestamp())}"
    )
