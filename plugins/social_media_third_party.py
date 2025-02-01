# plugins/social_media_third_party.py
from plugins.base_plugin import BasePlugin
import requests
from bs4 import BeautifulSoup
import re

class SocialMediaThirdPartyPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Social Media and Third-party Services"

    @property
    def description(self) -> str:
        return "Extract links to social media profiles associated with the website, detect third-party tracking and analytics services, third-party login services, and third-party widgets."

    @property
    def required_api_keys(self) -> list:
        return []  # No API keys required

    def run(self, target: str) -> dict:
        results = {}
        try:
            if not target.startswith(("http://", "https://")):
                target = "http://" + target  # Default to HTTP if scheme not provided
            response = requests.get(target, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')

            # 1. Extract Social Media Profiles
            social_media_profiles = self.extract_social_media_profiles(soup, target)
            results["Social Media Profiles"] = social_media_profiles

            # 2. Detect Third-party Tracking and Analytics Services
            tracking_services = self.detect_tracking_services(soup)
            results["Tracking and Analytics Services"] = tracking_services

            # 3. Detect Third-party Login Services
            login_services = self.detect_login_services(soup)
            results["Third-party Login Services"] = login_services

            # 4. Detect Third-party Widgets
            widgets = self.detect_widgets(soup)
            results["Third-party Widgets"] = widgets

        except Exception as e:
            results["Error"] = str(e)

        return results

    def extract_social_media_profiles(self, soup, base_url):
        social_media_domains = {
            "Facebook": "facebook.com",
            "Twitter": "twitter.com",
            "LinkedIn": "linkedin.com",
            "Instagram": "instagram.com",
            "YouTube": "youtube.com",
            "Pinterest": "pinterest.com",
            "TikTok": "tiktok.com",
            "Reddit": "reddit.com",
            "GitHub": "github.com",
            "Medium": "medium.com",
        }
        profiles = {}
        for platform, domain in social_media_domains.items():
            links = soup.find_all('a', href=True)
            for link in links:
                href = link['href']
                if domain in href:
                    profiles.setdefault(platform, []).append(href)
        # Remove duplicates
        for platform in profiles:
            profiles[platform] = list(set(profiles[platform]))
        return profiles if profiles else "No social media profiles found."

    def detect_tracking_services(self, soup):
        tracking_domains = {
            "Google Analytics": "analytics.google.com",
            "Facebook Pixel": "connect.facebook.net",
            "Hotjar": "hotjar.com",
            "Mixpanel": "mixpanel.com",
            "Crazy Egg": "crazyegg.com",
            "Clicky": "clicky.com",
            "Matomo": "matomo.org",
            "HubSpot": "hubspot.com",
            "Segment": "segment.com",
            "Quantcast": "quantcast.com",
        }
        services = {}
        scripts = soup.find_all('script', src=True)
        for name, domain in tracking_domains.items():
            for script in scripts:
                src = script['src']
                if domain in src:
                    services.setdefault(name, []).append(src)
        return services if services else "No tracking or analytics services detected."

    def detect_login_services(self, soup):
        login_services = {
            "Google OAuth": "accounts.google.com",
            "Facebook Login": "facebook.com",
            "Twitter Login": "twitter.com",
            "LinkedIn Login": "linkedin.com",
            "GitHub Login": "github.com",
            "Microsoft Login": "login.microsoftonline.com",
        }
        services = {}
        links = soup.find_all('a', href=True)
        for name, domain in login_services.items():
            for link in links:
                href = link['href']
                if domain in href:
                    services.setdefault(name, []).append(href)
        return services if services else "No third-party login services detected."

    def detect_widgets(self, soup):
        widget_domains = {
            "Facebook Widget": "facebook.com",
            "Twitter Widget": "twitter.com",
            "YouTube Embed": "youtube.com",
            "Google Maps": "google.com/maps",
            "Instagram Embed": "instagram.com",
            "Pinterest Widget": "pinterest.com",
            "Tawk.to": "tawk.to",
            "Intercom": "intercom.io",
            "Drift": "drift.com",
            "Zendesk": "zendesk.com",
        }
        widgets = {}
        iframes = soup.find_all('iframe', src=True)
        scripts = soup.find_all('script', src=True)
        for name, domain in widget_domains.items():
            for iframe in iframes:
                src = iframe['src']
                if domain in src:
                    widgets.setdefault(name, []).append(src)
            for script in scripts:
                src = script['src']
                if domain in src:
                    widgets.setdefault(name, []).append(src)
        return widgets if widgets else "No third-party widgets detected."
