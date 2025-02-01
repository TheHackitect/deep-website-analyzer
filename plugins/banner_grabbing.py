# plugins/banner_grabbing.py
import socket
import threading
from plugins.base_plugin import BasePlugin
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup, Comment
import re


class BannerGrabbingPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "Banner Grabbing"

    @property
    def description(self) -> str:
        return "Capture service banners for services running on open ports."

    @property
    def data_format(self) -> str:
        return "json"

    @property
    def required_api_keys(self) -> list:
        return []

    def run(self, target: str) -> dict:
        results = {}
        try:
            parsed_url = urlparse(self.normalize_url(target))
            hostname = parsed_url.hostname
            if not hostname:
                results["Error"] = "Invalid URL: Hostname could not be parsed."
                return results

            port_info = self.check_common_ports(hostname)
            open_ports = [port for port, status in port_info.items() if status == "Open"]

            if not open_ports:
                results["Message"] = "No common ports are open for banner grabbing."
                return results

            # Perform banner grabbing
            banners = self.grab_banners(hostname, open_ports)
            results["Banners"] = banners

        except Exception as e:
            results["Error"] = str(e)

        return results

    def normalize_url(self, target: str) -> str:
        if not target.startswith(("http://", "https://")):
            target = "http://" + target
        return target

    def check_common_ports(self, hostname: str) -> dict:
        port_info = {}
        # Common ports to scan with their corresponding services
        common_ports = {
            "FTP": 21,
            "SSH": 22,
            "SMTP": 25,
            "HTTP": 80,
            "HTTPS": 443,
            "POP3": 110,
            "IMAP": 143,
            "DNS": 53,
            "Telnet": 23,
            "SMB": 445,
            "RDP": 3389
        }
        for service, port in common_ports.items():
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(3)  # 3-second timeout
                    result = sock.connect_ex((hostname, port))
                    if result == 0:
                        port_info[port] = "Open"
                    else:
                        port_info[port] = "Closed"
            except Exception as e:
                port_info[port] = f"Error: {str(e)}"
        return port_info

    def grab_banners(self, hostname: str, ports: list) -> dict:
        banners = {}
        threads = []
        lock = threading.Lock()

        # Mapping services to ports for labeling
        service_port_map = {
            21: "FTP",
            22: "SSH",
            25: "SMTP",
            80: "HTTP",
            443: "HTTPS",
            110: "POP3",
            143: "IMAP",
            53: "DNS",
            23: "Telnet",
            445: "SMB",
            3389: "RDP"
        }

        def grab_banner(service: str, port: int):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(5)  # 5-second timeout
                    sock.connect((hostname, port))
                    # Some services send banners immediately upon connection
                    banner = sock.recv(1024).decode().strip()
                    with lock:
                        banners[f"Port {service}"] = banner if banner else "No banner received."
            except Exception as e:
                with lock:
                    banners[f"Port {service}"] = f"Failed to grab banner: {str(e)}"

        for port in ports:
            service = service_port_map.get(port, f"Port {port}")
            thread = threading.Thread(target=grab_banner, args=(service, port))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        return banners
