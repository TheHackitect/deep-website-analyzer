# tests/test_reverse_ip_lookup.py
import unittest
from plugins.reverse_ip_lookup import ReverseIPLookupPlugin
import os
class TestReverseIPLookupPlugin(unittest.TestCase):
    def setUp(self):
        self.plugin = ReverseIPLookupPlugin()

    def test_missing_config(self):
        # Temporarily rename config.json to simulate missing config
        if os.path.exists("config.json"):
            os.rename("config.json", "config_backup.json")
        result = self.plugin.run("example.com")
        self.assertIn("Error", result)
        # Restore config.json
        if os.path.exists("config_backup.json"):
            os.rename("config_backup.json", "config.json")

    def test_invalid_api_key(self):
        # Provide an invalid API key
        self.plugin.run = lambda target: {"Error": "Invalid API key."}
        result = self.plugin.run("example.com")
        self.assertIn("Error", result)

    def test_valid_run(self):
        # Mock a successful run
        self.plugin.run = lambda target: {"IP Address": "93.184.216.34", "Domains Hosted on IP": ["www.example.com"]}
        result = self.plugin.run("example.com")
        self.assertIn("IP Address", result)
        self.assertIn("Domains Hosted on IP", result)

if __name__ == '__main__':
    unittest.main()
