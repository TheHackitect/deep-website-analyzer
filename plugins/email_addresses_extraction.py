# plugins/email_addresses_extraction.py
import requests
from bs4 import BeautifulSoup
import re
from plugins.base_plugin import BasePlugin


class EmailAddressesExtractionPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Email Addresses Extraction"

    @property
    def description(self) -> str:
        return "Find email addresses present on the website."

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
            content = self.fetch_content(url)
            if not content:
                results["Error"] = "Failed to retrieve website content."
                return results

            emails = self.extract_emails(content)
            results["EmailAddresses"] = emails

        except Exception as e:
            results["Error"] = str(e)

        return results

    def normalize_url(self, target: str) -> str:
        if not target.startswith("http"):
            target = "http://" + target
        return target

    def fetch_content(self, url: str) -> str:
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Remove scripts and styles
                for script_or_style in soup(['script', 'style']):
                    script_or_style.decompose()
                text = soup.get_text(separator=' ')
                return text
            else:
                return ""
        except requests.RequestException:
            return ""

    def extract_emails(self, text: str) -> list:
        # Regex pattern for email extraction
        email_pattern = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
        emails = re.findall(email_pattern, text)
        # Deduplicate and sort
        unique_emails = sorted(list(set(emails)))
        return unique_emails
