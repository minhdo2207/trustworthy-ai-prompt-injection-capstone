"""Khoảng tin cậy chỉ dùng thư viện chuẩn: Wilson và bootstrap theo cụm (prompt).

Vì sao bootstrap theo cụm: các lần lấy mẫu của cùng một prompt không độc lập
(cùng một nội dung tấn công), nên Wilson trên tổng số lượt coi mỗi lượt là một
quan sát độc lập và cho khoảng quá hẹp. Đơn vị độc lập hợp lý hơn là *prompt*:
ta resample prompt (có hoàn lại) rồi lấy trung bình ASR theo prompt.
"""
from __future__ import annotations

import math
import random
from typing import Sequence

NAN = float("nan")
DEFAULT_B = 2000
DEFAULT_SEED = 20261009


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Khoảng Wilson cho tỉ lệ k/n; n=0 trả (nan, nan).

    Chọn Wilson thay vì Wald vì đúng ở biên (k=0 hoặc k=n) và ít phụ thuộc
    vào n nhỏ, đúng kiểu dữ liệu ASR của đồ án.
    """
    if n <= 0:
        return NAN, NAN
    if not 0 <= k <= n:
        raise ValueError(f"wilson: cần 0 <= k <= n, nhận k={k}, n={n}")
    p = k / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = (p + z2 / (2.0 * n)) / denom
    half = z * math.sqrt(p * (1.0 - p) / n + z2 / (4.0 * n * n)) / denom
    lo = 0.0 if k == 0 else max(0.0, centre - half)
    hi = 1.0 if k == n else min(1.0, centre + half)
    return lo, hi


def quantile(sorted_values: Sequence[float], q: float) -> float:
    """Phân vị q (0..1) nội suy tuyến tính trên dãy đã sắp xếp (kiểu numpy 'linear')."""
    if not sorted_values:
        return NAN
    pos = q * (len(sorted_values) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    frac = pos - lo
    return sorted_values[lo] * (1.0 - frac) + sorted_values[hi] * frac


def _percentile_ci(stats: list[float], alpha: float) -> tuple[float, float]:
    stats.sort()
    return quantile(stats, alpha / 2.0), quantile(stats, 1.0 - alpha / 2.0)


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if len(values) else NAN


def _resample_means(values: Sequence[float], rng: random.Random, b: int) -> list[float]:
    n = len(values)
    return [sum(rng.choices(values, k=n)) / n for _ in range(b)]


def bootstrap_mean_ci(
    values: Sequence[float],
    *,
    b: int = DEFAULT_B,
    seed: int = DEFAULT_SEED,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Khoảng bootstrap phân vị cho trung bình của `values` (mỗi phần tử = một cụm/prompt).

    Dùng `random.Random(seed)` mới cho mỗi lời gọi nên kết quả không phụ thuộc
    thứ tự tính các bảng. Rỗng -> (nan, nan); một phần tử -> khoảng suy biến.
    """
    n = len(values)
    if n == 0:
        return NAN, NAN
    if n == 1:
        return float(values[0]), float(values[0])
    rng = random.Random(seed)
    return _percentile_ci(_resample_means(list(values), rng, b), alpha)


def bootstrap_diff_ci(
    a: Sequence[float],
    b_values: Sequence[float],
    *,
    paired: bool,
    b: int = DEFAULT_B,
    seed: int = DEFAULT_SEED,
    alpha: float = 0.05,
) -> tuple[float, float, float]:
    """Hiệu mean(a) - mean(b_values) và khoảng bootstrap phân vị.

    paired=True: a[i] và b_values[i] cùng một prompt; resample chỉ số chung nên
    giữ được tương quan giữa hai cấu hình (khoảng hẹp hơn, đúng hơn).
    paired=False: hai tập prompt khác nhau (vd train vs holdout) -> resample độc lập.
    Trả (hiệu, lo, hi); thiếu dữ liệu -> nan.
    """
    if paired and len(a) != len(b_values):
        raise ValueError("bootstrap_diff_ci paired=True cần hai dãy cùng độ dài")
    if len(a) == 0 or len(b_values) == 0:
        return NAN, NAN, NAN
    diff = _mean(a) - _mean(b_values)
    rng = random.Random(seed)
    stats: list[float] = []
    if paired:
        n = len(a)
        if n == 1:
            return diff, diff, diff
        d = [x - y for x, y in zip(a, b_values)]
        stats = _resample_means(d, rng, b)
    else:
        na, nb = len(a), len(b_values)
        av, bv = list(a), list(b_values)
        for _ in range(b):
            ma = sum(rng.choices(av, k=na)) / na
            mb = sum(rng.choices(bv, k=nb)) / nb
            stats.append(ma - mb)
    lo, hi = _percentile_ci(stats, alpha)
    return diff, lo, hi


__all__ = [
    "DEFAULT_B", "DEFAULT_SEED", "NAN", "bootstrap_diff_ci", "bootstrap_mean_ci",
    "quantile", "wilson",
]
