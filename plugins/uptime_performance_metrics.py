# plugins/uptime_performance_metrics.py
import requests
import time
from bs4 import BeautifulSoup
from plugins.base_plugin import BasePlugin


class UptimePerformanceMetricsPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Uptime and Performance Metrics"

    @property
    def description(self) -> str:
        return (
            "Check site uptime and availability, measure resource loading times, application performance metrics, "
            "load times for critical resources, response header timing analysis, and evaluate performance optimization techniques."
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
            # 1. Uptime and Availability
            uptime = self.check_uptime(url)
            results["Uptime"] = uptime

            # 2. Response Time
            response_time = self.measure_response_time(url)
            results["ResponseTime_ms"] = response_time

            # 3. Response Headers
            headers = self.get_response_headers(url)
            results["ResponseHeaders"] = headers

            # 4. Critical Resources Load Time
            critical_resources = self.get_critical_resources_load_time(url)
            results["CriticalResourcesLoadTime_ms"] = critical_resources

            # 5. Performance Optimization Suggestions
            suggestions = self.get_performance_suggestions(headers)
            results["PerformanceSuggestions"] = suggestions

        except Exception as e:
            results["Error"] = str(e)

        return results

    def normalize_url(self, target: str) -> str:
        if not target.startswith("http"):
            target = "http://" + target
        return target

    def check_uptime(self, url: str) -> bool:
        try:
            response = requests.head(url, timeout=10)
            return response.status_code < 400
        except requests.RequestException:
            return False

    def measure_response_time(self, url: str) -> float:
        try:
            start_time = time.time()
            response = requests.get(url, timeout=10)
            end_time = time.time()
            return round((end_time - start_time) * 1000, 2)  # in milliseconds
        except requests.RequestException:
            return -1  # Indicates failure

    def get_response_headers(self, url: str) -> dict:
        try:
            response = requests.get(url, timeout=10)
            return dict(response.headers)
        except requests.RequestException:
            return {}

    def get_critical_resources_load_time(self, url: str) -> dict:
        load_times = {}
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            resources = []
            # Find CSS files
            for link in soup.find_all('link', rel='stylesheet'):
                href = link.get('href')
                if href:
                    full_url = self.make_absolute_url(url, href)
                    resources.append(full_url)
            # Find JS files
            for script in soup.find_all('script', src=True):
                src = script.get('src')
                if src:
                    full_url = self.make_absolute_url(url, src)
                    resources.append(full_url)
            # Measure load times
            for resource in resources:
                try:
                    start_time = time.time()
                    res = requests.get(resource, timeout=10)
                    end_time = time.time()
                    load_time = round((end_time - start_time) * 1000, 2)
                    load_times[resource] = load_time
                except requests.RequestException:
                    load_times[resource] = -1  # Indicates failure
            return load_times
        except requests.RequestException:
            return load_times

    def make_absolute_url(self, base_url: str, link: str) -> str:
        if link.startswith("http"):
            return link
        elif link.startswith("//"):
            return "http:" + link
        else:
            return requests.compat.urljoin(base_url, link)

    def get_performance_suggestions(self, headers: dict) -> list:
        suggestions = []
        # Example: Check for gzip compression
        if 'Content-Encoding' in headers:
            if 'gzip' not in headers['Content-Encoding']:
                suggestions.append("Enable GZIP compression to reduce response size.")
        else:
            suggestions.append("Enable GZIP compression to reduce response size.")

        # Example: Check for Cache-Control
        if 'Cache-Control' not in headers:
            suggestions.append("Implement Cache-Control headers to leverage browser caching.")

        # Example: Check for Content Security Policy
        if 'Content-Security-Policy' not in headers:
            suggestions.append("Implement Content Security Policy (CSP) to enhance security.")

        return suggestions
