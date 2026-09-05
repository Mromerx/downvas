import time
import requests
from typing import Any, Optional

from django.utils.translation import gettext as _

from .models import (
    CanvasCourse, CanvasFolder, CanvasFile, CourseTree
)
from .exceptions import (
    CanvasAPIError, CanvasAuthError, RateLimitError,
    CourseNotFoundError, CanvasConnectionError
)
from .html_parser import extract_file_links_from_html, _is_http_forbidden


class CanvasAPIClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "User-Agent": "DownVas/1.0 (Canvas Downloader)",
        })

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        try:
            response = self.session.request(method, url, **kwargs)
            remaining = response.headers.get("X-Rate-Limit-Remaining")
            if remaining:
                try:
                    if float(remaining) < 10.0:
                        time.sleep(2.0)
                except ValueError:
                    pass

            if response.status_code == 200:
                return response
            elif response.status_code == 401:
                raise CanvasAuthError(_("Token de acceso invalido o expirado."), status_code=401)
            elif response.status_code == 404:
                raise CourseNotFoundError(_("El curso no fue encontrado."), status_code=404)
            elif response.status_code in (403, 429):
                err_msg = response.text.lower()
                if "rate limit" in err_msg or response.status_code == 429:
                    time.sleep(5.0)
                    response = self.session.request(method, url, **kwargs)
                    if response.status_code == 200:
                        return response
                    raise RateLimitError(_("Limite de solicitudes alcanzado."), status_code=response.status_code)
                raise CanvasAPIError(
                    _("Acceso denegado ({status_code}): {body}").format(
                        status_code=response.status_code, body=response.text
                    ),
                    status_code=response.status_code,
                )
            else:
                raise CanvasAPIError(
                    _("Error HTTP {status_code}").format(status_code=response.status_code),
                    status_code=response.status_code,
                )

        except requests.exceptions.ConnectionError as e:
            raise CanvasConnectionError(_("No se pudo establecer conexion: {error}").format(error=e))
        except requests.RequestException as e:
            if isinstance(e, CanvasAPIError):
                raise
            raise CanvasAPIError(_("Error de red inesperado: {error}").format(error=e))

    def verify_authentication(self) -> None:
        self._request("GET", f"{self.base_url}/api/v1/users/self")

    def get_course(self, course_id: int) -> dict[str, Any]:
        resp = self._request("GET", f"{self.base_url}/api/v1/courses/{course_id}")
        return resp.json()

    def get_modules(self, course_id: int) -> list[dict[str, Any]]:
        url = f"{self.base_url}/api/v1/courses/{course_id}/modules"
        modules = []
        while url:
            r = self.session.get(url, params=[("include[]", "items"), ("include[]", "content_details")])
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list):
                modules.extend(data)
            url = self._get_next_link(r)
        return modules

    def get_folders(self, course_id: int) -> list[dict[str, Any]]:
        url = f"{self.base_url}/api/v1/courses/{course_id}/folders"
        folders = []
        while url:
            r = self._request("GET", url)
            data = r.json()
            if isinstance(data, list):
                folders.extend(data)
            url = self._get_next_link(r)
        return folders

    def get_files(self, course_id: int) -> list[dict[str, Any]]:
        url = f"{self.base_url}/api/v1/courses/{course_id}/files"
        files = []
        while url:
            r = self._request("GET", url)
            data = r.json()
            if isinstance(data, list):
                files.extend(data)
            url = self._get_next_link(r)
        return files

    def get_pages(self, course_id: int) -> list[dict[str, Any]]:
        url = f"{self.base_url}/api/v1/courses/{course_id}/pages"
        pages = []
        try:
            while url:
                r = self._request("GET", url, params=[("include[]", "body"), ("per_page", "100")])
                data = r.json()
                if isinstance(data, list):
                    pages.extend(data)
                url = self._get_next_link(r)
        except CourseNotFoundError:
            return []
        return pages

    def get_file_metadata(self, course_id: int, file_id: int) -> Optional[dict[str, Any]]:
        for url_fmt in (
            f"{self.base_url}/api/v1/courses/{course_id}/files/{file_id}",
            f"{self.base_url}/api/v1/files/{file_id}",
        ):
            try:
                r = self._request("GET", url_fmt)
                return r.json()
            except (CanvasAPIError, requests.HTTPError):
                continue
        return None

    def _paginated(self, url: str, params: list[tuple[str, str]] | None = None) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        first = True
        while url:
            kwargs = {}
            if params and first:
                kwargs["params"] = params
            first = False
            r = self._request("GET", url, **kwargs)
            data = r.json()
            if isinstance(data, list):
                items.extend(data)
            url = self._get_next_link(r)
        return items

    def _extract_rich_content_files(self, tree: CourseTree, course_id: int) -> None:
        sources: list[tuple[str, str, int]] = []

        try:
            for page in self.get_pages(course_id):
                body = page.get("body") or ""
                if body:
                    sources.append((page.get("title") or "Pagina", body, page.get("page_id") or 0))
        except (CanvasAPIError, requests.HTTPError) as e:
            if not _is_http_forbidden(e):
                raise

        try:
            for a in self._paginated(
                f"{self.base_url}/api/v1/courses/{course_id}/assignments",
                [("per_page", "100")],
            ):
                desc = a.get("description") or ""
                if desc:
                    sources.append((a.get("name") or "Tarea", desc, a.get("id") or 0))
        except (CanvasAPIError, requests.HTTPError) as e:
            if not _is_http_forbidden(e):
                raise

        for only_ann in (None, "true"):
            try:
                qp = [("per_page", "100")]
                if only_ann:
                    qp.append(("only_announcements", "true"))
                for d in self._paginated(
                    f"{self.base_url}/api/v1/courses/{course_id}/discussion_topics",
                    qp,
                ):
                    msg = d.get("message") or ""
                    if msg:
                        sources.append((d.get("title") or "Discusion", msg, d.get("id") or 0))
            except (CanvasAPIError, requests.HTTPError) as e:
                if not _is_http_forbidden(e):
                    raise

        try:
            r = self._request(
                "GET",
                f"{self.base_url}/api/v1/courses/{course_id}",
                params=[("include[]", "syllabus_body")],
            )
            sb = r.json().get("syllabus_body") or ""
            if sb:
                sources.append(("Silabo", sb, -1))
        except (CanvasAPIError, requests.HTTPError) as e:
            if not _is_http_forbidden(e):
                raise

        for label, html, pid in sources:
            self._add_files_from_html(tree, course_id, label, html, pid)

    def ensure_file_in_tree(self, tree: CourseTree, course_id: int, file_id: int) -> bool:
        if file_id in tree.files:
            return True
        meta = self.get_file_metadata(course_id, file_id)
        if not meta:
            return False
        tree.add_file(CanvasFile(
            id=file_id,
            folder_id=meta.get("folder_id"),
            display_name=(meta.get("display_name") or meta.get("filename") or "archivo"),
            module_name=None,
            size=meta.get("size"),
            url=meta.get("url"),
            locked=meta.get("locked_for_user", False),
            hidden=meta.get("hidden_for_user", False),
            source="none",
            course_id=course_id,
        ))
        tree.build_hierarchy()
        return True

    def _add_files_from_html(
        self,
        tree: CourseTree,
        course_id: int,
        label: str,
        html: str,
        pid: int,
        module_name: str | None = None,
        module_id: int | None = None,
    ) -> None:
        for fid, anchor_name in extract_file_links_from_html(html, course_id):
            if fid in tree.files:
                continue
            meta = self.get_file_metadata(course_id, fid)
            if meta:
                tree.add_file(CanvasFile(
                    id=fid,
                    folder_id=meta.get("folder_id"),
                    display_name=(meta.get("display_name") or meta.get("filename") or anchor_name or "archivo"),
                    module_name=module_name,
                    module_id=module_id,
                    size=meta.get("size"),
                    url=meta.get("url"),
                    locked=meta.get("locked_for_user", False),
                    hidden=meta.get("hidden_for_user", False),
                    page_name=label,
                    page_id=pid,
                    source="page",
                    course_id=course_id,
                ))
            else:
                tree.add_file(CanvasFile(
                    id=fid,
                    folder_id=None,
                    display_name=anchor_name or "archivo",
                    module_name=module_name,
                    module_id=module_id,
                    size=None,
                    url=None,
                    page_name=label,
                    page_id=pid,
                    source="page",
                    course_id=course_id,
                ))

    def get_module_item(self, course_id: int, item_id: int) -> dict[str, Any]:
        r = self._request(
            "GET",
            f"{self.base_url}/api/v1/courses/{course_id}/modules/items/{item_id}",
        )
        data = r.json()
        if not isinstance(data, dict):
            return {}

        modules_by_id: dict[str, str] = {}
        for m in data.get("modules") or []:
            if isinstance(m, dict):
                mid = str(m.get("id"))
                if mid and not modules_by_id.get(mid):
                    modules_by_id[mid] = m.get("name") or ""

        item: dict[str, Any] = data
        if isinstance(data.get("items"), list):
            for wrapper in data["items"]:
                if isinstance(wrapper, dict) and isinstance(wrapper.get("current"), dict):
                    item = wrapper["current"]
                    break
            else:
                item = data["items"][0] if data["items"] and isinstance(data["items"][0], dict) else data
        elif isinstance(data.get("current"), dict):
            item = data["current"]

        mid = str(item.get("module_id") or "")
        if mid and not item.get("module_name") and modules_by_id.get(mid):
            item["module_name"] = modules_by_id[mid]
        return item

    def get_page(self, course_id: int, page_ref: str) -> dict[str, Any]:
        ref = str(page_ref).strip("/")
        url = f"{self.base_url}/api/v1/courses/{course_id}/pages/{requests.utils.quote(ref, safe='-._~')}"
        r = self._request("GET", url, params=[("include[]", "body")])
        return r.json()

    def get_assignment(self, course_id: int, assignment_id: int) -> dict[str, Any]:
        r = self._request("GET", f"{self.base_url}/api/v1/courses/{course_id}/assignments/{assignment_id}")
        return r.json()

    def get_discussion_topic(self, course_id: int, topic_id: int) -> dict[str, Any]:
        r = self._request("GET", f"{self.base_url}/api/v1/courses/{course_id}/discussion_topics/{topic_id}")
        return r.json()

    def get_quiz(self, course_id: int, quiz_id: int) -> dict[str, Any]:
        r = self._request("GET", f"{self.base_url}/api/v1/courses/{course_id}/quizzes/{quiz_id}")
        return r.json()

    def resolve_page_item(
        self,
        tree: CourseTree,
        course_id: int,
        item: dict[str, Any],
        module_name: str | None = None,
        module_id: int | None = None,
    ) -> None:
        page_ref = item.get("page_url") or item.get("content_id")
        if not page_ref:
            return
        try:
            page = self.get_page(course_id, str(page_ref))
        except (CanvasAPIError, requests.HTTPError):
            return
        body = (page or {}).get("body") or ""
        if not body:
            return
        pid = (page.get("page_id") or item.get("content_id") or 0)
        label = item.get("title") or page.get("title") or "Pagina"
        self._add_files_from_html(tree, course_id, label, body, pid, module_name, module_id)

    def _resolve_content_item(
        self,
        tree: CourseTree,
        course_id: int,
        item: dict[str, Any],
        item_type: str,
        module_name: str | None = None,
    ) -> None:
        content_id = item.get("content_id")
        if not content_id:
            return
        label = item.get("title") or "Contenido"
        pid = content_id
        module_id = item.get("module_id")
        try:
            if item_type == "Assignment":
                obj = self.get_assignment(course_id, content_id)
                html = (obj or {}).get("description") or ""
                attachments = (obj or {}).get("attachments") or []
            elif item_type == "Discussion":
                obj = self.get_discussion_topic(course_id, content_id)
                html = (obj or {}).get("message") or ""
                attachments = (obj or {}).get("attachments") or []
            else:
                obj = self.get_quiz(course_id, content_id)
                html = (obj or {}).get("description") or ""
                attachments = []
        except (CanvasAPIError, requests.HTTPError):
            return

        if html:
            self._add_files_from_html(tree, course_id, label, html, pid, module_name, module_id)
        for att in attachments:
            fid = att.get("id") if isinstance(att, dict) else None
            if not fid or fid in tree.files:
                continue
            tree.add_file(CanvasFile(
                id=fid,
                folder_id=att.get("folder_id"),
                display_name=(att.get("display_name") or att.get("filename") or "archivo"),
                module_name=module_name,
                module_id=module_id,
                size=att.get("size"),
                url=att.get("url"),
                locked=att.get("locked_for_user", False),
                hidden=att.get("hidden_for_user", False),
                page_name=label,
                page_id=pid,
                source="page",
                course_id=course_id,
            ))

    def add_module_item_to_tree(self, tree: CourseTree, course_id: int, item_id: int) -> bool:
        item = self.get_module_item(course_id, item_id)
        if not item:
            return False

        item_type = item.get("type", "")
        module_id = item.get("module_id")
        module_name = item.get("module_name")
        if module_id and not module_name:
            module_name = f"Modulo {module_id}"
        if not module_name and module_id:
            try:
                for m in self.get_modules(course_id):
                    if str(m.get("id")) == str(module_id):
                        module_name = m.get("name")
                        break
            except (CanvasAPIError, requests.HTTPError):
                pass

        if item_type == "File":
            fid = item.get("content_id")
            if not fid:
                return False
            if self.ensure_file_in_tree(tree, course_id, fid):
                return True
            content = item.get("content_details", {})
            tree.add_file(CanvasFile(
                id=fid,
                folder_id=None,
                display_name=(content.get("display_name") or item.get("title") or "archivo"),
                module_name=module_name,
                module_id=module_id,
                size=content.get("size") or item.get("size"),
                url=content.get("url"),
                locked=content.get("locked_for_user", False),
                hidden=content.get("hidden_for_user", False),
                source="module",
                course_id=course_id,
            ))
            tree.build_hierarchy()
            return True

        if item_type == "Page":
            self.resolve_page_item(tree, course_id, item, module_name, module_id)
            return True

        if item_type in ("Assignment", "Discussion", "Quiz"):
            self._resolve_content_item(tree, course_id, item, item_type, module_name)
            return True

        return False

    def _get_next_link(self, response: requests.Response) -> str | None:
        link = response.headers.get("Link", "")
        for part in link.split(","):
            if 'rel="next"' in part:
                return part.split(";")[0].strip().strip("<>")
        return None

    def fetch_course_tree(self, course_id: int) -> CourseTree:
        try:
            cdata = self.get_course(course_id)
            course = CanvasCourse(id=course_id, name=cdata.get("name") or f"Curso {course_id}")
        except (CanvasAPIError, requests.HTTPError):
            course = CanvasCourse(id=course_id, name=f"Curso_{course_id}")

        tree = CourseTree(course)

        try:
            for module in self.get_modules(course_id):
                mname = module.get("name", f"Modulo {module.get('id')}")
                mid = module.get("id")
                for item in module.get("items", []):
                    if item.get("type") == "File":
                        content = item.get("content_details", {})
                        fid = item.get("content_id")
                        if not fid:
                            continue
                        tree.add_file(CanvasFile(
                            id=fid,
                            folder_id=None,
                            display_name=(content.get("display_name") or item.get("title") or "archivo"),
                            module_name=mname,
                            module_id=mid,
                            size=content.get("size"),
                            url=content.get("url"),
                            locked=content.get("locked_for_user", False),
                            hidden=content.get("hidden_for_user", False),
                            source="module",
                            course_id=course_id,
                        ))
                    elif item.get("type") == "Page":
                        self.resolve_page_item(tree, course_id, item, mname, mid)
        except (CanvasAPIError, requests.HTTPError) as e:
            if not _is_http_forbidden(e):
                raise

        try:
            for f in self.get_folders(course_id):
                tree.add_folder(CanvasFolder(
                    id=f["id"],
                    parent_folder_id=f.get("parent_folder_id"),
                    name=f["name"],
                    full_name=f["full_name"],
                    is_root=(f.get("parent_folder_id") is None)
                ))
        except (CanvasAPIError, requests.HTTPError) as e:
            if not _is_http_forbidden(e):
                raise

        try:
            for f in self.get_files(course_id):
                fid = f.get("id")
                if not fid:
                    continue
                folder_id = f.get("folder_id")
                api_name = (f.get("display_name") or f.get("filename") or "").strip()
                existing = tree.files.get(fid)
                if existing:
                    if existing.folder_id is None and folder_id is not None:
                        existing.folder_id = folder_id
                    if not existing.size and f.get("size"):
                        existing.size = f.get("size")
                    if existing.source == "none":
                        existing.source = "folder"
                    if api_name:
                        existing.display_name = api_name
                    if not existing.url and f.get("url"):
                        existing.url = f.get("url")
                else:
                    tree.add_file(CanvasFile(
                        id=fid,
                        folder_id=folder_id,
                        display_name=api_name or "archivo",
                        module_name=None,
                        size=f.get("size"),
                        url=f.get("url"),
                        locked=f.get("locked_for_user", False),
                        hidden=f.get("hidden_for_user", False),
                        source="folder",
                        course_id=course_id,
                    ))
        except (CanvasAPIError, requests.HTTPError) as e:
            if not _is_http_forbidden(e):
                raise

        try:
            self._extract_rich_content_files(tree, course_id)
        except (CanvasAPIError, requests.HTTPError) as e:
            if not _is_http_forbidden(e):
                raise

        tree.build_hierarchy()
        return tree
