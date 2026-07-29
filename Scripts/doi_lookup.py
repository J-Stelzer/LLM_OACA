from habanero import Crossref
from Levenshtein import distance

class DOILookup:
    def __init__(self):
        self.cr = Crossref()


    def lookup(self, full_cit, title=None, author=None, year=None, rep = 0):
        """
        This function tries to find the responding DOI for a paper, based on the given parameters.
        :param full_cit: the full citation string, which is used for the search query
        :param title: the title of the paper
        :param author: the author(s) of the paper
        :param year: the year of publication
        :param rep: the number of times the function has been called recursively:
        :return: the best matching entry from the Crossref API, which contains the DOI and other metadata
        """
        try:
            query = {"query": full_cit}
            if title:
                query["query.bibliographic"] = title
            if author:
                query["query.author"] = author
            if year:
                query["query.year"] = year


            results = self.cr.works(**query,sort="score", order="desc", limit=5)

            # If one of the results has a (close to) matching title, I want that ones infos
            for result in results['message']['items']:
                if distance(result["title"][0].lower(), title.lower() < 3):
                    return [result]

            return [results['message']['items'][0]]


        except RuntimeError as e:
            # In case there is a timeout or other runtime error, the function retries up to 10 times
            print(f"Error during DOI lookup: {e}")
            if rep < 10:
                self.lookup(full_cit, title, author, year, rep+1)
        return None


    def get_reference_count(self, doi):
        try:
            return self.cr.works(ids = doi)['message']['is-referenced-by-count']
        except Exception as e:
            return 0