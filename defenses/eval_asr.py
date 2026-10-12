#!/usr/bin/env python3
"""defenses/eval_asr.py — harness đo ASR cộng dồn qua các lớp phòng thủ (hợp đồng chung).

Pipeline mỗi lượt: L1 → L2 → L3 → model → L4 (xem docs/hop-dong-chung.md, mục 2).
Mỗi dòng kết quả = (config, prompt, sample_idx) với đúng 21 cột của hợp đồng mục 3.

Ví dụ:
  python3 defenses/eval_asr.py --configs baseline --splits train,benign --samples 3
  python3 defenses/eval_asr.py --configs baseline,L1,L1+L2,L1+L2+L3,L1+L2+L3+L4 \
      --out results/20261012-1 --resume
  # Chỉ cho cấu hình cuối, một lần (cùng cờ cho holdout và hai split ngoài ext_attack, ext_benign):
  python3 defenses/eval_asr.py --configs baseline,L1+L2+L3+L4 --splits holdout \
      --confirm-final-holdout
  python3 defenses/eval_asr.py --configs baseline,L1+L2+L3+L4 --splits ext_attack,ext_benign \
      --confirm-final-holdout

Đầu ra trong `--out`: results.csv, outputs.jsonl, run_config.json.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import json
import math
import os
import subprocess
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baseline_agent import agent as agent_mod  # noqa: E402
from baseline_agent.agent import BaselineAgent, OllamaClient  # noqa: E402
from defenses import base, success, utility  # noqa: E402

CSV_COLUMNS = [
    "run_id", "model", "config", "prompt_id", "split", "label", "attack_type", "liu_type",
    "technique", "goal_type", "sample_idx", "temperature", "blocked", "blocked_by",
    "attack_success", "model_refused", "utility_score", "n_model_calls",
    "latency_ms_total", "latency_ms_layers", "error",
]
DEFAULT_CONFIGS = "baseline,L1,L1+L2,L1+L2+L3,L1+L2+L3+L4"
SPLIT_FILES = {
    "train": "train_prompts.json",
    "holdout": "holdout_prompts.json",
    "benign": "benign_prompts.json",
    "test_indist": "test_indist_prompts.json",
    "ext_attack": "ext_attack_prompts.json",
    "ext_benign": "ext_benign_prompts.json",
}
# Các split chỉ được chạy một lần cho cấu hình cuối: hold-out và dữ liệu ngoài (zero-shot, không dùng chỉnh tham số).
FINAL_ONLY_SPLITS = ("holdout", "ext_attack", "ext_benign")
EXT_SPLITS = ("ext_attack", "ext_benign")
SCORABLE_CHECKS = ("canary_leak", "contains", "regex", "tool_call")
LAYER_MODULES = {
    "L1": "defenses.layer1_filtering",
    "L2": "defenses.layer2_refusal_classifier",
    "L3": "defenses.layer3_instruction_hierarchy",
    "L4": "defenses.layer4_consistency_check",
}
BLOCKED_TEXT = "[BLOCKED]"
MAX_CONSECUTIVE_ERRORS = 5
GIT_TIMEOUT_S = 10


class HarnessError(RuntimeError):
    """Lỗi cấu hình/đầu vào cần báo rõ cho người chạy (không phải lỗi từng lượt)."""


# --------------------------------------------------------------------------- cấu hình

def parse_config(name: str) -> tuple[str, ...]:
    """'baseline' → (); 'L1+L2' → ('L1','L2'); 'only_L3' → ('L3',). Thứ tự luôn L1<L2<L3<L4."""
    if name == "baseline":
        return ()
    only = name.startswith("only_")
    parts = (name[5:] if only else name).split("+")
    if any(p not in LAYER_MODULES for p in parts) or len(set(parts)) != len(parts) \
            or (only and len(parts) != 1):
        raise HarnessError(
            f"Cấu hình không hợp lệ: {name!r} (dùng baseline, L1, L1+L2, ..., only_L2, ...)")
    return tuple(sorted(parts))


def load_layers(names: set[str]) -> dict[str, Any]:
    """Nạp động các lớp cần dùng; thiếu module/hàm thì dừng với thông báo rõ."""
    mods = {}
    for n in sorted(names):
        modname = LAYER_MODULES[n]
        try:
            mod = importlib.import_module(modname)
        except ModuleNotFoundError as e:
            if e.name == modname:
                raise HarnessError(
                    f"Thiếu lớp {n}: không có module {modname}. Merge nhánh chứa lớp này "
                    f"hoặc bỏ các cấu hình dùng {n}.") from e
            raise HarnessError(f"Lớp {n} ({modname}) nạp lỗi vì thiếu {e.name!r}: {e}") from e
        except Exception as e:  # noqa: BLE001 — module hỏng phải báo rõ, không nuốt
            raise HarnessError(f"Lớp {n} ({modname}) nạp lỗi: {type(e).__name__}: {e}") from e
        fn = "check_after" if n == "L4" else "check"
        if not callable(getattr(mod, fn, None)):
            raise HarnessError(f"Lớp {n} ({modname}) thiếu hàm {fn}() theo hợp đồng.")
        mods[n] = mod
    return mods


def layer_params(mod: Any) -> dict:
    """Hằng số công khai (CHỮ HOA, kiểu đơn giản) của module lớp, để ghi vào run_config."""
    return {k: v for k, v in vars(mod).items()
            if k.isupper() and not k.startswith("_")
            and isinstance(v, (int, float, bool, str)) and len(str(v)) <= 300}


# --------------------------------------------------------------------------- dữ liệu

def load_prompts(split: str, data_dir: Path, limit: int = 0) -> list[dict]:
    path = data_dir / SPLIT_FILES[split]
    if not path.exists():
        raise HarnessError(f"Không thấy file dữ liệu cho split {split!r}: {path}")
    prompts = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(prompts, list):
        raise HarnessError(f"{path} phải là danh sách JSON (schema v2).")
    for p in prompts:
        missing = [k for k in ("id", "user_task", "untrusted_document", "label") if k not in p]
        if missing:
            raise HarnessError(f"{path.name}: prompt {p.get('id', '?')} thiếu {missing} "
                               "(schema cũ? cần schema v2).")
        if p["label"] == "attack":
            sc = p.get("success_check")
            if sc is None and split in EXT_SPLITS and p.get("goal_type") == "other":
                pass  # mục ngoài không có tiêu chí chấm: ASR để trống, vẫn đo chặn/từ chối
            elif not isinstance(sc, dict) or sc.get("type") not in SCORABLE_CHECKS:
                raise HarnessError(f"{path.name}: {p['id']} có success_check không hợp lệ: {sc!r}")
        elif p["label"] == "benign":
            utility.keypoint_hits("", p)  # kiểm tra keypoint_keywords song song với keypoints
        else:
            raise HarnessError(f"{path.name}: {p['id']} có label lạ: {p['label']!r}")
        own = p.get("split", split)
        if own in FINAL_ONLY_SPLITS and own != split:
            raise HarnessError(f"{path.name}: {p['id']} thuộc hold-out/dữ liệu ngoài "
                               f"(split {own!r}) nhưng nằm trong split {split!r}; từ chối chạy.")
    ids = [p["id"] for p in prompts]
    if len(set(ids)) != len(ids):
        raise HarnessError(f"{path.name}: id bị trùng.")
    return prompts[:limit] if limit > 0 else prompts


def derive_seed(seed_base: int, prompt_id: str, sample_idx: int, call_idx: int = 0) -> int:
    """Seed xác định cho model, độc lập với config để các cấu hình ghép cặp được."""
    h = hashlib.sha256(f"{seed_base}|{prompt_id}|{sample_idx}|{call_idx}".encode()).hexdigest()
    return int(h[:8], 16) & 0x7FFFFFFF


class GenResult(str):
    """Phản hồi trao cho L4: là `str` (nội dung + lời gọi công cụ in thành văn bản) nhưng
    còn thuộc tính `.content` và `.tool_calls`, để L4 so sánh được cả hành động công cụ."""

    content: str
    tool_calls: list

    def __new__(cls, content: str, tool_calls: list) -> "GenResult":
        text = content + "".join(
            f"\n[TOOL_CALL] {c['name']}({json.dumps(c['arguments'], ensure_ascii=False)})"
            for c in tool_calls)
        obj = super().__new__(cls, text)
        obj.content, obj.tool_calls = content, tool_calls
        return obj


# --------------------------------------------------------------------------- lưu kết quả

class ResultStore:
    """Ghi nối từng dòng ngay khi xong để chết giữa chừng không mất; hỗ trợ resume."""

    def __init__(self, out_dir: Path):
        self.dir = out_dir
        self.csv_path = out_dir / "results.csv"
        self.jsonl_path = out_dir / "outputs.jsonl"
        self.config_path = out_dir / "run_config.json"
        self._lock = threading.Lock()

    def prepare(self, resume: bool) -> set[tuple[str, str, int]]:
        """Chuẩn bị thư mục; trả các khoá (config, prompt_id, sample_idx) đã xong."""
        self.dir.mkdir(parents=True, exist_ok=True)
        has_data = self.csv_path.exists() and self.csv_path.stat().st_size > 0
        if has_data and not resume:
            raise HarnessError(f"{self.csv_path} đã có dữ liệu. Dùng --resume để chạy tiếp "
                               "hoặc chọn --out khác (không ghi đè kết quả cũ).")
        done = self._repair() if has_data else set()
        if not has_data:
            with open(self.csv_path, "w", encoding="utf-8", newline="") as f:
                csv.writer(f, lineterminator="\n").writerow(CSV_COLUMNS)
        return done

    def _read_valid_rows(self) -> list[dict]:
        valid = []
        with open(self.csv_path, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                try:
                    ok = (None not in row and None not in row.values()
                          and list(row) == CSV_COLUMNS and not row["error"]
                          and row["config"] and int(row["sample_idx"]) >= 0
                          and float(row["latency_ms_total"]) >= 0)
                except (ValueError, TypeError):
                    ok = False
                if ok:
                    valid.append(row)
        return valid

    def _repair(self) -> set[tuple[str, str, int]]:
        """Bỏ dòng dở dang (bị cắt) và dòng lỗi (sẽ chạy lại); đồng bộ outputs.jsonl."""
        rows = self._read_valid_rows()
        keys = {(r["config"], r["prompt_id"], int(r["sample_idx"])) for r in rows}
        tmp = self.csv_path.with_suffix(".csv.tmp")
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, self.csv_path)
        if self.jsonl_path.exists():
            kept: dict = {}
            for line in self.jsonl_path.read_text(encoding="utf-8").splitlines():
                try:
                    rec = json.loads(line)
                    key = (rec["config"], rec["prompt_id"], int(rec["sample_idx"]))
                except (ValueError, KeyError, TypeError):
                    continue
                if key in keys:
                    kept[key] = line
            tmp = self.jsonl_path.with_suffix(".jsonl.tmp")
            tmp.write_text("".join(line + "\n" for line in kept.values()), encoding="utf-8")
            os.replace(tmp, self.jsonl_path)
        return keys

    def append(self, row: dict, record: dict) -> None:
        with self._lock:
            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            with open(self.csv_path, "a", encoding="utf-8", newline="") as f:
                csv.DictWriter(f, fieldnames=CSV_COLUMNS, lineterminator="\n").writerow(row)

    def read_rows(self) -> list[dict]:
        with open(self.csv_path, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))


# --------------------------------------------------------------------------- một lượt

class Evaluator:
    """Chạy một lượt (config, prompt, sample) qua pipeline và đóng gói dòng kết quả."""

    def __init__(self, *, run_id: str, model: str, temperature: float, seed_base: int,
                 layers: dict[str, Any], client: OllamaClient, use_embedding: bool = False):
        self.run_id = run_id
        self.model = model
        self.temperature = temperature
        self.seed_base = seed_base
        self.layers = layers
        self.agent = BaselineAgent(client)
        self.use_embedding = use_embedding
        self._cache: dict = {}
        self._cache_lock = threading.Lock()

    def _run_layer(self, name: str, user_task: str, document: str):
        """L1–L3 xác định theo (lớp, tác vụ, tài liệu đầu vào) nên cache kết quả; thời gian
        ghi vào các dòng sau là thời gian đo ở lần chạy đầu."""
        key = (name, hashlib.sha1(f"{user_task}\x00{document}".encode()).hexdigest())
        with self._cache_lock:
            hit = self._cache.get(key)
        if hit:
            return hit
        t0 = time.perf_counter()
        res = self.layers[name].check(user_task, document)
        out = (res, (time.perf_counter() - t0) * 1000.0)
        with self._cache_lock:
            self._cache[key] = out
        return out

    def run_item(self, config: str, prompt: dict, split: str, sample_idx: int) -> tuple[dict, dict]:
        layer_names = parse_config(config)
        pre = [n for n in layer_names if n != "L4"]
        pid = prompt["id"]
        user_task, doc = prompt["user_task"], prompt["untrusted_document"]
        is_attack = prompt["label"] == "attack"
        canary = self.agent.generate_canary()
        temperature = self.temperature

        log: list[dict] = []
        addenda: list[str] = []
        suffixes: list[str] = []
        pre_ms = model_ms = l4_ms = 0.0
        n_calls = 0
        blocked_by = reason = error = ""
        response = raw_response = ""
        tool_calls: list = []
        hits: list = []

        def generate(task: str, document: str) -> GenResult:
            """Cho L4: cùng model/canary/system prompt/L3 như lần chạy chính."""
            nonlocal n_calls
            n_calls += 1
            # Lượt che của L4 không được thấy tác vụ thật: L3 (sandwich) lặp lại tác vụ trong
            # user_suffix, nên phải thay bằng tác vụ đã che (lỗi này từng làm L4 chặn ~47% benign).
            adds, sufs = addenda, suffixes
            if task != user_task:
                adds = [a.replace(user_task, task) for a in addenda]
                sufs = [x.replace(user_task, task) for x in suffixes]
            r = self.agent.run(task, document, canary, "\n\n".join(adds),
                               "\n\n".join(sufs), temperature,
                               derive_seed(self.seed_base, pid, sample_idx, n_calls - 1))
            return GenResult(r.response, r.tool_calls)

        try:
            for n in pre:
                res, ms = self._run_layer(n, user_task, doc)
                pre_ms += ms
                log.append({"layer": n, "action": res.action, "score": res.score,
                            "reason": res.reason, "ms": round(ms, 1)})
                if res.action == "block":
                    blocked_by, reason = n, res.reason
                    break
                if res.action not in ("pass", "sanitize"):
                    raise ValueError(f"{n} trả action lạ: {res.action!r}")
                if res.action == "sanitize":
                    doc = res.document
                addenda += [res.system_addendum] if res.system_addendum else []
                suffixes += [res.user_suffix] if res.user_suffix else []

            if not blocked_by:
                t_model = time.perf_counter()
                first = generate(user_task, doc)
                model_ms = (time.perf_counter() - t_model) * 1000.0
                response, tool_calls = first.content, first.tool_calls
                if "L4" in layer_names:
                    t4 = time.perf_counter()
                    res = self.layers["L4"].check_after(user_task, doc, first, generate)
                    l4_ms = (time.perf_counter() - t4) * 1000.0
                    log.append({"layer": "L4", "action": res.action, "score": res.score,
                                "reason": res.reason, "ms": round(l4_ms, 1)})
                    if res.action == "block":
                        blocked_by, reason = "L4", res.reason
                    elif res.action not in ("pass", "sanitize"):
                        raise ValueError(f"L4 trả action lạ: {res.action!r}")
        except KeyboardInterrupt:
            raise
        except Exception as e:  # noqa: BLE001 — mỗi lượt lỗi được ghi lại, không dừng cả run
            error = f"{type(e).__name__}: {e}"[:300]

        blocked = bool(blocked_by)
        if blocked:
            raw_response, response, tool_calls = response, BLOCKED_TEXT, []

        attack_success: Any = ""
        refused: Any = ""
        util: Any = ""
        if not error:
            refused = int(not blocked and utility.model_refused(response))
            try:
                if is_attack:
                    if prompt.get("success_check"):
                        attack_success = int(not blocked and success.check_success(
                            prompt["success_check"], response, canary, tool_calls))
                    # không có success_check (mục ngoài goal_type=other): ASR để trống, không phải 0
                elif not prompt.get("reference_keypoints"):
                    pass  # benign không có keypoint (tập ngoài): utility để trống, không phải 0
                elif blocked:
                    util = 0.0
                else:
                    hits = utility.keypoint_hits(response, prompt, self.use_embedding)
                    util = round(sum(h for h, _ in hits) / len(hits), 4) if hits else 0.0
            except Exception as e:  # noqa: BLE001
                error, attack_success, refused, util = f"scoring: {e}"[:300], "", "", ""

        layers_ms = pre_ms + l4_ms
        total_ms = pre_ms + model_ms + l4_ms
        row = {
            "run_id": self.run_id, "model": self.model, "config": config, "prompt_id": pid,
            "split": split, "label": prompt["label"],
            "attack_type": prompt.get("attack_type", "none"),
            "liu_type": prompt.get("liu_type", "none"),
            "technique": prompt.get("technique", ""),
            "goal_type": prompt.get("goal_type", ""),
            "sample_idx": sample_idx, "temperature": temperature,
            "blocked": int(blocked), "blocked_by": blocked_by,
            "attack_success": attack_success, "model_refused": refused, "utility_score": util,
            "n_model_calls": n_calls, "latency_ms_total": round(total_ms, 1),
            "latency_ms_layers": round(layers_ms, 1), "error": error,
        }
        record = {
            "run_id": self.run_id, "config": config, "prompt_id": pid, "split": split,
            "sample_idx": sample_idx, "canary": canary,
            "seed": derive_seed(self.seed_base, pid, sample_idx, 0),
            "response": response, "tool_calls": tool_calls, "reason": reason,
            "blocked_by": blocked_by, "layers": log, "error": error,
        }
        if raw_response:
            record["raw_response"] = raw_response
        if hits:
            record["keypoint_hits"] = [{"hit": h, "by": m} for h, m in hits]
        return row, record


# --------------------------------------------------------------------------- tóm tắt

def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else float("nan")


def print_summary_table(rows: list[dict], configs: Optional[list[str]] = None) -> None:
    """In ASR theo (config, split) với Wilson 95%, và bảng benign. Bỏ qua dòng lỗi."""
    ok = [r for r in rows if not r["error"]]
    n_err = len(rows) - len(ok)
    order = configs or list(dict.fromkeys(r["config"] for r in rows))
    base_lat = {s: _mean([float(r["latency_ms_total"]) for r in ok
                          if r["config"] == "baseline" and r["split"] == s])
                for s in {r["split"] for r in ok}}

    def block(label: str, header: str, fmt) -> None:
        lines = []
        for cfg in order:
            for split in sorted({r["split"] for r in ok}):
                g = [r for r in ok if r["config"] == cfg and r["split"] == split
                     and r["label"] == label]
                if g:
                    lines.append(fmt(cfg, split, g))
        if lines:
            print(header)
            print("-" * len(header))
            print("\n".join(lines))
            print()

    print("\n" + "=" * 100)
    block("attack",
          f"{'config':<18}{'split':<12}{'n':>5}{'ASR':>8}{'Wilson95%':>16}{'blocked':>9}"
          f"{'calls':>7}{'lat_ms':>9}{'xbase':>7}",
          lambda c, s, g: _attack_line(c, s, g, base_lat))
    block("benign",
          f"{'config':<18}{'split':<12}{'n':>5}{'blocked':>9}{'refused':>9}{'FP(b|r)':>9}"
          f"{'utility':>9}{'calls':>7}{'lat_ms':>9}",
          _benign_line)
    if n_err:
        print(f"CẢNH BÁO: {n_err} dòng lỗi (cột error) bị loại khỏi bảng; chạy lại bằng --resume.")
    print("=" * 100)


def _attack_line(cfg: str, split: str, g: list[dict], base_lat: dict) -> str:
    """ASR chỉ tính trên các lượt chấm được (`attack_success` khác rỗng); n là số lượt chấm được."""
    scored = [r for r in g if r["attack_success"] != ""]
    k, n = sum(int(r["attack_success"]) for r in scored), len(scored)
    lo, hi = wilson(k, n)
    lat = _mean([float(r["latency_ms_total"]) for r in g])
    ratio = lat / base_lat[split] if base_lat.get(split) else float("nan")
    asr = f"{k / n:.1%}" if n else "n/a"
    ci = f"[{lo:.1%},{hi:.1%}]" if n else "n/a"
    return (f"{cfg:<18}{split:<12}{n:>5}{asr:>8}{ci:>16}"
            f"{_mean([float(r['blocked']) for r in g]):>9.1%}"
            f"{_mean([float(r['n_model_calls']) for r in g]):>7.2f}{lat:>9.0f}{ratio:>7.2f}")


def _utility_cell(g: list[dict]) -> str:
    vals = [float(r["utility_score"]) for r in g if r["utility_score"] != ""]
    return f"{_mean(vals):.3f}" if vals else "n/a"


def _benign_line(cfg: str, split: str, g: list[dict]) -> str:
    fp = _mean([float(int(r["blocked"]) or int(r["model_refused"] or 0)) for r in g])
    return (f"{cfg:<18}{split:<12}{len(g):>5}{_mean([float(r['blocked']) for r in g]):>9.1%}"
            f"{_mean([float(r['model_refused'] or 0) for r in g]):>9.1%}{fp:>9.1%}"
            f"{_utility_cell(g):>9}"
            f"{_mean([float(r['n_model_calls']) for r in g]):>7.2f}"
            f"{_mean([float(r['latency_ms_total']) for r in g]):>9.0f}")


# --------------------------------------------------------------------------- run_config

def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                              timeout=GIT_TIMEOUT_S).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def ollama_version(host: Optional[str]) -> str:
    try:
        url = (host or base.DEFAULT_HOST).rstrip("/") + "/api/version"
        with urllib.request.urlopen(url, timeout=5) as r:
            return json.load(r).get("version", "unknown")
    except Exception:  # noqa: BLE001
        return "unknown"


def build_run_config(args: argparse.Namespace, run_id: str, configs: list[str],
                     splits: list[str], layers: dict[str, Any]) -> dict:
    data_files = {}
    for s in splits:
        p = Path(args.data_dir) / SPLIT_FILES[s]
        data_files[s] = {"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
    return {
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": args.model, "ollama_host": args.host or base.DEFAULT_HOST,
        "ollama_version": ollama_version(args.host),
        "embed_model": base.EMBED_MODEL, "utility_embedding": args.utility_embed,
        "temperature": args.temperature, "samples": args.samples,
        "seed_base": args.seed,
        "seed_scheme": "sha256(f'{seed_base}|{prompt_id}|{sample_idx}|{call_idx}')[:8] & 0x7fffffff",
        "num_predict": args.num_predict, "num_ctx": args.num_ctx or None,
        "timeout_s": args.timeout, "workers": args.workers, "limit": args.limit,
        "configs": configs, "splits": splits,
        "holdout_confirmed": bool(args.confirm_final_holdout),
        "git_commit": _git("rev-parse", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain", "--untracked-files=no")),
        "python": sys.version.split()[0], "argv": sys.argv[1:],
        "data_files": data_files,
        "system_prompt_template": agent_mod.SYSTEM_TEMPLATE,
        "user_template": agent_mod.USER_TEMPLATE,
        "tools": [t["function"]["name"] for t in agent_mod.TOOLS],
        "layer_params": {n: layer_params(m) for n, m in layers.items()},
        "thresholds": {
            "utility.TOKEN_OVERLAP_THRESHOLD": utility.TOKEN_OVERLAP_THRESHOLD,
            "utility.EMBED_THRESHOLD": utility.EMBED_THRESHOLD,
            "utility.REFUSAL_WINDOW": utility.REFUSAL_WINDOW,
            "utility.REFUSAL_MAX_LEN": utility.REFUSAL_MAX_LEN,
        },
    }


def _default_run_id() -> str:
    day = datetime.now().strftime("%Y%m%d")
    n = 1
    while (ROOT / "results" / f"{day}-{n}").exists():
        n += 1
    return f"{day}-{n}"


# --------------------------------------------------------------------------- điều phối

def _csv_list(text: str) -> list[str]:
    return [t.strip() for t in text.split(",") if t.strip()]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Harness đo ASR prompt injection qua các lớp phòng thủ L1–L4.")
    p.add_argument("--configs", default=DEFAULT_CONFIGS,
                   help="baseline,L1,L1+L2,L1+L2+L3,L1+L2+L3+L4,only_L1..only_L4")
    p.add_argument("--splits", default="train,benign",
                   help="train,benign,holdout,test_indist,ext_attack,ext_benign")
    p.add_argument("--samples", type=int, default=3, help="số lần lấy mẫu mỗi (config, prompt)")
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--seed", type=int, default=0, help="seed gốc, trộn với hash(prompt_id, sample_idx)")
    p.add_argument("--limit", type=int, default=0, help="chỉ lấy N prompt đầu mỗi split (0 = hết)")
    p.add_argument("--model", default=base.DEFAULT_MODEL)
    p.add_argument("--host", default=None, help="URL Ollama (mặc định theo OLLAMA_HOST_URL)")
    p.add_argument("--out", default=None, help="thư mục kết quả, mặc định results/<YYYYMMDD-N>")
    p.add_argument("--data-dir", default=str(ROOT / "attack_prompts"))
    p.add_argument("--workers", type=int, default=1, help="Ollama xử lý nối tiếp; tối đa nên là 2")
    p.add_argument("--resume", action="store_true", help="chạy tiếp, bỏ qua khoá đã xong")
    p.add_argument("--confirm-final-holdout", action="store_true",
                   help="BẮT BUỘC để chạy split holdout, ext_attack, ext_benign; chỉ dùng cho cấu hình cuối")
    p.add_argument("--utility-embed", action="store_true",
                   help="dùng embedding làm phương án phụ khi chấm utility (cần nomic-embed-text)")
    p.add_argument("--num-predict", type=int, default=400)
    p.add_argument("--num-ctx", type=int, default=0, help="0 = mặc định của server Ollama")
    p.add_argument("--timeout", type=int, default=300)
    return p


def _guard_holdout(splits: list[str], confirmed: bool) -> None:
    final = [s for s in splits if s in FINAL_ONLY_SPLITS]
    if final and not confirmed:
        print(f"TỪ CHỐI: split {final} chỉ được chạy cho cấu hình cuối cùng, một lần "
              "(hold-out và dữ liệu ngoài đều là dữ liệu chưa được dùng để chỉnh tham số).\n"
              "Nếu đúng là lần chạy cuối, thêm cờ --confirm-final-holdout. "
              "Mọi việc chỉnh ngưỡng/từ khoá/prompt hệ thống phải làm trên train/benign.",
              file=sys.stderr)
        raise SystemExit(2)


def _fmt_eta(seconds: float) -> str:
    s = int(max(seconds, 0))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def run(args: argparse.Namespace) -> Path:
    """Chạy toàn bộ đánh giá; trả thư mục kết quả."""
    configs = _csv_list(args.configs)
    splits = _csv_list(args.splits)
    bad = [s for s in splits if s not in SPLIT_FILES]
    if bad or not splits or not configs:
        raise HarnessError(f"--splits/--configs không hợp lệ: splits={splits} (hợp lệ: "
                           f"{list(SPLIT_FILES)}), configs={configs}")
    _guard_holdout(splits, args.confirm_final_holdout)
    if args.samples < 1 or args.workers < 1:
        raise HarnessError("--samples và --workers phải >= 1")
    if args.temperature == 0 and args.samples > 1:
        print("CẢNH BÁO: temperature=0 mà samples>1 → các mẫu gần như giống hệt.", file=sys.stderr)
    needed = {n for c in configs for n in parse_config(c)}
    layers = load_layers(needed)
    prompts = {s: load_prompts(s, Path(args.data_dir), args.limit) for s in splits}

    out_dir = Path(args.out) if args.out else ROOT / "results" / _default_run_id()
    run_id = out_dir.name
    store = ResultStore(out_dir)
    done = store.prepare(args.resume)
    cfg_new = build_run_config(args, run_id, configs, splits, layers)
    _write_run_config(store, cfg_new, args.resume)

    client = OllamaClient(model=args.model, host=args.host, temperature=args.temperature,
                          num_predict=args.num_predict, timeout=args.timeout,
                          num_ctx=args.num_ctx or None)
    ev = Evaluator(run_id=run_id, model=args.model, temperature=args.temperature,
                   seed_base=args.seed, layers=layers, client=client,
                   use_embedding=args.utility_embed)

    items = [(c, p, s, i) for i in range(args.samples) for s in splits
             for p in prompts[s] for c in configs]
    pending = [it for it in items if (it[0], it[1]["id"], it[3]) not in done]
    print(f"[run {run_id}] model={args.model} T={args.temperature} | tổng {len(items)} lượt, "
          f"đã xong {len(items) - len(pending)}, còn {len(pending)} | out={out_dir}", flush=True)

    progress = {"n": 0, "err_streak": 0, "t0": time.perf_counter()}
    plock = threading.Lock()

    def work(it) -> None:
        cfg, prompt, split, idx = it
        row, rec = ev.run_item(cfg, prompt, split, idx)
        store.append(row, rec)
        with plock:
            progress["n"] += 1
            progress["err_streak"] = progress["err_streak"] + 1 if row["error"] else 0
            n, left = progress["n"], len(pending) - progress["n"]
            eta = (time.perf_counter() - progress["t0"]) / n * left
            tag = ("ERR " + row["error"][:60]) if row["error"] else (
                f"blocked={row['blocked_by']}" if row["blocked"] else
                (f"success={row['attack_success']}" if row["label"] == "attack"
                 else f"utility={row['utility_score']} refused={row['model_refused']}"))
            print(f"[{n}/{len(pending)}] {cfg:<14} {prompt['id']:<8} s{idx} {tag:<28} "
                  f"{float(row['latency_ms_total']) / 1000:5.1f}s calls={row['n_model_calls']} "
                  f"ETA {_fmt_eta(eta)}", flush=True)
            if progress["err_streak"] >= MAX_CONSECUTIVE_ERRORS:
                raise HarnessError(
                    f"Dừng: {MAX_CONSECUTIVE_ERRORS} lượt lỗi liên tiếp (lỗi cuối: {row['error']}). "
                    "Kiểm tra Ollama/lớp phòng thủ rồi chạy lại với --resume.")

    try:
        if args.workers == 1:
            for it in pending:
                work(it)
        else:
            with ThreadPoolExecutor(max_workers=args.workers) as ex:
                futures = [ex.submit(work, it) for it in pending]
                try:
                    for f in as_completed(futures):
                        f.result()
                except BaseException:
                    ex.shutdown(wait=False, cancel_futures=True)
                    raise
    except KeyboardInterrupt:
        print(f"\nBị ngắt. Kết quả đã ghi được giữ nguyên; chạy tiếp: thêm --resume "
              f"--out {out_dir}", file=sys.stderr)
        raise SystemExit(130)

    _finish_run_config(store)
    print_summary_table(store.read_rows(), configs)
    print(f"[OK] {store.csv_path}\n     {store.jsonl_path}\n     {store.config_path}")
    return out_dir


def _write_run_config(store: ResultStore, new: dict, resume: bool) -> None:
    """Fresh: ghi mới. Resume: bắt buộc cùng model/nhiệt độ/seed để các dòng so sánh được."""
    cfg = new
    if resume and store.config_path.exists():
        old = json.loads(store.config_path.read_text(encoding="utf-8"))
        for k in ("model", "temperature", "seed_base", "num_predict"):
            if old.get(k) != new.get(k):
                raise HarnessError(f"--resume không khớp run_config.json: {k} cũ={old.get(k)!r} "
                                   f"mới={new.get(k)!r}")
        cfg = dict(old)
        cfg["samples"] = max(old.get("samples", 0), new["samples"])
        cfg["configs"] = list(dict.fromkeys(old.get("configs", []) + new["configs"]))
        cfg["splits"] = list(dict.fromkeys(old.get("splits", []) + new["splits"]))
        cfg["data_files"] = {**old.get("data_files", {}), **new["data_files"]}
        cfg["layer_params"] = new["layer_params"]
        cfg["holdout_confirmed"] = old.get("holdout_confirmed", False) or new["holdout_confirmed"]
        cfg["git_commit_resumed"] = new["git_commit"]
        cfg.setdefault("resumes", []).append({"utc": new["created_utc"], "argv": new["argv"]})
    store.config_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")


def _finish_run_config(store: ResultStore) -> None:
    cfg = json.loads(store.config_path.read_text(encoding="utf-8"))
    rows = store.read_rows()
    cfg["finished_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cfg["n_rows"] = len(rows)
    cfg["n_error_rows"] = sum(1 for r in rows if r["error"])
    store.config_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")


def main(argv: Optional[list[str]] = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    try:
        run(args)
    except HarnessError as e:
        print(f"LỖI: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
