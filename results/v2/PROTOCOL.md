# Giao thức v2 (ghi trước khi chạy hold-out)

Lý do: bộ prompt của nhóm quá nhỏ (69 train, 38 hold-out) để chỉnh các lớp và để chứng minh khái quát hoá. v2 đưa dữ liệu
công khai vào phần **chỉnh (tune)** và dành cho hold-out những nguồn/giai đoạn mà việc chỉnh chưa từng nhìn thấy.
Kết quả cũ (v1: thiết kế đóng băng `freeze-config-2`, tập ngoài A và B) vẫn giữ nguyên trong `results/final/`.

## Chia dữ liệu (theo nguồn)

| Vai trò | Nguồn |
|---|---|
| **Tune (được phép chỉnh)** | prompt train của nhóm (69) và benign tune (42); tập ngoài A (deepset, Gandalf, jackhhao, BIPIA); Mirror; SPML; bản dịch Việt của deepset; LLMail-Inject **giai đoạn 1** (mẫu tấn công) và nửa benign tune của email kiểm dương tính giả |
| **Hold-out (chạy một lần, sau đóng băng)** | prompt hold-out (38) và paraphrase (14) của nhóm; benign báo cáo (42); LLMail-Inject **giai đoạn 2** (email chưa dùng ở tập B: 500 tấn công chạy cả hệ thống, 1.500 cho phát hiện) và nửa benign còn lại |
| **Không dùng cho hold-out v2** | 240 email tấn công và 120 benign của giai đoạn 3 (v1) và 3.000 email giai đoạn 2 của tập B: kết quả tổng hợp đã được xem trước, nên chỉ thuộc v1 |

Các nguồn không có hàm chấm ASR (Mirror, SPML, deepset, jackhhao, Gandalf, BIPIA text) chỉ dùng để chỉnh và đo phát hiện,
không dùng để kết luận ASR. ASR chỉ tính trên prompt của nhóm và email LLMail (`tool_call` tới `contact@contact.com`).

## Quy tắc chỉnh (đặt trước)

- **L1**: được thêm/sửa họ mẫu và trọng số chỉ dựa trên tune. Mục tiêu: tăng tỉ lệ phát hiện trên tune attack (không tính SPML:
  payload mơ hồ, không phải lệnh rõ ràng). Ràng buộc: tỉ lệ chặn nhầm của L1 trên toàn bộ benign tune không vượt 1,0% và
  không thêm lượt chặn nhầm nào trên benign tune của nhóm so với bản đóng băng cũ. Ngưỡng 0,6 giữ nguyên.
- **L2**: giữ prompt v4 và model `qwen2.5:3b`. Ngưỡng chọn lại là giá trị cho tỉ lệ phát hiện cao nhất trên tune attack
  (không tính SPML) với FPR ≤ 2% trên benign tune; nếu không cải thiện rõ so với 0,5 thì giữ 0,5.
- **L3**: giữ nguyên biến thể `full`.
- **L4**: chọn lại τ là giá trị nhỏ nhất có FPR ≤ 10% trên benign tune **trong chuỗi** (L1+L2+L3+L4), như cũ. (Sửa trước khi chạy hold-out: ngân sách 10% áp cho từng quần thể benign, lấy ngưỡng lớn nhất; lý do ở `tuning_log.md`.)
- Mọi lần chỉnh ghi vào `results/v2/tuning_log.md`. Sau khi gắn tag `freeze-v2` không được sửa lớp nào.

## Chạy

1. Giai đoạn 1b: prompt train + benign của nhóm (3 mẫu), chuỗi cộng dồn và ablation (như cũ), cấu hình `freeze-v2`.
2. Giai đoạn 2b (một lần, `--confirm-final-holdout`): hold-out + paraphrase của nhóm (2 mẫu), email LLMail hold-out
   (1 mẫu mỗi email), ablation một lớp trên hold-out của nhóm, phát hiện L1/L2 trên LLMail giai đoạn 2 chưa dùng.
3. Phân tích, bảng, báo cáo và slide (v1 xuống phụ lục).

## Ghi chú trung thực

- Hold-out của nhóm (38 prompt) và các số tổng hợp của v1 (ví dụ L1 chặn 57,9% hold-out) đã được nhìn trước khi chỉnh v2.
  v2 không dùng từng prompt hold-out để chỉnh, nhưng phần hold-out thật sự "chưa thấy" chỉ là LLMail giai đoạn 2.
- LLMail giai đoạn 1 và 2 cùng người thi và cùng kịch bản; tách theo giai đoạn chỉ là tách theo thời gian, không phải tách theo
  người tấn công.
- Email benign của LLMail (160, kiểm dương tính giả) đã xuất hiện ở v1 (tập B, kết quả tổng hợp: không chặn nhầm). v2 chia đôi (80 chỉnh L4, 80 hold-out);
  nửa hold-out vì vậy không "chưa thấy" hoàn toàn, nhưng không dùng để chỉnh gì.
- **Giảm cỡ mẫu vì thời gian (quyết định trước khi chạy bất kỳ hold-out LLMail nào):** email LLMail gđ2 chạy cả hệ thống 500 → 200 tấn công
  (100 đã kích hoạt API, 100 do judge của bộ dữ liệu gán nhãn), đo phát hiện 1.500 → 600 email; giai đoạn 1b dùng 2 mẫu mỗi prompt thay vì 3 và
  không chạy ablation trên train. Các lần chạy song song trên Ollama không nhanh hơn (đã đo), nên chạy tuần tự.
- Giai đoạn 1b chỉ chạy 42 tài liệu benign của nhóm không dùng để chỉnh (nửa dùng để chỉnh không chạy lại), thêm một cắt giảm vì thời gian.
