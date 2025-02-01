# plugins/cdn_hosting_provider.py
from plugins.base_plugin import BasePlugin
import requests
from bs4 import BeautifulSoup
import re
import dns.resolver

class CDNHostingProviderPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "CDN and Hosting Provider"

    @property
    def description(self) -> str:
        return "Determine the use of CDN services and details about the hosting provider, including CDN edge locations and third-party CDN resources."

    @property
    def required_api_keys(self) -> list:
        return []  # No API keys required

    def run(self, target: str) -> dict:
        results = {}
        try:
            if not target.startswith(("http://", "https://")):
                target = "http://" + target  # Default to HTTP if scheme not provided
            parsed_url = requests.utils.urlparse(target)
            hostname = parsed_url.hostname

            # 1. Determine CDN Usage
            cdn_info = self.detect_cdn(hostname)
            results["CDN Usage"] = cdn_info

            # 2. Hosting Provider Details
            hosting_info = self.get_hosting_provider(hostname)
            results["Hosting Provider"] = hosting_info

        except Exception as e:
            results["Error"] = str(e)

        return results

    def detect_cdn(self, hostname):
        cdn_info = {}
        try:
            response = requests.get(f"http://{hostname}", timeout=10)
            headers = response.headers

            # Common CDN headers
            cdn_signatures = {
                "cloudflare": "cloudflare",
                "akamai": "akamai",
                "incapsula": "incapsula",
                "stackpath": "stackpath",
                "cdn77": "cdn77",
                "fastly": "fastly",
                "azure": "azure",
                "amazon": "amazon",
                "stackpath": "stackpath",
                "google": "google",
                "sucuri": "sucuri",
            }

            detected_cdn = []
            for cdn, signature in cdn_signatures.items():
                if signature in headers.get('Server', '').lower() or signature in headers.get('X-CDN', '').lower():
                    detected_cdn.append(cdn.capitalize())

            # Additionally, check for CDN-specific URLs in HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            scripts = soup.find_all('script', src=True)
            stylesheets = soup.find_all('link', href=True)
            cdn_domains = set()
            for tag in scripts + stylesheets:
                src = tag.get('src') or tag.get('href')
                for cdn in cdn_signatures.keys():
                    if cdn in src:
                        cdn_domains.add(cdn.capitalize())

            if cdn_domains:
                detected_cdn.extend(list(cdn_domains))

            detected_cdn = list(set(detected_cdn))  # Remove duplicates

            if detected_cdn:
                cdn_info["CDN Providers"] = detected_cdn
            else:
                cdn_info["CDN Providers"] = "No CDN detected."

        except Exception as e:
            cdn_info["Error"] = str(e)
        return cdn_info

    def get_hosting_provider(self, hostname):
        hosting_info = {}
        try:
            # Perform DNS lookup to get IP
            resolver = dns.resolver.Resolver()
            answers = resolver.resolve(hostname, 'A')
            ip_address = answers[0].to_text()
            hosting_info["IP Address"] = ip_address

            # Perform reverse DNS lookup
            reverse_dns = resolver.resolve_address(ip_address)
            reverse_hostname = reverse_dns[0].to_text()
            hosting_info["Reverse DNS"] = reverse_hostname

            # Perform WHOIS lookup (requires 'python-whois' package)
            try:
                import whois
                domain_info = whois.whois(hostname)
                hosting_info["Registrar"] = domain_info.registrar
                hosting_info["Creation Date"] = domain_info.creation_date
                hosting_info["Expiration Date"] = domain_info.expiration_date
            except ImportError:
                hosting_info["Registrar"] = "whois package not installed."
            except Exception as e:
                hosting_info["Registrar"] = f"WHOIS lookup failed: {str(e)}"

        except Exception as e:
            hosting_info["Error"] = str(e)
        return hosting_info
