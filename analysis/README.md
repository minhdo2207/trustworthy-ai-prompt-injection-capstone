# analysis — thống kê và bảng cho báo cáo

Phụ trách: Minh. Đọc `results/<run>/results.csv` (đúng 21 cột của `docs/hop-dong-chung.md`, mục 3) và sinh toàn bộ bảng,
dữ liệu biểu đồ và `report.md` (tiếng Việt, có ghi chú phương pháp để dán vào báo cáo). Chỉ dùng thư viện chuẩn và pandas;
Wilson và bootstrap tự cài trong `intervals.py`.

## Cách chạy

```bash
# từ thư mục gốc của repo
python3 -m analysis.stats results/<run>/results.csv                      # ra results/<run>/analysis/
python3 -m analysis.stats results/<run>/results.csv --out results/<run>/analysis \
    --benign-meta attack_prompts/benign_prompts.json                     # chỉ báo cáo benign tune:false
python3 -m analysis.stats results/a/results.csv results/b/results.csv --out results/merged/analysis   # gộp nhiều file
```

| Tuỳ chọn | Ý nghĩa |
|---|---|
| `--out DIR` | Thư mục ra. Mặc định: `<thư mục của CSV đầu tiên>/analysis` |
| `--benign-meta FILE` | `benign_prompts.json` để join `id -> tune`. Có thì bảng benign chính chỉ dùng `tune:false` (kèm Bảng 5b so sánh hai phần) |
| `--model NAME` | Bắt buộc khi CSV có nhiều model (không tự trộn model) |
| `--B N`, `--seed S` | Số lần bootstrap (mặc định 2000) và hạt giống (mặc định 20261009) |
| `--error-threshold X` | Cảnh báo nếu tỉ lệ dòng lỗi vượt X (mặc định 0.02) |

Mã thoát: 0 thành công; 2 nếu CSV vi phạm hợp đồng (thông báo nêu loại lỗi, số dòng, ví dụ `config/prompt_id/#sample`).
Cảnh báo (không dừng) được in ra stderr và ghi vào `report.md`. Khoảng 36 nghìn dòng chạy xong trong vài giây đến chục giây.

Chạy test: `python3 -m pytest tests/test_stats.py -q` (CSV tổng hợp do `tests/fixtures/make_stats_fixture.py` sinh,
đáp án tay tính nằm trong chú thích từng test).

## Đầu ra

```
<out>/report.md            tổng hợp tất cả bảng + ghi chú phương pháp + cảnh báo dữ liệu
<out>/tables/<tên>.tex     LaTeX booktabs (chỉ phần tabular; cần \usepackage{booktabs}); dùng \input{...}
<out>/tables/<tên>_<split>.tex   bản riêng cho từng split với bảng có cột split (tab01-04, 06-07, 09)
<out>/csv/<tên>.csv        số thật (không làm tròn) để xử lý tiếp
<out>/md/<tên>.md          markdown của từng bảng
<out>/dat/*.dat            dữ liệu pgfplots (cách nhau bằng dấu cách, tỉ lệ tính bằng %)
```

Tên bảng ổn định: `tab01_asr_split`, `tab02_asr_{attack_type,liu_type,goal_type}`, `tab03_cumulative`, `tab04_ablation`,
`tab05_benign`, `tab05b_benign_by_tune`, `tab06_cost`, `tab07_layers`, `tab07b_layer_increment`, `tab08_generalization`,
`tab09a_dead_summary`, `tab09b_dead_list`, `tab09c_effective_asr`, `tab10_errors`, `tab10b_error_types`.
Bảng không đủ dữ liệu (vd không có `baseline` thì không có Bảng 9) được bỏ qua và ghi ở mục "Bảng bị bỏ qua" của `report.md`.

Dùng trong LaTeX:

```latex
\begin{table}\centering\small
\input{results/run1/analysis/tables/tab03_cumulative_holdout.tex}
\caption{...}\end{table}
```

Biểu đồ cột có cận lỗi (`w_minus`/`w_plus` cho Wilson, `b_minus`/`b_plus` cho bootstrap; cột `label` đã thoát `_` dùng làm nhãn trục):

```latex
\begin{axis}[ybar, xtick=data, xticklabels from table={results/run1/analysis/dat/asr_holdout.dat}{label},
             error bars/y dir=both, error bars/y explicit]
  \addplot+ table[x=idx, y=asr_prompt, y error plus=b_plus, y error minus=b_minus]
            {results/run1/analysis/dat/asr_holdout.dat};
\end{axis}
```

(Các đoạn LaTeX này chưa được biên dịch thử trong môi trường dev vì máy không có TeX cài sẵn.)

File `.dat`: `asr_<split>.dat`, `benign.dat` (FPR, utility), `latency_{benign,attack,all}.dat`. Ô thiếu ghi `nan`.

## Khoảng tin cậy: dùng cái nào

- **Wilson 95% trên tổng số lượt** theo hợp đồng. Coi mọi lượt là độc lập nên **lạc quan** (các lượt của cùng prompt tương quan).
- **Bootstrap theo cụm 95%** (resample *prompt*, B=2000, seed cố định, phân vị) cho ASR trung bình theo prompt: khoảng nên trích dẫn.
- Hiệu giữa hai cấu hình trên cùng tập prompt: bootstrap **xếp cặp** theo prompt. Hiệu giữa hai split (khác tập prompt, vd
  train và holdout): bootstrap **độc lập**.
- Với ít prompt (dưới ~10) khoảng bootstrap rất rộng hoặc suy biến; đừng kết luận mạnh.

## Quy ước

- Chỉ dòng có `error` rỗng vào mẫu; dòng lỗi được đếm ở Bảng 10 (cảnh báo nếu > 2%).
- Giảm = ASR trước trừ ASR sau (điểm phần trăm, dương là tốt); mọi hiệu tính trên ASR theo prompt.
- Từ chối oan = `blocked` hoặc `model_refused` trên benign; utility tính benign bị chặn là 0 (có thêm cột chỉ tính lượt không bị chặn).
- Prompt "chết" = ASR baseline bằng 0 trên mọi lượt; ASR hiệu dụng chỉ tính trên prompt còn lại (có thiên lệch chọn lọc, xem ghi chú dưới Bảng 9c).
- Số trên `train` và benign `tune:true` đã dùng để chỉnh phòng thủ nên lạc quan; số báo cáo chính là `holdout`, `test_indist`, benign `tune:false`.

## Mã nguồn

| File | Vai trò |
|---|---|
| `intervals.py` | `wilson`, `bootstrap_mean_ci`, `bootstrap_diff_ci` (xếp cặp/độc lập), `quantile` |
| `loader.py` | Đọc, gộp, kiểm tra hợp đồng (`check_input`, `load_results`, `DataError`), đọc `--benign-meta` |
| `render.py` | Định dạng markdown, LaTeX booktabs, `.dat`; lớp `Table` |
| `stats.py` | Các hàm dựng từng bảng, `report.md`, CLI (`python3 -m analysis.stats`) |
