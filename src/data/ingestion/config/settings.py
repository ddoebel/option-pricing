import os


def _get_env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer, got '{raw}'") from exc


def _get_env_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return default
    return [x.strip() for x in raw.split(",") if x.strip()]


DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": _get_env_int("DB_PORT", 5432),
    "database": os.getenv("DB_NAME", "options_db"),
    "user": os.getenv("DB_USER", "quant_user"),
    "password": os.getenv("DB_PASSWORD", ""),
}

PIPELINE_CONFIG = {
    "symbols": _get_env_list("PIPELINE_SYMBOLS", ["SPY"]),
}