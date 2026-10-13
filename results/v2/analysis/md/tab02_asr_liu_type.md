**Bảng 2. ASR (%) theo kiểu liu và cấu hình**

| Split | Kiểu Liu | Prompt | baseline | L1 | L1+L2 | L1+L2+L3 | L1+L2+L3+L4 | only_L1 | only_L2 | only_L3 | only_L4 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | combined | 5 | 71.4 | 28.6 | 28.6 | 0.0 | 0.0 | 20.0 | 50.0 | 0.0 | 0.0 |
| all | context_ignoring | 25 | 11.8 | 0.0 | 0.0 | 0.0 | 2.9 | 0.0 | 16.7 | 0.0 | 16.7 |
| all | escape_characters | 6 | 77.8 | 22.2 | 0.0 | 0.0 | 0.0 | 16.7 | 100.0 | 50.0 | 100.0 |
| all | fake_completion | 8 | 7.7 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| all | naive | 10 | 25.0 | 8.3 | 8.3 | 8.3 | 16.7 | 0.0 | 0.0 | 0.0 | 0.0 |
| all | none | 67 | 23.5 | 8.2 | 1.0 | 0.0 | 0.0 | 6.0 | 0.0 | 9.1 | 13.6 |
| train | combined | 3 | 33.3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| train | context_ignoring | 16 | 18.8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| train | escape_characters | 3 | 33.3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| train | fake_completion | 3 | 33.3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| train | naive | 8 | 25.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| train | none | 36 | 8.3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| holdout | combined | 2 | 100.0 | 50.0 | 50.0 | 0.0 | 0.0 | 50.0 | 50.0 | 0.0 | 0.0 |
| holdout | context_ignoring | 6 | 8.3 | 0.0 | 0.0 | 0.0 | 8.3 | 0.0 | 16.7 | 0.0 | 16.7 |
| holdout | escape_characters | 2 | 100.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 100.0 | 50.0 | 100.0 |
| holdout | fake_completion | 4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| holdout | naive | 2 | 25.0 | 25.0 | 25.0 | 25.0 | 50.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| holdout | none | 22 | 36.4 | 18.2 | 2.3 | 0.0 | 0.0 | 18.2 | 0.0 | 9.1 | 13.6 |
| test_indist | context_ignoring | 3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| test_indist | escape_characters | 1 | 100.0 | 100.0 | 0.0 | 0.0 | 0.0 | 100.0 | n/a | n/a | n/a |
| test_indist | fake_completion | 1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| test_indist | none | 9 | 22.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |

`all` = gộp mọi split tấn công (chỉ để mô tả; số chính thức báo cáo theo split). Ô là ASR theo lượt; khoảng tin cậy nằm trong CSV. Nhóm có ít prompt cho khoảng rất rộng.
