from .errors import ToolErrorCode


TOOL_PERMISSIONS = {
    "investigation_agent": {
        "get_ncr",
        "get_product",
        "get_bom",
        "get_serial_genealogy",
        "get_manufacturing_history",
        "get_inspection_results",
        "get_process_measurements",
        "search_historical_ncrs",
        "get_8d",
    }
}


def authorize(role: str, tool_name: str) -> None:
    allowed_tools = TOOL_PERMISSIONS.get(role, set())

    if tool_name not in allowed_tools:
        raise PermissionError(
            f"{ToolErrorCode.TOOL_UNAUTHORIZED.value}: "
            f"role '{role}' cannot execute '{tool_name}'"
        )