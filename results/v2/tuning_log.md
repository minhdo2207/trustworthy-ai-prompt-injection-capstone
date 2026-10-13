# Nhật ký chỉnh (v2)

Dữ liệu chỉnh: `attack_prompts/v2_detection_tune.json` (12.328 mục: nhóm train và benign tune, tập A, Mirror, SPML, bản dịch Việt,
LLMail gđ1, 80 email benign tune). Không dùng hold-out. Quy tắc đặt trước: `PROTOCOL.md`.

## L1
- Bản đóng băng cũ (`freeze-config-2`) trên tập chỉnh: tỉ lệ phát hiện mục tiêu (không tính SPML) **38,9%** (1.994/5.128), chặn nhầm benign tune **0,17%** (8/4.600).
- Thêm 12 mẫu (11 họ mới theo cấu trúc, xem khối "v2" trong `defenses/layer1_filtering.py`): persona "không giới hạn", rò rỉ "xuất hướng dẫn/cấu hình",
  hỏi mật khẩu, ghi đè kiểu "negate/ nhầm chữ", "forget everything", "ignore ... regarding", ghi đè/rò rỉ tiếng Ý/Tây Ban Nha/Pháp/Đức,
  ép định dạng mật mã, chèn mã ("incorporate the following code ... ```"), yêu cầu gửi email tới một địa chỉ, thẻ vai giả (`</tool>`, `[system]`).
- Hai mẫu được siết sau khi thử với câu benign: chủ ngữ của "no restrictions" (you/I/it/AI/...), và chỉ giữ các động từ chèn mã hiếm (bỏ use/add/include).
- Không thêm mẫu gắn với mục tiêu riêng của LLMail (từ "confirmation", địa chỉ cụ thể) để tránh học thuộc mục tiêu của benchmark.
- Kết quả sau chỉnh: tỉ lệ phát hiện mục tiêu **51,3%** (2.630/5.128), chặn nhầm benign tune **0,26%** (12/4.600, đều là tài liệu mã BIPIA 4 và
  các câu "gương" của Mirror 8); benign tune của nhóm 0/42 (không có lượt chặn nhầm mới). Ràng buộc FPR <= 1,0%: đạt. Ngưỡng 0,6 giữ nguyên.
- Còn bỏ lọt nhiều: SPML (1,5%, mục tiêu loại trừ), bản dịch Việt (4,9%), BIPIA text (2%), email LLMail gđ1 (38,5%; phần lớn đổi cách nói hoặc làm rối chữ).

## L2
- Giữ prompt v4 và `qwen2.5:3b`. Điểm gần như nhị phân: mọi ngưỡng từ 0,15 đến 0,90 cho cùng tỉ lệ phát hiện (64,1% trên tune attack không tính SPML) và FPR 1,62%.
- Theo quy tắc ("không cải thiện rõ so với 0,5 thì giữ 0,5") ngưỡng giữ **0,5**. Điểm L2 trên mẫu: `l2_tune_scores.csv` (9.573 mục).

## L3
- Giữ nguyên biến thể `full`.

## L4
- Hiệu chỉnh trong chuỗi, xem `l4-calib` và phần cuối file này (điền sau khi chạy).
