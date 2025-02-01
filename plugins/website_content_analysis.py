# plugins/website_content_analysis.py
from plugins.base_plugin import BasePlugin
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

class WebsiteContentAnalysisPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Website Content Analysis"

    @property
    def description(self) -> str:
        return "Extract HTML content, meta tags, internal and external links, scripts, and resources."

    def run(self, target: str) -> dict:
        try:
            headers = {
                'User-Agent': 'DeepWebsiteAnalyzer/1.0'
            }
            response = requests.get(target, headers=headers, timeout=10)
            if response.status_code != 200:
                return {"Error": f"Failed to retrieve content. Status code: {response.status_code}"}

            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract meta tags
            meta_tags = {}
            for meta in soup.find_all('meta'):
                attrs = meta.attrs
                if 'name' in attrs and 'content' in attrs:
                    meta_tags[attrs['name']] = attrs['content']
                elif 'property' in attrs and 'content' in attrs:
                    meta_tags[attrs['property']] = attrs['content']

            # Extract internal and external links
            internal_links = set()
            external_links = set()
            parsed_uri = urlparse(target)
            base_url = f"{parsed_uri.scheme}://{parsed_uri.netloc}"

            for link in soup.find_all('a', href=True):
                href = link['href']
                href_parsed = urlparse(urljoin(base_url, href))
                if href_parsed.netloc == parsed_uri.netloc:
                    internal_links.add(href_parsed.geturl())
                else:
                    external_links.add(href_parsed.geturl())

            # Extract scripts
            scripts = [script['src'] for script in soup.find_all('script', src=True)]

            # Extract resources (images, CSS)
            images = [img['src'] for img in soup.find_all('img', src=True)]
            css = [link['href'] for link in soup.find_all('link', href=True) if link.get('rel') == ['stylesheet']]

            return {
                "Meta Tags": meta_tags,
                "Internal Links": list(internal_links),
                "External Links": list(external_links),
                "Scripts": scripts,
                "Images": images,
                "CSS Files": css
            }
        except Exception as e:
            return {"Error": str(e)}
