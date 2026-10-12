"""Kiểm tra tập ngoài thứ hai (ext2): đếm, không trùng, schema chạy được trong harness, vẫn bị khoá sau cờ xác nhận."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DATA = ROOT / "attack_prompts"

from defenses import eval_asr as E  # noqa: E402


def _items():
    return json.loads((DATA / "ext2_detection_full.json").read_text(encoding="utf-8"))


def test_detection_set_has_unique_texts_and_known_subsets():
    items = _items()
    texts = [" ".join(i["text"].casefold().split()) for i in items if i["subset"] != "vi_deepset"]
    assert len(texts) == len(set(texts))
    assert {i["subset"] for i in items} == {"mirror", "spml", "llmail", "vi_deepset"}
    assert {i["label"] for i in items} == {"attack", "benign"}


def test_translated_deepset_is_flagged_not_independent():
    items = _items()
    assert all(not i["independent"] for i in items if i["subset"] == "vi_deepset")
    assert all(i["independent"] for i in items if i["subset"] != "vi_deepset")


def test_spml_excludes_gandalf_source():
    prov = json.loads((DATA / "ext2_provenance.json").read_text(encoding="utf-8"))
    assert prov["spml_gandalf_excluded"] > 0


@pytest.mark.parametrize("split,label", [("ext2_attack", "attack"), ("ext2_benign", "benign")])
def test_harness_loads_ext2_splits(split, label):
    prompts = E.load_prompts(split, DATA)
    assert prompts and all(p["label"] == label and p["split"] == split for p in prompts)
    if label == "attack":
        assert all(p["success_check"]["type"] == "tool_call" for p in prompts)


def test_ext2_requires_confirmation():
    with pytest.raises(SystemExit):
        E._guard_holdout(["ext2_attack"], confirmed=False)
    E._guard_holdout(["ext2_attack"], confirmed=True)
