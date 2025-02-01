# plugins/waf_detection.py
import requests
from bs4 import BeautifulSoup
import re
from plugins.base_plugin import BasePlugin


class WAFDetectionPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Web Application Firewall (WAF) Detection"

    @property
    def description(self) -> str:
        return "Detect WAF services protecting the site."

    @property
    def data_format(self) -> str:
        return "json"

    @property
    def required_api_keys(self) -> list:
        return []

    def run(self, target: str) -> dict:
        results = {}
        try:
            url = self.normalize_url(target)
            response = self.fetch_response(url)
            if not response:
                results["Error"] = "Failed to retrieve website response."
                return results

            wafs = self.detect_wafs(response)
            results["DetectedWAFs"] = wafs

        except Exception as e:
            results["Error"] = str(e)

        return results

    def normalize_url(self, target: str) -> str:
        if not target.startswith("http"):
            target = "http://" + target
        return target

    def fetch_response(self, url: str) -> requests.Response:
        try:
            # Send a request with a known bad parameter to trigger WAF if present
            bad_url = f"{url}?redirect=<script>alert('waf')</script>"
            headers = {
                "User-Agent": "DeepWebsiteAnalyzer/1.0"
            }
            response = requests.get(bad_url, headers=headers, timeout=15)
            return response
        except requests.RequestException:
            return None

    def detect_wafs(self, response: requests.Response) -> list:
        detected_wafs = []
        # Define known WAF signatures
        waf_signatures = {
            "Cloudflare": {
                "headers": ["Server"],
                "patterns": [r"cloudflare"],
                "error_patterns": [r"Cloudflare"]
            },
            "AWS WAF": {
                "headers": ["X-Amzn-Trace-Id", "X-Cache"],
                "patterns": [r"awswaf"],
                "error_patterns": [r"AWS WAF"]
            },
            "Sucuri": {
                "headers": ["Server"],
                "patterns": [r"sucuri"],
                "error_patterns": [r"Sucuri"]
            },
            "Incapsula": {
                "headers": ["X-CDN"],
                "patterns": [r"Incapsula"],
                "error_patterns": [r"Incapsula"]
            },
            "ModSecurity": {
                "headers": ["Server"],
                "patterns": [r"Mod_Security"],
                "error_patterns": [r"Mod_Security"]
            },
            "Barracuda": {
                "headers": ["Server"],
                "patterns": [r"Barracuda"],
                "error_patterns": [r"Barracuda"]
            },
            "F5 BIG-IP": {
                "headers": ["X-F5-"],
                "patterns": [r"F5"],
                "error_patterns": [r"F5 BIG-IP"]
            },
            "Fortinet": {
                "headers": ["Server"],
                "patterns": [r"FortiWeb"],
                "error_patterns": [r"FortiWeb"]
            },
            "Akamai": {
                "headers": ["Server"],
                "patterns": [r"Akamai"],
                "error_patterns": [r"Akamai"]
            }
            # Add more WAF signatures as needed
        }

        # Check headers for WAF signatures
        for waf, signature in waf_signatures.items():
            # Header Analysis
            for header in signature["headers"]:
                header_value = response.headers.get(header, "")
                if any(re.search(pattern, header_value, re.IGNORECASE) for pattern in signature["patterns"]):
                    if waf not in detected_wafs:
                        detected_wafs.append(waf)
            # Error Page Analysis
            if response.status_code in [403, 406, 503]:
                soup = BeautifulSoup(response.text, 'html.parser')
                page_text = soup.get_text()
                for pattern in signature["error_patterns"]:
                    if re.search(pattern, page_text, re.IGNORECASE):
                        if waf not in detected_wafs:
                            detected_wafs.append(waf)

        return detected_wafs
