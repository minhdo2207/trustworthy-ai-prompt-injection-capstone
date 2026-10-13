**Bảng 2. ASR (%) theo loại tấn công và cấu hình**

| Split | Loại tấn công | Prompt | baseline | L1 | L1+L2 | L1+L2+L3 | L1+L2+L3+L4 | only_L1 | only_L2 | only_L3 | only_L4 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | code_switching_translation | 14 | 10.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 20.0 |
| all | direct_injection | 16 | 8.7 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| all | indirect_injection | 49 | 47.9 | 15.5 | 4.2 | 1.4 | 4.2 | 10.2 | 25.0 | 12.5 | 25.0 |
| all | jailbreak_roleplay | 16 | 13.0 | 8.7 | 4.3 | 0.0 | 0.0 | 6.3 | 0.0 | 0.0 | 25.0 |
| all | many_shot_jailbreaking | 12 | 12.5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 25.0 | 0.0 |
| all | obfuscation | 14 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| train | code_switching_translation | 8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| train | direct_injection | 9 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| train | indirect_injection | 27 | 37.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| train | jailbreak_roleplay | 9 | 11.1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| train | many_shot_jailbreaking | 8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| train | obfuscation | 8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| holdout | code_switching_translation | 5 | 20.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 20.0 |
| holdout | direct_injection | 5 | 20.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| holdout | indirect_injection | 16 | 56.3 | 28.1 | 9.4 | 3.1 | 9.4 | 25.0 | 25.0 | 12.5 | 25.0 |
| holdout | jailbreak_roleplay | 4 | 25.0 | 25.0 | 12.5 | 0.0 | 0.0 | 25.0 | 0.0 | 0.0 | 25.0 |
| holdout | many_shot_jailbreaking | 4 | 25.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 25.0 | 0.0 |
| holdout | obfuscation | 4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| test_indist | code_switching_translation | 1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| test_indist | direct_injection | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| test_indist | indirect_injection | 6 | 50.0 | 16.7 | 0.0 | 0.0 | 0.0 | 16.7 | n/a | n/a | n/a |
| test_indist | jailbreak_roleplay | 3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| test_indist | obfuscation | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |

`all` = gộp mọi split tấn công (chỉ để mô tả; số chính thức báo cáo theo split). Ô là ASR theo lượt; khoảng tin cậy nằm trong CSV. Nhóm có ít prompt cho khoảng rất rộng.
