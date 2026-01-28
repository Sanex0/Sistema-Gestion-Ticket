import logging

from flask_app.services.email_ingest import poll_once


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = poll_once()
    print(result)
