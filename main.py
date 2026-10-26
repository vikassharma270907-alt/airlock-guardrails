"""
Airlock Vercel Web Entrypoint.
Provides a standard WSGI application `app` to serve the Airlock dashboard and static assets.
"""

import mimetypes
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent


def app(environ, start_response):
    """WSGI application entrypoint for Vercel Serverless Python runtime."""
    raw_path = environ.get("PATH_INFO", "/").strip("/")
    path = raw_path if raw_path else "index.html"

    # Resolve file within repo root and prevent directory traversal
    try:
        resolved_path = (ROOT_DIR / path).resolve()
        if not str(resolved_path).startswith(str(ROOT_DIR)) or not resolved_path.is_file():
            resolved_path = ROOT_DIR / "index.html"
    except Exception:
        resolved_path = ROOT_DIR / "index.html"

    if resolved_path.is_file():
        mime_type, _ = mimetypes.guess_type(str(resolved_path))
        mime_type = mime_type or "application/octet-stream"
        content = resolved_path.read_bytes()
        start_response(
            "200 OK",
            [
                ("Content-Type", mime_type),
                ("Content-Length", str(len(content))),
                ("Cache-Control", "public, max-age=3600"),
            ],
        )
        return [content]

    start_response("404 Not Found", [("Content-Type", "text/plain")])
    return [b"Not Found"]


if __name__ == "__main__":
    from wsgiref.simple_server import make_server

    print("Airlock Dashboard serving on http://localhost:3000 ...")
    server = make_server("0.0.0.0", 3000, app)
    server.serve_forever()
