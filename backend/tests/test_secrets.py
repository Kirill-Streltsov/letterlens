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


