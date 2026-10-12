#!/usr/bin/env python3
"""analysis/ext2_report.py — tóm tắt kết quả tập ngoài thứ hai (ext2): đo cả hệ thống (giai đoạn 3) và phát hiện.

Đọc results/final/stage3-ext2/results.csv và attack_prompts/ext2_attack_prompts.json (để biết nhãn nguồn của từng
email). Mỗi prompt chạy một lần (m = 1) nên đơn vị là prompt: Wilson trên số prompt; hiệu giữa cấu hình dùng bootstrap
ghép cặp theo prompt. Ghi ext2_e2e.csv (ASR theo cấu hình, theo nhãn nguồn), ext2_benign.csv (chặn oan, độ trễ).

  python3 -m analysis.ext2_report --stage3 results/final/stage3-ext2 --out results/final/analysis-ext2
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.intervals import bootstrap_diff_ci, wilson  # noqa: E402

CHAIN = ["baseline", "L1", "L1+L2", "L1+L2+L3", "L1+L2+L3+L4"]


def e2e_attack(df: pd.DataFrame, cat: dict[str, str]) -> list[dict]:
    a = df[df.label == "attack"].copy()
    a["cat"] = a.prompt_id.map(cat)
    base = a[a.config == "baseline"].set_index("prompt_id").attack_success.astype(float)
    out = []
    for c in CHAIN:
        x = a[a.config == c].set_index("prompt_id")
        for name, sub in (("all", x), ("api_triggered", x[x.cat == "api_triggered"]), ("judge", x[x.cat != "api_triggered"])):
            if sub.empty:
                continue
            k, n = int(sub.attack_success.astype(float).sum()), len(sub)
            lo, hi = wilson(k, n)
            blocked = {L: int((sub.blocked_by == L).sum()) for L in ("L1", "L2", "L4")}
            row = {"config": c, "group": name, "n": n, "k": k, "asr": k / n, "wilson_lo": lo, "wilson_hi": hi,
                   "blocked_L1": blocked["L1"], "blocked_L2": blocked["L2"], "blocked_L4": blocked["L4"],
                   "reduction_vs_baseline": "", "red_lo": "", "red_hi": "",
                   "step_reduction": "", "step_lo": "", "step_hi": ""}
            if name == "all" and c != "baseline":
                ids = sorted(set(x.index) & set(base.index))
                d, l, h = bootstrap_diff_ci(list(base.loc[ids]), list(x.loc[ids].attack_success.astype(float)), paired=True)
                row.update(reduction_vs_baseline=d, red_lo=l, red_hi=h)
                prev = a[a.config == CHAIN[CHAIN.index(c) - 1]].set_index("prompt_id").attack_success.astype(float)
                ids2 = sorted(set(x.index) & set(prev.index))
                d2, l2, h2 = bootstrap_diff_ci(list(prev.loc[ids2]), list(x.loc[ids2].attack_success.astype(float)), paired=True)
                row.update(step_reduction=d2, step_lo=l2, step_hi=h2)
            out.append(row)
    return out


def e2e_benign(df: pd.DataFrame) -> list[dict]:
    b = df[df.label == "benign"]
    base_lat = b[b.config == "baseline"].latency_ms_total.mean()
    out = []
    for c in CHAIN:
        x = b[b.config == c]
        if x.empty:
            continue
        flag = (x.blocked.astype(int) == 1) | (x.model_refused.fillna(0).astype(int) == 1)
        k, n = int(flag.sum()), len(x)
        lo, hi = wilson(k, n)
        out.append({"config": c, "n": n, "frr_k": k, "frr": k / n, "wilson_lo": lo, "wilson_hi": hi,
                    "blocked_L1": int((x.blocked_by == "L1").sum()), "blocked_L2": int((x.blocked_by == "L2").sum()),
                    "blocked_L4": int((x.blocked_by == "L4").sum()), "mean_latency_ms": x.latency_ms_total.mean(),
                    "rho_T": x.latency_ms_total.mean() / base_lat, "mean_calls": x.n_model_calls.mean()})
    return out


def attack_cost(df: pd.DataFrame) -> list[dict]:
    a = df[df.label == "attack"]
    base = a[a.config == "baseline"].latency_ms_total.mean()
    return [{"config": c, "mean_latency_ms": a[a.config == c].latency_ms_total.mean(),
             "rho_T": a[a.config == c].latency_ms_total.mean() / base} for c in CHAIN if (a.config == c).any()]


def write(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--stage3", type=Path, default=ROOT / "results/final/stage3-ext2")
    ap.add_argument("--prompts", type=Path, default=ROOT / "attack_prompts/ext2_attack_prompts.json")
    ap.add_argument("--out", type=Path, default=ROOT / "results/final/analysis-ext2")
    args = ap.parse_args(argv)
    df = pd.read_csv(args.stage3 / "results.csv")
    if df.error.notna().any():
        print(f"CẢNH BÁO: {int(df.error.notna().sum())} dòng có lỗi", file=sys.stderr)
    prompts = json.loads(args.prompts.read_text(encoding="utf-8"))
    cat = {p["id"]: p["notes"].split("label_in_source=")[1].split(";")[0] for p in prompts}
    args.out.mkdir(parents=True, exist_ok=True)
    write(args.out / "ext2_e2e.csv", e2e_attack(df, cat))
    write(args.out / "ext2_benign.csv", e2e_benign(df))
    write(args.out / "ext2_attack_cost.csv", attack_cost(df))
    print(f"[OK] {args.out}; {len(df)} dòng")
    return 0


if __name__ == "__main__":
    sys.exit(main())
