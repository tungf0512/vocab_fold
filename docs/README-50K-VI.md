# FoldLex 50K — phiên bản 50.514 mục từ

**Đây là website HTML chạy trực tiếp, không yêu cầu cài đặt hoặc tài khoản.** Phù hợp với cách học giấy gập đôi: buổi sáng đọc cả hai cột **Words | Explanation**, trong ngày gập phần giải nghĩa và tự nhớ trước khi bấm mở.

## Số lượng dữ liệu

- **514 mục ban đầu**: có sẵn giải nghĩa tiếng Anh, dùng được không cần Internet.
- **50.000 mục mới**: được bổ sung từ kho từ tiếng Anh SCOWL (dùng trong bộ kiểm tra chính tả Hunspell en_US). Tất cả 50.000 **từ đều nằm ngay trong website**, tìm kiếm, lọc, lưu vào sổ, ôn tập và phát âm được.
- **Giải nghĩa của 50.000 mục mới không được tạo sẵn trong bản HTML này.** Khi bạn mở nghĩa lúc có Internet, website tra tiếng Anh tại Free Dictionary API (dictionaryapi.dev). Giải nghĩa tìm được được lưu vào IndexedDB của trình duyệt để xem lại, kể cả khi offline. Không phải từ nào cũng được API trả về định nghĩa; khi không có, website báo rõ.
- Có script `tools/make_fully_offline.py` để tự tạo thêm nhiều định nghĩa offline từ Open English WordNet 2025, dựa trên nguồn mở được cấp phép. Chi tiết bên dưới.

**IELTS không có một danh sách chính thức xác định từ nào thuộc band nào.** Nhãn 4.0–9.0 ở đây chỉ là nhóm học tham khảo, xếp tạm theo mức độ phổ biến của từ trong một nguồn văn bản lịch sử và loại từ. Đây **không phải** phân loại IELTS/CEFR đã được thẩm định. Kho 50.000 từ rất rộng, bao gồm cả từ quá hiếm/chuyên ngành và các biến thể, không phải 50.000 từ trọng tâm ôn thi.

Số mục theo nhóm:

| Nhóm ước lượng | Số mục |
|---|---:|
| 4.0 | 4.568 |
| 5.0 | 7.087 |
| 6.0 | 10.600 |
| 7.0 | 12.116 |
| 8.0 | 10.092 |
| 9.0 | 6.051 |
| **Tổng** | **50.514** |

## Cách sử dụng

1. Mở `index.html` bằng Chrome, Edge hoặc Firefox trên máy tính. Nên dùng trình duyệt có Internet để lấy nghĩa các từ mới.
2. Chọn **Morning Reading** để hiện hai cột. Chọn **Folded Recall** để giấu nghĩa; chỉ mở khi không nhớ.
3. Chọn **Got it** nếu nhớ được, **Again** nếu chưa nhớ. Ứng dụng có lịch nhắc ôn đơn giản, lưu trên trình duyệt của bạn.
4. Chọn **Word library** để duyệt hơn 50.000 từ, lọc nhóm band, loại từ, hoặc nhập từ khóa vào tìm kiếm.
5. Nút **Import/Export** để xuất dữ liệu và sao lưu tiến độ. CSV được xuất với lời giải thích đã có; ô trống nghĩa là từ đó chưa có giải nghĩa tải về. Tải JSON sao lưu tiến độ để chuyển trình duyệt.

Lưu ý: dữ liệu ghi nhớ là **trên từng trình duyệt và thiết bị**, không đồng bộ sang máy khác. Nếu trình duyệt xóa dữ liệu trang, tiến độ có thể mất; hãy thường xuyên backup. Nếu Chrome chặn IndexedDB trên trang `file://`, hãy chạy server nhỏ hoặc tải website lên dịch vụ hosting tĩnh:

```bash
python -m http.server 8000
# Truy cập http://localhost:8000
```

## Tạo bản với định nghĩa WordNet có thể dùng offline

Bản HTML có sẵn chứa đầy đủ **tên của 50.000 từ** nhưng không có sẵn toàn bộ phần giải nghĩa. Nếu bạn muốn lấy nghĩa từ từ điển WordNet theo dạng đóng gói trong một HTML:

1. Tải tài nguyên gốc `english-wordnet-2025.xml.gz` từ trang [Open English WordNet Downloads](https://en-word.net/downloads) (bản **2025 XML.gz**). Trang chủ: https://en-word.net/.
2. Đặt `english-wordnet-2025.xml.gz` bên cạnh `index.html` và `tools/make_fully_offline.py`, hoặc đưa đường dẫn tới file bằng cờ `--wordnet`.
3. Cài Python 3 và `lxml`: `python -m pip install lxml`.
4. Chạy:

```bash
python tools/make_fully_offline.py --website index.html \
  --wordnet english-wordnet-2025.xml.gz \
  --output FoldLex-50K-Fully-Offline.html
```

Script sẽ ghép các giải nghĩa WordNet khớp với từ trong danh sách. **Không bảo đảm đủ cả 50.000 định nghĩa** (WordNet có thể không chứa một số hình thái hoặc từ rất hiếm). Các từ còn thiếu tiếp tục sử dụng tra cứu trực tuyến. File HTML đã sinh có thể mở trực tiếp trên trình duyệt, không cần gọi API cho những định nghĩa WordNet đã đóng gói.

Nếu không tự tải file, script có thể thử tải source WordNet khi kết nối Internet (bỏ qua `--wordnet`).

## Nguồn và giấy phép

- **Danh sách từ mới:** [SCOWL / Kevin Atkinson](https://wordlist.aspell.net/) qua `/usr/share/hunspell/en_US.dic`. Thông báo bản quyền và điều khoản đi kèm ở `LICENSES/SCOWL-HUNSPELL.txt` (bao gồm nội dung từ gói Hunspell en_US). Phân loại từ loại tham chiếu từ `TextBlob/en/en-lexicon` có nguồn Brill và Twitter POS (MIT-like và CC BY 3.0); xem [TextBlob](https://github.com/sloria/TextBlob).
- **Dữ liệu tần suất xếp nhóm gần đúng:** `TextBlob/en/en-spelling.txt` tham chiếu văn bản public domain Project Gutenberg, một số nguồn Wiktionary và British National Corpus. Đây không phải đánh giá chính thức IELTS.
- **Nguồn giải nghĩa online:** [Free Dictionary API](https://dictionaryapi.dev/), chỉ tra khi người dùng mở nghĩa. Khả năng trả lời và giấy phép cụ thể có thể phụ thuộc nguồn từ điển/API.
- **Nguồn giải nghĩa offline tùy chọn:** [Open English WordNet 2025](https://en-word.net/) — CC BY 4.0, dẫn xuất từ Princeton WordNet; cần ghi nhận tác giả và đáp ứng giấy phép WordNet. Xem `LICENSES/WORDNET-ATTRIBUTION.txt`. Script chỉ tải dữ liệu từ nguồn công khai khi được người dùng chạy.
- **514 nghĩa gốc** được biên soạn riêng cho bản FoldLex starter.

**Cam kết về dữ liệu:** các mục không có giải nghĩa không được điền nội dung tự tạo hay giải nghĩa giả. Dữ liệu 50.000 mục là danh sách từ rộng theo hệ thống chính tả, không phải danh sách 50.000 từ IELTS được kiểm chứng.
