**Bảng 9a. Prompt 'chết' (baseline không bao giờ bị chiếm) theo loại**

| Split | Chiều | Giá trị | Prompt | Chết | Tỉ lệ chết (%) |
| --- | --- | --- | ---: | ---: | ---: |
| all | tổng | tất cả | 69 | 54 | 78.3 |
| all | attack_type | code_switching_translation | 8 | 8 | 100.0 |
| all | attack_type | direct_injection | 9 | 9 | 100.0 |
| all | attack_type | indirect_injection | 27 | 14 | 51.9 |
| all | attack_type | jailbreak_roleplay | 9 | 7 | 77.8 |
| all | attack_type | many_shot_jailbreaking | 8 | 8 | 100.0 |
| all | attack_type | obfuscation | 8 | 8 | 100.0 |
| all | liu_type | combined | 3 | 1 | 33.3 |
| all | liu_type | context_ignoring | 16 | 13 | 81.3 |
| all | liu_type | escape_characters | 3 | 1 | 33.3 |
| all | liu_type | fake_completion | 3 | 3 | 100.0 |
| all | liu_type | naive | 8 | 6 | 75.0 |
| all | liu_type | none | 36 | 30 | 83.3 |
| all | goal_type | integrity | 6 | 1 | 16.7 |
| all | goal_type | leak | 57 | 51 | 89.5 |
| all | goal_type | tool_action | 6 | 2 | 33.3 |
| train | tổng | tất cả | 69 | 54 | 78.3 |
| train | attack_type | code_switching_translation | 8 | 8 | 100.0 |
| train | attack_type | direct_injection | 9 | 9 | 100.0 |
| train | attack_type | indirect_injection | 27 | 14 | 51.9 |
| train | attack_type | jailbreak_roleplay | 9 | 7 | 77.8 |
| train | attack_type | many_shot_jailbreaking | 8 | 8 | 100.0 |
| train | attack_type | obfuscation | 8 | 8 | 100.0 |
| train | liu_type | combined | 3 | 1 | 33.3 |
| train | liu_type | context_ignoring | 16 | 13 | 81.3 |
| train | liu_type | escape_characters | 3 | 1 | 33.3 |
| train | liu_type | fake_completion | 3 | 3 | 100.0 |
| train | liu_type | naive | 8 | 6 | 75.0 |
| train | liu_type | none | 36 | 30 | 83.3 |
| train | goal_type | integrity | 6 | 1 | 16.7 |
| train | goal_type | leak | 57 | 51 | 89.5 |
| train | goal_type | tool_action | 6 | 2 | 33.3 |

Prompt chết = ASR baseline = 0 trên *mọi* lượt. Số lượt baseline mỗi prompt tối thiểu 3: nếu nhỏ, 'chết' có thể chỉ là chưa đủ mẫu (xác suất bỏ lỡ prompt có ASR thật p là (1-p)^lượt).
