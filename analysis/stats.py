"""Sinh bảng phân tích cho báo cáo từ CSV kết quả (hợp đồng mục 3).

Chạy: python3 -m analysis.stats results/<run>/results.csv [--out results/<run>/analysis]

Quy ước xuyên suốt:
- Chỉ dòng không lỗi (`error` rỗng) được đưa vào mẫu; dòng lỗi chỉ xuất hiện ở Bảng 10.
- "ASR theo lượt" (`asr`) = số thành công / số lượt, đi với khoảng Wilson (lạc quan).
- "ASR theo prompt" (`asr_prompt`) = trung bình ASR của từng prompt, đi với bootstrap theo
  cụm (resample prompt). Mọi hiệu giữa hai cấu hình/split dùng đại lượng này.
"""
from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from analysis.intervals import (DEFAULT_B, DEFAULT_SEED, NAN, bootstrap_diff_ci,
                                bootstrap_mean_ci, wilson)
from analysis.loader import (ATTACK_SPLITS, DEFAULT_ERROR_THRESHOLD, BLOCKING_LAYERS,
                             DataError, Issue, Loaded, load_benign_meta, load_results)
from analysis.render import (Table, md_table, num, pct, pct_ci, ratio, signed, signed_pp,
                             tex_label, write_dat, write_table)

CHAIN = ("baseline", "L1", "L1+L2", "L1+L2+L3", "L1+L2+L3+L4")
ONLY = ("only_L1", "only_L2", "only_L3", "only_L4")
BREAKDOWNS = ("attack_type", "liu_type", "goal_type")
GENERALIZATION_PAIRS = (("train", "holdout"), ("train", "test_indist"), ("test_indist", "holdout"))

__all__ = ["Context", "build_context", "run_analysis", "main", "wilson", "bootstrap_mean_ci",
           "bootstrap_diff_ci"]


# ---------------------------------------------------------------------------
# Ngữ cảnh dùng chung
# ---------------------------------------------------------------------------

def order_configs(configs: list[str]) -> list[str]:
    """Chuỗi cộng dồn trước, rồi only_L*, rồi các config lạ theo bảng chữ cái."""
    known = [c for c in CHAIN + ONLY if c in configs]
    return known + sorted(c for c in configs if c not in known)


def _config_rank(configs: list[str]) -> dict[str, int]:
    return {c: i for i, c in enumerate(order_configs(configs))}


@dataclass
class Context:
    loaded: Loaded
    b: int
    seed: int
    error_threshold: float
    valid: pd.DataFrame
    attack: pd.DataFrame
    benign_all: pd.DataFrame
    benign_eval: pd.DataFrame
    benign_scope: str
    ps: pd.DataFrame
    configs: list[str]
    splits: list[str]
    benign_meta: dict[str, bool | None] | None = None
    extra_issues: list[Issue] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)
    _vec: dict[tuple[str, str], pd.Series] = field(default_factory=dict)

    @property
    def issues(self) -> list[Issue]:
        return self.loaded.issues + self.extra_issues

    def prompt_means(self, config: str, split: str) -> pd.Series:
        """ASR từng prompt (index = prompt_id, đã sắp xếp) của một config trong một split."""
        key = (config, split)
        if key not in self._vec:
            sub = self.ps[(self.ps["config"] == config) & (self.ps["split"] == split)]
            self._vec[key] = pd.Series(sub["asr"].to_numpy(), index=sub["prompt_id"].to_numpy())
        return self._vec[key]


def _prompt_level_attack(attack: pd.DataFrame) -> pd.DataFrame:
    ps = (attack.groupby(["config", "split", "prompt_id"], sort=True)
          .agg(attack_type=("attack_type", "first"), liu_type=("liu_type", "first"),
               technique=("technique", "first"), goal_type=("goal_type", "first"),
               n=("attack_success", "size"), k=("attack_success", "sum"))
          .reset_index())
    ps["n"] = ps["n"].astype(int)
    ps["k"] = ps["k"].astype(int)
    ps["asr"] = ps["k"] / ps["n"]
    return ps


def _prepare_benign(benign: pd.DataFrame) -> pd.DataFrame:
    out = benign.copy()
    blocked = out["blocked"] == 1
    out["refused"] = (blocked | (out["model_refused"] == 1)).astype(int)
    out["blocked_i"] = blocked.astype(int)
    out["model_only"] = ((out["model_refused"] == 1) & ~blocked).astype(int)
    out["util_unblocked"] = out["utility_score"].where(~blocked)
    return out


def build_context(loaded: Loaded, *, b: int = DEFAULT_B, seed: int = DEFAULT_SEED,
                  benign_meta: dict[str, bool | None] | None = None,
                  error_threshold: float = DEFAULT_ERROR_THRESHOLD) -> Context:
    valid = loaded.valid
    attack = valid[valid["label"] == "attack"]
    benign_all = _prepare_benign(valid[valid["label"] == "benign"])
    extra: list[Issue] = []
    benign_eval, scope = benign_all, "tất cả benign (không có --benign-meta nên không loại được phần `tune`)"
    if benign_meta is not None:
        flag = benign_all["prompt_id"].map(lambda i: benign_meta.get(i))
        unknown = sorted(set(benign_all.loc[flag.isna(), "prompt_id"]))
        if unknown:
            extra.append(Issue("warning", "benign_meta_unknown",
                               "prompt benign không có cờ `tune` trong --benign-meta (bị loại khỏi "
                               "bảng benign chính)", len(unknown), unknown[:5]))
        benign_eval = benign_all[flag == False]  # noqa: E712 - flag chứa None/bool
        scope = "chỉ benign `tune:false`"
        if benign_eval.empty and not benign_all.empty:
            raise DataError("--benign-meta không để lại prompt benign `tune:false` nào trong CSV")
    present = set(attack["split"])
    splits = [s for s in ATTACK_SPLITS if s in present] + sorted(present - set(ATTACK_SPLITS))
    ps = _prompt_level_attack(attack) if len(attack) else pd.DataFrame(
        columns=["config", "split", "prompt_id", "attack_type", "liu_type", "technique",
                 "goal_type", "n", "k", "asr"])
    return Context(loaded=loaded, b=b, seed=seed, error_threshold=error_threshold, valid=valid,
                   attack=attack, benign_all=benign_all, benign_eval=benign_eval,
                   benign_scope=scope, ps=ps, configs=order_configs(list(valid["config"].unique())),
                   splits=splits, benign_meta=benign_meta, extra_issues=extra)


# ---------------------------------------------------------------------------
# Tóm tắt tỉ lệ và so sánh
# ---------------------------------------------------------------------------

def rate_summary(k: int, n: int, prompt_means: list[float], ctx: Context) -> dict[str, float]:
    """Tỉ lệ theo lượt (+Wilson) và trung bình theo prompt (+bootstrap theo cụm)."""
    lo, hi = wilson(k, n)
    blo, bhi = bootstrap_mean_ci(prompt_means, b=ctx.b, seed=ctx.seed)
    return {
        "n_runs": n, "n_prompts": len(prompt_means), "n_events": k,
        "rate": k / n if n else NAN, "wilson_lo": lo, "wilson_hi": hi,
        "rate_prompt": sum(prompt_means) / len(prompt_means) if prompt_means else NAN,
        "boot_lo": blo, "boot_hi": bhi,
    }


def asr_summary(sub: pd.DataFrame, ctx: Context) -> dict[str, float]:
    s = rate_summary(int(sub["k"].sum()), int(sub["n"].sum()), sub["asr"].tolist(), ctx)
    return {"n_runs": s["n_runs"], "n_prompts": s["n_prompts"], "n_success": s["n_events"],
            "asr": s["rate"], "wilson_lo": s["wilson_lo"], "wilson_hi": s["wilson_hi"],
            "asr_prompt": s["rate_prompt"], "boot_lo": s["boot_lo"], "boot_hi": s["boot_hi"]}


def paired_diff(ctx: Context, ref: pd.Series, cur: pd.Series, *, paired: bool = True
                ) -> dict[str, float]:
    """ref - cur theo prompt. paired=True: xếp cặp trên phần giao prompt; False: hai tập độc lập."""
    if paired:
        ids = sorted(set(ref.index) & set(cur.index))
        a, c = ref.loc[ids].tolist(), cur.loc[ids].tolist()
    else:
        a, c = ref.tolist(), cur.tolist()
    d, lo, hi = bootstrap_diff_ci(a, c, paired=paired, b=ctx.b, seed=ctx.seed)
    base = sum(a) / len(a) if a else NAN
    rel = d / base if a and base > 0 else NAN
    return {"n_paired": len(ids) if paired else min(len(a), len(c)),
            "diff": d, "lo": lo, "hi": hi, "rel": rel}


def _excludes_zero(lo: float, hi: float) -> bool:
    return not (math.isnan(lo) or math.isnan(hi)) and (lo > 0 or hi < 0)


def _frame(rows: list[dict], columns: list[str] | None = None) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=columns) if rows else pd.DataFrame(columns=columns or [])


# ---------------------------------------------------------------------------
# Bảng 1: ASR theo config x split
# ---------------------------------------------------------------------------

def table_asr_by_split(ctx: Context) -> Table:
    rows = []
    for split in ctx.splits:
        for cfg in ctx.configs:
            sub = ctx.ps[(ctx.ps["config"] == cfg) & (ctx.ps["split"] == split)]
            if sub.empty:
                continue
            rows.append({"split": split, "config": cfg, **asr_summary(sub, ctx)})
    data = _frame(rows)
    disp = pd.DataFrame({
        "Split": data["split"], "Config": data["config"],
        "Lượt": data["n_runs"].astype(int), "Prompt": data["n_prompts"].astype(int),
        "Thành công": data["n_success"].astype(int),
        "ASR lượt (%)": data["asr"].map(pct),
        "Wilson 95% (lạc quan)": [pct_ci(a, b) for a, b in zip(data["wilson_lo"], data["wilson_hi"])],
        "ASR theo prompt (%)": data["asr_prompt"].map(pct),
        "Bootstrap theo prompt 95%": [pct_ci(a, b) for a, b in zip(data["boot_lo"], data["boot_hi"])],
    }) if len(data) else pd.DataFrame()
    return Table(
        "tab01_asr_split", "Bảng 1. ASR theo cấu hình và split", data, disp,
        note=("Wilson coi mọi lượt là độc lập nên *lạc quan* (hẹp) vì các lượt của cùng prompt "
              "tương quan; khoảng bootstrap theo prompt là khoảng nên trích dẫn."),
        group_col="Split", split_col="Split")


# ---------------------------------------------------------------------------
# Bảng 2: ASR theo attack_type / liu_type / goal_type
# ---------------------------------------------------------------------------

def table_asr_breakdown(ctx: Context, dim: str) -> Table:
    scopes = ["all"] + ctx.splits
    rows = []
    for scope in scopes:
        base = ctx.ps if scope == "all" else ctx.ps[ctx.ps["split"] == scope]
        for value in sorted(base[dim].unique()):
            for cfg in ctx.configs:
                sub = base[(base[dim] == value) & (base["config"] == cfg)]
                if sub.empty:
                    continue
                rows.append({"dimension": dim, "split": scope, "value": value, "config": cfg,
                             **asr_summary(sub, ctx)})
    data = _frame(rows)
    names = {"attack_type": "Loại tấn công", "liu_type": "Kiểu Liu", "goal_type": "Mục tiêu"}
    drows = []
    for (split, value), grp in (data.groupby(["split", "value"], sort=False) if len(data) else []):
        cell = {r.config: pct(r.asr) for r in grp.itertuples()}
        drows.append({"Split": split, names[dim]: value,
                      "Prompt": int(grp["n_prompts"].max()),
                      **{c: cell.get(c, "n/a") for c in ctx.configs}})
    return Table(
        f"tab02_asr_{dim}", f"Bảng 2. ASR (%) theo {names[dim].lower()} và cấu hình",
        data, pd.DataFrame(drows),
        note=("`all` = gộp mọi split tấn công (chỉ để mô tả; số chính thức báo cáo theo split). "
              "Ô là ASR theo lượt; khoảng tin cậy nằm trong CSV. Nhóm có ít prompt cho khoảng rất rộng."),
        group_col="Split", split_col="Split")


# ---------------------------------------------------------------------------
# Bảng 3: cộng dồn baseline -> +L1 -> ...
# ---------------------------------------------------------------------------

def _added_layer(cfg: str) -> str:
    return "" if cfg == "baseline" else cfg.split("+")[-1]


def table_cumulative(ctx: Context) -> Table:
    chain = [c for c in CHAIN if c in ctx.configs]
    rows = []
    for split in ctx.splits:
        present = [c for c in chain if not ctx.ps[(ctx.ps["config"] == c) & (ctx.ps["split"] == split)].empty]
        base_vec = ctx.prompt_means("baseline", split) if "baseline" in present else None
        prev = None
        for cfg in present:
            sub = ctx.ps[(ctx.ps["config"] == cfg) & (ctx.ps["split"] == split)]
            cur = ctx.prompt_means(cfg, split)
            row = {"split": split, "config": cfg, "prev_config": prev or "",
                   "added_layer": _added_layer(cfg), **asr_summary(sub, ctx)}
            for tag, ref in (("prev", ctx.prompt_means(prev, split) if prev else None),
                             ("base", base_vec if cfg != "baseline" else None)):
                if ref is None:
                    d = {"n_paired": 0, "diff": NAN, "lo": NAN, "hi": NAN, "rel": NAN}
                else:
                    d = paired_diff(ctx, ref, cur)
                row.update({f"n_paired_{tag}": d["n_paired"], f"red_abs_{tag}": d["diff"],
                            f"red_abs_{tag}_lo": d["lo"], f"red_abs_{tag}_hi": d["hi"],
                            f"red_rel_{tag}": d["rel"]})
            rows.append(row)
            prev = cfg
    data = _frame(rows)
    disp = pd.DataFrame({
        "Split": data["split"], "Config": data["config"], "Lớp thêm": data["added_layer"],
        "Prompt": data["n_prompts"].astype(int),
        "ASR lượt (%)": data["asr"].map(pct),
        "Wilson 95%": [pct_ci(a, b) for a, b in zip(data["wilson_lo"], data["wilson_hi"])],
        "ASR prompt (%)": data["asr_prompt"].map(pct),
        "Bootstrap 95%": [pct_ci(a, b) for a, b in zip(data["boot_lo"], data["boot_hi"])],
        "Giảm vs bước trước (pp)": [_diff_cell(r) for r in _records(data, "prev")],
        "Giảm tương đối vs bước trước (%)": data["red_rel_prev"].map(pct),
        "Giảm vs baseline (pp)": [_diff_cell(r) for r in _records(data, "base")],
        "Giảm tương đối vs baseline (%)": data["red_rel_base"].map(pct),
    }) if len(data) else pd.DataFrame()
    return Table(
        "tab03_cumulative", "Bảng 3. Phòng thủ cộng dồn: baseline -> +L1 -> +L1+L2 -> ...", data, disp,
        note=("Giảm = ASR trước trừ ASR sau, tính theo prompt, điểm phần trăm (pp); dương là tốt. "
              "Khoảng trong ngoặc là bootstrap xếp cặp theo prompt (cùng tập prompt giữa hai cấu hình). "
              "Giảm tương đối = giảm tuyệt đối / ASR của bước đối chiếu."),
        group_col="Split", split_col="Split")


def _records(data: pd.DataFrame, tag: str) -> list[tuple[float, float, float]]:
    return list(zip(data[f"red_abs_{tag}"], data[f"red_abs_{tag}_lo"], data[f"red_abs_{tag}_hi"]))


def _diff_cell(r: tuple[float, float, float], digits: int = 1) -> str:
    d, lo, hi = r
    if math.isnan(d):
        return "-"
    return f"{signed_pp(d, digits)} [{signed_pp(lo, digits)}, {signed_pp(hi, digits)}]"


# ---------------------------------------------------------------------------
# Bảng 4: ablation only_L*
# ---------------------------------------------------------------------------

def table_ablation(ctx: Context, cumulative: Table) -> Table | None:
    only = [c for c in ONLY if c in ctx.configs]
    if not only:
        ctx.skipped["tab04_ablation"] = "không có cấu hình only_L* trong dữ liệu"
        return None
    chain_data = cumulative.data
    full_cfg = next((c for c in reversed(CHAIN[1:]) if c in ctx.configs), None)
    rows, notes = [], []
    for split in ctx.splits:
        have = lambda c: not ctx.ps[(ctx.ps["config"] == c) & (ctx.ps["split"] == split)].empty  # noqa: E731
        if not have("baseline"):
            continue
        base = ctx.prompt_means("baseline", split)
        full_red = NAN
        if full_cfg and have(full_cfg):
            full_red = paired_diff(ctx, base, ctx.prompt_means(full_cfg, split))["diff"]
        solo_sum = 0.0
        entries = [("baseline", "ref", "")] + [(c, "solo", c[-2:]) for c in only if have(c)]
        if full_cfg and have(full_cfg):
            entries.append((full_cfg, "full", ""))
        for cfg, role, layer in entries:
            sub = ctx.ps[(ctx.ps["config"] == cfg) & (ctx.ps["split"] == split)]
            row = {"split": split, "config": cfg, "role": role, "layer": layer, **asr_summary(sub, ctx)}
            if role == "ref":
                d = {"n_paired": 0, "diff": NAN, "lo": NAN, "hi": NAN, "rel": NAN}
            else:
                d = paired_diff(ctx, base, ctx.prompt_means(cfg, split))
            row.update({"red_abs_base": d["diff"], "red_abs_base_lo": d["lo"],
                        "red_abs_base_hi": d["hi"], "red_rel_base": d["rel"]})
            row["share_of_full"] = (d["diff"] / full_red
                                    if role == "solo" and full_red and not math.isnan(full_red)
                                    and full_red > 0 else NAN)
            step = chain_data[(chain_data["split"] == split) & (chain_data["added_layer"] == layer)] \
                if layer else chain_data.iloc[0:0]
            row["chain_red_abs_prev"] = float(step["red_abs_prev"].iloc[0]) if len(step) else NAN
            if role == "solo" and not math.isnan(d["diff"]):
                solo_sum += d["diff"]
            rows.append(row)
        if not math.isnan(full_red):
            notes.append(f"{split}: tổng giảm riêng lẻ của các lớp = {signed_pp(solo_sum)} pp, "
                         f"giảm của chuỗi đầy đủ = {signed_pp(full_red)} pp, chồng lấn/đồng tác động = "
                         f"{signed_pp(solo_sum - full_red)} pp.")
    data = _frame(rows)
    if data.empty:
        ctx.skipped["tab04_ablation"] = "không có baseline để đối chiếu"
        return None
    role_name = {"ref": "đối chiếu", "solo": "chỉ một lớp", "full": "chuỗi đầy đủ"}
    disp = pd.DataFrame({
        "Split": data["split"], "Config": data["config"], "Vai trò": data["role"].map(role_name),
        "ASR prompt (%)": data["asr_prompt"].map(pct),
        "Bootstrap 95%": [pct_ci(a, b) for a, b in zip(data["boot_lo"], data["boot_hi"])],
        "Giảm vs baseline (pp)": [_diff_cell(r) for r in _records(data, "base")],
        "Giảm tương đối (%)": data["red_rel_base"].map(pct),
        "Tỉ phần của chuỗi đầy đủ (%)": data["share_of_full"].map(pct),
        "Giảm biên trong chuỗi (pp)": data["chain_red_abs_prev"].map(signed_pp),
    })
    return Table(
        "tab04_ablation", "Bảng 4. Ablation: từng lớp chạy riêng (only_L*)", data, disp,
        note=("Đóng góp biên của một lớp so với baseline = baseline trừ only_Lk. Tỉ phần = giảm riêng lẻ / "
              "giảm của chuỗi đầy đủ (tổng các tỉ phần có thể vượt 100% khi các lớp chặn cùng một mẫu). "
              "Cột cuối là mức giảm khi *thêm* lớp đó vào chuỗi cộng dồn (Bảng 3). "
              + " ".join(notes)),
        group_col="Split", split_col="Split")


# ---------------------------------------------------------------------------
# Bảng 5: benign
# ---------------------------------------------------------------------------

def _benign_prompt_level(bd: pd.DataFrame) -> pd.DataFrame:
    return (bd.groupby(["config", "prompt_id"], sort=True)
            .agg(n=("refused", "size"), refused=("refused", "sum"), refused_rate=("refused", "mean"),
                 util=("utility_score", "mean"), util_un=("util_unblocked", "mean"))
            .reset_index())


def _benign_config_row(bd: pd.DataFrame, pl: pd.DataFrame, cfg: str, ctx: Context) -> dict:
    rows = bd[bd["config"] == cfg]
    pp = pl[pl["config"] == cfg]
    s = rate_summary(int(rows["refused"].sum()), len(rows), pp["refused_rate"].tolist(), ctx)
    ublo, ubhi = bootstrap_mean_ci(pp["util"].tolist(), b=ctx.b, seed=ctx.seed)
    un_prompts = pp["util_un"].dropna().tolist()
    uulo, uuhi = bootstrap_mean_ci(un_prompts, b=ctx.b, seed=ctx.seed)
    unblocked = rows[rows["blocked"] == 0]
    return {
        "config": cfg, "n_runs": len(rows), "n_prompts": len(pp),
        "n_refused": int(rows["refused"].sum()),
        "fpr": s["rate"], "fpr_wilson_lo": s["wilson_lo"], "fpr_wilson_hi": s["wilson_hi"],
        "fpr_prompt": s["rate_prompt"], "fpr_boot_lo": s["boot_lo"], "fpr_boot_hi": s["boot_hi"],
        "blocked_rate": float(rows["blocked_i"].mean()), "model_refused_rate": float(rows["model_only"].mean()),
        "utility": float(rows["utility_score"].mean()),
        "utility_prompt": float(pp["util"].mean()), "utility_boot_lo": ublo, "utility_boot_hi": ubhi,
        "n_unblocked_runs": len(unblocked),
        "utility_unblocked": float(unblocked["utility_score"].mean()) if len(unblocked) else NAN,
        "utility_unblocked_boot_lo": uulo, "utility_unblocked_boot_hi": uuhi,
    }


def table_benign(ctx: Context) -> Table | None:
    bd = ctx.benign_eval
    if bd.empty:
        ctx.skipped["tab05_benign"] = "không có dòng benign hợp lệ"
        return None
    pl = _benign_prompt_level(bd)
    vec = lambda cfg, col: pd.Series(pl.loc[pl["config"] == cfg, col].to_numpy(),  # noqa: E731
                                    index=pl.loc[pl["config"] == cfg, "prompt_id"].to_numpy())
    rows = []
    for cfg in [c for c in ctx.configs if c in set(bd["config"])]:
        row = _benign_config_row(bd, pl, cfg, ctx)
        if cfg != "baseline" and "baseline" in set(bd["config"]):
            f = paired_diff(ctx, vec("baseline", "refused_rate"), vec(cfg, "refused_rate"))
            u = paired_diff(ctx, vec("baseline", "util"), vec(cfg, "util"))
            # paired_diff trả ref - cur; với benign muốn cur - ref nên đổi dấu và đảo khoảng.
            row.update({"fpr_delta_base": -f["diff"], "fpr_delta_lo": -f["hi"], "fpr_delta_hi": -f["lo"],
                        "utility_delta_base": -u["diff"], "utility_delta_lo": -u["hi"],
                        "utility_delta_hi": -u["lo"]})
        rows.append(row)
    data = _frame(rows)
    for c in ("fpr_delta_base", "fpr_delta_lo", "fpr_delta_hi", "utility_delta_base",
              "utility_delta_lo", "utility_delta_hi"):
        if c not in data:
            data[c] = NAN
    disp = pd.DataFrame({
        "Config": data["config"], "Lượt": data["n_runs"].astype(int), "Prompt": data["n_prompts"].astype(int),
        "Từ chối oan (%)": data["fpr"].map(pct),
        "Wilson 95%": [pct_ci(a, b) for a, b in zip(data["fpr_wilson_lo"], data["fpr_wilson_hi"])],
        "Bootstrap 95%": [pct_ci(a, b) for a, b in zip(data["fpr_boot_lo"], data["fpr_boot_hi"])],
        "Bị chặn (%)": data["blocked_rate"].map(pct),
        "Model từ chối (%)": data["model_refused_rate"].map(pct),
        "Utility (cả bị chặn=0)": data["utility"].map(lambda x: num(x, 3)),
        "Utility (không bị chặn)": data["utility_unblocked"].map(lambda x: num(x, 3)),
        "Tăng từ chối vs baseline (pp)": [_diff_cell(r) for r in zip(
            data["fpr_delta_base"], data["fpr_delta_lo"], data["fpr_delta_hi"])],
        "Đổi utility vs baseline": [_utility_delta_cell(r) for r in zip(
            data["utility_delta_base"], data["utility_delta_lo"], data["utility_delta_hi"])],
    })
    return Table(
        "tab05_benign", "Bảng 5. Benign: từ chối oan và chất lượng tác vụ", data, disp,
        note=(f"Phạm vi: {ctx.benign_scope}. Từ chối oan = bị chặn *hoặc* model tự từ chối. Utility: benign bị "
              "chặn tính 0 theo hợp đồng; cột 'không bị chặn' chỉ tính các lượt qua được phòng thủ. "
              "Hiệu vs baseline là bootstrap xếp cặp theo prompt benign (dương = từ chối nhiều hơn / utility cao hơn)."))


def _utility_delta_cell(r: tuple[float, float, float]) -> str:
    d, lo, hi = r
    if math.isnan(d):
        return "-"
    return f"{signed(d)} [{signed(lo)}, {signed(hi)}]"


def table_benign_by_tune(ctx: Context) -> Table | None:
    if ctx.benign_meta is None or ctx.benign_all.empty:
        return None
    bd = ctx.benign_all
    flag = bd["prompt_id"].map(lambda i: ctx.benign_meta.get(i))
    rows = []
    for tune, name in ((False, "false"), (True, "true")):
        part = bd[flag == tune]
        if part.empty:
            continue
        pl = _benign_prompt_level(part)
        for cfg in [c for c in ctx.configs if c in set(part["config"])]:
            r = _benign_config_row(part, pl, cfg, ctx)
            rows.append({"tune": name, **{k: r[k] for k in (
                "config", "n_runs", "n_prompts", "fpr", "fpr_wilson_lo", "fpr_wilson_hi",
                "fpr_prompt", "fpr_boot_lo", "fpr_boot_hi", "utility", "utility_unblocked")}})
    if not rows:
        return None
    data = _frame(rows)
    disp = pd.DataFrame({
        "tune": data["tune"], "Config": data["config"], "Prompt": data["n_prompts"].astype(int),
        "Từ chối oan (%)": data["fpr"].map(pct),
        "Bootstrap 95%": [pct_ci(a, b) for a, b in zip(data["fpr_boot_lo"], data["fpr_boot_hi"])],
        "Utility": data["utility"].map(lambda x: num(x, 3)),
    })
    return Table(
        "tab05b_benign_by_tune", "Bảng 5b. Benign theo cờ `tune`", data, disp,
        note="Phần `tune:true` đã được dùng để chỉnh ngưỡng/từ khoá nên *lạc quan*; chỉ `tune:false` là số báo cáo.",
        group_col="tune")


# ---------------------------------------------------------------------------
# Bảng 6: chi phí
# ---------------------------------------------------------------------------

def table_cost(ctx: Context) -> Table:
    v = ctx.valid
    pops = {"benign": v[v["label"] == "benign"], "attack": v[v["label"] == "attack"], "all": v}
    rows = []
    for pop, df in pops.items():
        for cfg in [c for c in ctx.configs if c in set(df["config"])]:
            g = df[df["config"] == cfg]
            tot, lay = g["latency_ms_total"], g["latency_ms_layers"]
            rows.append({
                "population": pop, "config": cfg, "n_runs": len(g),
                "calls_mean": float(g["n_model_calls"].mean()),
                "lat_mean": float(tot.mean()), "lat_p50": float(tot.quantile(0.5)),
                "lat_p95": float(tot.quantile(0.95)),
                "layers_mean": float(lay.mean()), "layers_p50": float(lay.quantile(0.5)),
                "layers_p95": float(lay.quantile(0.95)),
            })
    data = _frame(rows)
    for col, src in (("ratio_calls", "calls_mean"), ("ratio_lat_mean", "lat_mean"),
                     ("ratio_lat_p50", "lat_p50"), ("ratio_lat_p95", "lat_p95")):
        data[col] = NAN
        for pop in data["population"].unique():
            m = data["population"] == pop
            b = data.loc[m & (data["config"] == "baseline"), src]
            if len(b) and b.iloc[0] > 0:
                data.loc[m, col] = data.loc[m, src] / b.iloc[0]
    disp = pd.DataFrame({
        "Nhóm": data["population"], "Config": data["config"], "Lượt": data["n_runs"].astype(int),
        "Lần gọi model TB": data["calls_mean"].map(lambda x: num(x, 2)),
        "Độ trễ TB (ms)": data["lat_mean"].map(lambda x: num(x, 0)),
        "p50 (ms)": data["lat_p50"].map(lambda x: num(x, 0)),
        "p95 (ms)": data["lat_p95"].map(lambda x: num(x, 0)),
        "Chậm gấp (TB)": data["ratio_lat_mean"].map(ratio),
        "Chậm gấp (p50)": data["ratio_lat_p50"].map(ratio),
        "Chậm gấp (p95)": data["ratio_lat_p95"].map(ratio),
        "Lớp phòng thủ TB (ms)": data["layers_mean"].map(lambda x: num(x, 1)),
        "Lớp p50 (ms)": data["layers_p50"].map(lambda x: num(x, 1)),
        "Lớp p95 (ms)": data["layers_p95"].map(lambda x: num(x, 1)),
    })
    return Table(
        "tab06_cost", "Bảng 6. Chi phí: số lần gọi model và độ trễ", data, disp,
        note=("Tỉ số so với `baseline` trong cùng nhóm. Lượt bị L1/L2 chặn không gọi model nên rẻ hơn; "
              "nhóm `benign` phản ánh chi phí cho lưu lượng bình thường. Độ trễ đuôi dài: xem p50/p95 bên cạnh trung bình."),
        group_col="Nhóm", split_col="Nhóm")


# ---------------------------------------------------------------------------
# Bảng 7: theo lớp (blocked_by) và đóng góp tăng thêm
# ---------------------------------------------------------------------------

def _populations(ctx: Context) -> list[tuple[str, pd.DataFrame]]:
    pops = [(s, ctx.attack[ctx.attack["split"] == s]) for s in ctx.splits]
    if not ctx.benign_eval.empty:
        pops.append(("benign", ctx.benign_eval))
    return pops


def table_layers(ctx: Context) -> Table:
    rows = []
    for name, df in _populations(ctx):
        for cfg in [c for c in ctx.configs if c in set(df["config"])]:
            g = df[df["config"] == cfg]
            r = {"population": name, "config": cfg, "n_runs": len(g), "blocked": int((g["blocked"] == 1).sum())}
            for layer in BLOCKING_LAYERS:
                r[f"n_{layer}"] = int((g["blocked_by"] == layer).sum())
            rows.append(r)
    data = _frame(rows)
    for col in ["blocked"] + [f"n_{l}" for l in BLOCKING_LAYERS]:
        data["rate_" + col.removeprefix("n_")] = data[col] / data["n_runs"]
    cell = lambda r, col: f"{int(r[col])} ({pct(r['rate_' + col.removeprefix('n_')])}%)"  # noqa: E731
    disp = pd.DataFrame({
        "Nhóm": data["population"], "Config": data["config"], "Lượt": data["n_runs"].astype(int),
        "Bị chặn": [cell(r, "blocked") for _, r in data.iterrows()],
        **{f"Bởi {l}": [cell(r, f"n_{l}") for _, r in data.iterrows()] for l in BLOCKING_LAYERS},
    }) if len(data) else pd.DataFrame()
    return Table(
        "tab07_layers", "Bảng 7a. Số lượt bị chặn theo lớp (`blocked_by`)", data, disp,
        note=(f"Nhóm tấn công là từng split; nhóm `benign` ({ctx.benign_scope}). Trong chuỗi, mỗi lượt chỉ được "
              "ghi cho lớp chặn *đầu tiên*, nên lớp sau chỉ thấy phần còn lại. L3 không chặn, tác dụng của nó "
              "thể hiện ở ASR chứ không ở cột này."),
        group_col="Nhóm", split_col="Nhóm")


def table_layer_increment(ctx: Context, cumulative: Table) -> Table | None:
    chain = [c for c in CHAIN if c in ctx.configs]
    if len(chain) < 2:
        ctx.skipped["tab07b_layer_increment"] = "chuỗi cộng dồn có ít hơn 2 cấu hình"
        return None
    benign_rate = (ctx.benign_eval.groupby("config")[["blocked_i", "refused"]].mean()
                   if not ctx.benign_eval.empty else None)
    rows = []
    for split in ctx.splits:
        g = ctx.attack[ctx.attack["split"] == split]
        brate = g.groupby("config")["blocked"].mean()
        steps = cumulative.data[cumulative.data["split"] == split]
        for r in steps.itertuples():
            if not r.prev_config:
                continue
            row = {"split": split, "config": r.config, "layer_added": r.added_layer,
                   "d_blocked_attack": brate.get(r.config, NAN) - brate.get(r.prev_config, NAN),
                   "red_asr": r.red_abs_prev, "red_asr_lo": r.red_abs_prev_lo, "red_asr_hi": r.red_abs_prev_hi,
                   "d_blocked_benign": NAN, "d_refused_benign": NAN}
            if benign_rate is not None and {r.config, r.prev_config} <= set(benign_rate.index):
                row["d_blocked_benign"] = (benign_rate.loc[r.config, "blocked_i"]
                                           - benign_rate.loc[r.prev_config, "blocked_i"])
                row["d_refused_benign"] = (benign_rate.loc[r.config, "refused"]
                                           - benign_rate.loc[r.prev_config, "refused"])
            rows.append(row)
    data = _frame(rows)
    disp = pd.DataFrame({
        "Split": data["split"], "Lớp thêm": data["layer_added"], "Config": data["config"],
        "Chặn thêm tấn công (pp)": data["d_blocked_attack"].map(signed_pp),
        "Giảm ASR (pp)": [_diff_cell(r) for r in zip(data["red_asr"], data["red_asr_lo"], data["red_asr_hi"])],
        "Chặn thêm benign (pp)": data["d_blocked_benign"].map(signed_pp),
        "Từ chối oan tăng thêm (pp)": data["d_refused_benign"].map(signed_pp),
    })
    return Table(
        "tab07b_layer_increment", "Bảng 7b. Đóng góp tăng thêm của từng lớp trong chuỗi", data, disp,
        note=("Lợi (giảm ASR, chặn thêm tấn công) đặt cạnh hại (chặn thêm và từ chối oan tăng thêm trên benign) cho từng bước "
              "thêm lớp. 'Giảm ASR' có thể lớn hơn 'chặn thêm' vì L1 làm sạch và L3 bọc tài liệu mà không chặn."),
        group_col="Split", split_col="Split")


# ---------------------------------------------------------------------------
# Bảng 8: khoảng cách tổng quát hoá
# ---------------------------------------------------------------------------

def table_generalization(ctx: Context) -> Table | None:
    rows = []
    for cfg in ctx.configs:
        for a, b in GENERALIZATION_PAIRS:
            if a not in ctx.splits or b not in ctx.splits:
                continue
            va, vb = ctx.prompt_means(cfg, a), ctx.prompt_means(cfg, b)
            if va.empty or vb.empty:
                continue
            # paired_diff trả ref - cur; muốn (b - a) nên đưa b làm ref.
            d = paired_diff(ctx, vb, va, paired=False)
            sa = asr_summary(ctx.ps[(ctx.ps["config"] == cfg) & (ctx.ps["split"] == a)], ctx)
            sb = asr_summary(ctx.ps[(ctx.ps["config"] == cfg) & (ctx.ps["split"] == b)], ctx)
            rows.append({
                "config": cfg, "from_split": a, "to_split": b,
                "n_prompts_from": sa["n_prompts"], "n_prompts_to": sb["n_prompts"],
                "asr_from": sa["asr_prompt"], "asr_to": sb["asr_prompt"],
                "wilson_from_lo": sa["wilson_lo"], "wilson_from_hi": sa["wilson_hi"],
                "wilson_to_lo": sb["wilson_lo"], "wilson_to_hi": sb["wilson_hi"],
                "gap": d["diff"], "gap_lo": d["lo"], "gap_hi": d["hi"],
                "ci_excludes_0": _excludes_zero(d["lo"], d["hi"]),
            })
    if not rows:
        ctx.skipped["tab08_generalization"] = "cần ít nhất hai split tấn công (vd train và holdout)"
        return None
    data = _frame(rows)
    disp = pd.DataFrame({
        "Config": data["config"], "Từ -> sang": data["from_split"] + " -> " + data["to_split"],
        "Prompt (từ/sang)": [f"{int(x)}/{int(y)}" for x, y in zip(data["n_prompts_from"], data["n_prompts_to"])],
        "ASR từ (%)": data["asr_from"].map(pct), "ASR sang (%)": data["asr_to"].map(pct),
        "Chênh lệch (pp)": data["gap"].map(signed_pp),
        "Bootstrap 95% (pp)": [f"[{signed_pp(lo)}, {signed_pp(hi)}]" for lo, hi in zip(data["gap_lo"], data["gap_hi"])],
        "Loại 0?": data["ci_excludes_0"].map({True: "có", False: "không"}),
    })
    return Table(
        "tab08_generalization", "Bảng 8. Khoảng cách tổng quát hoá giữa các split", data, disp,
        note=("Chênh lệch = ASR(split sang) - ASR(split từ) tính theo prompt; dương nghĩa là phòng thủ kém hơn trên split "
              "sang (dấu hiệu quá khớp với train). Hai split là hai tập prompt khác nhau nên dùng bootstrap độc lập, "
              "không xếp cặp."),
        group_col="Config")


# ---------------------------------------------------------------------------
# Bảng 9: prompt chết và ASR hiệu dụng
# ---------------------------------------------------------------------------

def _dead_prompts(ctx: Context) -> pd.DataFrame | None:
    base = ctx.ps[ctx.ps["config"] == "baseline"]
    if base.empty:
        return None
    out = base.assign(dead=base["k"] == 0)
    return out[["split", "prompt_id", "attack_type", "liu_type", "goal_type", "technique", "n", "dead"]]


def tables_dead(ctx: Context) -> list[Table]:
    dp = _dead_prompts(ctx)
    if dp is None:
        ctx.skipped["tab09_dead_prompts"] = "không có config baseline"
        return []
    out = []
    # 9a: tóm tắt theo loại
    rows = []
    for split in ["all"] + ctx.splits:
        part = dp if split == "all" else dp[dp["split"] == split]
        rows.append({"split": split, "dimension": "tổng", "value": "tất cả",
                     "n_prompts": len(part), "n_dead": int(part["dead"].sum()),
                     "dead_rate": float(part["dead"].mean()) if len(part) else NAN})
        for dim in BREAKDOWNS:
            for value, g in part.groupby(dim):
                rows.append({"split": split, "dimension": dim, "value": value, "n_prompts": len(g),
                             "n_dead": int(g["dead"].sum()), "dead_rate": float(g["dead"].mean())})
    d9a = _frame(rows)
    disp = pd.DataFrame({
        "Split": d9a["split"], "Chiều": d9a["dimension"], "Giá trị": d9a["value"],
        "Prompt": d9a["n_prompts"], "Chết": d9a["n_dead"], "Tỉ lệ chết (%)": d9a["dead_rate"].map(pct)})
    min_n = int(dp["n"].min())
    out.append(Table(
        "tab09a_dead_summary", "Bảng 9a. Prompt 'chết' (baseline không bao giờ bị chiếm) theo loại", d9a, disp,
        note=(f"Prompt chết = ASR baseline = 0 trên *mọi* lượt. Số lượt baseline mỗi prompt tối thiểu {min_n}: "
              "nếu nhỏ, 'chết' có thể chỉ là chưa đủ mẫu (xác suất bỏ lỡ prompt có ASR thật p là (1-p)^lượt)."),
        group_col="Split", split_col="Split"))
    # 9b: danh sách
    dead = dp[dp["dead"]].sort_values(["split", "attack_type", "prompt_id"])
    d9b = dead.rename(columns={"n": "n_baseline_runs"}).drop(columns="dead").reset_index(drop=True)
    disp = pd.DataFrame({"Split": d9b["split"], "Loại tấn công": d9b["attack_type"], "Prompt": d9b["prompt_id"],
                         "Kiểu Liu": d9b["liu_type"], "Mục tiêu": d9b["goal_type"], "Kỹ thuật": d9b["technique"],
                         "Lượt baseline": d9b["n_baseline_runs"]})
    out.append(Table("tab09b_dead_list", "Bảng 9b. Danh sách prompt chết", d9b, disp,
                     group_col="Split", split_col="Split"))
    # 9c: ASR hiệu dụng
    alive = dp[~dp["dead"]][["split", "prompt_id"]]
    rows = []
    for split in ctx.splits:
        ids = set(alive.loc[alive["split"] == split, "prompt_id"])
        n_dead = int(dp[(dp["split"] == split) & dp["dead"]].shape[0])
        for cfg in ctx.configs:
            full = ctx.ps[(ctx.ps["config"] == cfg) & (ctx.ps["split"] == split)]
            if full.empty:
                continue
            sub = full[full["prompt_id"].isin(ids)]
            if sub.empty:
                continue
            s = asr_summary(sub, ctx)
            rows.append({"split": split, "config": cfg, "n_alive_prompts": len(ids), "n_dead_prompts": n_dead,
                         **s, "asr_prompt_unconditional": float(full["asr"].mean())})
    if rows:
        d9c = _frame(rows)
        disp = pd.DataFrame({
            "Split": d9c["split"], "Config": d9c["config"],
            "Prompt sống/chết": [f"{int(a)}/{int(b)}" for a, b in zip(d9c["n_alive_prompts"], d9c["n_dead_prompts"])],
            "ASR hiệu dụng theo lượt (%)": d9c["asr"].map(pct),
            "Wilson 95%": [pct_ci(a, b) for a, b in zip(d9c["wilson_lo"], d9c["wilson_hi"])],
            "ASR hiệu dụng theo prompt (%)": d9c["asr_prompt"].map(pct),
            "Bootstrap 95%": [pct_ci(a, b) for a, b in zip(d9c["boot_lo"], d9c["boot_hi"])],
            "ASR không điều kiện (%)": d9c["asr_prompt_unconditional"].map(pct),
        })
        out.append(Table(
            "tab09c_effective_asr", "Bảng 9c. ASR hiệu dụng (chỉ trên prompt mà baseline bị chiếm)", d9c, disp,
            note=("ASR có điều kiện: chỉ tính các prompt có ASR baseline > 0. Lưu ý chọn lọc: dòng `baseline` bị thổi lên "
                  "vì chính điều kiện lọc (prompt được chọn vì đã thành công ở baseline); các config khác dùng lượt "
                  "lấy mẫu khác nên ít bị thiên lệch hơn nhưng vẫn có hồi quy về trung bình. Dùng để so sánh "
                  "phòng thủ trên phần tấn công thật sự có hiệu lực."),
            group_col="Split", split_col="Split"))
    return out


# ---------------------------------------------------------------------------
# Bảng 10: lỗi/timeout
# ---------------------------------------------------------------------------

def tables_errors(ctx: Context) -> list[Table]:
    rows_all = ctx.loaded.rows
    rows = []
    for cfg in order_configs(list(rows_all["config"].unique())) + ["(tổng)"]:
        sub = rows_all if cfg == "(tổng)" else rows_all[rows_all["config"] == cfg]
        for label in ("attack", "benign", "all"):
            g = sub if label == "all" else sub[sub["label"] == label]
            if g.empty:
                continue
            n_err = int(g["is_error"].sum())
            lo, hi = wilson(n_err, len(g))
            rows.append({"config": cfg, "label": label, "n_rows": len(g), "n_error": n_err,
                         "n_valid": len(g) - n_err, "error_rate": n_err / len(g),
                         "wilson_lo": lo, "wilson_hi": hi, "over_threshold": n_err / len(g) > ctx.error_threshold})
    data = _frame(rows)
    disp = pd.DataFrame({
        "Config": data["config"], "Nhóm": data["label"], "Dòng": data["n_rows"], "Lỗi": data["n_error"],
        "Hợp lệ (đưa vào mẫu)": data["n_valid"], "Tỉ lệ lỗi (%)": data["error_rate"].map(lambda x: pct(x, 2)),
        "Wilson 95%": [pct_ci(a, b, 2) for a, b in zip(data["wilson_lo"], data["wilson_hi"])],
        "Cảnh báo": data["over_threshold"].map({True: f"> {ctx.error_threshold:.0%}", False: ""}),
    })
    out = [Table("tab10_errors", "Bảng 10. Tỉ lệ lỗi/timeout (dòng có `error` khác rỗng, bị loại khỏi mẫu)",
                 data, disp, note=f"Ngưỡng cảnh báo {ctx.error_threshold:.0%}.", group_col="Config")]
    errs = rows_all[rows_all["is_error"]]
    if len(errs):
        counts = errs["error"].str.slice(0, 80).value_counts().head(10)
        d = pd.DataFrame({"error": counts.index, "count": counts.to_numpy()})
        out.append(Table("tab10b_error_types", "Bảng 10b. Các loại lỗi phổ biến", d,
                         pd.DataFrame({"Lỗi": d["error"], "Số dòng": d["count"]})))
    return out


# ---------------------------------------------------------------------------
# Dữ liệu .dat cho pgfplots
# ---------------------------------------------------------------------------

def _err(point: pd.Series, bound: pd.Series, upper: bool) -> pd.Series:
    return ((bound - point) if upper else (point - bound)).clip(lower=0)


def dat_files(ctx: Context, tables: dict[str, Table], out: Path) -> list[Path]:
    """Mọi tỉ lệ nhân 100 (đơn vị %); NaN ghi là `nan`. Cột `label` đã thoát `_` cho TeX."""
    paths = []
    t1 = tables.get("tab01_asr_split")
    if t1 is not None and len(t1.data):
        for split in ctx.splits:
            d = t1.data[t1.data["split"] == split].reset_index(drop=True)
            if d.empty:
                continue
            f = pd.DataFrame({
                "idx": range(len(d)), "config": d["config"], "label": d["config"].map(tex_label),
                "n_runs": d["n_runs"], "n_prompts": d["n_prompts"], "asr": 100 * d["asr"],
                "w_lo": 100 * d["wilson_lo"], "w_hi": 100 * d["wilson_hi"],
                "w_minus": 100 * _err(d["asr"], d["wilson_lo"], False),
                "w_plus": 100 * _err(d["asr"], d["wilson_hi"], True),
                "asr_prompt": 100 * d["asr_prompt"], "b_lo": 100 * d["boot_lo"], "b_hi": 100 * d["boot_hi"],
                "b_minus": 100 * _err(d["asr_prompt"], d["boot_lo"], False),
                "b_plus": 100 * _err(d["asr_prompt"], d["boot_hi"], True)})
            paths.append(write_dat(f, f"asr_{split}", out))
    t5 = tables.get("tab05_benign")
    if t5 is not None:
        d = t5.data.reset_index(drop=True)
        f = pd.DataFrame({
            "idx": range(len(d)), "config": d["config"], "label": d["config"].map(tex_label),
            "n_runs": d["n_runs"], "n_prompts": d["n_prompts"], "fpr": 100 * d["fpr"],
            "w_lo": 100 * d["fpr_wilson_lo"], "w_hi": 100 * d["fpr_wilson_hi"],
            "w_minus": 100 * _err(d["fpr"], d["fpr_wilson_lo"], False),
            "w_plus": 100 * _err(d["fpr"], d["fpr_wilson_hi"], True),
            "fpr_prompt": 100 * d["fpr_prompt"], "b_lo": 100 * d["fpr_boot_lo"], "b_hi": 100 * d["fpr_boot_hi"],
            "b_minus": 100 * _err(d["fpr_prompt"], d["fpr_boot_lo"], False),
            "b_plus": 100 * _err(d["fpr_prompt"], d["fpr_boot_hi"], True),
            "utility": 100 * d["utility"], "utility_unblocked": 100 * d["utility_unblocked"],
            "utility_prompt": 100 * d["utility_prompt"], "u_lo": 100 * d["utility_boot_lo"],
            "u_hi": 100 * d["utility_boot_hi"],
            "u_minus": 100 * _err(d["utility_prompt"], d["utility_boot_lo"], False),
            "u_plus": 100 * _err(d["utility_prompt"], d["utility_boot_hi"], True)})
        paths.append(write_dat(f, "benign", out))
    t6 = tables.get("tab06_cost")
    if t6 is not None:
        for pop, d in t6.data.groupby("population", sort=False):
            d = d.reset_index(drop=True)
            f = pd.DataFrame({
                "idx": range(len(d)), "config": d["config"], "label": d["config"].map(tex_label),
                "n_runs": d["n_runs"], "calls_mean": d["calls_mean"], "lat_mean": d["lat_mean"],
                "lat_p50": d["lat_p50"], "lat_p95": d["lat_p95"], "layers_mean": d["layers_mean"],
                "ratio_mean": d["ratio_lat_mean"], "ratio_p50": d["ratio_lat_p50"],
                "ratio_p95": d["ratio_lat_p95"]})
            paths.append(write_dat(f, f"latency_{pop}", out))
    return paths


# ---------------------------------------------------------------------------
# Báo cáo tổng hợp
# ---------------------------------------------------------------------------

METHOD_NOTES = r"""
## Ghi chú phương pháp

**Mẫu.** Mỗi dòng CSV là một lượt (một prompt, một cấu hình, một lần lấy mẫu). Chỉ dòng có `error` rỗng được đưa vào mẫu;
dòng lỗi/timeout bị loại và được đếm ở Bảng 10. Dữ liệu được kiểm tra theo hợp đồng trước khi tính (đủ 21 cột, kiểu đúng,
`attack_success` rỗng với benign, bị chặn thì `attack_success=0`, `blocked_by` khớp `config`, không trùng khoá, metadata
prompt nhất quán); vi phạm làm chương trình dừng với thông báo nêu rõ.

**Thước đo.**
- *ASR theo lượt* $= k/n$ với $k$ là số lượt `attack_success=1` và $n$ là số lượt tấn công hợp lệ của nhóm.
- *ASR theo prompt* $= \frac{1}{m}\sum_{i=1}^{m} \hat p_i$, với $\hat p_i$ là ASR của prompt $i$ (trung bình qua các `sample_idx`)
  và $m$ là số prompt. Hai đại lượng bằng nhau khi mọi prompt có cùng số lượt hợp lệ.
- *Tỉ lệ từ chối oan* = trung bình của (`blocked` hoặc `model_refused`) trên benign. *Utility* = trung bình `utility_score`
  trên benign; benign bị chặn tính 0 theo hợp đồng, nên có thêm cột utility chỉ tính trên lượt không bị chặn.
- *Chi phí* = trung bình `n_model_calls`, `latency_ms_total`, `latency_ms_layers`; tỉ số "chậm gấp" so với `baseline` cùng nhóm;
  kèm p50/p95 vì độ trễ có đuôi dài.
- *Giảm tuyệt đối* = ASR(bước trước hoặc baseline) $-$ ASR(cấu hình hiện tại), tính theo prompt, đơn vị điểm phần trăm (pp);
  *giảm tương đối* = giảm tuyệt đối / ASR đối chiếu.
- *Prompt chết* = prompt có ASR baseline $=0$ trên mọi lượt. *ASR hiệu dụng* = ASR chỉ trên các prompt còn lại (baseline bị chiếm).

**Khoảng tin cậy Wilson 95% (theo tổng số lượt).** Với $\hat p=k/n$ và $z=1{,}96$:
$$\frac{\hat p+\frac{z^2}{2n}\;\pm\; z\sqrt{\frac{\hat p(1-\hat p)}{n}+\frac{z^2}{4n^2}}}{1+\frac{z^2}{n}}$$
Công thức này coi $n$ lượt là độc lập. Thực tế các lượt của cùng một prompt tương quan (cùng nội dung tấn công), nên
Wilson **lạc quan** (khoảng hẹp hơn thực tế). Ta vẫn báo cáo vì hợp đồng yêu cầu và để đối chiếu.

**Bootstrap theo cụm (khoảng chính nên trích dẫn).** Đơn vị độc lập là *prompt*. Với $B=%(B)d$ lần: lấy mẫu có hoàn lại $m$ prompt
từ $m$ prompt, tính ASR theo prompt trung bình; khoảng tin cậy 95% là phân vị 2,5% và 97,5% của $B$ giá trị (phương pháp phân vị).
Hạt giống cố định (`seed=%(seed)d`), mỗi khoảng dùng bộ sinh số riêng nên kết quả tái lập và không phụ thuộc thứ tự tính bảng.
- *Hiệu giữa hai cấu hình* trên cùng tập prompt: bootstrap **xếp cặp** (resample chỉ số prompt chung, tính hiệu từng prompt rồi trung bình),
  giữ được tương quan giữa hai cấu hình nên khoảng hẹp hơn. Chỉ dùng phần giao prompt của hai cấu hình.
- *Hiệu giữa hai split* (khác tập prompt, vd train và holdout): bootstrap **độc lập** (resample riêng từng split).
- Khi chỉ có ít prompt (dưới khoảng 10), bootstrap kém tin cậy và khoảng rất rộng; một prompt duy nhất cho khoảng suy biến.
- Vì ASR từng prompt đã chứa nhiễu lấy mẫu trong prompt, bootstrap theo cụm gộp cả biến thiên giữa các prompt lẫn nhiễu đó;
  kết luận suy rộng cho tổng thể prompt cùng kiểu với bộ đã chọn. Khoảng không bao gồm sai khác giữa các phiên bản mô hình,
  nhiệt độ khác, hay lỗi của quy tắc chấm `success_check`.

**Lưu ý đọc kết quả.** (1) Mỗi bảng chỉ phản ánh đúng các lượt đã chạy với nhiệt độ/mô hình trong `run_config.json`.
(2) Số trên `train` và `tune:true` đã được dùng để chỉnh phòng thủ nên lạc quan; số báo cáo chính dùng `holdout`,
`test_indist` và benign `tune:false`. (3) Với $n$ nhỏ, không rút ra kết luận mạnh từ khác biệt vài điểm phần trăm.
"""


def _issue_section(issues: list[Issue]) -> str:
    warns = [i for i in issues if i.level == "warning"]
    if not warns:
        return "## Cảnh báo dữ liệu\n\nKhông có cảnh báo.\n"
    return "## Cảnh báo dữ liệu\n\n" + "\n".join(f"- {i.render()}" for i in warns) + "\n"


def _overview(ctx: Context, paths: list[str]) -> str:
    rows = ctx.loaded.rows
    valid = ctx.valid
    models = sorted(set(rows["model"]))
    runs = sorted(set(rows["run_id"]))
    per = valid.groupby(["config", "prompt_id"]).size()
    spp = f"{int(per.min())}–{int(per.max())}" if len(per) else "n/a"
    prompts = "; ".join(
        f"{s}: {ctx.ps.loc[ctx.ps['split'] == s, 'prompt_id'].nunique()} prompt" for s in ctx.splits)
    n_ben = ctx.benign_all["prompt_id"].nunique()
    lines = [
        f"- Nguồn: {', '.join(f'`{p}`' for p in paths)}",
        f"- Model: {', '.join(models)}; run_id: {', '.join(runs)}",
        f"- Tổng dòng: {len(rows)}; hợp lệ: {len(valid)}; lỗi bị loại: {int(rows['is_error'].sum())}",
        f"- Cấu hình ({len(ctx.configs)}): {', '.join(ctx.configs)}",
        f"- Prompt tấn công: {prompts}; prompt benign: {n_ben} (phạm vi bảng benign: {ctx.benign_scope})",
        f"- Số lượt hợp lệ mỗi (cấu hình, prompt): {spp}",
        f"- Bootstrap: B={ctx.b}, seed={ctx.seed}; khoảng tin cậy 95%",
    ]
    return "## Tổng quan dữ liệu\n\n" + "\n".join(lines) + "\n"


def build_report(ctx: Context, tables: list[Table], paths: list[str], files: list[Path], out: Path) -> str:
    parts = ["# Báo cáo phân tích thống kê\n", _overview(ctx, paths), _issue_section(ctx.issues),
             METHOD_NOTES.replace("%(B)d", str(ctx.b)).replace("%(seed)d", str(ctx.seed)), "## Bảng kết quả\n"]
    for t in tables:
        parts.append(f"### {t.title}\n")
        parts.append(md_table(t.display) if len(t.display) else "_(không có dữ liệu)_")
        if t.note:
            parts.append(f"\n> {t.note}\n")
        parts.append("")
    if ctx.skipped:
        parts.append("### Bảng bị bỏ qua\n")
        parts += [f"- `{k}`: {v}" for k, v in ctx.skipped.items()]
        parts.append("")
    parts.append("## File sinh ra\n")
    parts.append("Mỗi bảng có `tables/<tên>.tex` (booktabs, dùng `\\input`), `csv/<tên>.csv` (số thật), `md/<tên>.md`; "
                 "bảng có cột split còn có `tables/<tên>_<split>.tex`. Dữ liệu biểu đồ ở `dat/*.dat` "
                 "(tỉ lệ đơn vị %, cột cách nhau bằng dấu cách).\n")
    parts.append("```\n" + "\n".join(sorted(str(p.relative_to(out)) for p in files)) + "\n```")
    return "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Điều phối
# ---------------------------------------------------------------------------

def compute_tables(ctx: Context) -> list[Table]:
    """Tính mọi bảng theo thứ tự trong báo cáo (bỏ qua bảng không đủ dữ liệu)."""
    tables: list[Table] = []
    if ctx.ps.empty:
        ctx.skipped["tab01-04,07b,08,09"] = "không có dòng tấn công hợp lệ"
    else:
        tables.append(table_asr_by_split(ctx))
        tables += [table_asr_breakdown(ctx, d) for d in BREAKDOWNS]
        cum = table_cumulative(ctx)
        tables.append(cum)
        abl = table_ablation(ctx, cum)
        if abl is not None:
            tables.append(abl)
    for t in (table_benign(ctx), table_benign_by_tune(ctx)):
        if t is not None:
            tables.append(t)
    tables.append(table_cost(ctx))
    tables.append(table_layers(ctx))
    if not ctx.ps.empty:
        inc = table_layer_increment(ctx, cum)
        if inc is not None:
            tables.append(inc)
        gen = table_generalization(ctx)
        if gen is not None:
            tables.append(gen)
        tables += tables_dead(ctx)
    tables += tables_errors(ctx)
    return tables


def run_analysis(paths: list[str | Path], out: str | Path | None = None, *, benign_meta: str | Path | None = None,
                 b: int = DEFAULT_B, seed: int = DEFAULT_SEED, model: str | None = None,
                 error_threshold: float = DEFAULT_ERROR_THRESHOLD) -> tuple[Context, list[Table], Path]:
    """Đọc CSV -> sinh bảng, .dat và report.md trong `out`. Trả (ngữ cảnh, bảng, thư mục ra)."""
    str_paths = [str(p) for p in paths]
    out_dir = Path(out) if out else Path(str_paths[0]).resolve().parent / "analysis"
    loaded = load_results(str_paths, model=model, error_threshold=error_threshold)
    meta = load_benign_meta(benign_meta) if benign_meta else None
    ctx = build_context(loaded, b=b, seed=seed, benign_meta=meta, error_threshold=error_threshold)
    tables = compute_tables(ctx)
    out_dir.mkdir(parents=True, exist_ok=True)
    files: list[Path] = []
    for t in tables:
        files += write_table(t, out_dir)
    files += dat_files(ctx, {t.name: t for t in tables}, out_dir)
    report = out_dir / "report.md"
    report.write_text(build_report(ctx, tables, str_paths, files, out_dir), encoding="utf-8")
    return ctx, tables, out_dir


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python3 -m analysis.stats", description=__doc__.splitlines()[0])
    ap.add_argument("csv", nargs="+", help="một hoặc nhiều results.csv (được gộp)")
    ap.add_argument("--out", help="thư mục ra (mặc định: <thư mục file CSV đầu>/analysis)")
    ap.add_argument("--benign-meta", help="attack_prompts/benign_prompts.json để join id -> tune")
    ap.add_argument("--model", help="chọn một model khi CSV chứa nhiều model")
    ap.add_argument("--B", type=int, default=DEFAULT_B, help=f"số lần bootstrap (mặc định {DEFAULT_B})")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--error-threshold", type=float, default=DEFAULT_ERROR_THRESHOLD,
                    help="cảnh báo nếu tỉ lệ lỗi vượt ngưỡng (mặc định 0.02)")
    args = ap.parse_args(argv)
    try:
        ctx, tables, out = run_analysis(args.csv, args.out, benign_meta=args.benign_meta, b=args.B,
                                        seed=args.seed, model=args.model, error_threshold=args.error_threshold)
    except DataError as exc:
        print(f"LỖI DỮ LIỆU: {exc}", file=sys.stderr)
        return 2
    rows = ctx.loaded.rows
    print(f"Đã đọc {len(rows)} dòng ({len(ctx.valid)} hợp lệ, {int(rows['is_error'].sum())} lỗi bị loại); "
          f"{len(ctx.configs)} config; split: {', '.join(ctx.splits)}")
    for i in ctx.issues:
        if i.level == "warning":
            print("CẢNH BÁO " + i.render(), file=sys.stderr)
    print(f"Đã ghi {len(tables)} bảng và report.md vào {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
