# Backup dữ liệu lên Dropbox + giải phóng ổ đĩa

Toàn bộ dữ liệu "bộ nhớ trong" của app nằm trong thư mục `data/`:

| Dữ liệu | File/Thư mục | Backup? | Xoá local để giải phóng? |
|---------|--------------|---------|--------------------------|
| DB chính (user, GPT, billing, OTP…) | `data/gptweb.db` | ✅ ZIP lên Dropbox | ❌ App đang mở liên tục — **không** xoá |
| Lịch sử hội thoại | `data/conversations.db` | ✅ | ❌ |
| Vector DB (knowledge) | `data/knowledge/` | ✅ | ❌ |
| File người dùng upload | `data/uploads/` | ✅ | ✅ **Đây là phần giải phóng ổ đĩa** |

> **Vì sao không xoá được DB?** SQLite và ChromaDB được app mở và đọc/ghi trực
> tiếp trên đĩa mọi lúc. Nếu xoá bản local, app sẽ hỏng ngay. Nên DB chỉ được
> **sao lưu** lên Dropbox (phòng khi server chết thì khôi phục), còn thứ thực sự
> chiếm ổ đĩa và giải phóng được là **file upload cũ**.
>
> File upload cũ hơn `UPLOAD_RETENTION_DAYS` sẽ được đẩy lên Dropbox rồi xoá khỏi
> server. Link cũ (`/api/uploads/<tên>`) **vẫn hoạt động** — server tự lấy link
> tạm từ Dropbox và redirect tới đó.

---

## 1. Lấy credential Dropbox (làm 1 lần)

1. Vào https://www.dropbox.com/developers/apps → **Create app**.
2. Chọn **Scoped access** → **App folder** (an toàn, chỉ truy cập 1 thư mục
   riêng) hoặc **Full Dropbox** nếu muốn tự chọn đường dẫn.
3. Tab **Permissions** → bật: `files.content.write`, `files.content.read`,
   `files.metadata.read` → **Submit**.
4. Tab **Settings**:
   - Copy **App key** và **App secret**.
   - Mục **OAuth 2 → Access token expiration**: để mặc định (short-lived).

### Lấy refresh token (token dài hạn, khuyến nghị)

Mở URL sau trên trình duyệt (thay `<APP_KEY>`):

```
https://www.dropbox.com/oauth2/authorize?client_id=<APP_KEY>&token_access_type=offline&response_type=code
```

Bấm **Allow** → copy đoạn **code** hiện ra, rồi chạy (thay giá trị của bạn):

```bash
curl https://api.dropbox.com/oauth2/token \
  -d code=<CODE_VUA_COPY> \
  -d grant_type=authorization_code \
  -u <APP_KEY>:<APP_SECRET>
```

Kết quả JSON có `"refresh_token": "..."` — đó là token dài hạn (không hết hạn).

---

## 2. Điền vào `.env`

```env
DROPBOX_REFRESH_TOKEN=<refresh_token vừa lấy>
DROPBOX_APP_KEY=<app key>
DROPBOX_APP_SECRET=<app secret>
DROPBOX_BACKUP_DIR=/gpt-sbay-backups
BACKUP_KEEP=14
UPLOAD_RETENTION_DAYS=7
```

Cài thư viện: `pip install dropbox` (đã có sẵn trong `requirements.txt`).

---

## 3. Chạy backup

### Chạy tay

```bash
cd /www/python/gpt-sbay
python scripts/backup_to_dropbox.py            # backup DB + đẩy uploads cũ lên Dropbox + xoá local
python scripts/backup_to_dropbox.py --no-free  # chỉ backup, không xoá gì
```

### Tự động theo lịch (cron) — khuyến nghị

Chạy mỗi ngày lúc 3h sáng (chỉnh đường dẫn python trong venv của bạn):

```cron
0 3 * * * cd /www/python/gpt-sbay && /www/python/gpt-sbay/venv/bin/python scripts/backup_to_dropbox.py >> data/backup.log 2>&1
```

Trên aaPanel: **Cron** → *Thêm tác vụ* → loại **Shell Script**, dán lệnh trên.

### Từ trang Admin

- `GET  /api/admin/backup/status` — xem đã cấu hình Dropbox chưa + dung lượng `data/`.
- `POST /api/admin/backup?free_space=true` — backup ngay + giải phóng ổ đĩa.
- `POST /api/admin/backup?free_space=false` — chỉ backup, không xoá.

(Cần đăng nhập tài khoản `admin`.)

---

## 4. Khôi phục dữ liệu

1. Tải file `data_YYYYMMDD_HHMMSS.zip` mới nhất từ Dropbox (`/gpt-sbay-backups/`).
2. Dừng app.
3. Giải nén đè vào thư mục `data/`:
   ```bash
   unzip -o data_YYYYMMDD_HHMMSS.zip -d data/
   ```
4. File upload cũ nằm trong `/gpt-sbay-backups/uploads/` trên Dropbox — chỉ cần
   tải về `data/uploads/` nếu muốn phục vụ lại từ server (không bắt buộc, vì app
   đã tự redirect sang Dropbox).
5. Khởi động lại app.

---

## Tinh chỉnh

| Biến | Ý nghĩa | Mặc định |
|------|---------|----------|
| `UPLOAD_RETENTION_DAYS` | Giữ file upload trên server bao nhiêu ngày rồi mới đẩy lên Dropbox + xoá local. `0` = xoá ngay sau backup. | `7` |
| `BACKUP_KEEP` | Số bản ZIP backup DB giữ lại trên Dropbox (bản cũ hơn tự xoá). | `14` |
| `DROPBOX_BACKUP_DIR` | Thư mục gốc trên Dropbox. | `/gpt-sbay-backups` |
