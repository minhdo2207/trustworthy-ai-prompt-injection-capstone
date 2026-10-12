#!/bin/bash
cd /Users/mac/Webcraler/capstone-wt/main
export CAPSTONE_MODEL=qwen3:8b
until grep -q "STAGE1B DONE" results/final/stage1b.log; do sleep 60; done
run() { local out=$1; shift
  for attempt in 1 2 3; do
    echo "[$(date +%H:%M:%S)] $out attempt $attempt"
    python3 defenses/eval_asr.py "$@" --out "$out" --resume > "$out.log" 2>&1 && return 0
    echo "[$(date +%H:%M:%S)] $out failed (attempt $attempt)"; sleep 20
  done; return 1; }
run results/final/stage1-chain --configs L1+L2+L3+L4 --splits train,benign --samples 3
echo "[$(date +%H:%M:%S)] L4 CHAIN DONE"
run results/final/stage1-abl --configs only_L2,only_L4 --splits train,benign --samples 1
echo "[$(date +%H:%M:%S)] ABL L2,L4 DONE"
run results/final/stage1-abl-l3 --configs only_L3 --splits train,benign --samples 1 --num-ctx 8192
echo "[$(date +%H:%M:%S)] STAGE1 ALL DONE"
