# AI Agent Proposal — phụ trách: Thành, Ngọc, Nam

Mỗi người viết 1 file đề xuất riêng (`de-xuat-<ten>.md`), nêu rõ:

- **Model/API đề xuất**: tên model, nhà cung cấp, vì sao chọn (chi phí, tốc độ, chất lượng, free-tier có sẵn không).
- **Framework**: dùng LangChain/LlamaIndex, hay tự viết agent loop đơn giản bằng Python.
- **Kiến trúc agent**: agent nhận query → retrieve tài liệu (giả lập RAG) → đưa vào model → sinh output.
- **Các bước cài đặt cụ thể**: từ tạo API key/tải model đến chạy thử "Hello World" đầu tiên.
- **Ưu/nhược điểm** so với các lựa chọn khác đã cân nhắc.

Gợi ý các hướng để cân nhắc (không bắt buộc theo):
- API free-tier: Groq, OpenRouter (có nhiều model free), Google Gemini free tier.
- Model local 4-bit quantized qua Ollama: Llama-3-8B, Phi-3.

Sau khi cả 3 nộp đề xuất, cả nhóm họp chốt 1 phương án trước tuần 3 (ghi lại quyết định cuối trong `quyet-dinh-cuoi.md`).
