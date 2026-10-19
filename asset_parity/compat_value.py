"""Shared legacy keyword resolution without changing accepted values."""

_UNSET = object()


def _resolve_compat_value(
    primary_name: str,
    primary_value: object,
    legacy_name: str,
    legacy_value: object,
) -> object:
    if primary_value is _UNSET and legacy_value is _UNSET:
        raise TypeError(f"missing required argument: {primary_name}")
    if (
        primary_value is not _UNSET
        and legacy_value is not _UNSET
        and primary_value != legacy_value
    ):
        raise TypeError(f"{primary_name} and {legacy_name} disagree")
    return legacy_value if primary_value is _UNSET else primary_value


