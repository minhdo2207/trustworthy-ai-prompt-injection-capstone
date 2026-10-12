#!/bin/bash
# Giai đoạn 2: hold-out, test_indist, dữ liệu ngoài. CHẠY ĐÚNG MỘT LẦN, cấu hình đã đóng băng (tag freeze-config-2).
cd /Users/mac/Webcraler/capstone-wt/main
export CAPSTONE_MODEL=qwen3:8b
until grep -q "STAGE1 ALL DONE" results/final/stage1c.log; do sleep 60; done
run() { local out=$1; shift
  for attempt in 1 2 3; do
    echo "[$(date +%H:%M:%S)] $out attempt $attempt"
    python3 defenses/eval_asr.py "$@" --out "$out" --resume --confirm-final-holdout > "$out.log" 2>&1 && return 0
    echo "[$(date +%H:%M:%S)] $out failed (attempt $attempt)"; sleep 20
  done; return 1; }
CHAIN=baseline,L1,L1+L2,L1+L2+L3,L1+L2+L3+L4
run results/final/stage2-main --configs $CHAIN --splits holdout,test_indist --samples 2
echo "[$(date +%H:%M:%S)] S2 MAIN DONE"
run results/final/stage2-ext --configs $CHAIN --splits ext_attack,ext_benign --samples 1
echo "[$(date +%H:%M:%S)] S2 EXT DONE"
run results/final/stage2-abl --configs only_L2,only_L4 --splits holdout --samples 1
run results/final/stage2-abl-l3 --configs only_L3 --splits holdout --samples 1 --num-ctx 8192
echo "[$(date +%H:%M:%S)] S2 ABL DONE"
python3 defenses/eval_detection.py --n-l2 150 --max-l2-calls 0 --out results/final/detection-l2 > results/final/detection-l2.log 2>&1
echo "[$(date +%H:%M:%S)] STAGE2 ALL DONE"
