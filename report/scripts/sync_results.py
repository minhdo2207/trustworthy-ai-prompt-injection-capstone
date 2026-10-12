#!/usr/bin/env python3
"""Chuyển đầu ra của `analysis/stats.py` thành các tệp mà báo cáo `\\input` (tên ổn định).

Không tính lại số liệu: mọi con số đọc nguyên từ `<analysis>/csv/*.csv` và `<analysis>/dat/*.dat`;
script chỉ chọn cột, định dạng gọn (dấu phẩy thập phân, khoảng trong ngoặc vuông) và đổi tên.
Bảng sinh ra chỉ chứa môi trường `tabular` (booktabs); chú thích nằm trong báo cáo.

Dùng (từ thư mục gốc repo):
  python3 report/scripts/sync_results.py --analysis results/<run>/analysis \\
      --results-csv results/<run>/results.csv --benign-meta attack_prompts/benign_prompts.json --boot-b 2000

Sinh: report/tables/{asr_by_config_split,by_attack_type,cumulative,ablation,benign,cost,
generalization_gap,dead_prompts,numbers}.tex và report/results_dat/{cumulative,tradeoff}.dat.
Bảng nào thiếu dữ liệu nguồn thì bị bỏ qua (báo cáo sẽ hiện khung CHƯA CÓ SỐ LIỆU).
Không đọc `holdout_prompts.json`; chỉ đọc kết quả đã chạy.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path

REPORT_DIR = Path(__file__).resolve().parents[1]
CHAIN = ["baseline", "L1", "L1+L2", "L1+L2+L3", "L1+L2+L3+L4"]
SPLITS = ["train", "test_indist", "holdout"]
SPLIT_VI = {"train": "train", "test_indist": "test\\_indist", "holdout": "hold-out", "all": "tất cả"}
TEX_ESC = {"_": r"\_", "&": r"\&", "%": r"\%", "#": r"\#"}
NA = "---"


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def num(x: str | None) -> float | None:
    if x is None or x == "" or x.lower() in ("nan", "none"):
        return None
    try:
        v = float(x)
    except ValueError:
        return None
    return None if math.isnan(v) else v


def esc(s: str) -> str:
    return "".join(TEX_ESC.get(c, c) for c in s)


def pct(x: float | None, digits: int = 1) -> str:
    return NA if x is None else f"{100 * x:.{digits}f}".replace(".", ",")


def val(x: float | None, digits: int = 1) -> str:
    return NA if x is None else f"{x:.{digits}f}".replace(".", ",")


def cell_ci(p: float | None, lo: float | None, hi: float | None) -> str:
    if p is None:
        return NA
    ci = "" if lo is None or hi is None else f" [{pct(lo)}; {pct(hi)}]"
    return pct(p) + ci


def pp(d: float | None, lo: float | None, hi: float | None) -> str:
    """Hiệu hai tỉ lệ, điểm phần trăm có dấu, kèm khoảng nếu có."""
    if d is None:
        return NA
    sign = lambda v: ("+" if v > 0 else "") + pct(v)  # noqa: E731
    ci = "" if lo is None or hi is None else f" [{sign(lo)}; {sign(hi)}]"
    return sign(d) + ci


def tabular(spec: str, header: list[str], rows: list[list[str] | str]) -> str:
    """`rows` chứa danh sách ô, hoặc chuỗi "MID" để chèn \\midrule."""
    lines = ["% Sinh tự động bởi scripts/sync_results.py từ đầu ra analysis.stats; không sửa tay.",
             r"\begin{tabular}{" + spec + "}", r"\toprule", " & ".join(header) + r" \\", r"\midrule"]
    for r in rows:
        if r == "MID":
            lines.append(r"\midrule")
        elif isinstance(r, str):
            lines.append(r)
        else:
            lines.append(" & ".join(r) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines) + "\n"


def final_config(configs: set[str]) -> str | None:
    for c in reversed(CHAIN):
        if c in configs:
            return c
    return None


def chain_rows(rows: list[dict], split: str) -> dict[str, dict]:
    return {r["config"]: r for r in rows if r["split"] == split and r["config"] in CHAIN}


# ---------------------------------------------------------------- bảng
def t_asr_by_config_split(a: Path) -> str | None:
    rows = read_csv(a / "csv" / "tab01_asr_split.csv")
    out: list[list[str] | str] = []
    for split in SPLITS:
        sub = chain_rows(rows, split)
        if not sub:
            continue
        if out:
            out.append("MID")
        for cfg in CHAIN:
            r = sub.get(cfg)
            if r is None:
                continue
            out.append([SPLIT_VI[split], esc(cfg), r["n_prompts"], r["n_runs"],
                        cell_ci(num(r["asr"]), num(r["wilson_lo"]), num(r["wilson_hi"])),
                        cell_ci(num(r["asr_prompt"]), num(r["boot_lo"]), num(r["boot_hi"]))])
    if not out:
        return None
    return tabular("llrrll", ["Tập", "Cấu hình", "Prompt", "Lượt", "ASR theo lượt, Wilson 95\\%",
                              "ASR theo prompt, bootstrap 95\\%"], out)


def t_by_attack_type(a: Path) -> str | None:
    rows = [r for r in read_csv(a / "csv" / "tab02_asr_attack_type.csv") if r["dimension"] == "attack_type"]
    if not rows:
        return None
    present = [s for s in SPLITS if any(r["split"] == s for r in rows)]
    fin = final_config({r["config"] for r in rows})
    types = list(dict.fromkeys(r["value"] for r in rows))
    out = []
    for t in types:
        line = [esc(t)]
        for s in present:
            sel = {r["config"]: r for r in rows if r["split"] == s and r["value"] == t}
            base, last = sel.get("baseline"), sel.get(fin or "")
            line += [base["n_prompts"] if base else NA, pct(num(base["asr_prompt"])) if base else NA,
                     pct(num(last["asr_prompt"])) if last else NA]
        out.append(line)
    header = ["Loại tấn công"]
    for s in present:
        header += [f"{SPLIT_VI[s]}: $n$", "baseline", esc(fin or "cuối")]
    return tabular("l" + "rrr" * len(present), header, out)


def t_cumulative(a: Path) -> str | None:
    rows = read_csv(a / "csv" / "tab03_cumulative.csv")
    tr, ho = chain_rows(rows, "train"), chain_rows(rows, "holdout")
    if not tr and not ho:
        return None
    out = []
    for cfg in CHAIN:
        line = [esc(cfg)]
        for sub in (tr, ho):
            r = sub.get(cfg)
            line += ([cell_ci(num(r["asr_prompt"]), num(r["boot_lo"]), num(r["boot_hi"])),
                      pp(num(r["red_abs_prev"]), num(r["red_abs_prev_lo"]), num(r["red_abs_prev_hi"]))]
                     if r else [NA, NA])
        out.append(line)
    return tabular("lllll", ["Cấu hình", "train: ASR", "train: giảm so với bước trước (pp)",
                             "hold-out: ASR", "hold-out: giảm so với bước trước (pp)"], out)


def t_ablation(a: Path) -> str | None:
    rows = read_csv(a / "csv" / "tab04_ablation.csv")
    if not rows:
        return None
    cfgs = list(dict.fromkeys(r["config"] for r in rows))
    out = []
    for cfg in cfgs:
        line = [esc(cfg)]
        for s in ("train", "holdout"):
            r = next((x for x in rows if x["split"] == s and x["config"] == cfg), None)
            line += ([cell_ci(num(r["asr_prompt"]), num(r["boot_lo"]), num(r["boot_hi"])),
                      pp(num(r["red_abs_base"]), num(r["red_abs_base_lo"]), num(r["red_abs_base_hi"]))]
                     if r else [NA, NA])
        out.append(line)
    return tabular("lllll", ["Cấu hình", "train: ASR", "train: giảm so với baseline (pp)",
                             "hold-out: ASR", "hold-out: giảm so với baseline (pp)"], out)


def t_benign(a: Path) -> str | None:
    rows = read_csv(a / "csv" / "tab05_benign.csv")
    if not rows:
        return None
    layers = {r["config"]: r for r in read_csv(a / "csv" / "tab07_layers.csv") if r["population"] == "benign"}
    out = []
    for r in rows:
        if r["config"] not in CHAIN:
            continue
        ly = layers.get(r["config"], {})
        out.append([esc(r["config"]), r["n_prompts"],
                    cell_ci(num(r["fpr_prompt"]), num(r["fpr_boot_lo"]), num(r["fpr_boot_hi"])),
                    pct(num(ly.get("rate_L1", ""))), pct(num(ly.get("rate_L2", ""))),
                    pct(num(ly.get("rate_L4", ""))), pct(num(r["model_refused_rate"])),
                    val(num(r["utility"]), 3), val(num(r["utility_unblocked"]), 3)])
    return tabular("lrlrrrrrr", ["Cấu hình", "Prompt", "Từ chối oan, bootstrap 95\\% (\\%)", "L1 chặn", "L2 chặn",
                                 "L4 chặn", "Model từ chối", "Utility", "Utility (không chặn)"], out) if out else None


def t_cost(a: Path) -> str | None:
    rows = [r for r in read_csv(a / "csv" / "tab06_cost.csv") if r["population"] == "all"]
    if not rows:
        return None
    out = [[esc(r["config"]), val(num(r["calls_mean"]), 2), val(num(r["lat_mean"]), 0), val(num(r["lat_p95"]), 0),
            val(num(r["layers_mean"]), 0), val(num(r["ratio_calls"]), 2) + "$\\times$",
            val(num(r["ratio_lat_mean"]), 2) + "$\\times$"] for r in rows if r["config"] in CHAIN]
    return tabular("lrrrrrr", ["Cấu hình", "Số lần gọi", "Độ trễ TB (ms)", "p95 (ms)", "Riêng các lớp (ms)",
                               "Số lần gọi tương đối", "Độ trễ tương đối"], out) if out else None


def t_generalization(a: Path) -> str | None:
    rows = read_csv(a / "csv" / "tab08_generalization.csv")
    if not rows:
        return None
    out = []
    for cfg in CHAIN:
        line = [esc(cfg)]
        ref = next((r for r in rows if r["config"] == cfg), None)
        line.append(pct(num(ref["asr_from"])) if ref else NA)
        for to in ("holdout", "test_indist"):
            r = next((x for x in rows if x["config"] == cfg and x["to_split"] == to), None)
            line += ([pct(num(r["asr_to"])), pp(num(r["gap"]), num(r["gap_lo"]), num(r["gap_hi"]))]
                     if r else [NA, NA])
        out.append(line)
    return tabular("llllll", ["Cấu hình", "train: ASR", "hold-out: ASR", "$\\Delta_{\\mathrm{gen}}$ hold-out (pp)",
                              "test\\_indist: ASR", "$\\Delta_{\\mathrm{gen}}$ test\\_indist (pp)"], out)


def t_dead(a: Path) -> str | None:
    rows = read_csv(a / "csv" / "tab09a_dead_summary.csv")
    eff = read_csv(a / "csv" / "tab09c_effective_asr.csv")
    if not rows:
        return None
    out: list[list[str] | str] = []
    for s in ("train", "holdout"):
        for r in rows:
            if r["split"] == s and r["dimension"] in ("tổng", "attack_type"):
                out.append([SPLIT_VI[s], esc(r["value"]), r["n_prompts"], r["n_dead"], pct(num(r["dead_rate"]))])
    fin = final_config({r["config"] for r in eff})
    extra = [[SPLIT_VI[r["split"]], esc(r["config"]), r["n_alive_prompts"],
              cell_ci(num(r["asr_prompt"]), num(r["boot_lo"]), num(r["boot_hi"])),
              pct(num(r["asr_prompt_unconditional"]))]
             for r in eff if r["config"] in ("baseline", fin) and r["split"] in ("train", "holdout")]
    if extra:
        out += ["MID", r"\multicolumn{5}{l}{\textit{ASR hiệu dụng: chỉ tính trên các prompt còn sống}} \\",
                ["\\textbf{Tập}", "\\textbf{Cấu hình}", "\\textbf{Còn sống}", "\\textbf{ASR [bootstrap 95\\%]}",
                 "\\textbf{ASR toàn bộ}"], *extra]
    return tabular("llrrr", ["Tập", "Nhóm", "Prompt", "Prompt chết", "Tỉ lệ chết (\\%)"], out)


# ---------------------------------------------------------------- dat
def read_dat(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = [ln.split() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    return [dict(zip(lines[0], ln)) for ln in lines[1:]]


def dat_cumulative(a: Path) -> str | None:
    tr = {r["config"]: r for r in read_dat(a / "dat" / "asr_train.dat")}
    ho = {r["config"]: r for r in read_dat(a / "dat" / "asr_holdout.dat")}
    if not tr and not ho:
        return None
    lines = ["idx tr tr_m tr_p ho ho_m ho_p"]
    for i, cfg in enumerate(CHAIN):
        parts = [str(i)]
        for src in (tr, ho):
            r = src.get(cfg)
            parts += ([r["asr_prompt"], r["b_minus"], r["b_plus"]] if r else ["nan", "nan", "nan"])
        lines.append(" ".join(parts))
    return "\n".join(lines) + "\n"


def dat_tradeoff(a: Path) -> str | None:
    ho = {r["config"]: r for r in read_dat(a / "dat" / "asr_holdout.dat")}
    lat = {r["config"]: r for r in read_dat(a / "dat" / "latency_all.dat")}
    cfgs = [c for c in CHAIN if c in ho and c in lat]
    if not cfgs:
        return None
    return "cfg rho_T asr_ho\n" + "\n".join(f"{c} {lat[c]['ratio_mean']} {ho[c]['asr_prompt']}" for c in cfgs) + "\n"


# ---------------------------------------------------------------- số trong văn bản
def numbers_tex(results_csv: Path | None, benign_meta: Path | None, boot_b: int | None) -> str | None:
    setters: list[str] = []
    if results_csv and results_csv.exists():
        rows = read_csv(results_csv)
        prompts: dict[str, set[str]] = {}
        for r in rows:
            if r["label"] == "attack":
                prompts.setdefault(r["split"], set()).add(r["prompt_id"])
        for split, key in (("train", "nTrain"), ("test_indist", "nIndist"), ("holdout", "nHoldout")):
            if split in prompts:
                setters.append(f"\\setnum{{{key}}}{{{len(prompts[split])}}}")
        idx = [int(r["sample_idx"]) for r in rows if r["sample_idx"].isdigit()]
        if idx:
            setters.append(f"\\setnum{{nSamples}}{{{max(idx) + 1}}}")
        temps = Counter(r["temperature"] for r in rows if num(r["temperature"]) not in (None, 0.0))
        if temps:
            setters.append("\\setnum{tempMain}{" + temps.most_common(1)[0][0].replace(".", "{,}") + "}")
    if benign_meta and benign_meta.exists():
        meta = json.loads(benign_meta.read_text(encoding="utf-8"))
        flags = [bool(m.get("tune")) for m in meta if isinstance(m, dict)]
        if flags:
            setters.append(f"\\setnum{{nBenignTune}}{{{sum(flags)}}}")
            setters.append(f"\\setnum{{nBenignTest}}{{{len(flags) - sum(flags)}}}")
    if boot_b:
        setters.append(f"\\setnum{{bootB}}{{{boot_b}}}")
    if not setters:
        return None
    return "% Sinh tự động bởi scripts/sync_results.py; không sửa tay.\n" + "\n".join(setters) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--analysis", type=Path, required=True, help="thư mục đầu ra của analysis.stats")
    ap.add_argument("--results-csv", type=Path)
    ap.add_argument("--benign-meta", type=Path, help="benign_prompts.json (đếm tune/test)")
    ap.add_argument("--boot-b", type=int, help="số lần bootstrap đã dùng (mặc định của stats.py là 2000)")
    ap.add_argument("--out-dir", type=Path, default=REPORT_DIR)
    args = ap.parse_args(argv)

    a = args.analysis
    jobs = {
        "tables/asr_by_config_split.tex": t_asr_by_config_split(a),
        "tables/by_attack_type.tex": t_by_attack_type(a),
        "tables/cumulative.tex": t_cumulative(a),
        "tables/ablation.tex": t_ablation(a),
        "tables/benign.tex": t_benign(a),
        "tables/cost.tex": t_cost(a),
        "tables/generalization_gap.tex": t_generalization(a),
        "tables/dead_prompts.tex": t_dead(a),
        "tables/numbers.tex": numbers_tex(args.results_csv, args.benign_meta, args.boot_b),
        "results_dat/cumulative.dat": dat_cumulative(a),
        "results_dat/tradeoff.dat": dat_tradeoff(a),
    }
    for rel, text in jobs.items():
        path = args.out_dir / rel
        if text is None:
            print(f"bỏ qua {rel} (thiếu dữ liệu nguồn)")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"ghi {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
