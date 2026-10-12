# Phát hiện trên tập ngoài (zero-shot) — 2026-10-11T14:29:29+00:00

> **CẢNH BÁO: đánh giá ZERO-SHOT. L1/L2 đã được chỉnh trên train và benign `tune` của nhóm; tuyệt đối không chỉnh L1/L2 theo kết quả này.**

## Thiết lập

- Lệnh: `--no-l2 --out results/final/detection-l1`; commit: `574f0d586c58427b3c3cb485c0da4f397c7c8538`
- Dữ liệu: 2021 mục tấn công (embedded + bare) và 1729 mục benign (`ext_attack_full.json`, `ext_benign_full.json`; sha256 trong detection_meta.json)
- L1: THRESHOLD=0.6, chạy trên toàn bộ; thời gian L1 76s
- L2: không chạy (`--no-l2`)

Đọc kết quả: "phát hiện" = lớp trả `block`. `embedded` = tài liệu có payload nhúng; `bare` = chỉ payload. `macro_over_subset` là trung bình đơn giản qua các nguồn (tránh nguồn lớn chi phối). Wilson 95% theo số mục, coi các mục độc lập; nhiều mục cùng nguồn/tài liệu nền nên khoảng thực tế rộng hơn. Nhãn `goal_type`, `attack_type` do quy tắc gán (xem attack_prompts/README.md), không phải nhãn gốc của dataset.

## Kết quả

#### TPR embedded, theo `all` (scope=full)

| all | L1 |
|---|---|
| all | 37.6% [35.6%, 39.8%] (761/2021) |

#### TPR embedded, theo `subset` (scope=full)

| subset | L1 |
|---|---|
| bipia_code | 10.0% [5.5%, 17.4%] (10/100) |
| bipia_text | 0.0% [0.0%, 2.5%] (0/150) |
| deepset | 13.6% [9.9%, 18.4%] (34/250) |
| gandalf | 51.4% [48.2%, 54.5%] (509/991) |
| jackhhao | 39.2% [35.2%, 43.5%] (208/530) |

#### TPR embedded, theo `attack_type` (scope=full)

| attack_type | L1 |
|---|---|
| code_switching_translation | 11.5% [6.5%, 19.4%] (11/96) |
| direct_injection | 44.0% [41.3%, 46.8%] (546/1241) |
| indirect_injection | 4.0% [2.2%, 7.2%] (10/250) |
| jailbreak_roleplay | 44.7% [40.1%, 49.4%] (194/434) |

#### TPR embedded, theo `goal_type` (scope=full)

| goal_type | L1 |
|---|---|
| leak | 61.2% [56.7%, 65.5%] (287/469) |
| other | 30.5% [28.3%, 32.9%] (474/1552) |

#### TPR embedded, theo `liu_type` (scope=full)

| liu_type | L1 |
|---|---|
| context_ignoring | 72.5% [68.9%, 75.8%] (469/647) |
| naive | 4.0% [2.2%, 7.2%] (10/250) |
| none | 25.1% [22.6%, 27.7%] (282/1124) |

#### TPR embedded, theo `context_kind` (scope=full)

| context_kind | L1 |
|---|---|
| carrier | 42.3% [39.1%, 45.5%] (374/885) |
| code | 10.0% [5.5%, 17.4%] (10/100) |
| email | 34.4% [30.3%, 38.7%] (169/491) |
| table | 38.2% [34.2%, 42.3%] (208/545) |

#### TPR embedded, theo `macro_over_subset` (scope=full)

| macro_over_subset | L1 |
|---|---|
| mean | 22.8% (macro) |

#### TPR bare, theo `all` (scope=full)

| all | L1 |
|---|---|
| all | 37.4% [35.3%, 39.5%] (756/2021) |

#### TPR bare, theo `subset` (scope=full)

| subset | L1 |
|---|---|
| bipia_code | 5.0% [2.1%, 11.2%] (5/100) |
| bipia_text | 0.0% [0.0%, 2.5%] (0/150) |
| deepset | 13.6% [9.9%, 18.4%] (34/250) |
| gandalf | 51.4% [48.2%, 54.5%] (509/991) |
| jackhhao | 39.2% [35.2%, 43.5%] (208/530) |

#### TPR bare, theo `attack_type` (scope=full)

| attack_type | L1 |
|---|---|
| code_switching_translation | 11.5% [6.5%, 19.4%] (11/96) |
| direct_injection | 44.0% [41.3%, 46.8%] (546/1241) |
| indirect_injection | 2.0% [0.9%, 4.6%] (5/250) |
| jailbreak_roleplay | 44.7% [40.1%, 49.4%] (194/434) |

#### TPR bare, theo `goal_type` (scope=full)

| goal_type | L1 |
|---|---|
| leak | 61.2% [56.7%, 65.5%] (287/469) |
| other | 30.2% [28.0%, 32.6%] (469/1552) |

#### TPR bare, theo `liu_type` (scope=full)

| liu_type | L1 |
|---|---|
| context_ignoring | 72.5% [68.9%, 75.8%] (469/647) |
| naive | 2.0% [0.9%, 4.6%] (5/250) |
| none | 25.1% [22.6%, 27.7%] (282/1124) |

#### TPR bare, theo `context_kind` (scope=full)

| context_kind | L1 |
|---|---|
| carrier | 42.3% [39.1%, 45.5%] (374/885) |
| code | 5.0% [2.1%, 11.2%] (5/100) |
| email | 34.4% [30.3%, 38.7%] (169/491) |
| table | 38.2% [34.2%, 42.3%] (208/545) |

#### TPR bare, theo `macro_over_subset` (scope=full)

| macro_over_subset | L1 |
|---|---|
| mean | 21.8% (macro) |

#### FPR document, theo `all` (scope=full)

| all | L1 |
|---|---|
| all | 0.2% [0.1%, 0.6%] (4/1729) |

#### FPR document, theo `subset` (scope=full)

| subset | L1 |
|---|---|
| bipia_code | 4.0% [1.6%, 9.9%] (4/99) |
| bipia_email | 0.0% [0.0%, 7.3%] (0/49) |
| bipia_table | 0.0% [0.0%, 0.5%] (0/701) |
| deepset | 0.0% [0.0%, 1.5%] (0/247) |
| jackhhao | 0.0% [0.0%, 0.6%] (0/633) |

#### FPR document, theo `context_kind` (scope=full)

| context_kind | L1 |
|---|---|
| code | 4.0% [1.6%, 9.9%] (4/99) |
| email | 0.0% [0.0%, 7.3%] (0/49) |
| none | 0.0% [0.0%, 0.4%] (0/880) |
| table | 0.0% [0.0%, 0.5%] (0/701) |

#### FPR document, theo `macro_over_subset` (scope=full)

| macro_over_subset | L1 |
|---|---|
| mean | 0.8% (macro) |
