from flask import Flask, render_template, request, jsonify
import aiohttp
import asyncio
from bs4 import BeautifulSoup
from collections import Counter
import re
import socket
import ipaddress
import whois
from datetime import datetime, timezone

app = Flask(__name__)

# -------------------- Async Functions --------------------
async def fetch(session, url):
    async with session.get(url, timeout=10) as response:
        text = await response.text()
        raw_bytes = await response.read()
        return text, response.headers, response.status, response.reason, response.version, raw_bytes

async def extract_all_info(url):
    async with aiohttp.ClientSession() as session:
        try:
            # Fetch page
            html_text, headers, status, reason, version, content = await fetch(session, url)
            soup = BeautifulSoup(html_text, 'html.parser')

            # Keywords
            text_body = soup.get_text().lower()
            words = re.findall(r"\b\w{4,}\b", text_body)
            keywords = Counter(words).most_common(20)

            # Meta
            title = soup.title.string.strip() if soup.title else ""
            keywords_tag = soup.find("meta", attrs={"name": "keywords"})
            description_tag = soup.find("meta", attrs={"name": "description"})
            meta = {
                "title": title,
                "keywords": keywords_tag['content'] if keywords_tag and 'content' in keywords_tag.attrs else "",
                "description": description_tag['content'] if description_tag and 'content' in description_tag.attrs else ""
            }

            # SEO Score
            score = 100
            if len(meta['title']) > 60:
                score -= 10
            if not meta['description']:
                score -= 10
            if not soup.find('h1'):
                score -= 10

            # Server Info
            protocol = f"HTTP/{version.major}.{version.minor} {status} {reason}"
            content_type = headers.get('Content-Type', 'Unknown')
            server_type = headers.get('Server', 'Unknown')
            encoding = headers.get('Content-Encoding', '').lower()
            compressed = encoding in ['gzip', 'br', 'deflate']
            original_size = len(content)
            compressed_size = int(headers.get('Content-Length', original_size)) if headers.get('Content-Length') else original_size
            ratio = 100 * (1 - (compressed_size / original_size)) if original_size else 0

            server = {
                'protocol': protocol,
                'page_type': content_type,
                'server': server_type,
                'compressed': 'yes' if compressed else 'no',
                'original_size': f"{original_size:,}",
                'compressed_size': f"{compressed_size:,}",
                'compression_ratio': f"{ratio:.2f}%"
            }

            # Domain & WHOIS Info
            domain = url.replace('http://', '').replace('https://', '').split('/')[0]
            host = domain.split(':')[0]

            # Resolve IP
            try:
                ip = socket.gethostbyname(host)
            except socket.gaierror:
                ip = 'Unavailable'

            # WHOIS lookup (skip literal IPs)
            created = expire = None
            now = datetime.now(timezone.utc)
            domain_age = expire_str = 'Unknown'
            try:
                # if host is literal IP, this will succeed and we skip whois
                ipaddress.ip_address(host)
                # it's an IP, skip WHOIS
            except ValueError:
                # not an IP, attempt WHOIS
                try:
                    w = whois.whois(host)
                    created = w.creation_date[0] if isinstance(w.creation_date, list) else w.creation_date
                    expire  = w.expiration_date[0] if isinstance(w.expiration_date, list) else w.expiration_date
                    if created:
                        domain_age = f"{(now - created).days} days (Created on {created.strftime('%Y-%m-%d')})"
                    if expire:
                        expire_str = expire.strftime('%B %d, %Y')
                except (socket.gaierror, socket.timeout, whois.parser.PywhoisError) as e:
                    app.logger.warning(f"WHOIS lookup failed for {host}: {e}")

            info = {
                'ip': ip,
                'domain_age': domain_age,
                'expire': expire_str
            }

            # External links
            links = soup.find_all('a', href=True)
            external_links = [a['href'] for a in links if a['href'].startswith('http') and host not in a['href']]

            summary = (
                f"This website contains keywords such as: {', '.join([k[0] for k in keywords[:5]])}. "
                f"IP: {ip}. Hosted on {server_type}."
            )

            return {
                'keywords': keywords,
                'meta': meta,
                'seo_score': score,
                'server': server,
                'info': info,
                'summary': summary,
                'external_links': external_links,
                'subdomains': []
            }
        except Exception as e:
            app.logger.error(f"Extraction failed: {e}")
            return {'error': str(e)}

# -------------------- Routes --------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/extract', methods=['POST'])
def extract():
    data = request.get_json() or {}
    url = data.get('url')
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    result = asyncio.run(extract_all_info(url))
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
