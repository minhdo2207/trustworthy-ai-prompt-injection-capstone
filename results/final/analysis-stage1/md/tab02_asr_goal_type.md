**Bảng 2. ASR (%) theo mục tiêu và cấu hình**

| Split | Mục tiêu | Prompt | baseline | L1 | L1+L2 | L1+L2+L3 | L1+L2+L3+L4 | only_L1 | only_L2 | only_L3 | only_L4 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | integrity | 6 | 61.1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 50.0 | 50.0 | 50.0 |
| all | leak | 57 | 8.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.8 | 0.0 | 1.8 |
| all | tool_action | 6 | 44.4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| train | integrity | 6 | 61.1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 50.0 | 50.0 | 50.0 |
| train | leak | 57 | 8.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 1.8 | 0.0 | 1.8 |
| train | tool_action | 6 | 44.4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

`all` = gộp mọi split tấn công (chỉ để mô tả; số chính thức báo cáo theo split). Ô là ASR theo lượt; khoảng tin cậy nằm trong CSV. Nhóm có ít prompt cho khoảng rất rộng.
