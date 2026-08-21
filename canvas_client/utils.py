import re
from urllib.parse import urlparse


def human_readable_size(size_in_bytes: int) -> str:
    if size_in_bytes is None:
        return "0 B"
    size = float(size_in_bytes)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def extract_course_id(input_str: str) -> int | None:
    cleaned = input_str.strip()
    if cleaned.isdigit():
        return int(cleaned)
    match = re.search(r"/courses/(\d+)", cleaned)
    if match:
        return int(match.group(1))
    return None


def extract_file_id(input_str: str) -> int | None:
    cleaned = input_str.strip()
    if not cleaned:
        return None
    match = re.search(r"(?:/courses/\d+/)?(?:/api/v1/)?files?/(\d+)", cleaned)
    if match:
        return int(match.group(1))
    return None


def extract_module_item_id(input_str: str) -> int | None:
    cleaned = input_str.strip()
    if not cleaned:
        return None
    match = re.search(r"(?:/courses/\d+/)?modules/items/(\d+)", cleaned)
    if match:
        return int(match.group(1))
    return None


def extract_domain(url: str) -> str | None:
    try:
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"
    except Exception:
        pass
    return None
