# plugins/whois_info.py
from plugins.base_plugin import BasePlugin
import whois

class WHOISInfoPlugin(BasePlugin):
    @property
    def name(self) -> str:
        return "WHOIS Information"

    @property
    def description(self) -> str:
        return "Obtain domain registrar details, registration date, expiry date, and registrant contact details."

    def run(self, target: str) -> dict:
        try:
            w = whois.whois(target)
            return {
                "Registrar": w.registrar,
                "Creation Date": str(w.creation_date),
                "Expiration Date": str(w.expiration_date),
                "Registrant Name": w.name,
                "Registrant Email": w.email,
                "Registrant Country": w.country,
            }
        except Exception as e:
            return {"Error": str(e)}
