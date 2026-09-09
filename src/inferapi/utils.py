from datetime import UTC, datetime
from pathlib import Path


def file_creation_time(path: Path) -> datetime:
    """When the file was produced, as a timezone-aware datetime.

    st_birthtime is the real creation time and exists on macOS and recent Linux;
    elsewhere st_ctime is the closest thing the platform offers.
    """
    if not path.is_file():
        raise FileNotFoundError(f"{path} is not a file")

    stat = path.stat()
    timestamp = getattr(stat, "st_birthtime", stat.st_ctime)

    return datetime.fromtimestamp(timestamp, tz=UTC)
