"""Write the OpenAPI document to contracts/openapi.json (source for the web and iOS clients).

CI fails when the committed file differs from the code (scripts/check_contract.sh).
"""

from __future__ import annotations

import json
from pathlib import Path

from letterlens.api.app import create_app
from letterlens.config import Settings

OUT = Path(__file__).resolve().parents[2] / "contracts" / "openapi.json"


def main() -> None:
    app = create_app(Settings(env="test"))
    OUT.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
