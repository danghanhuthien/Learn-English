# Deploy lên hosting Python

Chạy một server Python cho cả API và Vue đã build. SQLite nằm trên ổ đĩa của server; không cần tạo dịch vụ database riêng.

## Cấu hình khởi đầu cho dùng cá nhân

| Mục | Giá trị |
|---|---|
| Loại | Application |
| Runtime | Python 3.11 hoặc 3.12 |
| RAM | 512 MB; nâng 1024 MB nếu cài dependencies bị thiếu RAM |
| CPU | 50% / 0.5 vCore |
| Storage | 1024 MB |
| Instances / workers | 1 |
| Nguồn | ZIP hoặc GitHub |

Đây là cấu hình thử khởi đầu, không phải cam kết số người dùng đồng thời. Không chạy npm dev trên host: `frontend/dist` có sẵn trong ZIP.

## File và lệnh

Upload `lingua-webapp.zip` và giải nén. Thư mục làm việc cần là thư mục chứa `deploy.py`, `backend/`, `frontend/`. ZIP có một thư mục ngoài cùng tên `lingua`; nếu host giải nén nguyên cấu trúc, đặt working directory là `lingua` hoặc di chuyển các file bên trong lên thư mục chạy của server.

Cài thư viện một lần, hoặc đặt làm install/build command nếu host có ô riêng:

```sh
python -m pip install -r backend/requirements.txt
```

Startup command:

```sh
python deploy.py
```

`deploy.py` kiểm tra FastAPI/Uvicorn trước khi chạy. Nếu thiếu thư viện, script tự dùng pip cài requirements vào `.vendor/` trong thư mục app; không cần quyền ghi vào thư viện Python hệ thống. Lần đầu cần mạng tới PyPI; lần sau dùng thư viện đã có. Không xóa `.vendor/` khi cập nhật chỉ mã nguồn.

Nếu host không cung cấp biến cổng, có thể chỉ định trực tiếp cổng được cấp, ví dụ với cổng **40301**:

```sh
python deploy.py --port 40301
```

Nếu server đang crash vì thiếu thư viện và Console không nhận lệnh, dừng server, thay file `deploy.py` bằng bản mới, rồi Start lại. Console của ứng dụng là stdin của process, không phải lúc nào cũng là shell để chạy pip.

Nếu host chỉ có một ô command và chưa tự cài requirements:

```sh
python -m pip install -r backend/requirements.txt && python deploy.py
```

## Environment variables

- `PORT` hoặc `SERVER_PORT`: **cổng thực mà host cấp**. `deploy.py` ưu tiên `PORT`, sau đó `SERVER_PORT`, mặc định 8000 khi không có cả hai. Không đặt 8000 nếu host yêu cầu cổng khác. Nếu host cấp sẵn `SERVER_PORT`, giữ nguyên và không tự thêm `PORT` khác.
- `LINGUA_PUBLIC_URL`: URL công khai thật, ví dụ `https://learn.example.com`, không có path. Dùng để cho phép origin website khi chạy sau reverse proxy; với HTTPS, cookie hồ sơ được đánh dấu Secure ngay cả khi proxy nối tới Python bằng HTTP.
- `LINGUA_DB`: đường dẫn tuyệt đối tới file SQLite trong thư mục **ghi được và được host giữ lại khi restart/redeploy**. Chỉ điền sau khi xác định đường dẫn của hosting. Nếu không đặt, dùng `backend/data/lingua.sqlite3`; cần kiểm tra host có giữ thư mục này qua redeploy không.
- `LINGUA_TIMEZONE=Asia/Bangkok` cho ngày học theo UTC+7.

Web/domain của host phải trỏ tới cùng cổng Python. Health check nếu có: `/api/health`. Dùng domain HTTPS cho truy cập công khai.

## Kiểm tra sau khi chạy

1. Logs hiển thị Uvicorn đã chạy và không có traceback.
2. Mở URL công khai: tổng quan hiển thị 30 chủ đề / 450 mục từ.
3. Học một flashcard, refresh trang và kiểm tra tiến độ còn.
4. Restart server, mở lại và kiểm tra tiến độ còn.
5. Xác nhận đường dẫn DB nằm trong storage bền vững trước khi cập nhật/redeploy.

Bản này dùng hồ sơ qua cookie, chưa có đăng nhập/khôi phục/đồng bộ thiết bị và giới hạn request. Phù hợp triển khai thử phục vụ cá nhân; trước khi mở thành dịch vụ cho đông người cần bổ sung các phần đó. Không upload DB chứa tiến độ cá nhân nếu bạn chỉ muốn một bản triển khai mới.
