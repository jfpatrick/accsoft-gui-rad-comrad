
def parse_cmw_error_message(original: str) -> str:
    """Parses compound CMW errors (both RBAC and RDA) into user-friendly strings that can be presented in the UI."""
    parts = original.split(' : ')
    parts = parts[-1].split(' --> ')
    return parts[-1]
