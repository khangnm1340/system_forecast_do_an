# TỔNG QUAN ĐỀ TÀI  
## Suy luận trạng thái tương tác người dùng từ dữ liệu sử dụng tài nguyên hệ thống

---

## 1. Giới thiệu đề tài

Trong các hệ điều hành hiện đại, hệ thống liên tục ghi nhận nhiều loại dữ liệu telemetry như mức sử dụng CPU, RAM, I/O đĩa, mạng, GPU cũng như các tín hiệu tương tác như bàn phím và chuột. Những dữ liệu này thường được sử dụng cho mục đích giám sát hiệu năng, chẩn đoán lỗi hoặc tối ưu tài nguyên.

Tuy nhiên, một câu hỏi mang tính nghiên cứu được đặt ra là:

> **Liệu chỉ từ dữ liệu telemetry của hệ thống, ta có thể suy luận được trạng thái tương tác của người dùng hay không?**

Đề tài này tập trung vào việc khảo sát khả năng suy luận các trạng thái tương tác người–máy (ví dụ: nhàn rỗi, gõ phím, duyệt web, xem nội dung đa phương tiện) **dựa hoàn toàn trên dữ liệu sử dụng tài nguyên hệ thống**, thay vì quan sát trực tiếp hành vi người dùng.

---

## 2. Bài toán ban đầu và động lực nghiên cứu

### 2.1. Bài toán ban đầu

Ở giai đoạn đầu, nhóm định hướng tiếp cận bài toán theo hướng:

- Dự đoán mức sử dụng CPU trong tương lai gần (ví dụ: 5 giây tiếp theo)
- Xem đây là một bài toán hồi quy (regression)
- Dữ liệu đầu vào bao gồm các chỉ số hệ thống và hành vi người dùng

### 2.2. Nhận xét và hạn chế

Trong quá trình phân tích dữ liệu thực tế thu thập được trên máy cá nhân, nhóm nhận thấy một vấn đề quan trọng:

- Phần lớn thời gian, mức sử dụng CPU của người dùng cá nhân dao động quanh giá trị rất thấp (khoảng 5–10%)
- Phân phối dữ liệu bị lệch mạnh, không có nhiều đỉnh (peak)
- Một mô hình đơn giản luôn dự đoán giá trị trung bình cũng có thể đạt sai số thấp

Điều này dẫn đến hệ quả:

> Việc dự đoán CPU usage trong bối cảnh này tuy có thể **đúng về mặt kỹ thuật** nhưng **không mang nhiều ý nghĩa thực tiễn hoặc khoa học**.

Từ nhận định trên, nhóm quyết định **không tiếp tục theo đuổi bài toán dự đoán tài nguyên đơn thuần**, mà chuyển sang một hướng tiếp cận khác có giá trị phân tích cao hơn.

---

## 3. Thu thập dữ liệu telemetry hệ thống

Nhóm xây dựng các script Python để ghi nhận dữ liệu telemetry trực tiếp trên hệ điều hành Linux, với tần suất **1 giây mỗi lần ghi**. Toàn bộ dữ liệu được thu thập từ hệ thống thật, không sử dụng dữ liệu giả lập.

### 3.1. Nhóm dữ liệu tài nguyên hệ thống

Bao gồm:

- CPU usage (%)
- RAM usage (%)
- Disk read / write (bytes per second)
- Network in / out (bytes per second)
- GPU usage (đối với GPU tích hợp Intel)

### 3.2. Nhóm dữ liệu tương tác người dùng

Bao gồm:

- Trạng thái hoạt động của bàn phím (`keyboard_active`)
- Số phím nhấn mỗi giây (`keys_per_sec`)
- Thời gian gõ liên tục (`typing_burst_sec`)
- Thời gian không tương tác (`idle_time_sec`)
- Trạng thái hoạt động của chuột (`mouse_active`)
- Cửa sổ ứng dụng đang được focus (`active window`, `app_id`, `window_title`)
- Số lượng process đang chạy

Các dữ liệu này **không ghi nhận nội dung nhạy cảm** (ví dụ: nội dung gõ phím, URL, lịch sử lệnh), nhằm đảm bảo tính riêng tư cho người dùng.

---

## 4. Nhận diện giới hạn của bài toán dự đoán tài nguyên

Từ dữ liệu thu thập được, nhóm nhận thấy:

- Tài nguyên hệ thống phản ánh **hệ quả của hành vi**, không phải hành vi trực tiếp
- Nhiều hành vi khác nhau có thể tạo ra **mẫu sử dụng tài nguyên tương tự**
- Các trạng thái “nhẹ” (typing, browsing) rất khó phân biệt nếu chỉ dựa vào CPU hoặc RAM

Do đó, việc dự đoán chính xác **giá trị tài nguyên cụ thể** không phải là mục tiêu phù hợp trong bối cảnh nghiên cứu này.

---

## 5. Cân nhắc các hướng tiếp cận khác

Nhóm đã cân nhắc nhiều hướng tiếp cận khác nhau, bao gồm:

- Dự đoán đồng thời nhiều tài nguyên (CPU, RAM, Disk, Network)
- Sử dụng mô hình chuỗi thời gian phức tạp (LSTM, GRU)
- Tập trung mạnh vào GPU hoặc các workload nặng

Tuy nhiên, các hướng này đều gặp một hoặc nhiều vấn đề sau:

- Yêu cầu dữ liệu khó thu thập đồng nhất giữa các máy
- Dữ liệu bị mất cân bằng nghiêm trọng
- Mô hình phức tạp nhưng khó giải thích và khó đánh giá

Từ đó, nhóm quyết định **định nghĩa lại bài toán**.

---

## 6. Bài toán mới: Suy luận trạng thái tương tác người dùng

### 6.1. Định nghĩa bài toán

Thay vì dự đoán giá trị tài nguyên, nhóm chuyển sang bài toán:

> **Suy luận trạng thái tương tác của người dùng dựa trên dữ liệu telemetry hệ thống**

Các trạng thái tương tác (interaction states) được định nghĩa ở mức **coarse-grained**, bao gồm:

- **Idle** (nhàn rỗi)
- **Typing** (gõ phím)
- **Browsing / Navigating** (duyệt nội dung)
- **Media playback** (xem video, nghe nhạc)
- **Interactive heavy** (lập trình, biên dịch, thao tác nặng)

### 6.2. Vai trò của rule-based labeling

Do không có nhãn sẵn, nhóm sử dụng **các luật (heuristics)** để gán nhãn ban đầu, ví dụ:

- **Typing**: `keys_per_sec` vượt một ngưỡng nhất định
- **Idle**: bàn phím và chuột không hoạt động trong một khoảng thời gian dài
- **Media playback**: `network_in` cao trong khi bàn phím không hoạt động

Quá trình này được kiểm tra bằng cách:

- Hiển thị trạng thái suy luận theo thời gian thực
- So sánh với hành vi thực tế của người dùng

Nhóm xác định rằng:

> Nếu giai đoạn gán nhãn sai, **toàn bộ mô hình học máy phía sau sẽ không còn ý nghĩa**.

---

## 7. Vai trò của học máy trong đề tài

Trong đề tài này, học máy **không được sử dụng để “đoán hành vi một cách kỳ diệu”**, mà đóng vai trò:

- Học ánh xạ từ dữ liệu telemetry → trạng thái tương tác
- Đánh giá mức độ **quan sát được (observability)** của hành vi người dùng
- Kiểm tra xem dữ liệu hệ thống có đủ thông tin để phân biệt các trạng thái hay không

Các mô hình đơn giản (ví dụ: *logistic regression*, *random forest*) được ưu tiên hơn mô hình phức tạp, nhằm:

- Dễ giải thích
- Phù hợp với kích thước và chất lượng dữ liệu thu thập được

---

## 8. Thách thức và vấn đề dữ liệu

Trong quá trình thu thập và phân tích, nhóm gặp một số thách thức chính:

- Dữ liệu mất cân bằng (ví dụ: thời gian xem YouTube chiếm tỷ lệ lớn)
- Sự khác biệt hành vi giữa các người dùng
- Ranh giới mờ giữa các trạng thái (ví dụ: browsing và typing)

Những vấn đề này được xem là **đặc trưng của dữ liệu thực tế**, và là một phần quan trọng của bài toán nghiên cứu.

---

## 9. Kết luận và bài học rút ra

Thông qua đề tài này, nhóm rút ra một số nhận định quan trọng:

- Việc **định nghĩa bài toán đúng** quan trọng hơn việc lựa chọn mô hình phức tạp
- Không phải mọi hành vi người dùng đều có thể suy luận chính xác từ dữ liệu telemetry hệ thống
- Dữ liệu thực tế thường nhiễu, mất cân bằng và khó xử lý hơn dữ liệu lý tưởng
- Học máy nên được sử dụng như **một công cụ đánh giá giới hạn**, không phải lời giải tuyệt đối

Đề tài hướng tới mục tiêu **hiểu rõ giới hạn của hệ thống**, thay vì chỉ tối ưu độ chính xác của mô hình.
