# Attack Prompts — phụ trách: Hương

Bộ prompt tấn công tự xây (~60-80 prompt), chia nhóm:

1. Direct injection (đưa thẳng vào query)
2. Indirect injection (giấu trong "document" agent phải tóm tắt)
3. Jailbreak roleplay/DAN-style
4. Code-switching / dịch ngôn ngữ khác để né filter
5. Obfuscation (base64, ký tự Unicode giả)
6. Many-shot jailbreaking (nhồi nhiều ví dụ giả trước câu lệnh thật)

Chia thành 2 file: `train_prompts.json` (dùng để thiết kế defense) và `holdout_prompts.json` (giữ lại để test generalization, không dùng khi tinh chỉnh defense).

Mỗi prompt ghi rõ: nội dung, loại tấn công, mục tiêu (leak system prompt / đổi hành vi / bypass refusal...).
