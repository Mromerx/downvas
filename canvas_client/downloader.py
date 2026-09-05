import os
import re
import shutil
import tempfile
import threading
import time
import uuid
import zipfile
from collections import defaultdict
from typing import Callable, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from django.utils.translation import gettext as _

from .exceptions import CanvasAPIError


@dataclass
class DownloadJob:
    url: str
    expected_size: Optional[int]
    display_name: str
    file_id: int
    course_id: Optional[int] = None


class FileDownloader:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "User-Agent": "DownVas/1.0 (Canvas Downloader)",
        })

    def _download_urls(self, job: DownloadJob) -> List[str]:
        candidates: List[str] = []

        if job.url:
            url = job.url if job.url.startswith("http") else f"{self.base_url}{job.url}"
            if url not in candidates:
                candidates.append(url)

        if job.course_id:
            candidates.append(f"{self.base_url}/api/v1/courses/{job.course_id}/files/{job.file_id}/download")

        candidates.append(f"{self.base_url}/api/v1/files/{job.file_id}/download")
        return candidates

    @staticmethod
    def _name_from_content_disposition(header: str) -> Optional[str]:
        if not header:
            return None
        match = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', header, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            try:
                return requests.utils.unquote(name)
            except Exception:
                return name
        return None

    def _signed_url(self, job: DownloadJob) -> Optional[str]:
        if not job.course_id:
            return None
        for path in (
            f"{self.base_url}/api/v1/courses/{job.course_id}/files/{job.file_id}",
            f"{self.base_url}/api/v1/files/{job.file_id}",
        ):
            try:
                r = self.session.get(path, timeout=30)
                r.raise_for_status()
                url = r.json().get("url")
                if isinstance(url, str) and url.startswith("http"):
                    return url
            except (requests.RequestException, ValueError):
                continue
        return None

    def _stream_to_file(
        self, url: str, dest: Path, job: DownloadJob,
        on_progress: Optional[Callable[[int, Optional[int]], None]] = None,
    ) -> Tuple[int, str]:
        final_name = job.display_name
        total = 0
        expected = job.expected_size or 0
        last_report = [0.0]

        def _report(final: bool = False) -> None:
            if not on_progress:
                return
            now = time.monotonic()
            if not final and now - last_report[0] < 0.2:
                return
            last_report[0] = now
            on_progress(total, expected)

        with self.session.get(url, stream=True, allow_redirects=True, timeout=30) as r:
            r.raise_for_status()

            content_type = r.headers.get("Content-Type", "")
            if "application/json" in content_type and not job.display_name.lower().endswith(".json"):
                raise CanvasAPIError(_("La descarga devolvio JSON inesperado en lugar de binario."))

            cd_name = self._name_from_content_disposition(r.headers.get("Content-Disposition", ""))
            if cd_name and Path(cd_name).suffix:
                final_name = cd_name

            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total += len(chunk)
                        _report()
            _report(final=True)
        return total, final_name

    def download_file(
        self, job: DownloadJob, temp_dir: Path,
        on_progress: Optional[Callable[[int, Optional[int]], None]] = None,
    ) -> Tuple[Path, str]:
        """Download a file to temp_dir. Returns (path, final_filename)."""
        ext = Path(job.display_name).suffix or ""
        part_file = _temp_path(temp_dir, ext)

        try:
            last_error: Optional[Exception] = None
            candidates = self._download_urls(job)

            for download_url in candidates:
                try:
                    _, final_name = self._stream_to_file(download_url, part_file, job, on_progress)
                    final_path = temp_dir / final_name
                    if final_path != part_file:
                        part_file.rename(final_path)
                    return final_path, final_name
                except (requests.HTTPError, CanvasAPIError) as e:
                    last_error = e
                    if part_file.exists():
                        try:
                            part_file.unlink()
                        except OSError:
                            pass
                    continue

            signed = self._signed_url(job)
            if signed and signed not in candidates:
                try:
                    part_file = _temp_path(temp_dir, ext)
                    _, final_name = self._stream_to_file(signed, part_file, job, on_progress)
                    final_path = temp_dir / final_name
                    if final_path != part_file:
                        part_file.rename(final_path)
                    return final_path, final_name
                except (requests.HTTPError, CanvasAPIError) as e:
                    last_error = e
                    if part_file.exists():
                        try:
                            part_file.unlink()
                        except OSError:
                            pass

            raise last_error if last_error else CanvasAPIError(_("Todas las URLs de descarga fallaron."))

        except Exception:
            if part_file.exists():
                try:
                    part_file.unlink()
                except OSError:
                    pass
            raise


def _temp_path(temp_dir: Path, ext: str) -> Path:
    return temp_dir / f"{uuid.uuid4().hex}{ext}"


def download_files_to_temp(
    base_url: str,
    token: str,
    jobs: List[DownloadJob],
    emit: Optional[Callable[[dict], None]] = None,
) -> Tuple[List[Tuple[Path, str]], Path]:
    """Download multiple files in parallel to a temp directory. Returns list of (path, name)."""
    downloader = FileDownloader(base_url, token)
    temp_dir = Path(tempfile.mkdtemp(prefix="downvas_"))
    results: List[Tuple[Path, str]] = []

    if emit:
        emit({"type": "phase", "phase": "download", "total_files": len(jobs)})

    throttle = defaultdict(float)
    throttle_lock = threading.Lock()

    def _report(index: int, name: str, got: int, expected: Optional[int]) -> None:
        if not emit:
            return
        now = time.monotonic()
        with throttle_lock:
            last = throttle.get(index, 0.0)
            if now - last < 0.2:
                return
            throttle[index] = now
        evt = {"type": "download", "index": index, "total": len(jobs), "file": name}
        if expected and expected > 0:
            evt["percent"] = round(min(got / expected * 100.0, 100.0), 1)
        emit(evt)

    def _download(job: DownloadJob, index: int):
        return downloader.download_file(
            job, temp_dir,
            on_progress=lambda got, expected: _report(index, job.display_name, got, expected),
        )

    try:
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {pool.submit(_download, j, i): (j, i) for i, j in enumerate(jobs)}
            for future in as_completed(futures):
                _, index = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    if emit:
                        emit({"type": "file_done", "index": index, "file": result[1]})
                except Exception:
                    pass
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise

    return results, temp_dir


def create_zip(
    file_paths: List[Path],
    zip_name: str,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
    directory: Optional[Path] = None,
) -> Path:
    """Create a zip file from a list of file paths. Returns the zip path."""
    fd, tmp_path = tempfile.mkstemp(
        suffix=".zip", prefix="downvas_",
        dir=str(directory) if directory else None,
    )
    os.close(fd)
    zip_path = Path(tmp_path)
    seen: defaultdict = defaultdict(int)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for index, fp in enumerate(file_paths):
            name = fp.name
            if fp.exists():
                zf.write(fp, _unique_arcname(name, seen))
            if on_progress:
                on_progress(index, len(file_paths), name)
    return zip_path


def _unique_arcname(name: str, seen: dict) -> str:
    count = seen.get(name, 0)
    seen[name] = count + 1
    if count == 0:
        return name
    stem, dot, suffix = name.rpartition(".")
    if dot:
        return f"{stem} ({count}){dot}{suffix}"
    return f"{name} ({count})"
