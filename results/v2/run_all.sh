#!/bin/bash
# Reanuda: giai đoạn 1b (train + benign KHÔNG dùng để chỉnh, 42 tài liệu), ablation hold-out, phát hiện hold-out.
cd "$(dirname "$0")/../.."
bash results/v2/run_v2.sh stage1b
bash results/v2/run_v2.sh hold-abl
bash results/v2/run_v2.sh det-hold
echo "[$(date +%H:%M:%S)] V2 ALL DONE"
