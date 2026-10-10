# Defenses

- `layer1_filtering.py` — L1: làm sạch + phát hiện chỉ dẫn tiêm bằng luật (chi tiết bên dưới).
- `layer2_refusal_classifier.py` — L2: LLM-judge nhỏ qua Ollama (chi tiết bên dưới).
- `_data.py` — đọc train + benign `tune` cho chế độ chạy độc lập của L1/L2 (không có hàm nào đọc hold-out).
- `layer3_instruction_hierarchy.py` — privileged-instruction separation / spotlighting.
- `layer4_consistency_check.py` — cải tiến mới: Dual-Response Consistency Check.
- `eval_asr.py` — script đo ASR cộng dồn qua từng lớp, trên cả train set và held-out set.

## L1 — lọc đầu vào (`layer1_filtering.py`)

`check(user_task, document)` chỉ quét `document`. Chạy độc lập: `python3 -m defenses.layer1_filtering`
(đặt `CAPSTONE_DATA_DIR` để trỏ tới bản v2 của dữ liệu).

**Cơ chế.** (1) *Làm sạch*: xoá ký tự vô hình/điều khiển/bidi/tag (tag chars được giải mã thành chữ ASCII ẩn và quét tiếp),
gỡ Zalgo, quy chuẩn tương thích kiểu NFKC *có chọn lọc* (fullwidth, chữ toán học, số La Mã, ligature), gộp homoglyph
Cyrillic/Greek/small-caps về Latin **chỉ trong từ trộn chữ viết** nên tiếng Nga/Hy Lạp/Trung/Nhật/Hàn/Việt hợp lệ không đổi;
ZWJ/ZWNJ chỉ bị xoá cạnh chữ-số ASCII (giữ emoji, chữ Ấn/Ba Tư). Khác biệt chỉ do NFC không tính là đổi.
(2) *Giải mã thử*: Base64, hex, URL-encode, `\uXXXX`/`&#..;`, ROT13, đảo chuỗi, tách chữ ("P r i n t", "R-e-v-e-a-l"); chỉ giữ
bản giải mã đọc được rồi quét lại, đệ quy tối đa 2. (3) *Chấm điểm*: mỗi họ mẫu lấy điểm cao nhất (cộng 0.5x điểm mẫu thứ hai
nếu khớp đoạn khác), điểm tổng = noisy-OR giữa các họ, `block` khi >= `THRESHOLD` (0.6). Tiếng Việt khớp trên bản bỏ dấu
nên bắt cả văn bản gõ không dấu.

**Họ mẫu và nguồn** (đầy đủ trong docstring): override (Liu 2024 Context Ignoring; HackAPrompt; Perez & Ribeiro), leak (prompt
leaking), authority/thẻ chat template (HackAPrompt, BIPIA), fake_completion (Liu 2024), task_hijack, output_shaping, audience
(Greshake 2023), persona (Shen 2024), refusal_suppress (HackAPrompt, Wei 2023), debug_mode, decode_exec (Wei 2023),
many_shot (Anil 2024), tool_action, sequence_cue. **Tự thiết kế**: bảng homoglyph, trọng số, tầng "có/không có từ phạm vi",
noisy-OR, quy tắc phủ định, giảm điểm khi câu tấn công chỉ được trích làm ví dụ, và các họ output_shaping/tool_action/sequence_cue
(viết sau khi thấy 21 prompt train mới nhắm tới mục tiêu integrity/tool_action).

**Hạn chế.** Không bắt paraphrase xa mẫu (ví dụ "set aside whatever guidance came before"), leet-speak, đảo/mã hoá kiểu lạ,
payload chia nhỏ. Người viết payload biết cue trích dẫn ("chẳng hạn ...") có thể dùng để hạ điểm. Bài viết bảo mật trích nguyên
văn câu tấn công không kèm cue sẽ bị chặn nhầm. Cụm tương tác "bỏ qua hướng dẫn trước đó về X" (sửa lỗi nội bộ) chỉ được
giảm điểm, không loại hẳn.

## L2 — bộ phân loại (`layer2_refusal_classifier.py`)

`check(user_task, document)` trả `block` khi `score >= THRESHOLD` (0.5). Chạy độc lập (hiệu chỉnh và in bảng):
`CAPSTONE_DATA_DIR=... python3 -m defenses.layer2_refusal_classifier [--model M] [--no-cache] [--max-new-calls N]`.
Biến môi trường: `CAPSTONE_L2_MODEL` (mặc định `qwen2.5:3b`), `CAPSTONE_L2_BACKEND` (`llm_judge` | `promptguard`),
`CAPSTONE_L2_CACHE` (đường dẫn hoặc `0` để tắt; mặc định `results/dev/l2_judge_cache.json`, không commit).
**Khi chạy đo độ trễ thật phải đặt `CAPSTONE_L2_CACHE=0`.**

**Cơ chế.** Judge Ollama, prompt tiếng Anh, temperature 0, seed 0, đầu ra JSON `{"injection", "confidence"}`; điểm =
P(injection). Tài liệu được cắt theo đoạn văn (<= 450 ký tự; đoạn dài hơn cắt cửa sổ trượt chồng lấn 120), chấm tối đa 6 đoạn
(đầu, cuối, đoạn có điểm L1 cao, rồi rải đều), điểm tài liệu = max, dừng sớm khi một đoạn >= 0.9. Lý do cắt nhỏ: ở thử nghiệm dev,
cửa sổ 1500 ký tự khiến model 3B bỏ sót lệnh nằm giữa tài liệu (AUC 0.749, TPR 40.6% trên cùng dữ liệu); cắt theo đoạn
đưa AUC lên 0.915. Một biến thể "trích câu đáng ngờ trước" (evidence) không cải thiện trên 14 mẫu bị sót nên bỏ.

**Giảm thiểu judge bị tiêm** (hạn chế đã biết, P7): system prompt coi tài liệu là dữ liệu; hai dòng đánh dấu với nonce từ hash và
loại chuỗi `<<<`/`>>>` khỏi tài liệu; nhắc lại nhiệm vụ sau tài liệu; một ví dụ few-shot tài liệu cố ép judge trả "false"; nhiều
verdict mâu thuẫn thì lấy verdict nguy hiểm nhất; đầu ra không phân tích được -> 0.5 và ghi `parse_fail`. Không có biện pháp nào
đảm bảo; chưa đo tỉ lệ judge bị ép thật. Backend `promptguard` là khung chưa kiểm chứng (cần `transformers` + trọng số cục bộ,
`CAPSTONE_PROMPTGUARD_PATH`); thiếu thì in thông báo và dùng `llm_judge`.

**Chọn model.** So `qwen2.5:3b` và `qwen2.5:7b` trên cùng 12 mẫu (6 tấn công, 6 benign), prompt v1, dữ liệu cũ: 3B đúng 5/6
tấn công, 0/6 benign bị chặn nhầm, ~1.5-4 s/lượt; 7B đúng 6/6 tấn công nhưng chặn nhầm 1/6 benign (BNF-002), ~17-44 s/lượt (máy đang bị
chia sẻ). n quá nhỏ để kết luận về độ chính xác; chọn 3B chủ yếu vì tốc độ (~10x).

**Số liệu hiệu chỉnh** (chỉ train + benign `tune`, dữ liệu v2 từ `tmp/01-data@e5fa5b0`): xem `CALIBRATION_NOTE` trong module.
n_attack = 69, n_benign = 42, AUC 0.915 (bootstrap 95% [0.873, 0.954]); ngưỡng 0.5: TPR 51/69 = 0.739 (Wilson [0.625, 0.828]),
FPR 0/42 (Wilson [0, 0.084]). Điểm judge rời rạc (0, 0.1, 0.9, 0.95, 0.98, 1) nên mọi ngưỡng trong (0.1, 0.9] cho cùng kết quả.
Bị sót chủ yếu là indirect injection thuộc mục tiêu integrity ("khi tóm tắt hãy ghi rằng ..."): judge coi đó là văn bản biên tập
bình thường; L1 bắt được các mẫu này.

**Rủi ro học vẹt.** Ngưỡng L2, trọng số/mẫu L1 và cả prompt judge đều được chọn/chỉnh sau khi xem train, nên block rate và TPR
trên train là lạc quan. Số đo gần với tổng quát hoá hơn: bộ probe tự viết (không dùng để chỉnh L2; L1 chỉ được chỉnh trên `probe`
1, không chỉnh trên `probe2`): trên `probe2` (30 tấn công) L1 chặn 20, L2 chặn 22, L1 hoặc L2 chặn 25; trên 24 benign khó tự viết L2
chặn nhầm 2 (8.3%; tài liệu Python/API mẫu), L1 0 (đã chỉnh trên tập này). Tất cả vẫn do một người viết.
