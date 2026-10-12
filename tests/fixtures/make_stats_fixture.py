"""Sinh CSV tổng hợp có giá trị biết trước để kiểm tra analysis.stats.

Dữ liệu nhỏ, mọi con số tay tính được (xem tests/test_stats.py):
- 10 prompt tấn công (train 4, holdout 4, test_indist 2), 4 lượt mỗi prompt.
- 4 prompt benign (BN-003 là `tune:true`), 2 lượt mỗi prompt.
- 9 cấu hình: chuỗi cộng dồn (5) và only_L1..only_L4.

Mỗi ô của ATTACK_SPEC là (thành công, bị L1 chặn, bị L2 chặn, bị L4 chặn) trong 4 lượt;
phần còn lại là "model không bị chiếm, không bị chặn".

Chạy: python3 tests/fixtures/make_stats_fixture.py out.csv [--errors] [--meta meta.json]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

COLUMNS = [
    "run_id", "model", "config", "prompt_id", "split", "label", "attack_type", "liu_type",
    "technique", "goal_type", "sample_idx", "temperature", "blocked", "blocked_by",
    "attack_success", "model_refused", "utility_score", "n_model_calls", "latency_ms_total",
    "latency_ms_layers", "error",
]
CONFIGS = ["baseline", "L1", "L1+L2", "L1+L2+L3", "L1+L2+L3+L4",
           "only_L1", "only_L2", "only_L3", "only_L4"]
LAYER_LATENCY = {"baseline": 0, "L1": 5, "L1+L2": 20, "L1+L2+L3": 25, "L1+L2+L3+L4": 70,
                 "only_L1": 5, "only_L2": 15, "only_L3": 5, "only_L4": 50}
HAS_L4 = {"L1+L2+L3+L4", "only_L4"}
N_ATTACK_SAMPLES = 4
N_BENIGN_SAMPLES = 2

# id: (split, attack_type, liu_type, technique, goal_type, [spec theo thứ tự CONFIGS])
ATTACK_SPEC: dict[str, tuple] = {
    "TR-001": ("train", "direct_injection", "context_ignoring", "ignore_previous", "leak", [
        (4, 0, 0, 0), (2, 2, 0, 0), (1, 2, 1, 0), (0, 2, 1, 0), (0, 2, 1, 1),
        (3, 1, 0, 0), (2, 0, 2, 0), (3, 0, 0, 0), (2, 0, 0, 2)]),
    "TR-002": ("train", "direct_injection", "naive", "polite_request", "integrity", [
        (2, 0, 0, 0), (1, 1, 0, 0), (0, 1, 1, 0), (0, 1, 1, 0), (0, 1, 1, 0),
        (2, 0, 0, 0), (1, 0, 1, 0), (2, 0, 0, 0), (1, 0, 0, 1)]),
    "TR-003": ("train", "obfuscation", "combined", "base64", "leak", [
        (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 1, 0), (0, 0, 1, 0), (0, 0, 1, 0),
        (0, 0, 0, 0), (0, 0, 1, 0), (0, 0, 0, 0), (0, 0, 0, 0)]),
    "TR-004": ("train", "obfuscation", "fake_completion", "tool_hijack", "tool_action", [
        (2, 0, 0, 0), (2, 0, 0, 0), (1, 0, 2, 0), (1, 0, 2, 0), (0, 0, 2, 1),
        (2, 0, 0, 0), (1, 0, 2, 0), (2, 0, 0, 0), (2, 0, 0, 0)]),
    "HO-001": ("holdout", "direct_injection", "naive", "ignore_previous", "leak", [
        (4, 0, 0, 0), (3, 1, 0, 0), (3, 1, 0, 0), (2, 1, 0, 0), (2, 1, 0, 1),
        (3, 1, 0, 0), (4, 0, 0, 0), (3, 0, 0, 0), (3, 0, 0, 1)]),
    "HO-002": ("holdout", "direct_injection", "context_ignoring", "polite_request", "integrity", [
        (3, 0, 0, 0), (3, 0, 0, 0), (2, 0, 1, 0), (2, 0, 1, 0), (1, 0, 1, 1),
        (3, 0, 0, 0), (2, 0, 1, 0), (3, 0, 0, 0), (2, 0, 0, 1)]),
    "HO-003": ("holdout", "obfuscation", "combined", "tool_hijack", "tool_action", [
        (1, 0, 0, 0), (1, 0, 0, 0), (1, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0),
        (1, 0, 0, 0), (1, 0, 0, 0), (0, 0, 0, 0), (1, 0, 0, 0)]),
    "HO-004": ("holdout", "obfuscation", "none", "base64", "leak", [
        (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 1, 0), (0, 0, 0, 0), (0, 0, 1, 0),
        (0, 0, 0, 0), (0, 0, 1, 0), (0, 0, 0, 0), (0, 0, 0, 0)]),
    "IN-001": ("test_indist", "direct_injection", "naive", "ignore_previous", "leak", [
        (3, 0, 0, 0), (2, 1, 0, 0), (2, 1, 0, 0), (1, 1, 0, 0), (1, 1, 0, 0),
        (2, 1, 0, 0), (3, 0, 0, 0), (3, 0, 0, 0), (3, 0, 0, 0)]),
    "IN-002": ("test_indist", "obfuscation", "escape_characters", "base64", "integrity", [
        (1, 0, 0, 0), (1, 0, 0, 0), (0, 0, 1, 0), (0, 0, 1, 0), (0, 0, 1, 0),
        (1, 0, 0, 0), (0, 0, 1, 0), (1, 0, 0, 0), (1, 0, 0, 0)]),
}

# Token: ok:<utility> | ref:<utility> (model tự từ chối) | L1/L2/L4 (bị chặn, utility 0)
BENIGN_SPEC: dict[str, dict[str, str]] = {
    "baseline": {"BN-001": "ok:1 ok:1", "BN-002": "ok:0.5 ok:0.5", "BN-003": "ok:1 ok:0.5", "BN-004": "ref:0 ok:0.5"},
    "L1": {"BN-001": "ok:1 ok:1", "BN-002": "L1 ok:0.5", "BN-003": "ok:1 ok:0.5", "BN-004": "ref:0 ok:0.5"},
    "L1+L2": {"BN-001": "ok:1 L2", "BN-002": "L1 ok:0.5", "BN-003": "L2 ok:0.5", "BN-004": "ref:0 ok:0.5"},
    "L1+L2+L3": {"BN-001": "ok:1 L2", "BN-002": "L1 ok:0.5", "BN-003": "ok:1 ok:0.5", "BN-004": "ref:0 ok:1"},
    "L1+L2+L3+L4": {"BN-001": "ok:1 L4", "BN-002": "L1 L4", "BN-003": "L2 ok:0.5", "BN-004": "ref:0 ok:1"},
    "only_L1": {"BN-001": "ok:1 ok:1", "BN-002": "ok:0.5 ok:0.5", "BN-003": "ok:1 ok:0.5", "BN-004": "L1 ok:0.5"},
    "only_L2": {"BN-001": "ok:1 ok:1", "BN-002": "L2 L2", "BN-003": "ok:1 ok:0.5", "BN-004": "ref:0 ok:0.5"},
    "only_L3": {"BN-001": "ok:1 ok:1", "BN-002": "ok:0.5 ok:0.5", "BN-003": "ok:1 ok:0.5", "BN-004": "ref:0 ok:0.5"},
    "only_L4": {"BN-001": "ok:1 ok:1", "BN-002": "ok:0.5 L4", "BN-003": "ok:1 ok:0.5", "BN-004": "ref:0 ok:0.5"},
}
BENIGN_TUNE = {"BN-001": False, "BN-002": False, "BN-003": True, "BN-004": False}


def _base_row(config: str, prompt_id: str, split: str, label: str, meta: tuple, idx: int) -> dict:
    attack_type, liu_type, technique, goal_type = meta
    return {"run_id": "fx-1", "model": "fixture-model", "config": config, "prompt_id": prompt_id,
            "split": split, "label": label, "attack_type": attack_type, "liu_type": liu_type,
            "technique": technique, "goal_type": goal_type, "sample_idx": idx, "temperature": 0.7,
            "attack_success": "", "utility_score": "", "model_refused": 0, "error": ""}


def _finish(row: dict, config: str, blocked_by: str) -> dict:
    calls = 0 if blocked_by in ("L1", "L2") else (2 if config in HAS_L4 else 1)
    layers = LAYER_LATENCY[config]
    row.update(blocked=int(bool(blocked_by)), blocked_by=blocked_by, n_model_calls=calls,
               latency_ms_layers=layers, latency_ms_total=layers + 1000 * calls + 10 * row["sample_idx"])
    return row


def attack_rows() -> list[dict]:
    rows = []
    for pid, (split, atype, liu, tech, goal, spec) in ATTACK_SPEC.items():
        for ci, config in enumerate(CONFIGS):
            succ, b1, b2, b4 = spec[ci]
            assert succ + b1 + b2 + b4 <= N_ATTACK_SAMPLES, (pid, config)
            seq = ["L1"] * b1 + ["L2"] * b2 + ["L4"] * b4 + ["S"] * succ
            seq += ["N"] * (N_ATTACK_SAMPLES - len(seq))
            for idx, tag in enumerate(seq):
                row = _base_row(config, pid, split, "attack", (atype, liu, tech, goal), idx)
                row["attack_success"] = int(tag == "S")
                row["model_refused"] = int(tag == "N")
                rows.append(_finish(row, config, tag if tag in ("L1", "L2", "L4") else ""))
    return rows


def benign_rows() -> list[dict]:
    rows = []
    for config in CONFIGS:
        for pid, tokens in BENIGN_SPEC[config].items():
            for idx, tok in enumerate(tokens.split()):
                row = _base_row(config, pid, "benign", "benign", ("none", "none", "none", "none"), idx)
                kind, _, val = tok.partition(":")
                blocked_by = tok if kind in ("L1", "L2", "L4") else ""
                row["utility_score"] = float(val) if val else 0.0
                row["model_refused"] = int(kind == "ref")
                rows.append(_finish(row, config, blocked_by))
    return rows


def error_rows() -> list[dict]:
    """Ba dòng lỗi; harness thật có thể để trống các cột kết quả khi lỗi."""
    def err(config, pid, split, label, meta, idx, msg):
        r = _base_row(config, pid, split, label, meta, idx)
        r.update(blocked="", blocked_by="", model_refused="", n_model_calls="", latency_ms_total="",
                 latency_ms_layers="", error=msg)
        return r
    atk = ATTACK_SPEC["TR-001"]
    ho = ATTACK_SPEC["HO-001"]
    return [
        err("baseline", "TR-001", "train", "attack", atk[1:5], 4, "timeout"),
        err("L1+L2", "HO-001", "holdout", "attack", ho[1:5], 4, "timeout"),
        err("L1", "BN-001", "benign", "benign", ("none",) * 4, 2, "model_error: 500"),
    ]


def build_rows(with_errors: bool = False) -> list[dict]:
    rows = attack_rows() + benign_rows()
    return rows + error_rows() if with_errors else rows


def build_large_rows(n_attack: int = 300, n_benign: int = 100, samples: int = 10, seed: int = 0) -> list[dict]:
    """Dữ liệu ngẫu nhiên hợp lệ theo hợp đồng để thử hiệu năng (không có giá trị biết trước)."""
    rng = random.Random(seed)
    splits = ["train", "holdout", "test_indist"]
    types = ["direct_injection", "indirect_injection", "jailbreak_roleplay", "code_switching_translation",
             "obfuscation", "many_shot_jailbreaking"]
    lius = ["naive", "escape_characters", "context_ignoring", "fake_completion", "combined", "none"]
    goals = ["leak", "integrity", "tool_action"]
    rows = []
    for i in range(n_attack):
        split = splits[i % 3]
        meta = (rng.choice(types), rng.choice(lius), f"tech{i % 17}", rng.choice(goals))
        p = rng.random()
        prefix = {"train": "TR", "holdout": "HO", "test_indist": "IN"}[split]
        pid = f"{prefix}-{i:04d}"
        for config in CONFIGS:
            asr = p if config == "baseline" else 0.3 * p
            for s in range(samples):
                row = _base_row(config, pid, split, "attack", meta, s)
                blocked_by = "L1" if "L1" in config and rng.random() < 0.1 else ""
                success = 0 if blocked_by else int(rng.random() < asr)
                row["attack_success"] = success
                rows.append(_finish(row, config, blocked_by))
    for i in range(n_benign):
        pid = f"BN-{i:04d}"
        for config in CONFIGS:
            for s in range(samples):
                row = _base_row(config, pid, "benign", "benign", ("none",) * 4, s)
                blocked_by = "L2" if "L2" in config and rng.random() < 0.05 else ""
                row["utility_score"] = 0.0 if blocked_by else rng.choice([0.5, 0.75, 1.0])
                rows.append(_finish(row, config, blocked_by))
    return rows


def write_csv(path: str | Path, rows: list[dict]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return path


def write_benign_meta(path: str | Path) -> Path:
    path = Path(path)
    path.write_text(json.dumps(
        [{"id": k, "split": "benign", "label": "benign", "tune": v} for k, v in BENIGN_TUNE.items()],
        ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--errors", action="store_true", help="thêm 3 dòng lỗi/timeout")
    ap.add_argument("--meta", help="ghi thêm benign_meta.json vào đường dẫn này")
    args = ap.parse_args()
    write_csv(args.out, build_rows(args.errors))
    if args.meta:
        write_benign_meta(args.meta)


if __name__ == "__main__":
    main()
