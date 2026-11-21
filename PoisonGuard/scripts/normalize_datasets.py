"""Normalize locally provisioned datasets into PoisonGuard event JSONL files."""

from __future__ import annotations

from pathlib import Path

from poisonguard.data.dataset_normalizers import (
    normalize_aeslc_parquet,
    normalize_lamp_json,
    normalize_personachat,
    normalize_sms_collection,
)


def main() -> None:
    root = Path("datas")
    normalize_aeslc_parquet(
        root / "aeslc" / "data" / "train-00000-of-00001.parquet",
        root / "aeslc" / "poisonguard_events.jsonl",
    )
    normalize_sms_collection(
        root / "sms+spam+collection" / "SMSSpamCollection",
        root / "sms+spam+collection" / "poisonguard_events.jsonl",
    )
    normalize_personachat(
        root / "persona-chat" / "test_self_original.txt",
        root / "persona-chat" / "poisonguard_events.jsonl",
    )
    lamp_questions = root / "LaMP" / "data" / "LaMP_4" / "dev" / "dev_questions.json"
    lamp_outputs = root / "LaMP" / "data" / "LaMP_4" / "dev" / "dev_outputs.json"
    if lamp_questions.is_file():
        normalize_lamp_json(
            lamp_questions,
            root / "LaMP" / "data" / "LaMP_4" / "train" / "poisonguard_events.jsonl",
            outputs_path=lamp_outputs if lamp_outputs.is_file() else None,
            task="LaMP-4",
        )


if __name__ == "__main__":
    main()
