# plugins/accessibility_user_experience.py
import requests
from bs4 import BeautifulSoup
import re
from plugins.base_plugin import BasePlugin


class AccessibilityUserExperiencePlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Accessibility and User Experience"

    @property
    def description(self) -> str:
        return (
            "Analyze website for accessibility features, mobile responsiveness, use of media queries, "
            "service worker usage, PWA features, and browser compatibility."
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
            url = self.normalize_url(target)
            response = self.fetch_response(url)
            if not response:
                results["Error"] = "Failed to retrieve website response."
                return results

            # 1. Accessibility Features
            accessibility = self.analyze_accessibility(response.text)
            results["AccessibilityFeatures"] = accessibility

            # 2. Mobile Responsiveness
            responsiveness = self.check_mobile_responsiveness(response.text)
            results["MobileResponsiveness"] = responsiveness

            # 3. Service Worker and PWA Features
            pwa_features = self.detect_pwa_features(url, response.text)
            results["PWAFeatures"] = pwa_features

            # 4. Browser Compatibility
            browser_compatibility = self.analyze_browser_compatibility(response.text)
            results["BrowserCompatibility"] = browser_compatibility

        except Exception as e:
            results["Error"] = str(e)

        return results

    def normalize_url(self, target: str) -> str:
        if not target.startswith("http"):
            target = "http://" + target
        return target

    def fetch_response(self, url: str) -> requests.Response:
        try:
            headers = {
                "User-Agent": "DeepWebsiteAnalyzer/1.0"
            }
            response = requests.get(url, headers=headers, timeout=15)
            return response
        except requests.RequestException:
            return None

    def analyze_accessibility(self, html: str) -> dict:
        accessibility = {}
        try:
            soup = BeautifulSoup(html, 'html.parser')
            # Check for alt attributes in images
            images = soup.find_all('img')
            images_without_alt = [img.get('src', '') for img in images if not img.get('alt')]
            accessibility["ImagesWithoutAlt"] = images_without_alt

            # Check for ARIA roles and labels
            aria_roles = soup.find_all(attrs={"role": True})
            aria_labels = soup.find_all(attrs={"aria-label": True})
            accessibility["ARIA_Roles"] = len(aria_roles)
            accessibility["ARIA_Labels"] = len(aria_labels)

            # Check for semantic HTML elements
            semantic_elements = ['header', 'nav', 'main', 'section', 'article', 'footer', 'aside']
            semantic_usage = {element: bool(soup.find(element)) for element in semantic_elements}
            accessibility["SemanticHTMLUsage"] = semantic_usage

        except Exception as e:
            accessibility["Error"] = str(e)
        return accessibility

    def check_mobile_responsiveness(self, html: str) -> dict:
        responsiveness = {}
        try:
            soup = BeautifulSoup(html, 'html.parser')
            # Check for viewport meta tag
            viewport = soup.find('meta', attrs={'name': 'viewport'})
            responsiveness["ViewportMetaTag"] = bool(viewport)

            # Check for media queries in inline styles or linked CSS
            media_queries = re.findall(r'@media\s*\((.*?)\)', html, re.IGNORECASE)
            responsiveness["MediaQueries"] = media_queries

        except Exception as e:
            responsiveness["Error"] = str(e)
        return responsiveness

    def detect_pwa_features(self, base_url: str, html: str) -> dict:
        pwa = {}
        try:
            # Check for manifest.json
            manifest_url = self.combine_urls(base_url, "/manifest.json")
            pwa["ManifestExists"] = self.check_url_exists(manifest_url)

            # Check for service worker registration in JavaScript
            service_worker_pattern = re.compile(r'serviceWorker\.register\([\'"](.*?)[\'"]\)')
            matches = service_worker_pattern.findall(html)
            pwa["ServiceWorkers"] = matches if matches else []

            # Check for PWA related meta tags
            theme_color = False
            app_name = False
            icons = False
            soup = BeautifulSoup(html, 'html.parser')
            if soup.find('meta', attrs={'name': 'theme-color'}):
                theme_color = True
            if soup.find('meta', attrs={'name': 'application-name'}):
                app_name = True
            if soup.find_all('link', rel='icon'):
                icons = True
            pwa["ThemeColorMetaTag"] = theme_color
            pwa["AppNameMetaTag"] = app_name
            pwa["IconsDefined"] = icons

        except Exception as e:
            pwa["Error"] = str(e)
        return pwa

    def analyze_browser_compatibility(self, html: str) -> dict:
        compatibility = {}
        try:
            # Check for usage of modern JavaScript features that may affect compatibility
            modern_js_patterns = [
                r'let\s+\w+\s*=',  # let declarations
                r'const\s+\w+\s*=',  # const declarations
                r'=>\s*{',  # Arrow functions
                r'class\s+\w+',  # ES6 Classes
                r'async\s+function',  # Async functions
                r'fetch\(',  # Fetch API
                r'Promise\s*\.',  # Promises
            ]
            matches = 0
            for pattern in modern_js_patterns:
                if re.search(pattern, html):
                    matches += 1
            compatibility["ModernJSFeatureUsage"] = matches
            compatibility["PotentialCompatibilityIssues"] = matches > 3  # Threshold can be adjusted

        except Exception as e:
            compatibility["Error"] = str(e)
        return compatibility

    def check_url_exists(self, url: str) -> bool:
        try:
            response = requests.head(url, timeout=10)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def combine_urls(self, base: str, path: str) -> str:
        return requests.compat.urljoin(base, path)
