**Bảng 1. ASR theo cấu hình và split**

| Split | Config | Lượt | Prompt | Thành công | ASR lượt (%) | Wilson 95% (lạc quan) | ASR theo prompt (%) | Bootstrap theo prompt 95% |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | baseline | 207 | 69 | 33 | 15.9 | [11.6, 21.5] | 15.9 | [8.7, 23.7] |
| train | L1 | 207 | 69 | 0 | 0.0 | [0.0, 1.8] | 0.0 | [0.0, 0.0] |
| train | L1+L2 | 207 | 69 | 0 | 0.0 | [0.0, 1.8] | 0.0 | [0.0, 0.0] |
| train | L1+L2+L3 | 207 | 69 | 0 | 0.0 | [0.0, 1.8] | 0.0 | [0.0, 0.0] |
| train | L1+L2+L3+L4 | 207 | 69 | 0 | 0.0 | [0.0, 1.8] | 0.0 | [0.0, 0.0] |
| train | only_L1 | 69 | 69 | 0 | 0.0 | [0.0, 5.3] | 0.0 | [0.0, 0.0] |
| train | only_L2 | 69 | 69 | 4 | 5.8 | [2.3, 14.0] | 5.8 | [1.4, 11.6] |
| train | only_L3 | 69 | 69 | 3 | 4.3 | [1.5, 12.0] | 4.3 | [0.0, 10.1] |
| train | only_L4 | 69 | 69 | 4 | 5.8 | [2.3, 14.0] | 5.8 | [1.4, 11.6] |

Wilson coi mọi lượt là độc lập nên *lạc quan* (hẹp) vì các lượt của cùng prompt tương quan; khoảng bootstrap theo prompt là khoảng nên trích dẫn.
