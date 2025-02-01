# plugins/website_technologies.py
from plugins.base_plugin import BasePlugin
import builtwith
import requests

class WebsiteTechnologiesPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Website Technologies and Frameworks"

    @property
    def description(self) -> str:
        return "Identify server-side technologies, CMS, JavaScript frameworks, and web application frameworks."

    def run(self, target: str) -> dict:
        try:
            headers = {
                'User-Agent': 'DeepWebsiteAnalyzer/1.0'
            }
            response = requests.get(target, headers=headers, timeout=10)
            if response.status_code != 200:
                return {"Error": f"Failed to retrieve content. Status code: {response.status_code}"}

            technologies = builtwith.parse(response.text)

            return {
                "Detected Technologies": technologies
            }
        except Exception as e:
            return {"Error": str(e)}
