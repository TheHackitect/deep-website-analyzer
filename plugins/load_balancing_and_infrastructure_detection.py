# plugins/load_balancing_infrastructure_detection.py
import requests
from bs4 import BeautifulSoup
import re
from plugins.base_plugin import BasePlugin


class LoadBalancingInfrastructureDetectionPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Load Balancing and Infrastructure Detection"

    @property
    def description(self) -> str:
        return (
            "Detect the presence of load balancers, map infrastructure components like firewalls and databases, "
            "and determine if the application is containerized or uses IaC tools."
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

            # 1. Detect Load Balancers
            load_balancers = self.detect_load_balancers(response)
            results["LoadBalancers"] = load_balancers

            # 2. Map Infrastructure Components
            infrastructure = self.map_infrastructure(url, response)
            results["InfrastructureComponents"] = infrastructure

            # 3. Detect Containerization and IaC Tools
            containerization_iac = self.detect_containerization_iac(url, response)
            results["Containerization_IaCTools"] = containerization_iac

        except Exception as e:
            results["Error"] = str(e)

        return results

    def normalize_url(self, target: str) -> str:
        if not target.startswith(("http://", "https://")):
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

    def detect_load_balancers(self, response: requests.Response) -> list:
        detected_load_balancers = []
        headers = response.headers

        # Common Load Balancer Indicators
        lb_indicators = {
            "Cloudflare": {"Server": re.compile(r"cloudflare", re.IGNORECASE)},
            "AWS Elastic Load Balancer": {"Server": re.compile(r"aws.*elb", re.IGNORECASE)},
            "HAProxy": {"Server": re.compile(r"haproxy", re.IGNORECASE)},
            "Nginx": {"Server": re.compile(r"nginx", re.IGNORECASE)},
            "F5 BIG-IP": {"Server": re.compile(r"F5 BIG-IP", re.IGNORECASE)},
            "Akamai": {"Server": re.compile(r"AkamaiGHost", re.IGNORECASE)},
            "Imperva Incapsula": {"Server": re.compile(r"Incapsula", re.IGNORECASE)},
            "Microsoft Azure": {"Server": re.compile(r"Microsoft-IIS", re.IGNORECASE)},
        }

        for lb, patterns in lb_indicators.items():
            for header, pattern in patterns.items():
                header_value = headers.get(header, "")
                if re.search(pattern, header_value):
                    detected_load_balancers.append(lb)

        # Check for X-Forwarded-For header as a generic load balancer indicator
        if "X-Forwarded-For" in headers and "X-Forwarded-Proto" in headers:
            if "Generic" not in detected_load_balancers:
                detected_load_balancers.append("Generic Load Balancer")

        return list(set(detected_load_balancers))  # Remove duplicates

    def map_infrastructure(self, base_url: str, response: requests.Response) -> dict:
        infrastructure = {
            "Firewalls": [],
            "Databases": [],
            "OtherComponents": []
        }
        headers = response.headers

        # 1. Detect Firewalls based on headers
        firewall_signatures = {
            "AWS WAF": re.compile(r"awswaf", re.IGNORECASE),
            "Cloudflare": re.compile(r"cloudflare", re.IGNORECASE),
            "Imperva Incapsula": re.compile(r"Incapsula", re.IGNORECASE),
            "Fortinet": re.compile(r"FortiGate", re.IGNORECASE),
            "F5 BIG-IP": re.compile(r"F5 BIG-IP", re.IGNORECASE),
        }

        for fw, pattern in firewall_signatures.items():
            for header_value in headers.values():
                if re.search(pattern, header_value):
                    infrastructure["Firewalls"].append(fw)

        # 2. Infer Databases based on error messages or headers
        error_patterns = {
            "MySQL": re.compile(r"you have an error in your sql syntax", re.IGNORECASE),
            "PostgreSQL": re.compile(r"PostgreSQL query failed", re.IGNORECASE),
            "Microsoft SQL Server": re.compile(r"Microsoft SQL Server", re.IGNORECASE),
            "Oracle": re.compile(r"ORA-\d+", re.IGNORECASE),
        }

        body = response.text
        for db, pattern in error_patterns.items():
            if re.search(pattern, body):
                infrastructure["Databases"].append(db)

        # 3. Detect Other Infrastructure Components (e.g., CDN, Proxy)
        other_signatures = {
            "Content Delivery Network (CDN)": re.compile(r"cdn", re.IGNORECASE),
            "Reverse Proxy": re.compile(r"proxy", re.IGNORECASE),
        }

        for component, pattern in other_signatures.items():
            for header_value in headers.values():
                if re.search(pattern, header_value):
                    infrastructure["OtherComponents"].append(component)

        return infrastructure

    def detect_containerization_iac(self, base_url: str, response: requests.Response) -> dict:
        containerization = {
            "Containerization": False,
            "IaCTools": []
        }
        headers = response.headers
        body = response.text

        # 1. Detect Docker
        docker_indicators = [
            re.compile(r"docker", re.IGNORECASE),
            re.compile(r"docker-host", re.IGNORECASE),
            re.compile(r"docker-swarm", re.IGNORECASE),
        ]
        for pattern in docker_indicators:
            if re.search(pattern, body) or re.search(pattern, headers.get("Server", "")):
                containerization["Containerization"] = True
                break

        # 2. Detect Kubernetes
        kubernetes_indicators = [
            re.compile(r"kubernetes", re.IGNORECASE),
            re.compile(r"svc.cluster.local", re.IGNORECASE),
        ]
        for pattern in kubernetes_indicators:
            if re.search(pattern, body) or re.search(pattern, headers.get("Server", "")):
                containerization["Containerization"] = True
                break

        # 3. Detect Infrastructure as Code (IaC) Tools
        iac_tools_signatures = {
            "Terraform": re.compile(r"terraform", re.IGNORECASE),
            "Ansible": re.compile(r"ansible", re.IGNORECASE),
            "Chef": re.compile(r"chef", re.IGNORECASE),
            "Puppet": re.compile(r"puppet", re.IGNORECASE),
        }

        for tool, pattern in iac_tools_signatures.items():
            if re.search(pattern, body) or re.search(pattern, headers.get("Server", "")):
                containerization["IaCTools"].append(tool)

        return containerization
