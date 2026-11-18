from __future__ import annotations

from app.db.database import Base, engine

# Import all models so SQLAlchemy registers their tables.
from app.db import models  # noqa: F401
from app.db import investigation_models  # noqa: F401


def main() -> None:

    print("========================================")
    print("MQI DATABASE INITIALIZATION")
    print("========================================")

    print(
        f"Database: {engine.url.render_as_string(hide_password=True)}"
    )

    Base.metadata.create_all(
        bind=engine
    )

    print()
    print("DATABASE INITIALIZATION COMPLETE")


if __name__ == "__main__":
    main()