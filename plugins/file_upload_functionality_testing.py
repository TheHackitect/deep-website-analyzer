# plugins/file_upload_functionality_testing.py
import requests
from bs4 import BeautifulSoup
import re
import os
from plugins.base_plugin import BasePlugin


class FileUploadFunctionalityTestingPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "File Upload Functionality Testing"

    @property
    def description(self) -> str:
        return "Identify and analyze file upload features for security testing."

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

            # 1. Detect File Upload Forms
            upload_forms = self.detect_file_upload_forms(base_url, response.text)
            results["FileUploadForms"] = upload_forms

            # 2. Analyze Each File Upload Form
            forms_analysis = self.analyze_upload_forms(base_url, upload_forms)
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

    def detect_file_upload_forms(self, base_url: str, html_content: str) -> list:
        upload_forms = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            forms = soup.find_all('form')
            for form in forms:
                file_inputs = form.find_all('input', {'type': 'file'})
                if file_inputs:
                    form_details = {}
                    form_details["Action"] = self.combine_urls(base_url, form.get('action', ''))
                    form_details["Method"] = form.get('method', 'GET').upper()
                    form_details["FileInputNames"] = [input_tag.get('name', '') for input_tag in file_inputs]
                    form_details["Accept"] = [input_tag.get('accept', '') for input_tag in file_inputs]
                    upload_forms.append(form_details)
        except Exception:
            pass
        return upload_forms

    def analyze_upload_forms(self, base_url: str, upload_forms: list) -> list:
        analysis_results = []
        try:
            for form in upload_forms:
                form_result = {}
                form_result["Action"] = form["Action"]
                form_result["Method"] = form["Method"]
                form_result["FileInputNames"] = form["FileInputNames"]
                form_result["AcceptedFileTypes"] = form["Accept"]

                # Attempt to upload a benign file
                test_file_path = self.create_test_file()
                files = {}
                for file_input in form["FileInputNames"]:
                    files[file_input] = ('test.txt', open(test_file_path, 'rb'), 'text/plain')

                try:
                    if form["Method"] == "POST":
                        response = requests.post(form["Action"], files=files, timeout=10)
                    else:
                        response = requests.get(form["Action"], files=files, timeout=10)

                    if response.status_code in [200, 201, 302]:
                        form_result["UploadStatus"] = "Success"
                        # Analyze response for potential vulnerabilities
                        vulnerability = self.analyze_response_for_vulnerabilities(response.text)
                        form_result["PotentialVulnerabilities"] = vulnerability
                    else:
                        form_result["UploadStatus"] = f"Failed with status code {response.status_code}"
                except requests.RequestException as e:
                    form_result["UploadStatus"] = f"Error during upload: {str(e)}"
                finally:
                    # Clean up the opened file
                    for file in files.values():
                        file[1].close()
                    # Remove the test file
                    os.remove(test_file_path)

                analysis_results.append(form_result)
        except Exception:
            pass
        return analysis_results

    def create_test_file(self) -> str:
        file_path = "test.txt"
        with open(file_path, 'w') as f:
            f.write("This is a test file for upload functionality testing.")
        return file_path

    def analyze_response_for_vulnerabilities(self, response_text: str) -> list:
        vulnerabilities = []
        # Simple heuristic checks
        if re.search(r'(uploaded successfully|file uploaded|successfully uploaded)', response_text, re.IGNORECASE):
            vulnerabilities.append("Unrestricted File Upload: Potential success message revealed.")
        if re.search(r'(error|failed|invalid)', response_text, re.IGNORECASE):
            vulnerabilities.append("Error Messages: May reveal server-side validation.")
        # Additional checks can be implemented here
        return vulnerabilities

    def check_url_exists(self, url: str) -> bool:
        try:
            response = requests.head(url, timeout=10)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def combine_urls(self, base: str, path: str) -> str:
        return requests.compat.urljoin(base, path)
