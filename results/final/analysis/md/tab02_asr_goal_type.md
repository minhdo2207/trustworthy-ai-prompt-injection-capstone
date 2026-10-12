**Bảng 2. ASR (%) theo mục tiêu và cấu hình**

| Split | Mục tiêu | Prompt | baseline | L1 | L1+L2 | L1+L2+L3 | L1+L2+L3+L4 | only_L1 | only_L2 | only_L3 | only_L4 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | integrity | 16 | 60.5 | 10.5 | 10.5 | 0.0 | 0.0 | 12.5 | 40.0 | 46.7 | 40.0 |
| all | leak | 131 | 8.5 | 2.1 | 0.7 | 0.0 | 0.0 | 3.2 | 3.7 | 0.0 | 4.9 |
| all | tool_action | 12 | 53.3 | 13.3 | 0.0 | 0.0 | 0.0 | 16.7 | 0.0 | 0.0 | 10.0 |
| train | integrity | 6 | 61.1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 50.0 | 50.0 | 50.0 |
| train | leak | 57 | 8.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.8 | 0.0 | 1.8 |
| train | tool_action | 6 | 44.4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| holdout | integrity | 9 | 55.6 | 22.2 | 22.2 | 0.0 | 0.0 | 22.2 | 33.3 | 44.4 | 33.3 |
| holdout | leak | 25 | 14.0 | 8.0 | 4.0 | 0.0 | 0.0 | 8.0 | 8.0 | 0.0 | 12.0 |
| holdout | tool_action | 4 | 100.0 | 50.0 | 0.0 | 0.0 | 0.0 | 50.0 | 0.0 | 0.0 | 25.0 |
| test_indist | integrity | 1 | 100.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| test_indist | leak | 11 | 13.6 | 9.1 | 0.0 | 0.0 | 0.0 | 9.1 | n/a | n/a | n/a |
| test_indist | tool_action | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| ext_attack | leak | 38 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a | n/a |

`all` = gộp mọi split tấn công (chỉ để mô tả; số chính thức báo cáo theo split). Ô là ASR theo lượt; khoảng tin cậy nằm trong CSV. Nhóm có ít prompt cho khoảng rất rộng.
