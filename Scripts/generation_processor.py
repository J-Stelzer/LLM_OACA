import re
from types import NoneType

import db
import doi_lookup as doi
import unpaywall as upw
from Levenshtein import distance

def split_response(response):
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
    # references is a list of dicts, where each dict has an index and reference field
    # I want to add a field to each dict indicating if there is a doi and a second field containing the doi
    # split the parts of the reference into a list of authors, the title, the journal, the doi and the year
    # sample
    # R2 Author, A. (Year). Title about LLMs in journalism. Journal Name, 1(1), 1–10. https://doi.org/10.0000/placeholder2
    # R3 Author, B. (Year). Title about LLMs in copywriting. Journal Name, 2(1), 11–22. https://doi.org/10.0000/placeholder3

    doi_pattern = r"10.\d{4,9}\/[-._;()\/:A-Za-z0-9]+"

    new_refs = {}
    try:
        for ref in references:
            authors = ref["reference"].split("(", maxsplit=1)[0].strip()
            author_list = []
            for author in authors.split(","):
                author_list.append(author.strip())
            #print("Authors done")
            year = re.findall(r"\((\d{4})\)", ref["reference"])
            #print("Year done")
            title_journal_part = ref["reference"].split(").", maxsplit=1)[1].strip()
            title = title_journal_part.split(".")[0].strip()
            #print("Title done")
            journal = title_journal_part.split(".")[1].strip().split(",", maxsplit=1)[0].strip()
            #print("Journal done")
            dois = re.findall(doi_pattern, ref["reference"], re.IGNORECASE)

            if dois:
                fin_doi = dois[0]
            else:
                fin_doi = None

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
    # references is a dict containing the reference and the full citation; we want to add 2 fields, one indicating if there is a doi and a second one containing the doi
    try:
        citation_infos = []
        for ref, info in references.items():
            #print(info)
            try:
                if info["has_doi"]:
                    doi = info["doi"]
                    unpaywall_result = lookup_unpaywall([doi])
                    result = unpaywall_result.to_dict()
                    if result["oa_status"] == "UNPAYWALL API ERROR":
                        citation_infos.append(try_doi_workaround(info))
                        continue
                    authors = []
                    if not isinstance(result["z_authors"], NoneType):
                        for author in result["z_authors"][0]:
                            authors.append(author["raw_author_name"])

                    hallucination_score = round(get_hallucination_score(info,    {
                        "authors": authors,
                        "title": result["title"][0] if result["title"] else "",
                        "journal": result["journal_name"][0]
                    }), 1)

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
                citation_infos.append(try_doi_workaround(info))
            except Exception as e:
                print(f"Error while extracting information: {e}")
                citation_infos.append(return_blank_ref(info))
                continue


        return citation_infos
    except Exception as e:
        print(f"Error during citation info retrieval: {e}")
        return None


def lookup_doi(citation, title):
    doi_lookup = doi.DOILookup()
    result = doi_lookup.lookup(citation, title)
    return result

def lookup_unpaywall(doi):
    upw_lookup = upw.Unpaywall()
    result = upw_lookup.lookup(doi)
    return result



def try_doi_workaround(info):
    try:
        potential_doi = lookup_doi(info["reference"], info["title"])
        if potential_doi:
            print(potential_doi)
            if potential_doi[0]["DOI"]:
                unpaywall_result = lookup_unpaywall([potential_doi[0]["DOI"]])
                print("[0]DOI")
                print(unpaywall_result)
            elif potential_doi["DOI"]:
                unpaywall_result = lookup_unpaywall(potential_doi["DOI"])
                print("DOI")
                print(unpaywall_result)
            else:
                return return_blank_ref(info)
            result = unpaywall_result.to_dict()

            authors = []
            if not isinstance(result["z_authors"][0], NoneType):
                for author in result["z_authors"][0]:
                    authors.append(author["raw_author_name"])
            print(result)
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
        return return_blank_ref(info)
    except Exception as e:
        print(f"Error during workaround: {e}")
        return return_blank_ref(info)


def return_blank_ref(info):
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
    return (get_authors_distance(generated_info["authors"], comparison_info["authors"])
            + get_title_distance(generated_info["title"], comparison_info["title"])
            + get_journal_distance(generated_info["journal"], comparison_info["journal"]))


def get_authors_distance(gen_authors, comp_authors):
    print(f"Comparing authors: {gen_authors} with {comp_authors}")
    gen_author_list = []
    x = 0
    if not gen_authors.rstrip(".").split(","):
        return 1.1
    for author in gen_authors.rstrip(".").split(","):
        if x%2 == 0:
            gen_author_list.append(author.lstrip(" & ").lstrip("& "))
        x += 1
    if isinstance(comp_authors, NoneType) or isinstance(gen_author_list, NoneType) or comp_authors == [] or gen_author_list == [] or len(gen_author_list) != len(comp_authors):
        return 1.1
    for gen_author, comp_author in zip(gen_author_list, comp_authors):
        print(f"Comparing '{gen_author}' with '{comp_author}'")

        if not gen_author or not comp_author or not isinstance(comp_author.split(" ")[-1], str) or distance(gen_author.strip().lower(), comp_author.split(" ")[-1].lower()) > 3:
            return 1.1
    return 0


def get_title_distance(gen_title, comp_title):
    return float(not isinstance(gen_title, str) or not isinstance(comp_title, str) or distance(gen_title.lower(), comp_title.lower()) > 5)*1.2

def get_journal_distance(gen_journal, comp_journal):
    return float(not isinstance(gen_journal, str) or not isinstance(comp_journal, str) or distance(gen_journal.lower(), comp_journal.lower()) > 5)*1.4



def save_generated_citations(generated_refs, source_id, llm):
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