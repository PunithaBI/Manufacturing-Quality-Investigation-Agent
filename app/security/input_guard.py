from __future__ import annotations



MAX_NCR_LENGTH = 100
MAX_INVESTIGATION_ID_LENGTH = 100
MAX_REQUESTED_RESULTS = 20


def validate_investigation_input(
    *,
    ncr_number: str,
    investigation_id: str | None = None,
    max_results: int = 20,
) -> tuple[bool, list[str]]:

    errors: list[str] = []

    if not isinstance(ncr_number, str):
        errors.append("NCR number must be a string.")
    else:
        ncr_number = ncr_number.strip()

        if not ncr_number:
            errors.append("NCR number is required.")

        if len(ncr_number) > MAX_NCR_LENGTH:
            errors.append("NCR number exceeds maximum length.")

        if any(ord(char) < 32 for char in ncr_number):
            errors.append("NCR number contains control characters.")

    if investigation_id is not None:

        if not isinstance(investigation_id, str):
            errors.append("Investigation ID must be a string.")

        else:
            investigation_id = investigation_id.strip()

            if len(investigation_id) > MAX_INVESTIGATION_ID_LENGTH:
                errors.append(
                    "Investigation ID exceeds maximum length."
                )

            if any(ord(char) < 32 for char in investigation_id):
                errors.append(
                    "Investigation ID contains control characters."
                )

    if (
        not isinstance(max_results, int)
        or isinstance(max_results, bool)
    ):
        errors.append("max_results must be an integer.")

    elif max_results < 1 or max_results > MAX_REQUESTED_RESULTS:
        errors.append(
            f"max_results must be between 1 and "
            f"{MAX_REQUESTED_RESULTS}."
        )

    return not errors, errors