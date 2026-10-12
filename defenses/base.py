"""defenses/base.py — kiểu dữ liệu và hàm gọi Ollama dùng chung (xem docs/hop-dong-chung.md).

Biến môi trường:
  CAPSTONE_MODEL    model sinh mặc định (mặc định qwen3:8b; máy chưa cài thì đặt qwen2.5:7b)
  OLLAMA_HOST_URL   địa chỉ Ollama (mặc định http://localhost:11434)
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Literal, Optional

DEFAULT_HOST = os.environ.get("OLLAMA_HOST_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("CAPSTONE_MODEL", "qwen3:8b")
EMBED_MODEL = os.environ.get("CAPSTONE_EMBED_MODEL", "nomic-embed-text")


@dataclass
class LayerResult:
    """Kết quả của một lớp phòng thủ (hợp đồng chung, mục 2).

    Mở rộng so với hợp đồng gốc: thêm `user_suffix` (L3 dùng cho sandwich/nhắc lại
    sau khối dữ liệu).
    """
    action: Literal["pass", "block", "sanitize"]
    document: str
    score: Optional[float] = None
    reason: str = ""
    latency_ms: float = 0.0
    system_addendum: str = ""
    user_suffix: str = ""


def strip_think(text: str) -> str:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S | re.I)
    return re.sub(r"<think>.*$", "", text, flags=re.S | re.I).strip()


def _post(path: str, body: dict, host: Optional[str], timeout: int) -> dict:
    req = urllib.request.Request(
        (host or DEFAULT_HOST).rstrip("/") + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def ollama_chat(messages: list, model: Optional[str] = None, temperature: float = 0.0,
                seed: Optional[int] = None, num_predict: int = 400, think: bool = False,
                timeout: int = 300, retries: int = 2, host: Optional[str] = None,
                tools: Optional[list] = None, num_ctx: Optional[int] = None) -> dict:
    """Gọi /api/chat. Trả {"content", "tool_calls", "eval_count", "total_ms"}."""
    options = {"temperature": temperature, "num_predict": num_predict}
    if seed is not None:
        options["seed"] = seed
    if num_ctx:
        options["num_ctx"] = num_ctx
    body = {"model": model or DEFAULT_MODEL, "messages": messages, "stream": False,
            "think": think, "options": options}
    if tools:
        body["tools"] = tools
    last = None
    for attempt in range(retries + 1):
        t0 = time.perf_counter()
        try:
            d = _post("/api/chat", body, host, timeout)
            msg = d.get("message", {})
            return {
                "content": strip_think(msg.get("content", "") or ""),
                "tool_calls": msg.get("tool_calls") or [],
                "eval_count": d.get("eval_count", 0),
                "total_ms": (time.perf_counter() - t0) * 1000.0,
            }
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Ollama lỗi sau {retries + 1} lần thử: {last}")


def ollama_embed(texts: list, model: Optional[str] = None, host: Optional[str] = None,
                 timeout: int = 120) -> list:
    d = _post("/api/embed", {"model": model or EMBED_MODEL, "input": texts}, host, timeout)
    return d["embeddings"]


def cosine(a: list, b: list) -> float:
    num = sum(x * y for x, y in zip(a, b))
    da = sum(x * x for x in a) ** 0.5
    db = sum(y * y for y in b) ** 0.5
    return num / (da * db) if da and db else 0.0
