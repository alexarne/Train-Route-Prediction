"""
Utility functions for data collection.
"""

from pathlib import Path
from datetime import datetime, timezone

LOGGING = True
PRINTING = True
loglocation = "./data/log.txt"

def log(message):
    """
    Log and/or print the message based on the current config.
    """
    if LOGGING:
        file = Path(loglocation)
        file.parent.mkdir(parents=True, exist_ok=True)
        with open(loglocation, "a") as f:
            time = getTimestamp()
            f.write(f"[{time}]: {message}\n")
    if PRINTING:
        print(message)

def getTimestamp() -> str:
    """
    Get the current time as a string of ISO 8601 format.
    """
    now = datetime.now(timezone.utc).astimezone()
    formatted = now.isoformat(timespec="milliseconds")
    return formatted