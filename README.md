# DownVas Web

Download courses from Canvas LMS through a web interface.

## Prerequisites

- Python 3.10 or higher
- A Canvas LMS instance
- A Canvas API token

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd downvas
```

2. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Generate a unique secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

5. Copy the example environment file and configure it:

```bash
cp .env.example .env
```

6. Edit `.env` and fill in your values:

```env
SECRET_KEY=<paste the generated key here>
CANVAS_URL=https://your-canvas-instance.com
CANVAS_TOKEN=your-api-token-here
```

## Running

```bash
source .venv/bin/activate
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

## Usage

1. Enter your Canvas URL and API token
2. Enter a course ID or full course URL
3. The course tree will load with all files organized by modules, pages, and folders
4. Select files using checkboxes (individual or by section)
5. Click "Download selected" to download directly to your browser

## How to get a Canvas API token

1. Log in to your Canvas instance
2. Go to Account > Settings
3. Click "New Access Token"
4. Copy the generated token


