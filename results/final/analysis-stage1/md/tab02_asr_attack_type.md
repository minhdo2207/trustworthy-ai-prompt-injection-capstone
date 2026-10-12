**Bảng 2. ASR (%) theo loại tấn công và cấu hình**

| Split | Loại tấn công | Prompt | baseline | L1 | L1+L2 | L1+L2+L3 | L1+L2+L3+L4 | only_L1 | only_L2 | only_L3 | only_L4 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | code_switching_translation | 8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| all | direct_injection | 9 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| all | indirect_injection | 27 | 34.6 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 14.8 | 11.1 | 14.8 |
| all | jailbreak_roleplay | 9 | 18.5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| all | many_shot_jailbreaking | 8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| all | obfuscation | 8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| train | code_switching_translation | 8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| train | direct_injection | 9 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| train | indirect_injection | 27 | 34.6 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 14.8 | 11.1 | 14.8 |
| train | jailbreak_roleplay | 9 | 18.5 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| train | many_shot_jailbreaking | 8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| train | obfuscation | 8 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

`all` = gộp mọi split tấn công (chỉ để mô tả; số chính thức báo cáo theo split). Ô là ASR theo lượt; khoảng tin cậy nằm trong CSV. Nhóm có ít prompt cho khoảng rất rộng.
