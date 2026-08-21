import re
from html import unescape
from typing import List, Optional, Tuple

from .exceptions import CanvasAPIError


def _is_http_forbidden(e: Exception) -> bool:
    if isinstance(e, CanvasAPIError):
        return e.status_code in (401, 403, 404)
    import requests as _req
    if isinstance(e, _req.HTTPError):
        resp = getattr(e, "response", None)
        if resp is not None:
            return resp.status_code in (401, 403, 404)
    return False


def extract_file_links_from_html(html: str, course_id: int) -> List[Tuple[int, Optional[str]]]:
    results: List[Tuple[int, Optional[str]]] = []
    seen: set = set()

    id_patterns = [
        re.compile(rf"/courses/{course_id}/files/(\d+)", re.IGNORECASE),
        re.compile(rf"/api/v1/courses/{course_id}/files/(\d+)", re.IGNORECASE),
        re.compile(r"/api/v1/files/(\d+)", re.IGNORECASE),
        re.compile(r"(?<!\d)/files/(\d+)", re.IGNORECASE),
    ]

    def push(fid: int, name: Optional[str]) -> None:
        if fid and fid not in seen:
            seen.add(fid)
            results.append((fid, name))

    def ids_in(text: str, name: Optional[str]) -> None:
        for pat in id_patterns:
            for m in pat.finditer(text):
                push(int(m.group(1)), name)

    attr_re = re.compile(
        r'([\w:-]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s"\'=<>`]+))',
        re.IGNORECASE,
    )

    for m in re.finditer(r"<a\b[^>]*>(.*?)</a>", html, re.IGNORECASE | re.DOTALL):
        attrs: dict[str, str] = {}
        for am in attr_re.finditer(m.group(0)):
            key = am.group(1).lower()
            value = am.group(2) or am.group(3) or am.group(4) or ""
            if key not in attrs:
                attrs[key] = value
        href = attrs.get("href", "")
        title = attrs.get("title")
        inner = re.sub(r"<[^>]+>", "", m.group(1))
        inner = unescape(inner).strip()
        name = (title or inner or None) if (title or inner) else None
        if href:
            ids_in(href, name)

    ids_in(html, None)

    return results


def extract_file_ids_from_html(html: str, course_id: int) -> list[int]:
    return [fid for fid, _ in extract_file_links_from_html(html, course_id)]
