#!/bin/bash
# Giao thức v2 (results/v2/PROTOCOL.md). Chạy sau khi gắn tag freeze-v2. Hold-out và LLMail gđ2 chạy ĐÚNG MỘT LẦN.
# Dùng: bash results/v2/run_v2.sh stage1b | stage2b
cd "$(dirname "$0")/../.."
export CAPSTONE_MODEL=qwen3:8b
CHAIN=baseline,L1,L1+L2,L1+L2+L3,L1+L2+L3+L4
run() { local out=$1; shift
  for attempt in 1 2 3; do
    echo "[$(date +%H:%M:%S)] $out attempt $attempt"
    python3 defenses/eval_asr.py "$@" --out "$out" --resume > "$out.log" 2>&1 && return 0
    echo "[$(date +%H:%M:%S)] $out failed (attempt $attempt)"; sleep 20
  done; return 1; }
case "$1" in
stage1b)
  run results/v2/stage1b-chain --configs $CHAIN --splits train,benign --samples 3
  run results/v2/stage1b-abl --configs only_L2,only_L4 --splits train,benign --samples 1
  run results/v2/stage1b-abl-l3 --configs only_L3 --splits train,benign --samples 1 --num-ctx 8192
  echo "[$(date +%H:%M:%S)] STAGE1B DONE";;
stage2b)
  run results/v2/stage2b-main --configs $CHAIN --splits holdout,test_indist --samples 2 --confirm-final-holdout
  run results/v2/stage2b-lm --configs $CHAIN --splits lm_attack,lm_benign --samples 1 --confirm-final-holdout
  run results/v2/stage2b-abl --configs only_L2,only_L4 --splits holdout --samples 1 --confirm-final-holdout
  run results/v2/stage2b-abl-l3 --configs only_L3 --splits holdout --samples 1 --num-ctx 8192 --confirm-final-holdout
  python3 defenses/eval_detection2.py --data attack_prompts/v2_detection_hold.json --out results/v2/detection-hold --resume
  echo "[$(date +%H:%M:%S)] STAGE2B DONE";;
*) echo "usage: $0 stage1b|stage2b"; exit 2;;
esac
