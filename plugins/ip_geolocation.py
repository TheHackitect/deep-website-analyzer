# plugins/ip_geolocation.py
from plugins.base_plugin import BasePlugin
import socket

class IPGeolocationPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "IP Geolocation"

    @property
    def description(self) -> str:
        return "Determine the physical location (country, region, city), coordinates, and ISP of an IP address."

    def run(self, target: str) -> dict:
        try:
            # Get IP address
            ip = socket.gethostbyname(target)
            # Use freegeoip.app for geolocation
            import requests
            response = requests.get(f"https://freegeoip.app/json/{ip}")
            data = response.json()
            return {
                "IP": ip,
                "Country": data.get("country_name"),
                "Region": data.get("region_name"),
                "City": data.get("city"),
                "Latitude": data.get("latitude"),
                "Longitude": data.get("longitude"),
                "ISP": data.get("metro_code"),
            }
        except Exception as e:
            return {"Error": str(e)}
