import re

from typing_extensions import deprecated

import doi_lookup as doi
import unpaywall as upw
from db import Database


def split_citations(citations):
    cits = citations.strip().split("\n")
    for cit in cits:
        yield split_citation(cit)

def split_citation(citation):
    full_citation = citation
    # use a regex to split the title ( [A-Za-z ]{15,}\. )
    title_match = re.search(r"\. [A-Za-z ]{15,}\.", citation)
    title = title_match.group(0).strip(' .').strip('. ') if title_match else "Unknown"
    return {
        "full_citation": full_citation,
        "title": title
    }

def lookup_doi(citation, title):
    doi_lookup = doi.DOILookup()
    result = doi_lookup.lookup(citation, title)
    return result

def lookup_unpaywall(dois):
    upw_lookup = upw.Unpaywall()
    result = upw_lookup.lookup(dois)
    return result


def get_citation_infos_from_dois(references, source = False):
    # references is a dict containing the reference and the full citation; we want to add 2 fields, one indicating if there is a doi and a second one containing the doi
    try:
        citation_infos = []
        for ref, info in references.items():
            #print(info)
            if info["has_doi"]:
                doi = info["doi"]
                unpaywall_result = lookup_unpaywall([doi])
                #print(unpaywall_result)
                result = unpaywall_result.to_dict()
                #print(result)
                authors = []
                if result["z_authors"]:
                    for author in result["z_authors"][0]:
                        authors.append(author["raw_author_name"])
                citation_infos.append({
                    "DOI": result["doi"][0],
                    "Title": result["title"][0] if result["title"] else "Unknown",
                    "Authors": authors if authors else "Unknown",
                    "Journal": result["journal_name"][0],
                    "Published": result["published_date"][0],
                    "Open Access": result["is_oa"][0],
                    "OA Standard": result["oa_status"][0],
                    "URL": result["doi_url"][0],
                    "Source": source,
                    "Index": info["index"],
                    "Reference": info["reference"]
                })
            else:
                citation_infos.append({
                    "DOI": None,
                    "Title": None,
                    "Authors": None,
                    "Journal": None,
                    "Published": None,
                    "Open Access": None,
                    "OA Standard": None,
                    "URL": None,
                    "Source": source,
                    "Index": info["index"],
                    "Reference": info["reference"]
                })
        return citation_infos
    except Exception as e:
        print(f"Error during citation info retrieval: {e}")
        return None


#@deprecated("Early version of the function, use get_citation_infos_from_dois instead")
def get_citation_infos_from_doi(dois, source = False):
    try:
        citation_infos = []
        unpaywall_results = lookup_unpaywall(dois)
        # print(unpaywall_results)
        # this is a pd dataframe, we need to iterate over the rows
        for index, row in unpaywall_results.iterrows():
            result = row.to_dict()
            #print(result)
            if result:
                authors = []
                if result["z_authors"]:
                    for author in result["z_authors"]:
                        authors.append(author["raw_author_name"])
                    # print(authors)
                citation_infos.append({
                    "DOI": result["doi"],
                    "Title": result["title"] if result["title"] else "Unknown",
                    "Authors": authors if authors else "Unknown",
                    "Journal": result["journal_name"],
                    "Published": result["published_date"],
                    "Open Access": result["is_oa"],
                    "OA Standard": result["oa_status"],
                    "URL": result["doi_url"],
                    "Source": source
                })

        #print(citation_infos)
        return citation_infos
    except Exception as e:
        print(f"Error during citation info retrieval: {e}")
        return None


#@deprecated("Early version of the function, use get_citation_infos_from_dois instead")
def get_citation_infos(citations, source = False):
    try:
        citation_infos = []
        dois = []
        for citation in citations:
            full_citation = citation["full_citation"]
            title = citation["title"]
            doi_result = lookup_doi(citation, title)
            if doi_result:
                dois.append(doi_result[0]["DOI"])

        unpaywall_results = lookup_unpaywall(dois)
        #print(unpaywall_results)
        # this is a pd dataframe, we need to iterate over the rows
        for index, row in unpaywall_results.iterrows():
            result = row.to_dict()
            #print(result)
            if result:
                authors = []
                if result["z_authors"]:
                    for author in result["z_authors"]:
                        authors.append(author["raw_author_name"])
                    # print(authors)
                citation_infos.append({
                    "DOI": result["doi"],
                    "Title": result["title"] if result["title"] else "Unknown",
                    "Authors": authors if authors else "Unknown",
                    "Journal": result["journal_name"],
                    "Published": result["published_date"],
                    "Open Access": result["is_oa"],
                    "OA Standard": result["oa_status"],
                    "URL": result["doi_url"],
                    "Source": source
                })

        #print(citation_infos)
        return citation_infos
    except Exception as e:
        print(f"Error during citation info retrieval: {e}")
        return None

def save_citations(citations):
    db = Database()
    return db.insert_papers(citations)

def save_citation(citation):
    db = Database()
    return db.insert_paper(citation)

def save_all_input_data(source_data, paragraph_data, citations_data):
    db = Database()
    return db.insert__all_input_data(source_data, paragraph_data, citations_data)

def save_reference_citation_links( ref_id, cit_ids):
    # Ref_id is the id of the source paper, cit_ids is a list of ids of the cited papers
    db = Database()
    links = [{"SourceID": ref_id, "CitationID": cit_id} for cit_id in cit_ids]
    return db.insert_references(links)

def save_paragraph(paragraph, source_id):
    db = Database()
    return db.insert_paragraph({
        "Paragraph": paragraph,
        "SourceID": source_id,
    })

def process_generated_citations(generated_citations):
    processed_citations = []
    for citation in generated_citations:
        processed_citation = split_citation(citation)
        processed_citations.append(processed_citation)
    return processed_citations


def find_apa_citations_in_paragraph(paragraph):
    apa_citation_pattern = r"\(([^)]+?,\s*\d{4}[a-z]?)\)"
    citations = re.findall(apa_citation_pattern, paragraph)
    return citations


def get_apa_dois(input_text):
    doi_pattern = r"10.\d{4,9}\/[-._;()\/:A-Za-z0-9]+"
    dois = re.findall(doi_pattern, input_text, re.IGNORECASE)
    return dois


def has_apa_dois(references):
    # try:
    # references is a dict containing the reference and the full citation; we want to add 2 fields, one indicating if there is a doi and a second one containing the doi
    doi_pattern = r"10.\d{4,9}\/[-._;()\/:A-Za-z0-9]+"
    #print(references)
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

    #print(new_refs)
    #except Exception as e:
    #    print(f"Error during APA DOI extraction: {e}")
    return new_refs


def get_apa_titles(input_text):
    # Title always comes after (YEAR). TITLE. So we can use a regex to find the title
    title_pattern = r"\)\.\s*([A-Za-z ?:]{15,})\."
    titles = re.findall(title_pattern, input_text)
    return titles