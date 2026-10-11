"""Đọc và kiểm tra CSV kết quả theo hợp đồng (docs/hop-dong-chung.md, mục 3).

Mọi bảng phía sau đều giả định dữ liệu đã qua `check_input`; vì vậy file này
nghiêm khắc: lỗi hợp đồng làm dừng chương trình với thông báo nêu rõ số dòng và
ví dụ, còn nghi vấn (cảnh báo) chỉ được ghi vào báo cáo.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import pandas as pd

REQUIRED_COLUMNS: tuple[str, ...] = (
    "run_id", "model", "config", "prompt_id", "split", "label", "attack_type",
    "liu_type", "technique", "goal_type", "sample_idx", "temperature", "blocked",
    "blocked_by", "attack_success", "model_refused", "utility_score",
    "n_model_calls", "latency_ms_total", "latency_ms_layers", "error",
)
ATTACK_SPLITS: tuple[str, ...] = ("train", "holdout", "test_indist")
ALL_SPLITS: tuple[str, ...] = ATTACK_SPLITS + ("benign",)
BLOCKING_LAYERS: tuple[str, ...] = ("L1", "L2", "L4")
KEY_COLUMNS = ["run_id", "config", "prompt_id", "sample_idx"]
META_COLUMNS = ["split", "label", "attack_type", "liu_type", "technique", "goal_type"]
NUMERIC_COLUMNS = (
    "sample_idx", "temperature", "blocked", "model_refused", "attack_success",
    "utility_score", "n_model_calls", "latency_ms_total", "latency_ms_layers",
)
DEFAULT_ERROR_THRESHOLD = 0.02
LATENCY_TOLERANCE_MS = 1.0

_ONLY_RE = re.compile(r"^only_(L[1-4])$")
_CUM_RE = re.compile(r"^L[1-4](\+L[1-4])*$")


class DataError(ValueError):
    """Dữ liệu đầu vào vi phạm hợp đồng; `issues` chứa chi tiết."""

    def __init__(self, message: str, issues: list["Issue"] | None = None):
        super().__init__(message)
        self.issues = issues or []


@dataclass
class Issue:
    level: str  # "error" | "warning"
    code: str
    message: str
    count: int = 0
    examples: list[str] = field(default_factory=list)

    def render(self) -> str:
        ex = f" Ví dụ: {'; '.join(self.examples)}." if self.examples else ""
        n = f" ({self.count} dòng)" if self.count else ""
        return f"[{self.level.upper()}:{self.code}] {self.message}{n}.{ex}"


@dataclass
class Loaded:
    """Dữ liệu đã gộp, ép kiểu; `rows` gồm cả dòng lỗi (cột `is_error`)."""

    rows: pd.DataFrame
    issues: list[Issue]
    sources: list[str]

    @property
    def valid(self) -> pd.DataFrame:
        return self.rows[~self.rows["is_error"]]


def config_layers(config: str) -> frozenset[str] | None:
    """Tập lớp bật trong `config`; None nếu tên không theo quy ước hợp đồng."""
    if config == "baseline":
        return frozenset()
    m = _ONLY_RE.match(config)
    if m:
        return frozenset([m.group(1)])
    if _CUM_RE.match(config):
        return frozenset(config.split("+"))
    return None


def read_csvs(paths: Iterable[str | Path]) -> pd.DataFrame:
    """Đọc mọi CSV dưới dạng chuỗi thuần (giữ nguyên "none", ô rỗng) và gộp lại."""
    frames = []
    for p in paths:
        path = Path(p)
        if not path.is_file():
            raise DataError(f"Không tìm thấy file CSV: {path}")
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        df["source_file"] = str(path)
        frames.append(df)
    if not frames:
        raise DataError("Chưa chỉ định file CSV nào.")
    return pd.concat(frames, ignore_index=True)


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    """Chuỗi -> số (không hợp lệ thành NaN) và thêm `is_error`, `*_empty` để kiểm tra."""
    out = df.copy()
    for col in REQUIRED_COLUMNS:
        out[col] = out[col].astype(str).str.strip()
    out["is_error"] = out["error"] != ""
    for col in NUMERIC_COLUMNS:
        out[f"{col}__empty"] = out[col] == ""
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def _examples(df: pd.DataFrame, mask: pd.Series, limit: int = 3) -> list[str]:
    sub = df.loc[mask, ["config", "prompt_id", "sample_idx"]].head(limit)
    return [f"{r.config}/{r.prompt_id}/#{r.sample_idx}" for r in sub.itertuples()]


def _add(issues: list[Issue], level: str, code: str, msg: str,
         df: pd.DataFrame, mask: pd.Series) -> None:
    n = int(mask.sum())
    if n:
        issues.append(Issue(level, code, msg, n, _examples(df, mask)))


def _numeric_issues(t: pd.DataFrame, ok: pd.Series, issues: list[Issue]) -> None:
    for col in ("sample_idx", "temperature", "blocked", "model_refused",
                "n_model_calls", "latency_ms_total", "latency_ms_layers"):
        _add(issues, "error", "bad_numeric",
             f"cột `{col}` rỗng hoặc không phải số", t, ok & t[col].isna())
    for col in ("blocked", "model_refused"):
        _add(issues, "error", "bad_binary", f"cột `{col}` phải là 0 hoặc 1",
             t, ok & t[col].notna() & ~t[col].isin([0, 1]))
    for col in ("sample_idx", "n_model_calls"):
        bad = ok & t[col].notna() & ((t[col] < 0) | (t[col] % 1 != 0))
        _add(issues, "error", "bad_integer", f"cột `{col}` phải là số nguyên >= 0", t, bad)
    for col in ("latency_ms_total", "latency_ms_layers"):
        bad = ok & t[col].notna() & ((t[col] < 0) | (t[col].abs() == float("inf")))
        _add(issues, "error", "bad_latency", f"cột `{col}` phải hữu hạn và >= 0", t, bad)


def _label_issues(t: pd.DataFrame, ok: pd.Series, issues: list[Issue]) -> None:
    attack = t["label"] == "attack"
    benign = t["label"] == "benign"
    a_ok, b_ok = ok & attack, ok & benign

    # Gộp kiểm tra cột đáp án: attack_success chỉ cho attack, utility chỉ cho benign.
    _add(issues, "error", "attack_success_missing",
         "dòng tấn công phải có `attack_success` là 0 hoặc 1",
         t, a_ok & ~t["attack_success"].isin([0, 1]))
    _add(issues, "error", "benign_has_attack_success",
         "dòng benign phải để trống `attack_success`",
         t, b_ok & ~t["attack_success__empty"])
    _add(issues, "error", "benign_utility_missing",
         "dòng benign phải có `utility_score` trong [0, 1]",
         t, b_ok & ~((t["utility_score"] >= 0) & (t["utility_score"] <= 1)))
    _add(issues, "warning", "attack_has_utility",
         "dòng tấn công có `utility_score` (hợp đồng: chỉ benign), sẽ bị bỏ qua",
         t, a_ok & ~t["utility_score__empty"])


def _block_issues(t: pd.DataFrame, ok: pd.Series, issues: list[Issue]) -> None:
    blocked = t["blocked"] == 1
    by = t["blocked_by"]
    _add(issues, "error", "bad_blocked_by",
         "`blocked_by` chỉ được là rỗng, L1, L2 hoặc L4 (L3 không chặn)",
         t, ok & (by != "") & ~by.isin(BLOCKING_LAYERS))
    _add(issues, "error", "blocked_without_layer",
         "`blocked=1` nhưng `blocked_by` rỗng", t, ok & blocked & (by == ""))
    _add(issues, "error", "layer_without_block",
         "`blocked=0` nhưng `blocked_by` khác rỗng", t, ok & ~blocked & (by != ""))
    _add(issues, "error", "blocked_but_success",
         "bị chặn (`blocked=1`) mà `attack_success=1`; hợp đồng: bị chặn thì luôn 0",
         t, ok & blocked & (t["attack_success"] == 1))
    _add(issues, "error", "blocked_benign_utility_nonzero",
         "benign bị chặn phải có `utility_score=0` theo hợp đồng",
         t, ok & blocked & (t["label"] == "benign") & (t["utility_score"] != 0))
    _add(issues, "error", "baseline_blocked",
         "cấu hình `baseline` không có lớp nào nên không thể bị chặn",
         t, ok & (t["config"] == "baseline") & blocked)

    layers = t["config"].map(config_layers)
    unknown = ok & layers.isna()
    if unknown.any():
        names = sorted(t.loc[unknown, "config"].unique())
        issues.append(Issue("warning", "unknown_config",
                            f"tên config không theo quy ước (bỏ qua kiểm tra lớp): {names}",
                            int(unknown.sum())))
    has_layer = pd.Series([(by_i in ls) if ls is not None else True
                           for by_i, ls in zip(by, layers)], index=t.index)
    _add(issues, "error", "layer_not_in_config",
         "`blocked_by` là lớp không bật trong `config`",
         t, ok & (by != "") & ~has_layer)

    _add(issues, "warning", "layers_latency_exceeds_total",
         f"`latency_ms_layers` lớn hơn `latency_ms_total` quá {LATENCY_TOLERANCE_MS} ms",
         t, ok & (t["latency_ms_layers"] > t["latency_ms_total"] + LATENCY_TOLERANCE_MS))
    _add(issues, "warning", "baseline_calls",
         "dòng `baseline` có `n_model_calls` khác 1",
         t, ok & (t["config"] == "baseline") & (t["n_model_calls"] != 1))
    _add(issues, "warning", "blocked_pre_model_calls",
         "bị L1/L2 chặn (trước model) nhưng `n_model_calls` > 0",
         t, ok & by.isin(["L1", "L2"]) & (t["n_model_calls"] > 0))


def _structure_issues(t: pd.DataFrame, issues: list[Issue]) -> None:
    for col in ("run_id", "model", "config", "prompt_id", "split", "label"):
        _add(issues, "error", "empty_identity", f"cột `{col}` không được rỗng", t, t[col] == "")
    _add(issues, "error", "bad_label", "`label` phải là attack hoặc benign",
         t, ~t["label"].isin(["attack", "benign"]))
    _add(issues, "error", "bad_split", f"`split` phải thuộc {list(ALL_SPLITS)}",
         t, ~t["split"].isin(ALL_SPLITS))
    _add(issues, "error", "label_split_mismatch",
         "`label=benign` chỉ đi với `split=benign` và ngược lại",
         t, t["label"].isin(["attack", "benign"]) & t["split"].isin(ALL_SPLITS)
         & ((t["label"] == "benign") != (t["split"] == "benign")))

    dup = t.duplicated(KEY_COLUMNS, keep=False)
    _add(issues, "error", "duplicate_key",
         "trùng khoá (run_id, config, prompt_id, sample_idx); có thể đã gộp một file hai lần",
         t, dup)

    nun = t.groupby("prompt_id")[META_COLUMNS].nunique()
    bad_ids = nun.index[(nun > 1).any(axis=1)]
    if len(bad_ids):
        issues.append(Issue(
            "error", "inconsistent_prompt_meta",
            f"cùng `prompt_id` nhưng khác {META_COLUMNS}", int(t["prompt_id"].isin(bad_ids).sum()),
            list(map(str, bad_ids[:3]))))


def _coverage_issues(t: pd.DataFrame, threshold: float, issues: list[Issue]) -> None:
    valid = t[~t["is_error"]]
    per = valid.groupby(["config", "split", "prompt_id"]).size()
    unbalanced = per.groupby(level=["config", "split"]).nunique()
    bad = [f"{c}/{s}" for c, s in unbalanced.index[unbalanced > 1]]
    if bad:
        issues.append(Issue(
            "warning", "unbalanced_samples",
            "số lượt hợp lệ mỗi prompt không đều trong cùng config/split (do lỗi/timeout bị loại?); "
            "ASR gộp theo lượt và ASR trung bình theo prompt sẽ lệch nhẹ", 0, bad[:5]))
    missing: list[str] = []
    for split, sub in valid.groupby("split"):
        all_ids = set(sub["prompt_id"])
        for cfg, s2 in sub.groupby("config"):
            gap = all_ids - set(s2["prompt_id"])
            if gap:
                missing.append(f"{split}/{cfg}: thiếu {len(gap)} prompt")
    if missing:
        issues.append(Issue(
            "warning", "missing_prompts",
            "có config không phủ hết prompt của split (so sánh xếp cặp chỉ dùng phần giao)",
            0, missing[:5]))
    if len(t):
        rate = float(t["is_error"].mean())
        if rate > threshold:
            issues.append(Issue(
                "warning", "error_rate",
                f"tỉ lệ dòng lỗi/timeout {rate:.2%} vượt ngưỡng {threshold:.0%}; "
                "các dòng này bị loại khỏi mẫu, kết quả có thể thiên lệch", int(t["is_error"].sum())))
        by_cfg = t.groupby("config")["is_error"].mean()
        over = [f"{c}: {r:.2%}" for c, r in by_cfg.items() if r > threshold]
        if over:
            issues.append(Issue("warning", "error_rate_config",
                                f"config vượt ngưỡng lỗi {threshold:.0%}", 0, over[:6]))


def check_input(df: pd.DataFrame, *, error_threshold: float = DEFAULT_ERROR_THRESHOLD
                ) -> tuple[pd.DataFrame, list[Issue]]:
    """Kiểm tra hợp đồng; trả (bảng đã ép kiểu, danh sách vấn đề). Không tự raise.

    Dòng có `error` khác rỗng chỉ bị kiểm tra phần định danh vì harness có thể
    không ghi được các cột kết quả khi lỗi.
    """
    issues: list[Issue] = []
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        issues.append(Issue("error", "missing_columns", f"thiếu cột bắt buộc: {missing}"))
        return df, issues
    extra = [c for c in df.columns if c not in REQUIRED_COLUMNS and c != "source_file"]
    if extra:
        issues.append(Issue("warning", "extra_columns", f"cột lạ (bỏ qua): {extra}"))
    if df.empty:
        issues.append(Issue("error", "empty", "CSV không có dòng dữ liệu nào"))
        return df, issues

    t = coerce_types(df)
    ok = ~t["is_error"]
    _structure_issues(t, issues)
    _numeric_issues(t, ok, issues)
    _label_issues(t, ok, issues)
    _block_issues(t, ok, issues)
    _coverage_issues(t, error_threshold, issues)
    return t, issues


def load_results(paths: Iterable[str | Path], *, model: str | None = None,
                 error_threshold: float = DEFAULT_ERROR_THRESHOLD) -> Loaded:
    """Đọc, gộp, kiểm tra; có lỗi hợp đồng thì raise `DataError` (không có chế độ bỏ qua)."""
    path_list = [str(p) for p in paths]
    df = read_csvs(path_list)
    if "model" in df.columns:
        if model is not None:
            df = df[df["model"].str.strip() == model]
            if df.empty:
                raise DataError(f"Không có dòng nào với --model {model!r}")
        else:
            models = sorted(set(df["model"].str.strip()))
            if len(models) > 1:
                raise DataError(
                    f"CSV chứa nhiều model {models}; trộn các model làm sai ASR. "
                    "Chọn một bằng --model.")
    t, issues = check_input(df, error_threshold=error_threshold)
    errors = [i for i in issues if i.level == "error"]
    if errors:
        lines = "\n".join("  " + i.render() for i in errors)
        raise DataError(f"CSV vi phạm hợp đồng ({len(errors)} loại lỗi):\n{lines}", issues)
    if bool(t["is_error"].all()):
        raise DataError("Mọi dòng đều có lỗi/timeout; không còn mẫu hợp lệ để phân tích.", issues)
    return Loaded(rows=t, issues=issues, sources=sorted(set(path_list)))


def load_benign_meta(path: str | Path) -> dict[str, bool | None]:
    """Đọc `benign_prompts.json` -> {id: tune}; thiếu/không rõ -> None."""
    try:
        items = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DataError(f"Không đọc được --benign-meta {path}: {exc}") from exc
    if not isinstance(items, list):
        raise DataError(f"--benign-meta {path} phải là danh sách JSON các prompt")
    meta: dict[str, bool | None] = {}
    for it in items:
        if not isinstance(it, dict) or "id" not in it:
            raise DataError(f"--benign-meta {path}: phần tử thiếu trường `id`")
        raw = it.get("tune")
        if isinstance(raw, bool):
            meta[str(it["id"])] = raw
        elif isinstance(raw, str) and raw.strip().lower() in ("true", "false"):
            meta[str(it["id"])] = raw.strip().lower() == "true"
        else:
            meta[str(it["id"])] = None
    return meta
