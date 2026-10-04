# Capstone — Prompt-Injection Red-Team & Layered Defense for an LLM

Môn học: **Trustworthy AI**
Nhóm: **Nhóm 4** — Minh, Thành, Ngọc, Hương, Nam
Thời gian thực nghiệm: **05/10 → 14/10/2026** (giữa kỳ 10/10, nộp cuối 14/10)

## Mục tiêu

Đo mức độ một LLM bị prompt injection khi đọc tài liệu không đáng tin cậy, rồi đo từng lớp phòng thủ giảm được bao nhiêu:

1. Đo **ASR** (tỉ lệ tấn công thành công) khi chạy thẳng model, không có phòng thủ.
2. Cài đặt các lớp phòng thủ dựa trên nghiên cứu đã có và đo ASR **cộng dồn** qua từng lớp.
3. Cài đặt lại ý tưởng kiểm tra nhất quán (MELON) làm lớp thứ 4 và đánh giá khả năng tổng quát hoá trên tập hold-out (kỹ thuật tấn công chưa từng thấy).
4. Báo cáo kèm tỉ lệ từ chối oan trên tập benign, chất lượng tác vụ và độ trễ, để biết phòng thủ có đáng giá không.

## Cơ sở lý thuyết

Khung chính: **Liu và cs. 2024**, *Formalizing and Benchmarking Prompt Injection Attacks and Defenses* (USENIX Security 2024) — [bài báo](https://arxiv.org/pdf/2310.12815), [mã nguồn](https://github.com/liu00222/Open-Prompt-Injection).

- Tác vụ đích: chỉ dẫn `s_t` (ví dụ "tóm tắt tài liệu") cộng dữ liệu `x_t`. Kẻ tấn công thay dữ liệu bằng `x̃` có giấu chỉ dẫn `s_e`; model nhận `f(s_t ⊕ x̃)`.
- 5 kiểu tấn công cơ bản: Naive, Escape Characters, Context Ignoring, Fake Completion, Combined. Các nhóm nâng cao (roleplay, code-switching, obfuscation, many-shot) gắn nguồn riêng cho từng loại.
- Phòng thủ chia hai nhóm: **prevention-based** (làm khó tấn công) và **detection-based** (phát hiện dữ liệu nhiễm).
- Thước đo: ASR (biến thể của ASV), tỉ lệ từ chối oan (FPR), tỉ lệ prompt tấn công lọt qua (FNR), chất lượng tác vụ khi không bị tấn công (PNA-T).

Các nguồn bổ sung: Greshake và cs. 2023 (injection gián tiếp), HackAPrompt 2023 (danh mục kỹ thuật), MELON, ICML 2025 (nguồn của L4), Spotlighting 2024 (nguồn của L3).

## Các lớp phòng thủ

| Lớp | Cơ chế | Người phụ trách |
|---|---|---|
| L1 | Lọc đầu vào: chuẩn hoá Unicode, bỏ ký tự vô hình, giải mã Base64/hex/ROT13 rồi quét lại, từ khoá đa ngôn ngữ | Ngọc,Minh|
| L2 | Bộ phân loại: Llama Prompt Guard 2 (dự phòng: ProtectAI deberta), ngưỡng chọn chỉ trên train | Ngọc, Minh |
| L3 | Tách chỉ dẫn và dữ liệu, **không huấn luyện**: spotlighting, system prompt theo thứ tự ưu tiên | Nam, Minh |
| L4 | Kiểm tra nhất quán, theo MELON: chạy lại với tác vụ người dùng bị che (giữ nguyên tài liệu); hai lần chạy cho hành vi giống nhau thì tài liệu đang điều khiển model | Minh, Thành |

Instruction Hierarchy, StruQ, SecAlign là phương pháp huấn luyện model, nhóm không làm, chỉ nêu như hướng phát triển.

## Mô hình và môi trường

- Model chính: **Qwen3-8B** chạy local qua Ollama (`ollama pull qwen3:8b`).
- Model chéo (làm nếu còn thời gian): GLM qua OpenRouter, chỉ chạy tập hold-out một lần.
- Tác vụ: tóm tắt/hỏi đáp tài liệu; system prompt có `SECRET_CANARY` sinh ngẫu nhiên mỗi lần chạy.
- Cài thư viện: `pip install -r requirements.txt`. API key để trong `.env` (đã nằm trong `.gitignore`), **không commit lên repo**.

## Phân công

| Thành viên | Việc chính | Thư mục |
|---|---|---|
| **Minh** | Điều phối, review, Related Work, script thống kê (khoảng tin cậy Wilson), kiểm tra giải mã, bản giữa kỳ, đóng băng repo (tag `v1.0`), báo cáo, slide, nộp bài | [`docs/`](docs/) |
| **Hương** | Bảng phân loại, gắn nhãn lại 72 prompt (schema v2), bổ sung 4 kiểu cơ bản, mẫu từ dataset có nguồn, tập benign ≥ 50, phụ lục, phân tích lỗi | [`attack_prompts/`](attack_prompts/) |
| **Ngọc** | L1, L2, ablation và tỉ lệ từ chối oan | [`defenses/`](defenses/) |
| **Nam** | L3, L4 (logic so khớp), chạy chéo GLM, demo | [`defenses/`](defenses/) |
| **Thành** | Agent giả lập, harness `eval_asr.py`, ASR baseline, ghép các lớp vào harness, tích hợp L4, đo độ trễ, chạy ma trận cuối | [`baseline_agent/`](baseline_agent/), [`defenses/`](defenses/) |

Chi tiết từng việc và hạn: xem bảng phân công 05–14/10 của nhóm.

## Cấu trúc thư mục

```
trustworthy-ai-prompt-injection-capstone/
├── README.md                  # file này
├── CONTRIBUTING.md            # quy tắc commit, nhánh, pull request
├── docs/                      # báo cáo tiến độ, kế hoạch (LaTeX), tài liệu
├── attack_prompts/            # bộ prompt tấn công train/hold-out (Hương)
├── ai_agent_proposal/         # đề xuất agent (đã chốt Qwen3-8B, xem baseline_agent/)
├── baseline_agent/            # agent giả lập chưa có phòng thủ (Thành)
├── defenses/                  # L1–L4 và eval_asr.py
└── requirements.txt
```

## Timeline

| Giai đoạn | Nội dung | Mốc |
|---|---|---|
| Trước 05/10 | Khảo sát tài liệu, threat model, bộ prompt tấn công ban đầu (72 prompt) | Xong |
| 05–07/10 | Khảo sát theo khung Liu 2024; gắn nhãn lại prompt; dựng agent giả lập và harness | |
| 08–10/10 | L1–L3, ASR baseline và bảng cộng dồn; thiết kế L4 | **Giữa kỳ 10/10** |
| 11–14/10 | L4, ablation, đóng băng repo, chạy ma trận cuối, báo cáo, slide, demo | **Nộp cuối 14/10** |

Phạm vi được ưu tiên: baseline, L1–L3 và kết quả hold-out là phần lõi. Nếu chậm, cắt theo thứ tự: chạy chéo GLM, tập `test_indist`, rồi L4 (chuyển thành hướng phát triển).

## Quy tắc làm việc

Nhánh `main` đã bị khoá: **mọi thay đổi phải qua pull request** (không bắt buộc approve, nhưng nên nhờ một người xem trước khi merge). Xem [CONTRIBUTING.md](CONTRIBUTING.md) cho cách đặt tên nhánh, định dạng commit và các quy tắc riêng của đề tài (không tinh chỉnh theo hold-out, mọi prompt phải ghi nguồn).

