# plugins/site_traffic_data.py
from plugins.base_plugin import BasePlugin
import requests

class SiteTrafficDataPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Site Traffic Data"

    @property
    def description(self) -> str:
        return "Access Alexa rank, estimated site traffic, page views, and bounce rate."

    def run(self, target: str) -> dict:
        try:
            # Extract domain from target URL
            from urllib.parse import urlparse
            parsed_url = urlparse(target)
            domain = parsed_url.netloc if parsed_url.netloc else parsed_url.path

            # SimilarWeb API Endpoint
            # Note: You need to sign up for SimilarWeb API and obtain an API key.
            api_key = "YOUR_SIMILARWEB_API_KEY"  # Replace with your actual API key
            url = f"https://api.similarweb.com/v1/website/{domain}/total-traffic-and-engagement/visits?api_key={api_key}&start_date=2023-01&end_date=2023-12&country=world&granularity=monthly"

            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {
                    "Total Visits": data.get('visits'),
                    "Page Views": data.get('page_views'),
                    "Bounce Rate": data.get('bounce_rate')
                }
            else:
                return {"Error": f"API request failed with status code {response.status_code}: {response.text}"}
        except Exception as e:
            return {"Error": str(e)}
