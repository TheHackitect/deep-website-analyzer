# plugins/dns_records.py
from plugins.base_plugin import BasePlugin
import dns.resolver

class DNSRecordsPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "DNS Records"

    @property
    def description(self) -> str:
        return "Retrieve DNS records such as A, AAAA, MX, NS, SOA, TXT, CNAME, PTR, SRV, and DNSSEC records."

    def run(self, target: str) -> dict:
        record_types = ['A', 'AAAA', 'MX', 'NS', 'SOA', 'TXT', 'CNAME', 'PTR', 'SRV', 'DNSKEY']
        results = {}
        resolver = dns.resolver.Resolver()
        for record in record_types:
            try:
                answers = resolver.resolve(target, record)
                results[record] = [str(rdata) for rdata in answers]
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout) as e:
                results[record] = f"Error: {str(e)}"
        return results
