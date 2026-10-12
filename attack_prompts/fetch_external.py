"""Tải dữ liệu công khai (tập ngoài) về `results/dev/external_raw/` để dựng tập kiểm tra zero-shot.

Chạy: python3 attack_prompts/fetch_external.py [--out DIR] [--only deepset,gandalf,jackhhao,bipia] [--force]

Nguồn (chỉ bốn nguồn sau, dung lượng tổng vài MB; không nguồn nào khác được phép):
  - deepset/prompt-injections           Hugging Face datasets-server /rows (Apache-2.0)
  - Lakera/gandalf_ignore_instructions  Hugging Face datasets-server /rows (MIT)
  - jackhhao/jailbreak-classification   Hugging Face datasets-server /rows (Apache-2.0)
  - microsoft/BIPIA                     tệp raw GitHub, ghim theo commit (MIT cho mã; dữ liệu có giấy phép riêng)

Mỗi tệp thô được kiểm số hàng (HF) hoặc số byte (GitHub) so với giá trị đã quan sát khi viết script;
sai lệch dừng với mã thoát 1 (dùng --allow-mismatch để ghi nhận sai lệch và chạy tiếp). Cuối cùng ghi
`manifest.json` (sha256, số hàng, số byte, thời điểm tải). Nếu có `attack_prompts/ext_provenance.json`
(do build_external.py ghi) thì so sha256 và cảnh báo khi nguồn đã đổi. Dữ liệu thô KHÔNG được commit.

Lỗi mạng: thử lại với lùi dần; hết lượt thử thì in thông báo rõ và thoát với mã 2.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "results" / "dev" / "external_raw"
PROVENANCE = ROOT / "attack_prompts" / "ext_provenance.json"

HF_ROWS = "https://datasets-server.huggingface.co/rows"
HF_SIZE = "https://datasets-server.huggingface.co/size"
BIPIA_COMMIT = "a004b69ec0dd446e0afd461d98cb5e96e120a5d0"
BIPIA_RAW = f"https://raw.githubusercontent.com/microsoft/BIPIA/{BIPIA_COMMIT}/"
PAGE = 100
RETRIES = 4
TIMEOUT_S = 60
MAX_TOTAL_BYTES = 60 * 1024 * 1024
USER_AGENT = "capstone-external-fetch/1.0 (research; contact: course project)"

# Số hàng quan sát được trên trang dataset (datasets-server /size) khi viết script.
HF_SOURCES = {
    "deepset": {"id": "deepset/prompt-injections", "splits": {"train": 546, "test": 116}},
    "gandalf": {"id": "Lakera/gandalf_ignore_instructions",
                "splits": {"train": 777, "validation": 111, "test": 112}},
    "jackhhao": {"id": "jackhhao/jailbreak-classification", "splits": {"train": 1044, "test": 262}},
}
# Số byte quan sát được qua API cây thư mục GitHub tại BIPIA_COMMIT.
BIPIA_FILES = {
    "LICENSE": 2642,
    "README.md": 9765,
    "benchmark/README.md": 2400,
    "benchmark/email/train.jsonl": 31586,
    "benchmark/email/test.jsonl": 30334,
    "benchmark/table/train.jsonl": 1638481,
    "benchmark/table/test.jsonl": 183302,
    "benchmark/code/train.jsonl": 125926,
    "benchmark/code/test.jsonl": 100451,
    "benchmark/text_attack_train.json": 5999,
    "benchmark/text_attack_test.json": 6322,
    "benchmark/code_attack_train.json": 16343,
    "benchmark/code_attack_test.json": 16356,
}


class FetchError(RuntimeError):
    """Lỗi tải cần báo rõ cho người chạy (mạng, kích thước, số hàng)."""


@dataclass
class Entry:
    key: str
    path: str
    rows: int | None
    bytes: int
    sha256: str
    url: str
    note: str = ""


def http_get(url: str, *, retries: int = RETRIES) -> bytes:
    """GET có thử lại. Lỗi 4xx (trừ 429) không thử lại vì không tự hết."""
    last: Exception | None = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            last = e
            if 400 <= e.code < 500 and e.code != 429:
                break
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e
        time.sleep(2.0 * (attempt + 1))
    raise FetchError(f"không tải được {url}: {last}. Kiểm tra kết nối mạng rồi chạy lại.")


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def fetch_hf_split(ds_id: str, split: str, expected: int) -> list[dict]:
    """Lấy mọi hàng của một split qua /rows. Trang nào có ô bị cắt thì tải lại từng hàng một."""
    rows: list[dict] = []
    offset, total = 0, None
    while total is None or offset < total:
        length = PAGE
        while True:
            q = urllib.parse.urlencode({"dataset": ds_id, "config": "default", "split": split,
                                        "offset": offset, "length": length})
            page = json.loads(http_get(f"{HF_ROWS}?{q}"))
            total = page["num_rows_total"]
            got = page["rows"]
            if any(r.get("truncated_cells") for r in got) and length > 1:
                length = max(1, length // 4)
                continue
            if any(r.get("truncated_cells") for r in got):
                raise FetchError(f"{ds_id}/{split}: ô bị cắt ở hàng {offset} ngay cả khi tải từng hàng")
            break
        if not got:
            raise FetchError(f"{ds_id}/{split}: trang rỗng tại offset {offset}/{total}")
        for r in got:
            rows.append({"row_idx": r["row_idx"], **r["row"]})
        offset += len(got)
    if len(rows) != total:
        raise FetchError(f"{ds_id}/{split}: tải {len(rows)} hàng, máy chủ báo {total}")
    return rows


def fetch_hf(key: str, out: Path, allow_mismatch: bool) -> list[Entry]:
    spec = HF_SOURCES[key]
    entries = []
    for split, expected in spec["splits"].items():
        rows = fetch_hf_split(spec["id"], split, expected)
        note = ""
        if len(rows) != expected:
            note = f"số hàng {len(rows)} khác giá trị kỳ vọng {expected}"
            if not allow_mismatch:
                raise FetchError(f"{spec['id']}/{split}: {note} (dùng --allow-mismatch để chấp nhận)")
            print(f"CẢNH BÁO: {spec['id']}/{split}: {note}", file=sys.stderr)
        data = (json.dumps(rows, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
        rel = f"{key}/{split}.json"
        write_bytes(out / rel, data)
        q = urllib.parse.urlencode({"dataset": spec["id"], "config": "default", "split": split})
        entries.append(Entry(f"{key}/{split}", rel, len(rows), len(data), sha256_of(data),
                             f"{HF_ROWS}?{q}", note))
        print(f"  {spec['id']}  {split:<10} {len(rows):>5} hàng", flush=True)
    return entries


def fetch_bipia(out: Path, allow_mismatch: bool) -> list[Entry]:
    entries = []
    for rel_remote, expected in BIPIA_FILES.items():
        data = http_get(BIPIA_RAW + rel_remote)
        note = ""
        if len(data) != expected:
            note = f"{len(data)} byte, kỳ vọng {expected}"
            if not allow_mismatch:
                raise FetchError(f"BIPIA {rel_remote}: {note} (dùng --allow-mismatch để chấp nhận)")
            print(f"CẢNH BÁO: BIPIA {rel_remote}: {note}", file=sys.stderr)
        rel = f"bipia/{rel_remote}"
        write_bytes(out / rel, data)
        rows = sum(1 for ln in data.decode("utf-8", "replace").splitlines() if ln.strip()) \
            if rel_remote.endswith(".jsonl") else None
        entries.append(Entry(f"bipia/{rel_remote}", rel, rows, len(data), sha256_of(data),
                             BIPIA_RAW + rel_remote, note))
        print(f"  BIPIA {rel_remote:<36} {len(data):>8} byte", flush=True)
    return entries


def hf_revisions() -> dict:
    """Ghi lại sha phiên bản của dataset trên Hugging Face (thông tin; /rows luôn trả bản mới nhất)."""
    out = {}
    for spec in HF_SOURCES.values():
        try:
            meta = json.loads(http_get(f"https://huggingface.co/api/datasets/{spec['id']}", retries=1))
            out[spec["id"]] = {"sha": meta.get("sha"), "lastModified": meta.get("lastModified"),
                               "license": (meta.get("cardData") or {}).get("license")}
        except (FetchError, ValueError):
            out[spec["id"]] = {"sha": None}
    return out


def compare_provenance(entries: list[Entry]) -> list[str]:
    if not PROVENANCE.exists():
        return []
    prev = json.loads(PROVENANCE.read_text(encoding="utf-8")).get("raw_sha256", {})
    return [f"{e.key}: sha256 khác lần dựng đã commit" for e in entries
            if e.key in prev and prev[e.key] != e.sha256]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--only", default="deepset,gandalf,jackhhao,bipia")
    ap.add_argument("--force", action="store_true", help="tải lại dù đã có manifest")
    ap.add_argument("--allow-mismatch", action="store_true",
                    help="chấp nhận sai lệch số hàng/số byte so với giá trị kỳ vọng")
    args = ap.parse_args(argv)
    wanted = [s.strip() for s in args.only.split(",") if s.strip()]
    bad = [s for s in wanted if s not in (*HF_SOURCES, "bipia")]
    if bad:
        print(f"LỖI: nguồn không được phép: {bad}", file=sys.stderr)
        return 1
    manifest_path = args.out / "manifest.json"
    if manifest_path.exists() and not args.force:
        print(f"Đã có {manifest_path}; dùng --force để tải lại.")
        return 0
    entries: list[Entry] = []
    try:
        for key in wanted:
            print(f"[{key}]", flush=True)
            entries += fetch_bipia(args.out, args.allow_mismatch) if key == "bipia" \
                else fetch_hf(key, args.out, args.allow_mismatch)
        total = sum(e.bytes for e in entries)
        if total > MAX_TOTAL_BYTES:
            raise FetchError(f"tổng dung lượng {total} byte vượt giới hạn {MAX_TOTAL_BYTES}")
    except FetchError as e:
        print(f"LỖI: {e}", file=sys.stderr)
        return 2
    manifest = {
        "fetched_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bipia_commit": BIPIA_COMMIT,
        "hf_revisions": hf_revisions() if any(k in HF_SOURCES for k in wanted) else {},
        "total_bytes": sum(e.bytes for e in entries),
        "files": {e.key: {"path": e.path, "rows": e.rows, "bytes": e.bytes, "sha256": e.sha256,
                          "url": e.url, "note": e.note} for e in entries},
    }
    write_bytes(manifest_path, (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode())
    for w in compare_provenance(entries):
        print(f"CẢNH BÁO: {w}", file=sys.stderr)
    print(f"[OK] {len(entries)} tệp, {manifest['total_bytes'] / 1024:.0f} KiB -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
