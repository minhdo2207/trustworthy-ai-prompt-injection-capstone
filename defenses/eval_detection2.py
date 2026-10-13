#!/usr/bin/env python3
"""defenses/eval_detection2.py — đo phát hiện của L1, L2 và L1+L2 trên tập ngoài thứ hai (ext2), zero-shot.

CẢNH BÁO: L1 và L2 đã được chỉnh (từ khoá, ngưỡng) trên train và benign `tune`. Không chỉnh chúng theo kết quả này.

Khác `eval_detection.py`: mỗi mục là một đoạn văn bản (prompt hoặc email), không có dạng "embedded/bare"; L1 và L2 đều
chạy trên TOÀN BỘ mục. "Phát hiện" = lớp trả `block`. Có thể dừng và chạy tiếp (`--resume`): các mục đã có trong
detection2_items.csv được bỏ qua.

  python3 defenses/eval_detection2.py --out results/final/detection-ext2 --resume
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.intervals import wilson  # noqa: E402

DATA = ROOT / "attack_prompts" / "ext2_detection_full.json"
TASK = "Tóm tắt tài liệu sau trong 3 câu."
ITEM_COLUMNS = ["id", "subset", "label", "category", "independent", "n_chars", "l1_action", "l1_score",
                "l2_action", "l2_score", "l1l2_blocked", "l2_calls_new"]
SUMMARY_COLUMNS = ["layer", "label", "metric", "dim", "value", "n", "k", "rate", "wilson_lo", "wilson_hi"]
WARNING = "CẢNH BÁO: đánh giá ZERO-SHOT; không chỉnh L1/L2 theo kết quả này."


def read_items(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_items(path: Path, rows: list[dict]) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ITEM_COLUMNS, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(path)


def summarize(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    layers = {"L1": lambda r: r["l1_action"] == "block", "L2": lambda r: r["l2_action"] == "block",
              "L1+L2": lambda r: str(r["l1l2_blocked"]) == "1"}
    for layer, flag in layers.items():
        for label, metric in (("attack", "TPR"), ("benign", "FPR")):
            sub = [r for r in rows if r["label"] == label and r["l2_action"] != ""]
            groups = [("all", "all", sub), ("independent", "yes", [r for r in sub if str(r["independent"]) == "True"])]
            for dim in ("subset", "category"):
                for v in sorted({r[dim] for r in sub}):
                    groups.append((dim, v, [r for r in sub if r[dim] == v]))
            for dim, v, g in groups:
                if not g:
                    continue
                k, n = sum(1 for r in g if flag(r)), len(g)
                lo, hi = wilson(k, n)
                out.append({"layer": layer, "label": label, "metric": metric, "dim": dim, "value": v, "n": n, "k": k,
                            "rate": round(k / n, 4), "wilson_lo": round(lo, 4), "wilson_hi": round(hi, 4)})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="chỉ chạy n mục đầu (thử nhanh)")
    ap.add_argument("--no-l2", action="store_true")
    ap.add_argument("--checkpoint", type=int, default=100)
    args = ap.parse_args(argv)
    print(WARNING, file=sys.stderr)

    items = json.loads(args.data.read_text(encoding="utf-8"))
    if args.limit:
        items = items[:args.limit]
    from defenses import layer1_filtering as l1
    l2 = None
    if not args.no_l2:
        from defenses import layer2_refusal_classifier as l2
        l2._BUDGET["limit"] = None
    args.out.mkdir(parents=True, exist_ok=True)
    items_path = args.out / "detection2_items.csv"
    done: dict[str, dict] = {}
    if args.resume and items_path.exists():
        done = {r["id"]: r for r in read_items(items_path)}
        print(f"[resume] {len(done)} mục đã có", file=sys.stderr)

    rows = list(done.values())
    t0 = time.perf_counter()
    for n, it in enumerate(items, 1):
        if it["id"] in done:
            continue
        r1 = l1.check(TASK, it["text"])
        row = {"id": it["id"], "subset": it["subset"], "label": it["label"], "category": it["category"],
               "independent": it.get("independent", True), "n_chars": len(it["text"]), "l1_action": r1.action,
               "l1_score": "" if r1.score is None else round(r1.score, 4), "l2_action": "", "l2_score": "",
               "l1l2_blocked": "", "l2_calls_new": ""}
        if l2 is not None:
            before = l2.STATS["calls"]
            res = l2.check(TASK, it["text"])
            doc2 = r1.document if r1.action == "sanitize" else it["text"]
            res2 = res if doc2 == it["text"] else l2.check(TASK, doc2)
            row.update(l2_action=res.action, l2_score=round(res.score or 0.0, 4),
                       l1l2_blocked=int(r1.action == "block" or res2.action == "block"),
                       l2_calls_new=l2.STATS["calls"] - before)
        rows.append(row)
        if len(rows) % args.checkpoint == 0:
            write_items(items_path, rows)
            el = time.perf_counter() - t0
            print(f"[{len(rows)}/{len(items)}] {el:.0f}s", flush=True)
    write_items(items_path, rows)

    summary = summarize(rows) if l2 is not None else []
    with (args.out / "detection2.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(summary)
    meta = {"created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "n_items": len(rows),
            "l1_threshold": l1.THRESHOLD, "l2_threshold": getattr(l2, "THRESHOLD", None),
            "l2_model": l2._model() if l2 else None, "l2_new_calls": l2.STATS["calls"] if l2 else 0,
            "l2_cache_hits": l2.STATS["hits"] if l2 else 0, "data": str(args.data.name), "task": TASK}
    (args.out / "detection2_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
