from typing import Optional
from dataclasses import dataclass
from collections import defaultdict


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
