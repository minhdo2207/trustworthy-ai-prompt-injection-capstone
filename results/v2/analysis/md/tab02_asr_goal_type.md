**Bảng 2. ASR (%) theo mục tiêu và cấu hình**

| Split | Mục tiêu | Prompt | baseline | L1 | L1+L2 | L1+L2+L3 | L1+L2+L3+L4 | only_L1 | only_L2 | only_L3 | only_L4 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | integrity | 16 | 61.5 | 11.5 | 11.5 | 3.8 | 11.5 | 6.3 | 33.3 | 33.3 | 33.3 |
| all | leak | 93 | 11.6 | 4.7 | 0.8 | 0.0 | 0.0 | 3.2 | 4.0 | 0.0 | 8.0 |
| all | tool_action | 12 | 66.7 | 22.2 | 0.0 | 0.0 | 0.0 | 16.7 | 0.0 | 0.0 | 25.0 |
| train | integrity | 6 | 66.7 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| train | leak | 57 | 8.8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| train | tool_action | 6 | 33.3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| holdout | integrity | 9 | 55.6 | 16.7 | 16.7 | 5.6 | 16.7 | 11.1 | 33.3 | 33.3 | 33.3 |
| holdout | leak | 25 | 16.0 | 8.0 | 2.0 | 0.0 | 0.0 | 8.0 | 4.0 | 0.0 | 8.0 |
| holdout | tool_action | 4 | 100.0 | 50.0 | 0.0 | 0.0 | 0.0 | 50.0 | 0.0 | 0.0 | 25.0 |
| test_indist | integrity | 1 | 100.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| test_indist | leak | 11 | 9.1 | 9.1 | 0.0 | 0.0 | 0.0 | 9.1 | n/a | n/a | n/a |
| test_indist | tool_action | 2 | 50.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |

`all` = gộp mọi split tấn công (chỉ để mô tả; số chính thức báo cáo theo split). Ô là ASR theo lượt; khoảng tin cậy nằm trong CSV. Nhóm có ít prompt cho khoảng rất rộng.
