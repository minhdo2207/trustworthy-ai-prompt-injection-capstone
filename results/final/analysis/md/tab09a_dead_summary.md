**Bảng 9a. Prompt 'chết' (baseline không bao giờ bị chiếm) theo loại**

| Split | Chiều | Giá trị | Prompt | Chết | Tỉ lệ chết (%) |
| --- | --- | --- | ---: | ---: | ---: |
| all | tổng | tất cả | 159 | 127 | 79.9 |
| all | attack_type | code_switching_translation | 14 | 13 | 92.9 |
| all | attack_type | direct_injection | 54 | 53 | 98.1 |
| all | attack_type | indirect_injection | 49 | 23 | 46.9 |
| all | attack_type | jailbreak_roleplay | 16 | 13 | 81.3 |
| all | attack_type | many_shot_jailbreaking | 12 | 11 | 91.7 |
| all | attack_type | obfuscation | 14 | 14 | 100.0 |
| all | liu_type | combined | 5 | 1 | 20.0 |
| all | liu_type | context_ignoring | 47 | 42 | 89.4 |
| all | liu_type | escape_characters | 6 | 1 | 16.7 |
| all | liu_type | fake_completion | 8 | 8 | 100.0 |
| all | liu_type | naive | 10 | 7 | 70.0 |
| all | liu_type | none | 83 | 68 | 81.9 |
| all | goal_type | integrity | 16 | 4 | 25.0 |
| all | goal_type | leak | 131 | 119 | 90.8 |
| all | goal_type | tool_action | 12 | 4 | 33.3 |
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
| holdout | tổng | tất cả | 38 | 24 | 63.2 |
| holdout | attack_type | code_switching_translation | 5 | 4 | 80.0 |
| holdout | attack_type | direct_injection | 5 | 4 | 80.0 |
| holdout | attack_type | indirect_injection | 16 | 6 | 37.5 |
| holdout | attack_type | jailbreak_roleplay | 4 | 3 | 75.0 |
| holdout | attack_type | many_shot_jailbreaking | 4 | 3 | 75.0 |
| holdout | attack_type | obfuscation | 4 | 4 | 100.0 |
| holdout | liu_type | combined | 2 | 0 | 0.0 |
| holdout | liu_type | context_ignoring | 6 | 5 | 83.3 |
| holdout | liu_type | escape_characters | 2 | 0 | 0.0 |
| holdout | liu_type | fake_completion | 4 | 4 | 100.0 |
| holdout | liu_type | naive | 2 | 1 | 50.0 |
| holdout | liu_type | none | 22 | 14 | 63.6 |
| holdout | goal_type | integrity | 9 | 3 | 33.3 |
| holdout | goal_type | leak | 25 | 21 | 84.0 |
| holdout | goal_type | tool_action | 4 | 0 | 0.0 |
| test_indist | tổng | tất cả | 14 | 11 | 78.6 |
| test_indist | attack_type | code_switching_translation | 1 | 1 | 100.0 |
| test_indist | attack_type | direct_injection | 2 | 2 | 100.0 |
| test_indist | attack_type | indirect_injection | 6 | 3 | 50.0 |
| test_indist | attack_type | jailbreak_roleplay | 3 | 3 | 100.0 |
| test_indist | attack_type | obfuscation | 2 | 2 | 100.0 |
| test_indist | liu_type | context_ignoring | 3 | 2 | 66.7 |
| test_indist | liu_type | escape_characters | 1 | 0 | 0.0 |
| test_indist | liu_type | fake_completion | 1 | 1 | 100.0 |
| test_indist | liu_type | none | 9 | 8 | 88.9 |
| test_indist | goal_type | integrity | 1 | 0 | 0.0 |
| test_indist | goal_type | leak | 11 | 9 | 81.8 |
| test_indist | goal_type | tool_action | 2 | 2 | 100.0 |
| ext_attack | tổng | tất cả | 38 | 38 | 100.0 |
| ext_attack | attack_type | direct_injection | 38 | 38 | 100.0 |
| ext_attack | liu_type | context_ignoring | 22 | 22 | 100.0 |
| ext_attack | liu_type | none | 16 | 16 | 100.0 |
| ext_attack | goal_type | leak | 38 | 38 | 100.0 |

Prompt chết = ASR baseline = 0 trên *mọi* lượt. Số lượt baseline mỗi prompt tối thiểu 1: nếu nhỏ, 'chết' có thể chỉ là chưa đủ mẫu (xác suất bỏ lỡ prompt có ASR thật p là (1-p)^lượt).
