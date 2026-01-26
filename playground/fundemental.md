# Typing & Focus Logger – Fundamental Input Labels

> Author: Thiên An  
> Purpose: Giải thích **cách hoạt động cốt lõi (fundamental)** của các nhãn (labels) liên quan đến **bàn phím / chuột / tập trung** trong script logger.

---

## 1. Tổng quan kiến trúc input

Script **không hook trực tiếp vào kernel** mà sử dụng:

- `libinput debug-events` (subprocess)
- Phân tích **stdout realtime**
- Lưu **timestamp** của sự kiện
- Suy luận trạng thái người dùng dựa trên *thời gian gần nhất có input*

👉 Tất cả label đều **dẫn xuất (derived features)**, không phải raw signal.

---

## 2. Luồng dữ liệu phím (Keyboard pipeline)

### 2.1 Input listener

```python
if "KEYBOARD_KEY" in line:
    last_keyboard_time = now
    if "pressed" in line:
        keystrokes.append(now)
        keys_counter += 1
```

#### Ý nghĩa:

- `last_keyboard_time`:
  - Lưu **thời điểm gần nhất có bất kỳ phím nào** (pressed hoặc released)

- `keystrokes` (deque):
  - Chỉ lưu **thời điểm nhấn phím (pressed)**
  - Dùng để tính WPM trung bình trong cửa sổ `WINDOW`

- `keys_counter`:
  - Đếm **số phím nhấn trong 1 interval (1 giây)**
  - Reset sau mỗi lần log

---

## 3. keyboard_active (label nhị phân)

```python
def is_keyboard_active():
    return time.time() - last_keyboard_time <= INPUT_ACTIVE_WINDOW
```

### Định nghĩa

| Label | Giá trị | Ý nghĩa |
|------|--------|--------|
| keyboard_active | 1 | Có phím được nhấn trong vòng `INPUT_ACTIVE_WINDOW` giây |
| keyboard_active | 0 | Không có hoạt động bàn phím |

📌 Đây **không phải đang gõ**, chỉ là **có tương tác bàn phím gần đây**.

---

## 4. idle_time_sec (label nền tảng nhất)

```python
def get_idle_time():
    return round(time.time() - max(last_keyboard_time, last_mouse_time), 1)
```

### Định nghĩa

- Idle = **thời gian kể từ input cuối cùng (keyboard hoặc mouse)**
- Là nền tảng cho:
  - typing_burst
  - focus reset

📌 Idle **không phân biệt người dùng đang suy nghĩ hay rời máy**.

---

## 5. typing_burst_sec (label hành vi)

```python
def get_typing_burst():
    idle = get_idle_time()

    if idle < BURST_IDLE_THRESHOLD:
        if typing_burst_start is None:
            typing_burst_start = time.time()
        return time.time() - typing_burst_start
    else:
        typing_burst_start = None
        return 0.0
```

### Định nghĩa logic

- Một **typing burst** bắt đầu khi:
  - Idle < `BURST_IDLE_THRESHOLD`

- Burst **kết thúc** khi:
  - Người dùng ngừng input quá threshold

### Ý nghĩa thực tế

| Trường hợp | typing_burst_sec |
|----------|------------------|
| Gõ liên tục | Tăng dần |
| Dừng gõ vài giây | Reset về 0 |

📌 Label này đo **độ liền mạch của hành vi gõ**, không phải tốc độ.

---

## 6. avg_wpm (WPM trung bình cửa sổ)

```python
def avg_wpm():
    return len(keystrokes) / 5
```

- `keystrokes` chỉ giữ các phím trong `WINDOW` (60s)
- 5 keystrokes = 1 word (chuẩn thống kê)

📌 Avg WPM **ổn định**, ít nhiễu, dùng cho EMA smoothing.

---

## 7. instant_wpm (WPM tức thời)

```python
def instant_wpm(keys_per_sec):
    return (keys_per_sec * 60) / 5
```

- Dựa trên **số phím gõ trong 1 giây**
- Rất nhạy, rất nhiễu

📌 Dùng để phát hiện:
- Spike gõ nhanh
- Ngắt quãng hành vi

---

## 8. focus_streak_sec (label nhận thức)

```python
def get_focus_streak():
    if is_keyboard_active() or is_mouse_active():
        if focus_streak_start is None:
            focus_streak_start = time.time()
        return time.time() - focus_streak_start
    else:
        focus_streak_start = None
        return 0.0
```

### Định nghĩa

- Focus = **có tương tác liên tục**
- Reset khi:
  - Không có keyboard
  - Không có mouse

📌 Đây là **focus hành vi**, không phải focus nhận thức sâu.

---

## 9. true_focus (label tổng hợp)

```python
true_focus = int(keyboard or mouse)
```

| true_focus | Ý nghĩa |
|-----------|--------|
| 1 | Người dùng đang tương tác hệ thống |
| 0 | Không có input |

📌 Dùng cho:
- Phân tích flow
- Phát hiện distraction

---

## 10. Quan hệ giữa các label

```text
last_keyboard_time
        ↓
 keyboard_active
        ↓
 idle_time_sec
        ↓
 typing_burst_sec

 keyboard_active + mouse_active
        ↓
   focus_streak_sec
```

---

## 11. Tóm tắt triết lý thiết kế

- ❌ Không đo phím trực tiếp
- ✅ Đo **thời gian + hành vi**
- ✅ Phù hợp cho:
  - ML labeling
  - Behavior analysis
  - Productivity research

> Đây là **human behavior telemetry**, không phải keylogger.

---

## 12. Gợi ý đặt file trong repo

```text
/docs
  └── input-labels.md
```

README.md:
```md
- 📊 Input behavior labeling: `docs/input-labels.md`
```

---

Nếu bạn muốn:
- Sơ đồ state machine
- Refactor thành class
- Gắn label cho ML training

👉 nói mình, mình viết tiếp cho bạn.

