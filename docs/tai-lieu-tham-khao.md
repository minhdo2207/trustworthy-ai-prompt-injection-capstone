# Tài liệu tham khảo và tài liệu dùng chung

Danh mục duy nhất cho cả nhóm: mỗi tài liệu dùng ở đâu, ai đọc, và đã kiểm chứng đến mức nào.
Khung chính của đề tài: **R1 (Liu và cs. 2024)**.

**Mức kiểm chứng**
- **A**: đã đối chiếu với bản PDF của bài (tên tác giả, tên loại tấn công/phòng thủ, số liệu trích ở đây là từ bài).
- **B**: chỉ đọc phần tóm tắt hoặc trang giới thiệu. **Phải đọc bản gốc trước khi trích số liệu.** Tên tác giả để trống thì điền khi mở trang bài.

---

## 1. Khung và phân loại tấn công

| ID | Tài liệu | Link | Vai trò trong đề tài | Dùng ở mục báo cáo | KC |
|---|---|---|---|---|---|
| R1 | Liu, Jia, Geng, Jia, Gong. *Formalizing and Benchmarking Prompt Injection Attacks and Defenses*. USENIX Security 2024 | https://arxiv.org/pdf/2310.12815 · mã: https://github.com/liu00222/Open-Prompt-Injection | **Khung chính**: định nghĩa hình thức `x̃ = A(x_t, s_e, x_e)`, 5 kiểu tấn công, 10 phòng thủ (prevention/detection), thước đo ASV, MR, PNA-T, FPR, FNR | Bài toán; phân loại; thước đo; kết quả phòng thủ | A |
| R2 | Greshake, Abdelnabi, Mishra, Endres, Holz, Fritz. *Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection*. 2023 | https://arxiv.org/pdf/2302.12173 | Mô hình đe doạ: 4 cách đưa lệnh vào (passive, active, user-driven, hidden); 6 loại hậu quả | Mô hình đe doạ; loại indirect | A |
| R3 | Schulhoff, Pinto, Khan, Bouchard, Si, Boyd-Graber, Anati, Tagliabue, Kost, Carnahan. *Ignore This Title and HackAPrompt*. EMNLP 2023 | https://www.cs.umd.edu/~jbg/docs/2023_emnlp_hackaprompt.pdf | Danh mục kỹ thuật chi tiết (Context Ignoring, Compound Instruction, Special Case, Few Shot, Refusal Suppression, Obfuscation, Payload Splitting, Defined Dictionary...) | Phụ lục: nhãn kỹ thuật cho từng prompt | A |
| R4 | Perez & Ribeiro. *Ignore Previous Prompt: Attack Techniques For Language Models*. 2022 | https://arxiv.org/abs/2211.09527 | Hai mục tiêu: goal hijacking và prompt leaking | Cột "mục tiêu tấn công" | B |
| R5 | Wang, Li, Xiang, Zhang, Li, Zhang, Wang, Tian. *The Landscape of Prompt Injection Threats in LLM Agents: From Taxonomy to Analysis* (SoK). 2026 | https://arxiv.org/pdf/2602.10453 | Phân loại phòng thủ theo giai đoạn (text, model, execution); benchmark AgentPI; số liệu chi phí MELON; kết luận "không có phòng thủ hoàn hảo" | Khảo sát phòng thủ; thảo luận chi phí và over-defense | A |
| R6 | Xu & Parhi. *A Survey of Attacks on Large Language Models*. 2025 | https://arxiv.org/pdf/2505.12567 | Tổng quan nền; phân biệt jailbreak với injection (dựa trên khung R1) | Related Work (phần nền) | A |

## 2. Họ jailbreak (nhóm nâng cao của bộ prompt)

| ID | Tài liệu | Link | Dùng cho nhóm | KC |
|---|---|---|---|---|
| R7 | Shen, Chen, Backes, Shen, Zhang. *"Do Anything Now"*. ACM CCS 2024 | https://arxiv.org/pdf/2308.03825 · dữ liệu: https://github.com/verazuo/jailbreak_llms | Roleplay/DAN | B |
| R8 | Yong, Menghini, Bach. *Low-Resource Languages Jailbreak GPT-4*. 2023 | https://arxiv.org/html/2310.02446v1 | Code-switching, ngôn ngữ khác | B |
| R9 | Wei, Haghtalab, Steinhardt. *Jailbroken: How Does LLM Safety Training Fail?* NeurIPS 2023 | https://arxiv.org/pdf/2307.02483 | Obfuscation (mismatched generalization) | B |
| R10 | Anil và cs. *Many-shot Jailbreaking*. NeurIPS 2024 | https://proceedings.neurips.cc/paper_files/paper/2024/hash/ea456e232efb72d261715e33ce25f208-Abstract.html | Many-shot | B |

## 3. Benchmark và dataset (lấy mẫu có nguồn)

| ID | Tài liệu / dataset | Link | Ghi chú | KC |
|---|---|---|---|---|
| D1 | BIPIA (Yi, Xie, Zhu, Kiciman, Sun, Xie, Wu) | https://arxiv.org/pdf/2312.14197 · https://github.com/microsoft/BIPIA | Benchmark indirect injection; có hai phòng thủ boundary awareness, explicit reminder | B |
| D2 | InjecAgent (Zhan, Liang, Ying, Kang) | https://arxiv.org/html/2403.02691v3 | 1.054 test case; mẫu cho prompt kiểu tool-action | B |
| D3 | AgentDojo (Debenedetti, Zhang, Balunović, Beurer-Kellner, Fischer, Tramèr) | https://arxiv.org/pdf/2406.13352 | 97 tác vụ, 629 test bảo mật, 4 môi trường; mẫu cách đo ASR cùng utility | A |
| D4 | Tensor Trust | https://proceedings.iclr.cc/paper_files/paper/2024/hash/519c51529c3544b3430bd8b17d400365-Abstract-Conference.html | Hơn 500 nghìn prompt từ trò chơi online | B |
| D5 | Lakera/gandalf_ignore_instructions | https://huggingface.co/datasets/Lakera/gandalf_ignore_instructions | Mẫu "ignore instructions" thật | B |
| D6 | deepset/prompt-injections | https://huggingface.co/datasets/deepset/prompt-injections | Có nhãn injection/không; có thể lấy mẫu benign | B |
| D7 | xTRam1/safe-guard-prompt-injection | tìm theo tên trên Hugging Face | context manipulation, social engineering, fake completion | B |
| D8 | jackhhao/jailbreak-classification | https://huggingface.co/datasets/jackhhao/jailbreak-classification | Nhãn jailbreak/benign | B |
| D9 | InjecGuard / NotInject | https://arxiv.org/pdf/2410.22770 | Đo over-defense: cơ sở cho tập benign và FPR | B |

## 4. Phòng thủ, theo từng lớp

**L1 — Lọc đầu vào (Ngọc)**

| ID | Tài liệu | Link | Lấy gì | KC |
|---|---|---|---|---|
| P1 | Alon & Kamfonas. *Detecting Language Model Attacks with Perplexity*. 2023 | https://arxiv.org/abs/2308.14132v3 | Lọc perplexity; false positive cao nếu chỉ dùng perplexity | B |
| P2 | Jain và cs. *Baseline Defenses for Adversarial Attacks Against Aligned LMs*. 2023 | https://arxiv.org/pdf/2309.00614 | Perplexity, paraphrase, retokenization | B |
| — | R1 mục 5 | (như R1) | Paraphrasing, retokenization làm giảm chất lượng dữ liệu sạch (PNA-T) | A |

**L2 — Bộ phân loại (Ngọc)**

| ID | Tài liệu / model | Link | Lấy gì | KC |
|---|---|---|---|---|
| P3 | Llama Prompt Guard 2 (86M, 22M) | https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-22M | Bộ phân loại; cần xin quyền truy cập trên Hugging Face | B |
| P4 | ProtectAI deberta-v3-base-prompt-injection-v2 | https://www.promptlayer.com/models/deberta-v3-base-prompt-injection | Phương án dự phòng | B |
| P5 | GenTel-Safe | https://arxiv.org/pdf/2409.19521 | Bộ phát hiện kèm benchmark | B |
| P6 | Attention Tracker | https://arxiv.org/pdf/2411.00348 | Phát hiện qua attention (cần truy cập bên trong model, chỉ để nêu) | B |
| P7 | *How Not to Detect Prompt Injections with an LLM* | https://arxiv.org/pdf/2507.05630 | Lỗ hổng cấu trúc của known-answer detection: dùng khi giải thích hạn chế của LLM-judge | B |

**L3 — Tách chỉ dẫn và dữ liệu (Nam)**

| ID | Tài liệu | Link | Lấy gì | KC |
|---|---|---|---|---|
| P8 | Hines, Lopez, Hall, Zarfati, Zunger. *Defending Against Indirect Prompt Injection Attacks With Spotlighting*. 2024 | https://arxiv.org/pdf/2403.14720 | Ba biến thể: delimiting, datamarking, encoding | B |
| P9 | Wallace và cs. *The Instruction Hierarchy*. OpenAI, 2024 | https://arxiv.org/pdf/2404.13208 | Ý tưởng thứ tự ưu tiên system > user > dữ liệu; **phương pháp huấn luyện, nhóm không làm** | B |
| P10 | Chen, Piet, Sitawarin, Wagner. *StruQ*. USENIX Security 2025 | https://arxiv.org/pdf/2402.06363 · https://github.com/Sizhe-Chen/StruQ | Hướng nâng cao (huấn luyện) | B |
| P11 | SecAlign | https://arxiv.org/pdf/2410.05451 | Hướng nâng cao (huấn luyện, DPO) | B |
| P12 | CaMeL, *Defeating Prompt Injections by Design* | https://arxiv.org/pdf/2503.18813 | Tách luồng điều khiển và dữ liệu; hướng nâng cao | B |
| — | R1 mục 5; D1 | (như trên) | Delimiters, sandwich, instructional prevention; boundary awareness, explicit reminder. **Sandwich làm giảm chất lượng tóm tắt** (PNA-T 0,38 → 0,24) | A |

**L4 — Kiểm tra nhất quán (Nam, Thành)**

| ID | Tài liệu | Link | Lấy gì | KC |
|---|---|---|---|---|
| P13 | MELON: *Provable Defense Against Indirect Prompt Injection Attacks in AI Agents*. ICML 2025 | https://arxiv.org/html/2502.05174v2 | **Che tác vụ người dùng, giữ tài liệu**, chạy lại, so sánh lời gọi tool (cosine, ngưỡng mặc định 0,8); tốn khoảng gấp đôi lượt gọi; kém với tấn công qua văn bản (72,73% trường hợp thất bại) | B (chi tiết cơ chế đã đọc trên bản HTML) |
| P14 | *Get my drift? Catching LLM Task Drift with Activation Deltas* | https://arxiv.org/pdf/2406.00799 | So activation trước và sau khi đọc dữ liệu ngoài; cần truy cập activation, chỉ để nêu | B |
| — | R5 mục 7 | (như R5) | MELON tốn khoảng 192% thời gian, 213% token so với baseline; không cải thiện với tấn công logic | A |

## 5. Vật liệu và công cụ

| Loại | Tên | Ghi chú | Người dùng |
|---|---|---|---|
| Model chính | Qwen3-8B qua Ollama (`ollama pull qwen3:8b`) | Tắt chế độ thinking khi đo | Thành, cả nhóm |
| Model chéo | GLM qua OpenRouter | Free tier giới hạn lượt gọi; chỉ chạy hold-out một lần, làm nếu còn thời gian | Nam |
| Model L2 | Prompt Guard 2; dự phòng ProtectAI deberta | Xin quyền ngày 05/10 | Ngọc |
| Embedding (L4) | `sentence-transformers` | Đã có trong `requirements.txt` | Nam, Thành |
| Thống kê | `statsmodels.stats.proportion.proportion_confint(k, n, method="wilson")`, `pandas` | Khoảng tin cậy Wilson 95%, bảng cộng dồn | Minh |
| Dữ liệu nội bộ | `attack_prompts/train_prompts.json` (48), `holdout_prompts.json` (24) | Có `SECRET_CANARY` làm đáp án; sẽ chuyển sang schema v2 | Hương |
| Tài liệu nội bộ | `docs/ke-hoach-1-thang.tex`, `docs/Nhom4_Bao_cao_tien_do_20261002.pdf`, `docs/khao-sat-prompt-injection.md` | Kế hoạch, báo cáo tiến độ, khảo sát | Minh |
| Quy tắc | `CONTRIBUTING.md`, `README.md` | Commit, nhánh, PR | Cả nhóm |

## 6. Mục báo cáo cần trích tài liệu nào

| Mục báo cáo | Tài liệu |
|---|---|
| Giới thiệu và bài toán | R1, R6 (phân biệt jailbreak với injection) |
| Mô hình đe doạ | R2, R4 |
| Phân loại tấn công và bộ prompt | R1, R3, R7–R10, D1–D9 (nguồn từng mẫu) |
| Phòng thủ L1, L2 | P1–P7 |
| Phòng thủ L3 | P8, D1, R1; trích P9–P12 như hướng nâng cao |
| Phòng thủ L4 | P13, P14, R5 |
| Thước đo và thiết lập | R1, D3 (cách đo ASR kèm utility) |
| Thảo luận và hạn chế | R5 (không có phòng thủ hoàn hảo, over-defense, tác vụ tĩnh), R1 (hạn chế: thiếu cơ chế phục hồi) |

## 7. Việc còn phải kiểm tra

1. Mở trang từng bài mức B, điền tên tác giả (đặc biệt P1, P2, P8–P14, D1–D4, R4, R7–R10) và đối chiếu số liệu trước khi trích.
2. Dataset Hugging Face (D5–D8): ghi số mẫu, giấy phép, ngày truy cập.
3. Prompt Guard 2: ghi giấy phép và giới hạn độ dài đầu vào từ model card.
4. Link của MELON: lấy link mã nguồn từ trang bài nếu muốn tham khảo cách cài đặt.
5. Khi viết BibTeX, dùng khoá dạng `liu2024formalizing`, `greshake2023indirect`, `wang2026landscape`.
