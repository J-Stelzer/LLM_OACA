import re
from types import NoneType

import db
import doi_lookup as doi
import unpaywall as upw
from Levenshtein import distance

def split_response(response):
    """
    Splits the response from the LLM into a list of references, where each reference is a dictionary containing the index and the reference string.
    :param response: LLM response
    :return: a list of reference dictionaries containing the index and the reference string
    """
    generated_refs = response.split("\n")
    final_refs = []
    for ref in generated_refs:
        if ref.strip() and ref.startswith("R"):
            content = ref.split(" ", maxsplit=1)
            index = re.sub(r'\D', '', content[0])
            ref = content[1]
            final_refs.append({"index": index, "reference": ref})
    return final_refs


def get_reference_parts(references: list):
    """
    This function takes a list of references and splits them into their components:
    authors, title, journal, year and doi. It also adds a field indicating whether there is a doi or not.
    :param references: a list of reference dictionaries containing the index and the reference string
    :return: a list of reference dictionaries containing the reference infos
    """
    doi_pattern = r"10.\d{4,9}\/[-._;()\/:A-Za-z0-9]+"

    new_refs = {}
    try:
        # I just loop over all reference and check for:
        for ref in references:
            # First, the authors
            authors = ref["reference"].split("(", maxsplit=1)[0].strip()
            author_list = []
            for author in authors.split(","):
                author_list.append(author.strip())
            #print("Authors done")

            # Second, the year
            year = re.findall(r"\((\d{4})\)", ref["reference"])
            #print("Year done")

            # Third, the title and the journal name
            title_journal_part = ref["reference"].split(").", maxsplit=1)[1].strip()
            title = title_journal_part.split(".")[0].strip()
            #print("Title done")
            journal = title_journal_part.split(".")[1].strip().split(",", maxsplit=1)[0].strip()
            #print("Journal done")

            # Fourth, the DOI
            dois = re.findall(doi_pattern, ref["reference"], re.IGNORECASE)

            if dois:
                fin_doi = dois[0]
            else:
                fin_doi = None

            # Finally, I store all the data in a dictionary
            new_refs["R"+ref["index"]] = {
                "index": ref["index"],
                "reference": ref["reference"],
                "authors": authors,
                "title": title,
                "journal": journal,
                "year": year,
                "doi": fin_doi,
                "has_doi": True if dois else False,
            }

        return new_refs
    except Exception as e:
        print(f"Error during reference parsing: {e}")


def get_citation_infos_from_dois(references):
    """
    This function gets citation infos from a list of DOIs. Has the same function as the function in the citation_processor;
    Only difference is, this one ties to find a working DOI in case the one provided by the LLM is not working (i.e. potential hallucination)
    Additionally, it checks whether the provided information are aligning with the information provided by the DOS request
    :param references: list of reference dictionaries containing the index and the reference string
    :return: a list of reference dictionaries containing the citation infos (DOI, title, authors, journal, published date, open access status, OA standard, URL) and the hallucination score
    """
    try:
        citation_infos = []
        for ref, info in references.items():
            #print(info)
            try:
                # First, I check whether there has been a DOI found in the original generated reference
                # If not, it automatically tries to find a working DOI based on the reference
                if info["has_doi"]:
                    doi = info["doi"]
                    # I get the citation infos from the Unpaywall API based on the DOI
                    unpaywall_result = lookup_unpaywall([doi])
                    result = unpaywall_result.to_dict()
                    # If the API does not return a result, I try to look up a potential working DOI
                    if result["oa_status"] == "UNPAYWALL API ERROR":
                        citation_infos.append(try_doi_workaround(info))
                        continue

                    # Second, get the author names from the API result
                    authors = []
                    if not isinstance(result["z_authors"], NoneType):
                        for author in result["z_authors"][0]:
                            authors.append(author["raw_author_name"])

                    # Third, I calculate the hallucination score based on the distance between the generated information and the information from the API result
                    hallucination_score = round(get_hallucination_score(info,    {
                        "authors": authors,
                        "title": result["title"][0] if result["title"] else "",
                        "journal": result["journal_name"][0]
                    }), 1)

                    # Finally, I store all the relevant information in a dictionary, which is then stored in the list of citation infos
                    citation_infos.append({
                        "DOI": result["doi"][0],
                        "Title": result["title"][0] if result["title"] else "Unknown",
                        "Authors": authors if authors else "Unknown",
                        "Journal": result["journal_name"][0],
                        "Published": result["published_date"][0],
                        "Open Access": result["is_oa"][0],
                        "OA Standard": result["oa_status"][0],
                        "URL": result["doi_url"][0],
                        "Source": False,
                        "Index": info["index"],
                        "Reference": info["reference"],
                        "Hallucination": hallucination_score,
                    })
                    continue
                # If there was no DOI, try workaround
                citation_infos.append(try_doi_workaround(info))
            except Exception as e:
                # If any errors occur during the process, try workaround
                print(f"Error while extracting information: {e}")
                citation_infos.append(return_blank_ref(info))
                continue

        return citation_infos
    except Exception as e:
        print(f"Error during citation info retrieval: {e}")
        return None


def lookup_doi(citation, title):
    """
    Tries to find potential DOI for generated reference without (working) DOI
    :param citation: the full citation string, which is used for the search query
    :param title: the title of the paper
    :return: the best matching entry from the Crossref API
    """
    doi_lookup = doi.DOILookup()
    result = doi_lookup.lookup(citation, title)
    return result

def lookup_unpaywall(doi):
    """
    Looks up information for a given DOI using the Unpaywall API
    :param doi: the DOI to look up
    :return: the result from the Unpaywall API
    """
    upw_lookup = upw.Unpaywall()
    result = upw_lookup.lookup(doi)
    return result



def try_doi_workaround(info):
    """
    Tries to find a working DOI for a given DOI
    :param info: a reference dictionary containing the index and the reference string, as well as the parsed authors, title, journal, year and DOI information
    :return: a dictionary containing information about the potential DOI
    """
    try:
        # First, I try to get a potential DOI
        potential_doi = lookup_doi(info["reference"], info["title"])
        # If there is none, either that paper does not exist or it is not a paper with a DOI and a blank reference info is returned
        if potential_doi:
            #print(potential_doi)
            # Second, depending on the returned result, the DOI is in different spots
            if potential_doi[0]["DOI"]:
                unpaywall_result = lookup_unpaywall([potential_doi[0]["DOI"]])
                #print("[0]DOI")
                #(unpaywall_result)
            elif potential_doi["DOI"]:
                unpaywall_result = lookup_unpaywall(potential_doi["DOI"])
                #print("DOI")
                #print(unpaywall_result)
            else:
                return return_blank_ref(info)
            result = unpaywall_result.to_dict()

            # Same process as for regular citation info look up;
            # Get authors, calculate hallucination score and store all relevant info in dictionary
            authors = []
            if not isinstance(result["z_authors"][0], NoneType):
                for author in result["z_authors"][0]:
                    authors.append(author["raw_author_name"])
            #print(result)

            hallucination_score = round(get_hallucination_score(info, {
                "authors": authors,
                "title": result["title"][0] if result["title"] else "",
                "journal": result["journal_name"][0]
            }), 1)

            return {
                "DOI": result["doi"][0],
                "Title": result["title"][0] if result["title"] else "Unknown",
                "Authors": authors if authors else "Unknown",
                "Journal": result["journal_name"][0],
                "Published": result["published_date"][0],
                "Open Access": result["is_oa"][0],
                "OA Standard": result["oa_status"][0],
                "URL": result["doi_url"][0],
                "Source": False,
                "Index": info["index"],
                "Reference": info["reference"],
                "Hallucination": hallucination_score
            }
        # If DOI lookup workaround not successful, return blank reference info
        return return_blank_ref(info)
    except Exception as e:
        # If an error during the DOI lookup workaround occurs, return blank reference info
        print(f"Error during workaround: {e}")
        return return_blank_ref(info)


def return_blank_ref(info):
    """
    Returns a blank reference info dictionary in case no information could be retrieved for a given reference
    :param info: a reference dictionary containing the index and the reference string
    :return: a blank reference dictionary
    """
    return {
        "DOI": None,
        "Title": None,
        "Authors": None,
        "Journal": None,
        "Published": None,
        "Open Access": None,
        "OA Standard": None,
        "URL": None,
        "Source": False,
        "Index": info["index"],
        "Reference": info["reference"],
        "Hallucination": 4
    }

def get_hallucination_score(generated_info, comparison_info):
    """
    This function calculates a hallucination score based on the distance between the generated information and the information from the API result.
    Every function has their own indicator (authors -> .1, title -> .2, journal -> .4)
    :param generated_info: a dictionary containing the generated information (authors, title, journal)
    :param comparison_info: a dictionary containing the comparison information provided by the DOI request (authors, title, journal)
    :return: a hallucination score
    """
    return (get_authors_distance(generated_info["authors"], comparison_info["authors"])
            + get_title_distance(generated_info["title"], comparison_info["title"])
            + get_journal_distance(generated_info["journal"], comparison_info["journal"]))


def get_authors_distance(gen_authors, comp_authors):
    """
    Calculates the hallucination distance between the generated information and the information from the API result for the authors.
    It loops over all authors and compares the last names in order
    :param gen_authors: a list of generated authors
    :param comp_authors: a list of comparison authors provided by the DOI request
    :return: a hallucination distance
    """
    print(f"Comparing authors: {gen_authors} with {comp_authors}")
    gen_author_list = []
    x = 0
    # If there is no author in the generated reference, return hallucination indicator
    if not gen_authors.rstrip(".").split(","):
        return 1.1

    # Split up the authors of the generated reference
    for author in gen_authors.rstrip(".").split(","):
        if x%2 == 0:
            gen_author_list.append(author.lstrip(" & ").lstrip("& "))
        x += 1
    # If there is no author(s) or the number of authors is not equal, return hallucination indicator
    if isinstance(comp_authors, NoneType) or isinstance(gen_author_list, NoneType) or comp_authors == [] or gen_author_list == [] or len(gen_author_list) != len(comp_authors):
        return 1.1
    for gen_author, comp_author in zip(gen_author_list, comp_authors):
        print(f"Comparing '{gen_author}' with '{comp_author}'")
        # If one of the authors is not within a reasonable distance, return hallucination indicator
        if not gen_author or not comp_author or not isinstance(comp_author.split(" ")[-1], str) or distance(gen_author.strip().lower(), comp_author.split(" ")[-1].lower()) > 3:
            return 1.1
    # return no hallucination
    return 0


def get_title_distance(gen_title, comp_title):
    """
Calculates the hallucination distance between the generated information and the information from the API result for the title.
    :param gen_title: the generated title
    :param comp_title: the comparison title provided by the DOI request
    :return: a hallucination distance
    """
    # If there is no title in the generated reference or the distance is larger than 5, return hallucination indicator, else return no hallucination
    return float(not isinstance(gen_title, str) or not isinstance(comp_title, str) or distance(gen_title.lower(), comp_title.lower()) > 5)*1.2

def get_journal_distance(gen_journal, comp_journal):
    """
Calculates the hallucination distance between the generated information and the information from the API result for the journal.
    :param gen_journal: the generated journal
    :param comp_journal: the comparison journal provided by the DOI request
    :return: a hallucination distance
    """
    # If there is no journal in the generated reference or the distance is larger than 5, return hallucination indicator, else return no hallucination
    return float(not isinstance(gen_journal, str) or not isinstance(comp_journal, str) or distance(gen_journal.lower(), comp_journal.lower()) > 5)*1.4



def save_generated_citations(generated_refs, source_id, llm):
    """
    Saves the generated citations to the database
    :param generated_refs: a list of reference dictionaries with the generated citation infos
    :param source_id: the ID of the source paper
    :param llm: the language model used to generate the citations
    :return: the result of the database insertion
    """
    citations_data = []
    for ref in generated_refs:
        citation = {
            "SourceID": source_id,
            "LLM": llm,
            "DOI": ref["DOI"],
            "Title": ref["Title"],
            "Authors": ref["Authors"],
            "Journal": ref["Journal"],
            "Open Access": ref["Open Access"],
            "OA Standard": ref["OA Standard"],
            "Index": ref["Index"],
            "Reference": ref["Reference"],
            "Hallucination": ref["Hallucination"]
        }
        citations_data.append(citation)
    database = db.Database()
    return database.insert_generated(citations_data)


#res = """R1 Caliskan, A., Bryson, J. J., & Narayanan, A. (2017). Semantics derived automatically from language corpora contain human biases. Science, 356(6334), 183–186.
#
#R2 Author, A. (Year). Title about LLMs in journalism. Journal Name, 1(1), 1–10. https://doi.org/10.0000/placeholder2
#
#R3 Author, B. (Year). Title about LLMs in copywriting. Journal Name, 2(1), 11–22. https://doi.org/10.0000/placeholder3
#
#R4 Author, C. (Year). Title about LLMs in academia. Journal Name, 3(1), 23–34. https://doi.org/10.0000/placeholder4
#
#R5 Author, D. (Year). Title about other writing tasks. Journal Name, 4(1), 35–46. https://doi.org/10.0000/placeholder5
#
#R6 OpenAI. (2023). ChatGPT: A language model accessible to the public. OpenAI Blog. https://openai.com/blog/chatgpt
#
#R7 Bartlett, F. C. (1932). Remembering: A study in experimental and social psychology. Cambridge, England: Cambridge University Press.
#
#R8 Boyd, R., & Richerson, P. J. (1985). Culture and the Evolutionary Process. Chicago, IL: University of Chicago Press.
#
#R9 Mesoudi, A. (2011). Cultural evolution: A review of the field. Trends in Cognitive Sciences, 15(6), 246–251.
#
#R10 Author, E. (Year). Transmission chain experiments in psychology: A methodological overview. Journal of Experimental Psychology: General, 110(2), 200–215.
#
#R11 Baumeister, R. F., Bratslavsky, E., Finkenauer, C., & Vohs, K. D. (2001). Bad is stronger than good. American Psychologist, 56(3), 323–329.
#"""
#
#print(list(split_response(res)))