**Bảng 2. ASR (%) theo kiểu liu và cấu hình**

| Split | Kiểu Liu | Prompt | baseline | L1 | L1+L2 | L1+L2+L3 | L1+L2+L3+L4 | only_L1 | only_L2 | only_L3 | only_L4 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | combined | 5 | 61.5 | 7.7 | 15.4 | 0.0 | 0.0 | 0.0 | 20.0 | 20.0 | 20.0 |
| all | context_ignoring | 47 | 11.4 | 1.1 | 1.1 | 0.0 | 0.0 | 4.0 | 9.1 | 4.5 | 9.1 |
| all | escape_characters | 6 | 53.3 | 13.3 | 0.0 | 0.0 | 0.0 | 16.7 | 60.0 | 40.0 | 60.0 |
| all | fake_completion | 8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 14.3 | 0.0 |
| all | naive | 10 | 21.4 | 3.6 | 3.6 | 0.0 | 0.0 | 0.0 | 10.0 | 0.0 | 10.0 |
| all | none | 83 | 16.7 | 4.8 | 1.1 | 0.0 | 0.0 | 7.5 | 3.4 | 3.4 | 6.9 |
| train | combined | 3 | 55.6 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| train | context_ignoring | 16 | 16.7 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 6.3 | 6.3 | 6.3 |
| train | escape_characters | 3 | 22.2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 33.3 | 33.3 | 33.3 |
| train | fake_completion | 3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 33.3 | 0.0 |
| train | naive | 8 | 20.8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 12.5 | 0.0 | 12.5 |
| train | none | 36 | 12.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 2.8 | 0.0 | 2.8 |
| holdout | combined | 2 | 75.0 | 25.0 | 50.0 | 0.0 | 0.0 | 0.0 | 50.0 | 50.0 | 50.0 |
| holdout | context_ignoring | 6 | 8.3 | 8.3 | 8.3 | 0.0 | 0.0 | 16.7 | 16.7 | 0.0 | 16.7 |
| holdout | escape_characters | 2 | 100.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 100.0 | 50.0 | 100.0 |
| holdout | fake_completion | 4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| holdout | naive | 2 | 25.0 | 25.0 | 25.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| holdout | none | 22 | 36.4 | 20.5 | 4.5 | 0.0 | 0.0 | 22.7 | 4.5 | 9.1 | 13.6 |
| test_indist | context_ignoring | 3 | 16.7 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| test_indist | escape_characters | 1 | 100.0 | 100.0 | 0.0 | 0.0 | 0.0 | 100.0 | n/a | n/a | n/a |
| test_indist | fake_completion | 1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| test_indist | none | 9 | 11.1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| ext_attack | context_ignoring | 22 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a | n/a |
| ext_attack | none | 16 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a | n/a |

`all` = gộp mọi split tấn công (chỉ để mô tả; số chính thức báo cáo theo split). Ô là ASR theo lượt; khoảng tin cậy nằm trong CSV. Nhóm có ít prompt cho khoảng rất rộng.
