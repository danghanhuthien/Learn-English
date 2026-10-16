# Kiểm tra bản 2.0: 900 câu giao tiếp

Ngày kiểm tra: **16/10/2026**, UTC+7.

## Dữ liệu nguồn

- Đọc riêng sheet `900 cau` trong workbook do người dùng cung cấp; không sửa workbook.
- JSON có 900 mục với 900 ID duy nhất, 10 chủ đề, 90 buổi, mỗi buổi đúng 10 mục.
- Phân bố mức nguồn: A1 124, A2 316, B1 298, B2 129, C1 33. Nhãn được giữ nguyên, chưa thẩm định lại CEFR.
- 897 câu tiếng Anh khác nhau; 3 cặp trùng nội dung được giữ theo ID và ngữ cảnh nguồn.
- Toàn bộ 900 câu đáp tách được tiếng Anh/tiếng Việt; vẫn lưu trường câu đáp đầy đủ để đối chiếu nguồn.
- Kiểm thử so từng trường của toàn bộ 900 records JSON với dữ liệu SQLite sau seed.

## Backend

**25/25 tests passed**:

```text
python -m unittest backend.test_sentences backend.test_app backend.test_deploy -v
```

Chạy qua trên hai bộ thư viện:

1. Python 3.11, FastAPI 0.111.0, Uvicorn 0.30.1, HTTPX 0.28.1.
2. Python 3.11, FastAPI 0.143.2, Starlette 1.8.0, Pydantic 2.14.1, Uvicorn 0.54.0, HTTPX 0.28.1; cài mới vào `.venv` thành công ngày kiểm tra. Starlette mới có cảnh báo deprecation về HTTPX trong TestClient; tests vẫn pass. Chưa chạy trực tiếp trong container Linux Python 3.12 của host.

Phạm vi mới: giữ đúng bộ câu; tìm có dấu/không dấu; lọc và phân trang; tiếp tục nửa buổi; mục tiêu ngày; ưu tiên câu đến hạn; lịch ôn; chống gửi trùng; tách hồ sơ; ghi chú/lưu câu; export; chuỗi học chung không cộng lẫn từ/câu; mô phỏng nâng từ schema v1 lên v2 và kiểm tra nguyên vẹn tất cả các hàng thuộc bảng cũ; backup chỉ tạo một lần khi cần.

Các test vocabulary và bootstrap hosting cũ tiếp tục pass. Backend không cần thêm thư viện để sử dụng bộ câu; openpyxl chỉ dùng khi trích file nguồn ở máy phát triển.

## Giao diện

`npm run build`: **passed**, Node 24.12.0, Vite 7.3.7. Build cuối khoảng 187 kB JS và 51 kB CSS trước gzip.

Đã kiểm tra bằng trình duyệt trên database QA riêng:

- Mở tab 900 câu và lượt học mặc định 5 câu A1–A2.
- Đi hết 4 bước nghe, hiểu nghĩa, ẩn câu để tự nhớ, xem gợi ý đáp lại; đánh giá chuyển sang câu kế tiếp và lưu tiến độ.
- Tìm mã CB-001, lưu câu và ghi chú, chuyển sang tự nhớ một câu và hoàn tất lượt.
- Hiện đủ 90 buổi; buổi đầu báo đúng 1/10 sau lần học trước đó. Học tiếp 5 câu chưa học qua chế độ đáp lại; thống kê thành 6 câu khác nhau.
- Restart backend và tải lại: số liệu còn. Đổi mục tiêu từ 5 lên 10 hiển thị đúng 6/10 câu mới hôm nay.
- Trình duyệt ở kích thước 390×844: không tràn ngang; menu 6 mục, bộ lọc, thẻ câu và các bước học dùng được.
- Kiểm tra thêm bố cục 1440×1024 và lưu ảnh xem trước bản giao.

Phát âm dùng Web Speech API. Đã kiểm tra thao tác nút nghe; chất lượng giọng, khả năng phát âm và dùng ngoại tuyến tùy thiết bị. Không có chấm phát âm hoặc đánh giá đúng/sai tự động cho câu trả lời tự do.

## Đóng gói

- `lingua-update-900-cau.zip`: chỉ code backend mới, dữ liệu JSON, frontend đã build và hướng dẫn cập nhật. Không có DB, `.vendor`, virtualenv hoặc node_modules; có thể giải nén ghi đè code trong thư mục ứng dụng hiện có.
- `lingua-hosting.zip`: bản đầy đủ, các file nằm ngay gốc ZIP.
- `lingua-webapp.zip`: bản đầy đủ với thư mục ngoài cùng `lingua/`.

ZIP được kiểm tra CRC và danh sách file. Không đăng nhập hoặc chỉnh server Botkeep trong lần làm này; bản cập nhật được kiểm thử cục bộ và chuẩn bị sẵn để người dùng upload.
