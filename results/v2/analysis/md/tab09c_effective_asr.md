**Bảng 9c. ASR hiệu dụng (chỉ trên prompt mà baseline bị chiếm)**

| Split | Config | Prompt sống/chết | ASR hiệu dụng theo lượt (%) | Wilson 95% | ASR hiệu dụng theo prompt (%) | Bootstrap 95% | ASR không điều kiện (%) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | baseline | 11/58 | 100.0 | [74.1, 100.0] | 100.0 | [100.0, 100.0] | 15.9 |
| train | L1 | 11/58 | 0.0 | [0.0, 25.9] | 0.0 | [0.0, 0.0] | 0.0 |
| train | L1+L2 | 11/58 | 0.0 | [0.0, 25.9] | 0.0 | [0.0, 0.0] | 0.0 |
| train | L1+L2+L3 | 11/58 | 0.0 | [0.0, 25.9] | 0.0 | [0.0, 0.0] | 0.0 |
| train | L1+L2+L3+L4 | 11/58 | 0.0 | [0.0, 25.9] | 0.0 | [0.0, 0.0] | 0.0 |
| train | only_L1 | 11/58 | 0.0 | [0.0, 25.9] | 0.0 | [0.0, 0.0] | 0.0 |
| holdout | baseline | 14/24 | 92.9 | [77.4, 98.0] | 92.9 | [82.1, 100.0] | 34.2 |
| holdout | L1 | 14/24 | 39.3 | [23.6, 57.6] | 39.3 | [14.3, 64.3] | 14.5 |
| holdout | L1+L2 | 14/24 | 14.3 | [5.7, 31.5] | 14.3 | [0.0, 32.1] | 5.3 |
| holdout | L1+L2+L3 | 14/24 | 3.6 | [0.6, 17.7] | 3.6 | [0.0, 10.7] | 1.3 |
| holdout | L1+L2+L3+L4 | 14/24 | 10.7 | [3.7, 27.2] | 10.7 | [0.0, 28.6] | 3.9 |
| holdout | only_L1 | 14/24 | 35.7 | [16.3, 61.2] | 35.7 | [14.3, 64.3] | 13.2 |
| holdout | only_L2 | 14/24 | 28.6 | [11.7, 54.6] | 28.6 | [7.1, 57.1] | 10.5 |
| holdout | only_L3 | 14/24 | 21.4 | [7.6, 47.6] | 21.4 | [0.0, 42.9] | 7.9 |
| holdout | only_L4 | 14/24 | 42.9 | [21.4, 67.4] | 42.9 | [21.4, 64.3] | 15.8 |
| test_indist | baseline | 4/10 | 75.0 | [40.9, 92.9] | 75.0 | [50.0, 100.0] | 21.4 |
| test_indist | L1 | 4/10 | 25.0 | [7.1, 59.1] | 25.0 | [0.0, 75.0] | 7.1 |
| test_indist | L1+L2 | 4/10 | 0.0 | [0.0, 32.4] | 0.0 | [0.0, 0.0] | 0.0 |
| test_indist | L1+L2+L3 | 4/10 | 0.0 | [0.0, 32.4] | 0.0 | [0.0, 0.0] | 0.0 |
| test_indist | L1+L2+L3+L4 | 4/10 | 0.0 | [0.0, 32.4] | 0.0 | [0.0, 0.0] | 0.0 |
| test_indist | only_L1 | 4/10 | 25.0 | [4.6, 69.9] | 25.0 | [0.0, 75.0] | 7.1 |

ASR có điều kiện: chỉ tính các prompt có ASR baseline > 0. Lưu ý chọn lọc: dòng `baseline` bị thổi lên vì chính điều kiện lọc (prompt được chọn vì đã thành công ở baseline); các config khác dùng lượt lấy mẫu khác nên ít bị thiên lệch hơn nhưng vẫn có hồi quy về trung bình. Dùng để so sánh phòng thủ trên phần tấn công thật sự có hiệu lực.
