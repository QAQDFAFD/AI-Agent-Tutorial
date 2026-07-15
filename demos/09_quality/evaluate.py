"""一个不依赖平台的可重复离线评测。"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

guardrails = importlib.import_module("demos.09_quality.guardrails")
structured = importlib.import_module("demos.02_openai_structured.main")


def evaluate(dataset_path: Path | None = None) -> dict:
    path = dataset_path or Path(__file__).with_name("dataset.jsonl")
    examples = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    passed = 0
    failures: list[dict] = []

    for example in examples:
        try:
            guardrails.check_input(example["input"])
            actual = structured.classify_locally(example["input"]).intent
        except guardrails.GuardrailRejected:
            actual = "blocked"

        ok = actual == example["expected_intent"]
        passed += ok
        if not ok:
            failures.append(
                {
                    "input": example["input"],
                    "expected": example["expected_intent"],
                    "actual": actual,
                }
            )

    return {
        "total": len(examples),
        "passed": passed,
        "accuracy": passed / len(examples),
        "failures": failures,
    }


def main() -> None:
    print(json.dumps(evaluate(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
