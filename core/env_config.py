import os
from pathlib import Path

TOKEN_KEY = "CANVAS_API_TOKEN"

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def get_api_token() -> str:
    """Return the Canvas API token stored in the environment/.env file."""
    token = os.environ.get(TOKEN_KEY)
    if token is not None:
        return token.strip()
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            stripped = line.lstrip()
            if stripped.startswith(TOKEN_KEY + "="):
                return stripped.split("=", 1)[1].strip()
    return ""


def set_api_token(value: str) -> None:
    """Persist the Canvas API token to the .env file and the current process."""
    value = (value or "").strip()
    if not value:
        return

    lines = ENV_PATH.read_text().splitlines() if ENV_PATH.exists() else []
    out = []
    replaced = False
    for line in lines:
        stripped = line.lstrip()
        is_token = stripped.startswith(TOKEN_KEY + "=") or stripped.startswith("# " + TOKEN_KEY + "=")
        if is_token:
            if not replaced:
                out.append(f"{TOKEN_KEY}={value}")
                replaced = True
            continue
        out.append(line)
    if not replaced:
        out.append(f"{TOKEN_KEY}={value}")

    ENV_PATH.write_text("\n".join(out) + "\n")
    os.environ[TOKEN_KEY] = value