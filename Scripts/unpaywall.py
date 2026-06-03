from types import NoneType

import pandas as pd
from unpywall.utils import UnpywallCredentials
from unpywall import Unpywall
from keys import UNPAYWALL_EMAIL


UnpywallCredentials(UNPAYWALL_EMAIL)

EMPTY_RESULT = pd.DataFrame()
EMPTY_RESULT['is_oa'] = False
EMPTY_RESULT["title"] = "Unknown"
EMPTY_RESULT["journal_name"] = "Unknown"
EMPTY_RESULT["published_date"] = "Unknown"
EMPTY_RESULT["oa_status"] = "UNPAYWALL API ERROR"
EMPTY_RESULT["doi_url"] = "Unknown"
EMPTY_RESULT["z_authors"] = [[{"raw_author_name": "Unknown"}]]
EMPTY_RESULT["doi_url"] = "Unknown"

class Unpaywall:
    def __init__(self):
        self.client = Unpywall()


    def lookup(self, doi):
        """
        This function looks up a DOI in the Unpaywall database and returns the result as a dictionary.
        If the DOI is not found, it returns a dictionary with the DOI and "Unknown" values for all other fields.
        :param doi: the DOI to look up
        :return: the result from the Unpaywall API
        """
        try:
            result = self.client.doi(doi, errors='ignore')
            if isinstance(result, NoneType):
                result = EMPTY_RESULT
                result['doi'] = doi

            return result
        except Exception as e:
            print(f"Error during Unpaywall lookup: {e}")
            return None