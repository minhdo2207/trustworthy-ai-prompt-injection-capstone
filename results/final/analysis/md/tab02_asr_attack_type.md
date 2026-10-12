**Bảng 2. ASR (%) theo loại tấn công và cấu hình**

| Split | Loại tấn công | Prompt | baseline | L1 | L1+L2 | L1+L2+L3 | L1+L2+L3+L4 | only_L1 | only_L2 | only_L3 | only_L4 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | code_switching_translation | 14 | 5.6 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 7.7 |
| all | direct_injection | 54 | 2.5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| all | indirect_injection | 49 | 40.0 | 9.6 | 3.2 | 0.0 | 0.0 | 12.2 | 18.6 | 14.0 | 20.9 |
| all | jailbreak_roleplay | 16 | 17.1 | 4.9 | 4.9 | 0.0 | 0.0 | 6.3 | 7.7 | 0.0 | 7.7 |
| all | many_shot_jailbreaking | 12 | 6.3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 8.3 | 0.0 |
| all | obfuscation | 14 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| train | code_switching_translation | 8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| train | direct_injection | 9 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| train | indirect_injection | 27 | 34.6 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 14.8 | 11.1 | 14.8 |
| train | jailbreak_roleplay | 9 | 18.5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| train | many_shot_jailbreaking | 8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| train | obfuscation | 8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| holdout | code_switching_translation | 5 | 20.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 20.0 |
| holdout | direct_injection | 5 | 20.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| holdout | indirect_injection | 16 | 53.1 | 31.3 | 12.5 | 0.0 | 0.0 | 31.3 | 25.0 | 18.8 | 31.3 |
| holdout | jailbreak_roleplay | 4 | 25.0 | 25.0 | 25.0 | 0.0 | 0.0 | 25.0 | 25.0 | 0.0 | 25.0 |
| holdout | many_shot_jailbreaking | 4 | 25.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 25.0 | 0.0 |
| holdout | obfuscation | 4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| test_indist | code_switching_translation | 1 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| test_indist | direct_injection | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| test_indist | indirect_injection | 6 | 41.7 | 16.7 | 0.0 | 0.0 | 0.0 | 16.7 | n/a | n/a | n/a |
| test_indist | jailbreak_roleplay | 3 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| test_indist | obfuscation | 2 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a |
| ext_attack | direct_injection | 38 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a | n/a | n/a | n/a |

`all` = gộp mọi split tấn công (chỉ để mô tả; số chính thức báo cáo theo split). Ô là ASR theo lượt; khoảng tin cậy nằm trong CSV. Nhóm có ít prompt cho khoảng rất rộng.
