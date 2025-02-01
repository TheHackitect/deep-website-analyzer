# plugins/web_server_software_detection.py
import requests
from bs4 import BeautifulSoup, Comment
import re
import socket
from plugins.base_plugin import BasePlugin


class WebServerSoftwareDetectionPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Web Server Software Detection"

    @property
    def description(self) -> str:
        return "Identify the web server software and its version."

    @property
    def data_format(self) -> str:
        return "json"

    @property
    def required_api_keys(self) -> list:
        return []

    def run(self, target: str) -> dict:
        results = {}
        try:
            base_url = self.normalize_url(target)
            # 1. Perform Banner Grabbing via HEAD request
            server_info = self.banner_grabbing(base_url)
            results["ServerInfo"] = server_info

            # 2. Analyze HTML for Meta Tags and Comments
            html_info = self.analyze_html(base_url)
            results["HTMLAnalysis"] = html_info

            # 3. Perform Port Scanning
            port_info = self.check_common_ports(base_url)
            results["PortAnalysis"] = port_info

        except Exception as e:
            results["Error"] = str(e)

        return results

    def normalize_url(self, target: str) -> str:
        if not target.startswith(("http://", "https://")):
            target = "http://" + target
        return target

    def banner_grabbing(self, url: str) -> dict:
        server_info = {}
        try:
            headers = {
                "User-Agent": "DeepWebsiteAnalyzer/1.0"
            }
            response = requests.head(url, headers=headers, timeout=10)
            server_header = response.headers.get("Server", "")
            if server_header:
                server_info["ServerHeader"] = server_header
                # Attempt to parse server and version
                match = re.match(r'([A-Za-z\-]+)\s?/?\s?(\d+(\.\d+)*)?', server_header)
                if match:
                    server_info["Server"] = match.group(1)
                    server_info["Version"] = match.group(2) if match.group(2) else "Unknown"
                else:
                    server_info["Server"] = "Unknown"
                    server_info["Version"] = "Unknown"
            else:
                server_info["ServerHeader"] = "Not Found"
                server_info["Server"] = "Unknown"
                server_info["Version"] = "Unknown"
        except requests.RequestException:
            server_info["Error"] = "Failed to perform banner grabbing."
        return server_info

    def analyze_html(self, url: str) -> dict:
        html_info = {}
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Check for meta generator tag
                generator = soup.find('meta', attrs={'name': 'generator'})
                if generator and generator.get('content'):
                    html_info["Generator"] = generator['content']
                else:
                    html_info["Generator"] = "Not Found"

                # Check for HTML comments for server info
                comments = soup.find_all(string=lambda text: isinstance(text, Comment))
                server_comments = []
                for comment in comments:
                    if re.search(r'(Apache|Nginx|IIS|LiteSpeed|Caddy)', comment, re.IGNORECASE):
                        server_comments.append(comment.strip())
                html_info["ServerComments"] = server_comments
            else:
                html_info["Error"] = f"Received status code {response.status_code}"
        except requests.RequestException:
            html_info["Error"] = "Failed to retrieve HTML content."
        return html_info

    def check_common_ports(self, base_url: str) -> dict:
        port_info = {}
        # Extract hostname and scheme
        parsed_url = requests.utils.urlparse(base_url)
        hostname = parsed_url.hostname
        scheme = parsed_url.scheme

        # Common ports to scan
        common_ports = {
            "HTTP": 80,
            "HTTPS": 443,
            "FTP": 21,
            "SSH": 22,
            "SMTP": 25,
            "DNS": 53
        }

        for service, port in common_ports.items():
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(5)  # Timeout after 5 seconds
                    result = sock.connect_ex((hostname, port))
                    if result == 0:
                        port_info[service] = "Open"
                    else:
                        port_info[service] = "Closed"
            except Exception as e:
                port_info[service] = f"Error: {str(e)}"
        return port_info

    def combine_urls(self, base: str, path: str) -> str:
        return requests.compat.urljoin(base, path)
