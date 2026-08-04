import logging
from types import NoneType

import pandas as pd
from unpywall.utils import UnpywallCredentials
from unpywall import Unpywall

from keys import UNPAYWALL_EMAIL

import requests
import json


UnpywallCredentials(UNPAYWALL_EMAIL)

EMPTY_RESULT = pd.DataFrame()
EMPTY_RESULT['is_oa'] = False
EMPTY_RESULT["title"] = None
EMPTY_RESULT["journal_name"] = None
EMPTY_RESULT["published_date"] = None
EMPTY_RESULT["oa_status"] = "UNPAYWALL API ERROR"
EMPTY_RESULT["doi_url"] = None
EMPTY_RESULT["z_authors"] = [[{"raw_author_name": "Unknown"}]]


def lookup_api(doi):
    """
    This function looks up a DOI in the Unpaywall database and returns the result as a dictionary, using the API directly
    If the DOI is not found, it returns a dictionary with the DOI and "Unknown" values for all other fields.
    :param doi: the DOI to look up
    :return: the result from the Unpaywall API
    """
    try:
        response = requests.get("https://api.unpaywall.org/v2/" + doi[0].rstrip(". ") + "?email=" + UNPAYWALL_EMAIL)
        # Handling exception if no result was found, returns empty result
        if response.status_code == 404:
            result_df = EMPTY_RESULT
            result_df['doi'] = doi[0]
            logging.warning("Error during lookup for DOI: " + doi[0] + "\nThere was no result found for that DOI.")
            return result_df

        # Convert results to JSON and then to a DataFrame, ensuring that a result has been found
        result = json.loads(response.content)
        if isinstance(result, NoneType):
            result_df = EMPTY_RESULT
            result_df['doi'] = doi[0]
        else:
            result_df = pd.DataFrame()
            result_df["z_authors"] = [result["z_authors"]]
            result_df["is_oa"] = result["is_oa"]
            result_df["title"] = result["title"]
            result_df["journal_name"] = result["journal_name"]
            result_df["published_date"] = result["published_date"]
            result_df["oa_status"] = result["oa_status"]
            result_df["doi_url"] = result["doi_url"]
            result_df["doi"] = result["doi"]


        return result_df
    except Exception as e:
        print(f"Error during Unpaywall lookup: {e}")
        return None


class Unpaywall:
    def __init__(self):
        self.client = Unpywall()


    def lookup(self, doi):
        """
        This function looks up a DOI in the Unpaywall database and returns the result as a dictionary, using the unpywall library
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

