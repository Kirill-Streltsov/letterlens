"""Convert pydantic models to strict JSON schemas for structured outputs.

Providers with strict structured outputs (Claude, Mistral, OpenAI-compatible)
need: no $ref, ``additionalProperties: false`` on every object, and every
property listed in ``required``. Optional fields stay nullable.
"""

from __future__ import annotations

import copy
from typing import Any

from pydantic import BaseModel

_DROP = {"title", "default", "examples"}


def strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    raw = model.model_json_schema()
    defs = raw.pop("$defs", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                name = node["$ref"].split("/")[-1]
                return resolve(copy.deepcopy(defs[name]))
            out = {k: resolve(v) for k, v in node.items() if k not in _DROP}
            if out.get("type") == "object" and "properties" in out:
                out["additionalProperties"] = False
                out["required"] = list(out["properties"].keys())
            elif out.get("type") == "object" and "additionalProperties" in out:
                # dict[str, str]: keep the value schema, providers accept it.
                pass
            return out
        if isinstance(node, list):
            return [resolve(v) for v in node]
        return node

    result = resolve(raw)
    assert isinstance(result, dict)
    return result
