# Lingua — tiếng Anh cho cuộc sống

**Deploy từ GitHub:** xem [DEPLOY-GIT.md](DEPLOY-GIT.md). Repo chứa `frontend/dist` đã build để chạy trực tiếp trên hosting Python; tiến độ SQLite nằm trên host và được loại khỏi Git.

Web app học từ vựng cho người Việt, viết bằng **Python / FastAPI + SQLite + Vue 3 / Vite**. Bản này chạy trên máy cá nhân, có giao diện thích ứng điện thoại và máy tính. Bộ học ban đầu gồm **30 chủ đề, 450 từ/cụm từ**, mỗi mục có nghĩa tiếng Việt và câu ví dụ tiếng Anh.

**Bản 2.0 bổ sung 900 câu giao tiếp**, 10 chủ đề, 90 buổi từ sheet `900 cau` của workbook người dùng cung cấp. Có học theo ngữ cảnh, tự nhớ, luyện đáp lại, lịch ôn và ghi chú riêng. Xem [UPDATE-900.md](UPDATE-900.md) để cập nhật server hiện có mà giữ tiến độ. Dữ liệu đã trích sẵn vào JSON; host không cần Excel hoặc openpyxl.

Để đưa lên hosting Python, xem [DEPLOY.md](DEPLOY.md). Gói có `deploy.py` tự nhận cổng từ `PORT` hoặc `SERVER_PORT` và hỗ trợ domain HTTPS qua `LINGUA_PUBLIC_URL`.

## Những gì đã có

- Tổng quan: số từ đã học, chuỗi ngày học, mục tiêu ngày, độ chính xác và biểu đồ 7 ngày.
- Chủ đề: bản thân, sinh hoạt, giao tiếp, công việc và các chủ đề mở rộng.
- Kho từ: tìm tiếng Anh/tiếng Việt, lọc chủ đề/mức độ/trạng thái, phân trang, lưu yêu thích.
- Thêm từ cá nhân bằng giao diện; bộ từ này chỉ xuất hiện trong hồ sơ của bạn.
- Flashcard: nghe từ/câu ví dụ, hiện nghĩa, tự đánh giá, lên lịch ôn tiếp theo.
- Trắc nghiệm chọn nghĩa và luyện gõ từ; đáp án được chấm ở backend.
- Lưu lịch sử vào SQLite. Gửi lại cùng lượt học không ghi thêm tiến độ.
- Điều chỉnh tên/mục tiêu; xuất lịch sử và từ riêng ra JSON.
- Nhập thêm từ vựng từ CSV bằng lệnh quản trị.
- Tab 900 câu: bộ lọc có dấu/không dấu, 90 buổi, mục tiêu 5/10 câu mới mỗi ngày, nghe → hiểu → tự nhớ → đáp lại, ôn theo mốc 1/3/7/14 ngày, lưu câu và ghi chú.
- Swagger API tại `/docs`; bộ kiểm thử tích hợp với database tạm.

## Chạy ngay trên máy hiện tại

Giao diện đã được build sẵn tại `frontend/dist/`. Nếu Python đã có FastAPI và Uvicorn, mở terminal tại thư mục dự án và chạy:

```powershell
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Mở **http://127.0.0.1:8000**. Có thể nhấp đúp `start.cmd` trên Windows. Nếu máy đã có ứng dụng chạy ở cổng 8000, dùng cổng khác, ví dụ `--port 8002`, rồi mở URL tương ứng.

Database tự tạo tại `backend/data/lingua.sqlite3`. Khởi động lại giữ nguyên dữ liệu; seed chỉ thêm mục còn thiếu.

## Cài mới trên máy khác

Yêu cầu: Python **3.11+**. Muốn sửa/build giao diện cần Node **20.19+ hoặc 22.12+**; máy kiểm thử dùng Node 24.12.

Từ thư mục dự án:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

Vì có `frontend/dist/` đi kèm, bạn không cần Node chỉ để sử dụng bản đóng gói. Cài dependencies lần đầu cần internet. Trên macOS/Linux, thay `.\.venv\Scripts\python.exe` bằng `.venv/bin/python`.

## Sửa giao diện / phát triển

Terminal 1, ở thư mục dự án:

```powershell
python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2, ở thư mục `frontend`:

```powershell
npm ci
npm run dev
```

Mở **http://127.0.0.1:5173**. Vite chuyển `/api` sang backend 8000 nên không cần cấu hình CORS rộng. Cookie hồ sơ được dùng cùng hostname; nên nhất quán `127.0.0.1`, tránh đổi qua lại với `localhost`.

Sau khi sửa giao diện:

```powershell
npm run build
```

Sau đó tải lại trang ở cổng 8000. Nếu thêm hoặc tạo `dist/assets` lần đầu, khởi động lại backend để đăng ký static mount. `--configLoader runner` giúp Vite chạy trong môi trường Windows có quyền đọc thư mục giới hạn.

## Cấu trúc

```text
lingua/
  backend/
    app.py              # API, schema, seed, lịch ôn và phục vụ Vue đã build
    seed.json           # 30 chủ đề / 450 mục từ có ví dụ
    import_words.py     # Nhập dữ liệu CSV theo transaction
    test_app.py         # Kiểm thử API bằng SQLite tạm
    requirements.txt
    words-example.csv
    data/               # SQLite tự tạo, không nằm trong file ZIP
  frontend/
    src/
      views/            # Dashboard, Topics, Library, Study, Practice, Settings
      components/       # Icon, TopicCard
      api.js            # Gọi API, state, phát âm và thông báo
      App.vue           # Khung ứng dụng
      style.css         # Giao diện responsive
    dist/               # Bản giao diện build sẵn
    package.json
    package-lock.json
    vite.config.js
  start.cmd
```

## Mô hình dữ liệu

| Bảng | Mục đích |
|---|---|
| `profiles` | Hồ sơ trình duyệt, tên, mục tiêu mỗi ngày |
| `topics` | Tên, nhóm, mô tả và màu/icon chủ đề |
| `words` | Từ, nghĩa, ví dụ, mức độ; `owner_id` cho từ cá nhân |
| `progress` | Lịch ôn, số lần nhớ liên tiếp, trạng thái lưu từ |
| `events` | Lịch sử học có mã duy nhất để chống ghi trùng |
| `quiz_sessions` | Bài luyện, danh sách câu hỏi, thời hạn 2 giờ |
| `quiz_answers` | Kết quả duy nhất cho từng câu của từng bài |

SQLite bật foreign keys và WAL. Mỗi request dùng connection riêng; `check_same_thread=False` cho phép FastAPI chuyển dependency/route giữa worker threads. Mọi truy vấn với input đều dùng parameters. Từ riêng và tiến độ được giới hạn theo hồ sơ.

## Lịch ôn hoạt động ra sao?

Đây là lịch ôn đơn giản, dễ hiểu, không phải thuật toán SM-2 hoặc FSRS:

- **Chưa nhớ:** ôn sau 10 phút, số lần nhớ liên tiếp về 0.
- **Hơi khó:** ít nhất 1 ngày; nhân khoảng cách trước với 1,2.
- **Đã nhớ:** ít nhất 1 ngày; nhân khoảng cách trước với 2,2.
- **Rất dễ:** ít nhất 3 ngày; nhân khoảng cách trước với 3.
- Khoảng cách tối đa 180 ngày. “Đã nhớ vững” khi nhớ liên tiếp ít nhất 3 lần và khoảng cách ôn ít nhất 7 ngày.
- Bài luyện trả lời đúng tương đương “Đã nhớ”; trả lời sai tương đương “Chưa nhớ”.

“Đã học” nghĩa là đã đánh giá/luyện từ ít nhất một lần, không đồng nghĩa đã thành thạo. Mục tiêu ngày tính **số từ khác nhau** đã luyện. Luyện một từ nhiều lần chỉ tính một từ cho mục tiêu, nhưng vẫn lưu mọi lượt hợp lệ vào lịch sử. Độ chính xác chỉ tính bài luyện, không tính tự đánh giá flashcard.

Ngày học tính theo `Asia/Bangkok` (UTC+7, cùng múi giờ Việt Nam). Chuỗi vẫn còn nếu hôm qua đã học và hôm nay chưa học. Có thể đặt `LINGUA_TIMEZONE` ở backend; giao diện ngày hiện tại mặc định hiển thị UTC+7.

## Mở rộng bộ từ

Bạn có thể dùng nút **Thêm từ** trong kho từ để tạo bộ từ riêng. Để bổ sung bộ từ chung cho mọi hồ sơ:

```powershell
python -m backend.import_words backend/words-example.csv
```

CSV UTF-8 có các cột `topic_slug,term,meaning,example,level`. Slug chủ đề nằm trong `seed.json`; mức độ nhận A1/A2/B1/B2. Từ trùng trong cùng chủ đề được bỏ qua. Một dòng không hợp lệ làm toàn bộ lượt nhập bị rollback, tránh nhập dở dang.

Để thêm chủ đề mới, thêm một object theo cấu trúc hiện có vào `seed.json`, sau đó khởi động lại backend. Việc sửa seed không tự ghi đè mục từ đã có trong DB. Bộ từ được soạn cho ứng dụng; nhãn mức độ là gợi ý học, chưa được thẩm định chính thức theo CEFR. Tìm kiếm tiếng Việt giữ dấu; tìm `đói` thay vì `doi`.

## Kiểm thử

```powershell
python -m unittest backend.test_app -v
```

Kiểm thử đầy đủ bản 2.0, bao gồm nâng cấp dữ liệu và khởi động trên host:

```powershell
python -m unittest backend.test_app backend.test_sentences backend.test_deploy -v
```

Kiểm tra seed, tìm kiếm, phân trang, lưu từ, lịch ôn, chống ghi trùng, request đồng thời, chấm trắc nghiệm, chuẩn hóa đáp án gõ, hết hạn bài, tách hồ sơ, từ tự thêm, settings, export và chặn origin lạ. Database tạm được tạo riêng cho mỗi test, không chạm tiến độ thật.

Build giao diện: `npm run build` trong `frontend`. Luồng flashcard, tìm từ, lưu từ và bài luyện cũng được kiểm tra trên trình duyệt. Chi tiết kết quả kiểm thử của bản giao nằm trong `VALIDATION.md`.

## Lưu trữ và giới hạn của bản hiện tại

- Đây là bản dùng cá nhân trên máy cục bộ, chưa có đăng ký/đăng nhập, khôi phục tài khoản, đồng bộ nhiều thiết bị hoặc dashboard quản trị.
- Cookie HttpOnly giữ mã hồ sơ, không phải tài khoản có mật khẩu. Xóa cookie/đổi trình duyệt tạo hồ sơ mới; dữ liệu hồ sơ cũ vẫn còn trong SQLite. Tệp xuất JSON dùng để lưu/đọc dữ liệu; chưa có chức năng import tiến độ trên giao diện.
- Để sao lưu đầy đủ, dừng backend rồi sao chép thư mục `backend/data/`. Dừng server trước khi sao chép tránh bỏ sót dữ liệu còn trong WAL.
- Phát âm dùng Web Speech API với giọng tiếng Anh trên thiết bị. Một số giọng cần mạng. Chưa có chấm phát âm bằng microphone hoặc hội thoại AI.
- Luyện gõ so khớp từ đích, không phân biệt hoa/thường và khoảng trắng thừa; không chấp nhận mọi từ đồng nghĩa. Câu tiếng Việt đôi khi có nhiều cách diễn đạt tiếng Anh; hãy đối chiếu đáp án và ví dụ.
- Chỉ bind `127.0.0.1` theo mặc định. Trước khi đưa lên internet cần đăng nhập thực sự, HTTPS, giới hạn request, quản lý vòng đời dữ liệu và backup. Chạy một instance có ổ đĩa bền vững cho SQLite; không đặt DB trong thư mục tạm của host.

Biến môi trường `LINGUA_DB` cho phép đổi đường dẫn database; nên dùng đường dẫn tuyệt đối. Không đưa file DB cá nhân vào Git hoặc gói chia sẻ.

## Tài liệu framework

- [Vue: Quick Start](https://vuejs.org/guide/quick-start)
- [FastAPI: SQLite / SQL databases](https://fastapi.tiangolo.com/tutorial/sql-databases/)
- [FastAPI: Static files](https://fastapi.tiangolo.com/tutorial/static-files/)
