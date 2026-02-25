from unpywall.utils import UnpywallCredentials
from unpywall import Unpywall
from keys import UNPAYWALL_EMAIL


UnpywallCredentials(UNPAYWALL_EMAIL)

class Unpaywall:
    def __init__(self):
        self.client = Unpywall()

    def lookup(self, doi):
        try:
            result = self.client.doi(doi)
            return result
        except Exception as e:
            print(f"Error during Unpaywall lookup: {e}")
            return None
