# FoldLex 100K — ghi chú dữ liệu

Bản hiện tại giữ nguyên đúng **100.000 mục từ duy nhất** từ
`data/FoldLex-100000-Vocabulary.csv` và đóng gói **97.760 giải nghĩa tiếng Anh
cục bộ**. Trong đó 97.623 nghĩa được xác minh trực tiếp từ nguồn từ điển mở
hoặc phần giải nghĩa tuyển chọn của FoldLex; 137 nghĩa là chú thích hình thái
được tạo từ một lemma đã có nghĩa thật và được đánh dấu riêng.

Còn **2.240 mục chưa có bằng chứng từ nguồn được phê duyệt**. Những mục này
được giữ lại trong ứng dụng nhưng không được gán nghĩa giả hay placeholder.
Xem `reports/unresolved-words.csv`, `reports/coverage.md` và
`reports/quality-audit.md`. Vì vậy không được mô tả bản phát hành này là có
100% coverage đã xác minh.

## Chạy offline

Mở `index.html`. Nếu trình duyệt hạn chế lưu trữ khi dùng `file://`, chạy:

```bash
python -m http.server 8000
```

Sau đó vào `http://localhost:8000/`. Website không gọi dịch vụ từ điển online
ở runtime; dữ liệu đã được nhúng trong HTML và có bản rich data trong `data/`.

## Dựng lại

```bash
python scripts/download_sources.py --output-dir .cache/foldlex-sources
python scripts/build_offline_database.py
python scripts/report_coverage.py
python scripts/validate_definitions.py
python -m unittest discover -s tests -p 'test_*.py'
```

Nguồn và giấy phép được ghi trong `docs/DATA_SOURCES.md` và thư mục
`LICENSES/`. Các nhãn band 4.0–9.0 chỉ là nhóm độ khó học tập ước lượng, không
phải band IELTS chính thức.

