"""defenses/layer1_filtering.py — L1: làm sạch + phát hiện chỉ dẫn tiêm vào bằng luật.

Giao diện (docs/hop-dong-chung.md mục 2): ``check(user_task, document) -> LayerResult``.
L1 chỉ nhìn ``document``; ``user_task`` là kênh tin cậy nên không bị quét.

Quy trình
---------
1. **Làm sạch** (``normalize``): xoá ký tự vô hình/điều khiển/bidi/tag, gỡ Zalgo,
   quy chuẩn tương thích kiểu NFKC *có chọn lọc* cho chữ Latin, gộp homoglyph
   Cyrillic/Greek/small-caps -> Latin theo **từ trộn chữ viết**. Tài liệu đổi thật sự
   -> ``sanitize``. Khác biệt chỉ do NFC (tiếng Việt tổ hợp) không tính là đổi.
2. **Giải mã thử** (``_decoded_views``): Base64, hex, URL-encode, ``\\uXXXX``/``&#..;``,
   ROT13, đảo chuỗi, tách chữ ("P r i n t", "R-e-v-e-a-l"), tag chars ẩn. Nếu ra văn
   bản đọc được thì quét lại bằng cùng bộ phát hiện, đệ quy tối đa ``MAX_DEPTH`` = 2.
3. **Chấm điểm** (``scan``): mỗi *họ mẫu* có điểm cao nhất trong họ; điểm tổng
   = ``1 - prod(1 - điểm_họ)`` (noisy-OR). ``score >= THRESHOLD`` -> ``block``.

Họ mẫu và nguồn (không có mẫu nào là chuỗi nguyên văn của một prompt train; mỗi mẫu
là một *họ cấu trúc*: động từ + đối tượng, có tầng "có/không có từ chỉ phạm vi")
------------------------------------------------------------------------------
- ``override``      động từ ghi đè/bỏ qua + chỉ dẫn/quy tắc. Nguồn: Liu 2024 "Context
                    Ignoring" (R1), HackAPrompt "Context Overflow/Ignore" (R3), Perez &
                    Ribeiro 2022 "ignore previous prompt" (R4). Tầng điểm: có từ phạm vi
                    (previous/above/all/your/trước đó/toàn bộ...) cao; không có thì thấp.
- ``leak``          động từ tiết lộ/in/lặp + system prompt/canary/cấu hình. Nguồn: R4
                    "prompt leaking"; HackAPrompt "system prompt leak".
- ``authority``     giả danh quyền lực/định dạng hệ thống: ``[SYSTEM]``, "SYSTEM
                    OVERRIDE", "tôi là quản trị viên", "developer message", thẻ chat
                    template. Nguồn: HackAPrompt, BIPIA (D1). Phần lớn là TỰ THIẾT KẾ.
- ``fake_completion`` "Answer: task complete" rồi chỉ dẫn mới. Nguồn: Liu 2024 "Fake
                    Completion" và "Combined".
- ``task_hijack``   "bỏ/đừng tóm tắt", "thay vì ...", "trước khi tóm tắt hãy ...".
- ``output_shaping`` "bản tóm tắt phải khẳng định ...". Mục tiêu integrity. TỰ THIẾT KẾ.
- ``audience``      lời nhắn gửi AI trong tài liệu ("Note to AI", "Chỉ dẫn cho AI",
                    "<!-- AI: ... -->"). Nguồn: Greshake 2023 (R2) indirect injection.
- ``persona``       DAN/đóng vai không giới hạn/developer mode. Nguồn: Shen 2024 (R7).
- ``refusal_suppress`` "không từ chối", "tạm bỏ bước từ chối". Nguồn: R3 "Refusal
                    Suppression", Wei 2023 (R9).
- ``debug_mode``    "DEBUG_MODE=TRUE", "developer mode". TỰ THIẾT KẾ.
- ``decode_exec``   "giải mã/ROT13/Base64 rồi thực hiện". Nguồn: R9 (mismatched
                    generalization), R3 "Obfuscation".
- ``many_shot``     nhiều lượt User/Assistant lặp trong *tài liệu*. Nguồn: Anil 2024 (R10).
- Lặp: mẫu mạnh khớp >= 3 lần cộng thêm điểm (dấu hiệu many-shot/nhồi). TỰ THIẾT KẾ.

Đa ngôn ngữ: Việt (so khớp trên bản **bỏ dấu** để cùng lúc bắt tiếng Việt có dấu và
gõ không dấu), Anh, Trung, Nhật, Hàn, Nga; thêm Pháp/Tây Ban Nha/Đức ở mức nhẹ (nhóm
code-switching trong train có các ngôn ngữ này nên đã thêm; ghi rõ để không coi đây là
độ tổng quát được chứng minh).

Giảm chặn nhầm (benign có hard negatives)
-----------------------------------------
- Từ khoá đơn lẻ ("system prompt", "canary", "Base64") điểm rất thấp hoặc không có.
- Cần động từ mệnh lệnh *nhắm vào mô hình* đứng cạnh đối tượng chỉ dẫn/hệ thống.
- Phủ định ("do not ignore ...") bị loại bằng lookbehind.
- Ví dụ trích dẫn ("chẳng hạn \"ignore previous ...\"") giảm điểm x ``QUOTE_DISCOUNT``
  trừ khi ngay sau đó có "rồi thực hiện/làm theo".
- Giải mã ra văn bản vô hại (khoá API, mã băm, URL-encode tên tiếng Việt) -> bỏ qua.

Hạn chế đã biết: không bắt được diễn đạt lạ ngoài các họ trên (paraphrase mạnh), văn
bản đảo/mã hoá kiểu khác, hay payload chia nhỏ qua nhiều tài liệu; bài viết bảo mật
trích nguyên văn câu tấn công không kèm cue trích dẫn sẽ bị chặn nhầm.

Chọn THRESHOLD: giá trị tiên nghiệm 0.6 (một mẫu mạnh >= 0.7 tự chặn; hai tín hiệu yếu
~0.35-0.45 cộng lại mới chặn), sau đó kiểm tra trên train + benign `tune`
(xem ``python -m defenses.layer1_filtering``). Ngưỡng và trọng số có nhìn train nên
tỉ lệ chặn trên train là lạc quan; chỉ hold-out mới đo được tổng quát hoá.
"""
from __future__ import annotations

import base64
import binascii
import codecs
import html
import re
import time
import unicodedata
import urllib.parse
from dataclasses import dataclass
from typing import Iterable, Optional

try:  # chạy được cả khi import như script lẻ
    from defenses.base import LayerResult
except ImportError:  # pragma: no cover
    from base import LayerResult  # type: ignore

THRESHOLD = 0.6
MAX_DEPTH = 2
MAX_SCAN_CHARS = 60_000
CORROBORATION = 0.5
QUOTE_DISCOUNT = 0.35
SCOPED_DISCOUNT = 0.45
REPEAT_BONUS = 0.15
MIN_B64_LEN = 20
MIN_DECODED_CHARS = 8

# ---------------------------------------------------------------------------
# 1. Làm sạch
# ---------------------------------------------------------------------------
_ALWAYS_DROP = (
    {0x00AD, 0x034F, 0x061C, 0x115F, 0x1160, 0x17B4, 0x17B5, 0x180E, 0x3164,
     0xFEFF, 0xFFA0, 0x200B, 0x200E, 0x200F}
    | set(range(0x202A, 0x202F))      # bidi embedding/override
    | set(range(0x2060, 0x2065))      # word joiner, invisible operators
    | set(range(0x2066, 0x206A))      # bidi isolates
    | set(range(0x206A, 0x2070))      # deprecated format chars
    | set(range(0xE0100, 0xE01F0))    # variation selectors supplement
    | set(range(0x80, 0xA0))          # C1 controls
    | set(range(0x0334, 0x0339))      # combining overlays (gạch ngang/chéo kiểu strikethrough)
)
_KEEP_CONTROLS = {"\t", "\n", "\r"}
_COMBINING = "̀-ͯ᪰-᫿᷀-᷿⃐-⃿︠-︯"
_ZALGO_RE = re.compile(rf"([^\W_])[{_COMBINING}]{{3,}}")

# bảng homoglyph tự viết (Cyrillic/Greek giống Latin); chỉ áp dụng trong từ trộn chữ
_CYR = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i",
    "ј": "j", "ѕ": "s", "һ": "h", "ԁ": "d", "ԛ": "q", "ԝ": "w", "ӏ": "l",
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P",
    "С": "C", "Т": "T", "Х": "X", "У": "Y", "І": "I", "Ј": "J", "Ѕ": "S",
}
_GRK = {
    "ο": "o", "ν": "v", "ι": "i", "ρ": "p", "α": "a", "ε": "e", "κ": "k", "υ": "u",
    "χ": "x", "τ": "t",
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M",
    "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X",
}
_HOMOGLYPH = {**_CYR, **_GRK}
_SMALLCAP = dict(zip("ᴀʙᴄᴅᴇɢʜᴊᴋʟᴍɴᴏᴘꜱᴛᴜᴠᴡᴢɪʀʏꜰ", "abcdeghjklmnopstuvwziryf"))
_EN_TRIGGER_WORDS = {
    "ignore", "system", "prompt", "secret", "reveal", "instructions", "instruction",
    "override", "bypass", "password", "admin", "developer", "disregard", "forget",
    "previous", "restrictions", "canary", "print", "output",
}
# vùng ký tự tương thích Latin mà NFKC trả về chữ/số ASCII (an toàn để quy chuẩn)
_COMPAT_RANGES = (
    (0xFF10, 0xFF19), (0xFF21, 0xFF3A), (0xFF41, 0xFF5A),  # fullwidth
    (0x1D400, 0x1D7FF),                                    # math alphanumeric
    (0xFB00, 0xFB06),                                      # ligature
)
_COMPAT_IF_LATIN_NEIGHBOR = (
    (0x2160, 0x217F), (0x24B6, 0x24E9), (0x1F130, 0x1F189), (0x2100, 0x214F),
)
_WORD_RE = re.compile(r"\w+", re.UNICODE)


def _in_ranges(cp: int, ranges: Iterable[tuple[int, int]]) -> bool:
    return any(lo <= cp <= hi for lo, hi in ranges)


def _is_ascii_alnum(ch: str) -> bool:
    return ch.isascii() and ch.isalnum()


def strip_invisible(text: str) -> tuple[str, int, str]:
    """Xoá ký tự vô hình. Trả (văn bản, số ký tự xoá, chữ ASCII ẩn trong tag chars).

    ZWJ/ZWNJ (U+200C/D) chỉ bị xoá khi nằm cạnh chữ/số ASCII: giữ nguyên trong
    chuỗi emoji và chữ Ấn/Ba Tư nơi chúng có nghĩa thật.
    """
    out: list[str] = []
    hidden: list[str] = []
    removed = 0
    n = len(text)
    for i, ch in enumerate(text):
        cp = ord(ch)
        if 0xE0000 <= cp <= 0xE007F:
            removed += 1
            if 0xE0020 <= cp <= 0xE007E:
                hidden.append(chr(cp - 0xE0000))
            continue
        if cp in _ALWAYS_DROP:
            removed += 1
            continue
        if cp in (0x200C, 0x200D):
            prev_c = text[i - 1] if i else ""
            next_c = text[i + 1] if i + 1 < n else ""
            if _is_ascii_alnum(prev_c) or _is_ascii_alnum(next_c):
                removed += 1
                continue
        if ch not in _KEEP_CONTROLS and unicodedata.category(ch) == "Cc":
            removed += 1
            continue
        out.append(ch)
    return "".join(out), removed, "".join(hidden)


def _fold_word(word: str) -> tuple[str, int, int]:
    """Quy chuẩn một từ. Trả (từ mới, số ký tự tương thích, số homoglyph)."""
    if word.isascii():
        return word, 0, 0
    has_ascii_letter = any(c.isascii() and c.isalpha() for c in word)
    compat = 0
    chars = []
    for c in word:
        cp = ord(c)
        if _in_ranges(cp, _COMPAT_RANGES) or (
            has_ascii_letter and _in_ranges(cp, _COMPAT_IF_LATIN_NEIGHBOR)
        ):
            folded = unicodedata.normalize("NFKC", c)
            if folded.isascii() and folded.isalnum():
                chars.append(folded)
                compat += 1
                continue
        chars.append(c)
    word = "".join(chars)

    letters = [c for c in word if c.isalpha()]
    latin = sum(1 for c in letters if c.isascii())
    lookalike = sum(1 for c in letters if c in _HOMOGLYPH)
    homo = 0
    if lookalike and latin and latin * 2 >= len(letters):
        word = "".join(_HOMOGLYPH.get(c, c) for c in word)
        homo = lookalike
    elif lookalike and not latin and len(letters) >= 4 and lookalike == len(letters):
        candidate = "".join(_HOMOGLYPH[c] for c in word if c in _HOMOGLYPH).lower()
        if candidate in _EN_TRIGGER_WORDS:
            word, homo = candidate, lookalike
    if len(letters) >= 4 and all(c in _SMALLCAP for c in letters):
        word = "".join(_SMALLCAP.get(c, c) for c in word)
        homo += len(letters)
    return word, compat, homo


def fold_confusables(text: str) -> tuple[str, int, int]:
    """Quy chuẩn tương thích + gộp homoglyph theo từng từ. Trả (text, n_compat, n_homoglyph)."""
    if text.isascii():
        return text, 0, 0
    parts: list[str] = []
    last = 0
    n_compat = n_homo = 0
    for m in _WORD_RE.finditer(text):
        new, c, h = _fold_word(m.group())
        if c or h:
            parts.append(text[last:m.start()])
            parts.append(new)
            last = m.end()
            n_compat += c
            n_homo += h
    parts.append(text[last:])
    return "".join(parts), n_compat, n_homo


def normalize(text: str) -> tuple[str, dict]:
    """Làm sạch ``text``. Trả (văn bản sạch, ghi chú các biến đổi đã áp dụng).

    ``notes`` có khoá tuỳ chọn: ``invisible``, ``hidden_tag_text``, ``compat``,
    ``homoglyph``, ``zalgo``. Rỗng nghĩa là không đổi gì đáng kể (NFC không tính).
    """
    notes: dict = {}
    t, removed, hidden = strip_invisible(text)
    if removed:
        notes["invisible"] = removed
    if hidden:
        notes["hidden_tag_text"] = hidden
    t2, n_compat, n_homo = fold_confusables(t)
    if n_compat:
        notes["compat"] = n_compat
    if n_homo:
        notes["homoglyph"] = n_homo
    t3, n_zalgo = _ZALGO_RE.subn(r"\1", t2)
    if n_zalgo:
        notes["zalgo"] = n_zalgo
    t4 = unicodedata.normalize("NFC", t3)
    return t4, notes


def _vi_fold(text: str) -> str:
    """Bỏ dấu tiếng Việt + hạ chữ thường, để mẫu tiếng Việt viết không dấu."""
    d = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    return "".join(c for c in d if unicodedata.category(c) != "Mn").lower()


# ---------------------------------------------------------------------------
# 2. Họ mẫu
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Pattern:
    family: str
    name: str
    weight: float
    rx: re.Pattern
    view: str = "text"   # "text" (NFKC, nguyên dấu) hoặc "vi" (bỏ dấu, chữ thường)


@dataclass
class Hit:
    family: str
    name: str
    weight: float
    snippet: str
    source: str = "plain"    # plain | base64 | hex | rot13 | ...

    def tag(self) -> str:
        src = "" if self.source == "plain" else f"@{self.source}"
        return f"{self.family}:{self.name}{src}"


_F = re.I | re.S
_PATTERNS: list[Pattern] = []


def _add(family: str, name: str, weight: float, regex: str,
         view: str = "text", flags: int = _F) -> None:
    _PATTERNS.append(Pattern(family, name, weight, re.compile(regex, flags), view))


def _words(lo: int, hi: int) -> str:
    return rf"(?:\w+\W+){{{lo},{hi}}}"


# --- override (Liu 2024 Context Ignoring; R3; R4) ---------------------------
_EN_OVR_V = r"(?<!not )(?<!n't )(?<!never )\b(?:ignore|disregard|forget|override|bypass|discard|abandon|neglect|skip|overrule|supersede|cancel|drop)\b"
_EN_Q = (r"(?:previous(?:ly)?|prior|above|earlier|preceding|former|original|initial|all|any|every|"
         r"your|safety|system|existing|current|those|these|my|past)")
_EN_OBJ_S = (r"(?:instructions?|directives?|prompts?|programming|guidelines?|rules?|commands?|"
             r"system\s+(?:message|prompt)|context|orders?)")
_EN_OBJ_W = r"(?:restrictions?|constraints?|limitations?|policies|safeguards?|filters?|guardrails?|safety|refusals?)"
_add("override", "en_q_strong", 0.85,
     rf"{_EN_OVR_V}\W+(?:\w+\W+){{0,2}}{_EN_Q}\W+(?:\w+\W+){{0,2}}{_EN_OBJ_S}\b")
_add("override", "en_q_weak_obj", 0.6,
     rf"{_EN_OVR_V}\W+(?:\w+\W+){{0,2}}{_EN_Q}\W+(?:\w+\W+){{0,2}}{_EN_OBJ_W}\b")
_add("override", "en_no_q", 0.38,
     rf"{_EN_OVR_V}\W+(?:the\W+|these\W+|any\W+)?{_EN_OBJ_S}\b")
_add("override", "en_bare_restrictions", 0.5,
     rf"{_EN_OVR_V}\W+(?:the\W+|all\W+)?(?:earlier\W+|previous\W+)?{_EN_OBJ_W}\b")
_add("override", "en_new_instructions", 0.45,
     r"\b(?:new|updated|revised|replacement)\s+(?:instructions?|rules?|directives?)\s*[:\-]|"
     r"\b(?:your\s+new\s+(?:task|instructions?|rules?)\s+(?:is|are)|from\s+now\s+on\s*,?\s+(?:you|ignore|only|always|never|do))\b")
_add("override", "en_instead", 0.45,
     r"\b(?:instead|rather)\b[^.\n]{0,25}\b(?:reveal|print|output|say|write|reply|respond|tell|show|display|leak)\b")

_VI_V = r"(?:bo\s+qua|phot\s+lo|quen\s+(?:het\s+)?|vo\s+hieu\s+hoa|huy\s+bo|huy|tam\s+bo|go\s+bo|bo\s+di|khong\s+(?:can\s+)?(?:tuan\s+theo|lam\s+theo|theo)|dung\s+(?:tuan|lam)\s+theo|(?<![a-z])bo(?=\s+(?:tat\s+ca|toan\s+bo|moi|cac|quy|chi|huong|luat|buoc\s+tu\s+choi|co\s+che)))"
_VI_Q = r"(?:truoc\s+do|o\s+tren|phia\s+tren|truoc\s+day|toan\s+bo|tat\s+ca|moi|cu|giu\s+kin|tu\s+choi|an\s+toan|bao\s+mat|cua\s+ban|he\s+thong|ban\s+dau|hien\s+tai|hien\s+hanh)"
_VI_OBJ_S = r"(?:chi\s+dan|huong\s+dan|quy\s+tac|luat|lenh|yeu\s+cau|chi\s+thi|prompt|loi\s+nhac|cau\s+lenh)"
_VI_OBJ_W = r"(?:gioi\s+han|han\s+che|rang\s+buoc|chinh\s+sach|bo\s+loc|co\s+che\s+tu\s+choi|buoc\s+tu\s+choi|quy\s+dinh)"
_add("override", "vi_q_strong", 0.85,
     rf"{_VI_V}\s+(?:\w+\s+){{0,3}}{_VI_OBJ_S}\s+(?:\w+\s+){{0,2}}{_VI_Q}|"
     rf"{_VI_V}\s+(?:\w+\s+){{0,3}}{_VI_Q}\s+(?:\w+\s+){{0,2}}{_VI_OBJ_S}", "vi")
_add("override", "vi_q_weak_obj", 0.6,
     rf"{_VI_V}\s+(?:\w+\s+){{0,3}}{_VI_OBJ_W}|"
     rf"{_VI_V}\s+(?:\w+\s+){{0,3}}{_VI_OBJ_S}\s+(?:\w+\s+){{0,2}}(?:giu\s+kin|bao\s+mat)", "vi")
_add("override", "vi_no_q", 0.38, rf"{_VI_V}\s+(?:cac\s+|nhung\s+|may\s+)?{_VI_OBJ_S}\b", "vi")
_add("override", "vi_new", 0.45,
     r"(?:quy\s+tac|chi\s+dan|huong\s+dan)\s+moi\s*[:\-]|tu\s+(?:gio|bay\s+gio)\s+(?:tro\s+di\s+)?(?:ban|may|hay)\b", "vi")

_add("override", "zh", 0.85,
     r"(?:忽略|无视|忽视|忘记|忘掉|绕过|不要遵守|不用遵守|无需遵守|覆盖|取消)(?:掉)?(?:你的|您的|以上|之前|先前|上述|前面|所有|任何|原有|现有|此前|全部|以往)+(?:的)?(?:所有|全部)?(?:指令|指示|说明|规则|限制|提示|设定|命令|约束|安全)")
_add("override", "zh_bare", 0.4,
     r"(?:忽略|无视|忘记|绕过)(?:掉)?(?:指令|规则|限制|约束|安全规则)")
_add("override", "ja", 0.85,
     r"(?:以前|これまで|上記|前|すべて|全て|あらゆる|既存|元)の?(?:指示|命令|ルール|制限|指令|プロンプト|設定)(?:を|は)?(?:すべて|全て|全部)?(?:無視|忘れ|破棄|無効|取り消)|"
     r"(?:指示|命令|ルール|制限)を(?:すべて|全て)?(?:無視|無効にし|忘れ)")
_add("override", "ko", 0.85,
     r"(?:이전|위의|앞의|기존|모든|이전의|원래)\s*(?:지시|지침|명령|규칙|제한|프롬프트|설정)\w*\s*(?:을|를|은|는)?\s*(?:모두\s*)?(?:무시|잊|따르지\s*마|무효|어기)|"
     r"(?:지시|지침|규칙|제한)\w*\s*(?:을|를)?\s*(?:모두\s*)?(?:무시|무효)")
_add("override", "ru", 0.85,
     r"(?:игнорир\w+|забудь\w*|отмени\w*|пренебреги\w*|не\s+следуй\w*|отбрось\w*)\s+(?:\w+\s+){0,3}(?:инструкци\w+|правил\w+|указани\w+|ограничени\w+|команд\w+|запрет\w+|подсказк\w+|установк\w+)")
_add("override", "fr", 0.8,
     r"\b(?:ignore[zr]?|oublie[zr]?|n['’]?ob[eé]is\s+pas)\s+(?:\w+\s+){0,3}(?:instructions?|consignes?|r[eè]gles?|restrictions?)\s+(?:\w+\s+){0,2}(?:pr[eé]c[eé]dentes?|ant[eé]rieures?|ci-dessus)|"
     r"\b(?:ignore[zr]?|oublie[zr]?)\s+(?:les\s+|toutes?\s+les\s+|tes\s+|vos\s+)(?:instructions?|consignes?|r[eè]gles?|restrictions?)\b")
_add("override", "es", 0.8,
     r"\b(?:ignora|ignore|olvida|omite|desobedece)\s+(?:\w+\s+){0,3}(?:instrucciones|reglas|restricciones|indicaciones|directrices)\s+(?:\w+\s+){0,2}(?:anteriores|previas|de\s+arriba)|"
     r"\b(?:ignora|olvida|omite)\s+(?:las\s+|todas\s+las\s+|tus\s+)(?:instrucciones|reglas|restricciones)\b|"
     r"\b(?:ignora|olvida)\s+(?:las\s+)?(?:restricciones|reglas)\s+anteriores\b")
_add("override", "de", 0.8,
     r"\b(?:ignoriere|ignorieren|vergiss|missachte)\w*\s+(?:\w+\s+){0,3}(?:anweisungen|instruktionen|regeln|einschr[aä]nkungen|vorgaben|befehle)")

# --- leak (R4 prompt leaking) -----------------------------------------------
_EN_POS = (r"(?:^|[.!?:;\n,\"'(\[\]>/\-–—]\s*|\b(?:please|kindly|then|and|now|just|also|first|next|instead|must|should|will|shall|"
           r"can|could|would|immediately|always|simply|by|you\s+to)\s+)")
_EN_LEAK_V = (_EN_POS + r"(?:reveal|print|show|display|output|repeat|echo|leak|disclose|expose|dump|tell|give|return|"
              r"reproduce|recite|share|provide|send|spill|translate|summari[sz]e|read|list|copy|quote|"
              r"write\s+out|paste|divulge|emit|expos)\w*")
_EN_T_SYS = (r"(?:(?:system|initial|hidden|secret|internal|original|developer|underlying|base|pre)[\s-]*"
             r"(?:prompt|message|instructions?|configuration|config|rules|directive)s?)")
_EN_T_YOUR = (r"(?:(?:your|its)\s+(?:\w+\s+)?(?:prompt|instructions?|configuration|config|rules|guidelines|"
              r"programming|settings|secrets?|credentials|api\s*keys?|keys?|training))")
_EN_T_SECRET = (r"(?:(?:the\s+)?(?:secret|confidential|hidden)\s+(?:value|token|key|code|string|word|flag|password|canary)s?|"
                r"(?:api\s+)?(?:token|key|password|credential|secret)s?\s+(?:you\s+(?:were|are|have\s+been)\s+given|given\s+to\s+you|you\s+(?:hold|have|know))|"
                r"(?<![a-z])canary(?![a-z]*\s+(?:deploy|release|build|test|rollout|group|user))[a-z_]*)")
_EN_QUAL = r"(?:actual|real|true|verbatim|exact|full|complete|entire|current|raw|literal|word[\s-]for[\s-]word)"
_add("leak", "en_your", 0.8, rf"{_EN_LEAK_V}\W+(?:\w+\W+){{0,5}}{_EN_T_YOUR}")
_add("leak", "en_sys_qual", 0.78, rf"{_EN_LEAK_V}\W+(?:\w+\W+){{0,5}}{_EN_QUAL}\W+(?:\w+\W+){{0,3}}(?:{_EN_T_SYS}|{_EN_T_SECRET}|value)")
_add("leak", "en_sys", 0.5, rf"{_EN_LEAK_V}\W+(?:\w+\W+){{0,4}}{_EN_T_SYS}")
_EN_SECRET_V = (r"(?:" + _EN_POS + r"(?:complete|fill|finish|insert|include|append|add|put|use|enter|type|say|state|exfiltrate|"
                r"respond\s+with|answer\s+with|reply\s+with|write)\b|" + _EN_LEAK_V + ")")
_add("leak", "en_secret", 0.7, rf"{_EN_SECRET_V}\W+(?:\w+\W+){{0,5}}{_EN_T_SECRET}")
_add("leak", "en_real_value_cfg", 0.6,
     r"\b(?:real|actual|true|secret)\s+(?:value|key|token|password)\b[^.\n]{0,40}\b(?:in|from)\s+(?:your|the)\s+(?:config\w*|system|session|environment|prompt)\b")
_add("leak", "en_your_prompt_ref", 0.4,
     r"\byour\s+(?:own\s+)?(?:system\s+(?:prompt|message)|hidden\s+(?:instructions|prompt)|initial\s+(?:instructions|prompt)|secret\s+\w+)\b")
_add("leak", "vi_your_prompt_ref", 0.4,
     r"\b(?:system\s+prompt|prompt\s+he\s+thong|thong\s+diep\s+he\s+thong|chi\s+dan\s+(?:noi\s+bo|he\s+thong|an))\s+cua\s+(?:chinh\s+)?ban\b", "vi")
_add("leak", "en_question", 0.55,
     rf"\bwhat(?:'s|\s+is|\s+are|\s+were)\s+(?:your|the)\s+(?:\w+\s+)?(?:system\s+prompt|initial\s+(?:prompt|instructions)|hidden\s+(?:prompt|instructions)|secret\s+\w+)")
_add("leak", "en_verbatim_prompt", 0.6,
     r"\b(?:verbatim|word[\s-]for[\s-]word)\b[^.\n]{0,40}\b(?:system|prompt|instructions?)\b|\b(?:system|prompt|instructions?)\b[^.\n]{0,40}\bverbatim\b")

_VI_POS = (r"(?:^|[.!?;:\n,\"(]\s*|(?<=hay\s)|(?<=phai\s)|(?<=can\s)|(?<=se\s)|(?<=nen\s)|(?<=roi\s)|(?<=va\s)|(?<=ngay\s)|"
           r"(?<=xin\s)|(?<=long\s)|(?<=sau\s)|(?<=do\s)|(?<=la\s)|(?<=de\s)|(?<=viec\s)|(?<=buoc\s)|(?<=duoc\s)|(?<=phep\s)|"
           r"(?<=muon\s)|(?<=neu\s)|(?<=cach\s)|(?<=ban\s))")
_VI_LV = (_VI_POS + r"(?:(?:hay\s+)?in(?=\s+(?:ra|lai|nguyen|toan|gia|system|prompt|cau|ma|noi|chi|ban|tat))|"
          r"(?:xuat|tiet\s+lo|hien\s+thi|cung\s+cap|doc|sao\s+chep|lap\s+lai|nhac\s+lai|cong\s+khai|dich|cho\s+toi\s+biet|noi\s+cho|tra\s+ve|liet\s+ke|chep|gui|dua\s+ra|viet\s+ra|de\s+lo|tom\s+tat|bay\s+ra|trinh\s+bay)\b)")
_VI_T = (r"(?:system\s+prompt|prompt\s+he\s+thong|thong\s+diep\s+he\s+thong|(?:chi\s+dan|huong\s+dan|quy\s+tac)\s+(?:noi\s+bo|he\s+thong|an|goc|ban\s+dau|dang\s+(?:dieu\s+khien|ap\s+dung))|"
         r"cau\s+hinh\s+(?:cua\s+ban|that|goc|noi\s+bo|khoi\s+tao|an|bi\s+mat)|ma\s+noi\s+bo|gia\s+tri\s+(?:that|bi\s+mat)|[a-z_]*canary|"
         r"(?:gia\s+tri|ma|khoa|token|mat\s+khau)\s+bi\s+mat|prompt\s+(?:that|goc|cua\s+ban|noi\s+bo|nguyen\s+van)|tin\s+nhan\s+he\s+thong)")
_VI_QUAL = r"(?:that|thuc\s+te|nguyen\s+van|chinh\s+xac|day\s+du|toan\s+bo|hien\s+tai|goc|dang\s+ap\s+dung|dang\s+dieu\s+khien)"
_add("leak", "vi", 0.75, rf"{_VI_LV}\s+(?:\w+[,;]?\s+){{0,5}}{_VI_T}", "vi")
_add("leak", "vi_canary", 0.7, rf"(?:{_VI_LV}|{_VI_POS}(?:hoan\s+thanh|hoan\s+tat|dien|them|nhap|viet)\b)\s+(?:\w+[,;]?\s+){{0,5}}(?:[a-z_]*canary|gia\s+tri\s+[a-z_]*secret[a-z_]*)", "vi")
_add("leak", "vi_real_value_cfg", 0.6,
     r"\bgia\s+tri\s+(?:that|thuc\s+te|bi\s+mat)\b[^.\n]{0,30}\b(?:trong\s+(?:cau\s+hinh|phien|he\s+thong)|cua\s+ban)\b", "vi")
_add("leak", "vi_qual", 0.75,
     rf"{_VI_LV}\s+(?:\w+\s+){{0,4}}{_VI_QUAL}\s+(?:\w+\s+){{0,2}}(?:system\s+prompt|prompt|chi\s+dan|cau\s+hinh|gia\s+tri|ma)\b", "vi")
_add("leak", "vi_your", 0.75,
     r"(?:chi\s+dan|prompt|cau\s+hinh|quy\s+tac|huong\s+dan)\s+(?:\w+\s+){0,2}(?:cua\s+(?:chinh\s+)?ban|dang\s+dieu\s+khien\s+ban)\b[^.\n]{0,40}\b(?:in|doc|xuat|noi|cho)\b|"
     r"(?:in|xuat|doc|tiet\s+lo)\b[^.\n]{0,30}\b(?:chi\s+dan|prompt|cau\s+hinh|quy\s+tac)\s+(?:\w+\s+){0,2}cua\s+(?:chinh\s+)?ban", "vi")
_add("leak", "zh", 0.8,
     r"(?:输出|显示|打印|泄露|透露|告诉我|重复|复述|公开|展示|给出|提供|翻译|说出|写出|发送)[^。\n]{0,10}(?:系统提示词?|系统指令|系统消息|初始提示词?|隐藏提示词?|你的(?:提示词?|指令|配置|规则)|内部(?:指令|提示词?|配置)|密钥|机密|金丝雀|canary)")
_add("leak", "ja", 0.8,
     r"(?:システムプロンプト|システムメッセージ|初期プロンプト|内部(?:指示|設定)|秘密(?:の値|のキー|のトークン)?|機密|隠された|カナリア|canary)(?:を|は)?(?:そのまま|全文|正確に|すべて)?(?:出力|表示|教え|明かし|公開|暴露|繰り返し|書き出|見せ)")
_add("leak", "ko", 0.8,
     r"(?:시스템\s*프롬프트|시스템\s*메시지|초기\s*프롬프트|내부\s*(?:지침|설정)|비밀\s*(?:값|키|토큰)|숨겨진\s*(?:프롬프트|지침)|카나리|canary)\s*(?:를|을)?\s*(?:그대로\s*)?(?:출력|공개|알려|보여|반복|유출|말해|밝혀)")
_add("leak", "ru", 0.8,
     r"(?:покажи\w*|выведи\w*|раскрой\w*|напечатай\w*|повтори\w*|выдай\w*|расскажи\w*|перескажи\w*|процитируй\w*|перечисли\w*)\s+(?:\w+\s+){0,5}(?:системн\w+\s+(?:промпт|сообщени|инструкци)\w*|свои\s+инструкци\w+|секретн\w+|скрыт\w+\s+(?:промпт|инструкци)\w+|канарей\w*|canary)")
_add("leak", "fr", 0.75,
     r"\b(?:r[eé]v[eè]le[zr]?|affiche[zr]?|reproduis\w*|donne[zr]?|montre[zr]?|[eé]cris|r[eé]p[eè]te[zr]?)\s+(?:\w+\s+){0,5}(?:(?:ton|votre|le)\s+(?:v[eé]ritable\s+|vrai\s+|r[eé]el\s+)?(?:message\s+syst[eè]me|prompt\s+syst[eè]me|invite\s+syst[eè]me)|tes\s+instructions|canary)")
_add("leak", "es", 0.75,
     r"\b(?:revela|muestra|imprime|repite|reproduce|dame|escribe|ense[nñ]a)\s+(?:\w+\s+){0,5}(?:(?:tu|el)\s+(?:verdadero\s+|real\s+)?(?:mensaje\s+del\s+sistema|prompt\s+del\s+sistema)|tus\s+instrucciones|(?:el\s+)?valor\s+(?:real\s+)?de\s+\w*canary\w*|\w*canary\w*)")
_add("leak", "de", 0.75,
     r"\b(?:gib|zeige|nenne|wiederhole|verrate|offenbare|drucke)\w*\s+(?:\w+\s+){0,5}(?:(?:deine|die|ihre)\s+(?:tats[aä]chliche\s+|echte\s+)?(?:systemanweisung|systemnachricht|systemprompt|anweisungen)|\w*canary\w*)")

# --- authority (giả danh quyền lực / định dạng hệ thống) -------------------
_add("authority", "tag_override", 0.55,
     r"(?:\[\s*|<\s*|\*\*\s*)(?:system|admin|administrator|developer|root|security|priority)\s*(?:override|message|notice|update|instructions?|mode|priority|prompt)\b|"
     r"\b(?:system|admin|administrator|developer|root|security)\s+override\b|\bpriority\s*(?:0|zero)\b")
_add("authority", "bracket_role", 0.4,
     r"\[\s*(?:SYSTEM|ADMIN|DEVELOPER|ROOT|INSTRUCTION)S?\s*\]", flags=re.S)
_add("authority", "claim_admin", 0.5,
     r"\b(?:i\s+am|i'm|this\s+is)\s+(?:the\s+|your\s+|an?\s+)?(?:admin(?:istrator)?|developer|system\s+administrator|owner|creator|operator)\b[^.\n]{0,60}\b(?:approve|authori[sz]e|permit|allow|grant|require|order)\w*")
_add("authority", "claim_msg", 0.5,
     r"\b(?:developer|admin|system|operator)\s+(?:message|instruction|notice)\s*[:\-]|"
     r"\b(?:treat|consider|regard)\s+(?:this|the\s+following)\s+(?:message|text|instruction)s?\s+as\s+(?:a\s+|an\s+)?(?:developer|system|admin)\b")
_add("authority", "claim_replace", 0.55,
     r"\b(?:this|the\s+following)\s+(?:message|instruction|directive|rule|command)s?\s+(?:replaces?|supersedes?|overrides?|takes?\s+precedence|has\s+priority)\b|"
     r"\b(?:highest|top|maximum|absolute)\s+priority\b[^.\n]{0,30}\b(?:instruction|command|directive)")
_add("authority", "vi_claim", 0.5,
     r"\b(?:toi|tao)\s+la\s+(?:quan\s+tri\s+vien|admin|nha\s+phat\s+trien|chu\s+he\s+thong|nguoi\s+tao\s+ra\s+ban)\b[^.\n]{0,60}\b(?:phe\s+duyet|cho\s+phep|uy\s+quyen|yeu\s+cau)|"
     r"\b(?:chi\s+dan|tin\s+nhan|thong\s+diep)\s+nay\s+(?:thay\s+the|uu\s+tien|ghi\s+de)\b|muc\s+uu\s+tien\s+(?:cao\s+nhat|0)\b|"
     r"\b(?:developer|admin|he\s+thong)\s+message\s*[:\-]|tin\s+nhan\s+tu\s+(?:nha\s+phat\s+trien|quan\s+tri)", "vi")
_add("authority", "zh", 0.5, r"(?:我是|这是)(?:管理员|开发者|系统管理员)[^。\n]{0,30}(?:批准|授权|允许)|(?:系统|管理员|开发者)(?:消息|指令|通知)\s*[:：]|最高优先级")
_add("authority", "template_tokens", 0.55,
     r"<\|\s*(?:im_start|im_end|system|user|assistant|endoftext|eot_id|begin_of_text|start_header_id|end_header_id)\s*\|>|<<\s*/?SYS\s*>>|\[/?INST\]|<start_of_turn>|<end_of_turn>",
     flags=re.I)
_add("authority", "role_header", 0.4,
     r"(?:^|\n)\s*#{2,3}\s*(?:system|instruction|new\s+instruction|human|assistant)\s*:?\s*(?:\n|$)|</?(?:system|instructions?|admin|developer)(?:_prompt)?>")

# --- fake completion (Liu 2024) ----------------------------------------------
_add("fake_completion", "answer_done", 0.55,
     r"(?:^|\n)\s*(?:answer|response|output|summary|result|tra\s+loi|dap\s+an|ket\s+qua)\s*[:：]\s*(?:the\s+)?(?:task|summar\w+|translation|nhiem\s+vu|tac\s+vu|tom\s+tat)?\s*(?:is\s+|has\s+been\s+|da\s+)?(?:complete\w*|done|finished|hoan\s+tat|hoan\s+thanh|xong)\b")
_add("fake_completion", "answer_done_vi", 0.55,
     r"(?:^|\n)\s*(?:tra\s+loi|dap\s+an|ket\s+qua)\s*[:：]\s*(?:nhiem\s+vu|tac\s+vu|tom\s+tat)?\s*(?:da\s+)?(?:hoan\s+tat|hoan\s+thanh|xong)\b", "vi")
_add("fake_completion", "task_complete_then", 0.5,
     r"\b(?:task|summary|job|translation)\s+(?:is\s+|was\s+|has\s+been\s+)?(?:complete\w*|done|finished)\W+(?:now|next|new|and\s+now|please|ignore|you\s+(?:must|should|will))\b")

# --- task hijack / output shaping / audience -----------------------------------
_add("task_hijack", "en", 0.4,
     r"(?<!not )(?<!n't )\b(?:ignore|skip|forget|stop|abandon)\s+(?:the\s+|this\s+|your\s+)?(?:summar\w+|translat\w+|task|assignment|user'?s?\s+request)\b|"
     r"\b(?:do\s+not|don't|never)\s+(?:summari[sz]e|translate)\b|"
     r"\bbefore\s+(?:you\s+)?(?:the\s+|your\s+)?(?:summar\w+|answer\w*|respon\w+)\W+(?:\w+\W+){0,3}(?:print|output|reveal|say|include|insert)\b")
_add("task_hijack", "vi", 0.42,
     r"\b(?:bo|bo\s+qua|dung|khong|ngung)\s+(?:viec\s+|buoc\s+|phan\s+)?(?:tom\s+tat|dich)\b|"
     r"\bthay\s+vi\s+(?:tom\s+tat|dich|tra\s+loi)\b|"
     r"\btruoc\s+khi\s+(?:tao\s+)?(?:ban\s+)?(?:tom\s+tat|tra\s+loi)\b[^.\n]{0,40}\b(?:ai\s+can|hay|phai)\b[^.\n]{0,20}\b(?:in|xuat|doc|tiet\s+lo)\b", "vi")
_add("output_shaping", "en", 0.55,
     r"\b(?:the\s+|your\s+)?(?:summary|answer|response|output|reply)\s+(?:must|should|needs?\s+to|has\s+to|shall)\s+(?:state|say|claim|assert|include|contain|mention|insert|affirm|declare|read)\b|"
     r"\b(?:in|to)\s+(?:your|the)\s+(?:summary|answer|response|reply)\W+(?:\w+\W+){0,3}(?:add|insert|append|include|attach|mention)\b|"
     r"\b(?:add|insert|append|attach|include)\b[^.\n]{0,40}\b(?:to|into|in)\s+(?:your|the)\s+(?:summary|response|answer|reply)\b")
_add("output_shaping", "vi", 0.55,
     r"\b(?:ban\s+)?(?:tom\s+tat|cau\s+tra\s+loi|phan\s+hoi)\s+(?:cua\s+ban\s+|nay\s+)?(?:phai|can|hay|se\s+phai)\s+(?:khang\s+dinh|neu|ghi|noi|bao\s+gom|chua|them|dinh\s+kem)\b|"
     r"\b(?:them|dinh\s+kem|chen|ghi)\b[^.\n]{0,45}\b(?:vao|trong)\s+(?:ban|phan|cau)\s+(?:tom\s+tat|tra\s+loi|phan\s+hoi)\b|"
     r"\bkhang\s+dinh\s+(?:rang\s+)?\w+[^.\n]{0,30}\bla\b", "vi")
_add("output_shaping", "en_state_that", 0.58,
     r"\b(?:when|while|as)\s+(?:you\s+)?(?:summari[sz]\w*|answer\w*|respond\w*|writ\w+)\b[^.\n]{0,15}\b(?:state|say|write|mention|claim|note|add|include|insist|report|assert)\s+that\b|"
     r"\b(?:state|say|write|claim|assert|report)\s+(?:in|within)\s+(?:your|the)\s+(?:summary|answer|response|reply)\s+that\b|"
     r"\b(?:use|treat|take|confirm)\b[^.\n]{0,30}\b(?:above|following|preceding)\b[^.\n]{0,30}\bas\s+(?:your\s+|the\s+)?final\s+(?:answer|summary|response)\b")
_add("output_shaping", "vi_state_that", 0.6,
     r"\bkhi\s+(?:tom\s+tat|tra\s+loi|viet\s+tom\s+tat)\W+(?:\w+\W+){0,2}(?:ghi|viet|noi|khang\s+dinh|nhan\s+manh|neu|bao)\s+rang\b|"
     r"\b(?:hay|phai|can)\s+(?:ghi|viet|noi|khang\s+dinh)\s+rang\b|"
     r"\blam\s+(?:cau\s+tra\s+loi|ban\s+tom\s+tat|phan\s+hoi)\s+cuoi\s+cung\b", "vi")
_add("override", "en_bare_above", 0.6,
     r"\bignore\s+(?:the\s+)?(?:above|previous|preceding|prior|earlier|everything(?:\s+above)?)\b\W+(?:and\W+|then\W+|but\W+|instead\W+|now\W+|just\W+|you\W+)")
_add("override", "ignore_doc_facts", 0.5,
     r"\bignore\s+(?:the\s+)?(?:numbers|figures|data|content|facts|statistics)\s+(?:in|of|from)\s+(?:the\s+)?(?:document|text|above|report)\b")
_add("override", "vi_ignore_doc_facts", 0.5,
     r"\bbo\s+qua\s+(?:cac\s+|nhung\s+)?(?:con\s+so|so\s+lieu|du\s+lieu|noi\s+dung|thong\s+tin)\b[^.\n]{0,30}(?:tai\s+lieu|o\s+tren|ben\s+tren|vua\s+doc)", "vi")
_add("fake_completion", "inline_done", 0.5,
     r"\b(?:summary|answer|response)\s*[(\[]\s*(?:completed?|done|finished)\s*[)\]]")
_add("fake_completion", "inline_done_vi", 0.5,
     r"\b(?:ban\s+)?tom\s+tat\s*\(\s*da\s+(?:hoan\s+tat|xong)\s*\)", "vi")
_add("escape_chars", "literal_newlines", 0.25, r"(?:\\n){3,}|(?:\\r\\n){2,}|(?:\\t){4,}", flags=re.S)
_add("authority", "upper_notice", 0.45, r"\b(?:SYSTEM|ADMIN|SECURITY|IMPORTANT|URGENT)\s+(?:NOTICE|ALERT|MESSAGE|UPDATE|DIRECTIVE|INSTRUCTION)S?\s*[:\-]", flags=re.S)
_add("authority", "vi_bracket_auto", 0.35, r"\[\s*(?:quy\s+trinh\s+tu\s+dong|tu\s+dong|he\s+thong|automation|automated)\b[^\]]{0,20}\]", "vi")

# --- tool_action (mục tiêu `tool_action` của hợp đồng) và dấu hiệu trình tự -----------
_add("tool_action", "named_call", 0.5,
     r"\b[a-z][a-z0-9]*_[a-z0-9_]+\s*\(\s*(?:[a-z_]+\s*=|<|[\"'])")
_add("tool_action", "call_tool_en", 0.5,
     r"\b(?:call|invoke|use|trigger|run|execute)\s+(?:the\s+)?(?:tool\s+|function\s+)?[a-z]+_[a-z_]+\b|"
     r"\b(?:call|invoke|use|trigger)\s+(?:the\s+)?(?:\w+\s+)?(?:tool|function)\b[^.\n]{0,40}\b(?:send|delete|email|forward|post|upload|remove|transfer)\w*")
_add("tool_action", "call_tool_vi", 0.5,
     r"\b(?:goi|dung|su\s+dung|kich\s+hoat|thuc\s+thi)\s+(?:cong\s+cu\s+|ham\s+)?[a-z]+_[a-z_]+\b|"
     r"\b(?:goi|su\s+dung)\s+(?:cong\s+cu|ham)\b[^.\n]{0,40}\b(?:gui|xoa|chuyen\s+tiep|dang|tai\s+len)\b", "vi")
_add("tool_action", "exfil_mail", 0.35,
     r"\bsend\b[^.\n]{0,70}\b(?:to|at)\s+[\w.+-]+@[\w-]+\.[\w.-]+|\bforward\b[^.\n]{0,50}\bto\s+[\w.+-]+@[\w-]+\.[\w.-]+")
_add("tool_action", "exfil_mail_vi", 0.35,
     r"\b(?:gui|chuyen\s+tiep)\b[^.\n]{0,70}\b(?:toi|cho|den)\s+[\w.+-]+@[\w-]+\.[\w.-]+", "vi")
_add("sequence_cue", "en", 0.45,
     r"\b(?:after|before|once)\s+(?:you\s+)?(?:summari[sz]\w*|answer\w*|respond\w*|repl\w+|finish\w*\s+(?:the\s+)?summar\w+)[^.\n]{0,30}\b(?:call|send|delete|forward|email|run|execute|print|output|include|add|state|write)\b|"
     r"\b(?:do|perform|execute)\s+this\s+(?:before|after)\s+(?:answering|responding|replying|summari[sz]\w*)\b")
_add("sequence_cue", "vi", 0.45,
     r"\b(?:sau|truoc)\s+khi\s+(?:da\s+)?(?:tom\s+tat|tra\s+loi(?:\s+nguoi\s+dung)?|tao\s+ban\s+tom\s+tat)(?:\s+xong)?[^.\n]{0,30}\b(?:goi|gui|xoa|chuyen\s+tiep|thuc\s+hien|in|xuat|them|ghi|dinh\s+kem|dung)\b|"
     r"\bthuc\s+hien\s+(?:ngay\s+)?(?:truoc|sau)\s+khi\s+(?:tra\s+loi|tom\s+tat)\b", "vi")
_add("refusal_suppress", "no_confirm", 0.4,
     r"\bwithout\s+(?:asking|confirmation|confirming|checking\s+with)\b|\bdo\s+not\s+(?:ask|wait\s+for)\s+(?:for\s+)?(?:confirmation|permission|approval)\b")
_add("refusal_suppress", "no_confirm_vi", 0.4,
     r"\bkhong\s+(?:can|duoc)\s+(?:hoi|xac\s+nhan|cho\s+phep)\b|\bngay\s+lap\s+tuc\b[^.\n]{0,30}\bkhong\s+(?:can|hoi)\b", "vi")
_add("persona", "mode_switch", 0.4, r"\byou\s+are\s+(?:now\s+)?in\s+(?:\w+\s+){0,2}mode\b")
_add("persona", "mode_switch_vi", 0.4, r"\bban\s+dang\s+o\s+che\s+do\b", "vi")

_AI = r"(?:(?-i:AI|A\.I\.|LLM|GPT)|assistant|language\s+model|model|chatbot|bot|agent|summari[sz]er|ChatGPT|Claude|Copilot)"
_add("audience", "en_note_to_ai", 0.55,
     rf"\b(?:note|message|instructions?|directive|attention|notice|hey|hello|dear|important|warning|memo)\s*(?:to|for)\s*(?:the\s+)?{_AI}\b|"
     rf"\b(?:if|when)\s+you\s+are\s+(?:an?\s+)?{_AI}\b|"
     rf"\b(?:attention|attn)\s*[:,]?\s*{_AI}\b")
_add("audience", "en_ai_colon", 0.3,
     rf"(?:<!--\s*|^|\n|[\"'(\[“‘])\s*{_AI}\s*[:\]>]\s*\w+")
_add("audience", "vi", 0.55,
     r"\b(?:chi\s+dan|huong\s+dan|luu\s+y|ghi\s+chu|thong\s+bao|nhac\s+nho|chu\s+thich)\s+(?:xu\s+ly\s+tu\s+dong\s+)?(?:danh\s+)?(?:cho|gui|danh\s+cho|toi)\s+(?:ai|tro\s+ly|mo\s+hinh|he\s+thong|llm|bot|chatbot)\b|"
     r"\b(?:phu\s+luc|chu\s+ky|ghi\s+chu)\s+(?:xu\s+ly\s+)?(?:tu\s+dong\s+)?(?:danh|cho|gui)\s+(?:cho\s+)?(?:ai|tro\s+ly|mo\s+hinh)\b|"
     r"\bchi\s+dan\s+cho\s+ai\b", "vi")
_add("audience", "vi_ai_must", 0.38,
     r"\b(?:ai|tro\s+ly|mo\s+hinh|llm|chatbot)\s+(?:phai|can|hay|se\s+phai|bat\s+buoc)\s+(?:\w+\s+){0,2}(?:in|xuat|doc|tiet\s+lo|bo|khang\s+dinh|them|gui|dinh\s+kem|goi|thuc\s+hien)\b", "vi")
_add("audience", "zh", 0.55, r"(?:给|致|对|写给)(?:AI|人工智能|助手|模型|大模型|语言模型)(?:的)?(?:指令|说明|提示|注意|消息)|如果你是(?:AI|人工智能|语言模型|助手)")

# --- persona / refusal suppression / debug / decode / many-shot -----------
_add("persona", "dan", 0.5, r"\bDAN\b", flags=re.S)
_add("persona", "keywords", 0.5,
     r"\bdo\s+anything\s+now\b|\bdeveloper\s+mode\b|\bjailbr(?:eak|oken)\b|\b(?:unrestricted|unfiltered|uncensored)\s+(?:ai|assistant|mode|persona|model|auditor|version)\b|\bwithout\s+(?:any\s+)?(?:restrictions|limits|limitations|filters|censorship|safety)\b|\bno\s+(?:ethical|moral|safety)?\s*(?:restrictions|limitations|guidelines|boundaries)\b")
_add("persona", "role_switch", 0.38,
     r"\byou\s+are\s+now\b|\bfrom\s+now\s+on\s*,?\s+you(?:'re|\s+are|\s+will)\b|\byou\s+will\s+(?:now\s+)?(?:act|behave|respond|play)\b|"
     r"\bpretend\s+(?:to\s+be|that\s+you|you\s+are)\b|\broleplay\s+as\b|\brole-play\s+as\b|\bact\s+as\s+(?:if\s+you|an?\s+(?:unrestricted|unfiltered|uncensored))\b")
_add("persona", "vi", 0.4,
     r"\btu\s+(?:gio|bay\s+gio)\s+(?:tro\s+di\s+)?(?:ban|may)\s+la\b|\b(?:hay\s+)?(?:dong|nhap)\s+vai\b[^.\n]{0,60}\b(?:khong\s+(?:co|bi)\s+(?:gioi\s+han|rang\s+buoc|han\s+che)|mien\s+(?:co\s+che|tru)|khong\s+(?:chiu|tuan)|khong\s+loc)|"
     r"\bkhong\s+(?:co|bi)\s+(?:gioi\s+han|rang\s+buoc|han\s+che)\b|\bgia\s+(?:vo|su)\s+(?:ban|rang\s+ban)\s+la\b|\bmien\s+(?:co\s+che|tru)\s+tu\s+choi\b|"
     r"\btrong\s+(?:tro\s+choi|truyen|vai|thoi\s+diem)[^.\n]{0,50}\b(?:khong\s+(?:co\s+)?(?:han\s+che|gioi\s+han|bao\s+mat)|bi\s+bai\s+bo|duoc\s+cong\s+khai)\b", "vi")
_add("persona", "vi_two_roles", 0.42,
     r"\b(?:tra\s+loi|phan\s+hoi)\s+bang\s+hai\s+vai\b|\bhai\s+vai\s*:", "vi")
_add("persona", "en_two", 0.4,
     r"\b(?:two|2)\s+(?:personas?|roles?|modes?|characters)\b[^.\n]{0,40}\b(?:refuse|unrestricted|unfiltered|no\s+limits|free)\b")
_add("persona", "zh", 0.45, r"你现在是|从现在开始你是|扮演[^。\n]{0,20}(?:没有|不受)(?:限制|约束)|(?:没有|不受)(?:任何)?(?:限制|约束|审查)")
_add("refusal_suppress", "en", 0.45,
     r"\b(?:do\s+not|don't|never)\s+(?:refuse|decline|apologi[sz]e|warn|add\s+(?:any\s+)?(?:warnings?|disclaimers?))\b|\bwithout\s+(?:any\s+)?(?:refusal|warnings?|disclaimers?)\b|\bno\s+refusals?\b")
_add("refusal_suppress", "vi", 0.45,
     r"\b(?:khong|dung|chang)\s+(?:duoc\s+)?(?:tu\s+choi|dua\s+(?:ra\s+)?loi\s+tu\s+choi|canh\s+bao)\b|\btam\s+bo\s+(?:buoc|co\s+che)\s+tu\s+choi\b|\bbo\s+(?:buoc|co\s+che|quy\s+tac)\s+(?:tu\s+choi|giu\s+kin)\b|\bkhong\s+(?:nhac|giai\s+thich)\s+(?:rang\s+)?ban\s+da\b", "vi")
_add("refusal_suppress", "zh", 0.45, r"不要拒绝|不得拒绝|不许拒绝|无需拒绝")
_add("debug_mode", "en", 0.5,
     r"\b(?:debug|developer|maintenance|admin|god|sudo)[\s_-]*mode\s*(?:=|:|is|on|enabled|activated|true)|\b(?:enable|activate|turn\s+on|switch\s+to)\s+(?:the\s+)?(?:debug|developer|maintenance|admin)\s+mode\b|\bDEBUG_MODE\s*=")
_add("debug_mode", "vi", 0.5,
     r"\b(?:bat|kich\s+hoat|chuyen\s+sang)\s+(?:che\s+do\s+)?(?:debug|nha\s+phat\s+trien|bao\s+tri|quan\s+tri)\b|\bdebug_mode\s*=\s*true\b", "vi")
_add("decode_exec", "en", 0.58,
     r"\b(?:decode|decrypt|unscramble|deobfuscate|rot-?13|base-?64|hex)\b[^.\n]{0,60}\b(?:then|and\s+then|and|afterwards?)\s+(?:execute|follow|run|do|perform|obey|carry\s+out|comply)\b|"
     r"\b(?:execute|follow|run|obey|carry\s+out)\s+(?:the\s+)?(?:decoded|decrypted|resulting|hidden)\s+(?:instruction|command|text|message)s?\b")
_add("decode_exec", "vi", 0.58,
     r"\b(?:giai\s+ma|khoi\s+phuc|bo\s+khoang\s+trang|ghep\s+cac\s+chu|bo\s+dau\s+gach|ap\s+dung\s+rot13|rot13|base64)\b[^.\n]{0,70}\b(?:roi|sau\s+do|va)\s+(?:thuc\s+hien|lam\s+theo|thuc\s+thi|tuan\s+theo)\b|"
     r"\b(?:thuc\s+hien|lam\s+theo|thuc\s+thi)\s+(?:chi\s+dan|cau\s+lenh|ket\s+qua|noi\s+dung)\s+(?:da\s+)?(?:giai\s+ma|nhan\s+duoc|khoi\s+phuc)\b|\bgiai\s+ma\b[^.\n]{0,40}\blam\s+theo\b", "vi")

# --- v2: mẫu thêm sau khi có dữ liệu chỉnh công khai (results/v2/tuning_log.md) ----------------
# Chỉ chọn bằng tập chỉnh (nhóm train, tập A, Mirror, SPML, bản dịch Việt, LLMail gđ1); không dùng hold-out.
# Mỗi mẫu là một họ cấu trúc (động từ + đối tượng), không phải chuỗi của một prompt cụ thể.
_add("persona", "no_restrictions", 0.62,
     r"\b(?:you|i|it|he|she|they|we|ai|assistant|bot|chatbot|model|persona|character|mode)\s+(?:\w+\s+){0,2}(?:have|has|had|with|having|are\s+free\s+of|is\s+free\s+of)\s+(?:absolutely\s+)?no\s+(?:\w+\s+)?(?:restrictions?|guidelines|limits|limitations|rules|filters|boundaries|constraints)\b|"
     r"\b(?:your|my)\s+new\s+(?:identity|name|persona|role)\s+is\b")
_add("leak", "output_instructions", 0.62,
     r"\b(?:output|print|show|display|reveal|repeat|dump|recite|give|return|write\s+out|tell\s+me|share)\s+(?:me\s+)?(?:your|the)\s+"
     r"(?:entire\s+|full\s+|complete\s+|whole\s+|exact\s+|raw\s+|original\s+|initial\s+|hidden\s+|internal\s+|json\s+)*"
     r"(?:context|configuration|config|system\s+(?:prompt|message|instructions?)|instructions?|prompt|setup|initial\s+prompt|rules)\b")
_add("leak", "ask_password", 0.6,
     r"\b(?:tell|give|show|reveal|say|spell|write|print|repeat|provide|share|what\s+is|what's|whats)\s+(?:me\s+)?(?:the\s+|your\s+)?(?:secret\s+)?"
     r"(?:password|passphrase|secret\s+(?:word|phrase|code|key|value))\b")
_add("override", "negate_typo", 0.65,
     r"\b(?:negate|nullify|void|invalidate|rescind|supersede|override)\s+(?:all\s+|any\s+|every\s+)?(?:the\s+)?(?:instr\w{3,9}|rules|commands|directives|guidelines|prompts?)\b|"
     r"\bnew\s+instr\w{3,9}\s+(?:that\s+)?(?:override|replace|supersede|overrule|cancel)")
_add("override", "forget_everything", 0.62,
     r"\bforget\s+(?:everything|all|your\s+(?:training|rules|instructions|guidelines|programming|previous\s+\w+))\b|"
     r"\bdo\s+(?:whatever|anything|everything)\s+i\s+(?:ask|say|want|tell)\b|\bskip\s+all\s+(?:content\s+)?(?:checks|filters|rules|restrictions|safety)\b")
_add("override", "scoped_ignore", 0.62,
     r"\bignore\s+(?:your|the|all|any|these|those)?\s*(?:previous\s+|above\s+|prior\s+|earlier\s+)?(?:instructions?|commands?|rules|directions?)\b"
     r"[^.\n]{0,60}\b(?:regarding|about|on|concerning|for|related\s+to|that|which|written)\b")
_add("override", "romance_german", 0.62,
     r"\b(?:ignora(?:r|te)?|ignorez|ignoriere[n]?|ignorer|pasa\s+por\s+alto|omite|descarta|salta|olvida(?:r)?|oublie[sz]?|vergiss|vergessen|dimentica)\s+"
     r"(?:todas?\s+|tutte\s+|toutes?\s+|alle[ns]?\s+)?(?:(?:las|los|le|les|tus|vos|deine|ihre|ihren|il|lo|i|gli)\s+)?"
     r"(?:instrucciones|restricciones|reglas|instructions|restrictions|r[èe]gles|anweisungen|regeln|beschr[äa]nkungen|istruzioni|restrizioni|regole|"
     r"il\s+testo|el\s+texto|le\s+texte|den\s+text|(?:tu|su|votre|dein|ihr)\s+\w+)\b")
_add("leak", "romance_german", 0.62,
     r"\b(?:muestra|mu[eé]strame|affiche[sz]?|zeig(?:e)?|mostra|mostrami|revela|rev[eé]lame|r[eé]v[eè]le|gib)\s+(?:me\s+|mir\s+)?"
     r"(?:(?:tu|tus|votre|vos|dein|deine|il\s+tuo|la\s+tua|le\s+tue)\s+)?(?:(?:completa|compl[eè]te|vollst[äa]ndige?n?|completo)\s+)?"
     r"(?:prompt|configuraci[óo]n|configuration|konfiguration|configurazione|instrucciones|instructions|anweisungen|istruzioni|prompt\s+de\s+sistema|system\s*prompt|systemprompt)\b")
_add("decode_exec", "format_cipher", 0.62,
     r"\b(?:provide|render|give|present|write|deliver|compose|format|express|encode|output)\s+(?:your\s+|the\s+)?(?:reply|answer|response|output|summary)\s+"
     r"(?:using|in|with|via|as|through|by)\s+(?:an?\s+)?(?:\w+\s+){0,2}"
     r"(?:cipher|substitution|base-?64|caesar|rot-?13|binary|morse|leet|reversed|backwards|pig\s+latin|hex(?:adecimal)?|encoded|encryption|code\s+words?)\b")
_add("task_hijack", "insert_code", 0.62,
     r"\b(?:incorporate|interweave|weave|inject|engage|feature|integrate|embed|insert)\s+(?:the\s+)?(?:following|subsequent|below|next)\s+"
     r"(?:\w+\s+){0,2}(?:code|snippet|script|excerpt|fragment|segment)\b[^`]{0,80}```")
_add("tool_action", "send_email_to", 0.62,
     r"\bsend\s+(?:an?\s+)?e-?mail\b[^.\n]{0,80}\bto\b[^.\n]{0,20}[\w.-]+@[\w.-]+|\btrigger(?:ing)?\s+a\s+tool\s+call\b")
_add("authority", "fake_role_tags", 0.6,
     r"</?\s*(?:tool|user|system|assistant)\s*>|\[/?\s*system\s*\]")

_MANY_SHOT_USER = re.compile(r"^\s*(?:user|human|nguoi\s+dung|yeu\s+cau|q|question)\s*\d*\s*[:：]", re.I | re.M)
_MANY_SHOT_ASST = re.compile(r"^\s*(?:assistant|ai|bot|tro\s+ly|tra\s+loi|a|answer|response)\s*\d*\s*[:：]", re.I | re.M)

_STRONG_FOR_REPEAT = {"override", "leak", "persona", "refusal_suppress", "authority", "task_hijack"}

# --- cue trích dẫn (giảm điểm khi câu tấn công chỉ được nêu làm ví dụ) -------
_QUOTE_CHARS = "\"“”'‘’«»「」『』"
_QUOTE_CUE = re.compile(
    r"\b(?:for\s+example|e\.g\.|such\s+as|like\s+the\s+phrase|the\s+(?:phrase|string|sentence|text)|called|known\s+as|"
    r"vi\s+du|chang\s+han|cum\s+tu|chuoi|cau|doan|nhu|goi\s+la|mau|nhan|viet|nhac\s+den|"
    r"phrase|string|sentence|text|quote[sd]?|example|sample|says?|titled)\b[\s:,;-]*(?:\w{1,8}[\s:,;-]*){0,2}$", re.I)
_EXEC_BEFORE = re.compile(r"\b(?:thuc\s+hien|lam\s+theo|thuc\s+thi|tuan\s+theo|execute|follow|run|obey|perform|comply)\b", re.I)
_NEG_BEFORE = re.compile(
    r"(?:\bkhong(?:\s+(?:duoc|nen|the|can|phai|bao\s+gio))?|\bdung|\bchang|\bnever|\bnot|n't|\bdo\s+not|\bmust\s+not|\bnot\s+to)\s+$",
    re.I)
_EXEC_AFTER = re.compile(
    r"^\W*(?:then|and\s+then|and|roi|sau\s+do|va)?\W*(?:execute|follow|run|do|obey|perform|comply|thuc\s+hien|lam\s+theo|thuc\s+thi)", re.I)


_SCOPED_AFTER = re.compile(
    r"^\W*(?:about|regarding|concerning|relating|related\s+to|for\s+the|on\s+the|sent|given\s+(?:yesterday|earlier|last)|"
    r"ve\s+(?:viec|cach|viec|quy|thu)|ve\b|lien\s+quan|da\s+gui|hom\s+qua|tuan\s+truoc)\b", re.I)


def _quoted_example(view: str, start: int, end: int) -> bool:
    """Khớp nằm trong cặp ngoặc kép, đứng sau cue "ví dụ/chẳng hạn", không kèm lệnh thực thi."""
    lo = max(0, start - 120)
    qpos = [i for i in range(lo, start) if view[i] in _QUOTE_CHARS]
    if not qpos:
        return False
    q = qpos[-1]
    close = next((i for i in range(end, min(len(view), end + 160)) if view[i] in _QUOTE_CHARS), None)
    if close is None or any(view[i] in _QUOTE_CHARS for i in range(start, end)):
        return False
    window = _vi_fold(view[max(0, q - 60):q])
    if not _QUOTE_CUE.search(window) or _EXEC_BEFORE.search(window):
        return False
    after = view[close + 1:close + 90].lstrip(" .,;!")
    return _EXEC_AFTER.match(_vi_fold(after)) is None


def _negated(view: str, start: int) -> bool:
    """Động từ ghi đè đứng sau phủ định ("không được bỏ qua", "do not ignore")."""
    return _NEG_BEFORE.search(view[max(0, start - 24):start]) is not None


def _scan_view(view: str, which: str, source: str, hits: list[Hit]) -> None:
    for p in _PATTERNS:
        if p.view != which:
            continue
        ms = list(p.rx.finditer(view))
        if not ms:
            continue
        m = ms[0]
        w = p.weight
        if p.family in ("override", "leak") and _negated(view, m.start()):
            continue
        if p.family == "override" and _SCOPED_AFTER.match(view[m.end():m.end() + 40]):
            w *= SCOPED_DISCOUNT
        if _quoted_example(view, m.start(), m.end()):
            w *= QUOTE_DISCOUNT
        if len(ms) >= 3 and p.family in _STRONG_FOR_REPEAT and w >= 0.35:
            w = min(0.95, w + REPEAT_BONUS)
        hits.append(Hit(p.family, p.name, w, view[m.start():m.end()][:80].replace("\n", " "), source))


def _scan_many_shot(view: str, source: str, hits: list[Hit]) -> None:
    if len(_MANY_SHOT_USER.findall(view)) >= 3 and len(_MANY_SHOT_ASST.findall(view)) >= 3:
        hits.append(Hit("many_shot", "dialogue_turns", 0.4, "repeated User/Assistant turns", source))


def scan_plain(text: str, source: str = "plain") -> list[Hit]:
    """Quét một đoạn văn bản (không giải mã). Dùng cả bản nguyên dấu lẫn bản bỏ dấu."""
    nfkc = unicodedata.normalize("NFKC", text)
    hits: list[Hit] = []
    _scan_view(nfkc, "text", source, hits)
    _scan_view(_vi_fold(nfkc), "vi", source, hits)
    _scan_many_shot(_vi_fold(nfkc), source, hits)
    return hits


# ---------------------------------------------------------------------------
# 3. Giải mã thử
# ---------------------------------------------------------------------------
_B64_RE = re.compile(rf"(?<![A-Za-z0-9+/=_-])[A-Za-z0-9+/_-]{{{MIN_B64_LEN},}}={{0,2}}(?![A-Za-z0-9+/=])")
_HEX_RE = re.compile(r"(?<![0-9A-Za-z])(?:(?:0x|\\x)?[0-9a-fA-F]{2}[ \t,:;-]?){8,}(?![0-9A-Za-z])")
_PCT_RE = re.compile(r"(?:%[0-9A-Fa-f]{2})")
_UESC_RE = re.compile(r"\\u([0-9a-fA-F]{4})|\\x([0-9a-fA-F]{2})|&#x([0-9a-fA-F]+);|&#(\d+);")
_SPACED_RE = re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z0-9_.][ \t]{1,3}){5,}[A-Za-z0-9_.](?![A-Za-z0-9])")
_HYPH_RE = re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z]-){3,}[A-Za-z](?![A-Za-z0-9])")


def _readable(data: bytes) -> Optional[str]:
    """Trả chuỗi nếu ``data`` là UTF-8 đọc được (chữ + khoảng trắng chiếm đa số)."""
    try:
        s = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if len(s) < MIN_DECODED_CHARS:
        return None
    printable = sum(1 for c in s if c.isprintable() or c in "\n\t")
    texty = sum(1 for c in s if c.isalpha() or c.isspace())
    if printable / len(s) < 0.97 or texty / len(s) < 0.6:
        return None
    return s


def _try_b64(token: str) -> Optional[str]:
    t = token.replace("-", "+").replace("_", "/")
    t += "=" * (-len(t) % 4)
    try:
        return _readable(base64.b64decode(t, validate=True))
    except (binascii.Error, ValueError):
        return None


def _try_hex(token: str) -> Optional[str]:
    t = re.sub(r"0x|\\x|[^0-9a-fA-F]", "", token)
    if len(t) < 16 or len(t) % 2:
        return None
    try:
        return _readable(bytes.fromhex(t))
    except ValueError:
        return None


def _unescape(m: re.Match) -> str:
    u, x, hx, dec = m.groups()
    try:
        if u:
            return chr(int(u, 16))
        if x:
            return chr(int(x, 16))
        if hx:
            return chr(int(hx, 16))
        return chr(int(dec))
    except (ValueError, OverflowError):
        return m.group()


def _join_spaced(text: str) -> Optional[str]:
    """"P r i n t   t h e" -> "Print the" (từ cách nhau >= 2 khoảng trắng)."""
    def fix(m: re.Match) -> str:
        words = re.split(r"\s{2,}", m.group())
        return " ".join(re.sub(r"\s", "", w) for w in words)

    out, n = _SPACED_RE.subn(fix, text)
    return out if n else None


def _join_hyphen(text: str) -> Optional[str]:
    out, n = _HYPH_RE.subn(lambda m: m.group().replace("-", ""), text)
    return out if n else None


def _decoded_views(text: str, depth: int) -> list[tuple[str, str]]:
    """Các (nhãn, văn bản giải mã) thu được từ ``text``. Chỉ giữ cái đọc được."""
    views: list[tuple[str, str]] = []
    for m in _B64_RE.finditer(text):
        s = _try_b64(m.group())
        if s:
            views.append(("base64", s))
    for m in _HEX_RE.finditer(text):
        s = _try_hex(m.group())
        if s:
            views.append(("hex", s))
    if len(_PCT_RE.findall(text)) >= 6:
        s = urllib.parse.unquote(text)
        if s != text:
            views.append(("urlencode", s))
    if len(_UESC_RE.findall(text)) >= 4:
        s = html.unescape(_UESC_RE.sub(_unescape, text))
        if s != text:
            views.append(("escape", s))
    joined = _join_spaced(text)
    if joined:
        views.append(("spaced_letters", joined))
    joined = _join_hyphen(text)
    if joined:
        views.append(("hyphen_letters", joined))
    if depth == 0:
        views.append(("rot13", codecs.encode(text, "rot13")))
        views.append(("reversed", text[::-1]))
    return views


def scan(text: str, depth: int = 0, source: str = "plain") -> list[Hit]:
    """Quét ``text`` và mọi bản giải mã (đệ quy tới MAX_DEPTH)."""
    hits = scan_plain(text, source)
    if depth >= MAX_DEPTH:
        return hits
    for label, decoded in _decoded_views(text, depth):
        sub = scan(decoded, depth + 1, label if source == "plain" else f"{source}>{label}")
        hits.extend(sub)
    return hits


def combine(hits: Iterable[Hit]) -> tuple[float, list[Hit]]:
    """Điểm = noisy-OR giữa các họ. Trong một họ: mẫu mạnh nhất, cộng ``CORROBORATION`` x
    điểm mẫu thứ hai khi nó khớp một đoạn *khác* (hai bằng chứng độc lập cùng họ).
    Trả (điểm, hit đại diện từng họ, xếp giảm dần)."""
    by_family: dict[str, list[Hit]] = {}
    for h in hits:
        by_family.setdefault(h.family, []).append(h)
    prod = 1.0
    top: list[Hit] = []
    for fam_hits in by_family.values():
        fam_hits.sort(key=lambda h: -h.weight)
        first = fam_hits[0]
        top.append(first)
        fam_prod = 1.0 - min(first.weight, 0.99)
        key = _vi_fold(first.snippet)
        second = next((h for h in fam_hits[1:] if _vi_fold(h.snippet) != key
                       and key not in _vi_fold(h.snippet) and _vi_fold(h.snippet) not in key), None)
        if second is not None:
            fam_prod *= 1.0 - CORROBORATION * min(second.weight, 0.99)
        prod *= fam_prod
    return round(1.0 - prod, 4), sorted(top, key=lambda h: -h.weight)


def _clip(text: str) -> str:
    if len(text) <= MAX_SCAN_CHARS:
        return text
    return text[: MAX_SCAN_CHARS - 20_000] + "\n" + text[-20_000:]


def _describe(notes: dict) -> str:
    parts = [f"{k}={v!r}" if k == "hidden_tag_text" else f"{k}={v}" for k, v in notes.items()]
    return ";".join(parts)


def check(user_task: str, document: str) -> LayerResult:
    """L1: làm sạch rồi quét. ``user_task`` không dùng (kênh tin cậy)."""
    t0 = time.perf_counter()
    clean, notes = normalize(document)
    body = clean
    if notes.get("hidden_tag_text"):
        body = clean + "\n" + notes["hidden_tag_text"]
    hits = scan(_clip(body))
    score, top = combine(hits)
    ms = lambda: (time.perf_counter() - t0) * 1000.0  # noqa: E731
    if score >= THRESHOLD:
        why = ",".join(h.tag() for h in top[:3])
        if notes:
            why += f"|sanitized[{_describe(notes)}]"
        return LayerResult("block", document, score, f"block:{why}", ms())
    changed = bool(notes)
    reason = (f"sanitize:{_describe(notes)}" if changed else
              ("pass:" + ",".join(h.tag() for h in top[:2]) if top else "pass"))
    return LayerResult("sanitize" if changed else "pass",
                       clean if changed else document, score, reason, ms())


# ---------------------------------------------------------------------------
# 4. Chạy độc lập
# ---------------------------------------------------------------------------
def _report() -> None:  # pragma: no cover - in số liệu
    from collections import defaultdict
    from defenses._data import load_benign_tune, load_train_attacks

    attacks = load_train_attacks()
    benign, from_fixture = load_benign_tune()
    per_type: dict = defaultdict(lambda: {"block": 0, "sanitize": 0, "pass": 0, "n": 0})
    lat = []
    missed = []
    for s in attacks:
        r = check(s.user_task, s.document)
        lat.append(r.latency_ms)
        d = per_type[s.attack_type]
        d[r.action] += 1
        d["n"] += 1
        if r.action != "block":
            missed.append((s.id, s.attack_type, r.action, r.score))
    print(f"L1  THRESHOLD={THRESHOLD}  train attacks n={len(attacks)}")
    print(f"{'attack_type':30s} {'n':>3s} {'block':>6s} {'sanit':>6s} {'pass':>5s}  block%")
    tot = {"block": 0, "sanitize": 0, "pass": 0, "n": 0}
    for t, d in sorted(per_type.items()):
        print(f"{t:30s} {d['n']:3d} {d['block']:6d} {d['sanitize']:6d} {d['pass']:5d}  {100 * d['block'] / d['n']:5.1f}")
        for k in tot:
            tot[k] += d[k]
    print(f"{'TOTAL':30s} {tot['n']:3d} {tot['block']:6d} {tot['sanitize']:6d} {tot['pass']:5d}  {100 * tot['block'] / tot['n']:5.1f}")
    bl = defaultdict(int)
    fp = []
    for s in benign:
        r = check(s.user_task, s.document)
        lat.append(r.latency_ms)
        bl[r.action] += 1
        if r.action != "pass":
            fp.append((s.id, r.action, r.score, r.reason[:70]))
    nb = len(benign)
    src = "FIXTURE tự viết (chưa có benign_prompts.json)" if from_fixture else "attack_prompts/benign_prompts.json"
    print(f"\nbenign tune n={nb}  nguồn: {src}")
    print(f"  block (chặn nhầm) {bl['block']}/{nb} = {100 * bl['block'] / nb:.1f}%   "
          f"sanitize (đổi nội dung) {bl['sanitize']}/{nb} = {100 * bl['sanitize'] / nb:.1f}%   pass {bl['pass']}/{nb}")
    for row in fp:
        print("  benign không pass:", row)
    print("\nattack không bị chặn:")
    for row in missed:
        print("  ", row)
    print(f"\nlatency trung bình mỗi lần gọi: {sum(lat) / len(lat):.2f} ms (n={len(lat)}, max {max(lat):.1f} ms)")


if __name__ == "__main__":  # pragma: no cover
    _report()
