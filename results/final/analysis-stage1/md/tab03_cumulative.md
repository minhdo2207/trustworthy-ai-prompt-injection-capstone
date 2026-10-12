**Bảng 3. Phòng thủ cộng dồn: baseline -> +L1 -> +L1+L2 -> ...**

| Split | Config | Lớp thêm | Prompt | ASR lượt (%) | Wilson 95% | ASR prompt (%) | Bootstrap 95% | Giảm vs bước trước (pp) | Giảm tương đối vs bước trước (%) | Giảm vs baseline (pp) | Giảm tương đối vs baseline (%) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | baseline |  | 69 | 15.9 | [11.6, 21.5] | 15.9 | [8.7, 23.7] | - | n/a | - | n/a |
| train | L1 | L1 | 69 | 0.0 | [0.0, 1.8] | 0.0 | [0.0, 0.0] | +15.9 [+8.7, +23.7] | 100.0 | +15.9 [+8.7, +23.7] | 100.0 |
| train | L1+L2 | L2 | 69 | 0.0 | [0.0, 1.8] | 0.0 | [0.0, 0.0] | 0.0 [0.0, 0.0] | n/a | +15.9 [+8.7, +23.7] | 100.0 |
| train | L1+L2+L3 | L3 | 69 | 0.0 | [0.0, 1.8] | 0.0 | [0.0, 0.0] | 0.0 [0.0, 0.0] | n/a | +15.9 [+8.7, +23.7] | 100.0 |
| train | L1+L2+L3+L4 | L4 | 69 | 0.0 | [0.0, 1.8] | 0.0 | [0.0, 0.0] | 0.0 [0.0, 0.0] | n/a | +15.9 [+8.7, +23.7] | 100.0 |

Giảm = ASR trước trừ ASR sau, tính theo prompt, điểm phần trăm (pp); dương là tốt. Khoảng trong ngoặc là bootstrap xếp cặp theo prompt (cùng tập prompt giữa hai cấu hình). Giảm tương đối = giảm tuyệt đối / ASR của bước đối chiếu.
