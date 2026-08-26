import shutil
from collections import defaultdict
from wsgiref.util import FileWrapper

from django.contrib import messages
from django.http import StreamingHttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect

from canvas_client.api_client import CanvasAPIClient
from canvas_client.exceptions import (
    CanvasAPIError, CanvasAuthError, CourseNotFoundError, CanvasConnectionError
)
from canvas_client.utils import extract_course_id, human_readable_size
from canvas_client.downloader import DownloadJob, download_files_to_temp, create_zip
from canvas_client.models import CourseTree

from .forms import CanvasConfigForm, CourseInputForm


def _config_form_from_session(request, initial=None):
    data = {
        "canvas_url": request.session.get("canvas_url", ""),
        "api_token": request.session.get("api_token", ""),
        "locale": request.session.get("locale", "en"),
    }
    if initial:
        data.update(initial)
    form = CanvasConfigForm(initial=data)
    if request.session.get("api_token"):
        form.fields["api_token"].widget.attrs["placeholder"] = "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022 (saved)"
    return form


def index(request):
    course_form = CourseInputForm()

    return render(request, "core/index.html", {
        "course_form": course_form,
    })


def settings_view(request):
    if request.method == "POST":
        config_form = CanvasConfigForm(request.POST)
        if not config_form.is_valid():
            messages.error(request, "Please fill in all settings fields.")
            return redirect("settings")

        request.session["canvas_url"] = config_form.cleaned_data["canvas_url"].strip().rstrip("/")
        request.session["api_token"] = config_form.cleaned_data["api_token"].strip()
        request.session["locale"] = config_form.cleaned_data["locale"]

        messages.success(request, "Settings saved.")
        return redirect("settings")

    config_form = _config_form_from_session(request)
    return render(request, "core/settings.html", {
        "config_form": config_form,
    })


def clear_session(request):
    request.session.flush()
    return redirect("index")


def save_config(request):
    if request.method != "POST":
        return redirect("index")

    config_form = CanvasConfigForm(request.POST)
    if not config_form.is_valid():
        messages.error(request, "Please fill in all settings fields.")
        return redirect("index")

    request.session["canvas_url"] = config_form.cleaned_data["canvas_url"].strip().rstrip("/")
    request.session["api_token"] = config_form.cleaned_data["api_token"].strip()
    request.session["locale"] = config_form.cleaned_data["locale"]

    messages.success(request, "Settings saved.")
    return redirect("index")


def load_course(request):
    if request.method != "POST":
        return redirect("index")

    course_form = CourseInputForm(request.POST)

    if not course_form.is_valid():
        messages.error(request, "Enter a course ID.")
        return redirect("index")

    canvas_url = request.session.get("canvas_url")
    api_token = request.session.get("api_token")
    locale = request.session.get("locale", "en")
    course_input = course_form.cleaned_data["course_input"].strip()

    if not canvas_url or not api_token:
        messages.error(request, "Save your Canvas settings first.")
        return redirect("index")

    course_id = extract_course_id(course_input)
    if not course_id:
        messages.error(request, "Could not identify the course ID. Enter a numeric ID or a valid URL.")
        return redirect("index")

    request.session["locale"] = locale

    try:
        client = CanvasAPIClient(canvas_url, api_token)
        tree = client.fetch_course_tree(course_id)
    except CanvasAuthError:
        messages.error(request, "Invalid or expired access token.")
        return redirect("index")
    except CourseNotFoundError:
        messages.error(request, "Course not found. Check the ID or URL.")
        return redirect("index")
    except CanvasConnectionError:
        messages.error(request, "Could not connect to Canvas. Check the URL.")
        return redirect("index")
    except CanvasAPIError:
        messages.error(request, "Error communicating with Canvas. Try again.")
        return redirect("index")

    tree_data = _serialize_tree(tree)
    request.session["course_tree"] = tree_data
    request.session["course_id"] = course_id

    return redirect("course_tree")


def course_tree(request):
    tree_data = request.session.get("course_tree")
    if not tree_data:
        return redirect("index")

    tree = _deserialize_tree(tree_data)
    sections = _build_sections(tree)

    return render(request, "core/course_tree.html", {
        "course": tree.course,
        "sections": sections,
        "course_id": request.session.get("course_id"),
        "total_files": len(tree.files),
    })


def download_files(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST required")

    tree_data = request.session.get("course_tree")
    canvas_url = request.session.get("canvas_url")
    api_token = request.session.get("api_token")
    course_id = request.session.get("course_id")

    if not tree_data or not canvas_url or not api_token:
        return redirect("index")

    tree = _deserialize_tree(tree_data)

    file_ids = request.POST.getlist("file_ids")
    if not file_ids:
        return redirect("course_tree")

    jobs = []
    for fid_str in file_ids:
        try:
            fid = int(fid_str)
        except ValueError:
            continue
        file = tree.files.get(fid)
        if not file:
            continue
        jobs.append(DownloadJob(
            url=file.url or "",
            expected_size=file.size,
            display_name=file.display_name,
            file_id=file.id,
            course_id=course_id,
        ))

    if not jobs:
        return redirect("course_tree")

    temp_dir = None
    try:
        results, temp_dir = download_files_to_temp(canvas_url, api_token, jobs)
    except Exception:
        return HttpResponseBadRequest("Error downloading files. Try again.")

    if not results:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return HttpResponseBadRequest("Could not download any files.")

    try:
        if len(results) == 1:
            file_path, file_name = results[0]
            file_iter = FileWrapper(open(file_path, "rb"))
            response = StreamingHttpResponse(
                file_iter,
                content_type="application/octet-stream",
            )
            response["Content-Disposition"] = f'attachment; filename="{file_name}"'
        else:
            zip_path = create_zip([fp for fp, _ in results], "courses.zip")
            file_iter = FileWrapper(open(zip_path, "rb"))
            response = StreamingHttpResponse(
                file_iter,
                content_type="application/zip",
            )
            response["Content-Disposition"] = 'attachment; filename="courses.zip"'
    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return HttpResponseBadRequest("Error preparing download.")

    response._downvas_temp_dir = temp_dir
    return response


def _serialize_tree(tree: CourseTree) -> dict:
    return {
        "course": {"id": tree.course.id, "name": tree.course.name},
        "files": {
            str(k): {
                "id": v.id, "folder_id": v.folder_id,
                "display_name": v.display_name, "module_name": v.module_name,
                "size": v.size, "url": v.url, "locked": v.locked,
                "hidden": v.hidden, "module_id": v.module_id,
                "page_name": v.page_name, "page_id": v.page_id,
                "source": v.source, "course_id": v.course_id,
            } for k, v in tree.files.items()
        },
        "folders": {
            str(k): {
                "id": v.id, "parent_folder_id": v.parent_folder_id,
                "name": v.name, "full_name": v.full_name, "is_root": v.is_root,
            } for k, v in tree.folders.items()
        },
        "root_folder_id": tree.root_folder_id,
    }


def _deserialize_tree(data: dict) -> CourseTree:
    from canvas_client.models import CanvasCourse, CanvasFile, CanvasFolder

    course = CanvasCourse(**data["course"])
    tree = CourseTree(course)

    for k, v in data["files"].items():
        tree.files[int(k)] = CanvasFile(**v)

    for k, v in data["folders"].items():
        tree.folders[int(k)] = CanvasFolder(**v)

    tree.root_folder_id = data.get("root_folder_id")
    tree.build_hierarchy()
    return tree


def _build_sections(tree: CourseTree) -> list[dict]:
    sections = []
    rendered = set()
    all_files = list(tree.files.values())

    module_files = [f for f in all_files if f.source == "module"]
    if module_files:
        mdict = defaultdict(list)
        for f in module_files:
            mdict[f.module_name].append(f)
        for mname, fs in mdict.items():
            fs.sort(key=lambda x: x.display_name.lower())
            sections.append({
                "name": mname or "No module",
                "type": "module",
                "files": [_file_dict(f) for f in fs],
            })
            rendered.update(f.id for f in fs)

    page_files = [f for f in all_files if f.source == "page"]
    if page_files:
        pdict = defaultdict(list)
        for f in page_files:
            pdict[f.page_name].append(f)
        for pname, fs in pdict.items():
            fs.sort(key=lambda x: x.display_name.lower())
            sections.append({
                "name": pname or "No page",
                "type": "page",
                "files": [_file_dict(f) for f in fs],
            })
            rendered.update(f.id for f in fs)

    folder_files = [f for f in all_files if f.folder_id is not None and f.id not in rendered]
    if folder_files:
        fdict = defaultdict(list)
        for f in folder_files:
            folder = tree.folders.get(f.folder_id)
            fdict[folder.name if folder else "No folder"].append(f)
        for fname, fs in fdict.items():
            fs.sort(key=lambda x: x.display_name.lower())
            sections.append({
                "name": fname,
                "type": "folder",
                "files": [_file_dict(f) for f in fs],
            })
            rendered.update(f.id for f in fs)

    flat = [f for f in all_files if f.id not in rendered]
    if flat:
        flat.sort(key=lambda x: x.display_name.lower())
        sections.append({
            "name": "Other files",
            "type": "other",
            "files": [_file_dict(f) for f in flat],
        })

    return sections


def _file_dict(f) -> dict:
    return {
        "id": f.id,
        "display_name": f.display_name,
        "size": human_readable_size(f.size) if f.size else "",
        "locked": f.locked,
        "hidden": f.hidden,
        "extension": f.extension,
    }
