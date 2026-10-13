**Bảng 5b. Benign theo cờ `tune`**

| tune | Config | Prompt | Từ chối oan (%) | Bootstrap 95% | Utility |
| --- | --- | ---: | ---: | ---: | ---: |
| false | baseline | 42 | 0.0 | [0.0, 0.0] | 0.933 |
| false | L1 | 42 | 2.4 | [0.0, 7.1] | 0.909 |
| false | L1+L2 | 42 | 4.8 | [0.0, 11.9] | 0.893 |
| false | L1+L2+L3 | 42 | 4.8 | [0.0, 11.9] | 0.877 |
| false | L1+L2+L3+L4 | 42 | 14.3 | [4.8, 26.2] | 0.778 |
| false | only_L1 | 42 | 2.4 | [0.0, 7.1] | 0.909 |

Phần `tune:true` đã được dùng để chỉnh ngưỡng/từ khoá nên *lạc quan*; chỉ `tune:false` là số báo cáo.
