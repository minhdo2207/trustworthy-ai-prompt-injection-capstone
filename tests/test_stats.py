"""Kiểm tra analysis.stats bằng CSV tổng hợp có đáp án tay tính (tests/fixtures/make_stats_fixture.py).

Cách tính tay nằm trong chú thích ở từng test; các số hằng được suy ra từ ATTACK_SPEC/BENIGN_SPEC
của fixture (4 lượt mỗi prompt tấn công, 2 lượt mỗi prompt benign), không lấy từ đầu ra của chương trình.
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))

import make_stats_fixture as fx  # noqa: E402
from analysis import render  # noqa: E402
from analysis.intervals import bootstrap_diff_ci, bootstrap_mean_ci, quantile, wilson  # noqa: E402
from analysis.loader import (DataError, check_input, config_layers, load_benign_meta,  # noqa: E402
                             load_results, read_csvs)
from analysis.stats import main, order_configs, run_analysis  # noqa: E402

B_FAST = 400


def write_rows(path: Path, rows: list[dict], drop: str | None = None) -> Path:
    fx.write_csv(path, rows)
    if drop:
        df = pd.read_csv(path, dtype=str, keep_default_na=False).drop(columns=[drop])
        df.to_csv(path, index=False)
    return path


def only(df: pd.DataFrame, **cond) -> pd.Series:
    sub = df
    for k, v in cond.items():
        sub = sub[sub[k] == v]
    assert len(sub) == 1, f"kỳ vọng đúng 1 dòng cho {cond}, có {len(sub)}"
    return sub.iloc[0]


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    d = tmp_path_factory.mktemp("stats")
    csv = write_rows(d / "results.csv", fx.build_rows(with_errors=False))
    meta = fx.write_benign_meta(d / "benign_meta.json")
    ctx, tables, out = run_analysis([csv], d / "out", benign_meta=meta, b=B_FAST)
    return {"ctx": ctx, "tables": {t.name: t for t in tables}, "out": out, "dir": d, "csv": csv, "meta": meta}


def T(run, name: str) -> pd.DataFrame:
    return run["tables"][name].data


# --------------------------------------------------------------------------- Wilson / bootstrap

def test_wilson_known_values():
    lo, hi = wilson(0, 10)
    assert lo == 0.0 and hi == pytest.approx(0.2775, abs=1e-4)
    lo, hi = wilson(10, 10)
    assert lo == pytest.approx(0.7225, abs=1e-4) and hi == 1.0
    lo, hi = wilson(5, 10)
    assert (lo, hi) == (pytest.approx(0.2366, abs=1e-4), pytest.approx(0.7634, abs=1e-4))
    lo, hi = wilson(8, 16)  # p=0.5, n=16: tâm 0.5, nửa độ rộng 1.96*0.1392/1.2401 = 0.22
    assert (lo, hi) == (pytest.approx(0.28, abs=2e-4), pytest.approx(0.72, abs=2e-4))
    assert all(math.isnan(x) for x in wilson(0, 0))


def test_wilson_properties():
    for n in (1, 7, 40):
        for k in range(n + 1):
            lo, hi = wilson(k, n)
            assert 0.0 <= lo <= k / n <= hi <= 1.0
            lo2, hi2 = wilson(n - k, n)
            assert lo == pytest.approx(1 - hi2) and hi == pytest.approx(1 - lo2)
    assert wilson(5, 100)[1] - wilson(5, 100)[0] < wilson(5, 20)[1] - wilson(5, 20)[0]
    with pytest.raises(ValueError):
        wilson(11, 10)
    with pytest.raises(ValueError):
        wilson(-1, 10)


def test_quantile_linear():
    assert quantile([1, 2, 3, 4], 0.5) == 2.5
    assert quantile([10], 0.9) == 10
    assert math.isnan(quantile([], 0.5))


def test_bootstrap_known_cases():
    # trung bình của 2 giá trị {0,1}: phân phối bootstrap {0:25%, 0.5:50%, 1:25%} nên khoảng = [0, 1]
    assert bootstrap_mean_ci([0.0, 1.0], b=2000, seed=1) == (0.0, 1.0)
    assert bootstrap_mean_ci([0.25] * 5, b=500, seed=1) == (0.25, 0.25)
    assert bootstrap_mean_ci([0.7], b=500, seed=1) == (0.7, 0.7)
    assert all(math.isnan(x) for x in bootstrap_mean_ci([]))


def test_bootstrap_reproducible_and_seed_sensitive():
    vals = [0.0, 0.25, 0.5, 1.0, 0.75, 0.0, 0.25]
    a = bootstrap_mean_ci(vals, b=500, seed=7)
    assert a == bootstrap_mean_ci(vals, b=500, seed=7)
    bootstrap_mean_ci([1, 2, 3], b=50, seed=99)  # gọi xen kẽ không ảnh hưởng (bộ sinh riêng mỗi lần)
    assert a == bootstrap_mean_ci(vals, b=500, seed=7)
    assert a != bootstrap_mean_ci(vals, b=500, seed=8)
    lo, hi = a
    assert lo <= sum(vals) / len(vals) <= hi


def test_bootstrap_diff_paired_vs_independent():
    # a = b + 0.25 cho mọi prompt: xếp cặp cho hiệu hằng số nên khoảng suy biến, độc lập thì không
    b_vals = [0.0, 0.5, 0.25, 1.0, 0.75, 0.25, 0.5, 0.0]
    a_vals = [x + 0.25 for x in b_vals]
    d, lo, hi = bootstrap_diff_ci(a_vals, b_vals, paired=True, b=500, seed=3)
    assert (d, lo, hi) == (pytest.approx(0.25), pytest.approx(0.25), pytest.approx(0.25))
    d2, lo2, hi2 = bootstrap_diff_ci(a_vals, b_vals, paired=False, b=500, seed=3)
    assert d2 == pytest.approx(0.25) and lo2 < 0.25 < hi2
    assert bootstrap_diff_ci(a_vals, b_vals, paired=False, b=300, seed=3) == \
        bootstrap_diff_ci(a_vals, b_vals, paired=False, b=300, seed=3)
    with pytest.raises(ValueError):
        bootstrap_diff_ci([1.0], [1.0, 2.0], paired=True)
    assert all(math.isnan(x) for x in bootstrap_diff_ci([], [1.0], paired=False))


# --------------------------------------------------------------------------- Bảng 1

def test_table1_counts_and_intervals(run):
    t1 = T(run, "tab01_asr_split")
    succ = {  # tổng thành công trên 16 lượt (train, holdout) hoặc 8 lượt (test_indist), tay cộng từ ATTACK_SPEC
        "train": [8, 5, 2, 1, 0, 7, 4, 7, 5],
        "holdout": [8, 7, 6, 4, 3, 7, 7, 6, 6],
        "test_indist": [4, 3, 2, 1, 1, 3, 3, 4, 4],
    }
    runs = {"train": 16, "holdout": 16, "test_indist": 8}
    prompts = {"train": 4, "holdout": 4, "test_indist": 2}
    assert len(t1) == 27
    for split, ks in succ.items():
        for cfg, k in zip(fx.CONFIGS, ks):
            r = only(t1, split=split, config=cfg)
            assert (r.n_runs, r.n_prompts, r.n_success) == (runs[split], prompts[split], k)
            assert r.asr == pytest.approx(k / runs[split])
            assert r.asr_prompt == pytest.approx(k / runs[split])  # mẫu cân bằng nên hai ASR trùng
            lo, hi = wilson(k, runs[split])
            assert (r.wilson_lo, r.wilson_hi) == (pytest.approx(lo), pytest.approx(hi))
            assert r.boot_lo <= r.asr_prompt <= r.boot_hi


def test_table1_bootstrap_hand_case(run):
    # test_indist baseline: ASR từng prompt = [0.75, 0.25] -> bootstrap trung bình có đuôi ở 0.25 và 0.75
    r = only(T(run, "tab01_asr_split"), split="test_indist", config="baseline")
    assert (r.boot_lo, r.boot_hi) == (pytest.approx(0.25), pytest.approx(0.75))
    # train full chain: mọi prompt ASR = 0 -> khoảng suy biến
    r = only(T(run, "tab01_asr_split"), split="train", config="L1+L2+L3+L4")
    assert (r.boot_lo, r.boot_hi) == (0.0, 0.0)


# --------------------------------------------------------------------------- Bảng 2

def test_table2_breakdowns(run):
    t = T(run, "tab02_asr_attack_type")
    # train baseline: direct = TR-001 (4) + TR-002 (2) = 6/8; obfuscation = TR-003 (0) + TR-004 (2) = 2/8
    assert only(t, split="train", config="baseline", value="direct_injection").asr == pytest.approx(0.75)
    assert only(t, split="train", config="baseline", value="obfuscation").asr == pytest.approx(0.25)
    # gộp: direct baseline = TR1 4 + TR2 2 + HO1 4 + HO2 3 + IN1 3 = 16/20
    r = only(t, split="all", config="baseline", value="direct_injection")
    assert (r.n_runs, r.n_prompts, r.n_success) == (20, 5, 16)
    t = T(run, "tab02_asr_goal_type")
    r = only(t, split="holdout", config="baseline", value="leak")  # HO-001 (4) + HO-004 (0) = 4/8
    assert (r.n_runs, r.n_success, r.n_prompts) == (8, 4, 2)
    t = T(run, "tab02_asr_liu_type")
    assert only(t, split="holdout", config="baseline", value="none").asr == 0.0
    assert set(t["value"]) == {"naive", "context_ignoring", "fake_completion", "combined", "escape_characters", "none"}
    disp = run["tables"]["tab02_asr_attack_type"].display
    assert {"baseline", "L1+L2", "only_L4"} <= set(disp.columns)


# --------------------------------------------------------------------------- Bảng 3 và 4

def test_table3_cumulative_holdout(run):
    t = T(run, "tab03_cumulative")
    h = t[t["split"] == "holdout"].reset_index(drop=True)
    assert list(h["config"]) == list(fx.CONFIGS[:5])
    assert list(h["asr_prompt"]) == pytest.approx([0.5, 0.4375, 0.375, 0.25, 0.1875])
    assert math.isnan(h.loc[0, "red_abs_prev"])
    assert list(h.loc[1:, "red_abs_prev"]) == pytest.approx([0.0625, 0.0625, 0.125, 0.0625])
    assert list(h.loc[1:, "red_abs_base"]) == pytest.approx([0.0625, 0.125, 0.25, 0.3125])
    assert list(h.loc[1:, "red_rel_prev"]) == pytest.approx([0.125, 0.0625 / 0.4375, 1 / 3, 0.25])
    assert list(h.loc[1:, "red_rel_base"]) == pytest.approx([0.125, 0.25, 0.5, 0.625])
    assert list(h["added_layer"]) == ["", "L1", "L2", "L3", "L4"]
    for col in ("red_abs_prev", "red_abs_base"):
        d, lo, hi = h.loc[1:, col], h.loc[1:, col + "_lo"], h.loc[1:, col + "_hi"]
        assert ((lo <= d) & (d <= hi)).all()


def test_table3_paired_bootstrap_hand_case(run):
    t = T(run, "tab03_cumulative")
    # test_indist, baseline -> L1+L2+L3: hiệu theo prompt = [0.75-0.25, 0.25-0] = [0.5, 0.25] -> khoảng [0.25, 0.5]
    r = only(t, split="test_indist", config="L1+L2+L3")
    assert r.red_abs_base == pytest.approx(0.375)
    assert (r.red_abs_base_lo, r.red_abs_base_hi) == (pytest.approx(0.25), pytest.approx(0.5))
    # bước L1+L2+L3 -> full ở test_indist không đổi gì: hiệu 0 trên mọi prompt
    r = only(t, split="test_indist", config="L1+L2+L3+L4")
    assert (r.red_abs_prev, r.red_abs_prev_lo, r.red_abs_prev_hi, r.red_rel_prev) == (0.0, 0.0, 0.0, 0.0)


def test_table4_ablation(run):
    t = T(run, "tab04_ablation")
    # train: baseline 0.5; only_L2 = 4/16 = 0.25 -> giảm 0.25; chuỗi đầy đủ giảm 0.5 -> tỉ phần 0.5
    r = only(t, split="train", config="only_L2")
    assert r.red_abs_base == pytest.approx(0.25) and r.share_of_full == pytest.approx(0.5)
    assert r.chain_red_abs_prev == pytest.approx(0.1875)  # bước +L2 trong Bảng 3 (31.25% -> 12.5%)
    assert only(t, split="train", config="only_L1").red_abs_base == pytest.approx(0.0625)
    # holdout: only_L3 = 6/16 giảm 0.125, chuỗi đầy đủ giảm 0.3125 -> 0.4
    r = only(t, split="holdout", config="only_L3")
    assert r.red_abs_base == pytest.approx(0.125) and r.share_of_full == pytest.approx(0.4)
    assert only(t, split="holdout", config="L1+L2+L3+L4").role == "full"
    # test_indist: tổng giảm riêng lẻ 0.125+0.125+0+0 = 0.25 < giảm của chuỗi 0.375 (đồng tác động âm)
    assert "-12.5 pp" in run["tables"]["tab04_ablation"].note
    assert only(t, split="test_indist", config="only_L4").red_abs_base == 0.0


# --------------------------------------------------------------------------- Bảng 5

def test_table5_benign_tune_false_only(run):
    t = T(run, "tab05_benign")
    exp_fpr = [1, 2, 3, 3, 4, 1, 3, 1, 2]  # trên 6 lượt của BN-001/002/004
    exp_blocked = [0, 1, 2, 2, 3, 1, 2, 0, 1]
    exp_util = [3.5, 3, 2, 2.5, 2, 3.5, 2.5, 3.5, 3]
    exp_util_un = [3.5 / 6, 3 / 5, 2 / 4, 2.5 / 4, 2 / 3, 3.5 / 5, 2.5 / 4, 3.5 / 6, 3 / 5]
    assert list(t["config"]) == fx.CONFIGS
    assert set(t["n_runs"]) == {6} and set(t["n_prompts"]) == {3}
    assert list(t["fpr"]) == pytest.approx([k / 6 for k in exp_fpr])
    assert list(t["blocked_rate"]) == pytest.approx([k / 6 for k in exp_blocked])
    assert list(t["model_refused_rate"]) == pytest.approx([(f - b) / 6 for f, b in zip(exp_fpr, exp_blocked)])
    assert list(t["utility"]) == pytest.approx([u / 6 for u in exp_util])
    assert list(t["utility_unblocked"]) == pytest.approx(exp_util_un)
    lo, hi = wilson(2, 6)
    r = only(t, config="L1")
    assert (r.fpr_wilson_lo, r.fpr_wilson_hi) == (pytest.approx(lo), pytest.approx(hi))
    # L1 so với baseline: hiệu từ chối theo prompt [0, 0.5, 0] -> trung bình 1/6, khoảng [0, 0.5]
    assert r.fpr_delta_base == pytest.approx(1 / 6)
    assert (r.fpr_delta_lo, r.fpr_delta_hi) == (pytest.approx(0.0), pytest.approx(0.5))
    assert r.utility_delta_base == pytest.approx(-0.5 / 6 * 1.0)  # (3 - 3.5)/6 theo lượt = theo prompt vì cân bằng
    assert math.isnan(only(t, config="baseline").fpr_delta_base)
    assert "tune:false" in run["tables"]["tab05_benign"].note


def test_table5b_by_tune(run):
    t = T(run, "tab05b_benign_by_tune")
    r = only(t, tune="true", config="baseline")  # BN-003: ok:1 ok:0.5 -> utility 0.75, không từ chối
    assert (r.n_prompts, r.fpr, r.utility) == (1, 0.0, pytest.approx(0.75))
    assert only(t, tune="true", config="L1+L2").fpr == pytest.approx(0.5)  # BN-003 s0 bị L2 chặn


def test_table5_without_meta_uses_all_benign(tmp_path):
    csv = write_rows(tmp_path / "r.csv", fx.build_rows())
    ctx, tables, _ = run_analysis([csv], tmp_path / "o", b=B_FAST)
    t = {x.name: x for x in tables}
    assert "tab05b_benign_by_tune" not in t
    r = only(t["tab05_benign"].data, config="baseline")
    # 8 lượt: thêm BN-003 (ok:1 ok:0.5) vào 6 lượt trên -> utility (3.5 + 1.5)/8 = 0.625, từ chối 1/8
    assert (r.n_runs, r.n_prompts, r.fpr, r.utility) == (8, 4, pytest.approx(0.125), pytest.approx(0.625))
    assert "không có --benign-meta" in t["tab05_benign"].note


def test_benign_meta_missing_ids_warn(tmp_path):
    csv = write_rows(tmp_path / "r.csv", fx.build_rows())
    meta = tmp_path / "m.json"
    meta.write_text('[{"id": "BN-001", "tune": false}, {"id": "BN-002", "tune": "false"}, {"id": "BN-003", "tune": true}]')
    ctx, tables, _ = run_analysis([csv], tmp_path / "o", benign_meta=meta, b=B_FAST)
    assert any(i.code == "benign_meta_unknown" and "BN-004" in i.examples for i in ctx.issues)
    assert only({t.name: t for t in tables}["tab05_benign"].data, config="baseline").n_prompts == 2


def test_load_benign_meta(tmp_path):
    p = tmp_path / "m.json"
    p.write_text('[{"id":"A","tune":true},{"id":"B","tune":"False"},{"id":"C"}]')
    assert load_benign_meta(p) == {"A": True, "B": False, "C": None}
    p.write_text('{"id": "A"}')
    with pytest.raises(DataError):
        load_benign_meta(p)
    with pytest.raises(DataError):
        load_benign_meta(tmp_path / "none.json")


# --------------------------------------------------------------------------- Bảng 6

def test_table6_cost(run):
    t = T(run, "tab06_cost")
    # baseline benign: 8 lượt, độ trễ 1000 + 10*idx với idx in {0,1} -> TB/p50 1005, p95 1010 (nội suy)
    r = only(t, population="benign", config="baseline")
    assert (r.n_runs, r.calls_mean, r.lat_mean, r.lat_p50, r.lat_p95) == (8, 1.0, 1005.0, 1005.0, 1010.0)
    assert (r.layers_mean, r.ratio_lat_mean, r.ratio_calls) == (0.0, 1.0, 1.0)
    # baseline tấn công: 40 lượt, idx 0..3 -> TB/p50 1015, p95 = 1030
    r = only(t, population="attack", config="baseline")
    assert (r.n_runs, r.lat_mean, r.lat_p50, r.lat_p95) == (40, 1015.0, 1015.0, 1030.0)
    # chuỗi đầy đủ trên benign: số lần gọi = 2+2+0+2+0+2+2+2 = 12 / 8 = 1.5; độ trễ (8*70 + 12000 + 40)/8 = 1575
    r = only(t, population="benign", config="L1+L2+L3+L4")
    assert r.calls_mean == pytest.approx(1.5) and r.lat_mean == pytest.approx(1575.0)
    assert r.layers_mean == 70.0 and r.layers_p95 == 70.0
    assert r.ratio_lat_mean == pytest.approx(1575 / 1005) and r.ratio_calls == pytest.approx(1.5)
    assert only(t, population="benign", config="only_L4").ratio_calls == pytest.approx(2.0)
    assert only(t, population="all", config="baseline").n_runs == 48


# --------------------------------------------------------------------------- Bảng 7

def test_table7_layer_counts(run):
    t = T(run, "tab07_layers")
    r = only(t, population="train", config="L1+L2+L3+L4")
    assert (r.n_runs, r.blocked, r.n_L1, r.n_L2, r.n_L4) == (16, 10, 3, 5, 2)
    r = only(t, population="train", config="only_L2")
    assert (r.blocked, r.n_L1, r.n_L2, r.n_L4) == (6, 0, 6, 0)
    r = only(t, population="holdout", config="L1+L2+L3")
    assert (r.blocked, r.n_L1, r.n_L2) == (2, 1, 1)
    r = only(t, population="benign", config="L1+L2+L3+L4")  # tune:false: BN-001 s1 L4, BN-002 s0 L1 + s1 L4
    assert (r.n_runs, r.blocked, r.n_L1, r.n_L2, r.n_L4) == (6, 3, 1, 0, 2)
    assert only(t, population="train", config="baseline").blocked == 0


def test_table7b_increments(run):
    t = T(run, "tab07b_layer_increment")
    r = only(t, split="train", layer_added="L2")  # chặn 8/16 - 3/16 = 5/16; ASR 31.25% -> 12.5%
    assert r.d_blocked_attack == pytest.approx(5 / 16)
    assert r.red_asr == pytest.approx(0.1875)
    assert r.d_blocked_benign == pytest.approx(1 / 6) and r.d_refused_benign == pytest.approx(1 / 6)
    r = only(t, split="train", layer_added="L3")  # L3 không chặn: chặn thêm 0, nhưng ASR vẫn giảm 0.0625
    assert r.d_blocked_attack == 0.0 and r.red_asr == pytest.approx(0.0625)
    assert only(t, split="holdout", layer_added="L3").d_blocked_attack == pytest.approx(-1 / 16)  # 2/16 vs 3/16


# --------------------------------------------------------------------------- Bảng 8

def test_table8_generalization(run):
    t = T(run, "tab08_generalization")
    r = only(t, config="baseline", from_split="train", to_split="holdout")
    assert (r.asr_from, r.asr_to, r.gap) == (0.5, 0.5, 0.0)
    assert not r.ci_excludes_0
    r = only(t, config="L1+L2+L3+L4", from_split="train", to_split="holdout")
    assert (r.n_prompts_from, r.n_prompts_to) == (4, 4)
    assert (r.asr_from, r.asr_to) == (0.0, pytest.approx(0.1875))
    assert r.gap == pytest.approx(0.1875)
    assert r.gap_lo == 0.0 and r.gap_hi > r.gap  # train toàn 0; holdout trung bình có thể rơi về 0 khi resample
    r = only(t, config="L1+L2+L3", from_split="train", to_split="holdout")
    assert r.gap == pytest.approx(0.25 - 0.0625)
    assert only(t, config="baseline", from_split="train", to_split="test_indist").n_prompts_to == 2


# --------------------------------------------------------------------------- Bảng 9

def test_table9_dead_prompts(run):
    lst = T(run, "tab09b_dead_list")
    assert set(lst["prompt_id"]) == {"TR-003", "HO-004"}
    assert set(lst["attack_type"]) == {"obfuscation"}
    assert set(lst["n_baseline_runs"]) == {4}
    s = T(run, "tab09a_dead_summary")
    r = only(s, split="all", dimension="tổng")
    assert (r.n_prompts, r.n_dead, r.dead_rate) == (10, 2, 0.2)
    r = only(s, split="all", dimension="attack_type", value="obfuscation")
    assert (r.n_prompts, r.n_dead) == (5, 2)
    assert only(s, split="all", dimension="attack_type", value="direct_injection").n_dead == 0
    assert only(s, split="test_indist", dimension="tổng").n_dead == 0


def test_table9_effective_asr(run):
    t = T(run, "tab09c_effective_asr")
    # train còn TR-001, TR-002, TR-004: baseline (1 + 0.5 + 0.5)/3, L1 (0.5 + 0.25 + 0.5)/3, chuỗi đầy đủ 0
    r = only(t, split="train", config="baseline")
    assert (r.n_alive_prompts, r.n_dead_prompts) == (3, 1)
    assert r.asr_prompt == pytest.approx(2 / 3) and r.asr == pytest.approx(8 / 12)
    assert (r.n_runs, r.n_success) == (12, 8)
    assert r.asr_prompt_unconditional == pytest.approx(0.5)
    assert only(t, split="train", config="L1").asr_prompt == pytest.approx(1.25 / 3)
    assert only(t, split="train", config="L1+L2+L3+L4").asr_prompt == 0.0
    # holdout còn HO-001..003: baseline (1 + 0.75 + 0.25)/3 = 2/3
    assert only(t, split="holdout", config="baseline").asr_prompt == pytest.approx(2 / 3)
    assert only(t, split="test_indist", config="baseline").n_dead_prompts == 0


def test_no_baseline_skips_dead_and_reference(tmp_path):
    rows = [r for r in fx.build_rows() if r["config"] != "baseline"]
    csv = write_rows(tmp_path / "r.csv", rows)
    ctx, tables, out = run_analysis([csv], tmp_path / "o", b=B_FAST)
    names = {t.name for t in tables}
    assert not any(n.startswith("tab09") for n in names)
    assert "tab09_dead_prompts" in ctx.skipped
    cum = {t.name: t for t in tables}["tab03_cumulative"].data
    assert "baseline" not in set(cum["config"])
    assert cum[cum["config"] == "L1"]["red_abs_base"].isna().all()
    assert "Bảng bị bỏ qua" in (out / "report.md").read_text(encoding="utf-8")


# --------------------------------------------------------------------------- Bảng 10 và lỗi

def test_error_rows_excluded_and_reported(tmp_path):
    clean = write_rows(tmp_path / "clean.csv", fx.build_rows())
    dirty = write_rows(tmp_path / "dirty.csv", fx.build_rows(with_errors=True))
    _, t_clean, _ = run_analysis([clean], tmp_path / "a", b=B_FAST)
    ctx, t_dirty, _ = run_analysis([dirty], tmp_path / "b", b=B_FAST)
    a, b = {t.name: t for t in t_clean}, {t.name: t for t in t_dirty}
    for name in ("tab01_asr_split", "tab03_cumulative", "tab05_benign", "tab06_cost", "tab07_layers"):
        pd.testing.assert_frame_equal(a[name].data, b[name].data)  # dòng lỗi không ảnh hưởng mẫu
    e = b["tab10_errors"].data
    r = only(e, config="(tổng)", label="all")
    assert (r.n_rows, r.n_error, r.n_valid) == (435, 3, 432)
    r = only(e, config="baseline", label="attack")  # 40 hợp lệ + 1 timeout
    assert (r.n_rows, r.n_error) == (41, 1) and r.over_threshold
    assert r.error_rate == pytest.approx(1 / 41)
    assert only(e, config="L1+L2+L3", label="all").n_error == 0
    types = b["tab10b_error_types"].data
    assert dict(zip(types["error"], types["count"])) == {"timeout": 2, "model_error: 500": 1}
    assert any(i.code == "error_rate_config" for i in ctx.issues)
    assert not any(i.code == "unbalanced_samples" for i in ctx.issues)
    assert "tab10b_error_types" not in a


def test_high_error_rate_warns(tmp_path):
    rows = fx.build_rows()
    for r in rows[:30]:
        r.update(error="timeout", blocked="", blocked_by="", attack_success="", utility_score="",
                 model_refused="", n_model_calls="", latency_ms_total="", latency_ms_layers="")
    loaded = load_results([write_rows(tmp_path / "r.csv", rows)])
    codes = {i.code for i in loaded.issues}
    assert "error_rate" in codes and "unbalanced_samples" in codes
    assert len(loaded.valid) == len(rows) - 30


# --------------------------------------------------------------------------- Dữ liệu bẩn

def _first(rows, **cond):
    return next(r for r in rows if all(r[k] == v for k, v in cond.items()))


def _m_benign_success(rows):
    _first(rows, label="benign")["attack_success"] = 0


def _m_blocked_but_success(rows):
    _first(rows, blocked_by="L1", label="attack")["attack_success"] = 1


def _m_bad_blocked(rows):
    _first(rows, label="attack")["blocked"] = "x"


def _m_blocked_by_l3(rows):
    r = _first(rows, config="L1+L2+L3", label="attack")
    r.update(blocked=1, blocked_by="L3", attack_success=0)


def _m_layer_not_in_config(rows):
    r = _first(rows, config="L1", label="attack", blocked=0)
    r.update(blocked=1, blocked_by="L2", attack_success=0)


def _m_duplicate(rows):
    rows.append(dict(rows[0]))


def _m_inconsistent(rows):
    _first(rows, prompt_id="TR-001", config="L1")["attack_type"] = "obfuscation"


def _m_layer_without_block(rows):
    _first(rows, label="attack", blocked=0)["blocked_by"] = "L1"


def _m_blocked_without_layer(rows):
    r = _first(rows, config="L1", label="attack", blocked=0)
    r.update(blocked=1, attack_success=0)


def _m_benign_blocked_utility(rows):
    _first(rows, blocked_by="L1", label="benign")["utility_score"] = 0.5


def _m_utility_range(rows):
    _first(rows, label="benign", blocked=0)["utility_score"] = 1.5


def _m_label_split(rows):
    _first(rows, label="attack")["split"] = "benign"


def _m_negative_latency(rows):
    _first(rows, label="attack")["latency_ms_total"] = -5


def _m_baseline_blocked(rows):
    r = _first(rows, config="baseline", label="attack")
    r.update(blocked=1, blocked_by="L1", attack_success=0)


def _m_success_missing(rows):
    _first(rows, label="attack", blocked=0)["attack_success"] = ""


def _m_calls_float(rows):
    _first(rows, label="attack")["n_model_calls"] = 1.5


def _m_empty_config(rows):
    _first(rows, label="attack")["config"] = ""


DIRTY = [
    (_m_benign_success, "benign_has_attack_success"),
    (_m_blocked_but_success, "blocked_but_success"),
    (_m_bad_blocked, "bad_numeric"),
    (_m_blocked_by_l3, "bad_blocked_by"),
    (_m_layer_not_in_config, "layer_not_in_config"),
    (_m_duplicate, "duplicate_key"),
    (_m_inconsistent, "inconsistent_prompt_meta"),
    (_m_layer_without_block, "layer_without_block"),
    (_m_blocked_without_layer, "blocked_without_layer"),
    (_m_benign_blocked_utility, "blocked_benign_utility_nonzero"),
    (_m_utility_range, "benign_utility_missing"),
    (_m_label_split, "label_split_mismatch"),
    (_m_negative_latency, "bad_latency"),
    (_m_baseline_blocked, "baseline_blocked"),
    (_m_success_missing, "attack_success_missing"),
    (_m_calls_float, "bad_integer"),
    (_m_empty_config, "empty_identity"),
]


@pytest.mark.parametrize("mutate,code", DIRTY, ids=[c for _, c in DIRTY])
def test_dirty_data_rejected_with_clear_error(tmp_path, mutate, code):
    rows = fx.build_rows()
    mutate(rows)
    path = write_rows(tmp_path / "r.csv", rows)
    _, issues = check_input(read_csvs([path]))
    assert code in {i.code for i in issues if i.level == "error"}, [i.code for i in issues]
    with pytest.raises(DataError) as exc:
        load_results([path])
    assert code in str(exc.value)
    assert main([str(path), "--out", str(tmp_path / "o")]) == 2
    assert not (tmp_path / "o" / "report.md").exists()


def test_missing_column_and_empty_file(tmp_path, capsys):
    path = write_rows(tmp_path / "r.csv", fx.build_rows(), drop="goal_type")
    with pytest.raises(DataError, match="thiếu cột bắt buộc.*goal_type"):
        load_results([path])
    assert main([str(path), "--out", str(tmp_path / "o")]) == 2
    assert "goal_type" in capsys.readouterr().err
    empty = tmp_path / "e.csv"
    empty.write_text(",".join(fx.COLUMNS) + "\n", encoding="utf-8")
    with pytest.raises(DataError, match="không có dòng"):
        load_results([empty])
    with pytest.raises(DataError, match="Không tìm thấy"):
        load_results([tmp_path / "missing.csv"])


def test_error_rows_may_omit_result_columns(tmp_path):
    loaded = load_results([write_rows(tmp_path / "r.csv", fx.build_rows(with_errors=True))])
    assert int(loaded.rows["is_error"].sum()) == 3
    assert not [i for i in loaded.issues if i.level == "error"]


def test_all_rows_error_rejected(tmp_path):
    rows = fx.error_rows()
    with pytest.raises(DataError, match="Mọi dòng"):
        load_results([write_rows(tmp_path / "r.csv", rows)])


def test_warnings_not_errors(tmp_path):
    rows = fx.build_rows()
    _first(rows, label="attack")["latency_ms_layers"] = 1e9  # lớp lâu hơn tổng
    _first(rows, label="attack")["utility_score"] = 0.5
    loaded = load_results([write_rows(tmp_path / "r.csv", rows)])
    codes = {i.code for i in loaded.issues}
    assert {"layers_latency_exceeds_total", "attack_has_utility"} <= codes


def test_multiple_models(tmp_path):
    rows = fx.build_rows()
    for r in rows[::2]:
        r["model"] = "other-model"
    path = write_rows(tmp_path / "r.csv", rows)
    with pytest.raises(DataError, match="nhiều model"):
        load_results([path])
    assert set(load_results([path], model="other-model").rows["model"]) == {"other-model"}
    with pytest.raises(DataError, match="--model"):
        load_results([path], model="zzz")


def test_merge_files_and_duplicates(tmp_path):
    rows = fx.build_rows()
    a = [r for r in rows if r["split"] in ("train", "benign")]
    b = [dict(r, run_id="fx-2") for r in rows if r["split"] not in ("train", "benign")]
    pa, pb = write_rows(tmp_path / "a.csv", a), write_rows(tmp_path / "b.csv", b)
    whole = write_rows(tmp_path / "all.csv", rows)
    _, t_merge, _ = run_analysis([pa, pb], tmp_path / "m", b=B_FAST)
    _, t_whole, _ = run_analysis([whole], tmp_path / "w", b=B_FAST)
    m, w = {t.name: t for t in t_merge}, {t.name: t for t in t_whole}
    for name in ("tab01_asr_split", "tab03_cumulative", "tab08_generalization", "tab09c_effective_asr"):
        pd.testing.assert_frame_equal(m[name].data, w[name].data)
    with pytest.raises(DataError, match="duplicate_key"):
        load_results([pa, pa])


def test_same_prompt_two_runs_pooled(tmp_path):
    rows = fx.build_rows()
    again = [dict(r, run_id="fx-2") for r in rows]
    ctx, tables, _ = run_analysis([write_rows(tmp_path / "a.csv", rows + again)], tmp_path / "o", b=B_FAST)
    r = only({t.name: t for t in tables}["tab01_asr_split"].data, split="train", config="baseline")
    assert (r.n_runs, r.n_prompts, r.n_success, r.asr) == (32, 4, 16, 0.5)


def test_config_helpers():
    assert config_layers("baseline") == frozenset()
    assert config_layers("L1+L2") == {"L1", "L2"}
    assert config_layers("only_L3") == {"L3"}
    assert config_layers("weird") is None
    assert order_configs(["only_L2", "zzz", "L1+L2", "baseline", "L1", "aaa"]) == \
        ["baseline", "L1", "L1+L2", "only_L2", "aaa", "zzz"]


# --------------------------------------------------------------------------- Tái lập, đầu ra, hiệu năng

def test_outputs_reproducible_and_seed_changes_only_intervals(tmp_path, run):
    ctx2, _, out2 = run_analysis([run["csv"]], tmp_path / "again", benign_meta=run["meta"], b=B_FAST)
    for p in sorted((run["out"] / "csv").glob("*.csv")):
        assert p.read_bytes() == (out2 / "csv" / p.name).read_bytes(), p.name
    for p in sorted((run["out"] / "dat").glob("*.dat")):
        assert p.read_bytes() == (out2 / "dat" / p.name).read_bytes(), p.name
    _, t3, _ = run_analysis([run["csv"]], tmp_path / "seed", benign_meta=run["meta"], b=B_FAST, seed=1)
    base = T(run, "tab01_asr_split")
    other = {t.name: t for t in t3}["tab01_asr_split"].data
    assert list(base["asr"]) == list(other["asr"])
    assert list(base["boot_lo"]) != list(other["boot_lo"]) or list(base["boot_hi"]) != list(other["boot_hi"])


def test_expected_files_and_latex(run):
    out = run["out"]
    for name in ("tab01_asr_split", "tab02_asr_attack_type", "tab03_cumulative", "tab04_ablation",
                 "tab05_benign", "tab06_cost", "tab07_layers", "tab07b_layer_increment",
                 "tab08_generalization", "tab09a_dead_summary", "tab09b_dead_list",
                 "tab09c_effective_asr", "tab10_errors"):
        for sub, ext in (("tables", "tex"), ("csv", "csv"), ("md", "md")):
            assert (out / sub / f"{name}.{ext}").is_file(), (sub, name)
    for split in ("train", "holdout", "test_indist"):
        assert (out / "tables" / f"tab03_cumulative_{split}.tex").is_file()
    tex = (out / "tables" / "tab03_cumulative.tex").read_text(encoding="utf-8")
    assert "\\toprule" in tex and "\\midrule" in tex and "\\bottomrule" in tex
    assert tex.count("\\begin{tabular}") == 1 and tex.count("\\end{tabular}") == 1
    body = tex.split("\\toprule", 1)[1]
    assert "%" not in body.replace("\\%", "")  # mọi % trong thân đã thoát
    holdout = (out / "tables" / "tab03_cumulative_holdout.tex").read_text(encoding="utf-8")
    assert "train" not in holdout and "L1+L2+L3+L4" in holdout


def test_dat_files(run):
    out = run["out"] / "dat"
    lines = (out / "asr_holdout.dat").read_text(encoding="utf-8").splitlines()
    header = lines[0].split()
    assert header[:3] == ["idx", "config", "label"] and len(lines) == 10
    rows = [dict(zip(header, ln.split())) for ln in lines[1:]]
    assert len(set(len(ln.split()) for ln in lines)) == 1  # mọi hàng cùng số cột, không có khoảng trắng thừa
    assert rows[0]["config"] == "baseline" and float(rows[0]["asr"]) == pytest.approx(50.0)
    lo, hi = wilson(8, 16)
    assert float(rows[0]["w_lo"]) == pytest.approx(100 * lo, abs=1e-3)
    assert float(rows[0]["w_plus"]) == pytest.approx(100 * (hi - 0.5), abs=1e-3)
    assert rows[6]["label"] == "only\\_L2"
    b = (out / "benign.dat").read_text(encoding="utf-8").splitlines()
    assert float(dict(zip(b[0].split(), b[1].split()))["fpr"]) == pytest.approx(100 / 6, abs=1e-3)
    for name in ("latency_benign", "latency_attack", "latency_all"):
        assert (out / f"{name}.dat").is_file()
    assert float(dict(zip(*[x.split() for x in (out / "latency_benign.dat").read_text().splitlines()[:2]]))["lat_mean"]) == 1005.0


def test_report_contents(run):
    text = (run["out"] / "report.md").read_text(encoding="utf-8")
    for needle in ("Ghi chú phương pháp", "Wilson", "Bootstrap", "lạc quan", "Bảng 1.", "Bảng 3.", "Bảng 4.",
                   "Bảng 5.", "Bảng 6.", "Bảng 7a.", "Bảng 7b.", "Bảng 8.", "Bảng 9a.", "Bảng 9c.", "Bảng 10.",
                   "seed=", "xếp cặp", "độc lập"):
        assert needle in text, needle
    assert text.count("| --- ") > 10


def test_render_helpers():
    assert render.escape_tex("a_b 50% & #1") == r"a\_b 50\% \& \#1"
    assert render.pct(0.3125) == "31.3" and render.pct(float("nan")) == "n/a"
    assert render.signed_pp(-0.00001) == "0.0" and render.signed_pp(0.0625) == "+6.3"
    df = pd.DataFrame({"a": ["x|y", "z"], "b": ["1.0", "2.5"]})
    md = render.md_table(df)
    assert "x\\|y" in md and "---:" in md
    assert render.dat_text(pd.DataFrame({"c": ["a", "b"], "v": [1.0, float("nan")]})) == "c v\na 1\nb nan\n"
    with pytest.raises(ValueError):
        render.dat_text(pd.DataFrame({"c": ["a b"]}))


def test_cli_default_out_dir(tmp_path, capsys):
    csv = write_rows(tmp_path / "results.csv", fx.build_rows(with_errors=True))
    assert main([str(csv), "--B", "50"]) == 0
    assert (tmp_path / "analysis" / "report.md").is_file()
    captured = capsys.readouterr()
    assert "435 dòng" in captured.out and "CẢNH BÁO" in captured.err


def test_attack_only_and_benign_only(tmp_path):
    rows = fx.build_rows()
    _, t, _ = run_analysis([write_rows(tmp_path / "a.csv", [r for r in rows if r["label"] == "attack"])],
                           tmp_path / "oa", b=B_FAST)
    names = {x.name for x in t}
    assert "tab01_asr_split" in names and "tab05_benign" not in names and "tab07b_layer_increment" in names
    _, t, out = run_analysis([write_rows(tmp_path / "b.csv", [r for r in rows if r["label"] == "benign"])],
                             tmp_path / "ob", b=B_FAST)
    names = {x.name for x in t}
    assert "tab05_benign" in names and "tab01_asr_split" not in names and "tab08_generalization" not in names
    assert (out / "report.md").is_file()


def test_performance_large_input(tmp_path):
    rows = fx.build_large_rows(n_attack=300, n_benign=100, samples=10, seed=0)
    assert len(rows) == 36000
    csv = write_rows(tmp_path / "big.csv", rows)
    t0 = time.perf_counter()
    ctx, tables, out = run_analysis([csv], tmp_path / "o")  # B mặc định 2000
    elapsed = time.perf_counter() - t0
    assert elapsed < 120, f"quá chậm: {elapsed:.1f}s"
    assert len(ctx.valid) == 36000 and (out / "report.md").is_file()
