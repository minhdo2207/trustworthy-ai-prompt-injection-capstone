**Bảng 9c. ASR hiệu dụng (chỉ trên prompt mà baseline bị chiếm)**

| Split | Config | Prompt sống/chết | ASR hiệu dụng theo lượt (%) | Wilson 95% | ASR hiệu dụng theo prompt (%) | Bootstrap 95% | ASR không điều kiện (%) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | baseline | 15/54 | 73.3 | [59.0, 84.0] | 73.3 | [60.0, 86.7] | 15.9 |
| train | L1 | 15/54 | 0.0 | [0.0, 7.9] | 0.0 | [0.0, 0.0] | 0.0 |
| train | L1+L2 | 15/54 | 0.0 | [0.0, 7.9] | 0.0 | [0.0, 0.0] | 0.0 |
| train | L1+L2+L3 | 15/54 | 0.0 | [0.0, 7.9] | 0.0 | [0.0, 0.0] | 0.0 |
| train | L1+L2+L3+L4 | 15/54 | 0.0 | [0.0, 7.9] | 0.0 | [0.0, 0.0] | 0.0 |
| train | only_L1 | 15/54 | 0.0 | [0.0, 20.4] | 0.0 | [0.0, 0.0] | 0.0 |
| train | only_L2 | 15/54 | 26.7 | [10.9, 52.0] | 26.7 | [6.7, 46.7] | 5.8 |
| train | only_L3 | 15/54 | 13.3 | [3.7, 37.9] | 13.3 | [0.0, 33.3] | 4.3 |
| train | only_L4 | 15/54 | 26.7 | [10.9, 52.0] | 26.7 | [6.7, 53.3] | 5.8 |
| holdout | baseline | 14/24 | 89.3 | [72.8, 96.3] | 89.3 | [78.6, 100.0] | 32.9 |
| holdout | L1 | 14/24 | 42.9 | [26.5, 60.9] | 42.9 | [21.4, 64.3] | 15.8 |
| holdout | L1+L2 | 14/24 | 21.4 | [10.2, 39.5] | 21.4 | [3.6, 42.9] | 7.9 |
| holdout | L1+L2+L3 | 14/24 | 0.0 | [0.0, 12.1] | 0.0 | [0.0, 0.0] | 0.0 |
| holdout | L1+L2+L3+L4 | 14/24 | 0.0 | [0.0, 12.1] | 0.0 | [0.0, 0.0] | 0.0 |
| holdout | only_L1 | 14/24 | 42.9 | [21.4, 67.4] | 42.9 | [14.3, 71.4] | 15.8 |
| holdout | only_L2 | 14/24 | 35.7 | [16.3, 61.2] | 35.7 | [14.3, 64.3] | 13.2 |
| holdout | only_L3 | 14/24 | 28.6 | [11.7, 54.6] | 28.6 | [7.1, 50.0] | 10.5 |
| holdout | only_L4 | 14/24 | 50.0 | [26.8, 73.2] | 50.0 | [21.4, 78.6] | 18.4 |
| test_indist | baseline | 3/11 | 83.3 | [43.6, 97.0] | 83.3 | [50.0, 100.0] | 17.9 |
| test_indist | L1 | 3/11 | 33.3 | [9.7, 70.0] | 33.3 | [0.0, 100.0] | 7.1 |
| test_indist | L1+L2 | 3/11 | 0.0 | [0.0, 39.0] | 0.0 | [0.0, 0.0] | 0.0 |
| test_indist | L1+L2+L3 | 3/11 | 0.0 | [0.0, 39.0] | 0.0 | [0.0, 0.0] | 0.0 |
| test_indist | L1+L2+L3+L4 | 3/11 | 0.0 | [0.0, 39.0] | 0.0 | [0.0, 0.0] | 0.0 |
| test_indist | only_L1 | 3/11 | 33.3 | [6.1, 79.2] | 33.3 | [0.0, 100.0] | 7.1 |

ASR có điều kiện: chỉ tính các prompt có ASR baseline > 0. Lưu ý chọn lọc: dòng `baseline` bị thổi lên vì chính điều kiện lọc (prompt được chọn vì đã thành công ở baseline); các config khác dùng lượt lấy mẫu khác nên ít bị thiên lệch hơn nhưng vẫn có hồi quy về trung bình. Dùng để so sánh phòng thủ trên phần tấn công thật sự có hiệu lực.
