#!/usr/bin/env python3
"""Gộp kết quả các lần chạy của ma trận cuối thành một `results.csv` + `outputs.jsonl` (đầu vào của `analysis.stats`).

Quy tắc gộp (đã dùng để tạo `results/final/merged`; script này tái tạo được nó, xem `--verify`):
  1. nối các thư mục chạy theo thứ tự cố định (RUNS);
  2. cấu hình `only_L1` không chạy riêng: nó là cấu hình `L1` ở lần lấy mẫu 0 (L1 không gọi mô hình và đứng đầu
     chuỗi) nên được sinh bằng cách sao các dòng `L1` có `sample_idx = 0` của stage1-chain (train, benign) và
     stage2-main (holdout, test_indist), đổi `config` thành `only_L1` và `run_id` thành `<run>-l1alias`.
Không gọi mô hình, chỉ đọc/ghi tệp.

Dùng: python3 report/scripts/merge_results.py --final-dir /.../results/final --out /đường/dẫn/mới [--verify /.../merged]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

RUNS_V1 = ["stage1-chain", "stage1-abl", "stage1-abl-l3", "stage1-abl-l1alias",
           "stage2-main", "stage2-ext", "stage2-abl", "stage2-abl-l3", "stage2-l1alias"]
ALIAS_V1 = {"stage1-abl-l1alias": ("stage1-chain", {"train", "benign"}),
            "stage2-l1alias": ("stage2-main", {"holdout", "test_indist"})}
# v2 (results/v2/PROTOCOL.md): chỉ các lần chạy của nhóm; email LLMail phân tích riêng (analysis/ext2_report.py)
RUNS_V2 = ["stage1b-chain", "stage1b-abl-l1alias",
           "stage2b-main", "stage2b-abl", "stage2b-abl-l3", "stage2b-l1alias"]
ALIAS_V2 = {"stage1b-abl-l1alias": ("stage1b-chain", {"train", "benign"}),
            "stage2b-l1alias": ("stage2b-main", {"holdout", "test_indist"})}
RUNS, ALIAS_SOURCES = RUNS_V1, ALIAS_V1


def read_rows(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        return list(rd.fieldnames or []), list(rd)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]


def alias_rows(final: Path, alias: str) -> tuple[list[dict], list[dict]]:
    src, splits = ALIAS_SOURCES[alias]
    _, rows = read_rows(final / src / "results.csv")
    outs = read_jsonl(final / src / "outputs.jsonl")
    keep = {(r["prompt_id"], r["sample_idx"]) for r in rows
            if r["config"] == "L1" and r["sample_idx"] == "0" and r["split"] in splits}
    new_rows = [{**r, "config": "only_L1", "run_id": alias} for r in rows
                if r["config"] == "L1" and r["sample_idx"] == "0" and r["split"] in splits]
    new_outs = [{**o, "config": "only_L1", "run_id": alias} for o in outs
                if o["config"] == "L1" and str(o["sample_idx"]) == "0" and (o["prompt_id"], "0") in keep]
    return new_rows, new_outs


def merge(final: Path) -> tuple[list[str], list[dict], list[dict]]:
    rows: list[dict] = []
    outs: list[dict] = []
    fields: list[str] = []
    for run in RUNS:
        if run in ALIAS_SOURCES:
            r, o = alias_rows(final, run)
        else:
            fields, r = read_rows(final / run / "results.csv")
            o = read_jsonl(final / run / "outputs.jsonl")
        rows += r
        outs += o
    return fields, rows, outs


def canon(rows: list[dict], key: list[str]) -> list[tuple]:
    return sorted(tuple((k, str(r.get(k, "") or "")) for k in sorted(r)) for r in rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--final-dir", type=Path, required=True, help="thư mục results/final chứa các thư mục chạy")
    ap.add_argument("--out", type=Path, required=True, help="thư mục ghi results.csv và outputs.jsonl")
    ap.add_argument("--v2", action="store_true", help="dùng danh sách lần chạy của giao thức v2")
    ap.add_argument("--verify", type=Path, help="thư mục merged có sẵn để so nội dung (không ghi đè)")
    args = ap.parse_args(argv)
    if args.v2:
        global RUNS, ALIAS_SOURCES
        RUNS, ALIAS_SOURCES = RUNS_V2, ALIAS_V2
    fields, rows, outs = merge(args.final_dir)
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "results.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    with (args.out / "outputs.jsonl").open("w", encoding="utf-8") as f:
        for o in outs:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    print(f"ghi {args.out}: {len(rows)} dòng results, {len(outs)} bản ghi outputs")
    if args.verify:
        _, ref = read_rows(args.verify / "results.csv")
        ok_rows = canon(rows, []) == canon(ref, [])
        ref_out = read_jsonl(args.verify / "outputs.jsonl")
        key = lambda o: (o["config"], o["prompt_id"], int(o["sample_idx"]), o.get("response"))  # noqa: E731
        ok_out = sorted(map(key, outs)) == sorted(map(key, ref_out))
        print(f"so với {args.verify}: results.csv {'GIỐNG' if ok_rows else 'KHÁC'}; outputs.jsonl {'GIỐNG' if ok_out else 'KHÁC'}")
        return 0 if ok_rows and ok_out else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
