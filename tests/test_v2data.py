"""Dữ liệu v2: tập chỉnh và hold-out không trùng nhau, hold-out LLMail không lẫn email đã xem ở v1, schema chạy được."""
import json
import re
import sys
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DATA = ROOT / "attack_prompts"

from defenses import eval_asr as E  # noqa: E402


def norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", s or "").casefold()).strip()


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def test_tune_and_hold_are_disjoint():
    tune = {norm(i["text"]) for i in load("v2_detection_tune.json")}
    hold = [norm(i["text"]) for i in load("v2_detection_hold.json")]
    assert not tune & set(hold)
    assert len(hold) == len(set(hold))


def test_hold_llmail_excludes_v1_set_b():
    v1 = {norm(i["text"]) for i in load("ext2_detection_full.json") if i["subset"] == "llmail" and i["label"] == "attack"}
    hold = {norm(i["text"]) for i in load("v2_detection_hold.json") if i["label"] == "attack"}
    e2e = {norm(p["untrusted_document"]) for p in load("lm_attack_prompts.json")}
    assert not v1 & hold and not v1 & e2e
    assert not hold & e2e                       # phát hiện và chạy cả hệ thống không dùng chung email


def test_tune_has_no_hold_out_sources():
    subsets = {i["subset"] for i in load("v2_detection_tune.json")}
    assert "lm_phase2" not in subsets and "lm_benign_hold" not in subsets
    assert {"team_train", "team_benign_tune", "lm_phase1", "B_mirror"} <= subsets


def test_benign_tune_and_hold_split_of_llmail_emails():
    t = {norm(p["untrusted_document"]) for p in load("lm_tune_benign_prompts.json")}
    h = {norm(p["untrusted_document"]) for p in load("lm_benign_prompts.json")}
    assert t and h and not t & h


@pytest.mark.parametrize("split,n", [("lm_attack", 500), ("lm_benign", 80), ("lm_tune_benign", 80)])
def test_harness_loads_lm_splits(split, n):
    assert len(E.load_prompts(split, DATA)) == n


def test_lm_hold_out_splits_are_guarded():
    with pytest.raises(SystemExit):
        E._guard_holdout(["lm_attack"], confirmed=False)
    with pytest.raises(SystemExit):
        E._guard_holdout(["lm_benign"], confirmed=False)
    E._guard_holdout(["lm_tune_benign"], confirmed=False)    # benign tune không bị khoá
