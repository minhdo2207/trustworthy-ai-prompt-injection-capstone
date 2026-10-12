#!/bin/bash
# Giai đoạn 1: train + benign (không đụng hold-out). Tự chạy lại (--resume) nếu lỗi.
cd /Users/mac/Webcraler/capstone-wt/main
export CAPSTONE_MODEL=qwen3:8b
run() {  # run <out> <args...>
  local out=$1; shift
  for attempt in 1 2 3; do
    echo "[$(date +%H:%M:%S)] $out attempt $attempt"
    python3 defenses/eval_asr.py "$@" --out "$out" --resume > "$out.log" 2>&1 && return 0
    echo "[$(date +%H:%M:%S)] $out failed (attempt $attempt), see $out.log"; sleep 20
  done
  return 1
}
run results/final/stage1-chain --configs baseline,L1,L1+L2,L1+L2+L3,L1+L2+L3+L4 --splits train,benign --samples 3
run results/final/stage1-abl --configs only_L2,only_L3,only_L4 --splits train,benign --samples 1
echo "[$(date +%H:%M:%S)] STAGE1 DONE"
