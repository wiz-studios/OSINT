from __future__ import annotations

from pathlib import Path

from flask import Flask, Response, g, request

from .config import Settings, load_settings
from .routes import bp


def create_app(settings: Settings) -> Flask:
    project_root = Path(__file__).resolve().parents[1]
    templates_dir = project_root / "templates"
    static_dir = project_root / "static"

    app = Flask(
        __name__,
        template_folder=str(templates_dir) if templates_dir.exists() else None,
        static_folder=str(static_dir) if static_dir.exists() else None,
        static_url_path="/static",
    )
    app.config["WIRETAPPER_SETTINGS"] = settings
    app.register_blueprint(bp)

    @app.before_request
    def _request_id() -> None:
        import uuid

        g.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex

    @app.after_request
    def _add_request_id_header(response: Response) -> Response:
        rid = getattr(g, "request_id", None)
        if rid:
            response.headers["X-Request-ID"] = rid
        return response

    return app


def main() -> int:
    settings = load_settings()
    app = create_app(settings)
    app.run(host=settings.host, port=settings.port, debug=settings.debug)
    return 0
