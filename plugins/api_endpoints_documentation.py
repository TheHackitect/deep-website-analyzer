# plugins/api_endpoints_documentation.py
import requests
from bs4 import BeautifulSoup
import re
import time
from plugins.base_plugin import BasePlugin


class APIEndpointsDocumentationPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "API Endpoints and Documentation"

    @property
    def description(self) -> str:
        return (
            "Detect public APIs and endpoints exposed by the website, check for API documentation availability, "
            "test API rate limits."
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

            # 1. Detect API Documentation
            api_docs = self.detect_api_documentation(url, response.text)
            results["APIDocumentation"] = api_docs

            # 2. Discover API Endpoints
            api_endpoints = self.discover_api_endpoints(url, response.text)
            results["APIEndpoints"] = api_endpoints

            # 3. Test API Rate Limits
            rate_limits = self.test_api_rate_limits(api_endpoints)
            results["APIRateLimits"] = rate_limits

        except Exception as e:
            results["Error"] = str(e)

        return results

    def normalize_url(self, target: str) -> str:
        if not target.startswith("http"):
            target = "http://" + target
        return target

    def fetch_response(self, url: str) -> requests.Response:
        try:
            headers = {
                "User-Agent": "DeepWebsiteAnalyzer/1.0"
            }
            response = requests.get(url, headers=headers, timeout=15)
            return response
        except requests.RequestException:
            return None

    def detect_api_documentation(self, base_url: str, html_content: str) -> list:
        possible_paths = [
            "/api-docs",
            "/swagger",
            "/v2/api-docs",
            "/docs",
            "/documentation",
            "/openapi",
            "/api/swagger-ui.html",
            "/swagger-ui/",
            "/docs/api",
        ]
        detected_docs = []
        for path in possible_paths:
            api_doc_url = self.combine_urls(base_url, path)
            if self.check_url_exists(api_doc_url):
                detected_docs.append(api_doc_url)
        return detected_docs

    def discover_api_endpoints(self, base_url: str, html_content: str) -> list:
        api_endpoints = set()
        # Common API path patterns
        api_patterns = [
            r'https?://[^/]+/api/[^\s"\']+',
            r'https?://[^/]+/v[0-9]+/[^\s"\']+',
            r'https?://[^/]+/service/[^\s"\']+',
            r'https?://[^/]+/rest/[^\s"\']+',
            r'https?://[^/]+/graphql/[^\s"\']+',
        ]
        for pattern in api_patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                # Clean URLs by stripping trailing characters
                clean_url = match.rstrip('",\'')
                api_endpoints.add(clean_url)
        return sorted(list(api_endpoints))

    def test_api_rate_limits(self, api_endpoints: list) -> dict:
        rate_limits = {}
        headers = {
            "User-Agent": "DeepWebsiteAnalyzer/1.0"
        }
        for endpoint in api_endpoints[:5]:  # Limit to first 5 endpoints to be respectful
            try:
                # Send 5 rapid requests to infer rate limiting
                responses = []
                for i in range(5):
                    response = requests.get(endpoint, headers=headers, timeout=10)
                    responses.append(response.status_code)
                    time.sleep(1)  # Delay between requests
                # Analyze response codes
                rate_limit_info = self.analyze_rate_limits(responses)
                rate_limits[endpoint] = rate_limit_info
            except requests.RequestException as e:
                rate_limits[endpoint] = {"Error": str(e)}
        return rate_limits

    def analyze_rate_limits(self, status_codes: list) -> dict:
        rate_limit_info = {}
        if 429 in status_codes:
            rate_limit_info["StatusCodes"] = status_codes
            rate_limit_info["RateLimitDetected"] = True
        else:
            rate_limit_info["StatusCodes"] = status_codes
            rate_limit_info["RateLimitDetected"] = False
        return rate_limit_info

    def check_url_exists(self, url: str) -> bool:
        try:
            response = requests.head(url, timeout=10)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def combine_urls(self, base: str, path: str) -> str:
        return requests.compat.urljoin(base, path)
