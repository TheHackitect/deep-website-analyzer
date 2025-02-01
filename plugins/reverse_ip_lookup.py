# plugins/reverse_ip_lookup.py
from plugins.base_plugin import BasePlugin
from sublist3r import Sublist3r
import os
import requests
import json
import dns.resolver

class ReverseIPLookupPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Reverse IP Lookup"

    @property
    def description(self) -> str:
        return "Find other domains hosted on the same IP address."

    @property
    def required_api_keys(self) -> list:
        return ["SecurityTrails_API_Key"]

    def run(self, target: str) -> dict:
        try:
            # Retrieve API key from config.json
            if not os.path.exists("config.json"):
                return {"Error": "Configuration file not found."}
            with open("config.json", "r") as f:
                config = json.load(f)
            plugin_config = config.get("Reverse IP Lookup", {})
            api_key = plugin_config.get("SecurityTrails_API_Key")
            if not api_key:
                return {"Error": "SecurityTrails API key not found. Please provide it in the settings."}

            # Resolve target domain to IP
            resolver = dns.resolver.Resolver()
            answers = resolver.resolve(target, 'A')
            ip_address = answers[0].to_text()

            # Use SecurityTrails API for Reverse IP Lookup
            headers = {
                'APIKEY': api_key,
                'Content-Type': 'application/json'
            }
            url = f"https://api.securitytrails.com/v1/domain/host/{ip_address}/subdomains"

            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                subdomains = [f"{sub}.{target}" for sub in data.get('subdomains', [])]
                return {
                    "IP Address": ip_address,
                    "Domains Hosted on IP": subdomains
                }
            else:
                return {"Error": f"API request failed with status code {response.status_code}: {response.text}"}
        except Exception as e:
            return {"Error": str(e)}
