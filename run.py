import os

from flask_app import app


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "yes", "y", "on"}


if __name__ == "__main__":
    # Desarrollo por defecto (auto-reload). Para desactivar: set FLASK_DEBUG=0
    debug = _env_bool("FLASK_DEBUG", True)
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "5000"))

    app.run(debug=debug, use_reloader=debug, host=host, port=port)
