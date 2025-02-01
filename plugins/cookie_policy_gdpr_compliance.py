# plugins/cookie_policy_gdpr_compliance.py
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
from plugins.base_plugin import BasePlugin


class CookiePolicyGDPRCompliancePlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Cookie Policy and GDPR Compliance"

    @property
    def description(self) -> str:
        return "Determine if the site complies with GDPR regarding cookies and data privacy."

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
            response = self.fetch_response(base_url)
            if not response:
                results["Error"] = "Failed to retrieve website content."
                return results

            # 1. Detect Cookie Consent Banners
            cookie_banners = self.detect_cookie_banners(base_url, response.text)
            results["CookieConsentBanners"] = cookie_banners

            # 2. Analyze Privacy Policy
            privacy_policy = self.analyze_privacy_policy(base_url, response.text)
            results["PrivacyPolicy"] = privacy_policy

            # 3. Inspect Cookie Attributes
            cookies_info = self.inspect_cookie_attributes(response.cookies)
            results["CookieAttributes"] = cookies_info

            # 4. Data Privacy Compliance Indicators
            data_privacy = self.check_data_privacy_compliance(base_url, response.text)
            results["DataPrivacyCompliance"] = data_privacy

        except Exception as e:
            results["Error"] = str(e)

        return results

    def normalize_url(self, target: str) -> str:
        if not target.startswith(("http://", "https://")):
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

    def detect_cookie_banners(self, base_url: str, html_content: str) -> dict:
        banners = {}
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            # Look for common cookie consent elements
            banner_keywords = ['cookie', 'cookies', 'GDPR', 'consent', 'privacy']
            consent_elements = []

            # Search for divs or sections with relevant keywords
            for tag in soup.find_all(['div', 'section']):
                text = tag.get_text(separator=' ').lower()
                if any(keyword in text for keyword in banner_keywords):
                    consent_elements.append(tag.prettify())

            # Search for scripts related to cookie consent
            scripts = soup.find_all('script')
            consent_scripts = []
            for script in scripts:
                if script.get('src') and re.search(r'cookieconsent|consent', script.get('src'), re.IGNORECASE):
                    consent_scripts.append(script.get('src'))

            banners["ConsentElements"] = consent_elements
            banners["ConsentScripts"] = consent_scripts

        except Exception:
            pass
        return banners

    def analyze_privacy_policy(self, base_url: str, html_content: str) -> dict:
        privacy_info = {}
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            # Look for links to privacy policy
            links = soup.find_all('a', href=True)
            privacy_links = []
            for link in links:
                href = link['href']
                if re.search(r'privacy', href, re.IGNORECASE):
                    full_url = urljoin(base_url, href)
                    privacy_links.append(full_url)

            if not privacy_links:
                privacy_info["PrivacyPolicyExists"] = False
                privacy_info["PrivacyPolicyURL"] = "Not Found"
                privacy_info["ComplianceIndicators"] = []
                return privacy_info

            # Assume the first privacy policy link is the relevant one
            privacy_url = privacy_links[0]
            privacy_response = requests.get(privacy_url, timeout=10)
            if privacy_response.status_code == 200:
                privacy_text = privacy_response.text.lower()
                compliance_indicators = []
                gdpr_keywords = ['gdpr', 'data protection', 'consent', 'data controller', 'rights', 'eraser', 'rectification']
                for keyword in gdpr_keywords:
                    if keyword in privacy_text:
                        compliance_indicators.append(keyword.title())

                privacy_info["PrivacyPolicyExists"] = True
                privacy_info["PrivacyPolicyURL"] = privacy_url
                privacy_info["ComplianceIndicators"] = compliance_indicators
            else:
                privacy_info["PrivacyPolicyExists"] = False
                privacy_info["PrivacyPolicyURL"] = privacy_url
                privacy_info["ComplianceIndicators"] = []

        except Exception:
            pass
        return privacy_info

    def inspect_cookie_attributes(self, cookies: requests.cookies.RequestsCookieJar) -> dict:
        cookie_details = {}
        try:
            for cookie in cookies:
                details = {
                    "Value": cookie.value,
                    "Domain": cookie.domain,
                    "Path": cookie.path,
                    "Secure": cookie.secure,
                    "HttpOnly": cookie.has_nonstandard_attr('HttpOnly'),
                    "SameSite": cookie._rest.get('samesite')
                }
                cookie_details[cookie.name] = details
        except Exception:
            pass
        return cookie_details

    def check_data_privacy_compliance(self, base_url: str, html_content: str) -> dict:
        compliance = {}
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            text = soup.get_text(separator=' ').lower()

            # Check for Data Protection Officer (DPO) contact
            dpo_present = bool(re.search(r'data protection officer|dpo', text))
            compliance["DataProtectionOfficer"] = dpo_present

            # Check for data access and deletion mechanisms
            access_present = bool(re.search(r'data access request|right to access', text))
            deletion_present = bool(re.search(r'data deletion request|right to be forgotten', text))
            compliance["DataAccessMechanism"] = access_present
            compliance["DataDeletionMechanism"] = deletion_present

        except Exception:
            pass
        return compliance
