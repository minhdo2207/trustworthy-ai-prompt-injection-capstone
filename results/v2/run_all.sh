#!/bin/bash
# Chạy toàn bộ giao thức v2 sau freeze-v2: giai đoạn 2b (hold-out, một lần) rồi 1b (train + benign).
cd "$(dirname "$0")/../.."
bash results/v2/run_v2.sh stage2b
bash results/v2/run_v2.sh stage1b
echo "[$(date +%H:%M:%S)] V2 ALL DONE"
