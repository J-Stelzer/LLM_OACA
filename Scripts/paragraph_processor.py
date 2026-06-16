import logging
import re


def replace_citations_with_indices(paragraph, references):
    """
    Replaces citations in brackets with the index of the respective reference
    :param paragraph: the paragraph in which the citations should be replaced
    :param references: a list of reference strings
    :return: the modified paragraph and a dictionary mapping citations to their indices
    """

    # First, I remove line breaks and split up citations where the same author published papers in multiple years (Author, 2020; 2025) -> (Author, 2020; Author, 2025)
    final_paragraph = replacer(paragraph).lower().replace("- ", "")
    final_paragraph = replace_multi_citations(final_paragraph)

    # Second, I split up the reference list into individual references, rebuild the expected citation based on authors and year and assign them an index
    refs = convert_to_ref_list(references)
    ref_index = build_reference_index(refs)


    # Third, I loop over all expected citations and if they are found within the paragraph, they are replaced with their index
    #linked = match_citations(cits, ref_index)
    final_links = {}
    for item in ref_index:
        if item:
            index = refs.index(item["reference"]) + 1
            found = False
            if item["index"] in final_paragraph:
                final_paragraph = final_paragraph.replace(f'{item["index"]}', f'R{index}')
                # add the index to the linked dict
                found = True

            if item["variation"] != []:
                for var in item["variation"]:
                    if var in final_paragraph:
                        final_paragraph = final_paragraph.replace(f'{var}', f'R{index}')
                        found = True
            if found:
                final_links[item["index"]] = {"reference": item["reference"], "index": index}



    return final_paragraph, final_links


def replace_multi_citations(paragraph):
    """
    Replaces multiple citations in brackets with the index of the respective reference (e.g. (Author, 2020; 2025) -> (Author, 2020; Author, 2025))
    :param paragraph: the paragraph in which the citations should be replaced
    :return: the modified paragraph and a dictionary mapping citations to their indices
    """
    # I use an extra function in order to be able to loop over all matches
    def repl(match):
        """
        Replaces a matched citation with the index of the respective reference
        :param match: The matched citation
        :return: The modified citation
        """
        authors = match.group(1)
        years = match.group(2).split(", ")
        return "; ".join(f"{authors}, {y}" for y in years)

    pattern = r"([^();]+?), ([0-9]{4}(?:, [0-9]{4})+)"
    return re.sub(pattern, repl, paragraph)


def find_in_text_citations(paragraph):
    """
    Finds all in-text citations in the paragraph and returns them as a list
    :param paragraph: the paragraph in which the citations should be found
    :return: a list of in-text citations
    """
    pattern = re.compile(r'\([a-zA-Z,.;&0-9 ]*[0-9]{4}[a-g]?\)')
    matches = pattern.findall(paragraph)
    return matches


def build_reference_index(references):
    """
    This function is used to reconstruct the expected citation of a reference
    :param references: a list of reference strings
    :return: a list of references and a dictionary mapping citations to their index
    """
    index = []

    # I loop over all references found in the reference list
    for ref in references:

        # First, I lower every reference and look for the year; It can happen that there is no year, if something went wrong during the splitting up of the references
        ref_l = ref.lower()
        year_match = re.search(r'\((\d{4}[a-z]?)\)', ref_l)
        if not year_match:
            year_match = re.search(r'\((n\.d\.?)\)', ref_l)
            if not year_match:
                year_match = re.search(r'\((in press)\)', ref_l)
                if not year_match:
                    logging.warning("no year match: " + ref_l)
                    continue
        year = year_match.group(1)

        # Second, I split up the authors
        authors = []
        authors_part = ref_l.split("(")[0]
        x = 0
        for author in authors_part.rstrip(".").split(","):
            if x % 2 == 0:
                name = author.lstrip("&.… ")
                if name != "".strip():
                    authors.append(name)
            x += 1
        if not authors:
            continue

        # Depending on the count of authors, the respective expected citation is built
        # There are apparently different variations for 2 and 3 authors, where a "," is added before the "&"
        var = []
        if len(authors) == 1:
            ind = f"{authors[0]}, {year}"

        elif len(authors) == 2:
            ind = f"{authors[0]} & {authors[1]}, {year}"
            var.append(f"{authors[0]}, & {authors[1]}, {year}")

        elif len(authors) == 3:
            ind = f"{authors[0]}, {authors[1]} & {authors[2]}, {year}"
            var.append(f"{authors[0]}, {authors[1]}, & {authors[2]}, {year}")
            var.append(f"{authors[0]} et al., {year}")

        else:
            #print(authors)
            if len(authors) == 4:
                ind = f"{authors[0]}, {authors[1]}, {authors[2]}, & {authors[3]}, {year}"
                var.append(f"{authors[0]} et al., {year}")
            else:
                ind = f"{authors[0]} et al., {year}"


        index.append({"index": ind, "reference": ref, "variation": var, "author_count": len(authors)})
    #print(len(index))
    index = sorted(index, key=lambda i: i["author_count"], reverse=True)

    return index


def convert_to_ref_list(citations):
    """
    Splits up reference list into individual citations
    :param citations: reference list as string
    :return: list of individual citations as strings
    """

    # 1: I  try to concatenate the DOI and remove all related whitespace characters
    pro_citations = re.sub(r'-\n', '-', citations)
    pro_citations = re.sub(r'–\n', '–', pro_citations)
    pro_citations = re.sub(r'\n\.', '.', pro_citations)
    pro_citations = re.sub(r'\n+', '\n', pro_citations)

    # Some references have 2 dots instead of one, usually around the title or journal
    # I don't want to remove the ... indicating the exclusion of authors, so I use a temporary placeholder string
    pro_citations = pro_citations.replace("...", "!?!?!?")
    pro_citations = re.sub(r'\.\.', '.', pro_citations)
    pro_citations = pro_citations.replace("!?!?!?", "...")

    # Some references add the month (and day) of publication to the year, so I remove them
    pro_citations = re.sub(r'\((\d{4}),?\s+[A-Za-z\s\d]+\)',r'(\1)', pro_citations)


    # 2: The regex pattern is looking for a name at the beginning of a new line, that is eventually followed by a year in brackets
    # Additionally I look for the next 2 dots to make sure I have a pattern like "authors. (year). title. journal."
    # The pattern can be split up into 3x3 versions;
        # On the one hand, the pattern depends on the year information, which can either be a year (rows 1, 4, 7), n.d(.) (rows 2, 5, 8) or in press (rows 3, 6, 9)
        # On the other hand there are authors in form of people and organisations
            # If it is starting with authors, I still include either brackets (rows 1-3) or numbers (rows 4-6), but not the combinations, since (year)
            # If it is starting with an organisation/just containing organisations (rows 7-9), I do not allow dots in the first part,
            # except for the one concluding the authors section, before the year; except "U.S."

    # a-zA-Z_\u00C0-\u032F includes all various kinds of characters
    # \uFB00-\uFB06\u00B4 includes accents and other kinds of symbols added to letters
    pattern = (
        r'(?=^([a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’\—\–\- ]+, +[a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’][a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’\s ́.,&\—\–\-…\\\/\(\)]*\.\s\(\d{4}[a-z]?\)\.([^\.\?]+[\.\?]){2}))|'
        r'(?=^([a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’\—\–\- ]+, +[a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’][a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’\s ́.,&\—\–\-…\\\/\(\)]*\.\s\(n\.d\.?\)\.([^\.\?]+[\.\?]){2}))|'
        r'(?=^([a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’\—\–\- ]+, +[a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’][a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’\s ́.,&\—\–\-…\\\/\(\)]*\.\s\(in press\)\.([^\.\?]+[\.\?]){2}))|'
        r'(?=^([a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’\—\–\- ]+, +[a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’][a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’\s ́.,&\—\–\-…\\\/\d]*\.\s\(\d{4}[a-z]?\)\.([^\.\?]+[\.\?]){2}))|'
        r'(?=^([a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’\—\–\- ]+, +[a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’][a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’\s ́.,&\—\–\-…\\\/\d]*\.\s\(n\.d\.?\)\.([^\.\?]+[\.\?]){2}))|'
        r'(?=^([a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’\—\–\- ]+, +[a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’][a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’\s ́.,&\—\–\-…\\\/\d]*\.\s\(in press\)\.([^\.\?]+[\.\?]){2}))|'
        r'(?=^((U.S. )?[a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’\—\–\-]+[a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’\s&\(\)\/\\\—\–\-\d:]*\.\s\(\d{4}[a-z]?\)\.([^\.\?]+[\.\?]){1}))|'
        r'(?=^((U.S. )?[a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’\—\–\-]+[a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’\s&\(\)\/\\\—\–\-\d:]*\.\s\(n\.d\.?\)\.([^\.\?]+[\.\?]){1}))|'
        r'(?=^((U.S. )?[a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’\—\–\-]+[a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’\s&\(\)\/\\\—\–\-\d:]*\.\s\(in press\)\.([^\.\?]+[\.\?]){1}))')

    #pattern = r'(?=^([a-zA-Z_\u00C0-\u02AF\u00B4’ \-]+,\s+[a-zA-Z_\u00C0-\u02AF\u00B4’][a-zA-Z_\u00C0-\u02AF\u00B4’\s.,&\-…\\\/\(\)]*\(\d{4}[a-z]?\).))' # OLD VERSION V2
    #pattern = r'(?=^([a-zA-Z_\u00C0-\u02AF\u00B4 \-]+,\s+[a-zA-Z_\u00C0-\u02A0\u00B4]\.|[a-zA-Z_\u00C0-\u02AF\u00B4 ]{3,}\.\s+\(\d{4}\)))' # OLD VERSION V1

    # 3: I split the reference list according to the regex pattern
    matches = re.findall(pattern, pro_citations, flags=re.MULTILINE)
    starting_points = []

    # 4: I go through all matches and extract the one that has the best fit, i.e. is the longest
    for match in matches:
        starting_points.append(max(match, key=len))

    for starting_point in starting_points:
        i = starting_points.index(starting_point)
        # In case there are duplications, e.g. due to multiple lines of author names, all matching the pattern,
        # I get rid of the shorter ones; The longest match comes first, since the matching works row by row
        while i < len(starting_points) - 1 and starting_points[i + 1] in starting_points[i]:
            del starting_points[i + 1]


    # 5: I get the rest of the reference by looking at the starting point of the following citation
    refs = []
    for starting_point in starting_points:
        cit_i = pro_citations.index(starting_point)
        sta_i = starting_points.index(starting_point)
        if sta_i + 1 < len(starting_points):
            cit_j = pro_citations.index(starting_points[sta_i + 1])
            # If there is an overlap between matches, the starting point of the second reference gets moved back
            # This can sometimes happen if the reference only contains author, year, title and journal, but no links and
            # the linebreak is placed "unfortunate"
            if cit_j - cit_i < len(starting_point):
                # It can however also happen, that the first author gets added, if there is no journal/publisher in the reference
                # This is a quick check to make sure that this is not the case
                ending_pattern = r"([a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’\—\–\- ]+, +[a-zA-Z_\u00C0-\u032F\uFB00-\uFB06\u00B4’]\.)$"
                ending_search = re.findall(ending_pattern, starting_point, flags=re.MULTILINE)
                if not ending_search:
                    refs.append(replacer(pro_citations[cit_i:cit_i + len(starting_point)]))
                    starting_points[sta_i + 1] = starting_points[sta_i + 1][len(starting_point) - (cit_j - cit_i):]
            else:
                refs.append(replacer(pro_citations[cit_i:cit_j]))
        else:
            refs.append(replacer(pro_citations[cit_i:]))


    # 6: I try to fix the doi in case it has been split up due to a linebreak
    for k in range(len(refs)):
        # 6.1:, fix the main part of the domain
        refs[k] = re.sub(
            r'https?\s*:\s*/\s*/\s*doi\s*\.\s*org\s*/\s*10\s*\.\s*',
            'https://doi.org/10.',
            refs[k],
            flags=re.IGNORECASE
        )

        # 6.2: fix the actual index
        refs[k] = re.sub(
            r'10\.\d{4,9}/(?:[A-Za-z0-9._;:<>()/-]+\s*)+',
            normalize_doi,
            refs[k]
        )

        # 6.3: remove potential artifacts following the DOI
        if "PubMedPMID:" in refs[k]:
            refs[k] = refs[k].replace("PubMedPMID:", " PubMedPMID:")

        if "PMID:" in refs[k]:
            refs[k] = refs[k].replace("PMID:", " PMID:")

        if "Epub" in refs[k]:
            refs[k] = refs[k].replace("Epub", " Epub")

        if ".https" in refs[k]:
            refs[k] = refs[k].replace("https", " https")

    return refs


def normalize_doi(match):
    # replace whitespace of DOI patterns
    return re.sub(r'\s+', '', match.group(0))

def replacer(citation):
    """
    Function replaces common line break patterns in citations and builds one consecutive string
    :param citation: a reference string with line breaks
    :return: a reference string without line breaks
    """
    cit = citation.replace('-\n', '-')
    cit = cit.replace('\n.', '.')
    cit = cit.replace('/\n', '/')
    cit = cit.replace(')\n', ')')
    cit = re.sub(r'(\d)\n(\d)', r'\1\2', cit)
    cit = re.sub(r'(/[a-zA-Z0-9]*)\n([a-zA-Z0-9]*/)', r'\1\2', cit)
    cit = cit.replace('\n', ' ')
    cit = re.sub(r'([a-zA-Z0-9]*-[a-zA-Z0-9]*) ([a-zA-Z0-9]*-[a-zA-Z0-9]*)', r'\1\2', cit)
    cit = cit.replace('  ', '\n')
    return cit.strip()
