**Bảng 2. ASR (%) theo kiểu liu và cấu hình**

| Split | Kiểu Liu | Prompt | baseline | L1 | L1+L2 | L1+L2+L3 | L1+L2+L3+L4 | only_L1 | only_L2 | only_L3 | only_L4 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | combined | 3 | 55.6 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| all | context_ignoring | 16 | 16.7 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 6.3 | 6.3 | 6.3 |
| all | escape_characters | 3 | 22.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 33.3 | 33.3 | 33.3 |
| all | fake_completion | 3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 33.3 | 0.0 |
| all | naive | 8 | 20.8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 12.5 | 0.0 | 12.5 |
| all | none | 36 | 12.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 2.8 | 0.0 | 2.8 |
| train | combined | 3 | 55.6 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| train | context_ignoring | 16 | 16.7 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 6.3 | 6.3 | 6.3 |
| train | escape_characters | 3 | 22.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 33.3 | 33.3 | 33.3 |
| train | fake_completion | 3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 33.3 | 0.0 |
| train | naive | 8 | 20.8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 12.5 | 0.0 | 12.5 |
| train | none | 36 | 12.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 2.8 | 0.0 | 2.8 |

`all` = gộp mọi split tấn công (chỉ để mô tả; số chính thức báo cáo theo split). Ô là ASR theo lượt; khoảng tin cậy nằm trong CSV. Nhóm có ít prompt cho khoảng rất rộng.
