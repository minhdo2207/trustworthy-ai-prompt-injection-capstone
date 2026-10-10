#!/usr/bin/env bash
# Biên dịch báo cáo bằng tectonic (tự chạy BibTeX và lặp lại số lần cần thiết).
# Dùng: ./build.sh [--keep-logs]   -> sinh main.pdf trong thư mục này.
set -euo pipefail
cd "$(dirname "$0")"
TECTONIC="${TECTONIC:-$(command -v tectonic || echo /opt/homebrew/bin/tectonic)}"
if [ ! -x "$TECTONIC" ]; then
  echo "Không tìm thấy tectonic. Cài bằng 'brew install tectonic' hoặc đặt biến TECTONIC." >&2
  exit 1
fi
# Sinh phụ lục prompt (cần dữ liệu prompt; bỏ qua nếu đã có tệp và SKIP_APPENDIX=1)
if [ "${SKIP_APPENDIX:-0}" != "1" ] && [ -f scripts/gen_appendix.py ]; then
  python3 scripts/gen_appendix.py || echo "Cảnh báo: gen_appendix.py lỗi, dùng tệp phụ lục hiện có." >&2
fi
LOG=$(mktemp)
"$TECTONIC" main.tex "$@" 2>&1 | tee "$LOG" | grep -Ev '^note: (downloading|Running|Rerunning|Skipped|Writing)' || true
echo "--- Tóm tắt cảnh báo ---"
echo "Overfull: $(grep -c 'Overfull' "$LOG" || true)  Underfull: $(grep -c 'Underfull' "$LOG" || true)"
echo "Tham chiếu chưa định nghĩa: $(grep -c 'undefined' "$LOG" || true)"
echo "Trích dẫn thiếu (bibtex): $(grep -ci 'I didn.t find' "$LOG" || true)"
rm -f "$LOG"
echo "Xong: $(pwd)/main.pdf"
