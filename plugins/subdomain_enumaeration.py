# plugins/subdomain_enumeration.py
import requests
from bs4 import BeautifulSoup
import dns.resolver
import re
from plugins.base_plugin import BasePlugin


class SubdomainEnumerationPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Subdomain Enumeration"

    @property
    def description(self) -> str:
        return (
            "List subdomains associated with the domain, including subdomains discovered via certificate transparency logs."
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
            domain = self.extract_domain(target)
            # 1. Subdomains from Certificate Transparency Logs (crt.sh)
            crt_subdomains = self.get_subdomains_crtsh(domain)
            results["CertificateTransparencyLogs"] = crt_subdomains

            # 2. Subdomains from DNS Brute-Forcing
            dns_subdomains = self.get_subdomains_dns(domain)
            results["DNSBruteForce"] = dns_subdomains

            # 3. Combine and deduplicate subdomains
            all_subdomains = list(set(crt_subdomains + dns_subdomains))
            results["AllSubdomains"] = all_subdomains

        except Exception as e:
            results["Error"] = str(e)

        return results

    def extract_domain(self, target: str) -> str:
        if target.startswith("http"):
            target = target.split("://")[1]
        domain = target.split("/")[0]
        return domain

    def get_subdomains_crtsh(self, domain: str) -> list:
        subdomains = []
        try:
            url = f"https://crt.sh/?q=%25.{domain}&output=json"
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                data = response.json()
                for entry in data:
                    name = entry.get("name_value")
                    if name:
                        # crt.sh can return multiple subdomains in a single name_value separated by newlines
                        for sub in name.split("\n"):
                            if sub.endswith(domain) and sub not in subdomains:
                                subdomains.append(sub.strip())
            else:
                pass  # Non-200 response
        except Exception as e:
            pass  # Handle exceptions silently or log if needed
        return subdomains

    def get_subdomains_dns(self, domain: str) -> list:
        subdomains = []
        try:
            # A simple wordlist for DNS brute-forcing
            wordlist = [
                "www", "mail", "ftp", "dev", "test", "api", "blog", "shop", "webmail",
                "smtp", "secure", "server", "ns1", "ns2", "vpn", "mobile", "m",
                "beta", "demo", "portal", "intranet", "support", "news", "images",
                "static", "downloads", "forum", "mail2", "mail1"
            ]
            resolver = dns.resolver.Resolver()
            for sub in wordlist:
                fqdn = f"{sub}.{domain}"
                try:
                    answers = resolver.resolve(fqdn, 'A')
                    if answers:
                        subdomains.append(fqdn)
                except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.Timeout):
                    continue  # Subdomain does not exist
                except Exception:
                    continue  # Other exceptions
        except Exception as e:
            pass  # Handle exceptions silently or log if needed
        return subdomains
