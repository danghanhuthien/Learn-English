# Nâng cấp Lingua: 900 câu giao tiếp

Bản mới thêm tab **900 câu giao tiếp** với 4 phần: Học hôm nay, Kho câu, 90 buổi học, Tiến độ. Phần từ vựng, từ tự thêm và lịch sử hiện có tiếp tục dùng database cũ.

## Dữ liệu được bổ sung

- Đúng **900 mục**, **10 chủ đề**, **90 buổi**, mỗi buổi 10 câu.
- Giữ mã câu gốc, trình độ A1–C1, câu tiếng Anh, nghĩa, câu đáp, tình huống, bối cảnh và số buổi từ sheet `900 cau`.
- Giữ 3 cặp câu tiếng Anh trùng nội dung nhưng khác mã/ngữ cảnh. Không gộp mất mục nguồn.
- Các cột tiến độ Excel không được dùng để ghi đè hồ sơ trong app. Mỗi hồ sơ bắt đầu bộ câu mới độc lập, mục tiêu 5 câu mới/ngày.
- File Excel được đọc để trích dữ liệu, không chỉnh sửa. JSON đi kèm lưu tên sheet, dòng nguồn và SHA-256 của workbook để đối chiếu.

## Hướng dẫn cập nhật trên Botkeep

1. **Stop server** trước khi thay mã nguồn.
2. Giữ một bản sao thư mục `backend/data/` để lưu SQLite. Nếu anh từng đặt `LINGUA_DB` ở chỗ khác thì sao lưu file ở đường dẫn đó. Giữ nguyên `.vendor/`, các biến môi trường và cookie trình duyệt.
3. Upload **`lingua-update-900-cau.zip`** vào thư mục chạy `/home/container`, rồi giải nén và cho phép ghi đè các **file mã nguồn** có cùng tên. ZIP này không có thư mục ngoài cùng, không chứa database, `.vendor` hoặc node_modules.
4. Sau giải nén cần có:

   ```text
   /home/container/backend/app.py
   /home/container/backend/sentences.py
   /home/container/backend/sentences_seed.json
   /home/container/frontend/dist/index.html
   /home/container/frontend/dist/assets/...
   ```

5. Giữ Startup command đang chạy được, ví dụ cổng server hiện tại là 40301:

   ```sh
   python deploy.py --port 40301
   ```

6. Bấm **Start**. App tự thêm các bảng/câu mới vào **chính database hiện có**. Khi phát hiện schema v1, app tạo backup SQLite nhất quán trong `backups/` cạnh file DB, trước khi nâng lên v2. Chạy lại không tạo câu trùng.
7. Mở lại **đúng URL và đúng trình duyệt cũ**, tải lại trang (Ctrl+F5 nếu vẫn thấy giao diện cũ). Bấm tab “900 câu giao tiếp”. Kiểm tra tiến độ từ vựng cũ còn nguyên.

Không cần tạo lại server, cài Node, chạy npm hoặc upload Excel. Phần bổ sung chỉ dùng các thư viện Python app đã có. Không xóa `backend/data`, không giải nén đè một database mẫu từ nguồn khác và không xóa cookie. File ZIP cập nhật được đóng gói để không mang theo DB của máy phát triển.

**Nếu host hiện tại đang chỉ tới một thư mục gốc khác**, giải nén vào đúng thư mục chứa `deploy.py` của server. Không chạy bản cập nhật trong một thư mục mới nếu muốn tiếp tục database mặc định và tiến độ cũ.

## Cách học

- **Học hôm nay:** mặc định A1–A2; lấy tối đa 20 câu đến hạn trước, rồi bổ sung câu mới trong hạn mức 5/ngày. Có thể đổi mục tiêu thành 10. Khi có từ 20 câu đến hạn trong bộ lọc, app tạm ngừng cấp câu mới để ưu tiên ôn.
- **Nghe & hiểu:** nghe trước khi hiện chữ → xem nghĩa/ngữ cảnh → ẩn câu để tự nói lại → thử đáp rồi mở câu đáp tham khảo → tự đánh giá.
- **Tự nhớ câu:** nhìn nghĩa/tình huống, tự nói tiếng Anh, mở câu nguồn để đối chiếu và đánh giá.
- **Phản xạ đáp lại:** nghe lời người đối diện, thử đáp thành tiếng, mở một cách trả lời tham khảo. Câu trả lời khác vẫn có thể đúng; app không chấm phát âm hay ý nghĩa bằng AI.
- **90 buổi:** chủ động học 5 hoặc 10 câu một lượt. Câu chưa học xuất hiện trước, nên sau nửa buổi có thể quay lại học tiếp. Khi học hết, có thể luyện lại buổi. Chế độ theo buổi hoặc luyện một câu riêng có thể vượt mục tiêu ngày theo lựa chọn của người học.
- **Kho câu:** tìm có dấu/không dấu, lọc chủ đề/trình độ/bối cảnh/buổi/trạng thái, nghe, lưu yêu thích và thêm ghi chú riêng.
- Tiến độ được ghi **sau mỗi lần đánh giá**, không cần học hết lượt. Lượt đang mở chưa đánh giá sẽ chưa tính là đã học.

## Lịch ôn riêng cho câu

- “Chưa nhớ”: 10 phút, quay về bước đầu.
- “Còn khó”: rút khoảng cách hiện tại xuống một nửa, tối thiểu 1 ngày; không tăng mốc nhớ.
- “Đã nhớ”: đi lần lượt qua 1, 3, 7, 14, 30, 60, 120 ngày.
- “Rất dễ”: tiến 2 mốc một lần.
- “Nhớ vững”: tới mốc thứ 4 và khoảng cách ôn ít nhất 14 ngày. Đây là trạng thái tự đánh giá phục vụ ôn tập.

Mục tiêu câu mới tính số câu lần đầu được đánh giá trong ngày; ôn lại không cộng thêm câu mới. Chuỗi học câu và thống kê từ vựng được giữ riêng. Huy hiệu ngày học trên thanh đầu trang tính ngày có học từ **hoặc** học câu. Export JSON trong Cài đặt có thêm mục `sentences` chứa lịch sử, lịch ôn, từ yêu thích và ghi chú câu.

Phát âm vẫn dùng giọng tiếng Anh có sẵn của trình duyệt/thiết bị; không có API AI trả phí hoặc yêu cầu microphone mới.

## Kiểm tra khi cập nhật xong

1. Tab mới hiện 900 câu / 90 buổi; Kho từ vựng vẫn có bộ cũ và từ riêng của anh.
2. Học thử một câu, đánh giá, tải lại: tiến độ còn.
3. Dừng rồi Start lại: tiến độ vẫn còn; tổng câu vẫn 900.
4. Vào Kho câu, tìm một mã như `CB-001`, lưu và ghi chú; tải lại kiểm tra.

ZIP đầy đủ `lingua-hosting.zip` dùng khi cài mới hoặc cần toàn bộ dự án. Để nâng cấp server đang có dữ liệu, dùng gói cập nhật và các bước ở trên.
