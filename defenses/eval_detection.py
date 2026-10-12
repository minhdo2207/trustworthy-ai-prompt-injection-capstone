#!/usr/bin/env python3
"""defenses/eval_detection.py — đánh giá lớp PHÁT HIỆN (L1, L2, L1+L2) trên tập ngoài, không cần sinh văn bản.

!!! CẢNH BÁO: đây là đánh giá ZERO-SHOT trên dữ liệu công khai. L1 và L2 đã được chỉnh (từ khoá, ngưỡng) trên
train và benign `tune` của nhóm. KHÔNG được chỉnh L1/L2 theo kết quả của script này; làm vậy biến tập ngoài thành tập
huấn luyện và làm mất giá trị bằng chứng tổng quát hoá. !!!

Đo gì:
- TPR (tỉ lệ phát hiện) trên payload tấn công ở hai dạng: `embedded` (tài liệu đã nhúng payload, giống lúc chạy thật)
  và `bare` (chỉ payload trần, tách riêng khả năng nhận ra lệnh khỏi khả năng tìm lệnh trong tài liệu dài).
- FPR trên benign ngoài (`ext_benign_full.json`), theo từng nguồn.
- Chia theo nguồn (subset), attack_type, goal_type, liu_type, loại tài liệu nền; Wilson 95%.
- "Phát hiện" = lớp trả `block`. (`sanitize` của L1 không tính là phát hiện; số lần sanitize ghi riêng trong items.)

L1 chạy trên toàn bộ; L2 (LLM judge qua Ollama, có cache theo hash) chỉ chạy trên mẫu con `--n-l2` mỗi bên (attack,
benign), rút xoay vòng đều giữa các nguồn theo seed; `--max-l2-calls` đặt trần số lượt gọi model MỚI (cache không
tính). Khi hết ngân sách, script dừng L2, giữ phần đã chạy và ghi rõ n thực tế. Để so công bằng, các hàng
`scope=l2_sample` tính L1, L2, L1+L2 trên cùng các mục L2 đã chạy xong.

Ví dụ:
  python3 defenses/eval_detection.py --no-l2                     # chỉ L1 trên toàn bộ
  python3 defenses/eval_detection.py --n-l2 30 --max-l2-calls 60 # thêm L2 trên mẫu nhỏ
  python3 defenses/eval_detection.py --n-l2 30 --l2-cache-only   # dựng lại báo cáo từ cache, không gọi model
Đầu ra trong `--out` (mặc định results/dev/<YYYYMMDD>-ext-detection): detection.csv, detection.md,
detection_items.csv (quyết định từng mục), detection_meta.json.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.intervals import wilson  # noqa: E402

DATA_DIR = ROOT / "attack_prompts"
ATTACK_DIMS = ("subset", "attack_type", "goal_type", "liu_type", "context_kind")
BENIGN_DIMS = ("subset", "context_kind")
SUMMARY_COLUMNS = ["scope", "layer", "label", "view", "metric", "dim", "value", "n", "k", "rate",
                   "wilson_lo", "wilson_hi"]
ITEM_COLUMNS = ["id", "label", "subset", "attack_type", "goal_type", "liu_type", "context_kind", "view",
                "l1_action", "l1_score", "l1_reason", "l2_score", "l2_action", "l2_reason", "l2_calls_new",
                "l1l2_blocked"]
WARNING = ("CẢNH BÁO: đánh giá ZERO-SHOT. L1/L2 đã được chỉnh trên train và benign `tune` của nhóm; tuyệt đối "
           "không chỉnh L1/L2 theo kết quả này.")


class DetectionError(RuntimeError):
    """Lỗi đầu vào/môi trường cần báo rõ cho người chạy."""


# --------------------------------------------------------------------------- dữ liệu

def load_full(data_dir: Path, raw: Path | None = None) -> tuple[list[dict], list[dict]]:
    """Đọc ext_attack_full.json / ext_benign_full.json; thiếu thì dựng lại từ dữ liệu thô (không commit chúng)."""
    a_path, b_path = data_dir / "ext_attack_full.json", data_dir / "ext_benign_full.json"
    if not (a_path.exists() and b_path.exists()):
        import importlib
        sys.path.insert(0, str(data_dir))
        try:
            be = importlib.import_module("build_external")
        finally:
            sys.path.remove(str(data_dir))
        raw = raw or be.DEFAULT_RAW
        if not (raw / "manifest.json").exists():
            raise DetectionError(f"Thiếu {a_path.name}/{b_path.name} và dữ liệu thô ở {raw}. "
                                 "Chạy attack_prompts/fetch_external.py rồi build_external.py.")
        print(f"[dựng lại] {a_path.name}, {b_path.name} từ {raw}", file=sys.stderr)
        be.build(raw, data_dir, data_dir, write_full=True)
    try:
        return (json.loads(a_path.read_text(encoding="utf-8")), json.loads(b_path.read_text(encoding="utf-8")))
    except json.JSONDecodeError as exc:
        raise DetectionError(f"JSON hỏng: {exc}") from exc


def sample_round_robin(items: list[dict], n: int, seed: int, key: str = "subset") -> list[dict]:
    """Rút tối đa n mục, xoay vòng đều giữa các nhóm `key`, thứ tự trong nhóm xáo theo seed."""
    rng = random.Random(seed)
    groups: dict[str, list[dict]] = defaultdict(list)
    for it in sorted(items, key=lambda x: x["id"]):
        groups[it[key]].append(it)
    for g in groups.values():
        rng.shuffle(g)
    order = sorted(groups)
    out: list[dict] = []
    while len(out) < n and any(groups.values()):
        for name in order:
            if groups[name] and len(out) < n:
                out.append(groups[name].pop())
    return out


# --------------------------------------------------------------------------- chạy các lớp

def _layer_fields(prefix: str, res: Any) -> dict:
    return {f"{prefix}_action": res.action, f"{prefix}_score": "" if res.score is None else round(res.score, 4),
            f"{prefix}_reason": (res.reason or "")[:120]}


def run_l1(attacks: list[dict], benign: list[dict], l1_check: Callable) -> list[dict]:
    """L1 trên mọi mục: attack ở hai dạng embedded/bare, benign ở dạng document."""
    rows: list[dict] = []
    for it in attacks:
        for view, doc in (("embedded", it["untrusted_document"]), ("bare", it["injection_payload"])):
            rows.append({**_meta(it), "view": view, **_layer_fields("l1", l1_check(it["user_task"], doc)),
                         "_doc": doc, "_task": it["user_task"]})
    for it in benign:
        rows.append({**_meta(it), "view": "document",
                     **_layer_fields("l1", l1_check(it["user_task"], it["untrusted_document"])),
                     "_doc": it["untrusted_document"], "_task": it["user_task"]})
    return rows


def _meta(it: dict) -> dict:
    return {"id": it["id"], "label": it["label"], "subset": it.get("subset", ""),
            "attack_type": it.get("attack_type", "none"), "goal_type": it.get("goal_type", ""),
            "liu_type": it.get("liu_type", "none"), "context_kind": it.get("context_kind", "")}


def run_l2(rows: list[dict], attacks: list[dict], benign: list[dict], l1_check: Callable, l2_check: Callable,
           budget_exc: type[BaseException], n_l2: int, seed: int, calls_new: Callable[[], int]) -> dict:
    """Chạy L2 trên mẫu con; sửa `rows` tại chỗ (thêm trường l2_*, l1l2_blocked). Trả thông tin chạy.

    Thứ tự xen kẽ attack/benign (attack: bare rồi embedded) để khi hết ngân sách phần đã chạy vẫn cân bằng.
    """
    sa = sample_round_robin(attacks, n_l2, seed)
    sb = sample_round_robin(benign, n_l2, seed + 1)
    index = {(r["id"], r["view"]): r for r in rows}
    plan: list[tuple[str, str]] = []
    for i in range(max(len(sa), len(sb))):
        if i < len(sa):
            plan += [(sa[i]["id"], "bare"), (sa[i]["id"], "embedded")]
        if i < len(sb):
            plan.append((sb[i]["id"], "document"))
    info = {"planned_docs": len(plan), "done_docs": 0, "stopped": "", "sample_attack": len(sa),
            "sample_benign": len(sb)}
    for rid, view in plan:
        r = index[(rid, view)]
        before = calls_new()
        try:
            res = l2_check(r["_task"], r["_doc"])
            doc2 = r["_doc"]
            if r["l1_action"] == "sanitize":   # đúng như chuỗi thật: L2 nhìn tài liệu sau L1
                doc2 = l1_check(r["_task"], r["_doc"]).document
                res2 = res if doc2 == r["_doc"] else l2_check(r["_task"], doc2)
            else:
                res2 = res
        except budget_exc:
            info["stopped"] = "hết ngân sách lượt gọi model mới (--max-l2-calls hoặc --l2-cache-only)"
            break
        except (RuntimeError, OSError) as exc:  # Ollama lỗi: giữ kết quả L1, dừng L2 với thông báo rõ
            info["stopped"] = f"lỗi gọi model: {exc}"
            break
        r.update(_layer_fields("l2", res))
        r["l2_calls_new"] = calls_new() - before
        r["l1l2_blocked"] = int(r["l1_action"] == "block" or res2.action == "block")
        info["done_docs"] += 1
    return info


# --------------------------------------------------------------------------- tổng hợp

def _summ(rows: list[dict], scope: str, layer: str, flag: Callable[[dict], int]) -> list[dict]:
    out: list[dict] = []
    for label, views, dims in (("attack", ("embedded", "bare"), ATTACK_DIMS), ("benign", ("document",), BENIGN_DIMS)):
        for view in views:
            sub = [r for r in rows if r["label"] == label and r["view"] == view]
            if not sub:
                continue
            metric = "TPR" if label == "attack" else "FPR"
            groups = [("all", "all", sub)]
            for dim in dims:
                for v in sorted({r[dim] for r in sub}):
                    groups.append((dim, v, [r for r in sub if r[dim] == v]))
            rates = []
            for dim, v, g in groups:
                k, n = sum(flag(r) for r in g), len(g)
                lo, hi = wilson(k, n)
                out.append({"scope": scope, "layer": layer, "label": label, "view": view, "metric": metric,
                            "dim": dim, "value": v, "n": n, "k": k, "rate": round(k / n, 4),
                            "wilson_lo": round(lo, 4), "wilson_hi": round(hi, 4)})
                if dim == "subset":
                    rates.append(k / n)
            if rates:
                out.append({"scope": scope, "layer": layer, "label": label, "view": view, "metric": metric,
                            "dim": "macro_over_subset", "value": "mean", "n": len(sub), "k": "",
                            "rate": round(sum(rates) / len(rates), 4), "wilson_lo": "", "wilson_hi": ""})
    return out


def summarize(rows: list[dict]) -> list[dict]:
    out = _summ(rows, "full", "L1", lambda r: int(r["l1_action"] == "block"))
    l2_rows = [r for r in rows if r.get("l2_action")]
    if l2_rows:
        out += _summ(l2_rows, "l2_sample", "L1", lambda r: int(r["l1_action"] == "block"))
        out += _summ(l2_rows, "l2_sample", "L2", lambda r: int(r["l2_action"] == "block"))
        out += _summ(l2_rows, "l2_sample", "L1+L2", lambda r: int(r["l1l2_blocked"]))
    return out


# --------------------------------------------------------------------------- ghi kết quả

def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def _pct(x: Any) -> str:
    return "" if x in ("", None) else f"{100 * float(x):.1f}%"


def _cell(r: dict) -> str:
    if r["k"] == "":
        return f"{_pct(r['rate'])} (macro)"
    return f"{_pct(r['rate'])} [{_pct(r['wilson_lo'])}, {_pct(r['wilson_hi'])}] ({r['k']}/{r['n']})"


def md_tables(summary: list[dict]) -> str:
    """Bảng markdown: mỗi (scope, label, view, dim) một bảng hàng=value, cột=layer."""
    lines: list[str] = []
    keys = list(dict.fromkeys((r["scope"], r["label"], r["view"], r["dim"]) for r in summary))
    for scope, label, view, dim in keys:
        part = [r for r in summary if (r["scope"], r["label"], r["view"], r["dim"]) == (scope, label, view, dim)]
        layers = list(dict.fromkeys(r["layer"] for r in part))
        values = list(dict.fromkeys(r["value"] for r in part))
        metric = part[0]["metric"]
        title = f"{metric} {view}, theo `{dim}` (scope={scope})"
        lines += [f"#### {title}", "", "| " + " | ".join([dim] + layers) + " |",
                  "|" + "---|" * (len(layers) + 1)]
        for v in values:
            cells = []
            for lay in layers:
                hit = [r for r in part if r["value"] == v and r["layer"] == lay]
                cells.append(_cell(hit[0]) if hit else "-")
            lines.append("| " + " | ".join([str(v)] + cells) + " |")
        lines.append("")
    return "\n".join(lines)


def build_markdown(summary: list[dict], meta: dict) -> str:
    head = [f"# Phát hiện trên tập ngoài (zero-shot) — {meta['created_utc']}", "", f"> **{WARNING}**", "",
            "## Thiết lập", "",
            f"- Lệnh: `{meta['argv']}`; commit: `{meta['git_commit']}`",
            f"- Dữ liệu: {meta['n_attack']} mục tấn công (embedded + bare) và {meta['n_benign']} mục benign "
            f"(`ext_attack_full.json`, `ext_benign_full.json`; sha256 trong detection_meta.json)",
            f"- L1: THRESHOLD={meta['l1_threshold']}, chạy trên toàn bộ; thời gian L1 {meta['l1_seconds']:.0f}s",
            ]
    l2 = meta.get("l2")
    if l2:
        head.append(f"- L2: model `{meta['l2_model']}`, THRESHOLD={meta['l2_threshold']}, mẫu {l2['sample_attack']} attack + "
                    f"{l2['sample_benign']} benign đề ra; đã chạy xong {l2['done_docs']}/{l2['planned_docs']} tài liệu; "
                    f"lượt gọi model mới {meta['l2_new_calls']}; dừng: {l2['stopped'] or 'không (chạy hết)'}")
    else:
        head.append("- L2: không chạy (`--no-l2`)")
    head += ["", "Đọc kết quả: \"phát hiện\" = lớp trả `block`. `embedded` = tài liệu có payload nhúng; `bare` = chỉ payload. "
             "`macro_over_subset` là trung bình đơn giản qua các nguồn (tránh nguồn lớn chi phối). Wilson 95% theo số mục, "
             "coi các mục độc lập; nhiều mục cùng nguồn/tài liệu nền nên khoảng thực tế rộng hơn. Nhãn `goal_type`, "
             "`attack_type` do quy tắc gán (xem attack_prompts/README.md), không phải nhãn gốc của dataset.", "",
             "## Kết quả", ""]
    return "\n".join(head) + "\n" + md_tables(summary)


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- điều phối

def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data-dir", type=Path, default=DATA_DIR)
    ap.add_argument("--raw", type=Path, default=None, help="thư mục dữ liệu thô nếu phải dựng lại tệp full")
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--no-l2", action="store_true", help="bỏ L2 (không gọi model)")
    ap.add_argument("--n-l2", type=int, default=150, help="số mục mỗi bên (attack, benign) cho L2")
    ap.add_argument("--max-l2-calls", type=int, default=0, help="trần lượt gọi model mới cho L2 (0 = không giới hạn)")
    ap.add_argument("--l2-cache-only", action="store_true",
                    help="L2 chỉ dùng cache, không gọi model mới (tái tạo báo cáo từ lần chạy trước)")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)
    print(WARNING, file=sys.stderr)

    try:
        attacks, benign = load_full(args.data_dir, args.raw)
    except DetectionError as exc:
        print(f"LỖI: {exc}", file=sys.stderr)
        return 1
    from defenses import layer1_filtering as l1
    t0 = time.perf_counter()
    rows = run_l1(attacks, benign, l1.check)
    l1_seconds = time.perf_counter() - t0
    print(f"[L1] {len(rows)} lượt trong {l1_seconds:.0f}s", flush=True)

    meta: dict[str, Any] = {
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "argv": " ".join(sys.argv[1:]),
        "git_commit": _git("rev-parse", "HEAD"), "n_attack": len(attacks), "n_benign": len(benign),
        "l1_threshold": l1.THRESHOLD, "l1_seconds": l1_seconds, "seed": args.seed,
        "n_l2": args.n_l2, "max_l2_calls": args.max_l2_calls,
        "data_sha256": {n: sha_file(args.data_dir / n) for n in ("ext_attack_full.json", "ext_benign_full.json")},
    }
    if not args.no_l2:
        from defenses import layer2_refusal_classifier as l2
        l2._BUDGET["limit"] = (l2.STATS["calls"] if args.l2_cache_only
                               else (l2.STATS["calls"] + args.max_l2_calls) if args.max_l2_calls else None)
        start = l2.STATS["calls"]
        meta["l2_model"], meta["l2_threshold"] = l2._model(), l2.THRESHOLD
        meta["l2"] = run_l2(rows, attacks, benign, l1.check, l2.check, l2.BudgetExceeded, args.n_l2, args.seed,
                            lambda: l2.STATS["calls"])
        meta["l2_new_calls"] = l2.STATS["calls"] - start
        meta["l2_cache_hits"] = l2.STATS["hits"]
        print(f"[L2] {meta['l2']['done_docs']}/{meta['l2']['planned_docs']} tài liệu, "
              f"{meta['l2_new_calls']} lượt gọi mới; {meta['l2']['stopped'] or 'xong'}", flush=True)

    summary = summarize(rows)
    out = args.out or ROOT / "results" / "dev" / f"{datetime.now().strftime('%Y%m%d')}-ext-detection"
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "detection.csv", SUMMARY_COLUMNS, summary)
    write_csv(out / "detection_items.csv", ITEM_COLUMNS, rows)
    (out / "detection.md").write_text(build_markdown(summary, meta), encoding="utf-8")
    (out / "detection_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[OK] {out}/detection.csv, detection.md, detection_items.csv, detection_meta.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
