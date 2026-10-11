#!/usr/bin/env python3
"""Sinh phụ lục A (bảng toàn bộ prompt) thành tệp LaTeX `sections/appendix_prompts_table.tex`.

Nguồn dữ liệu, theo thứ tự ưu tiên:
  1. commit mới nhất có tiêu đề bắt đầu bằng "milestone:" trên nhánh --ref (dữ liệu đã đóng băng);
  2. đầu nhánh --ref nếu tệp ở đó đã theo schema v2 (có trường `untrusted_document`);
  3. tệp trong worktree hiện tại (schema cũ: id, content, attack_type, technique, target).

Kỷ luật hold-out: `holdout_prompts.json` KHÔNG được đọc trừ khi có cờ --include-holdout
(chỉ dùng khi in bản báo cáo cuối, sau khi đã chạy xong hold-out).

Dùng: python3 scripts/gen_appendix.py [--ref tmp/01-data] [--include-holdout]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import unicodedata
from pathlib import Path

REPORT_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = REPORT_DIR.parent
DEFAULT_OUT = REPORT_DIR / "sections" / "appendix_prompts_table.tex"

SPLIT_FILES = {
    "train": "attack_prompts/train_prompts.json",
    "test_indist": "attack_prompts/test_indist_prompts.json",
    "holdout": "attack_prompts/holdout_prompts.json",
    "benign": "attack_prompts/benign_prompts.json",
}
TYPE_VI = {
    "direct_injection": "trực tiếp",
    "indirect_injection": "gián tiếp",
    "jailbreak_roleplay": "roleplay",
    "code_switching_translation": "đổi ngôn ngữ",
    "obfuscation": "che giấu",
    "many_shot_jailbreaking": "many-shot",
    "none": "benign",
}
LATEX_SPECIAL = {
    "\\": r"\textbackslash{}", "{": r"\{", "}": r"\}", "#": r"\#", "$": r"\$",
    "%": r"\%", "&": r"\&", "_": r"\_", "^": r"\textasciicircum{}",
    "~": r"\textasciitilde{}", "<": r"\textless{}", ">": r"\textgreater{}",
    "|": r"\textbar{}", '"': r"\textquotedbl{}", "`": r"\textasciigrave{}",
    "'": r"\textquotesingle{}",
}
SAFE_RANGES = [
    (0x20, 0x7E), (0xA0, 0xFF), (0x100, 0x24F), (0x1E00, 0x1EFF),
    (0x2013, 0x2014), (0x2018, 0x201D), (0x2026, 0x2026),
]


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(REPO_ROOT), *args], capture_output=True,
                             text=True, check=True)
        return out.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _is_v2(rows: list) -> bool:
    return bool(rows) and isinstance(rows[0], dict) and "untrusted_document" in rows[0]


def _parse(text: str | None) -> list | None:
    if not text:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, list) else None


def load_split(split: str, ref: str, milestone: str | None) -> tuple[list, str]:
    """Trả (danh sách prompt, mô tả nguồn). Rỗng nếu không có dữ liệu."""
    rel = SPLIT_FILES[split]
    if milestone:
        rows = _parse(_git("show", f"{milestone}:{rel}"))
        if rows:
            return rows, f"commit milestone {milestone[:7]} của {ref}"
    rows = _parse(_git("show", f"{ref}:{rel}"))
    if rows and _is_v2(rows):
        return rows, f"đầu nhánh {ref} (schema v2)"
    local = REPO_ROOT / rel
    if local.exists():
        rows = _parse(local.read_text(encoding="utf-8"))
        if rows:
            return rows, "worktree hiện tại (" + ("schema v2" if _is_v2(rows) else "schema cũ") + ")"
    return [], "không có dữ liệu"


def benign_summary(rows: list) -> str:
    """Một dòng thống kê cho tập benign (không liệt kê từng tài liệu dài)."""
    from collections import Counter
    by_src = Counter(
        (r.get("source") or {}).get("name", "?") if isinstance(r.get("source"), dict) else "?"
        for r in rows)
    parts = ", ".join(f"{tex_escape(k, chunk=10**6)}: {v}" for k, v in by_src.most_common())
    return (f"Tập benign gồm {len(rows)} tài liệu sạch (theo nguồn: {parts}); mỗi mẫu là một tài liệu dài nên "
            "không liệt kê từng dòng ở đây, xem \\texttt{benign\\_prompts.json} (dùng --include-benign để in đủ).")


def find_milestone(ref: str) -> str | None:
    out = _git("log", ref, "--format=%H%x09%s")
    for line in (out or "").splitlines():
        sha, _, subject = line.partition("\t")
        if subject.lower().startswith("milestone:"):
            return sha
    return None


def _safe(ch: str) -> bool:
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in SAFE_RANGES)


def tex_escape(text: str, max_chars: int | None = None, chunk: int = 7) -> str:
    """Thoát ký tự LaTeX, hiển thị ký tự lạ dưới dạng mã U+XXXX, cho phép ngắt chuỗi dài."""
    text = unicodedata.normalize("NFC", " ".join(text.split()))
    truncated = False
    if max_chars is not None and len(text) > max_chars:
        text, truncated = text[:max_chars], True
    out: list[str] = []
    run = 0
    for ch in text:
        if ch == " ":
            out.append(" ")
            run = 0
            continue
        if _safe(ch):
            out.append(LATEX_SPECIAL.get(ch, ch))
        else:
            out.append(r"\ucode{%04X}" % ord(ch))
        run += 1
        if run % chunk == 0:
            out.append(r"\allowbreak{}")
    if truncated:
        out.append(r" [\dots]")
    return "".join(out)


def _source_label(row: dict) -> str:
    src = row.get("source")
    if isinstance(src, dict):
        if src.get("origin") == "dataset":
            return tex_escape(src.get("name") or "dataset")
        return tex_escape(src["name"]) if src.get("name") else "tự viết"
    return "tự viết"


def normalise(row: dict, split: str) -> dict:
    """Đưa cả schema cũ và v2 về cùng một dạng để in."""
    payload = row.get("injection_payload") or row.get("untrusted_document") or row.get("content") or ""
    return {
        "id": row.get("id", "?"),
        "type": TYPE_VI.get(row.get("attack_type", "none"), row.get("attack_type", "?")),
        "technique": row.get("technique") or "—",
        "liu": row.get("liu_type") or "—",
        "goal": row.get("goal_type") or "—",
        "source": _source_label(row),
        "payload": payload,
        "split": split,
    }


def render(rows_by_split: dict[str, tuple[list, str]], max_chars: int, skipped: list[str]) -> str:
    lines = [
        "% Tệp sinh tự động bởi scripts/gen_appendix.py --- không sửa tay.",
        r"\begingroup\scriptsize\setlength{\tabcolsep}{3pt}\renewcommand{\arraystretch}{1.0}",
        r"\newcommand{\cellp}[1]{\raggedright\arraybackslash #1}",
    ]
    notes = [f"{split}: {len(rows)} prompt, nguồn {desc}" for split, (rows, desc) in rows_by_split.items()]
    lines.append(r"\par\noindent{\small\textit{Dữ liệu dùng để sinh bảng: " + "; ".join(tex_escape(n, chunk=10**6) for n in notes) + r".}}\par\vspace{2pt}")
    for sk in skipped:
        lines.append(r"\par\noindent{\small " + sk + r"}\par\vspace{2pt}")
    header = (r"\textbf{ID} & \textbf{Loại / kỹ thuật} & \textbf{Kiểu Liu / mục tiêu} "
              r"& \textbf{Nguồn} & \textbf{Trích đoạn payload (tối đa %d ký tự)} \\" % max_chars)
    spec = r"p{1.0cm}p{2.85cm}p{2.0cm}p{1.15cm}p{8.4cm}"
    lines += [
        r"\begin{longtable}{@{}" + spec + r"@{}}",
        r"\caption[Toàn bộ prompt tấn công]{Toàn bộ prompt tấn công dùng trong báo cáo (trích đoạn payload; ký tự lạ hiển thị dạng \ucode{XXXX}).}\label{tab:app-prompts}\\",
        r"\toprule", header, r"\midrule\endfirsthead",
        r"\toprule", header, r"\midrule\endhead",
        r"\bottomrule\endfoot",
    ]
    for split, (rows, _desc) in rows_by_split.items():
        if not rows:
            continue
        lines.append(r"\midrule\multicolumn{5}{@{}l}{\textit{\small Tập %s (%d prompt)}}\\\midrule" %
                     (tex_escape(split), len(rows)))
        for row in rows:
            n = normalise(row, split)
            cells = [
                tex_escape(n["id"]),
                tex_escape(n["type"]) + r": \textit{" + tex_escape(n["technique"], chunk=9) + "}",
                tex_escape(n["liu"], chunk=9) + r" / " + tex_escape(n["goal"]),
                n["source"],
                r"\texttt{" + tex_escape(n["payload"], max_chars) + "}",
            ]
            lines.append(" & ".join(r"\cellp{%s}" % c for c in cells) + r" \\")
    lines += [r"\end{longtable}", r"\endgroup"]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ref", default="tmp/01-data", help="nhánh chứa dữ liệu v2")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--max-chars", type=int, default=120)
    ap.add_argument("--include-benign", action="store_true",
                    help="liệt kê từng tài liệu benign (mặc định chỉ tóm tắt vì mỗi mẫu là tài liệu dài)")
    ap.add_argument("--include-holdout", action="store_true",
                    help="chỉ dùng cho bản cuối, sau khi đã chạy hold-out")
    args = ap.parse_args(argv)

    milestone = find_milestone(args.ref)
    rows_by_split: dict[str, tuple[list, str]] = {}
    skipped: list[str] = []
    for split in ("train", "test_indist", "holdout", "benign"):
        if split == "holdout" and not args.include_holdout:
            skipped.append(r"Tập hold-out chưa được đưa vào bản này: \TODO{chạy lại script với --include-holdout sau khi đã chạy hold-out}.")
            continue
        rows, desc = load_split(split, args.ref, milestone)
        if rows and split == "benign" and not args.include_benign:
            skipped.append(benign_summary(rows))
            continue
        if rows:
            rows_by_split[split] = (rows, desc)
    if not rows_by_split:
        print("Không tìm thấy dữ liệu prompt nào.", file=sys.stderr)
        return 1
    args.out.write_text(render(rows_by_split, args.max_chars, skipped), encoding="utf-8")
    for split, (rows, desc) in rows_by_split.items():
        print(f"{split}: {len(rows)} prompt <- {desc}")
    print(f"Đã ghi {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
