#!/bin/bash
# Giai đoạn 3: tập ngoài thứ hai (LLMail-Inject, chạy cả hệ thống). CHẠY ĐÚNG MỘT LẦN, cấu hình đã đóng băng.
cd "$(dirname "$0")/../.."
export CAPSTONE_MODEL=qwen3:8b
run() { local out=$1; shift
  for attempt in 1 2 3; do
    echo "[$(date +%H:%M:%S)] $out attempt $attempt"
    python3 defenses/eval_asr.py "$@" --out "$out" --resume --confirm-final-holdout > "$out.log" 2>&1 && return 0
    echo "[$(date +%H:%M:%S)] $out failed (attempt $attempt)"; sleep 20
  done; return 1; }
CHAIN=baseline,L1,L1+L2,L1+L2+L3,L1+L2+L3+L4
run results/final/stage3-ext2 --configs $CHAIN --splits ext2_attack,ext2_benign --samples 1
echo "[$(date +%H:%M:%S)] STAGE3 ALL DONE"
