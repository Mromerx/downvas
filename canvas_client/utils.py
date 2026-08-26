import re


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
