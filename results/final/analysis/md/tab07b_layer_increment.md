**Bảng 7b. Đóng góp tăng thêm của từng lớp trong chuỗi**

| Split | Lớp thêm | Config | Chặn thêm tấn công (pp) | Giảm ASR (pp) | Chặn thêm benign (pp) | Từ chối oan tăng thêm (pp) |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| train | L1 | L1 | +98.6 | +15.9 [+8.7, +23.7] | +2.4 | +2.4 |
| train | L2 | L1+L2 | 0.0 | 0.0 [0.0, 0.0] | +2.4 | +2.4 |
| train | L3 | L1+L2+L3 | 0.0 | 0.0 [0.0, 0.0] | 0.0 | 0.0 |
| train | L4 | L1+L2+L3+L4 | 0.0 | 0.0 [0.0, 0.0] | +11.1 | +11.1 |
| holdout | L1 | L1 | +57.9 | +17.1 [+7.9, +28.9] | +2.4 | +2.4 |
| holdout | L2 | L1+L2 | +18.4 | +7.9 [0.0, +18.4] | +2.4 | +2.4 |
| holdout | L3 | L1+L2+L3 | 0.0 | +7.9 [+1.3, +17.1] | 0.0 | 0.0 |
| holdout | L4 | L1+L2+L3+L4 | 0.0 | 0.0 [0.0, 0.0] | +11.1 | +11.1 |
| test_indist | L1 | L1 | +71.4 | +10.7 [0.0, +28.6] | +2.4 | +2.4 |
| test_indist | L2 | L1+L2 | +28.6 | +7.1 [0.0, +21.4] | +2.4 | +2.4 |
| test_indist | L3 | L1+L2+L3 | 0.0 | 0.0 [0.0, 0.0] | 0.0 | 0.0 |
| test_indist | L4 | L1+L2+L3+L4 | 0.0 | 0.0 [0.0, 0.0] | +11.1 | +11.1 |
| ext_attack | L1 | L1 | +29.2 | 0.0 [0.0, 0.0] | +2.4 | +2.4 |
| ext_attack | L2 | L1+L2 | +29.2 | 0.0 [0.0, 0.0] | +2.4 | +2.4 |
| ext_attack | L3 | L1+L2+L3 | 0.0 | 0.0 [0.0, 0.0] | 0.0 | 0.0 |
| ext_attack | L4 | L1+L2+L3+L4 | 0.0 | 0.0 [0.0, 0.0] | +11.1 | +11.1 |

Lợi (giảm ASR, chặn thêm tấn công) đặt cạnh hại (chặn thêm và từ chối oan tăng thêm trên benign) cho từng bước thêm lớp. 'Giảm ASR' có thể lớn hơn 'chặn thêm' vì L1 làm sạch và L3 bọc tài liệu mà không chặn.
