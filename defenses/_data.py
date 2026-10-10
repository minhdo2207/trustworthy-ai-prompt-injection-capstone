"""defenses/_data.py — đọc dữ liệu dev cho L1/L2 (chỉ train + benign `tune`).

Cố ý KHÔNG có hàm nào đọc tệp hold-out; `tests/test_l1.py` kiểm tra không có tên tệp đó trong mã.

Hỗ trợ cả schema cũ (`content`) lẫn schema v2 (`untrusted_document`, `user_task`,
`label`, `tune`) để chạy được trước và sau khi nhánh dữ liệu gộp vào.
Nếu chưa có `benign_prompts.json` thì rơi về fixture benign tự viết
(`tests/fixtures/benign_dev_fixture.json`) và đánh dấu `from_fixture=True`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRAIN_PATH = ROOT / "attack_prompts" / "train_prompts.json"
BENIGN_PATH = ROOT / "attack_prompts" / "benign_prompts.json"
BENIGN_FIXTURE = ROOT / "tests" / "fixtures" / "benign_dev_fixture.json"
DEFAULT_TASK = "Tóm tắt tài liệu sau trong 3 câu."


@dataclass
class Sample:
    id: str
    label: str            # "attack" | "benign"
    attack_type: str
    user_task: str
    document: str


def _to_sample(item: dict, label: str) -> Sample:
    doc = item.get("untrusted_document", item.get("content", ""))
    return Sample(
        id=item.get("id", "?"),
        label=label,
        attack_type=item.get("attack_type", "none") or "none",
        user_task=item.get("user_task", DEFAULT_TASK),
        document=doc,
    )


def _read(path: Path) -> list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_train_attacks(path: Path = TRAIN_PATH) -> list[Sample]:
    """Prompt tấn công thuộc split train (schema cũ hoặc v2)."""
    out = []
    for it in _read(path):
        if it.get("label", "attack") != "attack":
            continue
        if it.get("split", "train") != "train":
            continue
        out.append(_to_sample(it, "attack"))
    return out


def load_benign_tune(path: Path = BENIGN_PATH) -> tuple[list[Sample], bool]:
    """Benign có `tune` true. Trả (mẫu, from_fixture)."""
    from_fixture = not path.exists()
    items = _read(BENIGN_FIXTURE if from_fixture else path)
    out = [_to_sample(it, "benign") for it in items if it.get("tune", True)]
    return out, from_fixture
