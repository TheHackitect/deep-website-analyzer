# plugins/search_engine_indexing.py
from plugins.base_plugin import BasePlugin
import requests
from bs4 import BeautifulSoup
import re

class SearchEngineIndexingPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Search Engine Indexing and Robots.txt"

    @property
    def description(self) -> str:
        return "Find the number of pages indexed, retrieve robots.txt and sitemap.xml, list disallowed entries, perform sitemap enumeration, and check for sitemap discrepancies."

    @property
    def required_api_keys(self) -> list:
        return []  # No API keys required

    def run(self, target: str) -> dict:
        results = {}
        try:
            if not target.startswith(("http://", "https://")):
                target = "http://" + target  # Default to HTTP if scheme not provided
            parsed_url = requests.utils.urlparse(target)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

            # 1. Estimate Number of Pages Indexed
            indexed_pages = self.estimate_indexed_pages(target)
            results["Number of Pages Indexed"] = indexed_pages

            # 2. Retrieve robots.txt
            robots_txt, disallowed_entries = self.get_robots_txt(base_url)
            results["robots.txt"] = robots_txt
            results["Disallowed Entries"] = disallowed_entries

            # 3. Retrieve sitemap.xml
            sitemap_urls = self.get_sitemap(base_url)
            results["Sitemap URLs"] = sitemap_urls

            # 4. Sitemap Enumeration
            sitemap_contents = self.enumerate_sitemap(sitemap_urls)
            results["Sitemap Contents"] = sitemap_contents

            # 5. Check for Sitemap Discrepancies
            discrepancies = self.check_sitemap_discrepancies(sitemap_contents, target)
            results["Sitemap Discrepancies"] = discrepancies

        except Exception as e:
            results["Error"] = str(e)

        return results

    def estimate_indexed_pages(self, target):
        # Without API, use Google search with site: operator
        indexed_pages = {}
        try:
            query = f"site:{target}"
            url = f"https://www.google.com/search?q={query}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            }
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')

            result_stats = soup.find('div', id='result-stats')
            if result_stats:
                text = result_stats.get_text()
                match = re.search(r'About ([\d,]+) results', text)
                if match:
                    count = match.group(1).replace(',', '')
                    indexed_pages["Google"] = int(count)
                else:
                    indexed_pages["Google"] = "Could not parse result count."
            else:
                indexed_pages["Google"] = "Result stats not found."

        except Exception as e:
            indexed_pages["Google"] = f"Error estimating indexed pages: {str(e)}"
        return indexed_pages

    def get_robots_txt(self, base_url):
        robots_txt = ""
        disallowed = []
        try:
            robots_url = f"{base_url}/robots.txt"
            response = requests.get(robots_url, timeout=10)
            if response.status_code == 200:
                robots_txt = response.text
                # Parse disallowed entries
                lines = robots_txt.split('\n')
                for line in lines:
                    if line.strip().lower().startswith('disallow'):
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            path = parts[1].strip()
                            disallowed.append(path)
            else:
                robots_txt = f"robots.txt not found. Status code: {response.status_code}"
        except Exception as e:
            robots_txt = f"Error retrieving robots.txt: {str(e)}"
        return robots_txt, disallowed

    def get_sitemap(self, base_url):
        sitemap_urls = []
        try:
            sitemap_url = f"{base_url}/sitemap.xml"
            response = requests.get(sitemap_url, timeout=10)
            if response.status_code == 200:
                sitemap_urls.append(sitemap_url)
            else:
                # Attempt to find sitemap location from robots.txt
                robots_url = f"{base_url}/robots.txt"
                robots_response = requests.get(robots_url, timeout=10)
                if robots_response.status_code == 200:
                    matches = re.findall(r'Sitemap:\s*(\S+)', robots_response.text, re.I)
                    sitemap_urls.extend(matches)
        except Exception as e:
            sitemap_urls.append(f"Error retrieving sitemap: {str(e)}")
        return sitemap_urls if sitemap_urls else "No sitemap.xml found."

    def enumerate_sitemap(self, sitemap_urls):
        sitemap_contents = {}
        try:
            for sitemap in sitemap_urls:
                response = requests.get(sitemap, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'xml')
                    urls = [loc.text for loc in soup.find_all('loc')]
                    sitemap_contents[sitemap] = urls
                else:
                    sitemap_contents[sitemap] = f"Failed to retrieve sitemap. Status code: {response.status_code}"
        except Exception as e:
            sitemap_contents[sitemap] = f"Error enumerating sitemap: {str(e)}"
        return sitemap_contents

    def check_sitemap_discrepancies(self, sitemap_contents, target):
        discrepancies = {}
        try:
            # Extract all URLs from sitemap
            sitemap_urls = []
            for sitemap, urls in sitemap_contents.items():
                if isinstance(urls, list):
                    sitemap_urls.extend(urls)
            # Simple check: compare with actual URLs on the site (limited)
            # For demonstration, assume discrepancy if sitemap has URLs that return 404
            broken_urls = []
            for url in sitemap_urls:
                try:
                    response = requests.get(url, timeout=10)
                    if response.status_code == 404:
                        broken_urls.append(url)
                except:
                    broken_urls.append(url)
            discrepancies["Broken URLs in Sitemap"] = broken_urls if broken_urls else "No broken URLs detected in sitemap."
        except Exception as e:
            discrepancies["Error"] = str(e)
        return discrepancies
