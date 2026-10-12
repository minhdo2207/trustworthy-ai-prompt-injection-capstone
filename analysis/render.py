"""Định dạng bảng: markdown, CSV, LaTeX booktabs và .dat cho pgfplots.

Mỗi `Table` có hai dạng: `data` (số thật, ra CSV để xử lý tiếp) và `display`
(chuỗi đã làm tròn, ra markdown/LaTeX để dán vào báo cáo).
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pandas as pd

_NUMERIC_CELL = re.compile(r"[\d\s.,+\-\[\]()/%x]*|n/a")
_TEX_SPECIAL = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
                "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


@dataclass
class Table:
    name: str                       # tên file ổn định, vd "tab01_asr_split"
    title: str                      # tiêu đề tiếng Việt cho report.md
    data: pd.DataFrame              # dạng số, ra CSV
    display: pd.DataFrame           # dạng chuỗi, ra md/tex
    note: str = ""
    group_col: str | None = None    # cột đầu của display để ngắt nhóm bằng \midrule
    split_col: str | None = None    # nếu có: thêm file tex riêng cho từng giá trị


def is_nan(x: object) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


def _fixed(v: float, digits: int) -> str:
    """Làm tròn nửa lên (31.25 -> 31.3) thay vì nửa chẵn của float, để bảng nhìn nhất quán; không in -0.0."""
    d = Decimal(repr(round(v, 9))).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)
    return f"{d:f}" if d != 0 else f"{Decimal(0).quantize(Decimal(1).scaleb(-digits)):f}"


def pct(x: float, digits: int = 1) -> str:
    """Tỉ lệ 0..1 -> "12.3" (đơn vị % nằm ở tiêu đề cột)."""
    return "n/a" if is_nan(x) else _fixed(100.0 * x, digits)


def pct_ci(lo: float, hi: float, digits: int = 1) -> str:
    return "n/a" if is_nan(lo) or is_nan(hi) else f"[{pct(lo, digits)}, {pct(hi, digits)}]"


def signed_pp(x: float, digits: int = 1) -> str:
    """Hiệu của hai tỉ lệ -> điểm phần trăm có dấu, vd "+3.2" hoặc "-12.5"."""
    if is_nan(x):
        return "n/a"
    s = _fixed(100.0 * x, digits)
    return s if float(s) == 0 else (s if s.startswith("-") else "+" + s)


def signed(x: float, digits: int = 3) -> str:
    """Số có dấu (không nhân 100), vd utility +0.083."""
    if is_nan(x):
        return "n/a"
    s = _fixed(x, digits)
    return s if float(s) == 0 else (s if s.startswith("-") else "+" + s)


def num(x: float, digits: int = 1) -> str:
    return "n/a" if is_nan(x) else f"{x:,.{digits}f}"


def ratio(x: float) -> str:
    return "n/a" if is_nan(x) else f"{x:.2f}x"


def escape_tex(text: str) -> str:
    return "".join(_TEX_SPECIAL.get(ch, ch) for ch in str(text))


def _is_numeric_column(col: pd.Series) -> bool:
    return len(col) > 0 and all(bool(_NUMERIC_CELL.fullmatch(str(v))) for v in col)


def md_table(display: pd.DataFrame) -> str:
    """Bảng markdown; ký tự | trong ô được thoát."""
    cols = list(display.columns)
    head = "| " + " | ".join(str(c) for c in cols) + " |"
    sep = "| " + " | ".join("---:" if _is_numeric_column(display[c]) else "---" for c in cols) + " |"
    rows = ["| " + " | ".join(str(v).replace("|", "\\|") for v in r) + " |"
            for r in display.itertuples(index=False)]
    return "\n".join([head, sep, *rows])


def tex_table(display: pd.DataFrame, group_col: str | None = None) -> str:
    """`tabular` booktabs trần (không bọc `table`) để báo cáo tự \\input vào môi trường mình chọn."""
    cols = list(display.columns)
    align = "".join("r" if _is_numeric_column(display[c]) and c != group_col else "l" for c in cols)
    lines = [
        "% Sinh tự động bởi analysis.stats; cần \\usepackage{booktabs}. Không sửa tay.",
        f"\\begin{{tabular}}{{{align}}}",
        "\\toprule",
        " & ".join(escape_tex(c) for c in cols) + " \\\\",
        "\\midrule",
    ]
    prev: str | None = None
    for r in display.itertuples(index=False):
        cells = [str(v) for v in r]
        if group_col is not None:
            g = cells[cols.index(group_col)]
            if prev is not None and g != prev:
                lines.append("\\midrule")
            if g == prev:
                cells[cols.index(group_col)] = ""
            prev = g
        lines.append(" & ".join(escape_tex(c) for c in cells) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    return "\n".join(lines) + "\n"


def write_table(table: Table, out: Path) -> list[Path]:
    """Ghi csv/, md/, tables/ (và tex theo từng split nếu `split_col`). Trả danh sách file."""
    paths: list[Path] = []
    for sub in ("csv", "md", "tables"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    def put(sub: str, ext: str, name: str, text: str) -> None:
        p = out / sub / f"{name}.{ext}"
        p.write_text(text, encoding="utf-8")
        paths.append(p)

    put("csv", "csv", table.name, table.data.to_csv(index=False))
    put("md", "md", table.name, f"**{table.title}**\n\n{md_table(table.display)}\n"
        + (f"\n{table.note}\n" if table.note else ""))
    put("tables", "tex", table.name, tex_table(table.display, table.group_col))
    if table.split_col and table.split_col in table.display.columns:
        for value, part in table.display.groupby(table.split_col, sort=False):
            part = part.drop(columns=[table.split_col])
            gc = table.group_col if table.group_col != table.split_col else None
            put("tables", "tex", f"{table.name}_{value}", tex_table(part, gc))
    return paths


def tex_label(config: str) -> str:
    """Nhãn an toàn cho trục pgfplots: thoát dấu gạch dưới."""
    return config.replace("_", r"\_")


def dat_text(df: pd.DataFrame) -> str:
    """Bảng cách nhau bằng dấu cách, hàng đầu là tên cột; NaN -> `nan` (pgfplots bỏ qua điểm này)."""
    def cell(v: object) -> str:
        if isinstance(v, float):
            return "nan" if math.isnan(v) else f"{v:.6g}"
        s = str(v)
        if re.search(r"\s", s):
            raise ValueError(f"ô .dat chứa khoảng trắng: {s!r}")
        return s

    lines = [" ".join(df.columns)]
    lines += [" ".join(cell(v) for v in r) for r in df.itertuples(index=False)]
    return "\n".join(lines) + "\n"


def write_dat(df: pd.DataFrame, name: str, out: Path) -> Path:
    (out / "dat").mkdir(parents=True, exist_ok=True)
    p = out / "dat" / f"{name}.dat"
    p.write_text(dat_text(df), encoding="utf-8")
    return p
