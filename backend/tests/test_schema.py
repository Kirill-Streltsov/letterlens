from typing import Any

from letterlens.domain import ExplanationDraft, Extraction
from letterlens.llm.schema import strict_schema


def walk(node: Any) -> list[dict[str, Any]]:
    found = []
    if isinstance(node, dict):
        if node.get("type") == "object" and "properties" in node:
            found.append(node)
        for value in node.values():
            found += walk(value)
    elif isinstance(node, list):
        for value in node:
            found += walk(value)
    return found


def test_extraction_schema_is_strict() -> None:
    schema = strict_schema(Extraction)
    assert "$defs" not in schema and "$ref" not in str(schema)
    for obj in walk(schema):
        assert obj["additionalProperties"] is False
        assert set(obj["required"]) == set(obj["properties"])


def test_explanation_schema_has_no_open_objects() -> None:
    schema = strict_schema(ExplanationDraft)
    for obj in walk(schema):
        assert obj["additionalProperties"] is False
