"""Print the OpenAPI schema: `python -m app.openapi`."""

import json
import sys

from app.main import create_app
from app.platform.settings import Settings

# The schema does not depend on the database; the URL only fills the required setting.
SCHEMA_ONLY_URL = "postgresql+psycopg://schema:schema@localhost/schema"


def main() -> None:
    """Write the schema JSON to stdout."""
    app = create_app(Settings(database_url=SCHEMA_ONLY_URL))
    sys.stdout.write(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
