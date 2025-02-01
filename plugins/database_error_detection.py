# plugins/database_error_detection.py
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
from plugins.base_plugin import BasePlugin


class DatabaseErrorDetectionPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Database Error Detection"

    @property
    def description(self) -> str:
        return "Look for database error messages that could reveal database structure or vulnerabilities."

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

            # 1. Detect Forms that may interact with databases
            forms = self.detect_forms(base_url, response.text)
            results["Forms"] = forms

            # 2. Test Forms for Database Errors
            forms_analysis = self.test_forms_for_db_errors(base_url, forms)
            results["FormsAnalysis"] = forms_analysis

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

    def detect_forms(self, base_url: str, html_content: str) -> list:
        forms = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            for form in soup.find_all('form'):
                form_details = {}
                form_details["Action"] = urljoin(base_url, form.get('action', ''))
                form_details["Method"] = form.get('method', 'GET').upper()
                form_details["Inputs"] = [input_tag.get('name', '') for input_tag in form.find_all('input') if input_tag.get('name')]
                forms.append(form_details)
        except Exception:
            pass
        return forms

    def test_forms_for_db_errors(self, base_url: str, forms: list) -> list:
        analysis_results = []
        try:
            sql_error_patterns = [
                re.compile(r'syntax error.*?MySQL', re.IGNORECASE),
                re.compile(r'unclosed quotation mark after the character string', re.IGNORECASE),
                re.compile(r'You have an error in your SQL syntax', re.IGNORECASE),
                re.compile(r'Warning: mysql_', re.IGNORECASE),
                re.compile(r'pg_query():', re.IGNORECASE),
                re.compile(r'ORA-\d+', re.IGNORECASE),
                re.compile(r'SQLServer', re.IGNORECASE)
            ]

            # SQL Injection payload
            sql_payload = "' OR '1'='1"

            for form in forms:
                form_result = {}
                form_result["Action"] = form["Action"]
                form_result["Method"] = form["Method"]
                form_result["Inputs"] = form["Inputs"]
                form_result["VulnerableFields"] = []

                # Prepare payload
                data = {}
                for input_name in form["Inputs"]:
                    data[input_name] = sql_payload

                try:
                    if form["Method"] == "POST":
                        response = requests.post(form["Action"], data=data, timeout=10)
                    else:
                        response = requests.get(form["Action"], params=data, timeout=10)

                    if response:
                        for pattern in sql_error_patterns:
                            if pattern.search(response.text):
                                form_result["VulnerableFields"].append(input_name)
                                break
                        if not form_result["VulnerableFields"]:
                            form_result["VulnerableFields"] = "No database errors detected."
                except requests.RequestException as e:
                    form_result["Error"] = f"Error during form testing: {str(e)}"

                analysis_results.append(form_result)
        except Exception:
            pass
        return analysis_results
