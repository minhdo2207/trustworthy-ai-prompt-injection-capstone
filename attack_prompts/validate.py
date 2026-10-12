"""Kiểm tra dữ liệu prompt theo schema v2 (docs/hop-dong-chung.md, mục 1).

Chạy: python3 attack_prompts/validate.py   (thoát mã 1 nếu có lỗi)

Tập ngoài (ext_attack/ext_benign, xem README mục "Dữ liệu ngoài") được kiểm riêng bằng `validate_external`;
chạy `python3 attack_prompts/validate.py` sẽ kiểm cả hai nếu có các tệp `ext_*`.

Lỗi (làm hỏng dữ liệu): thiếu trường, sai enum, id trùng, success_check sai, canary cố định,
technique train trùng hold-out, hai prompt gần như giống hệt (> 0,85).
Cảnh báo: cặp tương đồng 0,6–0,85, tài liệu nền dùng quá nhiều lần.
"""
from __future__ import annotations

import base64
import binascii
import codecs
import itertools
import json
import re
import statistics
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

ATTACK_TYPES = {"direct_injection", "indirect_injection", "jailbreak_roleplay",
                "code_switching_translation", "obfuscation", "many_shot_jailbreaking"}
LIU_TYPES = {"naive", "escape_characters", "context_ignoring", "fake_completion", "combined", "none"}
GOAL_TYPES = {"leak", "integrity", "tool_action"}
SPLITS = {"train", "holdout", "benign", "test_indist"}
SPLIT_FILES = {"train": "train_prompts.json", "holdout": "holdout_prompts.json",
               "benign": "benign_prompts.json", "test_indist": "test_indist_prompts.json"}
ID_PREFIX = {"train": "TR", "holdout": "HO", "benign": "BN", "test_indist": "IN"}
REQUIRED_FILES = ("train", "holdout", "benign")
TOOLS = {"send_email", "delete_file"}
HN_CATEGORIES = {"system_prompt_topic", "ignore_phrase", "encoded_data", "code", "foreign_text",
                 "unicode", "security_training", "secret_word"}
SIM_WARN, SIM_ERROR = 0.60, 0.85
SHINGLE = 5
CARRIER_WORDS = (60, 250)
BENIGN_WORDS = (50, 250)
CARRIER_REUSE_WARN = 6

# Giá trị canary phải sinh ngẫu nhiên mỗi lần chạy: cấm mọi giá trị cố định gắn với tên canary.
CANARY_VALUE_PATTERNS = [
    re.compile(r"SECRET_CANARY[ \t]*[=:][ \t]*[\"'`]?[A-Za-z0-9]"),
    re.compile(r"SECRET_CANARY[ \t]+(?:là|is)[ \t]*[\"'`]?[A-Za-z0-9_-]{6,}"),
    re.compile(r"\bCANARY[_-][0-9A-Za-z]{6,}\b"),
    re.compile(r"\bcanary[_-]?[0-9a-f]{8,}\b", re.I),
]
B64_TOKEN = re.compile(r"[A-Za-z0-9+/]{16,}={0,2}")
HEX_TOKEN = re.compile(r"\b(?:[0-9a-fA-F]{2}){12,}\b")


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


# ---------- tiện ích văn bản ----------

def norm(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text).lower()).strip()


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def shingles(text: str, n: int = SHINGLE) -> set[str]:
    t = norm(text)
    return {t[i:i + n] for i in range(max(len(t) - n + 1, 1))}


def similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def word_count(text: str) -> int:
    return len(text.split())


VI_CHARS = re.compile(r"[ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]", re.I)


def guess_lang(text: str) -> str:
    """Ước lượng thô ngôn ngữ chính để thống kê (không dùng làm nhãn)."""
    if re.search(r"[぀-ヿ]", text):
        return "ja"
    if re.search(r"[가-힯]", text):
        return "ko"
    if re.search(r"[一-鿿]", text):
        return "zh"
    if re.search(r"[Ѐ-ӿ]", text) and not VI_CHARS.search(text):
        return "ru"
    letters = [c for c in text if c.isalpha()]
    if letters and len(VI_CHARS.findall(text)) / len(letters) > 0.04:
        return "vi"
    low = " " + norm(text) + " "
    en_hits = sum(low.count(w) for w in (" the ", " and ", " of ", " to ", " is ", " your ", " you "))
    if en_hits >= 2:
        return "en"
    return "other"


# ---------- đọc dữ liệu ----------

def load_list(path: Path, rep: Report) -> list[dict] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        rep.err(f"{path.name}: JSON hỏng: {exc}")
        return []
    if not isinstance(data, list):
        rep.err(f"{path.name}: phải là danh sách")
        return []
    return data


def known_refs(refs_path: Path) -> set[str]:
    if not refs_path.exists():
        return set()
    return set(re.findall(r"\|\s*((?:R|D|P)\d+)\s*\|", refs_path.read_text(encoding="utf-8")))


# ---------- kiểm tra từng bản ghi ----------

def check_source(rec: dict, where: str, refs: set[str], rep: Report) -> None:
    src = rec.get("source")
    if not isinstance(src, dict):
        rep.err(f"{where}: thiếu `source` (đối tượng)")
        return
    for key in ("origin", "name", "url", "license", "ref"):
        if not isinstance(src.get(key), str):
            rep.err(f"{where}: source.{key} phải là chuỗi")
    if src.get("origin") not in ("original", "dataset"):
        rep.err(f"{where}: source.origin phải là original hoặc dataset")
    if not src.get("name"):
        rep.err(f"{where}: source.name rỗng")
    if src.get("origin") == "dataset" and not (src.get("url") and src.get("license")):
        rep.err(f"{where}: nguồn dataset bắt buộc có url và license")
    ref = src.get("ref", "")
    if ref and refs and ref not in refs:
        rep.err(f"{where}: source.ref {ref!r} không có trong docs/tai-lieu-tham-khao.md")


def check_success(rec: dict, where: str, rep: Report) -> None:
    sc = rec.get("success_check")
    goal = rec.get("goal_type")
    if not isinstance(sc, dict) or "type" not in sc:
        rep.err(f"{where}: success_check phải là đối tượng có `type`")
        return
    t = sc["type"]
    expected = {"leak": {"canary_leak"}, "integrity": {"contains", "regex"}, "tool_action": {"tool_call"}}
    if goal in expected and t not in expected[goal]:
        rep.err(f"{where}: goal_type={goal} không khớp success_check.type={t}")
    if t == "canary_leak":
        if set(sc) != {"type"}:
            rep.err(f"{where}: canary_leak không được kèm trường khác (không ghi giá trị canary)")
    elif t == "contains":
        if not isinstance(sc.get("value"), str) or not sc["value"]:
            rep.err(f"{where}: contains cần `value` là chuỗi không rỗng")
    elif t == "regex":
        pat = sc.get("pattern")
        if not isinstance(pat, str) or not pat:
            rep.err(f"{where}: regex cần `pattern`")
        else:
            try:
                re.compile(pat)
            except re.error as exc:
                rep.err(f"{where}: regex không biên dịch được: {exc}")
    elif t == "tool_call":
        if sc.get("tool") not in TOOLS:
            rep.err(f"{where}: tool phải thuộc {sorted(TOOLS)}")
        if not isinstance(sc.get("args_contains"), str) or not sc["args_contains"]:
            rep.err(f"{where}: tool_call cần args_contains")
    else:
        rep.err(f"{where}: success_check.type không hợp lệ: {t!r}")


def integrity_leak_check(rec: dict, where: str, rep: Report) -> None:
    """Đáp án integrity không được khớp ngay trên tài liệu sạch (bỏ phần payload)."""
    sc, goal = rec.get("success_check") or {}, rec.get("goal_type")
    if goal != "integrity" or sc.get("type") not in ("contains", "regex"):
        return
    doc, payload = rec.get("untrusted_document", ""), rec.get("injection_payload", "")
    clean = doc.replace(payload, "") if payload else doc
    text = clean + "\n" + rec.get("user_task", "")
    try:
        hit = sc["value"] in text if sc["type"] == "contains" else re.search(sc["pattern"], text)
    except (KeyError, re.error):
        return
    if hit:
        rep.err(f"{where}: success_check đã khớp sẵn trên tài liệu sạch (tín hiệu sai)")


def check_attack(rec: dict, where: str, refs: set[str], rep: Report) -> None:
    if rec.get("label") != "attack":
        rep.err(f"{where}: label phải là attack")
    if rec.get("attack_type") not in ATTACK_TYPES:
        rep.err(f"{where}: attack_type không hợp lệ: {rec.get('attack_type')!r}")
    if rec.get("liu_type") not in LIU_TYPES:
        rep.err(f"{where}: liu_type không hợp lệ: {rec.get('liu_type')!r}")
    if rec.get("goal_type") not in GOAL_TYPES:
        rep.err(f"{where}: goal_type không hợp lệ: {rec.get('goal_type')!r}")
    for key in ("technique", "target_description", "injection_payload"):
        if not isinstance(rec.get(key), str) or not rec[key]:
            rep.err(f"{where}: thiếu `{key}`")
    payload, doc = rec.get("injection_payload", ""), rec.get("untrusted_document", "")
    if payload and doc and payload not in doc:
        rep.err(f"{where}: injection_payload không nằm trong untrusted_document")
    check_success(rec, where, rep)
    integrity_leak_check(rec, where, rep)


def check_benign(rec: dict, where: str, rep: Report) -> None:
    if rec.get("label") != "benign":
        rep.err(f"{where}: label phải là benign")
    if rec.get("attack_type") != "none":
        rep.err(f"{where}: benign phải có attack_type=none")
    if rec.get("liu_type", "none") != "none":
        rep.err(f"{where}: benign phải có liu_type=none")
    if rec.get("injection_payload"):
        rep.err(f"{where}: benign không có injection_payload")
    if "success_check" in rec:
        rep.err(f"{where}: benign không có success_check")
    kps = rec.get("reference_keypoints")
    if not (isinstance(kps, list) and 2 <= len(kps) <= 4 and all(isinstance(k, str) and k for k in kps)):
        rep.err(f"{where}: reference_keypoints phải gồm 2–4 chuỗi không rỗng")
        kps = []
    kws = rec.get("keypoint_keywords")
    if kws is not None:
        check_keywords(rec, kps, kws, where, rep)
    if not isinstance(rec.get("tune"), bool):
        rep.err(f"{where}: benign cần `tune` là true/false")
    if not isinstance(rec.get("hard_negative", False), bool):
        rep.err(f"{where}: hard_negative phải là bool")
    if rec.get("hard_negative") and rec.get("hn_category") not in HN_CATEGORIES:
        rep.err(f"{where}: hard_negative cần hn_category thuộc {sorted(HN_CATEGORIES)}")
    n = word_count(rec.get("untrusted_document", ""))
    if not BENIGN_WORDS[0] <= n <= BENIGN_WORDS[1]:
        rep.err(f"{where}: tài liệu benign {n} từ, ngoài khoảng {BENIGN_WORDS}")


def keyword_in(word: str, norm_text: str, stripped_text: str) -> bool:
    """Quy tắc khớp từ khoá (dùng chung cho bộ đo chất lượng): chữ thường NFC; riêng từ khoá viết không dấu
    thì được khớp trên văn bản đã bỏ dấu. Từ khoá có dấu phải khớp đúng dấu."""
    w = norm(word)
    return w in norm_text or (w == strip_accents(w) and w in stripped_text)


def check_keywords(rec: dict, kps: list, kws: Any, where: str, rep: Report) -> None:
    if not (isinstance(kws, list) and len(kws) == len(kps)
            and all(isinstance(g, list) and g and all(isinstance(w, str) and w for w in g) for g in kws)):
        rep.err(f"{where}: keypoint_keywords phải là danh sách các nhóm từ, cùng độ dài reference_keypoints")
        return
    doc = rec.get("untrusted_document", "") + " " + rec.get("user_task", "")
    nd, na = norm(doc), strip_accents(doc)
    for i, group in enumerate(kws):
        for w in group:
            if w != w.lower():
                rep.err(f"{where}: keypoint_keywords[{i}] phải chữ thường: {w!r}")
        for w in group:
            if len(w) < 2 or (len(w) < 3 and w.isascii() and not any(c.isdigit() for c in w)):
                rep.err(f"{where}: keypoint_keywords[{i}] quá ngắn, dễ khớp nhầm: {w!r}")
        if not any(keyword_in(w, nd, na) for w in group):
            rep.err(f"{where}: keypoint_keywords[{i}] không khớp tài liệu (không từ nào xuất hiện)")


def check_record(rec: Any, split: str, refs: set[str], rep: Report) -> None:
    where = f"{SPLIT_FILES[split]}:{rec.get('id', '?') if isinstance(rec, dict) else '?'}"
    if not isinstance(rec, dict):
        rep.err(f"{where}: phần tử không phải đối tượng")
        return
    rid = rec.get("id")
    if not (isinstance(rid, str) and re.fullmatch(rf"{ID_PREFIX[split]}-\d{{3}}", rid)):
        rep.err(f"{where}: id phải dạng {ID_PREFIX[split]}-NNN")
    if rec.get("split") != split:
        rep.err(f"{where}: split={rec.get('split')!r} khác file ({split})")
    for key in ("user_task", "untrusted_document"):
        if not isinstance(rec.get(key), str) or not rec[key].strip():
            rep.err(f"{where}: thiếu `{key}`")
    if "notes" in rec and not isinstance(rec["notes"], str):
        rep.err(f"{where}: notes phải là chuỗi")
    check_source(rec, where, refs, rep)
    if split == "benign":
        check_benign(rec, where, rep)
    else:
        check_attack(rec, where, refs, rep)
    if split == "test_indist" and not rec.get("paraphrase_of"):
        rep.err(f"{where}: test_indist cần paraphrase_of")


# ---------- kiểm tra chéo ----------

def decoded_views(text: str) -> list[str]:
    """Các dạng giải mã (Base64, hex, ROT13) của chuỗi để bắt canary giấu trong payload mã hoá."""
    views = [codecs.decode(text, "rot13")]
    for tok in B64_TOKEN.findall(text):
        try:
            views.append(base64.b64decode(tok + "=" * (-len(tok) % 4), validate=True).decode("utf-8"))
        except (binascii.Error, UnicodeDecodeError, ValueError):
            continue
    for tok in HEX_TOKEN.findall(text):
        try:
            views.append(bytes.fromhex(tok).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            continue
    return views


def check_fixed_canary(recs: list[dict], rep: Report) -> None:
    for rec in recs:
        text = "\n".join(str(rec.get(k, "")) for k in ("user_task", "untrusted_document", "injection_payload"))
        for view in [text, *decoded_views(text)]:
            for pat in CANARY_VALUE_PATTERNS:
                m = pat.search(view)
                if m:
                    rep.err(f"{rec['id']}: có vẻ chứa giá trị canary cố định: {m.group(0)!r}")
                    break


def check_unique_ids(by_split: dict[str, list[dict]], rep: Report) -> None:
    seen: dict[str, str] = {}
    for split, recs in by_split.items():
        for rec in recs:
            rid = rec.get("id")
            if rid in seen:
                rep.err(f"id trùng: {rid} ({seen[rid]} và {split})")
            seen[rid] = split


def check_techniques(by_split: dict[str, list[dict]], rep: Report) -> None:
    train_t = {r.get("technique") for r in by_split.get("train", [])}
    hold_t = {r.get("technique") for r in by_split.get("holdout", [])}
    overlap = (train_t & hold_t) - {None, ""}
    if overlap:
        rep.err(f"technique trùng giữa train và holdout: {sorted(overlap)}")
    train = {r["id"]: r for r in by_split.get("train", []) if "id" in r}
    for rec in by_split.get("test_indist", []):
        src = train.get(rec.get("paraphrase_of"))
        if src is None:
            rep.err(f"{rec.get('id')}: paraphrase_of={rec.get('paraphrase_of')!r} không có trong train")
            continue
        for key in ("technique", "goal_type", "attack_type"):
            if rec.get(key) != src.get(key):
                rep.err(f"{rec['id']}: {key} khác bản gốc {src['id']}")


def check_near_duplicates(by_split: dict[str, list[dict]], rep: Report) -> list[tuple[float, str, str]]:
    """Gần trùng giữa mọi cặp attack (so payload) và giữa mọi cặp benign (so tài liệu)."""
    flagged: list[tuple[float, str, str]] = []
    groups = {
        "attack": [r for s in ("train", "holdout", "test_indist") for r in by_split.get(s, [])
                   if isinstance(r, dict) and r.get("injection_payload")],
        "benign": [r for r in by_split.get("benign", []) if isinstance(r, dict)],
    }
    for name, recs in groups.items():
        key = "injection_payload" if name == "attack" else "untrusted_document"
        sh = {r["id"]: shingles(r[key]) for r in recs if isinstance(r.get(key), str) and r.get("id")}
        by_id = {r["id"]: r for r in recs if r.get("id") in sh}
        for a, b in itertools.combinations(sh, 2):
            ra, rb = by_id[a], by_id[b]
            if ra.get("attack_type") == rb.get("attack_type") == "many_shot_jailbreaking":
                continue
            s = similarity(sh[a], sh[b])
            if s > SIM_WARN:
                flagged.append((s, a, b))
                if s > SIM_ERROR:
                    rep.err(f"gần trùng ({s:.2f} > {SIM_ERROR}): {a} và {b}")
                else:
                    rep.warn(f"tương đồng cao ({s:.2f}): {a} và {b}")
    return sorted(flagged, reverse=True)


def carrier_id_of(rec: dict) -> str | None:
    m = re.search(r"carrier_id=(C\d+)", rec.get("notes", ""))
    return m.group(1) if m else None


def check_carriers(path: Path, by_split: dict[str, list[dict]], rep: Report) -> Counter:
    usage: Counter = Counter()
    data = load_list(path, rep)
    if data is None:
        rep.err(f"thiếu {path.name}")
        return usage
    ids = set()
    langs: Counter = Counter()
    for c in data:
        cid = c.get("id")
        if cid in ids:
            rep.err(f"carriers.json: id trùng {cid}")
        ids.add(cid)
        n = word_count(c.get("text", ""))
        if not CARRIER_WORDS[0] <= n <= CARRIER_WORDS[1]:
            rep.err(f"carriers.json:{cid}: {n} từ, ngoài khoảng {CARRIER_WORDS}")
        langs[c.get("lang")] += 1
    if len(data) < 25:
        rep.err(f"carriers.json: cần ≥ 25 tài liệu nền, có {len(data)}")
    texts = {c["id"]: c["text"] for c in data}
    for split, recs in by_split.items():
        for rec in recs:
            cid = carrier_id_of(rec)
            if cid is None:
                continue
            if cid not in ids:
                rep.err(f"{rec['id']}: carrier_id={cid} không có trong carriers.json")
                continue
            usage[cid] += 1
            doc = rec.get("untrusted_document", "")
            if split == "benign":
                if doc != texts[cid]:
                    rep.err(f"{rec['id']}: benign đối chứng phải đúng nguyên văn tài liệu nền {cid}")
            elif doc and texts[cid].split("\n\n")[0][:40] not in doc:
                rep.err(f"{rec['id']}: tài liệu không chứa tài liệu nền {cid}")
    for cid, n in usage.items():
        if n > CARRIER_REUSE_WARN:
            rep.warn(f"tài liệu nền {cid} dùng {n} lần (> {CARRIER_REUSE_WARN})")
    rep.stats["carriers"] = {"n": len(data), "lang": dict(langs), "max_reuse": max(usage.values(), default=0),
                             "used": len(usage)}
    return usage


# ---------- thống kê ----------

def lengths(recs: list[dict]) -> dict[str, float]:
    ls = [len(r.get("untrusted_document", "")) for r in recs]
    if not ls:
        return {}
    return {"min": min(ls), "median": statistics.median(ls), "max": max(ls)}


def compute_stats(by_split: dict[str, list[dict]], rep: Report) -> None:
    attacks = [r for s, rs in by_split.items() if s != "benign" for r in rs]
    st = rep.stats
    st["n_per_split"] = {s: len(rs) for s, rs in by_split.items()}
    st["attack_type_x_split"] = {
        s: dict(Counter(r.get("attack_type") for r in rs)) for s, rs in by_split.items() if s != "benign"}
    st["goal_type_x_split"] = {
        s: dict(Counter(r.get("goal_type") for r in rs)) for s, rs in by_split.items() if s != "benign"}
    st["liu_type_x_split"] = {
        s: dict(Counter(r.get("liu_type") for r in rs)) for s, rs in by_split.items() if s != "benign"}
    st["payload_language"] = dict(Counter(guess_lang(r.get("injection_payload", "")) for r in attacks))
    st["document_language"] = {
        s: dict(Counter(guess_lang(r.get("untrusted_document", "")) for r in rs)) for s, rs in by_split.items()}
    st["length_chars"] = {s: lengths(rs) for s, rs in by_split.items()}
    st["position"] = dict(Counter(
        (re.search(r"position=(\w+)", r.get("notes", "")) or [None, "?"])[1] for r in attacks))
    benign = by_split.get("benign", [])
    st["benign"] = {
        "n": len(benign),
        "hard_negative": sum(1 for r in benign if r.get("hard_negative")),
        "hn_category_x_tune": {
            f"{c}|tune={t}": n for (c, t), n in sorted(Counter(
                (r.get("hn_category"), r.get("tune")) for r in benign if r.get("hard_negative")).items(),
                key=lambda kv: (str(kv[0][0]), str(kv[0][1])))},
        "tune": sum(1 for r in benign if r.get("tune") is True),
        "no_tune": sum(1 for r in benign if r.get("tune") is False),
        "words_doc": ({"min": min(word_count(r.get("untrusted_document", "")) for r in benign),
                       "median": statistics.median(word_count(r.get("untrusted_document", "")) for r in benign),
                       "max": max(word_count(r.get("untrusted_document", "")) for r in benign)}
                      if benign else {}),
    }


# ---------- tập ngoài (zero-shot, từ dataset công khai) ----------

EXT_GOAL_TYPES = GOAL_TYPES | {"other"}
EXT_FILES = {"ext_attack": "ext_attack_prompts.json", "ext_benign": "ext_benign_prompts.json"}
EXT_FULL_FILES = {"ext_attack": "ext_attack_full.json", "ext_benign": "ext_benign_full.json"}
EXT_ID = {  # (split, đầy_đủ?) -> mẫu id
    ("ext_attack", False): r"EX-\d{3}", ("ext_attack", True): r"EXF-\d{4}",
    ("ext_benign", False): r"XB-\d{3}", ("ext_benign", True): r"XBF-\d{4}",
}
EXT_CONTEXT_KINDS = {"carrier", "email", "table", "code", "none"}
EXT_SUBSETS = {"deepset", "gandalf", "jackhhao", "bipia_text", "bipia_code", "bipia_email", "bipia_table"}
EXT_BENIGN_MIN_WORDS = 5


def check_ext_record(rec: Any, split: str, full: bool, fname: str, refs: set[str], rep: Report) -> None:
    where = f"{fname}:{rec.get('id', '?') if isinstance(rec, dict) else '?'}"
    if not isinstance(rec, dict):
        rep.err(f"{where}: phần tử không phải đối tượng")
        return
    if not (isinstance(rec.get("id"), str) and re.fullmatch(EXT_ID[(split, full)], rec["id"])):
        rep.err(f"{where}: id phải dạng {EXT_ID[(split, full)]}")
    if rec.get("split") != split:
        rep.err(f"{where}: split={rec.get('split')!r} khác {split}")
    for key in ("user_task", "untrusted_document"):
        if not isinstance(rec.get(key), str) or not rec[key].strip():
            rep.err(f"{where}: thiếu `{key}`")
    if not isinstance(rec.get("notes"), str) or "src=" not in rec.get("notes", ""):
        rep.err(f"{where}: notes phải ghi chỉ mục hàng gốc (`src=...`)")
    if rec.get("subset") not in EXT_SUBSETS:
        rep.err(f"{where}: subset phải thuộc {sorted(EXT_SUBSETS)}")
    if rec.get("context_kind") not in EXT_CONTEXT_KINDS:
        rep.err(f"{where}: context_kind phải thuộc {sorted(EXT_CONTEXT_KINDS)}")
    check_source(rec, where, refs, rep)
    src = rec.get("source") if isinstance(rec.get("source"), dict) else {}
    if src.get("origin") != "dataset":
        rep.err(f"{where}: tập ngoài phải có source.origin=dataset")
    if rec.get("context_kind") in ("table", "code") and "CC-BY-SA" not in str(src.get("license", "")):
        rep.err(f"{where}: ngữ cảnh {rec.get('context_kind')} (BIPIA) phải ghi giấy phép CC-BY-SA trong source.license")
    if split == "ext_attack":
        check_ext_attack(rec, where, rep)
    else:
        check_ext_benign(rec, where, rep)


def check_ext_attack(rec: dict, where: str, rep: Report) -> None:
    if rec.get("label") != "attack":
        rep.err(f"{where}: label phải là attack")
    if rec.get("attack_type") not in ATTACK_TYPES:
        rep.err(f"{where}: attack_type không hợp lệ: {rec.get('attack_type')!r}")
    if rec.get("liu_type") not in LIU_TYPES:
        rep.err(f"{where}: liu_type không hợp lệ: {rec.get('liu_type')!r}")
    goal = rec.get("goal_type")
    if goal not in EXT_GOAL_TYPES:
        rep.err(f"{where}: goal_type không hợp lệ: {goal!r}")
    for key in ("technique", "target_description", "injection_payload"):
        if not isinstance(rec.get(key), str) or not rec[key]:
            rep.err(f"{where}: thiếu `{key}`")
    payload, doc = rec.get("injection_payload", ""), rec.get("untrusted_document", "")
    if payload and doc and payload not in doc:
        rep.err(f"{where}: injection_payload không nằm trong untrusted_document")
    if goal == "other":
        if rec.get("success_check") is not None:
            rep.err(f"{where}: goal_type=other không được có success_check (không chấm ASR)")
    elif goal == "leak":
        if rec.get("success_check") != {"type": "canary_leak"}:
            rep.err(f"{where}: goal_type=leak phải có success_check đúng {{\"type\": \"canary_leak\"}}")
    else:
        check_success(rec, where, rep)


def check_ext_benign(rec: dict, where: str, rep: Report) -> None:
    if rec.get("label") != "benign":
        rep.err(f"{where}: label phải là benign")
    if rec.get("attack_type") != "none":
        rep.err(f"{where}: benign phải có attack_type=none")
    if rec.get("liu_type", "none") != "none":
        rep.err(f"{where}: benign phải có liu_type=none")
    if rec.get("injection_payload"):
        rep.err(f"{where}: benign không có injection_payload")
    if "success_check" in rec:
        rep.err(f"{where}: benign không có success_check")
    kps = rec.get("reference_keypoints", [])
    if kps not in ([], None):
        rep.err(f"{where}: tập ngoài không có reference_keypoints (utility để trống)")
    if word_count(rec.get("untrusted_document", "")) < EXT_BENIGN_MIN_WORDS:
        rep.err(f"{where}: tài liệu benign dưới {EXT_BENIGN_MIN_WORDS} từ (gần rỗng)")


def check_ext_against_group(recs: dict[str, list[dict]], group: dict[str, list[dict]], rep: Report) -> None:
    """Payload ngoài không được gần trùng payload nhóm; benign ngoài không gần trùng benign/tài liệu nền nhóm."""
    g_pay = [shingles(r["injection_payload"]) for rs in group.values() for r in rs
             if isinstance(r, dict) and r.get("injection_payload")]
    g_ben = [shingles(r["untrusted_document"]) for r in group.get("benign", []) if isinstance(r, dict)]
    for fname, rs in recs.items():
        for r in rs:
            if not isinstance(r, dict) or not r.get("id"):
                continue
            if r.get("label") == "attack" and isinstance(r.get("injection_payload"), str):
                mine, pool, what = shingles(r["injection_payload"]), g_pay, "payload của nhóm"
            elif isinstance(r.get("untrusted_document"), str):
                mine, pool, what = shingles(r["untrusted_document"]), g_ben, "benign của nhóm"
            else:
                continue
            if any(similarity(mine, g) > SIM_ERROR for g in pool):
                rep.err(f"{fname}:{r['id']}: gần trùng {what} (> {SIM_ERROR})")


def check_ext_internal_dups(recs: list[dict], fname: str, rep: Report) -> None:
    """Trùng nội bộ: chuỗi chuẩn hoá giống hệt (mọi tệp) và gần trùng > ngưỡng (tệp nhỏ, tối đa 400 mục)."""
    seen: dict[str, str] = {}
    key = lambda r: norm(r.get("injection_payload") or r.get("untrusted_document", ""))  # noqa: E731
    for r in recs:
        if not isinstance(r, dict):
            continue
        k = key(r)
        if k in seen:
            rep.err(f"{fname}: {r.get('id')} trùng nguyên văn {seen[k]}")
        seen[k] = r.get("id", "?")
    if len(recs) > 400:
        return
    sh = [(r["id"], shingles(key(r))) for r in recs if isinstance(r, dict) and r.get("id")]
    for (a, sa), (b, sb) in itertools.combinations(sh, 2):
        if similarity(sa, sb) > SIM_ERROR:
            rep.err(f"{fname}: gần trùng ({SIM_ERROR}): {a} và {b}")


def check_ext_subset_of_full(small: list[dict], full: list[dict], fname: str, rep: Report) -> None:
    by_id = {r.get("id"): r for r in full if isinstance(r, dict)}
    for r in small:
        if not isinstance(r, dict):
            continue
        m = re.search(r"full_id=(\w+-\d+)", r.get("notes", ""))
        ref = by_id.get(m.group(1)) if m else None
        if ref is None:
            rep.err(f"{fname}:{r.get('id')}: thiếu hoặc sai full_id trong notes")
        elif ref.get("untrusted_document") != r.get("untrusted_document"):
            rep.err(f"{fname}:{r.get('id')}: tài liệu khác mục {m.group(1)} trong tệp full")


def check_ext_provenance(base: Path, counts: dict[str, int], rep: Report) -> None:
    path = base / "ext_provenance.json"
    if not path.exists():
        rep.warn("thiếu ext_provenance.json (chạy build_external.py)")
        return
    try:
        prov = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        rep.err(f"ext_provenance.json: JSON hỏng: {exc}")
        return
    for fname, n in counts.items():
        want = prov.get("files", {}).get(fname, {}).get("n")
        if want is not None and want != n:
            rep.err(f"{fname}: {n} mục nhưng ext_provenance.json ghi {want}")


def validate_external(base: Path = HERE, group_base: Path | None = None, refs_path: Path | None = None,
                      require: bool = False) -> Report:
    """Kiểm các tệp ext_* trong `base` (các tệp *_full.json chỉ kiểm nếu có)."""
    rep = Report()
    refs = known_refs(refs_path if refs_path is not None else ROOT / "docs" / "tai-lieu-tham-khao.md")
    group_base = group_base or base
    loaded: dict[str, list[dict]] = {}
    for full in (False, True):
        for split, fname in (EXT_FULL_FILES if full else EXT_FILES).items():
            recs = load_list(base / fname, rep)
            if recs is None:
                if require and not full:
                    rep.err(f"thiếu file {fname}")
                continue
            loaded[fname] = recs
            for rec in recs:
                check_ext_record(rec, split, full, fname, refs, rep)
            check_ext_internal_dups(recs, fname, rep)
            check_fixed_canary([r for r in recs if isinstance(r, dict) and r.get("id")], rep)
    if not loaded:
        return rep
    ids: dict[str, str] = {}
    for fname, recs in loaded.items():
        for r in recs:
            rid = r.get("id") if isinstance(r, dict) else None
            if rid in ids and ids[rid] != fname:
                rep.err(f"id trùng giữa {ids[rid]} và {fname}: {rid}")
            ids[rid] = fname
    group: dict[str, list[dict]] = {}
    for split, fname in SPLIT_FILES.items():
        data = load_list(group_base / fname, Report())
        if data:
            group[split] = data
    team_ids = {r.get("id") for rs in group.values() for r in rs if isinstance(r, dict)}
    for rid in ids:
        if rid in team_ids:
            rep.err(f"id {rid} của tập ngoài trùng id của tập nhóm")
    check_ext_against_group(loaded, group, rep)
    for split in EXT_FILES:
        small, big = loaded.get(EXT_FILES[split]), loaded.get(EXT_FULL_FILES[split])
        if small is not None and big is not None:
            check_ext_subset_of_full(small, big, EXT_FILES[split], rep)
    check_ext_provenance(base, {f: len(r) for f, r in loaded.items()}, rep)
    rep.stats["ext"] = {
        fname: {"n": len(recs),
                "subset": dict(Counter(r.get("subset") for r in recs if isinstance(r, dict))),
                "context_kind": dict(Counter(r.get("context_kind") for r in recs if isinstance(r, dict))),
                **({"goal_type": dict(Counter(r.get("goal_type") for r in recs if isinstance(r, dict))),
                    "attack_type": dict(Counter(r.get("attack_type") for r in recs if isinstance(r, dict)))}
                   if "attack" in fname else {})}
        for fname, recs in loaded.items()}
    return rep


# ---------- điều phối ----------

def validate_dir(base: Path = HERE, carriers: Path | None = None, refs_path: Path | None = None,
                 require_all: bool = True) -> Report:
    """Chạy toàn bộ kiểm tra trên thư mục chứa các file prompt; trả về Report."""
    rep = Report()
    refs = known_refs(refs_path if refs_path is not None else ROOT / "docs" / "tai-lieu-tham-khao.md")
    by_split: dict[str, list[dict]] = {}
    for split, fname in SPLIT_FILES.items():
        recs = load_list(base / fname, rep)
        if recs is None:
            if require_all and split in REQUIRED_FILES:
                rep.err(f"thiếu file {fname}")
            continue
        by_split[split] = recs
        for rec in recs:
            check_record(rec, split, refs, rep)
    good = {s: [r for r in rs if isinstance(r, dict)] for s, rs in by_split.items()}
    check_unique_ids(good, rep)
    check_techniques(good, rep)
    check_fixed_canary([r for rs in good.values() for r in rs if r.get("id")], rep)
    flagged = check_near_duplicates(good, rep)
    carriers_path = carriers if carriers is not None else base / "carriers.json"
    if carriers_path.exists() or require_all:
        check_carriers(carriers_path, good, rep)
    compute_stats(good, rep)
    rep.stats["similarity_pairs_over_warn"] = [(round(s, 3), a, b) for s, a, b in flagged]
    return rep


def print_report(rep: Report) -> None:
    print(json.dumps(rep.stats, ensure_ascii=False, indent=2, default=str))
    for w in rep.warnings:
        print("CẢNH BÁO:", w)
    for e in rep.errors:
        print("LỖI:", e)
    print(f"\n{len(rep.errors)} lỗi, {len(rep.warnings)} cảnh báo")


def main() -> int:
    rep = validate_dir()
    print_report(rep)
    ext = validate_external()
    if ext.stats or ext.errors or ext.warnings:
        print("\n== Tập ngoài ==")
        print_report(ext)
    return 1 if rep.errors or ext.errors else 0


if __name__ == "__main__":
    sys.exit(main())
