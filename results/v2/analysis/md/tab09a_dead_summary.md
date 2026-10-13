**Bảng 9a. Prompt 'chết' (baseline không bao giờ bị chiếm) theo loại**

| Split | Chiều | Giá trị | Prompt | Chết | Tỉ lệ chết (%) |
| --- | --- | --- | ---: | ---: | ---: |
| all | tổng | tất cả | 121 | 92 | 76.0 |
| all | attack_type | code_switching_translation | 14 | 13 | 92.9 |
| all | attack_type | direct_injection | 16 | 15 | 93.8 |
| all | attack_type | indirect_injection | 49 | 25 | 51.0 |
| all | attack_type | jailbreak_roleplay | 16 | 14 | 87.5 |
| all | attack_type | many_shot_jailbreaking | 12 | 11 | 91.7 |
| all | attack_type | obfuscation | 14 | 14 | 100.0 |
| all | liu_type | combined | 5 | 2 | 40.0 |
| all | liu_type | context_ignoring | 25 | 21 | 84.0 |
| all | liu_type | escape_characters | 6 | 2 | 33.3 |
| all | liu_type | fake_completion | 8 | 7 | 87.5 |
| all | liu_type | naive | 10 | 7 | 70.0 |
| all | liu_type | none | 67 | 53 | 79.1 |
| all | goal_type | integrity | 16 | 5 | 31.3 |
| all | goal_type | leak | 93 | 83 | 89.2 |
| all | goal_type | tool_action | 12 | 4 | 33.3 |
| train | tổng | tất cả | 69 | 58 | 84.1 |
| train | attack_type | code_switching_translation | 8 | 8 | 100.0 |
| train | attack_type | direct_injection | 9 | 9 | 100.0 |
| train | attack_type | indirect_injection | 27 | 17 | 63.0 |
| train | attack_type | jailbreak_roleplay | 9 | 8 | 88.9 |
| train | attack_type | many_shot_jailbreaking | 8 | 8 | 100.0 |
| train | attack_type | obfuscation | 8 | 8 | 100.0 |
| train | liu_type | combined | 3 | 2 | 66.7 |
| train | liu_type | context_ignoring | 16 | 13 | 81.3 |
| train | liu_type | escape_characters | 3 | 2 | 66.7 |
| train | liu_type | fake_completion | 3 | 2 | 66.7 |
| train | liu_type | naive | 8 | 6 | 75.0 |
| train | liu_type | none | 36 | 33 | 91.7 |
| train | goal_type | integrity | 6 | 2 | 33.3 |
| train | goal_type | leak | 57 | 52 | 91.2 |
| train | goal_type | tool_action | 6 | 4 | 66.7 |
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
| test_indist | tổng | tất cả | 14 | 10 | 71.4 |
| test_indist | attack_type | code_switching_translation | 1 | 1 | 100.0 |
| test_indist | attack_type | direct_injection | 2 | 2 | 100.0 |
| test_indist | attack_type | indirect_injection | 6 | 2 | 33.3 |
| test_indist | attack_type | jailbreak_roleplay | 3 | 3 | 100.0 |
| test_indist | attack_type | obfuscation | 2 | 2 | 100.0 |
| test_indist | liu_type | context_ignoring | 3 | 3 | 100.0 |
| test_indist | liu_type | escape_characters | 1 | 0 | 0.0 |
| test_indist | liu_type | fake_completion | 1 | 1 | 100.0 |
| test_indist | liu_type | none | 9 | 6 | 66.7 |
| test_indist | goal_type | integrity | 1 | 0 | 0.0 |
| test_indist | goal_type | leak | 11 | 10 | 90.9 |
| test_indist | goal_type | tool_action | 2 | 0 | 0.0 |

Prompt chết = ASR baseline = 0 trên *mọi* lượt. Số lượt baseline mỗi prompt tối thiểu 1: nếu nhỏ, 'chết' có thể chỉ là chưa đủ mẫu (xác suất bỏ lỡ prompt có ASR thật p là (1-p)^lượt).
