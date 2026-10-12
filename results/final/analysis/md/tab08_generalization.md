**Bảng 8. Khoảng cách tổng quát hoá giữa các split**

| Config | Từ -> sang | Prompt (từ/sang) | ASR từ (%) | ASR sang (%) | Chênh lệch (pp) | Bootstrap 95% (pp) | Loại 0? |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| baseline | train -> holdout | 69/38 | 15.9 | 32.9 | +17.0 | [+0.8, +33.6] | có |
| baseline | train -> test_indist | 69/14 | 15.9 | 17.9 | +1.9 | [-15.5, +24.3] | không |
| baseline | test_indist -> holdout | 14/38 | 17.9 | 32.9 | +15.0 | [-9.4, +36.7] | không |
| L1 | train -> holdout | 69/38 | 0.0 | 15.8 | +15.8 | [+6.6, +27.6] | có |
| L1 | train -> test_indist | 69/14 | 0.0 | 7.1 | +7.1 | [0.0, +21.4] | không |
| L1 | test_indist -> holdout | 14/38 | 7.1 | 15.8 | +8.6 | [-9.6, +24.5] | không |
| L1+L2 | train -> holdout | 69/38 | 0.0 | 7.9 | +7.9 | [+1.3, +17.1] | có |
| L1+L2 | train -> test_indist | 69/14 | 0.0 | 0.0 | 0.0 | [0.0, 0.0] | không |
| L1+L2 | test_indist -> holdout | 14/38 | 0.0 | 7.9 | +7.9 | [+1.3, +17.1] | có |
| L1+L2+L3 | train -> holdout | 69/38 | 0.0 | 0.0 | 0.0 | [0.0, 0.0] | không |
| L1+L2+L3 | train -> test_indist | 69/14 | 0.0 | 0.0 | 0.0 | [0.0, 0.0] | không |
| L1+L2+L3 | test_indist -> holdout | 14/38 | 0.0 | 0.0 | 0.0 | [0.0, 0.0] | không |
| L1+L2+L3+L4 | train -> holdout | 69/38 | 0.0 | 0.0 | 0.0 | [0.0, 0.0] | không |
| L1+L2+L3+L4 | train -> test_indist | 69/14 | 0.0 | 0.0 | 0.0 | [0.0, 0.0] | không |
| L1+L2+L3+L4 | test_indist -> holdout | 14/38 | 0.0 | 0.0 | 0.0 | [0.0, 0.0] | không |
| only_L1 | train -> holdout | 69/38 | 0.0 | 15.8 | +15.8 | [+5.3, +28.9] | có |
| only_L1 | train -> test_indist | 69/14 | 0.0 | 7.1 | +7.1 | [0.0, +21.4] | không |
| only_L1 | test_indist -> holdout | 14/38 | 7.1 | 15.8 | +8.6 | [-10.9, +26.3] | không |
| only_L2 | train -> holdout | 69/38 | 5.8 | 13.2 | +7.4 | [-3.4, +20.3] | không |
| only_L3 | train -> holdout | 69/38 | 4.3 | 10.5 | +6.2 | [-4.6, +17.0] | không |
| only_L4 | train -> holdout | 69/38 | 5.8 | 18.4 | +12.6 | [-0.5, +27.0] | không |

Chênh lệch = ASR(split sang) - ASR(split từ) tính theo prompt; dương nghĩa là phòng thủ kém hơn trên split sang (dấu hiệu quá khớp với train). Hai split là hai tập prompt khác nhau nên dùng bootstrap độc lập, không xếp cặp.
