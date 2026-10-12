# Thí nghiệm bổ sung: L2 = Prompt Guard 2 (Ngọc, 12/10/2026)

Không thay cấu hình chính (L2 = LLM-judge `qwen2.5:3b`, tag `freeze-config-2`). Báo cáo đầy đủ: `docs/co-che-L1-L2.html` mục 7.

- `<model>/calibration.json`: chọn ngưỡng trên train (69) + benign tune (42); hai điểm vận hành FPR<=10% và FPR=0.
- `freeze.json`: sha256 của code và calibration trước khi chạy `final` (hold-out chấm đúng một lần).
- `<model>/items.csv`: điểm từng tài liệu (gốc và sau L1); `asr.csv`, `detection.csv`, `report.md`, `meta.json`.
- `l1_audit.json`: kiểm tra L1 bằng 35 mẫu tự viết (`python -m defenses.l1_audit`).

Chạy lại (cần quyền truy cập Prompt Guard 2 trên Hugging Face, trọng số tải vào `models/`, không commit):

```bash
python -c "from huggingface_hub import snapshot_download as s; s('meta-llama/Llama-Prompt-Guard-2-86M', local_dir='models/Llama-Prompt-Guard-2-86M')"
export CAPSTONE_PROMPTGUARD_PATH=models/Llama-Prompt-Guard-2-86M
python -m defenses.eval_promptguard calibrate     # chỉ train + benign tune
python -m defenses.eval_promptguard final         # một lần, ngưỡng đã ghi trong layer2
python -m defenses.eval_promptguard final --from-items   # dựng lại bảng, không chấm lại
```

ASR của `L1+PG2` và `only_PG2` là phản thực: dùng lại lượt sinh của cấu hình `L1` / `baseline` trong
`results/final/merged/results.csv` (L2 không sửa tài liệu; seed suy từ prompt và lượt lấy mẫu).

Kiểm tra giả định trên 435 lượt judge cho qua (L1 so với L1+L2 đã chạy): attack_success khớp 27/28, model_refused khớp 364/364, utility khớp chính xác 233/364. ASR và từ chối là xấp xỉ tốt; utility chỉ tham khảo.
