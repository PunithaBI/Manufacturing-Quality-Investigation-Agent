from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:

    app_name: str = os.getenv(
        "APP_NAME",
        "Manufacturing Quality Investigation Agent",
    )

    environment: str = os.getenv(
        "ENVIRONMENT",
        "development",
    )

    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./nordwind.db",
    )

    vector_index_directory: str = os.getenv(
        "VECTOR_INDEX_DIRECTORY",
        "data/vector_index",
    )
    openai_api_key: str = os.getenv(
        "OPENAI_API_KEY",
        "",
    )

    openai_base_url: str = os.getenv(
        "OPENAI_BASE_URL",
        "",
    )

    openai_model: str = os.getenv(
        "OPENAI_MODEL",
        "",
    )
    @property
    def database_url_safe(self) -> str:
        url = self.database_url

        if "@" in url and "://" in url:
            prefix, remainder = url.split(
                "://",
                1,
            )

            if "@" in remainder:
                credentials, host = remainder.rsplit(
                    "@",
                    1,
                )

                if ":" in credentials:
                    username = credentials.split(
                        ":",
                        1,
                    )[0]

                    return (
                        f"{prefix}://"
                        f"{username}:***@{host}"
                    )

        return url


settings = Settings()
