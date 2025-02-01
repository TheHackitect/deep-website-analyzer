# plugins/captcha_form_anti_automation.py
import requests
from bs4 import BeautifulSoup
import re
from plugins.base_plugin import BasePlugin


class CAPTCHAFormAntiAutomationPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "CAPTCHA and Form Anti-Automation Techniques"

    @property
    def description(self) -> str:
        return (
            "Determine if the site uses CAPTCHA mechanisms, identify anti-automation techniques like hidden fields or time-based tokens."
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

            # 1. Detect CAPTCHA Mechanisms
            captcha_info = self.detect_captcha(response.text)
            results["CAPTCHAMechanisms"] = captcha_info

            # 2. Detect Anti-Automation Techniques in Forms
            forms_info = self.analyze_forms(response.text)
            results["AntiAutomationTechniques"] = forms_info

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

    def detect_captcha(self, html: str) -> dict:
        captcha_detected = False
        captcha_methods = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            # Check for reCAPTCHA
            if soup.find('div', class_=re.compile(r'recaptcha', re.IGNORECASE)):
                captcha_detected = True
                captcha_methods.append("reCAPTCHA")
            # Check for hCaptcha
            if soup.find('div', class_=re.compile(r'hcaptcha', re.IGNORECASE)):
                captcha_detected = True
                captcha_methods.append("hCAPTCHA")
            # Check for CAPTCHA in scripts
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    if 'captcha' in script.string.lower():
                        captcha_detected = True
                        captcha_methods.append("JavaScript-based CAPTCHA")
            # Check for image-based CAPTCHAs
            img_captchas = soup.find_all('img', alt=re.compile(r'captcha', re.IGNORECASE))
            if img_captchas:
                captcha_detected = True
                captcha_methods.append("Image-based CAPTCHA")
        except Exception:
            pass
        return {
            "CaptchaDetected": captcha_detected,
            "CaptchaMethods": list(set(captcha_methods))  # Remove duplicates
        }

    def analyze_forms(self, html: str) -> dict:
        anti_automation = {
            "Forms": []
        }
        try:
            soup = BeautifulSoup(html, 'html.parser')
            forms = soup.find_all('form')
            for form in forms:
                form_info = {}
                form_info["Action"] = form.get('action', '')
                form_info["Method"] = form.get('method', 'GET').upper()
                # Detect hidden fields
                hidden_fields = form.find_all('input', type='hidden')
                form_info["HiddenFields"] = [field.get('name', '') for field in hidden_fields]
                # Detect CSRF tokens (common naming conventions)
                csrf_tokens = [field.get('name', '') for field in hidden_fields if re.search(r'csrf', field.get('name', ''), re.IGNORECASE)]
                form_info["CSRF_Tokens"] = csrf_tokens
                # Detect time-based tokens (simple heuristic: fields containing 'time' or 'timestamp')
                time_tokens = [field.get('name', '') for field in hidden_fields if re.search(r'time|timestamp', field.get('name', ''), re.IGNORECASE)]
                form_info["TimeBasedTokens"] = time_tokens
                # Detect JavaScript-based validation
                if form.find_all('script'):
                    form_info["JavaScriptValidation"] = True
                else:
                    form_info["JavaScriptValidation"] = False
                anti_automation["Forms"].append(form_info)
        except Exception:
            pass
        return anti_automation
