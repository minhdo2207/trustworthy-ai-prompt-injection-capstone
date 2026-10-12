# Tài liệu chưa kiểm chứng đủ, KHÔNG trích trong báo cáo (cập nhật 10/2026)

Quy ước: mục nào trong `refs.bib` đều đã đối chiếu tác giả/năm/nơi đăng/arXiv ID với trang arXiv
(API `export.arxiv.org`) hoặc trang hội nghị. Các mục dưới đây chưa đạt mức đó nên bị bỏ khỏi báo cáo
hoặc chỉ được ghi ở mức tối thiểu.

## Không trích (chưa kiểm chứng được)
- ProtectAI `deberta-v3-base-prompt-injection-v2` (P4 trong `docs/tai-lieu-tham-khao.md`): chỉ có link tới trang
  PromptLayer (bên thứ ba), chưa đọc model card gốc để lấy tác giả, giấy phép, số liệu.
- Số liệu "Yong và cs.: 79% trên AdvBench" và "many-shot: hiệu quả tăng theo luật luỹ thừa" (từ
  `docs/khao-sat-prompt-injection.md`, mức B): chưa đối chiếu bản gốc nên không đưa số vào báo cáo.
- Số liệu "sandwich làm PNA-T giảm 0,38 -> 0,24" của Liu và cs. (ghi trong `docs/tai-lieu-tham-khao.md`, mức A
  nhưng thiếu ngữ cảnh mô hình/tác vụ): báo cáo chỉ nêu định tính, không nêu số.
- Claim "MELON báo cáo ASR 0,32% trên GPT-4o": không trích (không có trong abstract; chưa đọc bảng kết quả).

## Trích nhưng ghi mức thấp hơn đầy đủ
- Greshake và cs. 2023: chỉ ghi arXiv. Nơi đăng AISec '23 (ACM) chỉ thấy qua các bài khác trích dẫn, chưa thấy trang ACM.
- Wallace và cs. 2024 (Instruction Hierarchy), Hines và cs. 2024 (Spotlighting), Alon & Kamfonas 2023, Jain và cs. 2023,
  Debenedetti và cs. 2025 (CaMeL), Wang và cs. 2026, Xu & Parhi 2025, Li và cs. 2024 (GenTel-Safe, InjecGuard),
  Hung và cs. 2024, Choudhary và cs. 2025: chỉ ghi preprint arXiv (trường comment của arXiv không nêu nơi đăng).
- Many-shot Jailbreaking (Anil và cs., NeurIPS 2024): danh sách tác giả trên trang NeurIPS có vẻ có lỗi chính tả
  (hai tên); bib chỉ ghi 6 tác giả đầu + "others".
- AgentDojo: bài báo nhóm đối chiếu ghi 97 tác vụ / 629 ca bảo mật; kết quả tìm kiếm cho thấy phiên bản sau/trang bộ dữ liệu
  ghi số khác (124 tác vụ). Báo cáo ghi chú "theo bản nhóm đã đối chiếu".
- Qwen2.5 Technical Report: trường tác giả trên arXiv có ký tự "Qwen" làm tác giả đầu; bib ghi `{Qwen Team}`.
- Llama Prompt Guard 2: chỉ có model card trên Hugging Face (không có bài báo); đã đọc trang 10/2026 (giấy phép
  Llama 4 Community License, cửa sổ 512 token, gated).

## Bộ dữ liệu ở phụ lục C (đã đọc trang Hugging Face 10/2026, chưa tải)
- deepset/prompt-injections: Apache-2.0; 546 train + 116 test; ngôn ngữ không ghi tag.
- Lakera/gandalf_ignore_instructions: MIT; 777/111/112; en.
- jackhhao/jailbreak-classification: Apache-2.0; 1.306 dòng; nhãn jailbreak/benign.
- xTRam1/safe-guard-prompt-injection: trang không ghi giấy phép; 8,24k train + 2,06k test.
Chưa có mẫu nào từ các bộ này được xác nhận đã đưa vào `attack_prompts/` (cần Hương xác nhận trường `source`).
