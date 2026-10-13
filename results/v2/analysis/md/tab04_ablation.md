**Bảng 4. Ablation: từng lớp chạy riêng (only_L*)**

| Split | Config | Vai trò | ASR prompt (%) | Bootstrap 95% | Giảm vs baseline (pp) | Giảm tương đối (%) | Tỉ phần của chuỗi đầy đủ (%) | Giảm biên trong chuỗi (pp) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | baseline | đối chiếu | 15.9 | [7.2, 24.6] | - | n/a | n/a | n/a |
| train | only_L1 | chỉ một lớp | 0.0 | [0.0, 0.0] | +15.9 [+7.2, +24.6] | 100.0 | 100.0 | +15.9 |
| train | L1+L2+L3+L4 | chuỗi đầy đủ | 0.0 | [0.0, 0.0] | +15.9 [+7.2, +24.6] | 100.0 | n/a | n/a |
| holdout | baseline | đối chiếu | 34.2 | [19.7, 48.7] | - | n/a | n/a | n/a |
| holdout | only_L1 | chỉ một lớp | 13.2 | [2.6, 26.3] | +21.1 [+10.5, +32.9] | 61.5 | 69.6 | +19.7 |
| holdout | only_L2 | chỉ một lớp | 10.5 | [2.6, 21.1] | +23.7 [+10.5, +38.2] | 69.2 | 78.3 | +9.2 |
| holdout | only_L3 | chỉ một lớp | 7.9 | [0.0, 15.8] | +26.3 [+13.2, +40.8] | 76.9 | 87.0 | +3.9 |
| holdout | only_L4 | chỉ một lớp | 15.8 | [5.3, 28.9] | +18.4 [+6.6, +31.6] | 53.8 | 60.9 | -2.6 |
| holdout | L1+L2+L3+L4 | chuỗi đầy đủ | 3.9 | [0.0, 10.5] | +30.3 [+15.8, +46.1] | 88.5 | n/a | n/a |
| test_indist | baseline | đối chiếu | 21.4 | [3.6, 42.9] | - | n/a | n/a | n/a |
| test_indist | only_L1 | chỉ một lớp | 7.1 | [0.0, 21.4] | +14.3 [0.0, +32.1] | 66.7 | 66.7 | +14.3 |
| test_indist | L1+L2+L3+L4 | chuỗi đầy đủ | 0.0 | [0.0, 0.0] | +21.4 [+3.6, +42.9] | 100.0 | n/a | n/a |

Đóng góp biên của một lớp so với baseline = baseline trừ only_Lk. Tỉ phần = giảm riêng lẻ / giảm của chuỗi đầy đủ (tổng các tỉ phần có thể vượt 100% khi các lớp chặn cùng một mẫu). Cột cuối là mức giảm khi *thêm* lớp đó vào chuỗi cộng dồn (Bảng 3). train: tổng giảm riêng lẻ của các lớp = +15.9 pp, giảm của chuỗi đầy đủ = +15.9 pp, chồng lấn/đồng tác động = 0.0 pp. holdout: tổng giảm riêng lẻ của các lớp = +89.5 pp, giảm của chuỗi đầy đủ = +30.3 pp, chồng lấn/đồng tác động = +59.2 pp. test_indist: tổng giảm riêng lẻ của các lớp = +14.3 pp, giảm của chuỗi đầy đủ = +21.4 pp, chồng lấn/đồng tác động = -7.1 pp.
