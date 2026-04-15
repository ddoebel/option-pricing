import functools
import hashlib
import json
import pickle
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine


def _json_fallback_serializer(value: Any) -> str:
    """Serializer for values that aren't directly JSON serializable."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return repr(value)


def _build_cache_key(function_name: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    payload = json.dumps(
        {"function_name": function_name, "args": args, "kwargs": kwargs},
        sort_keys=True,
        default=_json_fallback_serializer,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def cache_to_db(
    engine: Engine,
    namespace: str,
    ttl_hours: Optional[int] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Cache function output in quant_db.entsoe_api_cache table.

    Notes:
    - TTL is optional. If omitted, cached values do not expire.
    - Cached payload uses pickle so pandas objects can be restored losslessly.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_key = _build_cache_key(f"{namespace}.{func.__name__}", args, kwargs)
            now = datetime.now(timezone.utc)

            with engine.begin() as conn:
                result = conn.execute(
                    text(
                        """
                        SELECT payload
                        FROM entsoe_api_cache
                        WHERE cache_key = :cache_key
                          AND (expires_at IS NULL OR expires_at > :now_utc)
                        """
                    ),
                    {"cache_key": cache_key, "now_utc": now},
                ).fetchone()

                if result:
                    return pickle.loads(result[0])

                data = func(*args, **kwargs)
                expires_at = None
                if ttl_hours is not None:
                    expires_at = now + timedelta(hours=ttl_hours)

                conn.execute(
                    text(
                        """
                        INSERT INTO entsoe_api_cache (
                            cache_key,
                            namespace,
                            function_name,
                            args_json,
                            payload,
                            created_at,
                            expires_at
                        ) VALUES (
                            :cache_key,
                            :namespace,
                            :function_name,
                            CAST(:args_json AS JSONB),
                            :payload,
                            :created_at,
                            :expires_at
                        )
                        ON CONFLICT (cache_key) DO UPDATE
                        SET payload = EXCLUDED.payload,
                            created_at = EXCLUDED.created_at,
                            expires_at = EXCLUDED.expires_at,
                            args_json = EXCLUDED.args_json
                        """
                    ),
                    {
                        "cache_key": cache_key,
                        "namespace": namespace,
                        "function_name": func.__name__,
                        "args_json": json.dumps(
                            {"args": args, "kwargs": kwargs},
                            default=_json_fallback_serializer,
                        ),
                        "payload": pickle.dumps(data),
                        "created_at": now,
                        "expires_at": expires_at,
                    },
                )
                return data

        return wrapper

    return decorator
