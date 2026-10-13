#!/bin/bash
# Hiệu chỉnh L4 trong chuỗi (L1+L2+L3+L4) trên benign TUNE (42 tài liệu của nhóm + 80 email LLMail), 1 mẫu.
cd "$(dirname "$0")/../.."
export CAPSTONE_MODEL=qwen3:8b
python3 defenses/eval_asr.py --configs L1+L2+L3+L4 --splits benign,lm_tune_benign --samples 1 \
  --data-dir results/v2/calib_data --out results/v2/l4-calib --resume
