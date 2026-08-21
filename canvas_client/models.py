import re
from typing import List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from pathlib import Path


@dataclass
class CanvasCourse:
    id: int
    name: str


@dataclass
class CanvasFolder:
    id: int
    parent_folder_id: Optional[int]
    name: str
    full_name: str
    is_root: bool


@dataclass
class CanvasFile:
    id: int
    folder_id: Optional[int]
    display_name: str
    module_name: Optional[str]
    size: Optional[int]
    url: Optional[str]
    locked: bool = False
    hidden: bool = False
    module_id: Optional[int] = None
    page_name: Optional[str] = None
    page_id: Optional[int] = None
    source: str = "none"
    course_id: Optional[int] = None

    @property
    def extension(self) -> str:
        if "." in self.display_name:
            return "." + self.display_name.split(".")[-1].lower()
        return ""


class CourseTree:
    def __init__(self, course: CanvasCourse):
        self.course = course
        self.files: dict[int, CanvasFile] = {}
        self.folders: dict[int, CanvasFolder] = {}
        self.root_folder_id: Optional[int] = None
        self.subfolders_map: dict[int, list[int]] = defaultdict(list)
        self.folder_files_map: dict[int, list[CanvasFile]] = defaultdict(list)

    def add_folder(self, folder: CanvasFolder) -> None:
        self.folders[folder.id] = folder
        if folder.is_root:
            self.root_folder_id = folder.id

    def add_file(self, file: CanvasFile) -> None:
        self.files[file.id] = file

    def build_hierarchy(self) -> None:
        self.subfolders_map.clear()
        self.folder_files_map.clear()

        for folder in self.folders.values():
            if folder.parent_folder_id is not None:
                self.subfolders_map[folder.parent_folder_id].append(folder.id)

        for file in self.files.values():
            if file.folder_id is not None:
                self.folder_files_map[file.folder_id].append(file)

    def get_all_files(self) -> list[CanvasFile]:
        return list(self.files.values())

    def get_files_by_extension(self, ext: str) -> list[CanvasFile]:
        ext = ext.lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        return [f for f in self.files.values() if f.extension == ext]

    def get_file_download_path(self, file_id: int, base_dir: Path) -> Path:
        file = self.files.get(file_id)
        if not file:
            return base_dir / "unknown"

        def clean_name(name: str) -> str:
            return re.sub(r'[\\/*?:"<>|]', "", name).strip()

        course_folder = clean_name(self.course.name)
        file_name = clean_name(file.display_name)

        if file.page_name and file.page_id is not None:
            d = clean_name(file.page_name)
            return base_dir / course_folder / f"{d} ({file.page_id})" / file_name

        if file.module_name and file.module_id:
            d = clean_name(file.module_name)
            return base_dir / course_folder / f"{d} ({file.module_id})" / file_name

        if file.module_name:
            return base_dir / course_folder / clean_name(file.module_name) / file_name

        if file.folder_id and self.folders:
            path_parts = []
            current_folder_id = file.folder_id
            while current_folder_id:
                folder = self.folders.get(current_folder_id)
                if not folder:
                    break
                d = clean_name(folder.name)
                path_parts.insert(0, f"{d} ({folder.id})")
                current_folder_id = folder.parent_folder_id
            if path_parts:
                return base_dir / course_folder / Path(*path_parts) / file_name

        return base_dir / course_folder / file_name

    def find_file_by_name(self, name: str) -> list[CanvasFile]:
        query = name.lower()
        return [f for f in self.files.values() if query in f.display_name.lower()]

    def find_file_by_path(self, path_str: str) -> Optional[CanvasFile]:
        query = path_str.lower().strip()
        for f in self.files.values():
            if f.display_name.lower() == query:
                return f
        return None
