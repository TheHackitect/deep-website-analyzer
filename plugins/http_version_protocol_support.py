# plugins/http_version_protocol_support.py
import httpx
import requests
from bs4 import BeautifulSoup
import re
from plugins.base_plugin import BasePlugin


class HTTPVersionProtocolSupportPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "HTTP Version and Protocol Support"

    @property
    def description(self) -> str:
        return (
            "Determine the HTTP protocol versions supported by the server (e.g., HTTP/1.1, HTTP/2, HTTP/3), "
            "check for HTTP compression support, pipelining support, and HTTP methods allowed."
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
            base_url = self.normalize_url(target)

            # 1. Detect Supported HTTP Versions
            http_versions = self.detect_http_versions(base_url)
            results["SupportedHTTPVersions"] = http_versions

            # 2. Check HTTP Compression Support
            compression = self.check_http_compression(base_url)
            results["HTTPCompression"] = compression

            # 3. Check HTTP Pipelining Support
            pipelining = self.check_http_pipelining(base_url)
            results["HTTPPipelining"] = pipelining

            # 4. Identify Allowed HTTP Methods
            allowed_methods = self.identify_allowed_methods(base_url)
            results["AllowedHTTPMethods"] = allowed_methods

        except Exception as e:
            results["Error"] = str(e)

        return results

    def normalize_url(self, target: str) -> str:
        if not target.startswith(("http://", "https://")):
            target = "http://" + target
        return target

    def detect_http_versions(self, url: str) -> list:
        supported_versions = []
        try:
            # Using httpx to detect HTTP/1.1 and HTTP/2
            with httpx.Client(http_versions=[httpx.HTTPVersion.HTTP_1_1, httpx.HTTPVersion.HTTP_2],
                              timeout=10,
                              headers={"User-Agent": "DeepWebsiteAnalyzer/1.0"}) as client:
                response = client.get(url)
                if response.http_version == httpx.HTTPVersion.HTTP_1_1:
                    supported_versions.append("HTTP/1.1")
                elif response.http_version == httpx.HTTPVersion.HTTP_2:
                    supported_versions.append("HTTP/2")
                # HTTP/3 detection is not straightforward without QUIC support
                # Can be inferred via server announcements or TLS handshake, which is beyond this scope
        except Exception:
            pass
        return supported_versions

    def check_http_compression(self, url: str) -> list:
        compression_methods = []
        try:
            response = requests.get(url, headers={"User-Agent": "DeepWebsiteAnalyzer/1.0",
                                                 "Accept-Encoding": "gzip, deflate, br"}, timeout=10)
            encoding = response.headers.get("Content-Encoding", "")
            if encoding:
                methods = encoding.split(",")
                compression_methods = [method.strip() for method in methods]
        except Exception:
            pass
        return compression_methods

    def check_http_pipelining(self, url: str) -> bool:
        # HTTP pipelining is deprecated and rarely supported. This method provides a basic check.
        try:
            with httpx.Client(http_versions=[httpx.HTTPVersion.HTTP_1_1],
                              timeout=10,
                              headers={"User-Agent": "DeepWebsiteAnalyzer/1.0"}) as client:
                # Send two HEAD requests in quick succession
                response1 = client.head(url)
                response2 = client.head(url)
                # If both responses are received without errors, assume pipelining might be supported
                return response1.status_code == 200 and response2.status_code == 200
        except Exception:
            return False

    def identify_allowed_methods(self, url: str) -> list:
        allowed_methods = []
        try:
            response = requests.options(url, headers={"User-Agent": "DeepWebsiteAnalyzer/1.0"}, timeout=10)
            allow_header = response.headers.get("Allow", "")
            if allow_header:
                methods = [method.strip() for method in allow_header.split(",")]
                allowed_methods = methods
        except Exception:
            pass
        return allowed_methods
