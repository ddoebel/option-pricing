import os


def _get_env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return int(str(raw).strip())
    except ValueError as exc:
        raise ValueError(f"Environment variable {name} must be an integer, got '{raw}'") from exc


def _get_env_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return default
    return [x.strip() for x in raw.split(",") if x.strip()]


def get_db_config() -> dict[str, object]:
    """
    Read connection settings from the current process environment at call time.

    Important: do not snapshot these values at import time. The shell often sets
    ``DB_PORT`` / ``DB_USER`` after ``python`` starts unless they are exported, and
    tooling may load env files before the first DB connection but after imports.
    """
    return {
        "host": (os.getenv("DB_HOST") or "localhost").strip(),
        "port": _get_env_int("DB_PORT", 5432),
        "database": (os.getenv("DB_NAME") or "options_db").strip(),
        "user": (os.getenv("DB_USER") or "quant_user").strip(),
        "password": os.getenv("DB_PASSWORD") or "",
    }

PIPELINE_CONFIG = {
    "symbols": _get_env_list("PIPELINE_SYMBOLS", ["SPY"]),
}