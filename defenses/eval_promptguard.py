#!/usr/bin/env python3
"""defenses/eval_promptguard.py — L2 bằng Llama Prompt Guard 2 (P3), so với LLM-judge đã đóng băng.

Thí nghiệm BỔ SUNG (Ngọc), không thay cấu hình chính. Không gọi Qwen3-8B: Prompt Guard 2 chỉ là bộ lọc
đứng trước model, nên khi nó cho qua thì lượt sinh (gần như) giống lượt sinh đã có của cấu hình tương ứng trong
``results/final/merged/results.csv`` (harness dùng seed suy từ prompt và lượt lấy mẫu, L2 không sửa tài liệu). Kiểm tra trên kết quả
đã chạy: attack_success khớp 27/28, model_refused 364/364, utility chỉ 233/364 -> utility phản thực chỉ tham khảo.
Do đó:

- ``only_PG2``  = các lượt ``baseline``, lượt nào PG2 chặn tài liệu gốc thì tính bị chặn.
- ``L1+PG2``    = các lượt ``L1``, lượt nào L1 cho qua mà PG2 chặn tài liệu SAU L1 thì tính bị chặn.
- ``L1+PG2+L3`` chỉ tính được cận: lượt ``L1+L2+L3`` mà judge đã chặn nhưng PG2 cho qua thì không có lượt sinh
  (cận dưới coi là thất bại, cận trên coi là thành công).

Hai bước, đúng quy tắc CONTRIBUTING mục 6:
  1. ``calibrate``: chọn ngưỡng CHỈ trên train + benign ``tune`` (tài liệu gốc, cùng tiêu chí với judge:
     TPR lớn nhất với FPR <= 10%). Ghi ngưỡng vào ``PG_THRESHOLDS`` trong layer2 rồi commit.
  2. ``final``: chạy MỘT lần trên mọi split (gồm hold-out, dữ liệu ngoài) với ngưỡng đã cố định.

Ví dụ:
  CAPSTONE_PROMPTGUARD_PATH=models/Llama-Prompt-Guard-2-86M python -m defenses.eval_promptguard calibrate
  CAPSTONE_PROMPTGUARD_PATH=models/Llama-Prompt-Guard-2-86M python -m defenses.eval_promptguard final
Đầu ra: ``results/promptguard/<tên model>/`` (items.csv, asr.csv, detection.csv, report.md, meta.json).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

from analysis.intervals import wilson  # noqa: E402
from defenses import layer1_filtering as L1  # noqa: E402
from defenses import layer2_refusal_classifier as L2  # noqa: E402

DATA = ROOT / "attack_prompts"
MERGED = ROOT / "results" / "final" / "merged" / "results.csv"
SPLITS = {"train": "train_prompts.json", "benign": "benign_prompts.json", "holdout": "holdout_prompts.json",
          "test_indist": "test_indist_prompts.json", "ext_attack": "ext_attack_prompts.json",
          "ext_benign": "ext_benign_prompts.json"}
CALIB_SPLITS = ("train", "benign")


def load(split: str) -> list[dict]:
    items = json.loads((DATA / SPLITS[split]).read_text(encoding="utf-8"))
    for it in items:
        it["_split"] = split
    return items


def score_items(items: list[dict], with_l1: bool) -> list[dict]:
    """Điểm PG2 trên tài liệu gốc (``raw``) và, nếu cần, trên tài liệu sau L1 (``l1``)."""
    rows = []
    for it in items:
        doc, task = it["untrusted_document"], it["user_task"]
        t0 = time.perf_counter()
        s_raw, d = L2.score_document(task, doc)
        row = {"id": it["id"], "split": it["_split"], "label": it["label"],
               "attack_type": it.get("attack_type", "none"), "tune": bool(it.get("tune", False)),
               "pg_raw": round(s_raw, 6), "windows": d["chunks"], "pg_ms": round((time.perf_counter() - t0) * 1000, 1)}
        if with_l1:
            r1 = L1.check(task, doc)
            row["l1_action"] = r1.action
            if r1.action == "block":
                row["pg_l1"] = None
            elif r1.action == "sanitize":
                row["pg_l1"] = round(L2.score_document(task, r1.document)[0], 6)
            else:
                row["pg_l1"] = row["pg_raw"]
        rows.append(row)
    return rows


def calibrate(args) -> int:
    from defenses._data import load_benign_tune, load_train_attacks
    attacks = load_train_attacks(DATA / SPLITS["train"])
    benign, from_fixture = load_benign_tune(DATA / SPLITS["benign"])
    assert not from_fixture, "cần benign_prompts.json thật"
    pos = [L2.score_document(s.user_task, s.document)[0] for s in attacks]
    neg = [L2.score_document(s.user_task, s.document)[0] for s in benign]
    a = L2.auc(pos, neg)
    lo, hi = L2.bootstrap_auc_ci(pos, neg)
    # Điểm liên tục: cắt ngay trên điểm benign cao nhất còn cho phép (FPR <= 10%), làm tròn xuống 4 chữ số.
    ch = L2.choose_threshold(pos, neg, max_fpr=0.10)
    cut = ch["cut_score"]
    below = [x for x in sorted(set(pos) | set(neg)) if x < cut]
    thr = float(f"{(cut + (below[-1] if below else 0.0)) / 2:.4f}")
    tpr, fpr = L2.rates_at(pos, neg, thr)
    kp, kn = round(tpr * len(pos)), round(fpr * len(neg))
    out = {"date": datetime.now(timezone.utc).date().isoformat(), "model": Path(os.environ["CAPSTONE_PROMPTGUARD_PATH"]).name,
           "n_attack_train": len(pos), "n_benign_tune": len(neg), "auc": round(a, 4), "auc_ci": [round(lo, 4), round(hi, 4)],
           "threshold": thr, "tpr": [kp, len(pos), *map(lambda x: round(x, 3), wilson(kp, len(pos)))],
           "fpr": [kn, len(neg), *map(lambda x: round(x, 3), wilson(kn, len(neg)))],
           "youden_cut": round(ch["youden_cut"], 4), "youden_j": round(ch["youden_j"], 4),
           "tpr_at_0.5": L2.rates_at(pos, neg, 0.5)[0], "fpr_at_0.5": L2.rates_at(pos, neg, 0.5)[1],
           "per_attack_type": {}}
    for s, sc in zip(attacks, pos):
        t = out["per_attack_type"].setdefault(s.attack_type, [0, 0])
        t[0] += sc >= thr
        t[1] += 1
    out["benign_over_threshold"] = [s.id for s, sc in zip(benign, neg) if sc >= thr]
    # Điểm vận hành thứ hai, chốt cùng lúc: ngưỡng nghiêm FPR = 0 trên tune (để so với judge, judge có FPR 0/42).
    above = [x for x in pos if x > max(neg)]
    strict = float(f"{(max(neg) + min(above)) / 2:.6f}") if above else max(neg) + 1e-6
    ks = sum(x >= strict for x in pos)
    out["threshold_strict"] = strict
    out["tpr_strict"] = [ks, len(pos), *map(lambda x: round(x, 3), wilson(ks, len(pos)))]
    print(json.dumps(out, ensure_ascii=False, indent=1))
    od = args.out / out["model"]
    od.mkdir(parents=True, exist_ok=True)
    (od / "calibration.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


# --------------------------------------------------------------------------- final

def _asr_rows(merged: pd.DataFrame, items: pd.DataFrame, thr: float) -> pd.DataFrame:
    """ASR (lượt) và từ chối oan cho baseline / L1 / judge thật / PG2 phản thực."""
    blk_raw = dict(zip(items.id, items.pg_raw >= thr))
    blk_l1 = dict(zip(items.id, items.pg_l1.fillna(-1) >= thr))
    out = []

    def add(split, name, df, extra_block=None, bounds=None):
        df = df.copy()
        df["blocked"] = df.blocked.astype(bool)
        df["model_refused"] = df.model_refused.fillna(False).astype(bool)
        if extra_block is not None:
            hit = (~df.blocked.astype(bool)) & df.prompt_id.map(extra_block).fillna(False).astype(bool)
            df.loc[hit, "blocked"] = True
            df.loc[hit, "attack_success"] = df.loc[hit, "attack_success"].where(df.loc[hit, "attack_success"].isna(), 0.0)
            df.loc[hit, "utility_score"] = 0.0
            df.loc[hit, "model_refused"] = False
        lab = df.label.iloc[0]
        rec = {"split": split, "config": name, "n_rows": len(df), "n_prompts": df.prompt_id.nunique(),
               "blocked_pct": 100 * df.blocked.astype(bool).mean()}
        if lab == "attack":
            sc = df.dropna(subset=["attack_success"])
            k, n = int(sc.attack_success.sum()), len(sc)
            lo, hi = wilson(k, n) if n else (float("nan"), float("nan"))
            rec.update(asr_pct=100 * k / n if n else float("nan"), asr_lo=100 * lo, asr_hi=100 * hi, k=k, n=n)
            if bounds is not None:
                rec.update(asr_lower=bounds[0], asr_upper=bounds[1])
        else:
            ref = df.blocked.astype(bool) | df.model_refused.fillna(False).astype(bool)
            k, n = int(ref.sum()), len(df)
            lo, hi = wilson(k, n)
            rec.update(refusal_pct=100 * k / n, ref_lo=100 * lo, ref_hi=100 * hi, k=k, n=n,
                       utility=df.utility_score.fillna(0).mean())
        out.append(rec)

    main = merged[merged.run_id.isin(["benign-baseline", "stage1-chain", "stage2-main", "stage2-ext"])]
    abl = merged[merged.config == "only_L2"]
    for split in ["train", "holdout", "test_indist", "benign", "ext_attack", "ext_benign"]:
        m = main[main.split == split]
        if split == "benign":
            m = m[~m.prompt_id.map(dict(zip(items.id, items.tune))).fillna(False).astype(bool)]
            abl_s = abl[(abl.split == "benign") & ~abl.prompt_id.map(dict(zip(items.id, items.tune))).fillna(False).astype(bool)]
        else:
            abl_s = abl[abl.split == split]
        base = m[m.config == "baseline"]
        l1 = m[m.config == "L1"]
        if base.empty:
            continue
        add(split, "baseline", base)
        if not abl_s.empty:
            add(split, "only_L2 (judge, đã chạy)", abl_s)
        add(split, "only_PG2 (phản thực)", base, extra_block=blk_raw)
        add(split, "L1", l1)
        add(split, "L1+L2 (judge, đã chạy)", m[m.config == "L1+L2"])
        add(split, "L1+PG2 (phản thực)", l1, extra_block=blk_l1)
        l3 = m[m.config == "L1+L2+L3"].copy()
        if not l3.empty:
            # lượt judge chặn nhưng PG2 cho qua: không có lượt sinh với L3 -> chỉ có cận
            unknown = (l3.blocked_by == "L2") & ~l3.prompt_id.map(blk_l1).fillna(False).astype(bool)
            l3b = l3.copy()
            l3b["blocked"] = l3b.blocked.astype(bool)
            l3b.loc[l3b.blocked_by == "L2", "blocked"] = False      # judge không còn trong chuỗi
            if l3.label.iloc[0] == "attack":
                sc_lo = l3b.copy(); sc_lo.loc[unknown, "attack_success"] = sc_lo.loc[unknown, "attack_success"].where(sc_lo.loc[unknown, "attack_success"].isna(), 0.0)
                sc_hi = l3b.copy(); sc_hi.loc[unknown, "attack_success"] = sc_hi.loc[unknown, "attack_success"].where(sc_hi.loc[unknown, "attack_success"].isna(), 1.0)
                pg = l3b.prompt_id.map(blk_l1).fillna(False).astype(bool) & ~l3b.blocked.astype(bool)
                for x in (sc_lo, sc_hi):
                    x.loc[pg, "attack_success"] = x.loc[pg, "attack_success"].where(x.loc[pg, "attack_success"].isna(), 0.0)
                def asr(x):
                    s = x.dropna(subset=["attack_success"])
                    return 100 * s.attack_success.mean() if len(s) else float("nan")
                out.append({"split": split, "config": "L1+PG2+L3 (cận)", "n_rows": len(l3), "n_prompts": l3.prompt_id.nunique(),
                            "asr_lower": asr(sc_lo), "asr_upper": asr(sc_hi), "unknown_rows": int(unknown.sum())})
    return pd.DataFrame(out)


def _detection(items: pd.DataFrame, merged: pd.DataFrame, thr: float) -> pd.DataFrame:
    """TPR/FPR theo prompt: PG2 trên tài liệu gốc so với judge only_L2 (đã chạy) trên cùng prompt."""
    judge = (merged[merged.config == "only_L2"].groupby("prompt_id").blocked.max().astype(bool).to_dict())
    judge_chain = (merged[(merged.config == "L1+L2")].assign(b=lambda x: x.blocked_by == "L2")
                   .groupby("prompt_id").b.max().to_dict())
    rows = []
    groups = [("train", None), ("holdout", None), ("test_indist", None), ("ext_attack", None)]
    for split, _ in groups:
        sub = items[(items.split == split) & (items.label == "attack")]
        for key, g in [("all", sub)] + list(sub.groupby("attack_type")):
            rec = {"split": split, "label": "attack", "group": key, "n": len(g)}
            k = int((g.pg_raw >= thr).sum())
            rec.update(pg2_rate=100 * k / len(g), pg2_k=k)
            js = g.id.map(judge).dropna()
            if len(js):
                rec.update(judge_rate=100 * js.mean(), judge_n=len(js))
            l1p = g[g.l1_action != "block"]
            if len(l1p):
                rec.update(after_l1_n=len(l1p), pg2_after_l1=int((l1p.pg_l1 >= thr).sum()),
                           judge_after_l1=int(l1p.id.map(judge_chain).fillna(False).sum()))
            rows.append(rec)
    for split, cond in [("benign (tune=false)", (items.split == "benign") & ~items.tune),
                        ("benign (tune=true)", (items.split == "benign") & items.tune),
                        ("ext_benign", items.split == "ext_benign")]:
        g = items[cond]
        k = int((g.pg_raw >= thr).sum())
        rec = {"split": split, "label": "benign", "group": "all", "n": len(g), "pg2_rate": 100 * k / len(g), "pg2_k": k}
        js = g.id.map(judge).dropna()
        if len(js):
            rec.update(judge_rate=100 * js.mean(), judge_n=len(js))
        rows.append(rec)
    return pd.DataFrame(rows)


def final(args) -> int:
    name = Path(os.environ["CAPSTONE_PROMPTGUARD_PATH"]).name
    if name not in L2.PG_THRESHOLDS and not args.allow_uncalibrated:
        print(f"{name} chưa có trong PG_THRESHOLDS: chạy 'calibrate', ghi ngưỡng vào layer2 và commit trước.", file=sys.stderr)
        return 2
    thr = L2.threshold_for("promptguard")
    note = L2.PG_CALIBRATION_NOTES.get(name, "chưa hiệu chỉnh")
    od = args.out / name
    od.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    if args.from_items:
        # chỉ dựng lại bảng từ điểm đã chấm (không chấm lại hold-out)
        it = pd.read_csv(od / "items.csv")
        it["tune"] = it.tune.astype(bool)
    else:
        items = []
        for split in SPLITS:
            items += score_items(load(split), with_l1=True)
        it = pd.DataFrame(items)
        it.to_csv(od / "items.csv", index=False)
    wall = time.perf_counter() - t0
    merged = pd.read_csv(MERGED)
    strict = L2.PG_THRESHOLDS_STRICT.get(name)
    ops = [("FPR<=10%", thr)] + ([("FPR=0", strict)] if strict is not None else [])
    asr = pd.concat([_asr_rows(merged, it, t).assign(op=o, threshold=t) for o, t in ops], ignore_index=True)
    det = pd.concat([_detection(it, merged, t).assign(op=o, threshold=t) for o, t in ops], ignore_index=True)
    asr.to_csv(od / "asr.csv", index=False)
    det.to_csv(od / "detection.csv", index=False)
    lat = it.pg_ms.describe(percentiles=[0.5, 0.9]).round(1).to_dict()
    meta = {"created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "model": name,
            "threshold": thr, "threshold_strict": strict, "calibration": note, "stride": L2.PG_STRIDE,
            "git_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
            "n_items": len(it), "wall_s": round(wall, 1), "pg_ms_per_doc": lat,
            "device": "cpu", "note": "chạy MỘT lần với ngưỡng cố định; không chỉnh theo kết quả này"}
    (od / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    fmt = lambda df: df.assign(threshold=df.threshold.map(lambda t: f"{t:g}")).to_markdown(index=False, floatfmt=".1f")  # noqa: E731
    md = [f"# L2 = {name} (thí nghiệm bổ sung)\n", f"Ngưỡng {thr} (FPR<=10%) và {strict} (FPR=0), chọn trên train + benign tune: {note}.",
          f"Thời gian PG2 mỗi tài liệu trên CPU: trung vị {lat['50%']} ms, p90 {lat['90%']} ms.\n",
          "## ASR và từ chối oan\n", fmt(asr), "\n## Phát hiện theo prompt\n", fmt(det)]
    (od / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("stage", choices=["calibrate", "final"])
    ap.add_argument("--out", type=Path, default=ROOT / "results" / "promptguard")
    ap.add_argument("--from-items", action="store_true", help="dựng lại bảng từ items.csv đã có, không chấm lại")
    ap.add_argument("--allow-uncalibrated", action="store_true", help="chỉ để chạy thử")
    args = ap.parse_args(argv)
    os.environ["CAPSTONE_L2_BACKEND"] = "promptguard"
    ok, why = L2.promptguard_available()
    if not ok:
        print(f"Không dùng được Prompt Guard 2: {why}", file=sys.stderr)
        return 2
    return calibrate(args) if args.stage == "calibrate" else final(args)


if __name__ == "__main__":
    sys.exit(main())
