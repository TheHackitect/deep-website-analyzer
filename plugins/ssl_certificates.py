# plugins/ssl_certificates.py
from plugins.base_plugin import BasePlugin
import ssl
import socket
import OpenSSL
from datetime import datetime

class SSLCertificatesPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "SSL/TLS Certificates"

    @property
    def description(self) -> str:
        return "Fetch SSL certificate details, including validity dates, issuer, subject, and SANs."

    def run(self, target: str) -> dict:
        try:
            hostname = target if ":" not in target else target.split(":")[0]
            context = ssl.create_default_context()
            with socket.create_connection((hostname, 443), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert(True)
                    x509 = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_ASN1, cert)
                    issuer = x509.get_issuer().CN
                    subject = x509.get_subject().CN
                    not_before = datetime.strptime(x509.get_notBefore().decode('ascii'), '%Y%m%d%H%M%SZ')
                    not_after = datetime.strptime(x509.get_notAfter().decode('ascii'), '%Y%m%d%H%M%SZ')
                    san = []
                    for i in range(x509.get_extension_count()):
                        ext = x509.get_extension(i)
                        if 'subjectAltName' in str(ext.get_short_name()):
                            san = str(ext).split(", ")
                    return {
                        "Issuer": issuer,
                        "Subject": subject,
                        "Valid From": not_before.strftime("%Y-%m-%d"),
                        "Valid To": not_after.strftime("%Y-%m-%d"),
                        "SANs": san,
                    }
        except Exception as e:
            return {"Error": str(e)}
