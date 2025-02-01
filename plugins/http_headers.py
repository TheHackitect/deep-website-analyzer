# plugins/http_headers.py
from plugins.base_plugin import BasePlugin
import requests

class HTTPHeadersPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "HTTP Headers"

    @property
    def description(self) -> str:
        return "Retrieve server type, content type, cookies, and security headers."

    def run(self, target: str) -> dict:
        try:
            headers = {
                'User-Agent': 'DeepWebsiteAnalyzer/1.0'
            }
            response = requests.head(target, headers=headers, allow_redirects=True, timeout=10)
            if response.status_code >= 400:
                # Some servers may not respond properly to HEAD requests
                response = requests.get(target, headers=headers, allow_redirects=True, timeout=10)

            headers = response.headers

            # Extract relevant headers
            server = headers.get('Server', 'N/A')
            content_type = headers.get('Content-Type', 'N/A')
            cookies = response.cookies.get_dict()
            security_headers = {
                'Content-Security-Policy': headers.get('Content-Security-Policy', 'N/A'),
                'Strict-Transport-Security': headers.get('Strict-Transport-Security', 'N/A'),
                'X-Frame-Options': headers.get('X-Frame-Options', 'N/A'),
                'X-Content-Type-Options': headers.get('X-Content-Type-Options', 'N/A'),
                'Referrer-Policy': headers.get('Referrer-Policy', 'N/A'),
                'Permissions-Policy': headers.get('Permissions-Policy', 'N/A'),
                'X-XSS-Protection': headers.get('X-XSS-Protection', 'N/A')
            }

            return {
                "Server": server,
                "Content-Type": content_type,
                "Cookies": cookies,
                "Security Headers": security_headers
            }
        except Exception as e:
            return {"Error": str(e)}
