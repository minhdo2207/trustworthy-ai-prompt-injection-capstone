# Defenses

- `layer1_filtering.py` — input sanitization/filtering.
- `layer2_refusal_classifier.py` — refusal classifier (vd. Llama Prompt Guard 2 hoặc LLM-as-judge).
- `layer3_instruction_hierarchy.py` — privileged-instruction separation / spotlighting.
- `layer4_consistency_check.py` — cải tiến mới: Dual-Response Consistency Check.
- `eval_asr.py` — script đo ASR cộng dồn qua từng lớp, trên cả train set và held-out set.
