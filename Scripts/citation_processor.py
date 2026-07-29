import re
import types
from types import NoneType

from typing_extensions import deprecated
import datetime
import doi_lookup as dl
import unpaywall as upw
from Scripts import doi_lookup
from db import Database


def split_citations(citations):
    """
    This function splits the citation strings into a list of citation strings.
    :param citations: a list of citation strings
    :return: a list of citation strings
    """
    cits = citations.strip().split("\n")
    for cit in cits:
        yield split_citation(cit)

def split_citation(citation):
    """
    This function splits a citation string into its components: full citation and title.
    :param citation: a list of citation strings
    :return: a dictionary with the full citation and the title
    """
    full_citation = citation
    # use a regex to split the title ( [A-Za-z ]{15,}\. )
    title_match = re.search(r"\. [A-Za-z ]{15,}\.", citation)
    title = title_match.group(0).strip(' .').strip('. ') if title_match else "Unknown"
    return {
        "full_citation": full_citation,
        "title": title
    }

def lookup_doi(citation, title):
    """
    This function looks up the doi from the citation string.
    :param citation: a list of citation strings
    :param title:
    :return:
    """
    doi_lookup = dl.DOILookup()
    result = doi_lookup.lookup(citation, title)
    return result

def lookup_unpaywall(dois):
    """
    This function looks up the unpaywall information from the doi.
    :param dois: a list of DOIs
    :return: a list of unpaywall results
    """
    upw_lookup = upw
    result = upw_lookup.lookup_api(dois)
    return result


def get_citation_infos_from_dois(references):
    """
    This function gets citation infos from a list of DOIs. This function is only used for non-source papers (i.e. papers that are refernced within another paper)
    :param references: a list of references, each a dictionary containing citation information like the DOI and whether there was a DOI found
    :return: a list of citation infos ready to be stored to the database
    """
    try:
        doi_lookup = dl.DOILookup()
        citation_infos = []
        for ref, info in references.items():
            #print(info)
            if info["has_doi"]:
                doi = info["doi"]
                unpaywall_result = lookup_unpaywall([doi])
                citation_count = doi_lookup.get_reference_count(doi)
                result = unpaywall_result.to_dict()
                authors = []
                if result["z_authors"] and not isinstance(result["z_authors"][0], NoneType):
                    for author in result["z_authors"][0]:
                        authors.append(author["raw_author_name"])
                citation_infos.append({
                    "DOI": result["doi"][0],
                    "Title": result["title"][0] if result["title"] else None,
                    "Authors": authors if authors else None,
                    "Journal": result["journal_name"][0],
                    "Published": result["published_date"][0],
                    "Open Access": result["is_oa"][0],
                    "OA Standard": result["oa_status"][0],
                    "URL": result["doi_url"][0],
                    "Source": False,
                    "Index": info["index"],
                    "Reference": info["reference"],
                    "Citation Count": citation_count,
                    "StoreDate" : datetime.date.today().isoformat(),
                })
                continue

            citation_infos.append({
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
                "Citation Count": None,
                "StoreDate" : datetime.date.today().isoformat()
            })
        return citation_infos
    except Exception as e:
        print(f"Error during citation info retrieval: {e}")
        return None



def get_citation_infos_from_doi(doi):
    """
    This function gets citation infos from a DOI. This function is only used for source papers (i.e. the paper for which the citations are extracted)
    :param doi: the DOI of the paper
    :return: a list of citation infos ready to be stored to the database
    """
    try:
        doi_lookup = dl.DOILookup()
        citation_infos = []
        unpaywall_results = lookup_unpaywall(doi)
        # this is a pd dataframe, we need to iterate over the rows
        for index, row in unpaywall_results.iterrows():
            result = row.to_dict()
            #print(result)
            if result:
                citation_count = doi_lookup.get_reference_count(doi)
                authors = []
                if result["z_authors"]:
                    for author in result["z_authors"]:
                        authors.append(author["raw_author_name"])
                    #print(authors)

                citation_infos.append({
                    "DOI": result["doi"],
                    "Title": result["title"] if result["title"] else "Unknown",
                    "Authors": authors if authors else "Unknown",
                    "Journal": result["journal_name"],
                    "Published": result["published_date"],
                    "Open Access": result["is_oa"],
                    "OA Standard": result["oa_status"],
                    "URL": result["doi_url"],
                    "Source": True,
                    "Citation Count": citation_count,
                    "StoreDate" : datetime.date.today().isoformat()
                })

        #print(citation_infos)
        return citation_infos
    except Exception as e:
        print(f"Error during citation info retrieval (get_citation_infos_from_doi): {e}")
        return None


def save_citations(citations):
    """
    Saves multiple citation infos to database
    :param citations: a list of citation infos
    :return: the result of the database insertion
    """
    db = Database()
    return db.insert_papers(citations)


def save_citation(citation):
    """
    Saves one citation info to database
    :param citation: a dictionary containing citation information
    :return: the result of the database insertion
    """
    db = Database()
    return db.insert_paper(citation)


def save_reference_citation_links(source_id, cit_ids):
    """
    Saves links between source paper and papers cited within the source paper
    :param source_id: the ID of the source paper
    :param cit_ids: a list of IDs of the cited papers
    :return: the result of the database insertion
    """
    db = Database()
    links = [{"SourceID": source_id, "CitationID": cit_id} for cit_id in cit_ids]
    return db.insert_references(links)


def save_paragraph(paragraph, source_id, raw, refs):
    """
    Saves raw and processed paragraph and raw reference list of source paper to the database
    :param paragraph: the processed paragraph text
    :param source_id: the ID of the source paper
    :param raw: the raw text of the paragraph
    :param refs: the list of reference IDs
    :return: the result of the database insertion
    """
    db = Database()
    return db.insert_paragraph({
        "Paragraph": paragraph,
        "SourceID": source_id,
        "Raw": raw,
        "ReferenceList": refs,
        "StoreDate" : datetime.date.today().isoformat()
    })


def get_apa_dois_from_text(input_text:str):
    """
    This function gets APA DOIs from a text. It uses a regex to find all DOIs in the text and returns them as a list.
    :param input_text: the text to search for DOIs
    :return: a list of DOIs found in the text (should only be one)
    """
    doi_pattern = r"10.\d{4,9}\/[-._;()\/:A-Za-z0-9]+"
    dois = re.findall(doi_pattern, input_text, re.IGNORECASE)
    return dois



def has_apa_dois(references):
    """
    This function checks if the references contain DOIs. Regex looks for 10.... to find all DOIs in the references and returns a dictionary with the results.
    :param references: a list of references text
    :return: aa list of dictionaries containing the split up references with DOI info
    """
    # try:
    doi_pattern = r"10.\d{4,9}\/[-._;()\/:A-Za-z0-9]+"
    new_refs = {}


    for cit, info in references.items():
        if not info:
            new_refs[cit] = {
                "index": None,
                "reference": cit,
                "has_doi": False,
                "doi": None
            }
            continue
        # print(info)
        dois = re.findall(doi_pattern, info["reference"], re.IGNORECASE)
        if dois:
            new_refs[cit] = {
                "index": info["index"],
                "reference": info["reference"],
                "has_doi": True,
                "doi": dois[0]
            }

        else:
            new_refs[cit] = {
                "index": info["index"],
                "reference": info["reference"],
                "has_doi": False,
                "doi": None
            }

    return new_refs
