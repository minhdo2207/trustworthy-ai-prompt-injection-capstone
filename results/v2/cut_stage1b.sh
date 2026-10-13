#!/bin/bash
# Giai đoạn 1b: dừng sau lượt lấy mẫu 0 (một mẫu mỗi mục) để kịp thời hạn, rồi chạy ablation hold-out và phát hiện hold-out.
cd "$(dirname "$0")/../.."
while [ "$(python3 -c "import csv;print(sum(1 for _ in csv.DictReader(open('results/v2/stage1b-chain/results.csv'))))")" -lt 555 ]; do sleep 20; done
pkill -f "run_all.sh"; pkill -f "run_v2.sh"; pkill -f "eval_asr.py.*stage1b"; sleep 3
echo "[$(date +%H:%M:%S)] STAGE1B DONE (1 mẫu mỗi mục, cắt sau lượt 0)" >> results/v2/run_all.log
bash results/v2/run_v2.sh hold-abl >> results/v2/run_all.log 2>&1
bash results/v2/run_v2.sh det-hold >> results/v2/run_all.log 2>&1
echo "[$(date +%H:%M:%S)] V2 ALL DONE" >> results/v2/run_all.log
