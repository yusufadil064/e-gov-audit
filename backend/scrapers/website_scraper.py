"""
WebsiteScraper
Responsible for fetching website content and extracting structural signals
that inform the cost estimation model.
"""
import re
import time
import urllib.request
import urllib.error
import urllib.parse
import ssl
import socket
from typing import Optional
from backend.models.website_profile import WebsiteMetrics, TechStack


class WebsiteScraper:
    """
    Fetches and parses a government website to extract technical signals.
    Uses only stdlib to avoid dependency issues.
    """

    KNOWN_CMS = {
        "wordpress": ["wp-content", "wp-includes", "wp-json", "WordPress"],
        "drupal": ["drupal", "Drupal", "sites/default"],
        "joomla": ["joomla", "Joomla", "/components/com_"],
        "laravel": ["laravel_session", "X-Powered-By: PHP", "csrf-token"],
        "next.js": ["__NEXT_DATA__", "_next/static"],
        "react": ["__reactFiber", "react-root", "data-reactroot"],
        "vue": ["__vue__", "data-v-", "nuxt"],
    }

    KNOWN_CDN = {
        "cloudflare": ["cloudflare", "cf-ray"],
        "aws": ["amazonaws.com", "cloudfront.net"],
        "gcp": ["googleapis.com", "googleusercontent.com"],
        "azure": ["azure.com", "azurefd.net"],
        "fastly": ["fastly"],
        "bgn-cdn": ["cdn-web.bgn.go.id"],
    }

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self._ctx = ssl.create_default_context()
        self._ctx.check_hostname = False
        self._ctx.verify_mode = ssl.CERT_NONE

    def fetch(self, url: str) -> dict:
        """
        Main entry: fetch website and return raw signal dict.
        """
        url = self._normalize_url(url)
        result = {
            "url": url,
            "html": "",
            "headers": {},
            "status_code": 0,
            "error": None,
            "load_time_ms": 0,
        }
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (compatible; GovBudgetAnalyzer/1.0; "
                        "+https://github.com/example)"
                    )
                },
            )
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=self.timeout, context=self._ctx) as resp:
                result["status_code"] = resp.status
                result["headers"] = dict(resp.headers)
                result["html"] = resp.read(500_000).decode("utf-8", errors="replace")
                result["load_time_ms"] = int((time.time() - t0) * 1000)
        except urllib.error.HTTPError as e:
            result["status_code"] = e.code
            result["error"] = f"HTTP {e.code}: {e.reason}"
        except urllib.error.URLError as e:
            result["error"] = f"URL Error: {e.reason}"
        except socket.timeout:
            result["error"] = "Connection timed out"
        except Exception as e:
            result["error"] = str(e)
        return result

    def extract_metrics(self, fetch_result: dict) -> WebsiteMetrics:
        """
        Parses raw fetch result into a structured WebsiteMetrics object.
        """
        html = fetch_result.get("html", "")
        headers = fetch_result.get("headers", {})
        url = fetch_result.get("url", "")
        m = WebsiteMetrics()

        # SSL
        m.has_ssl = url.startswith("https://")

        # Mobile responsive
        m.has_mobile_responsive = bool(
            re.search(r'viewport.*width=device-width', html, re.IGNORECASE)
        )

        # Search
        m.has_search = bool(
            re.search(r'<input[^>]*(search|pencarian|cari)[^>]*>', html, re.IGNORECASE)
            or re.search(r'type=["\']search["\']', html, re.IGNORECASE)
        )

        # Login system
        m.has_login_system = bool(
            re.search(r'(login|masuk|signin|log in)', html, re.IGNORECASE)
            and re.search(r'<(form|input)[^>]*>', html, re.IGNORECASE)
        )

        # Map integration
        m.has_map_integration = bool(
            re.search(r'(google.*map|leaflet|openstreetmap|maps\.googleapis)', html, re.IGNORECASE)
        )

        # Media gallery
        m.has_media_gallery = bool(
            re.search(r'(gallery|galeri|lightbox|slick|swiper|carousel)', html, re.IGNORECASE)
        )

        # Multilingual
        m.has_multilingual = bool(
            re.search(r'(lang=["\'][a-z]{2}["\']|hreflang|language.switcher)', html, re.IGNORECASE)
        ) and bool(re.search(r'(english|indonesia|en\b)', html, re.IGNORECASE))

        # API endpoints
        m.has_api = bool(
            re.search(r'(/api/|/rest/|/graphql|fetch\(|axios\.|XMLHttpRequest)', html, re.IGNORECASE)
        )

        # Navigation depth
        nav_links = re.findall(r'<a\s[^>]*href=["\']([^"\']+)["\'][^>]*>', html, re.IGNORECASE)
        m.total_nav_items = len(nav_links)

        # Submenu / dropdown depth estimation
        dropdown_count = len(re.findall(r'dropdown|submenu|sub-menu|nav-child', html, re.IGNORECASE))
        m.nav_depth = min(4, 1 + (dropdown_count // 3))

        # Estimate page count from nav items
        unique_paths = set()
        for link in nav_links:
            parsed = urllib.parse.urlparse(link)
            if parsed.path and parsed.path != "/" and len(parsed.path) > 1:
                unique_paths.add(parsed.path.split("?")[0])
        m.total_pages_estimated = max(5, len(unique_paths))

        # CDN detection
        combined = html + str(headers)
        m.has_cdn = any(
            kw in combined
            for cdn_signals in self.KNOWN_CDN.values()
            for kw in cdn_signals
        )

        # Subdomain detection from links
        base_domain = urllib.parse.urlparse(url).netloc
        subdomains = set()
        for link in nav_links:
            parsed = urllib.parse.urlparse(link)
            if parsed.netloc and parsed.netloc != base_domain and base_domain.split(".", 1)[-1] in parsed.netloc:
                subdomains.add(parsed.netloc)
        m.subdomains = list(subdomains)

        # Custom design heuristic
        custom_css = len(re.findall(r'<link[^>]+stylesheet[^>]+>', html, re.IGNORECASE))
        inline_style = len(re.findall(r'<style[^>]*>', html, re.IGNORECASE))
        m.has_custom_design = (custom_css + inline_style) >= 2

        # CMS / DB detection
        for cms_name, signals in self.KNOWN_CMS.items():
            if any(sig in html for sig in signals):
                m.has_cms = True
                m.has_database = True
                break

        return m

    def extract_tech_stack(self, fetch_result: dict) -> TechStack:
        """
        Detects framework, CMS, CDN, server, etc.
        """
        html = fetch_result.get("html", "")
        headers = fetch_result.get("headers", {})
        ts = TechStack()

        # Server
        ts.server = headers.get("Server", headers.get("server", "Unknown"))

        # CMS detection
        for cms_name, signals in self.KNOWN_CMS.items():
            if any(sig in html for sig in signals):
                ts.cms = cms_name
                ts.framework = cms_name
                break

        # PHP detection
        powered_by = headers.get("X-Powered-By", headers.get("x-powered-by", ""))
        if "PHP" in powered_by:
            ts.language = "PHP"
        elif "ASP.NET" in powered_by:
            ts.language = "C# / ASP.NET"

        # Next.js / React
        if "__NEXT_DATA__" in html:
            ts.framework = "Next.js"
            ts.language = "JavaScript (Node.js)"
        elif "data-reactroot" in html or "__reactFiber" in html:
            ts.framework = "React"
            ts.language = "JavaScript"
        elif "__vue__" in html or "data-v-" in html:
            ts.framework = "Vue.js"
            ts.language = "JavaScript"

        # CDN
        combined = html + str(headers)
        for cdn_name, signals in self.KNOWN_CDN.items():
            if any(kw in combined for kw in signals):
                ts.cdn = cdn_name
                break

        # JS Libraries
        libs = []
        lib_patterns = {
            "jQuery": r'jquery',
            "Bootstrap": r'bootstrap',
            "Tailwind": r'tailwind',
            "Font Awesome": r'font-awesome|fontawesome',
            "Leaflet": r'leaflet',
            "Chart.js": r'chart\.js',
            "Slick": r'slick',
            "Swiper": r'swiper',
        }
        for lib, pat in lib_patterns.items():
            if re.search(pat, html, re.IGNORECASE):
                libs.append(lib)
        ts.detected_libraries = libs

        return ts

    @staticmethod
    def _normalize_url(url: str) -> str:
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url
