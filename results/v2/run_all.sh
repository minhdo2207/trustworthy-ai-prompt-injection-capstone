#!/bin/bash
# Giao thức v2 sau freeze-v2, chạy tuần tự (Ollama không tăng tốc khi chạy song song): chờ hold-out nhóm xong, rồi email LLMail,
# giai đoạn 1b (train + benign), ablation hold-out, phát hiện hold-out.
cd "$(dirname "$0")/../.."
while pgrep -f "eval_asr.py.*stage2b-main" > /dev/null; do sleep 10; done
bash results/v2/run_v2.sh lm
bash results/v2/run_v2.sh stage1b
bash results/v2/run_v2.sh hold-abl
bash results/v2/run_v2.sh det-hold
echo "[$(date +%H:%M:%S)] V2 ALL DONE"
