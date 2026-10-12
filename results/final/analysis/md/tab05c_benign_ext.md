**Bảng 5c. Benign ngoài (ext_benign): từ chối oan**

| Config | Lượt | Prompt | Từ chối oan (%) | Wilson 95% | Bootstrap 95% | Bị chặn (%) | Model từ chối (%) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 120 | 120 | 0.8 | [0.1, 4.6] | [0.0, 2.5] | 0.0 | 0.8 |
| L1 | 120 | 120 | 0.8 | [0.1, 4.6] | [0.0, 2.5] | 0.0 | 0.8 |
| L1+L2 | 120 | 120 | 2.5 | [0.9, 7.1] | [0.0, 5.0] | 1.7 | 0.8 |
| L1+L2+L3 | 120 | 120 | 2.5 | [0.9, 7.1] | [0.0, 5.0] | 1.7 | 0.8 |
| L1+L2+L3+L4 | 120 | 120 | 2.5 | [0.9, 7.1] | [0.0, 5.0] | 1.7 | 0.8 |

Tài liệu benign thật từ dataset công khai (BIPIA, deepset, jackhhao); zero-shot, không chỉnh tham số theo tập này. Không có `reference_keypoints` nên không có utility. Từ chối oan = bị chặn hoặc model tự từ chối.
