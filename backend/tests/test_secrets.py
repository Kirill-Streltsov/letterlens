import os

import pytest

from letterlens.secrets import load_ssm_into_env


class FakeSsm:
    def get_paginator(self, name: str) -> "FakeSsm":
        assert name == "get_parameters_by_path"
        return self

    def paginate(self, **kwargs: object) -> list[dict[str, object]]:
        assert kwargs["WithDecryption"] is True
        return [
            {
                "Parameters": [
                    {"Name": "/letterlens/test/database_url", "Value": "postgresql://x"},
                    {"Name": "/letterlens/test/llm_api_key", "Value": "k"},
                ]
            }
        ]


def test_parameters_become_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LETTERLENS_DATABASE_URL", raising=False)
    monkeypatch.setenv("LETTERLENS_LLM_API_KEY", "explicit")
    loaded = load_ssm_into_env("/letterlens/test/", FakeSsm())
    assert set(loaded) == {"LETTERLENS_DATABASE_URL", "LETTERLENS_LLM_API_KEY"}
    assert os.environ["LETTERLENS_DATABASE_URL"] == "postgresql://x"
    assert os.environ["LETTERLENS_LLM_API_KEY"] == "explicit"
    monkeypatch.delenv("LETTERLENS_DATABASE_URL")


def test_no_prefix_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LETTERLENS_SSM_PREFIX", raising=False)
    assert load_ssm_into_env() == []
