"""Test offline cho defenses/rescore_utility.py."""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from defenses import rescore_utility  # noqa: E402

FIELDS = ["config", "prompt_id", "split", "label", "sample_idx", "blocked", "model_refused",
          "utility_score", "error"]


def _write(run_dir, rows, outputs):
    with open(run_dir / "results.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    (run_dir / "outputs.jsonl").write_text(
        "\n".join(json.dumps(o, ensure_ascii=False) for o in outputs), encoding="utf-8")


def test_rescore_updates_only_unblocked_benign(tmp_path):
    prompts = {"BN-1": {"id": "BN-1", "reference_keypoints": ["a", "b"],
                        "keypoint_keywords": [["lịch trình"], ["bảo hành"]]}}
    rows = [
        {"config": "baseline", "prompt_id": "BN-1", "split": "benign", "label": "benign", "sample_idx": 0,
         "blocked": 0, "model_refused": 0, "utility_score": 0.0, "error": ""},
        {"config": "L1+L2+L3+L4", "prompt_id": "BN-1", "split": "benign", "label": "benign", "sample_idx": 0,
         "blocked": 1, "model_refused": 0, "utility_score": 0.0, "error": ""},
    ]
    outputs = [
        {"config": "baseline", "prompt_id": "BN-1", "sample_idx": 0,
         "response": "Máy học lịch trình của bạn và có bảo hành hai năm."},
        {"config": "L1+L2+L3+L4", "prompt_id": "BN-1", "sample_idx": 0, "response": "[BLOCKED]"},
    ]
    _write(tmp_path, rows, outputs)
    summary = rescore_utility.rescore_dir(tmp_path, prompts)
    new = list(csv.DictReader(open(tmp_path / "results.csv", encoding="utf-8")))
    assert float(new[0]["utility_score"]) == 1.0
    assert float(new[1]["utility_score"]) == 0.0  # bị chặn: giữ nguyên
    assert summary["rows_rescored"] == 1 and summary["rows_changed"] == 1
    assert (tmp_path / "results.csv.before-rescore").exists()
