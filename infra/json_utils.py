"""
Infrastructure: Fast JSON serialization using orjson with stdlib fallback.
"""

from __future__ import annotations

from typing import Any

try:
    import orjson

    def json_dumps(obj: Any) -> str:
        """Serialize to JSON string using orjson (10x faster than stdlib)."""
        return orjson.dumps(obj).decode("utf-8")

    def json_loads(data: str | bytes) -> Any:
        """Deserialize from JSON using orjson."""
        return orjson.loads(data)

    def json_dumps_bytes(obj: Any) -> bytes:
        """Serialize to JSON bytes (zero-copy for Redis/network)."""
        return orjson.dumps(obj)

    JSON_ENGINE = "orjson"

except ImportError:
    import json

    def json_dumps(obj: Any) -> str:
        return json.dumps(obj, ensure_ascii=False)

    def json_loads(data: str | bytes) -> Any:
        return json.loads(data)

    def json_dumps_bytes(obj: Any) -> bytes:
        return json.dumps(obj, ensure_ascii=False).encode("utf-8")

    JSON_ENGINE = "stdlib"
