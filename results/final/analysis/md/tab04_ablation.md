**Bảng 4. Ablation: từng lớp chạy riêng (only_L*)**

| Split | Config | Vai trò | ASR prompt (%) | Bootstrap 95% | Giảm vs baseline (pp) | Giảm tương đối (%) | Tỉ phần của chuỗi đầy đủ (%) | Giảm biên trong chuỗi (pp) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | baseline | đối chiếu | 15.9 | [8.7, 23.7] | - | n/a | n/a | n/a |
| train | only_L1 | chỉ một lớp | 0.0 | [0.0, 0.0] | +15.9 [+8.7, +23.7] | 100.0 | 100.0 | +15.9 |
| train | only_L2 | chỉ một lớp | 5.8 | [1.4, 11.6] | +10.1 [+3.4, +17.4] | 63.6 | 63.6 | 0.0 |
| train | only_L3 | chỉ một lớp | 4.3 | [0.0, 10.1] | +11.6 [+3.4, +20.3] | 72.7 | 72.7 | 0.0 |
| train | only_L4 | chỉ một lớp | 5.8 | [1.4, 11.6] | +10.1 [+2.9, +17.9] | 63.6 | 63.6 | 0.0 |
| train | L1+L2+L3+L4 | chuỗi đầy đủ | 0.0 | [0.0, 0.0] | +15.9 [+8.7, +23.7] | 100.0 | n/a | n/a |
| holdout | baseline | đối chiếu | 32.9 | [19.7, 47.4] | - | n/a | n/a | n/a |
| holdout | only_L1 | chỉ một lớp | 15.8 | [5.3, 28.9] | +17.1 [+5.3, +30.3] | 52.0 | 52.0 | +17.1 |
| holdout | only_L2 | chỉ một lớp | 13.2 | [2.6, 23.7] | +19.7 [+7.9, +32.9] | 60.0 | 60.0 | +7.9 |
| holdout | only_L3 | chỉ một lớp | 10.5 | [2.6, 21.1] | +22.4 [+10.5, +35.5] | 68.0 | 68.0 | +7.9 |
| holdout | only_L4 | chỉ một lớp | 18.4 | [7.9, 31.6] | +14.5 [+2.6, +28.9] | 44.0 | 44.0 | 0.0 |
| holdout | L1+L2+L3+L4 | chuỗi đầy đủ | 0.0 | [0.0, 0.0] | +32.9 [+19.7, +47.4] | 100.0 | n/a | n/a |
| test_indist | baseline | đối chiếu | 17.9 | [0.0, 39.3] | - | n/a | n/a | n/a |
| test_indist | only_L1 | chỉ một lớp | 7.1 | [0.0, 21.4] | +10.7 [0.0, +28.6] | 60.0 | 60.0 | +10.7 |
| test_indist | L1+L2+L3+L4 | chuỗi đầy đủ | 0.0 | [0.0, 0.0] | +17.9 [0.0, +39.3] | 100.0 | n/a | n/a |
| ext_attack | baseline | đối chiếu | 0.0 | [0.0, 0.0] | - | n/a | n/a | n/a |
| ext_attack | L1+L2+L3+L4 | chuỗi đầy đủ | 0.0 | [0.0, 0.0] | 0.0 [0.0, 0.0] | n/a | n/a | n/a |

Đóng góp biên của một lớp so với baseline = baseline trừ only_Lk. Tỉ phần = giảm riêng lẻ / giảm của chuỗi đầy đủ (tổng các tỉ phần có thể vượt 100% khi các lớp chặn cùng một mẫu). Cột cuối là mức giảm khi *thêm* lớp đó vào chuỗi cộng dồn (Bảng 3). train: tổng giảm riêng lẻ của các lớp = +47.8 pp, giảm của chuỗi đầy đủ = +15.9 pp, chồng lấn/đồng tác động = +31.9 pp. holdout: tổng giảm riêng lẻ của các lớp = +73.7 pp, giảm của chuỗi đầy đủ = +32.9 pp, chồng lấn/đồng tác động = +40.8 pp. test_indist: tổng giảm riêng lẻ của các lớp = +10.7 pp, giảm của chuỗi đầy đủ = +17.9 pp, chồng lấn/đồng tác động = -7.1 pp. ext_attack: tổng giảm riêng lẻ của các lớp = 0.0 pp, giảm của chuỗi đầy đủ = 0.0 pp, chồng lấn/đồng tác động = 0.0 pp.
