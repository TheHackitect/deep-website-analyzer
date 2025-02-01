# plugins/email_authentication_records.py
import dns.resolver
import socket
from plugins.base_plugin import BasePlugin


class EmailAuthenticationRecordsPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Email and Authentication Records"

    @property
    def description(self) -> str:
        return (
            "Retrieve and analyze SPF, DKIM, and DMARC records, email server configurations, and check for email server vulnerabilities."
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
            # 1. Retrieve SPF Record
            spf_record = self.get_spf_record(domain)
            results["SPF"] = spf_record

            # 2. Retrieve DKIM Records
            dkim_records = self.get_dkim_records(domain)
            results["DKIM"] = dkim_records

            # 3. Retrieve DMARC Record
            dmarc_record = self.get_dmarc_record(domain)
            results["DMARC"] = dmarc_record

            # 4. Email Server Configurations
            mx_records = self.get_mx_records(domain)
            results["MXRecords"] = mx_records

            # 5. Email Server Vulnerability Checks
            vulnerabilities = self.check_email_server_vulnerabilities(mx_records)
            results["Vulnerabilities"] = vulnerabilities

        except Exception as e:
            results["Error"] = str(e)

        return results

    def extract_domain(self, target: str) -> str:
        if target.startswith("http"):
            target = target.split("://")[1]
        domain = target.split("/")[0]
        return domain

    def get_spf_record(self, domain: str) -> str:
        try:
            answers = dns.resolver.resolve(domain, 'TXT')
            for rdata in answers:
                for txt_string in rdata.strings:
                    txt_decoded = txt_string.decode('utf-8')
                    if txt_decoded.startswith("v=spf1"):
                        return txt_decoded
            return "No SPF record found."
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            return "No SPF record found."
        except Exception as e:
            return f"Error retrieving SPF record: {str(e)}"

    def get_dkim_records(self, domain: str) -> list:
        # DKIM selectors can vary. Common selectors are 'default', 'selector1', etc.
        selectors = ['default', 'selector1']
        records = {}
        for selector in selectors:
            dkim_domain = f"{selector}._domainkey.{domain}"
            try:
                answers = dns.resolver.resolve(dkim_domain, 'TXT')
                for rdata in answers:
                    for txt_string in rdata.strings:
                        txt_decoded = txt_string.decode('utf-8')
                        if txt_decoded.startswith("v=DKIM1"):
                            records[selector] = txt_decoded
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
                records[selector] = "No DKIM record found."
            except Exception as e:
                records[selector] = f"Error retrieving DKIM record: {str(e)}"
        return records

    def get_dmarc_record(self, domain: str) -> str:
        dmarc_domain = f"_dmarc.{domain}"
        try:
            answers = dns.resolver.resolve(dmarc_domain, 'TXT')
            for rdata in answers:
                for txt_string in rdata.strings:
                    txt_decoded = txt_string.decode('utf-8')
                    if txt_decoded.startswith("v=DMARC1"):
                        return txt_decoded
            return "No DMARC record found."
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            return "No DMARC record found."
        except Exception as e:
            return f"Error retrieving DMARC record: {str(e)}"

    def get_mx_records(self, domain: str) -> list:
        try:
            answers = dns.resolver.resolve(domain, 'MX')
            mx_records = []
            for rdata in answers:
                mx_records.append({
                    "preference": rdata.preference,
                    "exchange": rdata.exchange.to_text()
                })
            return mx_records
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            return []
        except Exception as e:
            return [f"Error retrieving MX records: {str(e)}"]

    def check_email_server_vulnerabilities(self, mx_records: list) -> dict:
        vulnerabilities = {}
        for mx in mx_records:
            exchange = mx.get("exchange", "")
            if exchange.endswith('.'):
                exchange = exchange[:-1]  # Remove trailing dot
            try:
                # Simple check: Can we establish a connection to SMTP port 25?
                smtp_port = 25
                sock = socket.create_connection((exchange, smtp_port), timeout=5)
                sock.close()
                vulnerabilities[exchange] = "SMTP Port 25 is open."
            except socket.timeout:
                vulnerabilities[exchange] = "SMTP Port 25 connection timed out."
            except socket.error as e:
                vulnerabilities[exchange] = f"SMTP Port 25 connection failed: {str(e)}"
            except Exception as e:
                vulnerabilities[exchange] = f"Error checking SMTP port: {str(e)}"
        return vulnerabilities
