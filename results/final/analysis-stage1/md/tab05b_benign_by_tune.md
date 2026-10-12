**Bảng 5b. Benign theo cờ `tune`**

| tune | Config | Prompt | Từ chối oan (%) | Bootstrap 95% | Utility |
| --- | --- | ---: | ---: | ---: | ---: |
| false | baseline | 42 | 0.0 | [0.0, 0.0] | 0.931 |
| false | L1 | 42 | 2.4 | [0.0, 7.1] | 0.914 |
| false | L1+L2 | 42 | 4.8 | [0.0, 11.9] | 0.901 |
| false | L1+L2+L3 | 42 | 4.8 | [0.0, 11.9] | 0.864 |
| false | L1+L2+L3+L4 | 42 | 15.9 | [7.1, 26.2] | 0.737 |
| false | only_L1 | 42 | 2.4 | [0.0, 7.1] | 0.917 |
| false | only_L2 | 42 | 2.4 | [0.0, 7.1] | 0.909 |
| false | only_L3 | 42 | 0.0 | [0.0, 0.0] | 0.897 |
| false | only_L4 | 42 | 7.1 | [0.0, 16.7] | 0.877 |
| true | baseline | 42 | 0.0 | [0.0, 0.0] | 0.884 |
| true | L1 | 42 | 0.0 | [0.0, 0.0] | 0.883 |
| true | L1+L2 | 42 | 0.0 | [0.0, 0.0] | 0.886 |
| true | L1+L2+L3 | 42 | 0.0 | [0.0, 0.0] | 0.864 |
| true | L1+L2+L3+L4 | 42 | 10.3 | [3.2, 19.0] | 0.776 |
| true | only_L1 | 42 | 0.0 | [0.0, 0.0] | 0.873 |
| true | only_L2 | 42 | 0.0 | [0.0, 0.0] | 0.873 |
| true | only_L3 | 42 | 0.0 | [0.0, 0.0] | 0.891 |
| true | only_L4 | 42 | 4.8 | [0.0, 11.9] | 0.819 |

Phần `tune:true` đã được dùng để chỉnh ngưỡng/từ khoá nên *lạc quan*; chỉ `tune:false` là số báo cáo.
