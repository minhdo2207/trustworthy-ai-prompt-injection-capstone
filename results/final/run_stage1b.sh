#!/bin/bash
cd /Users/mac/Webcraler/capstone-wt/main
export CAPSTONE_MODEL=qwen3:8b
run() { local out=$1; shift
  for attempt in 1 2 3; do
    echo "[$(date +%H:%M:%S)] $out attempt $attempt"
    python3 defenses/eval_asr.py "$@" --out "$out" --resume > "$out.log" 2>&1 && return 0
    echo "[$(date +%H:%M:%S)] $out failed (attempt $attempt)"; sleep 20
  done; return 1; }
run results/dev/l4-chain-calib --configs L1+L2+L3+L4 --splits benign --samples 1
echo "[$(date +%H:%M:%S)] CALIB DONE"
run results/final/stage1-chain --configs baseline,L1,L1+L2,L1+L2+L3 --splits train,benign --samples 3
echo "[$(date +%H:%M:%S)] STAGE1B DONE"
