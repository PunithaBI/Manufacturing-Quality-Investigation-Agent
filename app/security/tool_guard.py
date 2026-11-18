from __future__ import annotations

from app.tools.authorization import authorize


def authorize_tool_call(
    *,
    role: str,
    tool_name: str,
) -> tuple[bool, str | None]:

    try:
        authorize(
            role=role,
            tool_name=tool_name,
        )

    except PermissionError as exc:
        return False, str(exc)

    return True, None