# plugins/backup_old_files_detection.py
import requests
from bs4 import BeautifulSoup
import re
from plugins.base_plugin import BasePlugin


class BackupOldFilesDetectionPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Backup and Old Files Detection"

    @property
    def description(self) -> str:
        return "Find backup files or old versions of files that may be publicly accessible."

    @property
    def data_format(self) -> str:
        return "json"

    @property
    def required_api_keys(self) -> list:
        return []

    def run(self, target: str) -> dict:
        results = {}
        try:
            base_url = self.normalize_url(target)
            # 1. Detect Backup Files
            backup_files = self.detect_backup_files(base_url)
            results["BackupFiles"] = backup_files

            # 2. Detect Old Files via Directory Traversal
            old_files = self.detect_old_files(base_url)
            results["OldFiles"] = old_files

            # 3. Analyze robots.txt for Disallowed Paths
            robots_info = self.analyze_robots_txt(base_url)
            results["RobotsTxtDisallowedPaths"] = robots_info

        except Exception as e:
            results["Error"] = str(e)

        return results

    def normalize_url(self, target: str) -> str:
        if not target.startswith(("http://", "https://")):
            target = "http://" + target
        return target

    def detect_backup_files(self, base_url: str) -> list:
        backup_files_found = []
        try:
            response = requests.get(base_url, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                links = soup.find_all('a', href=True)
                backup_patterns = re.compile(r'.*\.(bak|old|backup|sql|tar\.gz|zip)$', re.IGNORECASE)
                for link in links:
                    href = link['href']
                    if backup_patterns.match(href):
                        full_url = self.combine_urls(base_url, href)
                        if self.check_url_exists(full_url):
                            backup_files_found.append(full_url)
        except Exception:
            pass
        return backup_files_found

    def detect_old_files(self, base_url: str) -> list:
        old_files_found = []
        try:
            common_old_dirs = ['/backup/', '/old/', '/temp/', '/archive/', '/backups/']
            for dir_path in common_old_dirs:
                full_url = self.combine_urls(base_url, dir_path)
                if self.check_url_exists(full_url):
                    old_files_found.append(full_url)
        except Exception:
            pass
        return old_files_found

    def analyze_robots_txt(self, base_url: str) -> list:
        disallowed_paths = []
        try:
            robots_url = self.combine_urls(base_url, '/robots.txt')
            response = requests.get(robots_url, timeout=10)
            if response.status_code == 200:
                lines = response.text.splitlines()
                user_agent = None
                for line in lines:
                    line = line.strip()
                    if line.startswith('User-agent:'):
                        user_agent = line.split(':', 1)[1].strip()
                    elif line.startswith('Disallow:') and user_agent in ['*', None]:
                        path = line.split(':', 1)[1].strip()
                        disallowed_paths.append(path)
        except Exception:
            pass
        return disallowed_paths

    def check_url_exists(self, url: str) -> bool:
        try:
            response = requests.head(url, timeout=10)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def combine_urls(self, base: str, path: str) -> str:
        return requests.compat.urljoin(base, path)
