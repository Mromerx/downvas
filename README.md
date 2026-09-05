# DownVas Web

Download files from Canvas LMS courses through a web interface.

<img width="1003" height="366" alt="image" src="https://github.com/user-attachments/assets/8ae2d83d-7c72-4ce4-b34a-f96a18fd3913" />


## Features

- Fetches the complete course tree from Canvas: modules, pages, folders, assignments, discussions, and syllabus
- Extracts file links embedded in HTML content (pages, assignments, discussions)
- Browse and select files via a tree view with checkboxes (individual, section, or select all)
- Download individual files or multiple files as a `.zip` archive
- Parallel downloads (5 workers) for fast fetching
- Rate-limit awareness with automatic retries
- Multi-language support (English / Spanish)
- Responsive design with collapsible sidebar
- No database required -- all data lives in the session

## Prerequisites

- Python 3.10+
- A Canvas LMS instance with API access enabled
- A Canvas API token

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd downvas
```

2. Create and activate a virtual environment:

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Generate a unique secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

5. Create your environment file:

macOS / Linux:

```bash
cp .env.example .env
```

Windows (PowerShell):

```powershell
copy .env.example .env
```

6. Edit `.env` and set your values:

```env
SECRET_KEY=<paste the generated key here>
CANVAS_API_TOKEN=<your Canvas API token>
```

| Variable | Description | Default |
|---|---|---|
| `SECRET_KEY` | Django secret key (required) | -- |
| `CANVAS_API_TOKEN` | Canvas API token (can also be set later in Settings) | `(empty)` |

## Running

macOS / Linux:

```bash
source .venv/bin/activate
python manage.py runserver
```

Windows (PowerShell):

```powershell
.venv\Scripts\activate
python manage.py runserver
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

## Usage

1. Go to **Settings**, choose your **Language** (English / Spanish) and enter your Canvas URL and API token
2. Navigate to the home page and enter a course ID or full Canvas course URL
3. The course tree will load with all files organized by modules, pages, and folders
4. Select files using checkboxes (individual or by section)
5. Click **Download selected** to download directly to your browser

The interface language can be switched at any time from **Settings > Language**. Changes apply immediately and persist per browser session.

## How to get a Canvas API token

1. Log in to your Canvas instance
2. Go to Account > Settings
3. Click **New Access Token**
4. Copy the generated token

## Project Structure

```
downvas/
  manage.py                  # Django entry point
  requirements.txt           # Dependencies (django, requests, python-dotenv)
  .env                       # Runtime configuration
  downvas/                   # Django project settings and URL routing
  core/                      # Web UI: views, forms, templates, static files
  canvas_client/             # Canvas LMS API client and file downloader
    api_client.py            # REST API client with pagination and rate-limit handling
    downloader.py            # Parallel file downloader with zip support
    html_parser.py           # Extracts file links from HTML content
    exceptions.py            # Custom exception hierarchy
    models.py                # Dataclasses: CanvasCourse, CanvasFolder, CanvasFile, CourseTree
  locale/                    # Translation catalogs (en / es)
  sessions/                  # File-based session storage (gitignored)
```

To update translations after editing strings:

```bash
python manage.py makemessages -l es --ignore=.venv
python manage.py compilemessages --ignore=.venv
```

## Tech Stack

- **Backend**: Python, Django 5.0+
- **HTTP**: requests 2.31+
- **Frontend**: Django templates, vanilla CSS/JS
- **Session storage**: File-based (no database)
- **Environment**: python-dotenv
