import json
from pathlib import Path


def test_shipped_json_results_are_marked_synthetic() -> None:
    for path in Path("outputs").glob("**/*.json"):
        if any(part in path.parts for part in ("attack_work", "work", "adv", "clean")) or path.name.startswith("trigger"):
            continue
        value = json.loads(path.read_text(encoding="utf-8"))
        assert "not a paper result" in str(value.get("label", "")), path
