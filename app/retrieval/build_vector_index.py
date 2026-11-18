from __future__ import annotations

import argparse
from pathlib import Path

from .ingestion import VectorIngestionService


SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
}


def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "Build the manufacturing semantic "
            "vector index."
        )
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Directory containing manufacturing documents",
    )

    parser.add_argument(
        "--index",
        default="data/vector_index",
        help="Vector index directory",
    )

    args = parser.parse_args()

    input_directory = Path(
        args.input
    )

    if not input_directory.exists():
        raise SystemExit(
            f"Input directory does not exist: "
            f"{input_directory}"
        )

    service = VectorIngestionService(
        index_directory=args.index,
    )

    total_chunks = 0

    for path in sorted(
        input_directory.rglob("*")
    ):

        if not path.is_file():
            continue

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        print(
            f"Ingesting: {path}"
        )

        count = service.ingest_text_file(
            path,
            source_type="manufacturing_document",
        )

        total_chunks += count

    print()
    print(
        "VECTOR INDEX BUILD COMPLETE"
    )
    print(
        f"Chunks indexed: {total_chunks}"
    )
    print(
        f"Index: {args.index}"
    )


if __name__ == "__main__":
    main()