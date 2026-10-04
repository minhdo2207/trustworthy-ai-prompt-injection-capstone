# Quy tắc làm việc trên repo

Áp dụng cho cả nhóm: Minh, Thành, Ngọc, Hương, Nam.

## 1. Nhánh `main` đã bị khoá

- **Không push thẳng lên `main`.** Mọi thay đổi phải đi qua pull request (PR).
- Không bắt buộc có người approve, nhưng **nên nhờ một người xem qua trước khi merge**, nhất là PR đụng tới `defenses/` hoặc `attack_prompts/`.
- Mọi bình luận trong PR phải được giải quyết (resolve) trước khi merge.
- Không force-push và không xoá nhánh `main`.

## 2. Quy trình một thay đổi

```bash
git checkout main
git pull
git checkout -b <ten>/<loai>-<mo-ta-ngan>     # ví dụ: ngoc/feat-l1-unicode-filter
# ... sửa, chạy thử ...
git add <file cụ thể>                         # không dùng git add .
git commit -m "feat(defenses): thêm L1 chuẩn hoá Unicode"
git push -u origin <ten-nhanh>
```

Sau đó mở PR trên GitHub vào `main`, gán người review, và báo vào nhóm chat.
Nếu sửa trực tiếp trên web GitHub, chọn **"Create a new branch for this commit and start a pull request"**, không commit thẳng vào `main`.

## 3. Tên nhánh

Dạng `<ten>/<loai>-<mo-ta-ngan>`, chữ thường, không dấu, nối bằng dấu gạch ngang.

Ví dụ: `huong/data-benign-set`, `thanh/feat-harness`, `nam/fix-l3-delimiter`, `minh/docs-related-work`.

## 4. Định dạng commit

```
<loai>(<pham-vi>): <mô tả ngắn, viết ở thể mệnh lệnh>

<giải thích thêm nếu cần: vì sao, ảnh hưởng gì>
```

**Loại (`<loai>`):**

| Loại | Dùng khi |
|---|---|
| `feat` | Thêm chức năng hoặc lớp phòng thủ mới |
| `fix` | Sửa lỗi |
| `data` | Thêm hoặc sửa bộ prompt, tập benign |
| `docs` | Tài liệu, báo cáo, README |
| `exp` | Kết quả thực nghiệm, file CSV, bảng số liệu |
| `refactor` | Sắp xếp lại code, không đổi hành vi |
| `chore` | Cấu hình, `requirements.txt`, `.gitignore` |

**Phạm vi (`<pham-vi>`):** `attack_prompts`, `baseline_agent`, `defenses`, `docs`, hoặc tên lớp như `l1`, `l2`, `l3`, `l4`, `harness`.

**Quy tắc:**

1. Dòng đầu **không quá 72 ký tự**, không kết thúc bằng dấu chấm.
2. Mỗi commit làm **một việc**. Không gộp sửa code và đổi dữ liệu vào cùng một commit.
3. Không commit `Update`, `fix`, `abc`, `Add files via upload`. Mô tả phải cho người khác biết đã đổi gì.
4. Commit bằng **đúng tài khoản GitHub của mình** (kiểm tra `git config user.name` và `git config user.email`).
5. Viết bằng tiếng Việt hoặc tiếng Anh đều được, nhưng cả một PR thống nhất một thứ tiếng.

Ví dụ tốt:

```
data(attack_prompts): thêm 4 prompt Fake Completion vào hold-out
exp(harness): ghi ASR baseline Qwen3-8B trên train và hold-out
fix(l2): sửa ngưỡng Prompt Guard chọn nhầm trên hold-out
```

## 5. Quy tắc cho pull request

- **Tiêu đề PR** theo cùng định dạng với commit.
- **Mô tả PR** gồm: làm gì, vì sao, cách kiểm tra lại, và liên kết issue (`Closes #<số>`).
- PR nhỏ, một mục đích, dễ review. Tránh PR hàng chục file.
- Người review kiểm tra: chạy được không, có đụng tới dữ liệu hold-out không, có file lạ không, tài liệu tham khảo có link và nguồn đúng không.
- Dùng **Squash and merge** để lịch sử `main` gọn, mỗi PR một commit.
- Xoá nhánh sau khi merge.

## 6. Quy tắc riêng của đề tài

1. **Không được tinh chỉnh ngưỡng, từ khoá, prompt hệ thống dựa trên hold-out.** Chỉ chỉnh trên `train`. Hold-out chỉ chạy cho cấu hình cuối.
2. Mọi prompt có nguồn bên ngoài phải ghi `source` (tên bài hoặc dataset, link, giấy phép).
3. Kết quả thực nghiệm phải chạy lại được từ script. Không sửa tay file CSV kết quả.
4. Không đổi nội dung `attack_prompts/holdout_prompts.json` sau khi đã chạy đo hold-out mà không báo cả nhóm.

## 7. Repo công khai: không đưa lên những thứ này

- **API key, token, mật khẩu** (OpenRouter, Hugging Face...). Lưu trong `.env` (đã nằm trong `.gitignore`); chỉ commit `.env.example` với giá trị giả.
- File model lớn, thư mục `venv`, cache.
- Dữ liệu cá nhân của bất kỳ ai.

Nếu lỡ commit lên nhánh một khoá bí mật: **thu hồi khoá ngay** trên trang nhà cung cấp, rồi báo trưởng nhóm. Xoá commit không đủ, vì khoá đã lộ.

## 8. Khi bị xung đột (conflict)

Cập nhật nhánh của mình theo `main`, không tự ý sửa `main`:

```bash
git fetch origin
git rebase origin/main      # hoặc: git merge origin/main
# giải quyết xung đột, rồi:
git push --force-with-lease   # chỉ trên nhánh của chính mình
```

Không chắc thì hỏi trưởng nhóm trước khi force-push.
