from flask import Flask, request, jsonify, render_template
from flask_compress import Compress
import os, aiohttp, asyncio, re, socket, logging
from collections import Counter
from bs4 import BeautifulSoup
from datetime import datetime, timezone, date as dcls
from urllib.parse import urlparse
from functools import lru_cache
import whois

app = Flask(__name__)
Compress(app)
logging.basicConfig(level=logging.INFO)


# ──────────────────────── HỖ TRỢ XỬ LÝ THỜI GIAN ────────────────────────
def _to_aware(dt):
    if isinstance(dt, list):
        dt = dt[0] if dt else None
    if not dt:
        return None
    if isinstance(dt, datetime):
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    if isinstance(dt, dcls):
        return datetime(dt.year, dt.month, dt.day, tzinfo=timezone.utc)
    if isinstance(dt, str):
        dt = dt.strip()
        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                x = datetime.strptime(dt, fmt)
                return x if x.tzinfo else x.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


@lru_cache(maxsize=128)
def cached_whois(host: str):
    return whois.whois(host)


def whois_times(host: str):
    try:
        w = cached_whois(host)
    except Exception as exc:
        logging.warning("WHOIS lookup failed for %s: %s", host, exc)
        return None, None
    return _to_aware(w.creation_date), _to_aware(w.expiration_date)


# ──────────────────────── HỖ TRỢ BÊN NGOÀI ────────────────────────
async def get_similarweb_rank(session, domain):
    try:
        url = f"https://www.similarweb.com/website/{domain}/"
        html, *_ = await fetch(session, url)
        match = re.search(r'"globalRank":\s*{"rank":\s*(\d+)', html)
        return f"#{int(match.group(1)):,}" if match else "Unknown"
    except:
        return "Unknown"


async def get_subdomains(session, domain):
    try:
        url = f"https://crt.sh/?q=%.{domain}&output=json"
        async with session.get(url, timeout=10) as r:
            data = await r.json(content_type=None)
            subs = sorted(set(entry["name_value"] for entry in data if domain in entry["name_value"]))
            return list(set(
                s.strip() for d in subs for s in d.split('\n') if s != domain
            ))[:30]
    except:
        return []


# ──────────────────────── NETWORK + PARSER ────────────────────────
async def fetch(session, url: str):
    async with session.get(url, timeout=10, allow_redirects=True, ssl=True) as r:
        html = await r.text(errors="ignore")
        raw = await r.read()
        return html, r.headers, raw, r.version, r.status, r.reason, str(r.url)


async def extract_all(url: str):
    conn = aiohttp.TCPConnector(limit=10, ttl_dns_cache=300)
    try:
        async with aiohttp.ClientSession(connector=conn) as ses:
            html, headers, raw, ver, status, reason, final_url = await fetch(ses, url)

            soup = BeautifulSoup(html, "lxml")

            # 1. Từ khoá phổ biến
            words = Counter(re.findall(r"\b[a-zA-Z]{4,}\b", soup.get_text(" ").lower())).most_common(20)

            # 2. Thẻ meta cơ bản
            title = soup.title.string.strip() if soup.title else ""
            kw = soup.find("meta", attrs={"name": "keywords"})
            desc = soup.find("meta", attrs={"name": "description"})
            meta = {
                "title": title,
                "keywords": kw["content"] if kw and "content" in kw.attrs else "",
                "description": desc["content"] if desc and "content" in desc.attrs else "",
            }

            # 3. Điểm SEO đơn giản
            seo_score = 100
            if len(meta["title"]) > 60:
                seo_score -= 10
            if not meta["description"]:
                seo_score -= 10
            if not soup.find("h1"):
                seo_score -= 10

            # 4. Thông tin máy chủ
            enc = headers.get("Content-Encoding", "").lower()
            page_type = headers.get("Content-Type", "Unknown")
            server_sw = headers.get("Server", "Unknown")
            orig_size = len(raw)
            comp_size = int(headers.get("Content-Length", orig_size) or orig_size)
            server = {
                "protocol": f"HTTP/{ver.major}.{ver.minor} {status} {reason}",
                "page_type": page_type,
                "server": server_sw,
                "compressed": "yes" if enc in ("gzip", "br", "deflate") else "no",
                "original_size": f"{orig_size:,}",
                "compressed_size": f"{comp_size:,}",
                "compression_ratio": (
                    f"{100*(1-comp_size/orig_size):.2f}%" if orig_size else "0%"
                ),
            }

            # 5. Domain/IP + WHOIS
            host = urlparse(url).hostname or ""
            try:
                ip_addr = socket.gethostbyname(host)
            except socket.gaierror:
                ip_addr = "Unavailable"

            now = datetime.now(timezone.utc)
            cr, ex = whois_times(host)
            domain_age = f"{(now - cr).days} ngày (tạo {cr:%Y-%m-%d})" if cr else "Unknown"
            rank = await get_similarweb_rank(ses, host)
            subdomains = await get_subdomains(ses, host)

            # HTTPS & redirect
            https_status = {
                "https": final_url.startswith("https://"),
                "redirected": final_url != url
            }

            info = {
                "ip": ip_addr,
                "domain_age": domain_age,
                "expire": ex.strftime("%Y-%m-%d") if ex else "Unknown",
                "traffic_rank": rank,
                **https_status
            }

            # 6. Liên kết ngoài
            links = [
                a["href"]
                for a in soup.find_all("a", href=True)
                if a["href"].startswith("http") and host not in a["href"]
            ][:30]

            return {
                "keywords": words,
                "meta": meta,
                "seo_score": seo_score,
                "server": server,
                "info": info,
                "summary": f"Top keywords: {', '.join(k for k,_ in words[:5])}. "
                        f"IP: {ip_addr}. Server: {server_sw}.",
                "external_links": links,
                "subdomains": subdomains,
            }
    except Exception as e:
        return {
            "error": f"Fetch error: {str(e)}",
            "keywords": [], "meta": {}, "seo_score": 0,
            "server": {}, "info": {}, "external_links": [],
            "subdomains": [],
        }


# ──────────────────────── ROUTES ────────────────────────
@app.get("/")
def home():
    return render_template("index.html")


@app.post("/extract")
def extract():
    payload = request.get_json(silent=True) or {}
    url = (payload.get("url") or "").strip()

    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        data = loop.run_until_complete(extract_all(url))
        loop.close()
        return jsonify(data)
    except Exception as exc:
        logging.exception("extract failed")
        return jsonify({"error": str(exc)}), 500


# ──────────────────────── MAIN ────────────────────────
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
