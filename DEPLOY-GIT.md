# Deploy Lingua từ GitHub

Repository: **https://github.com/danghanhuthien/Learn-English**

Branch: **main**

Repo có cả mã nguồn Python/Vue, dữ liệu 450 từ + 900 câu và giao diện đã build trong `frontend/dist`. Không có SQLite cá nhân, cookie, `.vendor`, môi trường Python hoặc node_modules. Host chỉ cần Python, không cần Node để chạy bản đã build.

## Cấu hình Botkeep

Trong bước chọn nguồn của server, chọn **GitHub**:

| Trường | Giá trị |
|---|---|
| Repository | `https://github.com/danghanhuthien/Learn-English.git` |
| Branch | `main` |
| Loại | Application / Python |
| Runtime | Python 3.12 |
| Working directory nếu có | Gốc repository, nơi có `deploy.py` |
| Start command | `python deploy.py` |

`deploy.py` nhận cổng từ `PORT`, sau đó `SERVER_PORT`. Nếu host không cung cấp biến cổng, điền rõ cổng được cấp. Với server cũ của anh là 40301:

```sh
python deploy.py --port 40301
```

Một server mới có thể được cấp cổng khác; dùng cổng hiển thị trong Network. Lần đầu script tự cài thư viện còn thiếu vào `.vendor/`. Khi thành công, log hiển thị `Application startup complete`.

## Chuyển server đang có dữ liệu từ ZIP sang Git

1. Dừng server và tải bản sao đầy đủ `backend/data/` về máy. Nếu đã đặt `LINGUA_DB`, sao lưu file tại đường dẫn đó. Dừng trước khi sao chép giúp giữ dữ liệu SQLite nhất quán.
2. Trong tab GitHub của hosting, kết nối repo trên và chọn nhánh `main`. Chỉ dùng cách đồng bộ giữ được storage/SQLite hiện có. Nếu panel yêu cầu thư mục trống hoặc cài lại server, chưa thực hiện cho tới khi đã có backup.
3. Sau khi mã được lấy về, đặt SQLite cũ trở lại `backend/data/lingua.sqlite3`, hoặc giữ `LINGUA_DB` trỏ tới vị trí bền vững đang dùng. Giữ nguyên hostname/domain và cookie trình duyệt để mở lại đúng hồ sơ.
4. Giữ các biến môi trường hiện tại, kiểm tra cổng và Start lại.

Nếu tạo một server mới từ GitHub, cần chuyển SQLite cũ sang để giữ tiến độ; repo không có file đó. Nếu không chuyển, app tạo một database/hồ sơ học mới. Tên miền/hostname mới cũng có cookie hồ sơ mới; bản hiện tại chưa có đăng nhập hoặc chuyển hồ sơ tự động giữa domain.

`.gitignore` ngăn Git theo dõi dữ liệu runtime; việc host có xóa toàn bộ workspace lúc redeploy hay không vẫn phụ thuộc host. Đặt DB trên storage bền vững và giữ backup. Không dùng lệnh `git clean -fdx`, vì lệnh đó xóa cả file đang được ignore, bao gồm DB/thư viện cài trên host.

## Mỗi lần cập nhật sau này

1. Sửa và kiểm tra code trên máy phát triển.
2. Nếu sửa Vue, chạy tại thư mục `frontend`:

   ```sh
   npm ci
   npm run build
   ```

3. Commit cả mã nguồn và `frontend/dist`, rồi push lên `main`.
4. Dừng server nếu cần, dùng chức năng cập nhật từ Git trong panel để lấy commit mới, rồi Start lại. Chỉ push GitHub chưa tự cập nhật host nếu chưa bật cơ chế deploy tự động của host.

Nếu hosting có terminal shell thực sự và checkout đã ở `main`, có thể cập nhật ở thư mục repository bằng:

```sh
git pull --ff-only origin main
```

Console nhập lệnh cho ứng dụng Python không nhất thiết là shell; không gõ lệnh Git vào console ứng dụng nếu panel không hỗ trợ terminal.

## Biến môi trường

- `LINGUA_DB`: đường dẫn tuyệt đối tới SQLite trên storage bền vững, nếu cần đổi vị trí mặc định.
- `LINGUA_PUBLIC_URL`: origin công khai thật, ví dụ `https://learn.example.com`, không kèm đường dẫn; cần khi reverse proxy dùng HTTPS ở bên ngoài.
- `LINGUA_TIMEZONE=Asia/Bangkok`: ngày học UTC+7.
- `PORT` hoặc `SERVER_PORT`: cổng host cấp, nếu không dùng `--port`.

Không commit token GitHub, mật khẩu, cookie hoặc file `.env`. Để host có quyền truy cập repo private, dùng phần kết nối GitHub/credential của host.

## Kiểm tra tự động

GitHub Actions chạy các test backend trên Python 3.11/3.12 và build Vue mỗi khi push `main` hoặc mở pull request. Workflow chỉ đọc repository; không có quyền ghi commit hoặc tự triển khai lên host. Kết quả xem trong tab **Actions**.
