"""defenses/rescore_utility.py — chấm lại `utility_score` và `model_refused` của dòng benign.

Vì sao có file này: bộ từ khoá của benign được hiệu chuẩn sau khi đo baseline (xem
`attack_prompts/src_benign.py`, `VI_ALTERNATES`). Các dòng benign đã ghi trước đó dùng từ khoá cũ.
Công cụ này chấm lại từ `outputs.jsonl` (câu trả lời đã lưu) bằng đúng hàm của harness, nên áp dụng
giống nhau cho mọi cấu hình mà không phải chạy lại model.

Chỉ đổi các dòng benign có `reference_keypoints`, không bị chặn, không lỗi; dòng bị chặn giữ utility 0.
Ghi `results.csv.before-rescore` trước khi ghi đè.

Dùng: python3 -m defenses.rescore_utility results/final/stage1-chain [results/final/stage2 ...]
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from defenses import utility  # noqa: E402

BENIGN_FILES = ("benign_prompts.json",)


def load_prompts(data_dir: Path) -> dict:
    out: dict = {}
    for name in BENIGN_FILES:
        p = data_dir / name
        if p.exists():
            for item in json.loads(p.read_text("utf-8")):
                out[item["id"]] = item
    return out


def load_responses(path: Path) -> dict:
    resp: dict = {}
    for line in path.read_text("utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            resp[(r["config"], r["prompt_id"], int(r["sample_idx"]))] = r.get("response", "")
    return resp


def rescore_dir(run_dir: Path, prompts: dict) -> dict:
    csv_path, out_path = run_dir / "results.csv", run_dir / "outputs.jsonl"
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)
    resp = load_responses(out_path)
    before, after, changed = [], [], 0
    for row in rows:
        p = prompts.get(row["prompt_id"])
        if (row["split"] != "benign" or row["label"] != "benign" or p is None
                or not p.get("reference_keypoints") or row["error"] or int(row["blocked"] or 0)):
            continue
        text = resp.get((row["config"], row["prompt_id"], int(row["sample_idx"])))
        if text is None:
            continue
        hits = utility.keypoint_hits(text, p, False)
        new_u = round(sum(h for h, _ in hits) / len(hits), 4) if hits else 0.0
        new_r = int(utility.model_refused(text))
        old_u = float(row["utility_score"]) if row["utility_score"] != "" else None
        before.append(old_u if old_u is not None else 0.0)
        after.append(new_u)
        if old_u != new_u or str(new_r) != str(row["model_refused"]):
            changed += 1
        row["utility_score"], row["model_refused"] = new_u, new_r
    shutil.copyfile(csv_path, run_dir / "results.csv.before-rescore")
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return {"dir": str(run_dir), "rows_rescored": len(after), "rows_changed": changed,
            "mean_before": round(statistics.mean(before), 4) if before else None,
            "mean_after": round(statistics.mean(after), 4) if after else None}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("dirs", nargs="+", type=Path)
    ap.add_argument("--data-dir", type=Path, default=ROOT / "attack_prompts")
    args = ap.parse_args()
    prompts = load_prompts(args.data_dir)
    for d in args.dirs:
        print(json.dumps(rescore_dir(d, prompts), ensure_ascii=False))


if __name__ == "__main__":
    main()
