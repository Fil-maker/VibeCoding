"""Print the OpenAPI schema: `python -m app.openapi`."""

import json
import sys

from app.main import create_app
from app.platform.settings import Settings

# The schema does not depend on the database; the URL only fills the required setting.
SCHEMA_ONLY_URL = "postgresql+psycopg://schema:schema@localhost/schema"
SCHEMA_ONLY_BASE_URL = "http://localhost"
SCHEMA_ONLY_MAIL_FROM = "schema@localhost"
SCHEMA_ONLY_SMTP_HOST = "localhost"


def main() -> None:
    """Write the schema JSON to stdout."""
    app = create_app(
        Settings(
            database_url=SCHEMA_ONLY_URL,
            app_base_url=SCHEMA_ONLY_BASE_URL,
            mail_from=SCHEMA_ONLY_MAIL_FROM,
            smtp_host=SCHEMA_ONLY_SMTP_HOST,
        )
    )
    sys.stdout.write(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
