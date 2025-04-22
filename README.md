## 📊 Website Keyword & SEO Analyzer

**Website Keyword & SEO Analyzer** là một ứng dụng web đơn giản viết bằng Flask, dùng để phân tích từ khóa, thông tin SEO, máy chủ, domain và liên kết ngoài từ một URL bất kỳ.

---

### 🚀 Các tính năng đã hỗ trợ

#### 🔑 Từ khóa phổ biến
- Trích xuất và thống kê 20 từ khóa xuất hiện nhiều nhất (≥4 ký tự) từ nội dung trang web.
- Có biểu đồ tần suất từ khóa bằng `Chart.js`.

#### 🧾 SEO Meta Info
- Hiển thị thẻ `title`, `meta[name=keywords]`, `meta[name=description]`.
- Tính điểm SEO đơn giản (tối đa 100 điểm) dựa trên độ dài tiêu đề, mô tả và thẻ `<h1>`.

#### 🖥️ Thông tin máy chủ (Server Info)
- Giao thức HTTP (version + status code).
- Server software.
- Loại nội dung (`Content-Type`).
- Dung lượng gốc và đã nén, tỷ lệ nén.
- Tự động nhận diện nếu có nén gzip/br/deflate.

#### 🌐 Domain & IP
- IP máy chủ.
- Tuổi của domain (tính từ ngày tạo đến hiện tại).
- Ngày hết hạn domain.
- Xếp hạng traffic toàn cầu (via `SimilarWeb`, không cần API key).
- Kiểm tra xem trang web có dùng HTTPS và có redirect không.

#### 📡 Subdomains (Tên miền phụ)
- Truy vấn các subdomain có trong chứng chỉ SSL thông qua `crt.sh`.

#### 🔗 Liên kết ngoài
- Trích xuất danh sách các liên kết ngoài (khác domain), tối đa 30.

---

### 🛠️ Công nghệ sử dụng

| Thành phần     | Mô tả                                           |
|----------------|-------------------------------------------------|
| **Flask**      | Web framework Python                           |
| **aiohttp**    | Gửi HTTP request bất đồng bộ                   |
| **BeautifulSoup** | Phân tích HTML                             |
| **whois**      | Lấy thông tin WHOIS domain                    |
| **Tailwind CSS** | Thiết kế giao diện responsive, dark mode     |
| **Font Awesome** | Icon đẹp mắt cho từng khối chức năng        |
| **Chart.js**   | Biểu đồ tần suất từ khóa                      |

---

### ⚙️ Cài đặt & chạy

1. **Clone dự án & tạo môi trường ảo:**

```bash
git clone https://github.com/dangkhoa2004/extract_keywords.git
cd extract_keywords
python -m venv venv
source venv/bin/activate  # hoặc venv\Scripts\activate (Windows)
```

2. **Cài đặt thư viện:**

```bash
pip install -r requirements.txt
```

3. **Chạy ứng dụng:**

```bash
python app.py
```

4. Truy cập tại: [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

### 📁 Cấu trúc thư mục

```
.
├── app.py
├── templates/
│   ├── index.html
│   └── components/
│       ├── header.html
│       ├── keyword_form.html
│       ├── loading.html
│       └── results.html
├── static/ (tuỳ chọn nếu có)
├── requirements.txt
└── README.md
```

---

### 📌 Ghi chú

- API từ `crt.sh` và `similarweb.com` không cần API key, nhưng có thể thay đổi hoặc giới hạn.
- Nếu bạn muốn triển khai production, hãy dùng `gunicorn`, `uvicorn`, hoặc `waitress`.

---

### 💡 Gợi ý mở rộng

- Tải báo cáo dạng PDF / CSV.
- Kiểm tra tốc độ trang với Lighthouse API.
- Thêm phân tích robots.txt, sitemap.xml.
- Tích hợp kiểm tra mobile-friendly hoặc accessibility.