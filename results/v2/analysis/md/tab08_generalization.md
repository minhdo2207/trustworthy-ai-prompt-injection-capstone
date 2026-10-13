**Bảng 8. Khoảng cách tổng quát hoá giữa các split**

| Config | Từ -> sang | Prompt (từ/sang) | ASR từ (%) | ASR sang (%) | Chênh lệch (pp) | Bootstrap 95% (pp) | Loại 0? |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| baseline | train -> holdout | 69/38 | 15.9 | 34.2 | +18.3 | [+2.1, +35.4] | có |
| baseline | train -> test_indist | 69/14 | 15.9 | 21.4 | +5.5 | [-13.1, +28.4] | không |
| baseline | test_indist -> holdout | 14/38 | 21.4 | 34.2 | +12.8 | [-11.1, +35.5] | không |
| L1 | train -> holdout | 69/38 | 0.0 | 14.5 | +14.5 | [+5.3, +26.3] | có |
| L1 | train -> test_indist | 69/14 | 0.0 | 7.1 | +7.1 | [0.0, +21.4] | không |
| L1 | test_indist -> holdout | 14/38 | 7.1 | 14.5 | +7.3 | [-10.9, +23.7] | không |
| L1+L2 | train -> holdout | 69/38 | 0.0 | 5.3 | +5.3 | [0.0, +11.8] | không |
| L1+L2 | train -> test_indist | 69/14 | 0.0 | 0.0 | 0.0 | [0.0, 0.0] | không |
| L1+L2 | test_indist -> holdout | 14/38 | 0.0 | 5.3 | +5.3 | [0.0, +11.8] | không |
| L1+L2+L3 | train -> holdout | 69/38 | 0.0 | 1.3 | +1.3 | [0.0, +3.9] | không |
| L1+L2+L3 | train -> test_indist | 69/14 | 0.0 | 0.0 | 0.0 | [0.0, 0.0] | không |
| L1+L2+L3 | test_indist -> holdout | 14/38 | 0.0 | 1.3 | +1.3 | [0.0, +3.9] | không |
| L1+L2+L3+L4 | train -> holdout | 69/38 | 0.0 | 3.9 | +3.9 | [0.0, +10.5] | không |
| L1+L2+L3+L4 | train -> test_indist | 69/14 | 0.0 | 0.0 | 0.0 | [0.0, 0.0] | không |
| L1+L2+L3+L4 | test_indist -> holdout | 14/38 | 0.0 | 3.9 | +3.9 | [0.0, +10.5] | không |
| only_L1 | train -> holdout | 69/38 | 0.0 | 13.2 | +13.2 | [+2.6, +26.3] | có |
| only_L1 | train -> test_indist | 69/14 | 0.0 | 7.1 | +7.1 | [0.0, +21.4] | không |
| only_L1 | test_indist -> holdout | 14/38 | 7.1 | 13.2 | +6.0 | [-11.7, +21.8] | không |

Chênh lệch = ASR(split sang) - ASR(split từ) tính theo prompt; dương nghĩa là phòng thủ kém hơn trên split sang (dấu hiệu quá khớp với train). Hai split là hai tập prompt khác nhau nên dùng bootstrap độc lập, không xếp cặp.
