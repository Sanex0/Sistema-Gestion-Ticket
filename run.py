import os
import threading
import logging

from flask_app import app
from flask_app.services.email_ingest import connect_and_idle_loop


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "yes", "y", "on"}


if __name__ == "__main__":
    # Desarrollo por defecto (auto-reload). Para desactivar: set FLASK_DEBUG=0
    debug = _env_bool("FLASK_DEBUG", True)
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "5003"))

    logging.basicConfig(level=logging.INFO)

    # Opcional: arrancar el poller de email en un hilo separado
    # Por defecto enciende el poller para que el ingreso de correos sea automático
    start_poller = _env_bool('START_EMAIL_POLLER', True)
    if start_poller:
        # Evitar doble arranque cuando Flask usa reloader
        if not debug or os.getenv('WERKZEUG_RUN_MAIN') == 'true':
            keepalive = int(os.getenv('EMAIL_KEEPALIVE', '300'))
            min_backoff = int(os.getenv('EMAIL_MIN_BACKOFF', '5'))
            max_backoff = int(os.getenv('EMAIL_MAX_BACKOFF', '600'))
            t = threading.Thread(
                target=connect_and_idle_loop,
                kwargs={'imap_cfg': None, 'keepalive': keepalive, 'min_backoff': min_backoff, 'max_backoff': max_backoff},
                daemon=True,
            )
            t.start()
            logging.info('Email poller thread started (keepalive=%s)', keepalive)

    app.run(debug=debug, use_reloader=debug, host=host, port=port)
