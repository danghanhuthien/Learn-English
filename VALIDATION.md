# Kết quả kiểm tra bản giao

Ngày kiểm tra: **13/10/2026**, múi giờ UTC+7.

## Backend

`python -m unittest backend.test_app -v`: **11/11 tests passed** sau khi bổ sung cấu hình deploy.

- 30 chủ đề, 450 mục từ, mỗi chủ đề 15 mục; seed chạy lại không tạo trùng.
- Tìm tiếng Anh/tiếng Việt, phân trang, escape ký tự LIKE, input giống SQL injection.
- Lưu từ không làm tăng số từ đã học.
- Lịch ôn, đánh giá lại, tính ngày học, chống gửi trùng và phát hiện event ID bị tái sử dụng sai.
- 24 request đồng thời, 6 worker kiểm thử, connection riêng hoạt động.
- Chấm trắc nghiệm ở server; lựa chọn ngoài danh sách bị từ chối; gửi lại không cộng điểm lần nữa.
- Luyện gõ chuẩn hóa hoa/thường/khoảng trắng; bài luyện hết hạn bị từ chối.
- Tách hồ sơ, từ riêng, kiểm tra settings và chặn truy cập từ riêng của hồ sơ khác.
- Export không chứa mã cookie hồ sơ; origin không hợp lệ bị chặn.
- CSV import bỏ qua từ trùng, rollback toàn bộ lượt nhập có dòng lỗi.
- Domain HTTPS sau reverse proxy: origin đã cấu hình được phép ghi, cookie Secure, domain khác bị chặn.

Môi trường thực chạy: Windows, Python **3.11**, FastAPI **0.111.0**, Uvicorn **0.30.1**, HTTPX **0.28.1**, Pydantic **2.7.4**, SQLite từ Python. Bộ TestClient/AnyIO đã cài có phát `ResourceWarning` về memory streams trong lúc kết thúc tests; không có test fail hoặc lỗi API khi kiểm tra trình duyệt. Việc tạo môi trường Python mới bị chính sách socket của máy chặn tải PyPI; backend đã được chạy và kiểm thử bằng các thư viện có sẵn nêu trên. Hướng dẫn cài mới yêu cầu mạng tới PyPI.

## Frontend

`npm run build`: **passed**, Node **24.12.0**, Vite **7.3.7**. Lockfile npm đi kèm.

Build cuối: JS khoảng **154 kB**, CSS khoảng **33 kB** trước gzip. Không tải font, ảnh hoặc thư viện qua CDN khi mở app; giọng đọc có thể dùng mạng tùy thiết bị.

## Trình duyệt

Kiểm tra trên trình duyệt trong Codex với database QA riêng tại cổng 8001:

- Flashcard hiện đúng từ, nghĩa, ví dụ; đánh giá “Đã nhớ” chuyển sang thẻ kế tiếp và cập nhật chuỗi ngày.
- Tìm `hungry`, lưu từ, lọc “Đã lưu” thấy đúng thẻ với trạng thái đã lưu.
- Hoàn thành bài trắc nghiệm 5 câu; cả phản hồi đúng/sai và bảng tổng kết hoạt động.
- Gõ ` JOB ` được chấm đúng cho nghĩa “công việc, nghề nghiệp”.
- Thêm `grab a coffee`, tìm lại thấy nghĩa và ví dụ vừa nhập.
- Đổi tên/mục tiêu thành 20 từ/ngày, tổng quan hiển thị đúng 7/20 từ của hồ sơ thử.
- Nhóm “Công việc” hiển thị 6 chủ đề đúng.
- Màn hình 390×844: không tràn ngang; menu dưới màn hình và bố cục một cột hoạt động.
- Màn hình 1440×1024: sidebar, topic grid và dashboard hoạt động.
- Không thấy console errors/warnings trong lần kiểm tra cuối.

Ảnh xem trước được chụp từ bản dùng thật tại cổng 8000, vẫn có 450 mục từ và chưa có lượt học. Dữ liệu QA không nằm trong file ZIP.

## Phạm vi chưa kiểm chứng

Chưa triển khai lên hosting, chưa kiểm tải nhiều người dùng, chưa kiểm trên Safari/iOS/Android thật. Việc đọc phát âm phụ thuộc giọng thiết bị; không có chấm phát âm hoặc hội thoại AI trong bản này. Đây là bản chạy cục bộ, chưa phải dịch vụ nhiều người dùng có tài khoản.
