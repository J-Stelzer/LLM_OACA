import re
from types import NoneType
import datetime
import db
import doi_lookup as dl
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
            #print("Authors done")

            # Second, the year
            year = re.findall(r"\((\d{4})\)", ref["reference"])
            #print("Year done")

            # Third, the title and the journal name
            # I use the fact that the title always comes after the year and a dot "(9999)."
            # and that the title and journal are usually split by a dot or question mark
            title_journal_part = ref["reference"].split(").", maxsplit=1)[1].strip()
            title = title_journal_part.split(".")[0].strip()
            #print("Title done")
            if "?" in title_journal_part:
                journal = title_journal_part.split("?")[1].strip().split(",", maxsplit=1)[0].strip()
            else:
                journal = title_journal_part.split(".")[1].strip().split(",", maxsplit=1)[0].strip()
            #print("Journal done")

            # Fourth, check for DOI
            # If the LLM does not specifically indicate that a paper does not have a DOI, it is assumed that it should have one
            # In this case, the crossref API will be used to identify the correct DOI later on
            if "NO DOI" not in ref["reference"]:
                dois = re.findall(doi_pattern, ref["reference"], re.IGNORECASE)
                if dois:
                    fin_doi = dois[0]
                else:
                    fin_doi = None
            else:
                fin_doi = "NO DOI"

            # Finally, I store all the data in a dictionary
            new_refs["R"+ref["index"]] = {
                "index": ref["index"],
                "reference": ref["reference"],
                "authors": authors,
                "title": title,
                "journal": journal,
                "year": year,
                "doi": fin_doi,
                "has_doi": True if fin_doi and fin_doi != "NO DOI" else False,
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
        doi_look = dl.DOILookup()
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
                    citation_count = doi_look.get_reference_count(doi)
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
                        "Index": info["index"],
                        "Reference": info["reference"],
                        "Hallucination": hallucination_score,
                        "Citation Count": citation_count,
                        "StoreDate" : datetime.date.today().isoformat()
                    })
                    continue
                # If there was no DOI, try workaround
                if info["doi"] != "NO DOI":
                    citation_infos.append(try_doi_workaround(info))
                else:
                    citation_infos.append({
                        "DOI": info["doi"],
                        "Title": info["title"],
                        "Authors": info["authors"],
                        "Journal": info["journal"],
                        "Published": None,
                        "Open Access": None,
                        "OA Standard": None,
                        "URL": None,
                        "Index": info["index"],
                        "Reference": info["reference"],
                        "Hallucination": -1,
                        "Citation Count": None,
                        "StoreDate" : datetime.date.today().isoformat()
                    })
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
    doi_lookup = dl.DOILookup()
    result = doi_lookup.lookup(citation, title)
    return result

def lookup_unpaywall(doi):
    """
    Looks up information for a given DOI using the Unpaywall API
    :param doi: the DOI to look up
    :return: the result from the Unpaywall API
    """
    upw_lookup = upw
    result = upw_lookup.lookup_api(doi)
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
                "Index": info["index"],
                "Reference": info["reference"],
                "Hallucination": hallucination_score,
                "StoreDate" : datetime.date.today().isoformat()
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
        "Index": info["index"],
        "Reference": info["reference"],
        "Hallucination": 4,
        "Citation Count": None,
        "StoreDate" : datetime.date.today().isoformat()
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
    The last name is a practical choice, since the reference does not contain the full names
    :param gen_authors: a list of generated authors
    :param comp_authors: a list of comparison authors provided by the DOI request
    :return: a hallucination distance
    """

    gen_author_list = []

    #print(f"Comparing authors: {gen_authors} with {comp_authors}")
    # If there is no author in the generated reference, return hallucination indicator
    if not gen_authors.rstrip(".").split(","):
        return 1.1

    skips_authors = False
    if "…" in gen_authors or "..." in gen_authors:
        skips_authors = True

    # Split up the authors of the generated reference
    x = 0
    for author in gen_authors.rstrip(".").split(","):
        if x%2 == 0:
            name = author.lstrip(" & ").lstrip("& ")
            # This part deals with van, de, etc.
            if len(name.split(" ")) > 1:
                name = name.split(" ")[-1]
            gen_author_list.append(name)
        x += 1

    print(gen_author_list)
    print(comp_authors)

    # If there is no author(s) or the number of authors is not equal, return hallucination indicator
    if isinstance(comp_authors, NoneType) or isinstance(gen_author_list, NoneType) or comp_authors == [] or gen_author_list == []:
        return 1.1

    # Finally, here I check whether the authors match
    for i in range(min(len(gen_author_list), len(comp_authors))):
        print(f"Comparing '{gen_author_list[i]}' with '{comp_authors[i]}'")

        # First, I verify, that they are not null/None, i.e. that there is a name
        if not gen_author_list[i] or not comp_authors[i] or not isinstance(comp_authors[i].split(" ")[-1], str):
            return 1.1

        # Second, I check if we have reached the end for the generated authors, i.e. if some names were omitted due to the number of authors
        if skips_authors:
            last_author = gen_author_list[i].replace("…", "").replace("...", "")
            if distance(last_author.lower(), comp_authors[i].split(" ")[-1].lower()) > 3:
                return 1.1
            else:
                return 0
        # Last, check for all other authors before the last one
        if distance(gen_author_list[i].strip().lower(), comp_authors[i].split(" ")[-1].lower()) > 3:
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
    # If there is no title in the generated reference, return hallucination indicator
    if not isinstance(gen_title, str) or not isinstance(comp_title, str):
        return 1.2
    # If the distance is between the shorter title (length n) and the first n characters of the other one larger than 3 return hallucination indicator,
    # else return no hallucination
    shorter_len = min(len(gen_title), len(comp_title))
    return float(distance(gen_title.lower()[:shorter_len], comp_title.lower()[:shorter_len]) > 3)*1.2


def get_journal_distance(gen_journal, comp_journal):
    """
Calculates the hallucination distance between the generated information and the information from the API result for the journal.
    :param gen_journal: the generated journal
    :param comp_journal: the comparison journal provided by the DOI request
    :return: a hallucination distance
    """
    # If there is no journal in the generated reference or the distance is larger than 5, return hallucination indicator, else return no hallucination
    # If there is no title in the generated reference, return hallucination indicator
    if not isinstance(gen_journal, str) or not isinstance(comp_journal, str):
        return 1.4
    # If the distance is between the shorter title (length n) and the first n characters of the other one larger than 3 return hallucination indicator,
    # else return no hallucination
    shorter_len = min(len(gen_journal), len(comp_journal))
    return float(distance(gen_journal.lower()[:shorter_len], comp_journal.lower()[:shorter_len]) > 3)*1.4
    #return float(not isinstance(gen_journal, str) or not isinstance(comp_journal, str) or distance(gen_journal.lower(), comp_journal.lower()) > 5)*1.4



def save_generated_citations(generated_refs, source_id, llm):
    """
    Saves the generated citations to the database
    :param generated_refs: a list of reference dictionaries with the generated citation infos
    :param source_id: the ID of the source paper
    :param llm: the language model used to generate the citations
    :return: the result of the database insertion
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
            "Hallucination": ref["Hallucination"],
            "Citation Count": ref["Citation Count"],
            "StoreDate" : datetime.date.today().isoformat()
        }
        citations_data.append(citation)
    database = db.Database()
    return database.insert_generated(citations_data)

