# plugins/cookies_session_data_analysis.py
import requests
from bs4 import BeautifulSoup
import re
from collections import Counter
import math
from plugins.base_plugin import BasePlugin


class CookiesSessionDataAnalysisPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Cookies and Session Data Analysis"

    @property
    def description(self) -> str:
        return (
            "Retrieve and analyze cookies set by the website, session IDs, session management, "
            "entropy of session IDs, session fixation vulnerabilities, and client-side storage."
        )

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

            # 1. Retrieve Cookies
            cookies = self.get_cookies(response)
            results["Cookies"] = cookies

            # 2. Analyze Session IDs
            session_analysis = self.analyze_session_ids(cookies)
            results["SessionIDAnalysis"] = session_analysis

            # 3. Client-Side Storage Analysis
            client_storage = self.analyze_client_side_storage(response.text)
            results["ClientSideStorage"] = client_storage

            # 4. Session Fixation Vulnerabilities
            # Note: Detecting session fixation requires interaction with login forms, which is beyond this plugin's scope.
            # Here, we'll check if session cookies have the 'HttpOnly' and 'Secure' flags set.
            session_vulnerabilities = self.check_session_vulnerabilities(cookies)
            results["SessionFixationVulnerabilities"] = session_vulnerabilities

        except Exception as e:
            results["Error"] = str(e)

        return results

    def normalize_url(self, target: str) -> str:
        if not target.startswith("http"):
            target = "http://" + target
        return target

    def fetch_response(self, url: str) -> requests.Response:
        try:
            response = requests.get(url, timeout=15)
            return response
        except requests.RequestException:
            return None

    def get_cookies(self, response: requests.Response) -> dict:
        cookies = {}
        for cookie in response.cookies:
            cookies[cookie.name] = {
                "value": cookie.value,
                "domain": cookie.domain,
                "path": cookie.path,
                "secure": cookie.secure,
                "httpOnly": cookie.has_nonstandard_attr('HttpOnly'),
                "expires": cookie.expires,
                "samesite": cookie._rest.get('samesite')
            }
        return cookies

    def analyze_session_ids(self, cookies: dict) -> dict:
        session_cookies = {}
        for name, attrs in cookies.items():
            if re.search(r'session|sid|auth', name, re.IGNORECASE):
                entropy = self.calculate_entropy(attrs['value'])
                session_cookies[name] = {
                    "value_length": len(attrs['value']),
                    "entropy": entropy
                }
        return session_cookies

    def calculate_entropy(self, data: str) -> float:
        if not data:
            return 0.0
        counter = Counter(data)
        probabilities = [count / len(data) for count in counter.values()]
        entropy = -sum(p * math.log2(p) for p in probabilities)
        return round(entropy, 2)

    def analyze_client_side_storage(self, html: str) -> dict:
        storage = {
            "localStorage": False,
            "sessionStorage": False,
            "cookies_via_js": False
        }
        try:
            soup = BeautifulSoup(html, 'html.parser')
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    if 'localStorage' in script.string:
                        storage["localStorage"] = True
                    if 'sessionStorage' in script.string:
                        storage["sessionStorage"] = True
                    if re.search(r'document\.cookie', script.string):
                        storage["cookies_via_js"] = True
        except Exception:
            pass
        return storage

    def check_session_vulnerabilities(self, cookies: dict) -> dict:
        vulnerabilities = {}
        for name, attrs in cookies.items():
            if re.search(r'session|sid|auth', name, re.IGNORECASE):
                issues = []
                if not attrs['HttpOnly']:
                    issues.append("HttpOnly flag not set.")
                if not attrs['secure']:
                    issues.append("Secure flag not set.")
                if issues:
                    vulnerabilities[name] = issues
        return vulnerabilities
