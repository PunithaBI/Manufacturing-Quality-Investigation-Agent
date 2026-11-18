from __future__ import annotations

import re

from .errors import ToolErrorCode


MAX_ID_LENGTH = 100
MAX_SEARCH_LENGTH = 200


def validate_required_string(
    value: str,
    field_name: str,
    *,
    max_length: int = MAX_ID_LENGTH,
) -> str:
    """
    Validate an identifier or required string.

    Fail-closed:
    - rejects None/empty values
    - removes surrounding whitespace
    - rejects excessively long values
    - rejects control characters
    """

    if value is None:
        raise ValueError(
            f"{ToolErrorCode.INVALID_INPUT.value}: "
            f"{field_name} is required"
        )

    value = value.strip()

    if not value:
        raise ValueError(
            f"{ToolErrorCode.INVALID_INPUT.value}: "
            f"{field_name} cannot be empty"
        )

    if len(value) > max_length:
        raise ValueError(
            f"{ToolErrorCode.INVALID_INPUT.value}: "
            f"{field_name} exceeds maximum length of {max_length}"
        )

    if any(ord(char) < 32 for char in value):
        raise ValueError(
            f"{ToolErrorCode.INVALID_INPUT.value}: "
            f"{field_name} contains invalid control characters"
        )

    return value


def validate_identifier(
    value: str,
    field_name: str,
    *,
    max_length: int = MAX_ID_LENGTH,
) -> str:
    """
    Validate a manufacturing identifier such as:

    NCR-0001
    PROD-001
    SN-00001
    MO-0001
    8D-0001
    """

    value = validate_required_string(
        value,
        field_name,
        max_length=max_length,
    )

    if not re.fullmatch(r"[A-Za-z0-9._:/-]+", value):
        raise ValueError(
            f"{ToolErrorCode.INVALID_INPUT.value}: "
            f"{field_name} contains unsupported characters"
        )

    return value


def validate_positive_integer(
    value: int,
    field_name: str,
    *,
    maximum: int,
) -> int:
    """
    Validate a bounded positive integer.
    """

    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(
            f"{ToolErrorCode.INVALID_INPUT.value}: "
            f"{field_name} must be an integer"
        )

    if value < 1:
        raise ValueError(
            f"{ToolErrorCode.INVALID_INPUT.value}: "
            f"{field_name} must be greater than zero"
        )

    if value > maximum:
        raise ValueError(
            f"{ToolErrorCode.TOOL_LIMIT_EXCEEDED.value}: "
            f"{field_name} cannot exceed {maximum}"
        )

    return value


def validate_limit(
    limit: int,
    *,
    maximum: int,
) -> int:
    """
    Validate result limits requested by a tool caller.
    """

    if not isinstance(limit, int) or isinstance(limit, bool):
        raise ValueError(
            f"{ToolErrorCode.INVALID_INPUT.value}: "
            "limit must be an integer"
        )

    if limit < 1:
        raise ValueError(
            f"{ToolErrorCode.INVALID_INPUT.value}: "
            "limit must be greater than zero"
        )

    if limit > maximum:
        raise ValueError(
            f"{ToolErrorCode.TOOL_LIMIT_EXCEEDED.value}: "
            f"limit cannot exceed {maximum}"
        )

    return limit


def validate_search_text(
    value: str,
    field_name: str = "search_text",
) -> str:
    """
    Validate free-text search input.
    """

    value = validate_required_string(
        value,
        field_name,
        max_length=MAX_SEARCH_LENGTH,
    )

    return value