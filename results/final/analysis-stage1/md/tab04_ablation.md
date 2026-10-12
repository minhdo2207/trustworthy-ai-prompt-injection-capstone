**Bảng 4. Ablation: từng lớp chạy riêng (only_L*)**

| Split | Config | Vai trò | ASR prompt (%) | Bootstrap 95% | Giảm vs baseline (pp) | Giảm tương đối (%) | Tỉ phần của chuỗi đầy đủ (%) | Giảm biên trong chuỗi (pp) |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | baseline | đối chiếu | 15.9 | [8.7, 23.7] | - | n/a | n/a | n/a |
| train | only_L1 | chỉ một lớp | 0.0 | [0.0, 0.0] | +15.9 [+8.7, +23.7] | 100.0 | 100.0 | +15.9 |
| train | only_L2 | chỉ một lớp | 5.8 | [1.4, 11.6] | +10.1 [+3.4, +17.4] | 63.6 | 63.6 | 0.0 |
| train | only_L3 | chỉ một lớp | 4.3 | [0.0, 10.1] | +11.6 [+3.4, +20.3] | 72.7 | 72.7 | 0.0 |
| train | only_L4 | chỉ một lớp | 5.8 | [1.4, 11.6] | +10.1 [+2.9, +17.9] | 63.6 | 63.6 | 0.0 |
| train | L1+L2+L3+L4 | chuỗi đầy đủ | 0.0 | [0.0, 0.0] | +15.9 [+8.7, +23.7] | 100.0 | n/a | n/a |

Đóng góp biên của một lớp so với baseline = baseline trừ only_Lk. Tỉ phần = giảm riêng lẻ / giảm của chuỗi đầy đủ (tổng các tỉ phần có thể vượt 100% khi các lớp chặn cùng một mẫu). Cột cuối là mức giảm khi *thêm* lớp đó vào chuỗi cộng dồn (Bảng 3). train: tổng giảm riêng lẻ của các lớp = +47.8 pp, giảm của chuỗi đầy đủ = +15.9 pp, chồng lấn/đồng tác động = +31.9 pp.
