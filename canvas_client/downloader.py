import re
import tempfile
import zipfile
from typing import List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

import requests

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

    def _stream_to_file(self, url: str, dest: Path, job: DownloadJob) -> Tuple[int, str]:
        final_name = job.display_name
        total = 0
        with self.session.get(url, stream=True, allow_redirects=True, timeout=30) as r:
            r.raise_for_status()

            content_type = r.headers.get("Content-Type", "")
            if "application/json" in content_type and not job.display_name.lower().endswith(".json"):
                raise CanvasAPIError("La descarga devolvio JSON inesperado en lugar de binario.")

            cd_name = self._name_from_content_disposition(r.headers.get("Content-Disposition", ""))
            if cd_name and Path(cd_name).suffix:
                final_name = cd_name

            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total += len(chunk)
        return total, final_name

    def download_file(self, job: DownloadJob, temp_dir: Path) -> Tuple[Path, str]:
        """Download a file to temp_dir. Returns (path, final_filename)."""
        ext = Path(job.display_name).suffix or ""
        part_file = Path(tempfile.mktemp(suffix=ext, dir=str(temp_dir)))

        try:
            last_error: Optional[Exception] = None
            candidates = self._download_urls(job)

            for download_url in candidates:
                try:
                    bytes_dl, final_name = self._stream_to_file(download_url, part_file, job)
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
                    part_file = Path(tempfile.mktemp(suffix=ext, dir=str(temp_dir)))
                    bytes_dl, final_name = self._stream_to_file(signed, part_file, job)
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

            raise last_error if last_error else CanvasAPIError("Todas las URLs de descarga fallaron.")

        except Exception:
            if part_file.exists():
                try:
                    part_file.unlink()
                except OSError:
                    pass
            raise


def download_files_to_temp(
    base_url: str, token: str, jobs: List[DownloadJob]
) -> List[Tuple[Path, str]]:
    """Download multiple files in parallel to a temp directory. Returns list of (path, name)."""
    downloader = FileDownloader(base_url, token)
    temp_dir = Path(tempfile.mkdtemp(prefix="downvas_"))
    results: List[Tuple[Path, str]] = []

    def _download(job):
        return downloader.download_file(job, temp_dir)

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(_download, j): j for j in jobs}
        for future in futures:
            try:
                result = future.result()
                results.append(result)
            except Exception:
                pass

    return results, temp_dir


def create_zip(file_paths: List[Path], zip_name: str) -> Path:
    """Create a zip file from a list of file paths. Returns the zip path."""
    zip_path = Path(tempfile.mktemp(suffix=".zip", prefix="downvas_"))
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fp in file_paths:
            if fp.exists():
                zf.write(fp, fp.name)
    return zip_path
