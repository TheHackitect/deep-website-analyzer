# plugins/historical_data_archive.py
import requests
import json
import dns.resolver
import whois
from datetime import datetime
from plugins.base_plugin import BasePlugin


class HistoricalDataArchivePlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Historical Data and Archive"

    @property
    def description(self) -> str:
        return (
            "Access archive snapshots (e.g., via Wayback Machine), historical DNS records, and domain history."
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
            # Validate and normalize the target
            if not target.startswith("http"):
                target = "http://" + target

            # 1. Wayback Machine Snapshots
            snapshots = self.get_wayback_snapshots(target)
            results["WaybackMachineSnapshots"] = snapshots

            # 2. Current DNS Records (Historical DNS without paid services is limited)
            dns_records = self.get_dns_records(target)
            results["DNSRecords"] = dns_records

            # 3. Domain History via WHOIS
            domain_history = self.get_domain_history(target)
            results["DomainHistory"] = domain_history

        except Exception as e:
            results["Error"] = str(e)

        return results

    def get_wayback_snapshots(self, url: str) -> list:
        snapshots = []
        wayback_api = f"http://archive.org/wayback/available?url={url}"
        response = requests.get(wayback_api, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if "archived_snapshots" in data and "closest" in data["archived_snapshots"]:
                snapshot = data["archived_snapshots"]["closest"]
                snapshots.append({
                    "timestamp": snapshot.get("timestamp"),
                    "available": snapshot.get("available"),
                    "url": snapshot.get("url")
                })
        return snapshots

    def get_dns_records(self, domain: str) -> dict:
        resolver = dns.resolver.Resolver()
        records = {}
        record_types = ['A', 'AAAA', 'MX', 'NS', 'CNAME', 'TXT']
        for record in record_types:
            try:
                answers = resolver.resolve(domain, record)
                records[record] = [r.to_text() for r in answers]
            except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
                records[record] = []
            except Exception as e:
                records[record] = [f"Error: {str(e)}"]
        return records

    def get_domain_history(self, domain: str) -> dict:
        history = {}
        try:
            w = whois.whois(domain)
            history["creation_date"] = str(w.creation_date)
            history["expiration_date"] = str(w.expiration_date)
            history["updated_date"] = str(w.updated_date)
            history["registrar"] = w.registrar
            history["registrant_name"] = w.name
            history["registrant_organization"] = w.org
            history["status"] = w.status
        except Exception as e:
            history["Error"] = str(e)
        return history
