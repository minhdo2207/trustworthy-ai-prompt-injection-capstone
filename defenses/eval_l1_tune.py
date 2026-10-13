#!/usr/bin/env python3
"""defenses/eval_l1_tune.py — đo L1 trên tập chỉnh v2 (không gọi model): TPR theo nguồn, chặn nhầm theo nguồn, mẫu bỏ lọt.

Chỉ dùng v2_detection_tune.json (giao thức v2). KHÔNG chạy trên dữ liệu hold-out.
  python3 defenses/eval_l1_tune.py [--show-miss SUBSET] [--show-fp] [--out results/v2/l1_tune_<tag>.json]
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from defenses import layer1_filtering as L1  # noqa: E402

TASK = "Tóm tắt tài liệu sau trong 3 câu."
EXCLUDE_TPR = {"B_spml"}          # payload mơ hồ: không dùng làm mục tiêu TPR (xem PROTOCOL.md)


def evaluate(items: list[dict]) -> list[dict]:
    rows = []
    for it in items:
        r = L1.check(TASK, it["text"])
        rows.append({"id": it["id"], "label": it["label"], "subset": it["subset"], "action": r.action,
                     "score": r.score or 0.0, "reason": r.reason})
    return rows


def summarize(rows: list[dict]) -> dict:
    out = {"tpr": {}, "fpr": {}}
    for lab, key in (("attack", "tpr"), ("benign", "fpr")):
        by = collections.defaultdict(lambda: [0, 0])
        for r in rows:
            if r["label"] == lab:
                by[r["subset"]][1] += 1
                by[r["subset"]][0] += r["action"] == "block"
        out[key] = {k: v for k, v in sorted(by.items())}
    att = [r for r in rows if r["label"] == "attack" and r["subset"] not in EXCLUDE_TPR]
    ben = [r for r in rows if r["label"] == "benign"]
    out["tpr_objective"] = [sum(r["action"] == "block" for r in att), len(att)]
    out["fpr_all"] = [sum(r["action"] == "block" for r in ben), len(ben)]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, default=ROOT / "attack_prompts" / "v2_detection_tune.json")
    ap.add_argument("--show-miss", default="")
    ap.add_argument("--show-fp", action="store_true")
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--sample", type=int, default=0, help="chỉ lấy n mục mỗi (nguồn, nhãn) để lặp nhanh")
    args = ap.parse_args()
    items = json.loads(args.data.read_text(encoding="utf-8"))
    if args.sample:
        import random
        rng, groups = random.Random(0), collections.defaultdict(list)
        for it in items:
            groups[(it["subset"], it["label"])].append(it)
        items = [x for g in groups.values() for x in rng.sample(g, min(args.sample, len(g)))]
    t0 = time.perf_counter()
    rows = evaluate(items)
    s = summarize(rows)
    print(f"[{len(rows)} mục, {time.perf_counter() - t0:.0f}s]")
    for k in ("tpr", "fpr"):
        for sub, (a, b) in s[k].items():
            print(f"  {k.upper()} {sub:18} {a:5}/{b:<5} {100 * a / b:5.1f}%")
    a, b = s["tpr_objective"]
    c, d = s["fpr_all"]
    print(f"MỤC TIÊU: TPR (không tính SPML) {a}/{b} = {100 * a / b:.1f}% | FPR benign tune {c}/{d} = {100 * c / d:.2f}%")
    byid = {it["id"]: it for it in items}
    if args.show_miss:
        miss = [r for r in rows if r["subset"] == args.show_miss and r["label"] == "attack" and r["action"] != "block"]
        for r in miss[:args.n]:
            print("MISS", r["id"], "|", byid[r["id"]]["text"][:220].replace("\n", " "))
    if args.show_fp:
        for r in [r for r in rows if r["label"] == "benign" and r["action"] == "block"][:args.n]:
            print("FP", r["id"], r["subset"], r["reason"][:60], "|", byid[r["id"]]["text"][:200].replace("\n", " "))
    if args.out:
        args.out.write_text(json.dumps(s, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
