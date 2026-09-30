# Capstone — Prompt-Injection Red-Team & Layered Defense for an LLM Agent

Môn học: **Trustworthy AI**
Nhóm: **Minh, Thành, Ngọc, Hương, Nam** (5 thành viên)

## Mục tiêu

Xây dựng một LLM agent dạng RAG (tóm tắt/trả lời dựa trên tài liệu lấy từ nguồn ngoài), sau đó:

1. Đo Attack Success Rate (ASR) khi agent chưa có phòng thủ, bằng bộ prompt injection/jailbreak tự thiết kế.
2. Triển khai lại 3 lớp phòng thủ chuẩn (input sanitization, refusal classifier, privileged-instruction separation) và đo ASR giảm dần qua từng lớp.
3. Đề xuất lớp phòng thủ thứ 4 tự nghĩ ra — **Dual-Response Consistency Check** — và đánh giá khả năng tổng quát hoá trên tập tấn công chưa từng thấy (held-out set).

Chi tiết plan đầy đủ (literature review, methodology, metric, timeline 10 tuần, 2 mốc nộp): xem báo cáo tiến độ.

**Báo cáo tiến độ (Claude Doc, đang cập nhật):** https://claude.ai/artifact/X9UckLMTyS9LjZUzSATWNS

## Phân công công việc

| Thành viên | Việc phụ trách | Thư mục |
|---|---|---|
| **Minh** | Cập nhật doc tiến độ, tổng hợp báo cáo | [`docs/`](docs/) + link doc ở trên |
| **Hương** | Tìm & tuyển chọn bộ prompt tấn công (injection, jailbreak, obfuscation...) | [`attack_prompts/`](attack_prompts/) |
| **Thành** | Đề xuất AI Agent dùng (model + framework) + cách cài đặt | [`ai_agent_proposal/`](ai_agent_proposal/) |
| **Ngọc** | Đề xuất AI Agent dùng (model + framework) + cách cài đặt | [`ai_agent_proposal/`](ai_agent_proposal/) |
| **Nam** | Đề xuất AI Agent dùng (model + framework) + cách cài đặt | [`ai_agent_proposal/`](ai_agent_proposal/) |

> Thành, Ngọc, Nam: mỗi người viết 1 đề xuất riêng trong `ai_agent_proposal/` (ví dụ `de-xuat-thanh.md`), nêu rõ: model/API chọn, framework (LangChain/LlamaIndex/tự viết), lý do chọn, các bước cài đặt cụ thể. Cả nhóm họp chốt 1 phương án trước tuần 3.

## Cấu trúc thư mục

```
trustworthy-ai-prompt-injection-capstone/
├── README.md                  # file này
├── docs/                      # ghi chú, tài liệu tham khảo, báo cáo
├── attack_prompts/            # bộ prompt tấn công (Hương)
├── ai_agent_proposal/         # đề xuất AI Agent + cài đặt (Thành, Ngọc, Nam)
├── baseline_agent/            # code agent RAG chưa có phòng thủ
├── defenses/                  # 3 lớp phòng thủ chuẩn + lớp cải tiến
└── requirements.txt
```

## Timeline

| Tuần | Nội dung | Mốc |
|---|---|---|
| 1-2 | Khảo sát tài liệu + lập kế hoạch | ✅ Xong |
| 3-5 | Baseline agent + bộ prompt tấn công + đo ASR | **Giữa kỳ (tuần 5)** |
| 6-8 | Cài đặt 3 lớp phòng thủ chuẩn | |
| 9 | Lớp cải tiến (Dual-Response Consistency) + held-out test | |
| 10 | Hoàn thiện báo cáo | **Cuối kỳ (tuần 10)** |
