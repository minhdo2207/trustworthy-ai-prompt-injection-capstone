# Phát hiện trên tập ngoài (zero-shot) — 2026-10-11T23:07:36+00:00

> **CẢNH BÁO: đánh giá ZERO-SHOT. L1/L2 đã được chỉnh trên train và benign `tune` của nhóm; tuyệt đối không chỉnh L1/L2 theo kết quả này.**

## Thiết lập

- Lệnh: `--n-l2 150 --max-l2-calls 0 --out results/final/detection-l2`; commit: `bb33fed8fd1396b8a8a76305157fe00812e8d1dc`
- Dữ liệu: 2021 mục tấn công (embedded + bare) và 1729 mục benign (`ext_attack_full.json`, `ext_benign_full.json`; sha256 trong detection_meta.json)
- L1: THRESHOLD=0.6, chạy trên toàn bộ; thời gian L1 73s
- L2: model `qwen2.5:3b`, THRESHOLD=0.5, mẫu 150 attack + 150 benign đề ra; đã chạy xong 450/450 tài liệu; lượt gọi model mới 759; dừng: không (chạy hết)

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

#### TPR embedded, theo `all` (scope=l2_sample)

| all | L1 | L2 | L1+L2 |
|---|---|---|---|
| all | 24.0% [17.9%, 31.4%] (36/150) | 45.3% [37.6%, 53.3%] (68/150) | 50.0% [42.1%, 57.9%] (75/150) |

#### TPR embedded, theo `subset` (scope=l2_sample)

| subset | L1 | L2 | L1+L2 |
|---|---|---|---|
| bipia_code | 10.0% [3.5%, 25.6%] (3/30) | 70.0% [52.1%, 83.3%] (21/30) | 70.0% [52.1%, 83.3%] (21/30) |
| bipia_text | 0.0% [0.0%, 11.3%] (0/30) | 0.0% [0.0%, 11.3%] (0/30) | 0.0% [0.0%, 11.3%] (0/30) |
| deepset | 16.7% [7.3%, 33.6%] (5/30) | 36.7% [21.9%, 54.5%] (11/30) | 40.0% [24.6%, 57.7%] (12/30) |
| gandalf | 46.7% [30.2%, 63.9%] (14/30) | 46.7% [30.2%, 63.9%] (14/30) | 60.0% [42.3%, 75.4%] (18/30) |
| jackhhao | 46.7% [30.2%, 63.9%] (14/30) | 73.3% [55.5%, 85.8%] (22/30) | 80.0% [62.7%, 90.5%] (24/30) |

#### TPR embedded, theo `attack_type` (scope=l2_sample)

| attack_type | L1 | L2 | L1+L2 |
|---|---|---|---|
| code_switching_translation | 11.1% [2.0%, 43.5%] (1/9) | 22.2% [6.3%, 54.7%] (2/9) | 22.2% [6.3%, 54.7%] (2/9) |
| direct_injection | 36.4% [24.9%, 49.6%] (20/55) | 43.6% [31.4%, 56.7%] (24/55) | 56.4% [43.3%, 68.6%] (31/55) |
| indirect_injection | 5.0% [1.7%, 13.7%] (3/60) | 35.0% [24.2%, 47.6%] (21/60) | 35.0% [24.2%, 47.6%] (21/60) |
| jailbreak_roleplay | 46.2% [28.8%, 64.5%] (12/26) | 80.8% [62.1%, 91.5%] (21/26) | 80.8% [62.1%, 91.5%] (21/26) |

#### TPR embedded, theo `goal_type` (scope=l2_sample)

| goal_type | L1 | L2 | L1+L2 |
|---|---|---|---|
| leak | 62.5% [38.6%, 81.5%] (10/16) | 68.8% [44.4%, 85.8%] (11/16) | 81.2% [57.0%, 93.4%] (13/16) |
| other | 19.4% [13.6%, 26.9%] (26/134) | 42.5% [34.5%, 51.0%] (57/134) | 46.3% [38.0%, 54.7%] (62/134) |

#### TPR embedded, theo `liu_type` (scope=l2_sample)

| liu_type | L1 | L2 | L1+L2 |
|---|---|---|---|
| context_ignoring | 63.2% [41.0%, 80.8%] (12/19) | 68.4% [46.0%, 84.6%] (13/19) | 89.5% [68.6%, 97.1%] (17/19) |
| naive | 5.0% [1.7%, 13.7%] (3/60) | 35.0% [24.2%, 47.6%] (21/60) | 35.0% [24.2%, 47.6%] (21/60) |
| none | 29.6% [20.2%, 41.0%] (21/71) | 47.9% [36.7%, 59.3%] (34/71) | 52.1% [40.7%, 63.3%] (37/71) |

#### TPR embedded, theo `context_kind` (scope=l2_sample)

| context_kind | L1 | L2 | L1+L2 |
|---|---|---|---|
| carrier | 34.1% [21.9%, 48.9%] (15/44) | 59.1% [44.4%, 72.3%] (26/44) | 68.2% [53.4%, 80.0%] (30/44) |
| code | 10.0% [3.5%, 25.6%] (3/30) | 70.0% [52.1%, 83.3%] (21/30) | 70.0% [52.1%, 83.3%] (21/30) |
| email | 17.2% [7.6%, 34.5%] (5/29) | 24.1% [12.2%, 42.1%] (7/29) | 31.0% [17.3%, 49.2%] (9/29) |
| table | 27.7% [16.9%, 41.8%] (13/47) | 29.8% [18.6%, 44.0%] (14/47) | 31.9% [20.4%, 46.2%] (15/47) |

#### TPR embedded, theo `macro_over_subset` (scope=l2_sample)

| macro_over_subset | L1 | L2 | L1+L2 |
|---|---|---|---|
| mean | 24.0% (macro) | 45.3% (macro) | 50.0% (macro) |

#### TPR bare, theo `all` (scope=l2_sample)

| all | L1 | L2 | L1+L2 |
|---|---|---|---|
| all | 22.7% [16.7%, 30.0%] (34/150) | 49.3% [41.4%, 57.2%] (74/150) | 52.7% [44.7%, 60.5%] (79/150) |

#### TPR bare, theo `subset` (scope=l2_sample)

| subset | L1 | L2 | L1+L2 |
|---|---|---|---|
| bipia_code | 3.3% [0.6%, 16.7%] (1/30) | 46.7% [30.2%, 63.9%] (14/30) | 46.7% [30.2%, 63.9%] (14/30) |
| bipia_text | 0.0% [0.0%, 11.3%] (0/30) | 10.0% [3.5%, 25.6%] (3/30) | 10.0% [3.5%, 25.6%] (3/30) |
| deepset | 16.7% [7.3%, 33.6%] (5/30) | 46.7% [30.2%, 63.9%] (14/30) | 46.7% [30.2%, 63.9%] (14/30) |
| gandalf | 46.7% [30.2%, 63.9%] (14/30) | 66.7% [48.8%, 80.8%] (20/30) | 76.7% [59.1%, 88.2%] (23/30) |
| jackhhao | 46.7% [30.2%, 63.9%] (14/30) | 76.7% [59.1%, 88.2%] (23/30) | 83.3% [66.4%, 92.7%] (25/30) |

#### TPR bare, theo `attack_type` (scope=l2_sample)

| attack_type | L1 | L2 | L1+L2 |
|---|---|---|---|
| code_switching_translation | 11.1% [2.0%, 43.5%] (1/9) | 22.2% [6.3%, 54.7%] (2/9) | 22.2% [6.3%, 54.7%] (2/9) |
| direct_injection | 36.4% [24.9%, 49.6%] (20/55) | 58.2% [45.0%, 70.3%] (32/55) | 67.3% [54.1%, 78.2%] (37/55) |
| indirect_injection | 1.7% [0.3%, 8.9%] (1/60) | 28.3% [18.5%, 40.8%] (17/60) | 28.3% [18.5%, 40.8%] (17/60) |
| jailbreak_roleplay | 46.2% [28.8%, 64.5%] (12/26) | 88.5% [71.0%, 96.0%] (23/26) | 88.5% [71.0%, 96.0%] (23/26) |

#### TPR bare, theo `goal_type` (scope=l2_sample)

| goal_type | L1 | L2 | L1+L2 |
|---|---|---|---|
| leak | 62.5% [38.6%, 81.5%] (10/16) | 81.2% [57.0%, 93.4%] (13/16) | 87.5% [64.0%, 96.5%] (14/16) |
| other | 17.9% [12.3%, 25.3%] (24/134) | 45.5% [37.3%, 54.0%] (61/134) | 48.5% [40.2%, 56.9%] (65/134) |

#### TPR bare, theo `liu_type` (scope=l2_sample)

| liu_type | L1 | L2 | L1+L2 |
|---|---|---|---|
| context_ignoring | 63.2% [41.0%, 80.8%] (12/19) | 79.0% [56.7%, 91.5%] (15/19) | 89.5% [68.6%, 97.1%] (17/19) |
| naive | 1.7% [0.3%, 8.9%] (1/60) | 28.3% [18.5%, 40.8%] (17/60) | 28.3% [18.5%, 40.8%] (17/60) |
| none | 29.6% [20.2%, 41.0%] (21/71) | 59.2% [47.5%, 69.8%] (42/71) | 63.4% [51.8%, 73.6%] (45/71) |

#### TPR bare, theo `context_kind` (scope=l2_sample)

| context_kind | L1 | L2 | L1+L2 |
|---|---|---|---|
| carrier | 34.1% [21.9%, 48.9%] (15/44) | 68.2% [53.4%, 80.0%] (30/44) | 72.7% [58.1%, 83.7%] (32/44) |
| code | 3.3% [0.6%, 16.7%] (1/30) | 46.7% [30.2%, 63.9%] (14/30) | 46.7% [30.2%, 63.9%] (14/30) |
| email | 17.2% [7.6%, 34.5%] (5/29) | 34.5% [19.9%, 52.7%] (10/29) | 41.4% [25.5%, 59.3%] (12/29) |
| table | 27.7% [16.9%, 41.8%] (13/47) | 42.5% [29.5%, 56.7%] (20/47) | 44.7% [31.4%, 58.8%] (21/47) |

#### TPR bare, theo `macro_over_subset` (scope=l2_sample)

| macro_over_subset | L1 | L2 | L1+L2 |
|---|---|---|---|
| mean | 22.7% (macro) | 49.3% (macro) | 52.7% (macro) |

#### FPR document, theo `all` (scope=l2_sample)

| all | L1 | L2 | L1+L2 |
|---|---|---|---|
| all | 0.0% [0.0%, 2.5%] (0/150) | 2.7% [1.0%, 6.7%] (4/150) | 2.7% [1.0%, 6.7%] (4/150) |

#### FPR document, theo `subset` (scope=l2_sample)

| subset | L1 | L2 | L1+L2 |
|---|---|---|---|
| bipia_code | 0.0% [0.0%, 11.3%] (0/30) | 13.3% [5.3%, 29.7%] (4/30) | 13.3% [5.3%, 29.7%] (4/30) |
| bipia_email | 0.0% [0.0%, 11.3%] (0/30) | 0.0% [0.0%, 11.3%] (0/30) | 0.0% [0.0%, 11.3%] (0/30) |
| bipia_table | 0.0% [0.0%, 11.3%] (0/30) | 0.0% [0.0%, 11.3%] (0/30) | 0.0% [0.0%, 11.3%] (0/30) |
| deepset | 0.0% [0.0%, 11.3%] (0/30) | 0.0% [0.0%, 11.3%] (0/30) | 0.0% [0.0%, 11.3%] (0/30) |
| jackhhao | 0.0% [0.0%, 11.3%] (0/30) | 0.0% [0.0%, 11.3%] (0/30) | 0.0% [0.0%, 11.3%] (0/30) |

#### FPR document, theo `context_kind` (scope=l2_sample)

| context_kind | L1 | L2 | L1+L2 |
|---|---|---|---|
| code | 0.0% [0.0%, 11.3%] (0/30) | 13.3% [5.3%, 29.7%] (4/30) | 13.3% [5.3%, 29.7%] (4/30) |
| email | 0.0% [0.0%, 11.3%] (0/30) | 0.0% [0.0%, 11.3%] (0/30) | 0.0% [0.0%, 11.3%] (0/30) |
| none | 0.0% [0.0%, 6.0%] (0/60) | 0.0% [0.0%, 6.0%] (0/60) | 0.0% [0.0%, 6.0%] (0/60) |
| table | 0.0% [0.0%, 11.3%] (0/30) | 0.0% [0.0%, 11.3%] (0/30) | 0.0% [0.0%, 11.3%] (0/30) |

#### FPR document, theo `macro_over_subset` (scope=l2_sample)

| macro_over_subset | L1 | L2 | L1+L2 |
|---|---|---|---|
| mean | 0.0% (macro) | 2.7% (macro) | 2.7% (macro) |
