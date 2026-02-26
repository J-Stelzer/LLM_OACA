from habanero import Crossref
import json

class DOILookup:
    def __init__(self):
        self.cr = Crossref()


    def lookup(self, full_cit, title=None, author=None, year=None, doi=None, rep = 0):
        try:
            query = {"query": full_cit}
            if title:
                query["query.bibliographic"] = title
            if author:
                query["query.author"] = author
            if year:
                query["query.year"] = year
            if doi:
                query["query.doi"] = doi

            results = self.cr.works(**query,sort="score", order="desc", limit=5)

            for result in results['message']['items']:
                if result["title"][0].lower() == title.lower():
                    return [result]

            return [results['message']['items'][0]]


        except RuntimeError as e:
            print(f"Error during DOI lookup: {e}")
        # except Exception as e:
            print(f"Error during DOI lookup: {e}")
            if rep < 10:
                self.lookup(full_cit, title, author, year, doi, rep+1)
        return None


#test = "S. Petridis, et al., AngleKindling: Supporting Journalistic Angle Ideation with Large Language Models in Proceedings of the 2023 CHI Conference on Human Factors in Computing Systems, CHI ’23., (Association for Computing Machinery, 2023), pp. 1–16."
#titel = "AngleKindling: Supporting Journalistic Angle Ideation with Large Language Models in Proceedings of the 2023 CHI Conference on Human Factors in Computing Systems"
#lookup = DOILookup()
#result2 = lookup.lookup(test, titel)
#print(result2)
#
#test = "A. Caliskan, J. J. Bryson, A. Narayanan, Semantics derived automatically from language corpora contain human-like biases. Science 356, 183–186 (2017)."
#titel = "Semantics derived automatically from language corpora contain human-like biases"
#lookup = DOILookup()
#results = lookup.lookup(test, titel)
#print(results)
#for result in result2:
#    print(f"Title: {result['title'][0]}")
#    print(f"DOI: {result['DOI']}")
#    # print(result)