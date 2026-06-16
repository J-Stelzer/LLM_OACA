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


'''
test = """Abeare, C., Messa, I., Whitfield, C., Zuccato, B., Casey, J., Rykulski, N., &
Erdodi, L. (2019). Performance validity in collegiate football athletes
at baseline neurocognitive testing. The Journal of Head Trauma
Rehabilitation, 34(4), E20–E31. https://doi.org/10.1097/HTR.000000
0000000451
ACS Pearson. (2009). Advanced clinical solutions for the WAIS-IV and
WMS-IV—Technical manual. Psychological Corporation.
Ali, S., Crisan, I., Abeare, C. A., & Erdodi, L. A. (2022). Cross-cultural
performance validity testing: Managing false positives in examinees with
limited English proficiency. Developmental Neuropsychology, 47(6), 273–
294. https://doi.org/10.1080/87565641.2022.2105847
Allen, L. M., Conder, R. L., Green, P., & Cox, D. R. (1997). CARB 97
manual for the computerized assessment of response bias. CogniSyst.
Allen, L. M., III, Iverson, G. L., & Green, P. (2003). Computerized
assessment of response bias in forensic neuropsychology. Journal of
Forensic Neuropsychology, 3(1–2), 205–225. https://doi.org/10.1300/
J151v03n01_02
Altman, D. G., & Bland, J. M. (1994). Diagnostic tests 3: Receiver operating
characteristic plots. The BMJ, 309(6948), Article 188. https://doi.org/10
.1136/bmj.309.6948.188
An, K. Y., Abeare, K., Cutler, L., Brantuo, M., Ali, S., Giromini, L., Hastings,
M., & Erdodi, L. (2024). That old dog can still hunt—Alternative cutoffs
and the recognition trial improve the classification accuracy of the Rey 15-
item test. Professional Psychology, Research and Practice, 55(5), 426–435.
https://doi.org/10.1037/pro0000557
Andriessen, T. M., Horn, J., Franschman, G., van der Naalt, J., Haitsma, I.,
Jacobs, B., Steyerberg, E. W., & Vos, P. E. (2011). Epidemiology, severity
classification, and outcome of moderate and severe traumatic brain injury:
A prospective multicenter study. Journal of Neurotrauma, 28(10), 2019–
2031. https://doi.org/10.1089/neu.2011.2034
Armistead-Jehle, P., & Buican, B. (2013). Comparison of select advanced
clinical solutions embedded Effort measures to the Word Memory Test in
the detection of suboptimal effort. Archives of Clinical Neuropsychology,
28(3), 297–301. https://doi.org/10.1093/arclin/act017
Bianchini, K. J., Curtis, K. L., & Greve, K. W. (2006). Compensation
and malingering in traumatic brain injury: A dose–response relationship?
The Clinical Neuropsychologist, 20(4), 831–847. https://doi.org/10.1080/
13854040600875203
Bolla-Wilson, K., & Bleecker, M. L. (1986). Influence of verbal intelligence,
sex, age, and education on the Rey Auditory Verbal Learning Test.
Developmental Neuropsychology, 2(3), 203–211. https://doi.org/10.1080/
87565648609540342
Bortnik, K. E., & Dean, A. C. (2021). Performance validity testing in
patients with dementia. In K. B. Boone (Ed.), Assessment of feigned
cognitive impairment: A neuropsychological perspective (pp. 481–503).
Guilford Press.
Brantuo, M. A., An, K., Biss, R. K., Ali, S., & Erdodi, L. A. (2022).
Neurocognitive profiles associated with limited English proficiency in
cognitively intact adults. Archives of Clinical Neuropsychology, 37(7),
1579–1600. https://doi.org/10.1093/arclin/acac019
Chafetz, M., & Underhill, J. (2013). Estimated costs of malingered disability.
Archives of Clinical Neuropsychology, 28(7), 633–639. https://doi.org/10
.1093/arclin/act038
Chafetz, M. D. (2008). Malingering on the social security disability con-
sultative exam: Predictors and base rates. The Clinical Neuropsychologist,
22(3), 529–546. https://doi.org/10.1080/13854040701346104
Crişan, I. (2023). English versus native language administration of the IOP-
29-M produces similar results in a sample of Romanian bilinguals: A brief
report. Psychology & Neuroscience, 16(3), 254–260. https://doi.org/10
.1037/pne0000316
Crișan, I., Ali, S., Cutler, L., Matei, A., Avram, L., & Erdodi, L. A. (2023).
Geographic variability in limited English proficiency: A cross-cultural study
of cognitive profiles. Journal of the International Neuropsychological
Society, 29(10), 972–983. https://doi.org/10.1017/S1355617723000280
Crişan, I., Sava, F. A., Maricuţoiu, L. P., Ciumăgeanu, M. D., Axinia, O.,
Gîrniceanu, L., & Ciotlăuş, L. (2022). Evaluation of various detection
strategies in the assessment of noncredible memory performance: Results
of two experimental studies. Assessment, 29(8), 1973–1984. https://
doi.org/10.1177/10731911211040105
Curtis, K. L., Greve, K. W., Bianchini, K. J., & Brennan, A. (2006). California
verbal learning test indicators of malingered neurocognitive dysfunction:
Sensitivity and specificity in traumatic brain injury. Assessment, 13(1),
46–61. https://doi.org/10.1177/1073191105285210
Cutler, L., Abeare, C. A., Messa, I., Holcomb, M., & Erdodi, L. A. (2022).
This will only take a minute: Time cutoffs are superior to accuracy cutoffs
on the forced choice recognition trial of the Hopkins Verbal Learning Test–
Revised. Applied Neuropsychology: Adult, 29(6), 1425–1439. https://
doi.org/10.1080/23279095.2021.1884555
Delis, D. C., Kramer, J. H., Kaplan, E., & Thompkins, B. A. O. (1987).
CVLT: California Verbal Learning Test-Adult Version: Manual.
Psychological corporation.
Denning, J. H. (2021). When 10 is enough: Errors on the first 10 items of the
Test of Memory Malingering (TOMMe10) and administration time predict
freestanding performance validity tests (PVTs) and underperformance
on memory measures. Applied Neuropsychology: Adult, 28(1), 35–47.
https://doi.org/10.1080/23279095.2019.1588122
Denning, J. H. (2023). When failing one performance validity test matters.
Applied Neuropsychology: Adult. Advance online publication. https://
doi.org/10.1080/23279095.2023.2285503
Erdodi, L. A. (2023a). Multivariate models of performance validity: The
Erdodi Index captures the dual nature of non-credible responding
(continuous and categorical). Assessment, 30(5), 1467–1485. https://
doi.org/10.1177/10731911221101910
Erdodi, L. A. (2023b). From “below chance” to “a single error is one too
many”: Evaluating various thresholds for invalid performance on two
forced choice recognition tests. Behavioral Sciences & the Law, 41(5),
445–462. https://doi.org/10.1002/bsl.2609
Erdodi, L. A. (2024). Seeing clearly in the twilight: The clinical and forensic
relevance of the Indeterminate/Borderline range in multivariate models of
performance validity testing. Psychological Injury and Law, 17(1), 12–33.
https://doi.org/10.1007/s12207-024-09496-6
Erdodi, L. A., Green, P., Sirianni, C., & Abeare, C. A. (2019). The myth
of high false positive rates on the Word Memory Test in mild TBI.
Psychological Injury and Law, 12(2), 155–169. https://doi.org/10.1007/
s12207-019-09356-8
Erdodi, L. A., Hurtubise, J. L., Charron, C., Dunn, A., Enache, A.,
McDermott, A., & Hirst, R. B. (2018). The D-KEFS Trails as performance
validity tests. Psychological Assessment, 30(8), 1082–1095. https://
doi.org/10.1037/pas0000561
Erdodi, L. A., Nussbaum, S., Sagar, S., Abeare, C. A., & Schwartz, E. S.
(2017). Limited English proficiency increases failure rates on performance validity tests with high verbal mediation. Psychological Injury and Law,
10(1), 96–103. https://doi.org/10.1007/s12207-017-9282-x
Erdodi, L. A., Tyson, B. T., Shahein, A. G., Lichtenstein, J. D., Abeare,
C. A., Pelletier, C. L., Zuccato, B. G., Kucharski, B., & Roth, R. M.
(2017). The power of timing: Adding a time-to-completion cutoff to the
Word Choice Test and Recognition Memory Test improves classification
accuracy. Journal of Clinical and Experimental Neuropsychology, 39(4),
369–383. https://doi.org/10.1080/13803395.2016.1230181
Frederick, R. I., & Speed, F. M. (2007). On the interpretation of below-
chance responding in forced choice tests. Assessment, 14(1), 3–11. https://
doi.org/10.1177/1073191106292009
Graver, C., & Green, P. (2022). Misleading conclusions about word memory
test results in multiple sclerosis (MS) by Loring and Goldstein (2019).
Applied Neuropsychology: Adult, 29(3), 315–323. https://doi.org/10.1080/
23279095.2020.1748035
Green, P. (2003). Green’s Word Memory Test. Green’s Publishing.
Green, P., & Flaro, L. (2015). Results from three performance validity tests
(PVTs) in adults with intellectual disability. Applied Neuropsychology:
Adult, 22(4), 293–303. https://doi.org/10.1080/23279095.2014.92
5903
Green, P., Flaro, L., & Courtney, J. (2009). Examining false positives on
the Word Memory Test in adults with mild traumatic brain injury. Brain
Injury, 23(9), 741–750. https://doi.org/10.1080/02699050903133962
Greer, N., Sayer, N. A., Spoont, M., Taylor, B. C., Ackland, P. E.,
MacDonald, R., McKenzie, L., Rosebush, C., & Wilt, T. J. (2020).
Prevalence and severity of psychiatric disorders and suicidal behavior in
service members and veterans with and without traumatic brain injury:
Systematic review. The Journal of Head Trauma Rehabilitation, 35(1),
1–13. https://doi.org/10.1097/HTR.0000000000000478
Greve, K. W., Bianchini, K. J., & Doane, B. M. (2006). Classification
accuracy of the test of memory malingering in traumatic brain injury:
Results of a known-groups analysis. Journal of Clinical and Experimental
Neuropsychology, 28(7), 1176–1190. https://doi.org/10.1080/138033905
00263550
Greve, K. W., Bianchini, K. J., Etherton, J. L., Meyers, J. E., Curtis, K. L.,
& Ord, J. S. (2010). The Reliable Digit Span test in chronic pain:
Classification accuracy in detecting malingered pain-related disability.
The Clinical Neuropsychologist, 24(1), 137–152. https://doi.org/10
.1080/13854040902927546
Greve, K. W., Bianchini, K. J., Mathias, C. W., Houston, R. J., & Crouch,
J. A. (2002). Detecting malingered neurocognitive dysfunction with the
Wisconsin Card Sorting Test: A preliminary investigation in traumatic
brain injury. The Clinical Neuropsychologist, 16(2), 179–191. https://
doi.org/10.1076/clin.16.2.179.13241
Greve, K. W., Curtis, K. L., Bianchini, K. J., & Ord, J. S. (2009). Are the
original and second edition of the California Verbal Learning Test equally
accurate in detecting malingering? Assessment, 16(3), 237–248. https://
doi.org/10.1177/1073191108326227
Greve, K. W., Ord, J., Curtis, K. L., Bianchini, K. J., & Brennan, A. (2008).
Detecting malingering in traumatic brain injury and chronic pain: A
comparison of three forced-choice symptom validity tests. The Clinical
Neuropsychologist, 22(5), 896–918. https://doi.org/10.1080/1385404
0701565208
Hand, D. J. (2009). Measuring classifier performance: A coherent alternative
to the area under the ROC curve. Machine Learning, 77(1), 103–123.
https://doi.org/10.1007/s10994-009-5119-5
Heaton, R. K., Miller, S. W., Taylor, M. J., & Grant, I. (2004). Revised
comprehensive norms for an expanded Halstead-Reitan battery:
Demographically adjusted neuropsychological norms for African
American and Caucasian adults. Psychological Assessment Resources.
Heinly, M. T., Greve, K. W., Bianchini, K., Love, J. M., & Brennan, A.
(2005). WAIS digit-span-based indicators of malingered neurocognitive
dysfunction: Classification accuracy in traumatic brain injury. Assessment,
12(4), 429–444. https://doi.org/10.1177/1073191105281099
Hermann, B. P., Connell, B., Barr, W. B., & Wyler, A. R. (1995). The utility
of the Warrington Recognition Memory Test for temporal lobe epilepsy:
Pre- and postoperative results. Journal of Epilepsy, 8(2), 139–145. https://
doi.org/10.1016/0896-6974(95)00022-6
Hill, A. B. (1965). The environment and disease: Association or causation?
Proceedings of the Royal Society of Medicine, 58(5), 295–300. https://
doi.org/10.1177/003591576505800503
Hirnstein, M., Stuebs, J., Moè, A., & Hausmann, M. (2023). Sex/gender
differences in verbal fluency and verbal-episodic memory: A meta-
analysis. Perspectives on Psychological Science, 18(1), 67–90. https://
doi.org/10.1177/17456916221082116
Iverson, G. L., & Franzen, M. D. (1994). The recognition memory test,
digit span, and Knox cube test as markers of malingered memory
impairment. Assessment, 1(4), 323–334. https://doi.org/10.1177/10731
9119400100401
Kim, M. S., Boone, K. B., Victor, T., Marion, S. D., Amano, S., Cottingham,
M. E., Ziegler, E. A., & Zeller, M. A. (2010). The Warrington Recognition
Memory Test for words as a measure of response bias: Total score and
response time cutoffs developed on “real world” credible and noncredible
subjects. Archives of Clinical Neuropsychology, 25(1), 60–70. https://
doi.org/10.1093/arclin/acp088
Kim, M. S., Torres, K., Kang, H. J., & Drane, D. L. (2023). Specificity
of performance validity tests in patients with confirmed epilepsy. The
Clinical Neuropsychologist, 37(7), 1530–1547. https://doi.org/10.1080/
13854046.2022.2127424
Kljajevic, V., Evensmoen, H. R., Sokołowski, D., Pani, J., Hansen, T. I., &
Håberg, A. K. (2023). Female advantage in verbal learning revisited:
A HUNT study. Memory, 31(6), 831–849. https://doi.org/10.1080/0965
8211.2023.2203431
Kramer, J. H., Yaffe, K., Lengenfelder, J., & Delis, D. C. (2003). Age
and gender interactions on verbal memory performance. Journal of the
International Neuropsychological Society, 9(1), 97–102. https://doi.org/
10.1017/S1355617703910113
Lamberty, G. J., Nakase-Richardson, R., Farrell-Carnahan, L., McGarity,
S., Bidelspach, D., Harrison-Felix, C., & Cifu, D. X. (2014).
Development of a traumatic brain injury model system within the
Department of Veterans Affairs Polytrauma System of Care. The Journal
of Head Trauma Rehabilitation, 29(3), E1–E7. https://doi.org/10.1097/
HTR.0b013e31829a64d1
Larochette, A. C., & Harrison, A. G. (2012). Word memory test performance
in Canadian adolescents with learning disabilities: A preliminary study.
Applied Neuropsychology: Child, 1(1), 38–47. https://doi.org/10.1080/
21622965.2012.665777
Larrabee, G. J., Millis, S. R., & Meyers, J. E. (2009). 40 plus or minus 10, a
new magical number: Reply to Russell. The Clinical Neuropsychologist,
23(5), 841–849. https://doi.org/10.1080/13854040902796735
Lewin, C., Wolgers, G., & Herlitz, A. (2001). Sex differences favoring women
in verbal but not in visuospatial episodic memory. Neuropsychology, 15(2),
165–173. https://doi.org/10.1037/0894-4105.15.2.165
Lichtenstein, J. D., Greenacre, M. K., Cutler, L., Abeare, K., Baker, S. D.,
Kent, K. J., Ali, S., & Erdodi, L. A. (2019). Geographic variation and
instrumentation artifacts: In search of confounds in performance validity
assessment in adults with mild TBI. Psychological Injury and Law, 12(2),
127–145. https://doi.org/10.1007/s12207-019-09354-w
Lupu, T., Elbaum, T., Wagner, M., & Braw, Y. (2018). Enhanced detection
of feigned cognitive impairment using per item response time measure-
ments in the Word Memory Test. Applied Neuropsychology: Adult, 25(6),
532–542. https://doi.org/10.1080/23279095.2017.1341410
Malec, J. F., Brown, A. W., Leibson, C. L., Flaada, J. T., Mandrekar, J. N.,
Diehl, N. N., & Perkins, P. K. (2007). The mayo classification system for traumatic brain injury severity. Journal of Neurotrauma, 24(9), 1417–
1424. https://doi.org/10.1089/neu.2006.0245
Martin, P. K., & Schroeder, R. W. (2014). Chance performance and floor
effects: Threats to the validity of the Wechsler Memory Scale—Fourth
edition designs subtest. Archives of Clinical Neuropsychology, 29(4),
385–390. https://doi.org/10.1093/arclin/acu015
Martin, P. K., & Schroeder, R. W. (2020). Base rates of invalid test
performance across clinical non-forensic contexts and settings. Archives
of Clinical Neuropsychology, 35(6), 717–725. https://doi.org/10.1093/
arclin/acaa017
Martin, P. K., Schroeder, R. W., & Odland, A. P. (2015). Neuropsychologists’
validity testing beliefs and practices: A survey of North American
Professionals. The Clinical Neuropsychologist, 29(6), 741–776. https://
doi.org/10.1080/13854046.2015.1087597
Martin, P. K., Schroeder, R. W., & Odland, A. P. (2025).
Neuropsychological validity assessment beliefs and practices: A survey
of North American neuropsychologists and validity assessment experts.
Archives of Clinical Neuropsychology, 40(2), 201–223. https://doi.org/
10.1093/arclin/acae102
Messa, I., Holcomb, M., Lichtenstein, J., Tyson, B., Roth, R., & Erdodi, L.
(2022). They are not destined to fail: A systematic examination of scores
on embedded performance validity indicators in patients with intellectual
disability. The Australian Journal of Forensic Sciences, 54(5), 664–680.
https://doi.org/10.1080/00450618.2020.1865457
Millis, S. R. (1992). The Recognition Memory Test in the detection of
malingered and exaggerated memory deficits. Clinical Neuropsychologist,
6(4), 406–414. https://doi.org/10.1080/13854049208401867
Millis, S. R. (1994). Assessment of motivation and memory with the
Recognition Memory Test after financially compensable mild head injury.
Journal of Clinical Psychology, 50(4), 601–605. https://doi.org/10.2466/
pms.1994.79.1.384
Naugle, R. I., Chelune, G. J., Schuster, J., Lüders, H. O., & Comair, Y.
(1994). Recognition memory for words and faces before and after tem-
poral lobectomy. Assessment, 1(4), 373–381. https://doi.org/10.1177/
107319119400100406
O’Bryant, S. E., Hilsabeck, R. C., McCaffrey, R. J., & Drew Gouvier, W.
(2003). The Recognition Memory Test Examination of ethnic differences
and norm validity. Archives of Clinical Neuropsychology, 18(2), 135–143.
https://doi.org/10.1093/arclin/18.2.135
Parsons, J., Rodrigues, N. B., & Erdodi, L. A. (2024). The classification
accuracy of Warrington’s recognition memory test (words) as a performance
validity Test in a neurorehabilitation setting. Applied Neuropsychology:
Adult. Advance online publication. https://doi.org/10.1080/23279095.2024
.2337130
Popper, K. (1963). Conjectures and Refutations: The Growth of Scientific
Knowledge. Routledge.
Proto, D. A., Pastorek, N. J., Miller, B. I., Romesser, J. M., Sim, A. H., &
Linck, J. F. (2014). The dangers of failing one or more performance
validity tests in individuals claiming mild traumatic brain injury-related
postconcussive symptoms. Archives of Clinical Neuropsychology, 29(7),
614–624. https://doi.org/10.1093/arclin/acu044
Rai, J., Gervais, R., & Erdodi, L. (2023). A large-scale investigation of the
classification accuracy of various performance validity tests in a medical-
legal setting. Psychology & Neuroscience, 16(3), 225–243. https://doi.org/
10.1037/pne0000320
Richman, J., Green, P., Gervais, R., Flaro, L., Merten, T., Brockhaus, R., &
Ranks, D. (2006). Objective tests of symptom exaggeration in independent
medical examinations. Journal of Occupational and Environmental
Medicine, 48(3), 303–311. https://doi.org/10.1097/01.jom.0000183482
.41957.c3
Roor, J. J., Peters, M. J. V., Dandachi-FitzGerald, B., & Ponds,
R. W. H. M. (2024). Performance validity test failure in the clinical
population: A systematic review and meta-analysis of prevalence rates.
Neuropsychology Review, 34(1), 299–319. https://doi.org/10.1007/
s11065-023-09582-7
Rowland, J. A., Miskey, H. M., Brearly, T. W., Martindale, S. L., & Shura,
R. D. (2017). Word Memory Test performance across cognitive domains,
psychiatric presentations, and mild traumatic brain injury. Archives of
Clinical Neuropsychology, 32(3), 306–315. https://doi.org/10.1093/arcli
n/acw107
Silverberg, N. D., Iverson, G. L., Cogan, A., Dams, O. C. K., Delmonico, R.,
Graf, M. J. P., Iaccarino, M. A., Kajankova, M., Kamins, J., McCulloch,
K. L., McKinney, G., Nagele, D., Panenka, W. J., Rabinowitz, A. R.,
Reed, N., Wethe, J. V., Whitehair, V., Anderson, V., Arciniegas, D. B., …
Zemek, R. (2023). The American congress of rehabilitation medicine
diagnostic criteria for mild traumatic brain injury. Archives of Physical
Medicine and Rehabilitation, 104(8), 1343–1355. https://doi.org/10.1016/
j.apmr.2023.03.036
Steffens, T., Steffens, L. M., & Marcrum, S. C. (2020). Chance-level hit
rates in closed-set, forced-choice audiometry and a novel utility for the
significance test-based detection of malingering. PLOS ONE, 15(4),
Article e0231715. https://doi.org/10.1371/journal.pone.0231715
Sundermann, E. E., Maki, P. M., Rubin, L. H., Lipton, R. B., Landau, S.,
Biegon, A., & the Alzheimer’s Disease Neuroimaging Initiative. (2016).
Female advantage in verbal memory: Evidence of sex-specific cognitive
reserve. Neurology, 87(18), 1916–1924. https://doi.org/10.1212/WNL
.0000000000003288
Temple, C. M., & Cornish, K. M. (1993). Recognition memory for words and
faces in schoolchildren: A female advantage for words. British Journal
of Developmental Psychology, 11(4), 421–426. https://doi.org/10.1111/
j.2044-835X.1993.tb00613.x
Toth, A. J., & Campbell, M. J. (2021). Reply to: “concerns about cognitive
performance at chance level”. Scientific Reports, 11(1), Article 15536.
https://doi.org/10.1038/s41598-021-93954-7
Trueblood, W. (1994). Qualitative and quantitative characteristics of
malingered and other invalid WAIS-R and clinical memory data. Journal
of Clinical and Experimental Neuropsychology, 16(4), 597–607. https://
doi.org/10.1080/01688639408402671
Tyson, B. T., & Shahein, A. (2023). Combining accuracy scores with
time cutoffs improves the specificity of the Word Choice Test.
Psychology & Neuroscience, 16(3), 244–253. https://doi.org/10.1037/
pne0000315
Uiterwijk, D., Wong, D., Stargatt, R., & Crowe, S. F. (2021). Performance and
symptom validity testing in neuropsychological assessments in Australia:
A survey of practises and beliefs. Australian Psychologist, 56(5), 355–371.
https://doi.org/10.1080/00050067.2021.1948797
Vakil, E., Greenstein, Y., & Blachstein, H. (2010). Normative data for
composite scores for children and adults derived from the Rey Auditory
Verbal Learning Test. The Clinical Neuropsychologist, 24(4), 662–677.
https://doi.org/10.1080/13854040903493522
van Baalen, B., Odding, E., Maas, A. I., Ribbers, G. M., Bergen, M. P., &
Stam, H. J. (2003). Traumatic brain injury: Classification of initial severity
and determination of functional outcome. Disability and Rehabilitation,
25(1), 9–18. https://doi.org/10.1080/713813430
Victor, T. L., & Boone, K. B. (2021). Identification of feigned intellectual
disability. In K. B. Boone (Ed.), Assessment of feigned cognitive impairment.
A neuropsychological perspective (pp. 453–480). Guilford Press.
Votruba, K. L., Rykulski, N., Dumitrescu, C., & Abeare, C. A. (2020).
Handedness and performance validity test performance. Psychology &
Neuroscience, 13(2), 196–205. https://doi.org/10.1037/pne0000188
Wald, N. J., & Bestwick, J. P. (2014). Is the area under an ROC curve a
valid measure of the performance of a screening or diagnostic test?
Journal of Medical Screening, 21(1), 51–56. https://doi.org/10.1177/
0969141313517497
Warrington, E. K. (1984). Recognition Memory Test manual. NFERNelson.
Zelinski, E. M., Gilewski, M. J., & Schaie, K. W. (1993). Individual dif-
ferences in cross-sectional and 3-year longitudinal memory performance
across the adult life span. Psychology and Aging, 8(2), 176–186. https://
doi.org/10.1037/0882-7974.8.2.176
Zuccato, B. G., Tyson, B. T., & Erdodi, L. A. (2018). Early bird fails the PVT?
The effects of timing artifacts on performance validity tests. Psychological
Assessment, 30(11), 1491–1498. https://doi.org/10.1037/pas0000596"""

test2 = """Andersen, S. L. (2014). Episodic memory and executive function in familial
longevity (Publication No. 3627457) (Doctoral dissertation, Boston
University). ProQuest Dissertations & Theses Global.
Andersen, S. L. (2020). Centenarians as models of resistance and resilience
to Alzheimer’s disease and related dementias. Advances in Geriatric
Medicine and Research, 2(3), Article e200018. https://doi.org/10.20900/
agmr20200018
Andersen, S. L., Du, M., Cosentino, S., Schupf, N., Rosso, A. L., Perls, T. T.,
Sebastiani, P., & the Long Life Family Study. (2022). Slower decline in
processing speed is associated with familial longevity. Gerontology,
68(1), 17–29. https://doi.org/10.1159/000514950
Andersen, S. L., Sweigart, B., Sebastiani, P., Drury, J., Sidlowski, S., &
Perls, T. T. (2019). Reduced prevalence and incidence of cognitive
impairment among centenarian offspring. The Journals of Gerontology:
Series A: Biological Sciences and Medical Sciences, 74(1), 108–113.
https://doi.org/10.1093/gerona/gly141
Andresen, E. M., Malmgren, J. A., Carter, W. B., & Patrick, D. L. (1994).
Screening for depression in well older adults: Evaluation of a short form of
the CES-D (Center for Epidemiologic Studies Depression Scale).
American Journal of Preventive Medicine, 10(2), 77–84. https://doi.org/10
.1016/S0749-3797(18)30622-6
Appelbaum, M., Cooper, H., Kline, R. B., Mayo-Wilson, E., Nezu, A. M., &
Rao, S. M. (2018). Journal article reporting standards for quantitative
research in psychology: The APA Publications and Communications
Board task force report. American Psychologist, 73(1), 3–25. https://
doi.org/10.1037/amp0000191
Baltes, P. B., Staudinger, U. M., & Lindenberger, U. (1999). Lifespan
psychology: Theory and application to intellectual functioning. Annual
Review of Psychology, 50(1), 471–507. https://doi.org/10.1146/annurev
.psych.50.1.471
Barral, S., Cosentino, S., Costa, R., Andersen, S. L., Christensen, K., Eckfeldt,
J. H., Newman, A. B., Perls, T. T., Province, M. A., Hadley, E. C., Rossi,
W. K., Mayeux, R., & Long Life Family Study. (2013). Exceptional memory
performance in the Long Life Family Study. Neurobiology of Aging, 34(11),
2445–2448. https://doi.org/10.1016/j.neurobiolaging.2013.05.002
Barral, S., Cosentino, S., Costa, R., Matteini, A., Christensen, K., Andersen,
S. L., Glynn, N. W., Newman, A. B., & Mayeux, R. (2012). Cognitive
function in families with exceptional survival. Neurobiology of Aging, 33(3),
619.e1–619.e7. https://doi.org/10.1016/j.neurobiolaging.2011.02.004
Borelli, W. V., Schilling, L. P., Radaelli, G., Ferreira, L. B., Pisani, L.,
Portuguez, M. W., & da Costa, J. C. (2018). Neurobiological findings
associated with high cognitive performance in older adults: A systematic
review. International Psychogeriatrics, 30(12), 1813–1825. https://
doi.org/10.1017/S1041610218000431
Brewster, P. W., Melrose, R. J., Marquine, M. J., Johnson, J. K., Napoles, A.,
MacKay-Brandt, A., Farias, S., Reed, B., & Mungas, D. (2014). Life
experience and demographic influences on cognitive function in older adults.
Neuropsychology, 28(6), 846–858. https://doi.org/10.1037/neu0000098

Caplan, Z., & Rabe, M. (2023). 2020 Census briefs, the older population:
2020. U.S. Census Bureau.
Chan, D., Shafto, M., Kievit, R., Matthews, F., Spink, M., Valenzuela, M.,
Henson, R. N., & the Cam-CAN. (2018). Lifestyle activities in mid-life
contribute to cognitive reserve in late-life, independent of education, occu-
pation, and late-life activities. Neurobiology of Aging, 70, 180–183. https://
doi.org/10.1016/j.neurobiolaging.2018.06.012
Christensen, H., Griffiths, K., Mackinnon, A., & Jacomb, P. (1997). A
quantitative review of cognitive deficits in depression and Alzheimer-type
dementia. Journal of the International Neuropsychological Society, 3(6),
631–651. https://doi.org/10.1017/S1355617797006310
Corwin, J., & Bylsma, F. W. (1993). Psychological examination of traumatic
encephalopathy. Clinical Neuropsychologist, 7(1), 3–21. https://doi.org/
10.1080/13854049308401883
Cosentino, S., Schupf, N., Christensen, K., Andersen, S. L., Newman, A., &
Mayeux, R. (2013). Reduced prevalence of cognitive impairment in
families with exceptional longevity. JAMA Neurology, 70(7), 867–874.
https://doi.org/10.1001/jamaneurol.2013.1959
Cotter, A., Kim, J., Semons-Booker, K., Sherman, K., Sparapani, R., & Whittle,
J. (2021). Influence of mid-life cognitive activity on cognitive function among
men aged 68 years or older. Aging Clinical and Experimental Research,
33(10), 2689–2694. https://doi.org/10.1007/s40520-021-01825-y
Cullati, S., Kliegel, M., & Widmer, E. (2018). Development of reserves over
the life course and onset of vulnerability in later life. Nature Human
Behaviour, 2(8), 551–558. https://doi.org/10.1038/s41562-018-0395-3
Davidson, P. S., Cook, S. P., & Glisky, E. L. (2006). Flashbulb memories for
September 11th can be preserved in older adults. Aging, Neuropsychology,
and Cognition, 13(2), 196–206. https://doi.org/10.1080/13825580490904192
Davies, G., Harris, S. E., Reynolds, C. A., Payton, A., Knight, H. M.,
Liewald, D. C., Lopez, L. M., Luciano, M., Gow, A. J., Corley, J.,
Henderson, R., Murray, C., Pattie, A., Fox, H. C., Redmond, P., Lutz,
M. W., Chiba-Falek, O., Linnertz, C., Saith, S., … Deary, I. J. (2014). A
genome-wide association study implicates the APOE locus in non-
pathological cognitive ageing. Molecular Psychiatry, 19(1), 76–87.
https://doi.org/10.1038/mp.2012.159
Deary, I. J. (2012). Intelligence. Annual Review of Psychology, 63(1), 453–
482. https://doi.org/10.1146/annurev-psych-120710-100353
Deary, I. J., Yang, J., Davies, G., Harris, S. E., Tenesa, A., Liewald, D.,
Luciano, M., Lopez, L. M., Gow, A. J., Corley, J., Redmond, P., Fox,
H. C., Rowe, S. J., Haggarty, P., McNeill, G., Goddard, M. E., Porteous,
D. J., Whalley, L. J., Starr, J. M., … Visscher, P. M. (2012). Genetic
contributions to stability and change in intelligence from childhood to old
age. Nature, 482(7384), 212–215. https://doi.org/10.1038/nature10781
Delis, D. C., Kaplan, E., & Kramer, J. H. (2001). Delis–Kaplan executive
function system. The Psychological Corporation.
Delis, D. C., Kramer, J. H., Kaplan, E., & Ober, B. A. (2000). California Verbal
Learning Test-Second Edition (CVLT-II). Psychological Corporation.
Delpratt, N., Barzilai, N., Milman, S., Aleksic, S., Weiss, E., Verghese,
J., & Blumen, H. M. (2025). Gray matter covariance networks asso-
ciated with parental longevity—Results from the LonGenity study. The
Journals of Gerontology: Series A, 80(7), Article glaf066. https://
doi.org/10.1093/gerona/glaf066
Duffner, L. A., Deckers, K., Cadar, D., Steptoe, A., de Vugt, M., & Köhler, S.
(2022). The role of cognitive and social leisure activities in dementia risk:
Assessing longitudinal associations of modifiable and non-modifiable risk
factors. Epidemiology and Psychiatric Sciences, 31, Article e5. https://
doi.org/10.1017/S204579602100069X
Feher, E. P., Mahurin, R. K., Doody, R. S., Cooke, N., Sims, J., & Pirozzolo,
F. J. (1992). Establishing the limits of the Mini-Mental State. Examination
of ‘subtests’. Archives of Neurology, 49(1), 87–92. https://doi.org/10
.1001/archneur.1992.00530250091022
Finkel, D., Andel, R., & Pedersen, N. L. (2018). Gender differences in
longitudinal trajectories of change in physical, social, and cognitive/
sedentary leisure activities. The Journals of Gerontology: Series B, 73(8),
1491–1500. https://doi.org/10.1093/geronb/gbw116
Folstein, M. F., Folstein, S. E., McHugh, P. R., & Fanjiang, G. (2001). Mini-
mental state examination user’s guide. PsYchological Assessment Resources.
Gill, C. E., Jardine, R., & Martin, N. G. (1985). Further evidence for genetic
influences on educational achievement. British Journal of Educational
Psychology, 55(3), 240–250. https://doi.org/10.1111/j.2044-8279.1985
.tb02629.x
Glisky, E. L., Polster, M. R., & Routhieaux, B. C. (1995). Double disso-
ciation between item and source memory. Neuropsychology, 9(2), 229–
235. https://doi.org/10.1037/0894-4105.9.2.229
Greicius, M. D., Krasnow, B., Reiss, A. L., & Menon, V. (2003). Functional
connectivity in the resting brain: A network analysis of the default mode
hypothesis. Proceedings of the National Academy of Sciences, 100(1),
253–258. https://doi.org/10.1073/pnas.0135058100
Grodstein, F. (2012). How early can cognitive decline be detected? BMJ,
344(4), Article d7652. https://doi.org/10.1136/bmj.d7652
Hall, C. B., Derby, C., LeValley, A., Katz, M. J., Verghese, J., & Lipton,
R. B. (2007). Education delays accelerated decline on a memory test in
persons who develop dementia. Neurology, 69(17), 1657–1664. https://
doi.org/10.1212/01.wnl.0000278163.82636.30
Harada, C. N., Natelson Love, M. C., & Triebel, K. L. (2013). Normal
cognitive aging. Clinics in Geriatric Medicine, 29(4), 737–752. https://
doi.org/10.1016/j.cger.2013.07.002
Hilborn, J. V., Strauss, E., Hultsch, D. F., & Hunter, M. A. (2009).
Intraindividual variability across cognitive domains: Investigation of
dispersion levels and performance profiles in older adults. Journal of
Clinical and Experimental Neuropsychology, 31(4), 412–424. https://
doi.org/10.1080/13803390802232659
Hultsch, D. F., Hertzog, C., Dixon, R. A., & Small, B. J. (1998). Memory
change in the aged. Cambridge University Press.
Ihle, A., Gouveia, É. R., Gouveia, B. R., Orsholits, D., Oris, M., & Kliegel,
M. (2020). Solving the puzzle of cognitive reserve effects on cognitive
decline: The importance of considering functional impairment. Dementia
and Geriatric Cognitive Disorders, 49(4), 349–354. https://doi.org/10
.1159/000511768
Ihle, A., Oris, M., Fagot, D., Baeriswyl, M., Guichard, E., & Kliegel, M.
(2015). The association of leisure activities in middle adulthood with
cognitive performance in old age: The moderating role of educational
level. Gerontology, 61(6), 543–550. https://doi.org/10.1159/000381311
Kaplan, E., Goodglass, H., & Weintraub, S. (2001). Boston Naming Test
(2nd ed.). PRO-ED.
Kulminski, A. M., Raghavachari, N., Arbeev, K. G., Culminskaya, I., Arbeeva,
L., Wu, D., Ukraintseva, S. V., Christensen, K., & Yashin, A. I. (2016).
Protective role of the apolipoprotein E2 allele in age-related disease traits and
survival: Evidence from the Long Life Family Study. Biogerontology, 17(5–
6), 893–905. https://doi.org/10.1007/s10522-016-9659-3
Lachman, M. E., Agrigoroaei, S., Murphy, C., & Tun, P. A. (2010). Frequent
cognitive activity compensates for education differences in episodic
memory. The American Journal of Geriatric Psychiatry, 18(1), 4–10.
https://doi.org/10.1097/JGP.0b013e3181ab8b62
Lara, E., Martín-María, N., Miret, M., Olaya, B., Haro, J. M., & Ayuso-
Mateos, J. L. (2021). Is there a combined effect of depression and cog-
nitive reserve on cognitive function? Findings from a population-based
study. Psychology & Health, 37(9), 1132–1147. https://doi.org/10.1080/
08870446.2021.1927030
Li, X., Song, R., Qi, X., Xu, H., Yang, W., Kivipelto, M., Bennett, D. A., &
Xu, W. (2021). Influence of cognitive reserve on cognitive trajectories:
Role of brain pathologies. Neurology, 97(17), e1695–e1706. https://
doi.org/10.1212/WNL.0000000000012728
Maguire, E. A., Gadian, D. G., Johnsrude, I. S., Good, C. D., Ashburner, J.,
Frackowiak, R. S., & Frith, C. D. (2000). Navigation-related structural
change in the hippocampi of taxi drivers. Proceedings of the National
Academy of Sciences of the United States of America, 97(8), 4398–4403.
https://doi.org/10.1073/pnas.070039597
Martin, N. G., & Martin, P. G. (1975). The inheritance of scholastric abilities
in a sample of twins. I. Ascertainments of the sample and diagnosis of
zygosity. Annals of Human Genetics, 39(2), 213–218. https://doi.org/10
.1111/j.1469-1809.1975.tb00124.x
Matteini, A. M., Fallin, M. D., Kammerer, C. M., Schupf, N., Yashin, A. I.,
Christensen, K., Arbeev, K. G., Barr, G., Mayeux, R., Newman, A. B., &
Walston, J. D. (2010). Heritability estimates of endophenotypes of long and
health life: The Long Life Family Study. The Journals of Gerontology:
Series A: Biological Sciences and Medical Sciences, 65A(12), 1375–1379.
https://doi.org/10.1093/gerona/glq154
McClearn, G. E., Johansson, B., Berg, S., Pedersen, N. L., Ahern, F., Petrill,
S. A., & Plomin, R. (1997). Substantial genetic influence on cognitive
abilities in twins 80 or more years old. Science, 276(5318), 1560–1563.
https://doi.org/10.1126/science.276.5318.1560
Mehta, K. M., & Yeo, G. W. (2017). Systematic review of dementia
prevalence and incidence in United States race/ethnic populations.
Alzheimer’s & Dementia: The Journal of the Alzheimer’s Association,
13(1), 72–83. https://doi.org/10.1016/j.jalz.2016.06.2360
Montemurro, S., Rumiati, R. I., Pucci, V., Nucci, M., & Mondini, S. (2025).
Cognitive reserve can impact trajectories in ageing: A longitudinal study.
Aging Clinical and Experimental Research, 37(1), Article 93. https://
doi.org/10.1007/s40520-025-03000-z
Murabito, J. M., Beiser, A. S., Decarli, C., Seshadri, S., Wolf, P. A., & Au, R.
(2014). Parental longevity is associated with cognition and brain ageing in
middle-aged offspring. Age and Ageing, 43(3), 358–363. https://doi.org/
10.1093/ageing/aft175
Newman, A. B., Glynn, N. W., Taylor, C. A., Sebastiani, P., Perls, T. T.,
Mayeux, R., Christensen, K., Zmuda, J. M., Barral, S., Lee, J. H.,
Simonsick, E. M., Walston, J. D., Yashin, A. I., & Hadley, E. (2011). Health
and function of participants in the Long Life Family Study: A comparison
with other cohorts. Aging, 3(1), 63–76. https://doi.org/10.18632/aging
.100242
Nyberg, L., Lövdén, M., Riklund, K., Lindenberger, U., & Bäckman, L.
(2012). Memory aging and brain maintenance. Trends in Cognitive
Sciences, 16(5), 292–305. https://doi.org/10.1016/j.tics.2012.04.005
Nyborn, J. A., Himali, J. J., Beiser, A. S., Devine, S. A., Du, Y., Kaplan, E.,
O’Connor, M. K., Rinn, W. E., Denison, H. S., Seshadri, S., Wolf, P. A., &
Au, R. (2013). The Framingham Heart Study clock drawing performance:
Normative data from the offspring cohort. Experimental Aging Research,
39(1), 80–108. https://doi.org/10.1080/0361073X.2013.741996
Opdebeeck, C., Martyr, A., & Clare, L. (2016). Cognitive reserve and cognitive
function in healthy older people: A meta-analysis. Aging, Neuropsychology,
23(1), 40–60. https://doi.org/10.1080/13825585.2015.1041450
Park, D. C., Lautenschlager, G., Hedden, T., Davidson, N. S., Smith, A. D.,
& Smith, P. K. (2002). Models of visuospatial and verbal memory across
the adult life span. Psychology and Aging, 17(2), 299–320. https://doi.org/
10.1037/0882-7974.17.2.299
Park, D. C., & Reuter-Lorenz, P. (2009). The adaptive brain: Aging and
neurocognitive scaffolding. Annual Review of Psychology, 60(1), 173–
196. https://doi.org/10.1146/annurev.psych.59.103006.093656
Persson, J., Lustig, C., Nelson, J. K., & Reuter-Lorenz, P. A. (2007).
Age differences in deactivation: A link to cognitive control? Journal of
Cognitive Neuroscience, 19(6), 1021–1032. https://doi.org/10.1162/jo
cn.2007.19.6.1021
Petersen, S. E., van Mier, H., Fiez, J. A., & Raichle, M. E. (1998). The effects
of practice on the functional anatomy of task performance. Proceedings of
the National Academy of Sciences of the United States of America, 95(3),
853–860. https://doi.org/10.1073/pnas.95.3.853
Pettigrew, C., Nazarovs, J., Soldan, A., Singh, V., Wang, J., Hohman, T.,
Dumitrescu, L., Libby, J., Kunkle, B., Gross, A. L., Johnson, S., Lu, Q.,
Engelman, C., Masters, C. L., Maruff, P., Laws, S. M., Morris, J. C.,
Hassenstab, J., Cruchaga, C., … Albert, M. (2023). Alzheimer’s disease
genetic risk and cognitive reserve in relationship to long-term cognitive
trajectories among cognitively normal individuals. Alzheimer’s Research &
Therapy, 15(1), Article 66. https://doi.org/10.1186/s13195-023-01206-9
Plomin, R., DeFries, J. C., Knopik, V. S., & Neiderhiser, J. M. (2013).
Behavioral genetics (6th ed.). Worth Publishers.
Ponsoni, A., Damiani Branco, L., Cotrena, C., Milman Shansis, F., &
Fonseca, R. P. (2020). The effects of cognitive reserve and depressive
symptoms on cognitive performance in major depression and bipolar
disorder. Journal of Affective Disorders, 274, 813–818. https://doi.org/10
.1016/j.jad.2020.05.143
Powell, A., Page, Z. A., Close, J. C. T., Sachdev, P. S., & Brodaty, H. (2023).
Defining exceptional cognition in older adults: A systematic review of
cognitive super-ageing. International Journal of Geriatric Psychiatry,
38(12), Article e6034. https://doi.org/10.1002/gps.6034
Rajan, K. B., Weuve, J., Barnes, L. L., McAninch, E. A., Wilson, R. S., &
Evans, D. A. (2021). Population estimate of people with clinical
Alzheimer’s disease and mild cognitive impairment in the United States
(2020–2060). Alzheimer’s & Dementia: The Journal of the Alzheimer’s
Association, 17(12), 1966–1975. https://doi.org/10.1002/alz.12362
Saczynski, J. S., Jonsdottir, M. K., Sigurdsson, S., Eiriksdottir, G., Jonsson,
P. V., Garcia, M. E., Kjartansson, O., van Buchem, M. A., Gudnason, V.,
& Launer, L. J. (2008). White matter lesions and cognitive performance:
The role of cognitively complex leisure activity. The Journals of
Gerontology: Series A: Biological Sciences and Medical Sciences, 63(8),
848–854. https://doi.org/10.1093/gerona/63.8.848
Sajeev, G., Weuve, J., Jackson, J. W., VanderWeele, T. J., Bennett, D. A.,
Grodstein, F., & Blacker, D. (2016). Late-life cognitive activity and
dementia: A systematic review and bias analysis. Epidemiology, 27(5),
732–742. https://doi.org/10.1097/EDE.0000000000000513
Sala, G., Jopp, D., Gobet, F., Ogawa, M., Ishioka, Y., Masui, Y., Inagaki, H.,
Nakagawa, T., Yasumoto, S., Ishizaki, T., Arai, Y., Ikebe, K., Kamide, K.,
& Gondo, Y. (2019). The impact of leisure activities on older adults’
cognitive function, physical function, and mental health. PLOS ONE,
14(11), Article e0225006. https://doi.org/10.1371/journal.pone.0225006
Scarmeas, N., Albert, S. M., Manly, J. J., & Stern, Y. (2006). Education and
rates of cognitive decline in incident Alzheimer’s disease. Journal of
Neurology, Neurosurgery & Psychiatry, 77(3), 308–316. https://doi.org/
10.1136/jnnp.2005.072306
Schupf, N., Barral, S., Perls, T., Newman, A., Christensen, K., Thyagarajan,
B., Province, M., Rossi, W. K., & Mayeux, R. (2013). Apolipoprotein E
and familial longevity. Neurobiology of Aging, 34(4), 1287–1291. https://
doi.org/10.1016/j.neurobiolaging.2012.08.019
Sebastiani, P., Andersen, S. L., Sweigart, B., Du, M., Cosentino, S.,
Thyagarajan, B., Christensen, K., Schupf, N., & Perls, T. T. (2020).
Patterns of multi-domain cognitive aging in participants of the Long Life
Family Study. GeroScience, 42(5), 1335–1350. https://doi.org/10.1007/
s11357-020-00202-3
Sebastiani, P., Gurinovich, A., Nygaard, M., Sasaki, T., Sweigart, B., Bae, H.,
Andersen, S. L., Villa, F., Atzmon, G., Christensen, K., Arai, Y., Barzilai, N.,
Puca, A., Christiansen, L., Hirose, N., & Perls, T. T. (2019). APOE alleles
and extreme human longevity. The Journals of Gerontology: Series A:
Biological Sciences and Medical Sciences, 74(1), 44–51. https://doi.org/10
.1093/gerona/gly174
Sebastiani, P., Nussbaum, L., Andersen, S. L., Black, M. J., & Perls, T. T.
(2016). Increasing sibling relative risk of survival to older and older ages and
the importance of precise definitions of “aging,” “life span,” and “lon-
gevity”. The Journals of Gerontology: Series A: Biological Sciences and
Medical Sciences, 71(3), 340–346. https://doi.org/10.1093/gerona/glv020
Shors, T. J., Anderson, M. L., Curlik, D. M., II, & Nokia, M. S. (2012). Use it or
lose it: How neurogenesis keeps the brain fit for learning. Behavioural Brain
Research, 227(2), 450–458. https://doi.org/10.1016/j.bbr.2011.04.023
Singh-Manoux, A., Kivimaki, M., Glymour, M. M., Elbaz, A., Berr, C.,
Ebmeier, K. P., Ferrie, J. E., & Dugravot, A. (2012). Timing of onset of
cognitive decline: Results from Whitehall II prospective cohort study.
BMJ, 344(4), Article d7622. https://doi.org/10.1136/bmj.d7622
Small, B. J., Dixon, R. A., McArdle, J. J., & Grimm, K. J. (2012). Do changes
in lifestyle engagement moderate cognitive decline in normal aging?
Evidence from the Victoria Longitudinal Study. Neuropsychology, 26(2),
144–155. https://doi.org/10.1037/a0026579
Smart, E. L., Gow, A. J., & Deary, I. J. (2014). Occupational complexity and
lifetime cognitive abilities. Neurology, 83(24), 2285–2291. https://doi.org/
10.1212/WNL.0000000000001075
Sörman, D. E., Ljungberg, J. K., & Rönnlund, M. (2018). Reading habits
among older adults in relation to level and 15-year changes in verbal fluency
and episodic recall. Frontiers in Psychology, 9, Article 1872. https://doi.org/
10.3389/fpsyg.2018.01872
Steenland, K., Goldstein, F. C., Levey, A., & Wharton, W. (2016). A meta-
analysis of Alzheimer’s disease incidence and prevalence comparing
African-Americans and Caucasians. Journal of Alzheimer’s Disease,
50(1), 71–76. https://doi.org/10.3233/JAD-150778
Stern, R. A., Javorsky, D. J., Singer, E. A., Singer Harris, N. G., Somerville, J. A.,
Duke, L. M., Thompson, J. A., & Kaplan, E. (1999). The Boston Qualitative Scoring System for the Rey–Osterrieth Complex Figure: Professional manual.
Psychological Assessment Resources.
Stern, R. A., & White, T. (2003). Neuropsychological assessment battery:
Administration, scoring, and interpretation manual. Psychological
Assessment Resources.
Stern, Y. (2009). Cognitive reserve. Neuropsychologia, 47(10), 2015–2028.
https://doi.org/10.1016/j.neuropsychologia.2009.03.004
Stern, Y., Albert, M., Barnes, C. A., Cabeza, R., Pascual-Leone, A., & Rapp,
P. R. (2023). A framework for concepts of reserve and resilience in aging.
Neurobiology of Aging, 124, 100–103. https://doi.org/10.1016/j.neurobio
laging.2022.10.015
Stern, Y., Arenaza-Urquijo, E. M., Bartrés-Faz, D., Belleville, S., Cantilon,
M., Chetelat, G., Ewers, M., Franzmeier, N., Kempermann, G., Kremen,
W. S., Okonkwo, O., Scarmeas, N., Soldan, A., Udeh-Momoh, C.,
Valenzuela, M., Vemuri, P., Vuoksimaa, E., & the Reserve, Resilience and
Protective Factors PIA Empirical Definitions and Conceptual Frameworks
Workgroup. (2020). Whitepaper: Defining and investigating cognitive
reserve, brain reserve, and brain maintenance. Alzheimer’s & Dementia:
The Journal of the Alzheimer’s Association, 16(9), 1305–1311. https://
doi.org/10.1016/j.jalz.2018.07.219
Stevenson, M., Bae, H., Schupf, N., Andersen, S., Zhang, Q., Perls, T., &
Sebastiani, P. (2015). Burden of disease variants in participants of the
Long Life Family Study. Aging, 7(2), 123–132. https://doi.org/10.18632/
aging.100724
Stieger, M., & Lachman, M. E. (2021). Increases in cognitive activity reduce
aging-related declines in executive functioning. Frontiers in Psychiatry,
12, Article 708974. https://doi.org/10.3389/fpsyt.2021.708974
Stijntjes, M., de Craen, A. J., van Heemst, D., Meskers, C. G., van Buchem,
M. A., Westendorp, R. G., Slagboom, P. E., & Maier, A. B. (2013).
Familial longevity is marked by better cognitive performance at middle
age: The Leiden Longevity Study. PLOS ONE, 8(3), Article e57962.
https://doi.org/10.1371/journal.pone.0057962
Strauss, E., Sherman, E. M. S., & Spreen, O. (2006). A compendium of
neuropsychological tests: Administration, norms, and commentary (3rd
ed.). Oxford University Press.
Thorvaldsson, V., Skoog, I., & Johansson, B. (2017). IQ as moderator of
terminal decline in perceptual and motor speed, spatial, and verbal ability:
Testing the cognitive reserve hypothesis in a population-based sample
followed from age 70 until death. Psychology and Aging, 32(2), 148–157.
https://doi.org/10.1037/pag0000150
Tian, Q., Pilling, L. C., Atkins, J. L., Melzer, D., & Ferrucci, L. (2020). The
relationship of parental longevity with the aging brain-results from UK
Biobank. GeroScience, 42(5), 1377–1385. https://doi.org/10.1007/s11357-
020-00227-8
Tucker-Drob, E. M., Reynolds, C. A., Finkel, D., & Pedersen, N. L. (2014).
Shared and unique genetic and environmental influences on aging-related
changes in multiple cognitive abilities. Developmental Psychology, 50(1),
152–166. https://doi.org/10.1037/a0032468
Wang, S., & Blazer, D. G. (2015). Depression and cognition in the elderly.
Annual Review of Clinical Psychology, 11(1), 331–360. https://doi.org/10
.1146/annurev-clinpsy-032814-112828
Wang, Y., Wang, S., Zhu, W., Liang, N., Zhang, C., Pei, Y., Wang, Q., Li, S.,
& Shi, J. (2022). Reading activities compensate for low education-related
cognitive deficits. Alzheimer’s Research & Therapy, 14(1), Article 156.
https://doi.org/10.1186/s13195-022-01098-1
Wechsler, D. (1997). Wechsler Memory Scale (third edition manual). The
Psychological Corporation.
Weziak-Bialowolska, D., Bialowolski, P., & Sacco, P. L. (2023). Mind-
stimulating leisure activities: Prospective associations with health, well-
being, and longevity. Frontiers in Public Health, 11, Article 1117822.
https://doi.org/10.3389/fpubh.2023.1117822
Whitfield, K. E., Forrester, S., & Thorpe, R. J., Jr. (2019). A comparison of
variances in age cohorts to understand longevity in African Americans.
The Journals of Gerontology: Series A: Biological Sciences and Medical
Sciences, 74(Suppl_1), S27–S31. https://doi.org/10.1093/gerona/glz214
Wilson, R. S., Barnes, L. L., & Bennett, D. A. (2003). Assessment of lifetime
participation in cognitively stimulating activities. Journal of Clinical and
Experimental Neuropsychology, 25(5), 634–642. https://doi.org/10.1076/
jcen.25.5.634.14572
Wilson, R. S., Barnes, L. L., Krueger, K. R., Hoganson, G., Bienias, J. L., &
Bennett, D. A. (2005). Early and late life cognitive activity and cognitive
systems in old age. Journal of the International Neuropsychological
Society, 11(4), 400–407. https://doi.org/10.1017/S1355617705050459
Wilson, R. S., Bennett, D. A., Beckett, L. A., Morris, M. C., Gilley, D. W.,
Bienias, J. L., Scherr, P. A., & Evans, D. A. (1999). Cognitive activity in
older persons from a geographically defined population. The Journals of
Gerontology: Series B: Psychological Sciences and Social Sciences,
54B(3), P155–P160. https://doi.org/10.1093/geronb/54B.3.P155
Wilson, R. S., Boyle, P. A., Yu, L., Barnes, L. L., Schneider, J. A., &
Bennett, D. A. (2013). Life-span cognitive activity, neuropathologic
burden, and cognitive aging. Neurology, 81(4), 314–321. https://doi.org/
10.1212/WNL.0b013e31829c5e8a
Wilson, R. S., Rajan, K. B., Barnes, L. L., Weuve, J., & Evans, D. A. (2016).
Factors related to racial differences in late-life level of cognitive function.
Neuropsychology, 30(5), 517–524. https://doi.org/10.1037/neu0000290
Wilson, R. S., Wang, T., Yu, L., Grodstein, F., Bennett, D. A., & Boyle, P. A.
(2021). Cognitive activity and onset age of incident Alzheimer disease
dementia. Neurology, 97(9), e922–e929. https://doi.org/10.1212/WNL
.0000000000012388
Wilson, R. S., Yu, L., Lamar, M., Schneider, J. A., Boyle, P. A., & Bennett,
D. A. (2019). Education and cognitive reserve in old age. Neurology,
92(10), e1041–e1050. https://doi.org/10.1212/WNL.0000000000007036
Wojczynski, M. K., Jiuan Lin, S., Sebastiani, P., Perls, T. T., Lee, J.,
Kulminski, A., Newman, A., Zmuda, J. M., Christensen, K., & Province,
M. A. (2022). NIA long life family study: Objectives, design, and heri-
tability of cross-sectional and longitudinal phenotypes. The Journals of
Gerontology: Series A: Biological Sciences and Medical Sciences, 77(4),
717–727. https://doi.org/10.1093/gerona/glab333
Wu, Z., Woods, R. L., Wolfe, R., Storey, E., Chong, T. T. J., Shah, R. C.,
Orchard, S. G., McNeil, J. J., Murray, A. M., Ryan, J., & the ASPREE
Investigator Group. (2021). Trajectories of cognitive function in com-
munity-dwelling older adults: A longitudinal study of population het-
erogeneity. Alzheimer’s & Dementia: Diagnosis, Assessment & Disease
Monitoring, 13(1), Article e12180. https://doi.org/10.1002/dad2.12180
Xiang, Q., Andersen, S. L., Perls, T. T., & Sebastiani, P. (2021). Studying the
interplay between apolipoprotein E and education on cognitive decline in
centenarians using Bayesian beta regression. Frontiers in Genetics, 11,
Article 606831. https://doi.org/10.3389/fgene.2020.606831
Yang, X., Xu, X. Y., Guo, L., Zhang, Y., Wang, S. S., & Li, Y. (2022). Effect
of leisure activities on cognitive aging in older adults: A systematic review
and meta-analysis. Frontiers in Psychology, 13, Article 1080740. https://
doi.org/10.3389/fpsyg.2022.1080740
Zhu, C. E., Zhou, L., & Zhang, X. (2022). Effects of leisure activities on the
cognitive ability of older adults: A latent variable growth model analysis.
Frontiers in Psychology, 13, Article 838878. https://doi.org/10.3389/
fpsyg.2022.838878"""


test3 = """
Abe, M., Suzuki, K., Okada, K., Miura, R., Fujii, T., Etsurou, M., &
Yamadori, A. (2004). Normative data on tests for frontal lobe functions:
Trail Making Test, verbal fluency, Wisconsin Card Sorting Test (Keio
version). No to Shinkei, 56(7), 567–574.
Abrams, R. C., Lachs, M., McAvay, G., Keohane, D. J., & Bruce, M. L.
(2002). Predictors of self-neglect in community-dwelling elders. The
American Journal of Psychiatry, 159(10), 1724–1730. https://doi.org/10
.1176/appi.ajp.159.10.1724
Arciniegas, D. B., Held, K., & Wagner, P. (2002). Cognitive impairment
following traumatic brain injury. Current Treatment Options in
Neurology, 4(1), 43–57. https://doi.org/10.1007/s11940-002-0004-6
Barker-Collo, S., Bennett, D. A., Krishnamurthi, R. V., Parmar, P., Feigin,
V. L., Naghavi, M., Forouzanfar, M. H., Johnson, C. O., Nguyen, G.,
Mensah, G. A., Vos, T., Murray, C. J., Roth, G. A., the GBD 2013 Writing
Group, & the GBD 2013 Stroke Panel Experts Group. (2015). Sex dif-
ferences in stroke incidence, prevalence, mortality and disability-adjusted
life years: Results from the Global Burden of Disease Study 2013.
Neuroepidemiology, 45(3), 203–214. https://doi.org/10.1159/000441103
Barrash, J., Bruss, J., Anderson, S. W., Kuceyeski, A., Manzel, K., Tranel,
D., & Boes, A. D. (2022). Lesions in different prefrontal sectors are
associated with different types of acquired personality disturbances.
Cortex, 147, 169–184. https://doi.org/10.1016/j.cortex.2021.12.004
Bates, E., Wilson, S. M., Saygin, A. P., Dick, F., Sereno, M. I., Knight, R. T.,
& Dronkers, N. F. (2003). Voxel-based lesion-symptom mapping. Nature
Neuroscience, 6(5), 448–450. https://doi.org/10.1038/nn1050
Bathgate, D., Snowden, J. S., Varma, A., Blackshaw, A., & Neary, D. (2001).
Behaviour in frontotemporal dementia, Alzheimer’s disease and vascular
dementia. Acta Neurologica Scandinavica, 103(6), 367–378. https://
doi.org/10.1034/j.1600-0404.2001.2000236.x
Becerra, L. R., Breiter, H. C., Stojanovic, M., Fishman, S., Edwards, A., Comite,
A. R., Gonzalez, R. G., & Borsook, D. (1999). Human brain activation under
controlled thermal stimulation and habituation to noxious heat: An fMRI
study. Magnetic Resonance in Medicine, 41(5), 1044–1057. https://doi.org/10
.1002/(SICI)1522-2594(199905)41:5<1044::AID-MRM25>3.0.CO;2-M
Bechara, A., & Damasio, H. (2002). Decision-making and addiction (part
I): Impaired activation of somatic states in substance dependent in-
dividuals when pondering decisions with negative future consequences.
Neuropsychologia, 40(10), 1675–1689. https://doi.org/10.1016/S0028-
3932(02)00015-5
Bielak, A. A. M., Hatt, C. R., & Diehl, M. (2017). Cognitive performance in
adults’ daily lives: Is there a lab-life gap? Research in Human Development,
14(3), 219–233. https://doi.org/10.1080/15427609.2017.1340050
Bouchama, A., Dehbi, M., Mohamed, G., Matthies, F., Shoukri, M., &
Menne, B. (2007). Prognostic factors in heat wave–related deaths: A meta-
analysis. Archives of Internal Medicine, 167(20), 2170–2176. https://
doi.org/10.1001/archinte.167.20.ira70009
Brunner, E., & Munzel, U. (2000). The nonparametric Behrens-Fisher problem:
Asymptotic theory and a small-sample approximation. Biometrical Journal,
42(1), 17–25. https://doi.org/10.1002/(SICI)1521-4036(200001)42:1<17::
AID-BIMJ17>3.0.CO;2-U
Burgess, P. W., Alderman, N., Evans, J., Emslie, H., & Wilson, B. A. (1998).
The ecological validity of tests of executive function. Journal of the
International Neuropsychological Society, 4(6), 547–558. https://doi.org/
10.1017/S1355617798466037
Cicerone, K. D., Goldin, Y., Ganci, K., Rosenbaum, A., Wethe, J. V.,
Langenbahn, D. M., Malec, J. F., Bergquist, T. F., Kingsley, K., Nagele, D.,
Trexler, L., Fraas, M., Bogdanova, Y., & Harley, J. P. (2019). Evidence-
based cognitive rehabilitation: Systematic review of the literature from
2009 through 2014. Archives of Physical Medicine and Rehabilitation,
100(8), 1515–1533. https://doi.org/10.1016/j.apmr.2019.02.011
Clar, H. E. (1985). Disturbances of the hypothalamic thermoregulation. Acta
Neurochirurgica, 75(1–4), 106–112. https://doi.org/10.1007/BF01406330
Coon, E. A., & Low, P. A. (2018). Thermoregulation in Parkinson disease. In
A. A. Romanovsky (Ed.), Handbook of clinical neurology (Vol. 157, pp. 715–
725). Elsevier. https://doi.org/10.1016/B978-0-444-64074-1.00043-4
Cubelli, R. (2017). Definition: Spatial neglect. Cortex, 92, 320–321. https://
doi.org/10.1016/j.cortex.2017.03.021
Damasio, A. R. (1994). Descartes’ error: Emotion, reason and the human
brain. Putnam.
De Tanti, A., Gasperini, G., & Rossini, M. (2005). Paroxysmal episodic
hypothalamic instability with hypothermia after traumatic brain injury. Brain
Injury, 19(14), 1277–1283. https://doi.org/10.1080/02699050500309270
de Vetten, L., & Bocca, G. (2013). Systemic effects of hypothermia due to
hypothalamic dysfunction after resection of a craniopharyngioma: Case
report and review of literature. Neuropediatrics, 44(3), 159–162. https://
doi.org/10.1055/s-0032-1327773
Demakis, G. J. (2003). A meta-analytic review of the sensitivity of the
Wisconsin Card Sorting Test to frontal and lateralized frontal brain
damage. Neuropsychology, 17(2), 255–264. https://doi.org/10.1037/0894-
4105.17.2.255
DiMicco, J. A., & Zaretsky, D. V. (2007). The dorsomedial hypothalamus: A
new player in thermoregulation. American Journal of Physiology-
Regulatory, Integrative and Comparative Physiology, 292(1), R47–R63.
https://doi.org/10.1152/ajpregu.00498.2006
El-Gamal, N., & Frank, S. M. (1995). Perioperative thermoregulatory
dysfunction in a patient with a previous traumatic hypothalamic injury.
Anesthesia and Analgesia, 80(6), 1245–1247. https://doi.org/10.1097/
00000539-199506000-00032
Fellows, L. K., & Farah, M. J. (2007). The role of ventromedial prefrontal
cortex in decision making: Judgment under uncertainty or judgment per se?
Cerebral Cortex, 17(11), 2669–2674. https://doi.org/10.1093/cercor/bhl176
Fletcher, P. D., Downey, L. E., Golden, H. L., Clark, C. N., Slattery, C. F.,
Paterson, R. W., Rohrer, J. D., Schott, J. M., Rossor, M. N., & Warren,
J. D. (2015). Pain and temperature processing in dementia: A clinical and
neuroanatomical analysis. Brain, 138(11), 3360–3372. https://doi.org/10
.1093/brain/awv276
Fong, H., Zheng, J., & Kurrasch, D. (2023). The structural and functional
complexity of the integrative hypothalamus. Science, 382(6669), 388–
394. https://doi.org/10.1126/science.adh8488
Fricke, C., & Voderholzer, U. (2023). Endocrinology of underweight and
anorexia nervosa. Nutrients, 15(16), Article 3509. https://doi.org/10.3390/
nu15163509
Funayama, M., Koreki, A., Takata, T., Nakagawa, Y., & Mimura, M. (2024).
Post-stroke urinary incontinence is associated with behavior control
deficits and overactive bladder. Neuropsychologia, 201, Article 108942.
https://doi.org/10.1016/j.neuropsychologia.2024.108942
Funayama, M., Mimura, M., Koshibe, Y., & Kato, Y. (2010). Squalor
syndrome after focal orbitofrontal damage. Cognitive and Behavioral
Neurology, 23(2), 135–139. https://doi.org/10.1097/WNN.0b013e
3181d746ba
Gonzalez-Escamilla, G., Chirumamilla, V. C., Meyer, B., Bonertz, T., von
Grotthus, S., Vogt, J., Stroh, A., Horstmann, J. P., Tüscher, O., Kalisch, R.,
Muthuraman, M., & Groppa, S. (2018). Excitability regulation in the
dorsomedial prefrontal cortex during sustained instructed fear responses:
A TMS-EEG study. Scientific Reports, 8(1), Article 14506. https://doi.org/
10.1038/s41598-018-32781-9
Gowda, R., Jaffa, M., & Badjatia, N. (2018). Thermoregulation in brain
injury. In A. A. Romanovsky (Ed.), Handbook of clinical neurology (Vol.
157, pp. 789–797). Elsevier. https://doi.org/10.1016/B978-0-444-64074-1
.00049-5
Grafman, J., Schwab, K., Warden, D., Pridgen, A., Brown, H. R., & Salazar,
A. M. (1996). Frontal lobe injuries, violence, and aggression: A report of
the Vietnam Head Injury Study. Neurology, 46(5), 1231–1238. https://
doi.org/10.1212/WNL.46.5.1231
Haller, S., Kovari, E., Herrmann, F. R., Cuvinciuc, V., Tomm, A. M., Zulian,
G. B., Lovblad, K. O., Giannakopoulos, P., & Bouras, C. (2013). Do brain
T2/FLAIR white matter hyperintensities correspond to myelin loss in
normal aging? A radiologic-neuropathologic correlation study. Acta
Neuropathologica Communications, 1, Article 14. https://actaneuroco
mms.biomedcentral.com/articles/10.1186/2051-5960-1-14#citeas
Hornberger, M., Yew, B., Gilardoni, S., Mioshi, E., Gleichgerrcht, E.,
Manes, F., & Hodges, J. R. (2014). Ventromedial-frontopolar prefrontal
cortex atrophy correlates with insight loss in frontotemporal dementia and
Alzheimer’s disease. Human Brain Mapping, 35(2), 616–626. https://
doi.org/10.1002/hbm.22200
Ideno, Y., Takayama, M., Hayashi, K., Takagi, H., & Sugai, Y. (2012).
Evaluation of a Japanese version of the Mini-Mental State Examination in
elderly persons. Geriatrics & Gerontology International, 12(2), 310–316.
https://doi.org/10.1111/j.1447-0594.2011.00772.x
Imai, Y., & Hasegawa, K. (1994). The Revised Hasegawa’s Dementia Scale
(HDS-R)—Evaluation of its usefulness as a screening test for dementia.
Journal of the Hong Kong College of Psychiatrists, 4(Suppl. 2), 20–24. https://
www.easap.asia/index.php/advanced-search/item/503-v4n2-9402-p20-24
Jang, W., Sohn, Y., Park, J. H., Pai, H., Kim, D. S., & Kim, B. (2021).
Clinical characteristics of patients with adrenal insufficiency and fever.
Journal of Korean Medical Science, 36(23), Article e152. https://doi.org/
10.3346/jkms.2021.36.e152
Kado, Y., Sanada, S., Yanagihara, M., Ogino, T., Abiru, K., & Nakano, K.
(2004). Effect of development and aging on the modified Wisconsin Card
Sorting Test in normal subjects. No to Hattatsu, 36(6), 475–480.
Karnath, H. O., Sperber, C., Wiesen, D., & de Haan, B. (2019). Lesion-
behavior mapping in cognitive neuroscience: A practical guide to uni-
variate and multivariate approaches. In S. Pollmann (Ed.), Spatial learning
and attention guidance (pp. 209–238). Humana Press. https://doi.org/10
.1007/7657_2019_18
Kashima, H. (2003). The Japanese version of behavioural assessment of the
dysexecutive syndrome. Shinko Igaku Shuppansha.
Kashima, H., & Kato, M. (1995). Wisconsin Card Sorting Test (Keio
version). Brain Science and Mental Disorders, 6, 209–216.
Katoh, S., Shimogaki, H., Onodera, A., Ueda, H., Oikawa, K., Ikeda, K.,
Ueda-Ishibashi, H., Kosaka, K., Imai, K., & Hasegawa, K. (1991).
Development of the Revised Version of Hasegawa’s Dementia Scale
(HDS-R). Journal of Geriatric Psychiatry, 2, 1339–1347.
Kibayashi, K., & Shojo, H. (2003). Accidental fatal hypothermia in elderly
people with Alzheimer’s disease. Medicine, Science, and the Law, 43(2),
127–131. https://doi.org/10.1258/rsmmsl.43.2.127
Knoch, D., & Fehr, E. (2007). Resisting the power of temptations: The right
prefrontal cortex and self-control. Annals of the New York Academy of
Sciences, 1104(1), 123–134. https://doi.org/10.1196/annals.1390.004
Kong, J., White, N. S., Kwong, K. K., Vangel, M. G., Rosman, I. S., Gracely,
R. H., & Gollub, R. L. (2006). Using fMRI to dissociate sensory encoding
from cognitive evaluation of heat pain intensity. Human Brain Mapping,
27(9), 715–721. https://doi.org/10.1002/hbm.20213
Kothari, R. U., Brott, T., Broderick, J. P., Barsan, W. G., Sauerbeck, L. R.,
Zuccarello, M., & Khoury, J. (1996). The ABCs of measuring intrace-
rebral hemorrhage volumes. Stroke, 27(8), 1304–1305. https://doi.org/10
.1161/01.str.27.8.1304
Kugo, A., Terada, S., Ata, T., Ido, Y., Kado, Y., Ishihara, T., Hikiji, M.,
Fujisawa, Y., Sasaki, K., & Kuroda, S. (2007). Japanese version of the
Frontal Assessment Battery for dementia. Psychiatry Research, 153(1),
69–75. https://doi.org/10.1016/j.psychres.2006.04.004
Luby, M., Hong, J., Merino, J. G., Lynch, J. K., Hsia, A. W., Magadán, A.,
Song, S. S., Latour, L. L., & Warach, S. (2013). Stroke mismatch volume
with the use of ABC/2 is equivalent to planimetric stroke mismatch
volume. American Journal of Neuroradiology, 34(10), 1901–1907.
https://doi.org/10.3174/ajnr.A3476
Martínez Dubarbie, F., López-García, S., Andrés-Gómez, M., Lage, C.,
Pozueta, A., García-Martínez, M., Kazimierczak, M., Bravo, M., Jiménez-
Bonilla, J., Banzo, I., Rodríguez-Rodríguez, E., & Sánchez-Juan, P.
(2020). Fatal consequences of decreased sensitivity to pain and temper-
ature in a frontotemporal dementia patient. Neurocase, 26(6), 364–367.
https://doi.org/10.1080/13554794.2020.1842464
Medina, J., Kimberg, D. Y., Chatterjee, A., & Coslett, H. B. (2010).
Inappropriate usage of the Brunner–Munzel test in recent voxel-based
lesion-symptom mapping studies. Neuropsychologia, 48(1), 341–343.
https://doi.org/10.1016/j.neuropsychologia.2009.09.016
Menon, V., & Uddin, L. Q. (2010). Saliency, switching, attention and
control: A network model of insula function. Brain Structure & Function,
214(5–6), 655–667. https://doi.org/10.1007/s00429-010-0262-0
Moeller, T. B., & Reif, E. (2020). Japanese version of pocket atlas of
sectional anatomy: Computed tomography and magnetic resonance
imaging (T. Machida, Trans.; 4th ed.). Thieme.
Nurmi, M. E., & Jehkonen, M. (2015). Recognition and rehabilitation of
impaired awareness of illness, i.e. anosognosia in a patient with cere-
brovascular disease. Duodecim, 131(3), 228–234.
Osilla, E. V., Marsidi, J. L., Shumway, K. R., & Sharma, S. (2023). Physiology,
temperature regulation. In StatPearls [Internet]. StatPearls Publishing.
Pavlou, M. P., & Lachs, M. S. (2008). Self-neglect in older adults: A primer
for clinicians. Journal of General Internal Medicine, 23(11), 1841–1846.
https://doi.org/10.1007/s11606-008-0717-7
Pfeiffer, R. F. (1990). Bromocriptine-induced hypothermia. Neurology,
40(2), Article 383. https://doi.org/10.1212/WNL.40.2.383
Pickens, S., Burnett, J., Trail Ross, M. E., Jones, E., & Jefferson, F. (2023).
Meeting the challenges in conducting research in vulnerable older adults
with self-neglect-notes from a field team. Frontiers in Medicine, 10,
Article 1114895. https://doi.org/10.3389/fmed.2023.1114895
Ponsford, J., & Kinsella, G. (1991). The use of a rating scale of attentional
behaviour. Neuropsychological Rehabilitation, 1(4), 241–257. https://
doi.org/10.1080/09602019108402257
Ratcliffe, P. J., Bell, J. I., Collins, K. J., Frackowiak, R. S., & Rudge, P.
(1983). Late onset post-traumatic hypothalamic hypothermia. Journal of
Neurology, Neurosurgery & Psychiatry, 46(1), 72–74. https://doi.org/10
.1136/jnnp.46.1.72
Reeves, M. J., Bushnell, C. D., Howard, G., Gargano, J. W., Duncan, P. W.,
Lynch, G., Khatiwoda, A., & Lisabeth, L. (2008). Sex differences in stroke:
Epidemiology, clinical presentation, medical care, and outcomes. The Lancet
Neurology, 7(10), 915–926. https://doi.org/10.1016/S1474-4422(08)70193-5
Ren, L., Gang, X., Yang, S., Sun, M., & Wang, G. (2022). A new perspective
of hypothalamic disease: Shapiro’s syndrome. Frontiers in Neurology, 13,
Article 911332. https://doi.org/10.3389/fneur.2022.911332
Rial-Pensado, E., Rivas-Limeres, V., Grijota-Martínez, C., Rodríguez-
Díaz, A., Capelli, V., Barca-Mayo, O., Nogueiras, R., Mittag, J.,
Diéguez, C., & López, M. (2022). Temperature modulates systemic
and central actions of thyroid hormones on BAT thermogenesis.
Frontiers in Physiology, 13, Article 1017381. https://doi.org/10.3389/
fphys.2022.1017381
Rorden, C., Karnath, H. O., & Bonilha, L. (2007). Improving lesion-
symptom mapping. Journal of Cognitive Neuroscience, 19(7), 1081–
1088. https://doi.org/10.1162/jocn.2007.19.7.1081
Rudebeck, P. H., & Murray, E. A. (2014). The orbitofrontal oracle: Cortical
mechanisms for the prediction and evaluation of specific behavioral
outcomes. Neuron, 84(6), 1143–1156. https://doi.org/10.1016/j.neuron
.2014.10.049
Rueckert, L., & Grafman, J. (1996). Sustained attention deficits in patients
with right frontal lesions. Neuropsychologia, 34(10), 953–963. https://
doi.org/10.1016/0028-3932(96)00016-4
Savioli, G., Ceresa, I. F., Bavestrello Piccini, G., Gri, N., Nardone, A., La
Russa, R., Saviano, A., Piccioni, A., Ricevuti, G., & Esposito, C. (2023).
Hypothermia: Beyond the narrative review—The point of view of emer-
gency physicians and medico-legal considerations. Journal of Personalized
Medicine, 13(12), Article 1690. https://doi.org/10.3390/jpm13121690
Senzaki, A., Edakubo, T., Hoshi, K., & Kato, M. (1997). The reliability and
validity of a clinical attentional scale. Sogo Rehabilitation, 25, 567–573.
https://doi.org/10.11477/mf.1552108403
Silva, R. V., Reis, C. M. S., & Novaes, M. R. C. G. (2015). Risk factors of
burn injury and prevention methods in the elderly. Revista Brasileira de
Cirurgia Plástica, 30(3), 461–467. https://doi.org/10.5935/2177-1235
.2015RBCP0179
Spaccavento, S., Marinelli, C. V., Nardulli, R., Macchitella, L., Bivona, U.,
Piccardi, L., Zoccolotti, P., & Angelelli, P. (2019). Attention deficits in
stroke patients: The role of lesion characteristics, time from stroke, and
concomitant neuropsychological deficits. Behavioural Neurology, 2019,
Article 7835710. https://doi.org/10.1155/2019/7835710
Stuss, D. T., & Levine, B. (2002). Adult clinical neuropsychology: Lessons
from studies of the frontal lobes. Annual Review of Psychology, 53(1),
401–433. https://doi.org/10.1146/annurev.psych.53.100901.135220
Stuss, D. T., Picton, T. W., & Alexander, M. P. (2001). Consciousness, self-
awareness, and the frontal lobes. In S. P. Salloway, P. F. Malloy, & J. D.
Duffy (Eds.), The frontal lobes and neuropsychiatric illness (pp. 101–
109). American Psychiatric Publishing.
Sugishita, M., Hemmi, I., & Takeuchi, T. (2016). Reexamination of the
validity and reliability of the Japanese version of the Mini-Mental State
Examination (MMSE–J). Japanese Journal of Cognitive Neuroscience,
18, 168–183. https://doi.org/10.11253/ninchishinkeikagaku.18.168
Sugishita, M., Koshizuka, Y., Sudou, S., Sugishita, K., Hemmi, I., Karasawa,
H., Ihara, M., Asada, T., & Mihara, B. (2018). The validity and reliability
of the Japanese version of the Mini-Mental State Examination (MMSE-J)
with the original procedure of the attention and calculation task (2001).
Japanese Journal of Cognitive Neuroscience, 20(2), 91–110. https://
doi.org/10.11253/ninchishinkeikagaku.20.91
Terneusen, A., Winkens, I., van Heugten, C., Stapert, S., Jacobs, H. I. L.,
Ponds, R., & Quaedflieg, C. (2023). Neural correlates of impaired self-
awareness of deficits after acquired brain injury: A systematic review.
Neuropsychology Review, 33(1), 222–237. https://doi.org/10.1007/
s11065-022-09535-6
Tyler, M. P., Wright, B. J., Raison, C. L., Lowry, C. A., Evans, L., & Hale,
M. W. (2024). Greater severity of depressive symptoms is associated with
changes to perceived sweating, preferred ambient temperature, and
warmth-seeking behavior. Temperature, 11(3), 266–279. https://doi.org/
10.1080/23328940.2024.2374097
Uniform Data System for Medical Rehabilitation. (1997). Guide for the
uniform data set for medical rehabilitation (including the FIM instrument)
(Version 5.1). State University of New York at Buffalo.
van Marum, R. J., Wegewijs, M. A., Loonen, A. J., & Beers, E. (2007).
Hypothermia following antipsychotic drug use. European Journal of
Clinical Pharmacology, 63(6), 627–631. https://doi.org/10.1007/s00228-
007-0294-4
von Salis, S., Ehlert, U., & Fischer, S. (2021). Altered experienced ther-
moregulation in depression—No evidence for an effect of early life stress.
Frontiers in Psychiatry, 12, Article 620656. https://doi.org/10.3389/fpsyt
.2021.620656
Watanuki, T., Hara, H., Miyamori, T., & Etoh, F. (2002). The Rivermead
behavioural memory test in Japanese. Chiba Test Center.
Wen, H. T., Rhoton, A. L., Jr., de Oliveira, E., Cardoso, A. C., Tedeschi, H.,
Baccanelli, M., & Marino, R., Jr. (1999). Microsurgical anatomy of the
temporal lobe: Part 1: Mesial temporal lobe anatomy and its vascular
relationships as applied to amygdalohippocampectomy. Neurosurgery,
45(3), 549–591. https://doi.org/10.1097/00006123-199909000-00028
Wheeler, D. S., Wan, S., Miller, A., Angeli, N., Adileh, B., Hu, W., &
Holland, P. C. (2014). Role of lateral hypothalamus in two aspects of
attention in associative learning. European Journal of Neuroscience,
40(2), 2359–2377. https://doi.org/10.1111/ejn.12592
Wheeler, M., Williams, O. A., Johns, L., Chiu, E. G., Slavkovab, E. D., &
Demeyere, N. (2023). Unravelling the complex interactions between self-
awareness, cognitive change, and mood at 6-months post-stroke using the
Y-shaped model. Neuropsychological Rehabilitation, 33(4), 680–702.
https://doi.org/10.1080/09602011.2022.2042329
Wilke, M., de Haan, B., Juenger, H., & Karnath, H. O. (2011). Manual, semi-
automated, and automated delineation of chronic brain lesions: A com-
parison of methods. NeuroImage, 56(4), 2038–2046. https://doi.org/10
.1016/j.neuroimage.2011.04.014
Wilson, B. A., Alderman, N., Burgess, P. W., Emslie, H., & Evans, J. J.
(1996). Behavioural assessment of the dysexecutive syndrome. Thames
Valley Test Company.
Zald, D. H., & Andreotti, C. (2010). Neuropsychological assessment of the
orbital and ventromedial prefrontal cortex. Neuropsychologia, 48(12),
3377–3391. https://doi.org/10.1016/j.neuropsychologia.2010.08.012
Zilles, K., Eickhoff, S., & Palomero-Gallagher, N. (2013). The human
parietal cortex: A novel approach to its architectonic mapping. In A. M.
Siegel, R. A. Andersen, H. J. Freund, & D. D. Spencer (Eds.), The parietal
lobes (pp. 1–22). Lippincott Williams & Wilkins."""


test4 = """Asmundson, G. J. G., Noel, M., Petter, M., & Parkerson, H. A. (2012).
Pediatric fear-avoidance model of chronic pain: Foundation, application
and future directions. Pain Research & Management, 17(6), 397–405.
https://doi.org/10.1155/2012/908061
Ayr, L. K., Yeates, K. O., Taylor, H. G., & Browne, M. (2009). Dimensions
of postconcussive symptoms in children with mild traumatic brain injuries.
Journal of the International Neuropsychological Society, 15(1), 19–30.
https://doi.org/10.1017/S1355617708090188
Birnie, K. A., Heathcote, L. C., Bhandari, R. P., Feinstein, A., Yoon, I. A., &
Simons, L. E. (2020). Parent physical and mental health contributions to
interpersonal fear avoidance processes in pediatric chronic pain. Pain,
161(6), 1202–1211. https://doi.org/10.1097/j.pain.0000000000001820
Buzzanca-Fried, K. E., Snyder, A. R., Bauer, R. M., Morgan-Daniel, J., de
Corcho, C. P., Addeo, R., Lahey, S. M., Houck, Z., & Beneciuk, J. M.
(2024). Psychological constructs from the fear avoidance model and
beyond as predictors for persisting symptoms after concussion: An
integrative review. Archives of Physical Medicine and Rehabilitation,
105(12), 2362–2374. https://doi.org/10.1016/j.apmr.2024.04.007
Chanques, G., Viel, E., Constantin, J.-M., Jung, B., de Lattre, S., Carr, J.,
Cissé, M., Lefrant, J.-Y., & Jaber, S. (2010). The measurement of pain in
intensive care unit: Comparison of 5 self-report intensity scales. Pain,
151(3), 711–721. https://doi.org/10.1016/j.pain.2010.08.039
Chow, E. T., Otis, J. D., & Simons, L. E. (2016). The longitudinal impact of
parent distress and behavior on functional outcomes among youth with
chronic pain. The Journal of Pain, 17(6), 729–738. https://doi.org/10
.1016/j.jpain.2016.02.014
Chrisman, S. P. D., Bollinger, B. J., Mendoza, J. A., Palermo, T. M., Zhou,
C., Brooks, M. A., & Rivara, F. P. (2022). Mobile Subthreshold Exercise
Program (MSTEP) for concussion: Study protocol for a randomized
controlled trial. Trials, 23(1), Article 355. https://doi.org/10.1186/s13063-
022-06239-3
Chrisman, S. P. D., Mendoza, J. A., Zhou, C., Palermo, T. M., Gogue-Garcia,
T., Janz, K. F., & Rivara, F. P. (2021). Pilot study of telehealth delivered
rehabilitative exercise for youth with concussion: The Mobile Subthreshold
Exercise Program (MSTEP). Frontiers in Pediatrics, 9, Article 645814.
https://doi.org/10.3389/fped.2021.645814
Chrisman, S. P. D., Whitlock, K. B., Mendoza, J. A., Burton, M. S., Somers,
E., Hsu, A., Fay, L., Palermo, T. M., & Rivara, F. P. (2019). Pilot
randomized controlled trial of an exercise program requiring minimal in-
person visits for youth with persistent sport-related concussion. Frontiers
in Neurology, 10, Article 623. https://doi.org/10.3389/fneur.2019.00623
Copley, M., Jimenez, N., Kroshus, E., & Chrisman, S. P. D. (2020).
Disparities in use of subspecialty concussion care based on ethnicity.
Journal of Racial and Ethnic Health Disparities, 7(3), 571–576. https://
doi.org/10.1007/s40615-019-00686-6
Crombez, G., Eccleston, C., Van Damme, S., Vlaeyen, J. W., & Karoly, P.
(2012). Fear-avoidance model of chronic pain: The next generation. The
Clinical Journal of Pain, 28(6), 475–483. https://doi.org/10.1097/AJP
.0b013e3182385392
Cronbach, L. J. (1951). Coefficient alpha and the internal structure of tests.
Psychometrika, 16(3), 297–334. https://doi.org/10.1007/BF02310555
Fann, J. R., Bombardier, C. H., Dikmen, S., Esselman, P., Warms, C. A.,
Pelzer, E., Rau, H., & Temkin, N. (2005). Validity of the Patient Health
Questionnaire-9 in assessing depression following traumatic brain injury.
The Journal of Head Trauma Rehabilitation, 20(6), 501–511. https://
doi.org/10.1097/00001199-200511000-00003
Fay, T. B., Yeates, K. O., Taylor, H. G., Bangert, B., Dietrich, A., Nuss, K. E.,
Rusin, J., & Wright, M. (2010). Cognitive reserve as a moderator of
postconcussive symptoms in children with complicated and uncomplicated
mild traumatic brain injury. Journal of the International Neuropsychological
Society, 16(1), 94–105. https://doi.org/10.1017/S1355617709991007
Hajek, C. A., Yeates, K. O., Taylor, H. G., Bangert, B., Dietrich, A., Nuss,
K. E., Rusin, J., & Wright, M. (2011). Agreement between parents and
children on ratings of post-concussive symptoms following mild traumatic
brain injury. Child Neuropsychology: A Journal on Normal and Abnormal
Development in Childhood and Adolescence, 17(1), 17–33. https://
doi.org/10.1080/09297049.2010.495058
Hecker, L., King, S., Stapert, S., Geusgens, C., den Hollander, M., Fleischeuer,
B., & van Heugten, C. (2025). Can exposure therapy be effective for per-
sistent post-concussion symptoms? A nonconcurrent multiple baseline
design across 4 cases. The Journal of Head Trauma Rehabilitation, 40(4),
269–278. https://doi.org/10.1097/HTR.0000000000001023
King, S., Stapert, S. Z., Wijenberg, M. L. M., Winkens, I., Verbunt, J. A.,
Rijkeboer, M. M., van der Naalt, J., & van Heugten, C. M. (2024).
Psychometric properties of two instruments assessing catastrophizing and
fear-avoidance behavior in mild traumatic brain injury. Neuropsychology,
38(5), 403–415. https://doi.org/10.1037/neu0000954
King, S., Stapert, S. Z., Winkens, I., van der Naalt, J., van Heugten, C. M., &
Rijkeboer, M. M. (2024). Efficacy of an intensive exposure intervention
for individuals with persistent concussion symptoms following concus-
sion: A concurrent multiple baseline Single-Case Experimental Design
(SCED) Study. The Journal of Head Trauma Rehabilitation, 39(5), E419–
E429. https://doi.org/10.1097/HTR.0000000000000942
Kroenke, K., Spitzer, R. L., & Williams, J. B. (2001). The PHQ-9: Validity of
a brief depression severity measure. Journal of General Internal Medicine,
16(9), 606–613. https://doi.org/10.1046/j.1525-1497.2001.016009606.x
Lovette, B. C., Briskin, E. A., Grunberg, V. A., Vranceanu, A.-M., &
Greenberg, J. (2024). “I completely shut down”: A mixed methods eval-
uation of the fear-avoidance model for young adults with a recent concussion
and anxiety. Rehabilitation Psychology, 69(3), 206–216. https://doi.org/10
.1037/rep0000549
Löwe, B., Decker, O., Müller, S., Brähler, E., Schellberg, D., Herzog, W., &
Herzberg, P. Y. (2008). Validation and standardization of the Generalized
Anxiety Disorder Screener (GAD-7) in the general population. Medical
Care, 46(3), 266–274. https://doi.org/10.1097/MLR.0b013e318160d093
Löwe, B., Unützer, J., Callahan, C. M., Perkins, A. J., & Kroenke, K. (2004).
Monitoring depression treatment outcomes with the Patient Health
Questionnaire-9. Medical Care, 42(12), 1194–1201. https://doi.org/10
.1097/00005650-200412000-00006
Maizels, M., Smitherman, T. A., & Penzien, D. B. (2006). A review of
screening tools for psychiatric comorbidity in headache patients.
Headache: The Journal of Head and Face Pain, 46(Suppl. 3), S98–S109.
https://doi.org/10.1111/j.1526-4610.2006.00561.x
McCarty, C. A., Zatzick, D., Stein, E., Wang, J., Hilt, R., Rivara, F. P. &
Seattle Sports Concussion Research Collaborative. (2016). Collaborative
care for adolescents with persistent postconcussive symptoms: A ran-
domized trial. Pediatrics, 138(4), Article e20160459. https://doi.org/10
.1542/peds.2016-0459
McCarty, C. A., Zatzick, D. F., Marcynyszyn, L. A., Wang, J., Hilt, R.,
Jinguji, T., Quitiquit, C., Chrisman, S. P. D., & Rivara, F. P. (2021). Effect
of collaborative care on persistent postconcussive symptoms in adoles-
cents: A randomized clinical trial. JAMA Network Open, 4(2), Article
e210207. https://doi.org/10.1001/jamanetworkopen.2021.0207
Moran, L. M., Taylor, H. G., Rusin, J., Bangert, B., Dietrich, A., Nuss, K. E.,
Wright, M., & Yeates, K. O. (2011). Do postconcussive symptoms dis-
criminate injury severity in pediatric mild traumatic brain injury? The
Journal of Head Trauma Rehabilitation, 26(5), 348–354. https://doi.org/
10.1097/HTR.0b013e3181f8d32e
Neville, A., Kopala-Sibley, D. C., Soltani, S., Asmundson, G. J. G., Jordan,
A., Carleton, R. N., Yeates, K. O., Schulte, F., & Noel, M. (2021). A
longitudinal examination of the interpersonal fear avoidance model of
pain: The role of intolerance of uncertainty. Pain, 162(1), 152–160. https://
doi.org/10.1097/j.pain.0000000000002009
O’Connor, S. S., Zatzick, D. F., Wang, J., Temkin, N., Koepsell, T. D., Jaffe,
K. M., Durbin, D., Vavilala, M. S., Dorsch, A., & Rivara, F. P. (2012).
Association between posttraumatic stress, depression, and functional
impairments in adolescents 24 months after traumatic brain injury. Journal
of Traumatic Stress, 25(3), 264–271. https://doi.org/10.1002/jts.21704
Patricios, J. S., Schneider, K. J., Dvorak, J., Ahmed, O. H., Blauwet, C., Cantu,
R. C., Davis, G. A., Echemendia, R. J., Makdissi, M., McNamee, M.,
Broglio, S., Emery, C. A., Feddermann-Demont, N., Fuller, G. W., Giza,
C. C., Guskiewicz, K. M., Hainline, B., Iverson, G. L., Kutcher, J. S., …
Meeuwisse, W. (2023). Consensus statement on concussion in sport: The
6th International Conference on Concussion in Sport–Amsterdam, October
2022. British Journal of Sports Medicine, 57(11), 695–711. https://doi.org/
10.1136/bjsports-2023-106898
R Core Team. (2024). A language and environment for statistical computing
[Computer software]. R Foundation for Statistical Computing. https://
www.R-project.org/
Rescorla, L. A., Ginzburg, S., Achenbach, T. M., Ivanova, M. Y., Almqvist, F.,
Begovac, I., Bilenberg, N., Bird, H., Chahed, M., Dobrean, A., Döpfner, M.,
Erol, N., Hannesdottir, H., Kanbayashi, Y., Lambert, M. C., Leung, P. W. L.,
Minaei, A., Novik, T. S., Oh, K.-J., … Verhulst, F. C. (2013). Cross-informant
agreement between parent-reported and adolescent self-reported problems in
25 societies. Journal of Clinical Child and Adolescent Psychology, 42(2),
262–273. https://doi.org/10.1080/15374416.2012.717870
Revelle, W. (2024). Procedures for psychological, psychometric and per-
sonality research (R package Version 2.4.6) [Computer software]. https://
CRAN.R-project.org/package=psych
Richardson, L. P., McCauley, E., Grossman, D. C., McCarty, C. A.,
Richards, J., Russo, J. E., Rockhill, C., & Katon, W. (2010). Evaluation of
the Patient Health Questionnaire-9 item for detecting major depression
among adolescents. Pediatrics, 126(6), 1117–1123. https://doi.org/10
.1542/peds.2010-0852
Rioux, M., Brasher, P. M. A., McKeown, G., Yeates, K. O., Vranceanu, A.-
M., Snell, D. L., Cairncross, M., Panenka, W. J., Iverson, G. L., Debert,
C. T., Bayley, M. T., Hunt, C., Burke, M. J., & Silverberg, N. D. (2025).
Graded exposure therapy for adults with persistent symptoms after mTBI:
A historical comparison study. Neuropsychological Rehabilitation, 35(7),
1349–1365. https://doi.org/10.1080/09602011.2024.2403647
Salbach-Andrae, H., Lenz, K., & Lehmkuhl, U. (2009). Patterns of agreement
among parent, teacher and youth ratings in a referred sample. European
Psychiatry, 24(5), 345–351. https://doi.org/10.1016/j.eurpsy.2008.07.008
Sherwood, L. J., Korakakis, V., Mosler, A. B., Fortington, L., & Murphy,
M. C. (2023). Quantifying fear avoidance behaviors in people with
concussion: A COSMIN-informed systematic review. The Journal of
Orthopaedic and Sports Physical Therapy, 53(9), 540–565. https://
doi.org/10.2519/jospt.2023.11685
Silverberg, N. D., Panenka, W. J., & Iverson, G. L. (2018). Fear avoidance
and clinical outcomes from mild traumatic brain injury. Journal of
Neurotrauma, 35(16), 1864–1873. https://doi.org/10.1089/neu.2018.5662
Simons, L. E. (2016). Fear of pain in children and adolescents with neu-
ropathic pain and complex regional pain syndrome. Pain, 157(Suppl. 1),
S90–S97. https://doi.org/10.1097/j.pain.0000000000000377
Simons, L. E., & Kaczynski, K. J. (2012). The Fear Avoidance model of
chronic pain: Examination for pediatric application. The Journal of Pain,
13(9), 827–835. https://doi.org/10.1016/j.jpain.2012.05.002
Simons, L. E., Pielech, M., Cappucci, S., & Lebel, A. (2015). Fear of pain in
pediatric headache. Cephalalgia, 35(1), 36–44. https://doi.org/10.1177/
0333102414534084
Simons, L. E., Sieberg, C. B., Carpino, E., Logan, D., & Berde, C. (2011).
The Fear of Pain Questionnaire (FOPQ): Assessment of pain-related fear
among children and adolescents with chronic pain. The Journal of Pain,
12(6), 677–686. https://doi.org/10.1016/j.jpain.2010.12.008
Simons, L. E., Smith, A., Kaczynski, K., & Basch, M. (2015). Living in fear
of your child’s pain: The Parent Fear of Pain Questionnaire. Pain, 156(4),
694–702. https://doi.org/10.1097/j.pain.0000000000000100
Snell, D. L., Siegert, R. J., Debert, C., Cairncross, M., & Silverberg, N. D.
(2020). Evaluation of the fear avoidance behavior after Traumatic Brain
Injury Questionnaire. Journal of Neurotrauma, 37(13), 1566–1573.
https://doi.org/10.1089/neu.2019.6729
Spitzer, R. L., Kroenke, K., Williams, J. B. W., & Löwe, B. (2006). A brief
measure for assessing generalized anxiety disorder: The GAD-7. Archives
of Internal Medicine, 166(10), 1092–1097. https://doi.org/10.1001/archi
nte.166.10.1092
Taylor, H. G., Dietrich, A., Nuss, K., Wright, M., Rusin, J., Bangert, B.,
Minich, N., & Yeates, K. O. (2010). Post-concussive symptoms in
children with mild traumatic brain injury. Neuropsychology, 24(2), 148–
159. https://doi.org/10.1037/a0018112
Terpstra, A. R., Cairncross, M., Yeates, K. O., Vranceanu, A.-M.,
Greenberg, J., Hunt, C., & Silverberg, N. D. (2021). Psychological
mediators of avoidance and endurance behavior after concussion.
Rehabilitation Psychology, 66(4), 470–478. https://doi.org/10.1037/re
p0000390
Turk, D. C., & Wilson, H. D. (2010). Fear of pain as a prognostic factor in
chronic pain: Conceptual models, assessment, and treatment implications.
Current Pain and Headache Reports, 14(2), 88–95. https://doi.org/10
.1007/s11916-010-0094-x
Varni, J. W., Burwinkle, T. M., & Seid, M. (2005). The PedsQL as a pediatric
patient-reported outcome: Reliability and validity of the PedsQL Measure-
ment Model in 25,000 children. Expert Review of Pharmacoeconomics &
Outcomes Research, 5(6), 705–719. https://doi.org/10.1586/14737167.5
.6.705
Varni, J. W., Burwinkle, T. M., Seid, M., & Skarr, D. (2003). The PedsQL
4.0 as a pediatric population health measure: Feasibility, reliability, and
validity. Ambulatory Pediatrics, 3(6), 329–341. https://doi.org/10.1367/
1539-4409(2003)003<0329:TPAAPP>2.0.CO;2
Varni, J. W., Seid, M., & Kurtin, P. S. (2001). PedsQL 4.0: Reliability and
validity of the Pediatric Quality of Life Inventory version 4.0 generic core
scales in healthy and patient populations. Medical Care, 39(8), 800–812.
https://doi.org/10.1097/00005650-200108000-00006
Vlaeyen, J. W. S., & Linton, S. J. (2000). Fear-avoidance and its con-
sequences in chronic musculoskeletal pain: A state of the art. Pain, 85(3),
317–332. https://doi.org/10.1016/S0304-3959(99)00242-0
Waters, E., Stewart-Brown, S., & Fitzpatrick, R. (2003). Agreement between
adolescent self-report and parent reports of health and well-being: Results
of an epidemiological study. Child: Care, Health and Development, 29(6),
501–509. https://doi.org/10.1046/j.1365-2214.2003.00370.x
Wijenberg, M. L. M., Stapert, S. Z., Verbunt, J. A., Ponsford, J. L., & Van
Heugten, C. M. (2017). Does the fear avoidance model explain persistent
symptoms after traumatic brain injury? Brain Injury, 31(12), 1597–1604.
https://doi.org/10.1080/02699052.2017.1366551
Wilson, C., Budd, B., Chernin, R., King, H., Leddy, A., Maclennan, F., &
Mallandain, I. (2011). The role of meta-cognition and parenting in ado-
lescent worry. Journal of Anxiety Disorders, 25(1), 71–79. https://doi.org/
10.1016/j.janxdis.2010.08.005
Zale, E. L., & Ditre, J. W. (2015). Pain-related fear, disability, and the fear-
avoidance model of chronic pain. Current Opinion in Psychology, 5, 24–
30. https://doi.org/10.1016/j.copsyc.2015.03.014
"""

test5 = """Aaltonen, S., Urjansson, M., Varjonen, A., Vähä-Ypyä, H., Iso-Markku, P.,
Kaartinen, S., Vasankari, T., Kujala, U. M., Silventoinen, K., Kaprio, J., &
Vuoksimaa, E. (2023). Accelerometer-measured physical activity and
sedentary behavior in nonagenarians: Associations with self-reported
physical activity, anthropometric, sociodemographic, health and cognitive
characteristics. PLOS ONE, 18(12), Article e0294817. https://doi.org/10
.1371/journal.pone.0294817
Albert, M. S. (2011). Changes in cognition. Neurobiology of Aging,
32(Suppl. 1), S58–S63. https://doi.org/10.1016/j.neurobiolaging.2011
.09.010
Albert, M. S., DeKosky, S. T., Dickson, D., Dubois, B., Feldman, H. H., Fox,
N. C., Gamst, A., Holtzman, D. M., Jagust, W. J., Petersen, R. C., Snyder,
P. J., Carrillo, M. C., Thies, B., & Phelps, C. H. (2011). The diagnosis of
mild cognitive impairment due to Alzheimer’s disease: Recommendations
from the National Institute on Aging-Alzheimer’s Association work-
groups on diagnostic guidelines for Alzheimer’s disease. Alzheimer’s &
Dementia, 7(3), 270–279. https://doi.org/10.1016/j.jalz.2011.03.008
Alenius, M., Hokkanen, L., Koskinen, S., Hallikainen, I., Hänninen, T.,
Karrasch, M., Raivio, M. M., Laakkonen, M. L., Krüger, J., Suhonen, N. M.,
Kivipelto, M., & Ngandu, T. (2022). Cognitive performance at time of
AD diagnosis: A clinically augmented register-based study. Frontiers in
Psychology, 13, Article 901945. https://doi.org/10.3389/fpsyg.2022.901945
Alenius, M., Koskinen, S., Hallikainen, I., Ngandu, T., Lipsanen, J., Sainio,
P., Tuulio-Henriksson, A., & Hänninen, T. (2019). Cognitive performance
among cognitively healthy adults aged 30–100 years. Dementia and
Geriatric Cognitive Disorders Extra, 9(1), 11–23. https://doi.org/10.1159/
000495657
Bäckman, L., Jones, S., Berger, A. K., Laukka, E. J., & Small, B. J. (2005).
Cognitive impairment in preclinical Alzheimer’s disease: A meta-
analysis. Neuropsychology, 19(4), 520–531. https://doi.org/10.1037/
0894-4105.19.4.520
Baker, L. D., Snyder, H. M., Espeland, M. A., Whitmer, R. A., Kivipelto, M.,
Woolard, N., Katula, J., Papp, K. V., Ventrelle, J., Graef, S., Hill, M. A.,
Rushing, S., Spell, J., Lovato, L., Felton, D., Williams, B. J., Ghadimi
Nouran, M., Raman, R., Ngandu, T., … the U.S. POINTER Study Group.
(2024). Study design and methods: U.S. study to protect brain health
through lifestyle intervention to reduce risk (U.S. POINTER). Alzheimer’s
& Dementia, 20(2), 769–782. https://doi.org/10.1002/alz.13365
Beam, C. R., Kaneshiro, C., Jang, J. Y., Reynolds, C. A., Pedersen, N. L., &
Gatz, M. (2018). Differences between women and men in incidence rates
of dementia and Alzheimer’s disease. Journal of Alzheimer’s Disease,
64(4), 1077–1083. https://doi.org/10.3233/JAD-180141
Bellenguez, C., Küçükali, F., Jansen, I. E., Kleineidam, L., Moreno-Grau, S.,
Amin, N., Naj, A. C., Campos-Martin, R., Grenier-Boley, B., Andrade, V.,
Holmans, P. A., Boland, A., Damotte, V., van der Lee, S. J., Costa, M. R.,
Kuulasmaa, T., Yang, Q., de Rojas, I., Bis, J. C., … Lambert, J. C. (2022).
New insights into the genetic etiology of Alzheimer’s disease and related
dementias. Nature Genetics, 54(4), 412–436. https://doi.org/10.1038/
s41588-022-01024-z
Berlau, D. J., Corrada, M. M., & Kawas, C. (2009). The prevalence of disability
in the oldest-old is high and continues to increase with age: Findings from
The 90+ study. International Journal of Geriatric Psychiatry, 24(11), 1217–
1225. https://doi.org/10.1002/gps.2248
Bock, J. R., Russell, J., Hara, J., & Fortier, D. (2021). Optimizing cognitive
assessment outcome measures for Alzheimer’s disease by matching wordlist
memory test features to scoring methodology. Frontiers in Digital Health, 3,
Article 750549. https://doi.org/10.3389/fdgth.2021.750549
Brandt, J., Spencer, M., & Folstein, M. (1988). Telephone Interview for
Cognitive Status. Neuropsychiatry, Neuropsychology, & Behavioral
Neurology, 1(2), 111–117.
Brooks, B. L., Iverson, G. L., Holdnack, J. A., & Feldman, H. H. (2008).
Potential for misclassification of mild cognitive impairment: A study of
memory scores on the Wechsler Memory Scale–III in healthy older adults.
Journal of the International Neuropsychological Society, 14(3), 463–478.
https://doi.org/10.1017/S1355617708080521
Brooks, B. L., Iverson, G. L., & White, T. (2007). Substantial risk of “accidental
MCI” in healthy older adults: Base rates of low memory scores in neuro-
psychological assessment. Journal of the International Neuropsychological
Society, 13(3), 490–500. https://doi.org/10.1017/S1355617707070531
Calamia, M., Markon, K., & Tranel, D. (2013). The robust reliability of
neuropsychological measures: Meta-analyses of test–retest correlations.
The Clinical Neuropsychologist, 27(7), 1077–1105. https://doi.org/10
.1080/13854046.2013.809795
Cholerton, B., Latimer, C. S., Crane, P. K., Corrada, M. M., Gibbons, L. E.,
Larson, E. B., Kawas, C. H., Keene, C. D., & Montine, T. J. (2024).
Neuropathologic burden and dementia in nonagenarians and centenarians:
Comparison of 2 community-based cohorts. Neurology, 102(3), Article
e208060. https://doi.org/10.1212/WNL.0000000000208060
Corrada, M. M., Brookmeyer, R., Berlau, D., Paganini-Hill, A., & Kawas,
C. H. (2008). Prevalence of dementia after age 90: Results from the 90+
study. Neurology, 71(5), 337–343. https://doi.org/10.1212/01.wnl.000031
0773.65918.cd
Corrada, M. M., Brookmeyer, R., Paganini-Hill, A., Berlau, D., & Kawas,
C. H. (2010). Dementia incidence continues to increase with age in the
oldest old: The 90+ study. Annals of Neurology, 67(1), 114–121. https://
doi.org/10.1002/ana.21915
Debanne, S. M., Patterson, M. B., Dick, R., Riedel, T. M., Schnell, A., &
Rowland, D. Y. (1997). Validation of a telephone cognitive assessment
battery. Journal of the American Geriatrics Society, 45(11), 1352–1359.
https://doi.org/10.1111/j.1532-5415.1997.tb02935.x
Dubois, B., & Albert, M. L. (2004). Amnestic MCI or prodromal Alzheimer’s
disease? The Lancet Neurology, 3(4), 246–248. https://doi.org/10.1016/
S1474-4422(04)00710-0
Dubois, B., Villain, N., Schneider, L., Fox, N., Campbell, N., Galasko, D.,
Kivipelto, M., Jessen, F., Hanseeuw, B., Boada, M., Barkhof, F.,
Nordberg, A., Froelich, L., Waldemar, G., Frederiksen, K. S., Padovani,
A., Planche, V., Rowe, C., Bejanin, A., … Frisoni, G. B. (2024).
Alzheimer disease as a clinical-biological construct-an International
Working Group recommendation. JAMA Neurology, 81(12), 1304–1311.
https://doi.org/10.1001/jamaneurol.2024.3770
Elliott, E., Green, C., Llewellyn, D. J., & Quinn, T. J. (2020). Accuracy of
telephone-based cognitive screening tests: Systematic review and meta-
analysis. Current Alzheimer Research, 17(5), 460–471. https://doi.org/10
.2174/1567205017999200626201121
Elman, J. A., Vuoksimaa, E., Franz, C. E., Kremen, W. S., & the
Alzheimer’s Disease Neuroimaging Initiative. (2020). Degree of cog-
nitive impairment does not signify early versus late mild cognitive
impairment: Confirmation based on Alzheimer’s disease polygenic risk.
Neurobiology of Aging, 94, 149–153. https://doi.org/10.1016/j.neurobio
laging.2020.05.015
Escott-Price, V., & Hardy, J. (2022). Genome-wide association studies for
Alzheimer’s disease: Bigger is not always better. Brain Communications,
4(3), Article fcac125. https://doi.org/10.1093/braincomms/fcac125
Farrer, L. A., Cupples, L. A., Haines, J. L., Hyman, B., Kukull, W. A.,
Mayeux, R., Myers, R. H., Pericak-Vance, M. A., Risch, N., van Duijn,
C. M., & the APOE and Alzheimer Disease Meta Analysis Consortium.
(1997). Effects of age, sex, and ethnicity on the association between
apolipoprotein E genotype and Alzheimer disease. A meta-analysis. JAMA,
278(16), 1349–1356. https://doi.org/10.1001/jama.1997.03550160069041
Flake, J. K., Pek, J., & Hehman, E. (2017). Construct validation in social
and personality research: Current practice and recommendations. Social
Psychological and Personality Science, 8(4), 370–378. https://doi.org/10
.1177/1948550617693063
Fröhlich, S., Muller, K., & Voelcker-Rehage, C. (2024). Normative data for
the CERAD-NP for healthy high-agers (80–84 years) and effects of age-
typical visual impairment and hearing loss. Journal of the International
Neuropsychological Society, 30(7), 697–709. https://doi.org/10.1017/
S1355617721001284
Gatz, M., Reynolds, C., Nikolic, J., Lowe, B., Karel, M., & Pedersen, N.
(1995). An empirical test of telephone screening to identify potential
dementia cases. International Psychogeriatrics, 7(3), 429–438. https://
doi.org/10.1017/S1041610295002171
Gatz, M., Reynolds, C. A., John, R., Johansson, B., Mortimer, J. A., & Pedersen,
N. L. (2002). Telephone screening to identify potential dementia cases in a
population-based sample of older adults. International Psychogeriatrics,
14(3), 273–289. https://doi.org/10.1017/S1041610202008475
Getsios, D., Blume, S., Ishak, K. J., Maclaine, G., & Hernández, L. (2012).
An economic evaluation of early assessment for Alzheimer’s disease in the
United Kingdom. Alzheimer’s & Dementia, 8(1), 22–30. https://doi.org/10
.1016/j.jalz.2010.07.001
Gicas, K. M., Honer, W. G., Leurgans, S. E., Wilson, R. S., Boyle, P. A.,
Schneider, J. A., & Bennett, D. A. (2023). Longitudinal change in serial
position scores in older adults with entorhinal and hippocampal neuro-
pathologies. Journal of the International Neuropsychological Society,
29(6), 561–571. https://doi.org/10.1017/S1355617722000595
Gilsanz, P., Corrada, M. M., Kawas, C. H., Mayeda, E. R., Glymour, M. M.,
Quesenberry, C. P., Jr., Lee, C., & Whitmer, R. A. (2019). Incidence of
dementia after age 90 in a multiracial cohort. Alzheimer’s & Dementia,
15(4), 497–505. https://doi.org/10.1016/j.jalz.2018.12.006
Gustavson, D. E., Elman, J. A., Panizzon, M. S., Franz, C. E., Zuber, J.,
Sanderson-Cimino, M., Reynolds, C. A., Jacobson, K. C., Xian, H., Jak,
A. J., Toomey, R., Lyons, M. J., & Kremen, W. S. (2020). Association of
baseline semantic fluency and progression to mild cognitive impairment in
middle-aged men. Neurology, 95(8), e973–e983. https://doi.org/10.1212/
WNL.0000000000010130
Gustavson, D. E., Reynolds, C. A., Hohman, T. J., Jefferson, A. L., Elman,
J. A., Panizzon, M. S., Neale, M. C., Logue, M. W., Lyons, M. J., Franz,
C. E., & Kremen, W. S. (2023). Alzheimer’s disease polygenic scores
predict changes in episodic memory and executive function across 12
years in late middle age. Journal of the International Neuropsychological
Society, 29(2), 136–147. https://doi.org/10.1017/S1355617722000108
Halekoh, U., Hojsgaard, S., & Yan, J. (2006). The R package geepack for
generalized estimating equations. Journal of Statistical Software, 15(2),
1–11. https://doi.org/10.18637/jss.v015.i02
Hallikainen, I., Alenius, M., Hokkanen, L., Karrasch, M., Kruger, J.,
Ngandu, T., Paajanen, T., Rosenvall, A., Suhonen, N., & Hänninen, T.
(2023). CERAD-tehtäväsarjaan koulutustason huomioivat katkaisurajat ja
kokonaispistemäärä käyttöön [New education-based cut-off scores and
total score for the Finnish version of the CERAD neuropsychological
battery]. Suomen Lääkärilehti, 78, Article e35809. https://www.laakarile
hti.fi/e35809
Halonen, P., Enroth, L., Jämsen, E., Vargese, S., & Jylhä, M. (2023).
Dementia and related comorbidities in the population aged 90 and over in
the vitality 90+ study, Finland: Patterns and trends from 2001 to 2018.
Journal of Aging and Health, 35(5–6), 370–382. https://doi.org/10.1177/
08982643221123451
He, W., Goodkind, D., & Kowal, P. (2016). An aging world: 2015: International
population reports (1st ed.). U.S. Government Publishing Office.
Hogervorst, E., Bandelow, S., Hart, J., Jr., & Henderson, V. W. (2004).
Telephone word-list recall tested in the rural aging and memory study:
Two parallel versions for the TICS-M. International Journal of Geriatric
Psychiatry, 19(9), 875–880. https://doi.org/10.1002/gps.1170
Hosmer, D. W., & Lemeshow, S. (2000). Applied logistic regression
(2nd ed.). Wiley. https://doi.org/10.1002/0471722146
Jack, C. R., Jr., Andrews, J. S., Beach, T. G., Buracchio, T., Dunn, B., Graf,
A., Hansson, O., Ho, C., Jagust, W., McDade, E., Molinuevo, J. L.,
Okonkwo, O. C., Pani, L., Rafii, M. S., Scheltens, P., Siemers, E., Snyder,
H. M., Sperling, R., Teunissen, C. E., & Carrillo, M. C. (2024). Revised
criteria for diagnosis and staging of Alzheimer’s disease: Alzheimer’s
Association Workgroup. Alzheimer’s & Dementia, 20(8), 5143–5169.
https://doi.org/10.1002/alz.13859
Jak, A. J., Preis, S. R., Beiser, A. S., Seshadri, S., Wolf, P. A., Bondi, M. W., &
Au, R. (2016). Neuropsychological criteria for mild cognitive impairment
and dementia risk in the Framingham Heart Study. Journal of the
International Neuropsychological Society, 22(9), 937–943. https://doi.org/
10.1017/S1355617716000199
Järvenpää, T., Rinne, J. O., Räihä, I., Koskenvuo, M., Löppönen, M.,
Hinkka, S., & Kaprio, J. (2002). Characteristics of two telephone screens
for cognitive impairment. Dementia and Geriatric Cognitive Disorders,
13(3), 149–155. https://doi.org/10.1159/000048646
Jedynak, B. M., Lang, A., Liu, B., Katz, E., Zhang, Y., Wyman, B. T.,
Raunig, D., Jedynak, C. P., Caffo, B., Prince, J. L., & the Alzheimer’s
Disease Neuroimaging Initiative. (2012). A computational neurodegen-
erative disease progression score: Method and results with the Alzheimer’s
disease neuroimaging initiative cohort. NeuroImage, 63(3), 1478–1486.
https://doi.org/10.1016/j.neuroimage.2012.07.059
Jedynak, B. M., Liu, B., Lang, A., Gel, Y., Prince, J. L., & the Alzheimer’s
Disease Neuroimaging Initiative. (2015). A computational method for
computing an Alzheimer’s disease progression score; experiments and
validation with the ADNI data set. Neurobiology of Aging, 36(Suppl. 1),
S178–S184. https://doi.org/10.1016/j.neurobiolaging.2014.03.043
Jetsonen, V., Kuvaja-Köllner, V., Välimäki, T., Selander, T., Martikainen,
J., & Koivisto, A. M. (2021). Total cost of care increases significantly
from early to mild Alzheimer’s disease: 5-year ALSOVA follow-up.
Age and Ageing, 50(6), 2116–2122. https://doi.org/10.1093/ageing/
afab144
Julkunen, V., Schwarz, C., Kalapudas, J., Hallikainen, M., Piironen, A. K.,
Mannermaa, A., Kujala, H., Laitinen, T., Kosma, V. M., Paajanen, T. I.,
Kälviäinen, R., Hiltunen, M., Herukka, S. K., Kärkkäinen, S., Kokkola, T.,
Urjansson, M., Perola, M., Palotie, A., Vuoksimaa, E., … the FinnGen.
(2023). A FinnGen pilot clinical recall study for Alzheimer’s disease.
Scientific Reports, 13(1), Article 12641. https://doi.org/10.1038/s41598-
023-39835-7
Kaprio, J., Bollepalli, S., Buchwald, J., Iso-Markku, P., Korhonen, T.,
Kovanen, V., Kujala, U., Laakkonen, E. K., Latvala, A., Leskinen, T.,
Lindgren, N., Ollikainen, M., Piirtola, M., Rantanen, T., Rinne, J., Rose,
R. J., Sillanpää, E., Silventoinen, K., Sipilä, S., … Waller, K. (2019). The
older Finnish Twin Cohort—45 years of follow-up. Twin Research and
Human Genetics, 22(4), 240–254. https://doi.org/10.1017/thg.2019.54
Kawas, C. H., Kim, R. C., Sonnen, J. A., Bullain, S. S., Trieu, T., & Corrada,
M. M. (2015). Multiple pathologies are common and related to dementia in
the oldest-old: The 90+ study. Neurology, 85(6), 535–542. https://doi.org/
10.1212/WNL.0000000000001831
Kazak, A. E. (2018). Editorial: Journal article reporting standards. American
Psychologist, 73(1), 1–2. https://doi.org/10.1037/amp0000263
Kremen, W. S., Panizzon, M. S., Franz, C. E., Spoon, K. M., Vuoksimaa,
E., Jacobson, K. C., Vasilopoulos, T., Xian, H., McCaffery, J. M.,
Rana, B. K., Toomey, R., McKenzie, R., & Lyons, M. J. (2014). Genetic complexity of episodic memory: A twin approach to studies of
aging. Psychology and Aging, 29(2), 404–417. https://doi.org/10.1037/
a0035962
Kunkle, B. W., Grenier-Boley, B., Sims, R., Bis, J. C., Damotte, V., Naj,
A. C., Boland, A., Vronskaya, M., van der Lee, S. J., Amlie-Wolf, A.,
Bellenguez, C., Frizatti, A., Chouraki, V., Martin, E. R., Sleegers, K.,
Badarinarayan, N., Jakobsdottir, J., Hamilton-Nelson, K. L., Moreno-
Grau, S., … the Polygenic and Environmental Risk for Alzheimer’s
Disease Consortium (GERAD/PERADES). (2019). Genetic meta-analysis
of diagnosed Alzheimer’s disease identifies new risk loci and implicates
Aβ, tau, immunity and lipid processing. Nature Genetics, 51(3), 414–430.
https://doi.org/10.1038/s41588-019-0358-2
Lam, J. O., Whitmer, R. A., Corrada, M. M., Kawas, C. H., Vieira, K. E.,
Quesenberry, C. P., & Gilsanz, P. (2024). Gender differences in the
association between education and late-life cognitive function in the
LifeAfter90 study: A multiethnic cohort of the oldest-old. Alzheimer’s &
Dementia, 20(11), 7547–7555. https://doi.org/10.1002/alz.14217
Lambert, J. C., Ibrahim-Verbaas, C. A., Harold, D., Naj, A. C., Sims, R.,
Bellenguez, C., DeStafano, A. L., Bis, J. C., Beecham, G. W., Grenier-
Boley, B., Russo, G., Thorton-Wells, T. A., Jones, N., Smith, A. V.,
Chouraki, V., Thomas, C., Ikram, M. A., Zelenika, D., Vardarajan, B. N., …
Amouyel, P.. (2013). Meta-analysis of 74,046 individuals identifies 11 new
susceptibility loci for Alzheimer’s disease. Nature Genetics, 45(12), 1452–
1458. https://doi.org/10.1038/ng.2802
Lancaster, C., Tabet, N., & Rusted, J. (2017). The elusive nature of APOE ε4
in mid-adulthood: Understanding the cognitive profile. Journal of the
International Neuropsychological Society, 23(3), 239–253. https://doi.org/
10.1017/S1355617716000990
Lindgren, N., Rinne, J. O., Palviainen, T., Kaprio, J., & Vuoksimaa, E. (2019).
Prevalence and correlates of dementia and mild cognitive impairment
classified with different versions of the modified Telephone Interview for
Cognitive Status (TICS-m). International Journal of Geriatric Psychiatry,
34(12), 1883–1891. https://doi.org/10.1002/gps.5205
Livingston, G., Huntley, J., Liu, K. Y., Costafreda, S. G., Selbæk, G., Alladi,
S., Ames, D., Banerjee, S., Burns, A., Brayne, C., Fox, N. C., Ferri, C. P.,
Gitlin, L. N., Howard, R., Kales, H. C., Kivimäki, M., Larson, E. B.,
Nakasujja, N., Rockwood, K., … Mukadam, N. (2024). Dementia pre-
vention, intervention, and care: 2024 report of the Lancet standing
Commission. The Lancet, 404(10452), 572–628. https://doi.org/10.1016/
S0140-6736(24)01296-0
Lopez-Lee, C., Torres, E. R. S., Carling, G., & Gan, L. (2024). Mechanisms
of sex differences in Alzheimer’s disease. Neuron, 112(8), 1208–1221.
https://doi.org/10.1016/j.neuron.2024.01.024
Luck, T., Pabst, A., Rodriguez, F. S., Schroeter, M. L., Witte, V., Hinz, A.,
Mehnert, A., Engel, C., Loeffler, M., Thiery, J., Villringer, A., & Riedel-
Heller, S. G. (2018). Age-, sex-, and education-specific norms for an
extended CERAD Neuropsychological Assessment Battery—Results
from the population-based LIFE-Adult-Study. Neuropsychology, 32(4),
461–475. https://doi.org/10.1037/neu0000440
Lumley, T. (2004). Analysis of complex survey samples. Journal of
Statistical Software, 9(1), 1–19. https://doi.org/10.18637/jss.v009.i08
Marden, J. R., Mayeda, E. R., Walter, S., Vivot, A., Tchetgen Tchetgen,
E. J., Kawachi, I., & Glymour, M. M. (2016). Using an Alzheimer
disease polygenic risk score to predict memory decline in Black and
White Americans over 14 years of follow-up. Alzheimer Disease and
Associated Disorders, 30(3), 195–202. https://doi.org/10.1097/WAD
.0000000000000137
Mitsis, E. M., Jacobs, D., Luo, X., Andrews, H., Andrews, K., & Sano, M.
(2010). Evaluating cognition in an elderly cohort via telephone assess-
ment. International Journal of Geriatric Psychiatry, 25(5), 531–539.
https://doi.org/10.1002/gps.2373
Morris, J. C., Heyman, A., Mohs, R. C., Hughes, J. P., van Belle, G.,
Fillenbaum, G., Mellits, E. D., & Clark, C. (1989). The Consortium to
Establish a Registry for Alzheimer’s Disease (CERAD). Part I. Clinical
and neuropsychological assessment of Alzheimer’s disease. Neurology,
39(9), 1159–1165. https://doi.org/10.1212/WNL.39.9.1159
Neu, S. C., Pa, J., Kukull, W., Beekly, D., Kuzma, A., Gangadharan, P.,
Wang, L. S., Romero, K., Arneric, S. P., Redolfi, A., Orlandi, D.,
Frisoni, G. B., Au, R., Devine, S., Auerbach, S., Espinosa, A., Boada,
M., Ruiz, A., Johnson, S. C., … Toga, A. W. (2017). Apolipoprotein E
genotype and sex risk factors for Alzheimer disease: A meta-analysis.
JAMA Neurology, 74(10), 1178–1189. https://doi.org/10.1001/jamaneu
rol.2017.2188
Nyberg, L., & Pudas, S. (2019). Successful memory aging. Annual Review
of Psychology, 70, 219–243. https://doi.org/10.1146/annurev-psych-
010418-103052
Obuchowski, N. A. (1997). Nonparametric analysis of clustered ROC curve
data. Biometrics, 53(2), 567–578. https://doi.org/10.2307/2533958
R Core Team. (2023). R: A language and environment for statistical
computing [Computer software]. R Foundation for Statistical Computing.
https://www.R-project.org/
Rabin, L. A., Saykin, A. J., Wishart, H. A., Nutter-Upham, K. E.,
Flashman, L. A., Pare, N., & Santulli, R. B. (2007). The Memory and
Aging Telephone Screen: Development and preliminary validation.
Alzheimer’s & Dementia, 3(2), 109–121. https://doi.org/10.1016/j.jalz
.2007.02.002
Rajan, K. B., Weuve, J., Barnes, L. L., McAninch, E. A., Wilson, R. S., &
Evans, D. A. (2021). Population estimate of people with clinical
Alzheimer’s disease and mild cognitive impairment in the United States
(2020–2060). Alzheimer’s & Dementia, 17(12), 1966–1975. https://
doi.org/10.1002/alz.12362
Rapp, S. R., Legault, C., Espeland, M. A., Resnick, S. M., Hogan, P. E.,
Coker, L. H., Dailey, M., Shumaker, S. A., & the CAT Study Group.
(2012). Validation of a cognitive assessment battery administered over the
telephone. Journal of the American Geriatrics Society, 60(9), 1616–1623.
https://doi.org/10.1111/j.1532-5415.2012.04111.x
Rey, A. (1964). L’ examen clinique en psychologie (2nd ed.) [The clinical
examination in psychology]. Presses Universitaires de France.
Saari, T. T. (2025). Verbal memory assessment via telephone interview.
Open Science Framework. https://osf.io/hy3dg
Saari, T. T., Piirtola, M., Aaltonen, A., Palviainen, T., Varjonen, A., Julkunen,
V., Rinne, J. O., Kaprio, J., & Vuoksimaa, E. (2024). Measurement
invariance of the Center for Epidemiological Studies–Depression scale and
associations with genetic risk in older adults. PLOS ONE, 19(10), Article
e0312194. https://doi.org/10.1371/journal.pone.0312194
Schmidt, M. (1996). Rey Auditory and Verbal Learning Test: A handbook.
Western Psychological Services.
Schwarz, C., Franz, C. E., Kremen, W. S., & Vuoksimaa, E. (2024). Reserve,
resilience and maintenance of episodic memory and other cognitive
functions in aging. Neurobiology of Aging, 140, 60–69. https://doi.org/10
.1016/j.neurobiolaging.2024.04.011
Smith, V., Younes, K., Poston, K. L., Mormino, E. C., & Young, C. B.
(2023). Reliability of remote National Alzheimer’s Coordinating Center
Uniform Data Set data. Alzheimer’s & Dementia: Diagnosis, Assessment
& Disease Monitoring, 15(4), Article e12498. https://doi.org/10.1002/da
d2.12498
Steinberg, B. A., Bieliauskas, L. A., Smith, G. E., Ivnik, R. J., & Malec, J. F.
(2005). Mayo’s older Americans normative studies: Age- and IQ-adjusted
norms for the Auditory Verbal Learning Test and the Visual Spatial
Learning Test. The Clinical Neuropsychologist, 19(3–4), 464–523. https://
doi.org/10.1080/13854040590945193
Stricker, N. H., Christianson, T. J., Lundt, E. S., Alden, E. C., Machulda,
M. M., Fields, J. A., Kremers, W. K., Jack, C. R., Jr., Knopman, D. S.,
Mielke, M. M., & Petersen, R. C. (2021). Mayo normative studies:
Regression-based normative data for the Auditory Verbal Learning Test
for ages 30–91 years and the importance of adjusting for sex. Journal of
the International Neuropsychological Society, 27(3), 211–226. https://
doi.org/10.1017/S1355617720000752
Sundermann, E. E., Maki, P., Biegon, A., Lipton, R. B., Mielke, M. M.,
Machulda, M., Bondi, M. W., & the Alzheimer’s Disease Neuroimaging
Initiative. (2019). Sex-specific norms for verbal memory tests may improve
diagnostic accuracy of amnestic MCI. Neurology, 93(20), e1881–e1889.
https://doi.org/10.1212/WNL.0000000000008467
Tabata, K., Uraoka, N., Benhamida, J., Hanna, M. G., Sirintrapun, S. J.,
Gallas, B. D., Gong, Q., Aly, R. G., Emoto, K., Matsuda, K. M.,
Hameed, M. R., Klimstra, D. S., & Yagi, Y. (2019). Validation of
mitotic cell quantification via microscopy and multiple whole-slide
scanners. Diagnostic Pathology, 14(1), Article 65. https://doi.org/10
.1186/s13000-019-0839-8
Thomas, K. R., Cook, S. E., Bondi, M. W., Unverzagt, F. W., Gross, A. L.,
Willis, S. L., & Marsiske, M. (2020). Application of neuropsychological
criteria to classify mild cognitive impairment in the active study.
Neuropsychology, 34(8), 862–873. https://doi.org/10.1037/neu0000694
Vargese, S. S., Jylhä, M., Raitanen, J., Enroth, L., Halonen, P., & Aaltonen, M.
(2023). Dementia-related disability in the population aged 90 years and
over: Differences over time and the role of comorbidity in the vitality 90+
study. BMC Geriatrics, 23(1), Article 276. https://doi.org/10.1186/s12877-
023-03980-5
Vuoksimaa, E., McEvoy, L. K., Holland, D., Franz, C. E., Kremen, W. S., &
the Alzheimer’s Disease Neuroimaging Initiative. (2020). Modifying the
minimum criteria for diagnosing amnestic MCI to improve prediction of
brain atrophy and progression to Alzheimer’s disease. Brain Imaging and
Behavior, 14(3), 787–796. https://doi.org/10.1007/s11682-018-0019-6
Vuoksimaa, E., Palviainen, T., Lindgren, N., Rinne, J. O., & Kaprio, J. (2020).
Accuracy of imputation for apolipoprotein E epsilon alleles in genome-wide
genotyping data. JAMA Network Open, 3(1), Article e1919960. https://
doi.org/10.1001/jamanetworkopen.2019.19960
Vuoksimaa, E., Saari, T. T., Aaltonen, A., Aaltonen, S., Herukka, S. K., Iso-
Markku, P., Kokkola, T., Kyttälä, A., Kärkkäinen, S., Liedes, H.,
Ollikainen, M., Palviainen, T., Ruotsalainen, I., Toivola, A., Urjansson,
M., Vasankari, T., Vähä-Ypyä, H., Forsberg, M. M., Hiltunen, M., … the
FinnGen. (2024). TWINGEN: Protocol for an observational clinical
biobank recall and biomarker cohort study to identify Finnish individuals
with high risk of Alzheimer’s disease. BMJ Open, 14(6), Article e081947.
https://doi.org/10.1136/bmjopen-2023-081947
Wagle, J., Selbæk, G., Benth, J. S., Gjøra, L., Rønqvist, T. K., Bekkhus-
Wetterberg, P., Persson, K., & Engedal, K. (2023). The CERAD Word List
Memory Test: Normative data based on a Norwegian population-based
sample of healthy older adults 70 years and above. The HUNT study.
Journal of Alzheimer’s Disease, 91(1), 321–343. https://doi.org/10.3233/
JAD-220672
Wechsler, D. (1997). Wechsler Memory Scale: Manual (3rd ed.). The
Psychological Corporation.
Wechsler, D. (2008). Wechsler Memory Scale (3rd ed.). Hogrefe.
Weintraub, S., Wicklund, A. H., & Salmon, D. P. (2012). The neuropsy-
chological profile of Alzheimer disease. Cold Spring Harbor Perspectives
in Medicine, 2(4), Article a006171. https://doi.org/10.1101/cshperspect
.a006171
Weissberger, G. H., Strong, J. V., Stefanidis, K. B., Summers, M. J., Bondi,
M. W., & Stricker, N. H. (2017). Diagnostic accuracy of memory measures
in Alzheimer’s dementia and mild cognitive impairment: A systematic
review and meta-analysis. Neuropsychology Review, 27(4), 354–388.
https://doi.org/10.1007/s11065-017-9360-6
Welsh, K. A., Breitner, J. C. S., & Magruder-Habib, K. M. (1993).
Detection of dementia in the elderly using telephone screening of
cognitive status. Neuropsychiatry, Neuropsychology, & Behavioral
Neurology, 6(2), 103–110.
Welsh, K. A., Butters, N., Hughes, J. P., Mohs, R. C., & Heyman, A. (1992).
Detection and staging of dementia in Alzheimer’s disease. Use of the
neuropsychological measures developed for the Consortium to Establish a
Registry for Alzheimer’s Disease. Archives of Neurology, 49(5), 448–452.
https://doi.org/10.1001/archneur.1992.00530290030008
Wetterberg, H., Najar, J., Rydberg Sterner, T., Rydén, L., Falk Erhag, H.,
Sacuiu, S., Kern, S., Zettergren, A., & Skoog, I. (2023). Decreasing
incidence and prevalence of dementia among octogenarians: A population-
based study on 3 cohorts born 30 years apart. The Journals of Gerontology:
Series A, 78(6), 1069–1077. https://doi.org/10.1093/gerona/glad071
Wilson, R. S., Leurgans, S. E., Foroud, T. M., Sweet, R. A., Graff-Radford,
N., Mayeux, R., Bennett, D. A., & the National Institute on Aging Late-
Onset Alzheimer’s Disease Family Study Group. (2010). Telephone
assessment of cognitive function in the late-onset Alzheimer’s disease
family study. Archives of Neurology, 67(7), 855–861. https://doi.org/10
.1001/archneurol.2010.129
Yaari, R., Fleisher, A. S., Gamst, A. C., Bagwell, V. P., & Thal, L. J. (2006).
Utility of the Telephone Interview for Cognitive Status for enrollment in
clinical trials. Alzheimer’s & Dementia, 2(2), 104–109. https://doi.org/10
.1016/j.jalz.2006.02.004"""

test6 = """
Abe, M., Suzuki, K., Okada, K., Miura, R., Fujii, T., Etsurou, M., &
Yamadori, A. (2004). Normative data on tests for frontal lobe functions:
Trail Making Test, verbal fluency, Wisconsin Card Sorting Test (Keio
version). No to Shinkei, 56(7), 567–574.
Abrams, R. C., Lachs, M., McAvay, G., Keohane, D. J., & Bruce, M. L.
(2002). Predictors of self-neglect in community-dwelling elders. The
American Journal of Psychiatry, 159(10), 1724–1730. https://doi.org/10
.1176/appi.ajp.159.10.1724
Arciniegas, D. B., Held, K., & Wagner, P. (2002). Cognitive impairment
following traumatic brain injury. Current Treatment Options in
Neurology, 4(1), 43–57. https://doi.org/10.1007/s11940-002-0004-6
Barker-Collo, S., Bennett, D. A., Krishnamurthi, R. V., Parmar, P., Feigin,
V. L., Naghavi, M., Forouzanfar, M. H., Johnson, C. O., Nguyen, G.,
Mensah, G. A., Vos, T., Murray, C. J., Roth, G. A., the GBD 2013 Writing
Group, & the GBD 2013 Stroke Panel Experts Group. (2015). Sex dif-
ferences in stroke incidence, prevalence, mortality and disability-adjusted
life years: Results from the Global Burden of Disease Study 2013.
Neuroepidemiology, 45(3), 203–214. https://doi.org/10.1159/000441103
Barrash, J., Bruss, J., Anderson, S. W., Kuceyeski, A., Manzel, K., Tranel,
D., & Boes, A. D. (2022). Lesions in different prefrontal sectors are
associated with different types of acquired personality disturbances.
Cortex, 147, 169–184. https://doi.org/10.1016/j.cortex.2021.12.004
Bates, E., Wilson, S. M., Saygin, A. P., Dick, F., Sereno, M. I., Knight, R. T.,
& Dronkers, N. F. (2003). Voxel-based lesion-symptom mapping. Nature
Neuroscience, 6(5), 448–450. https://doi.org/10.1038/nn1050
Bathgate, D., Snowden, J. S., Varma, A., Blackshaw, A., & Neary, D. (2001).
Behaviour in frontotemporal dementia, Alzheimer’s disease and vascular
dementia. Acta Neurologica Scandinavica, 103(6), 367–378. https://
doi.org/10.1034/j.1600-0404.2001.2000236.x
Becerra, L. R., Breiter, H. C., Stojanovic, M., Fishman, S., Edwards, A., Comite,
A. R., Gonzalez, R. G., & Borsook, D. (1999). Human brain activation under
controlled thermal stimulation and habituation to noxious heat: An fMRI
study. Magnetic Resonance in Medicine, 41(5), 1044–1057. https://doi.org/10
.1002/(SICI)1522-2594(199905)41:5<1044::AID-MRM25>3.0.CO;2-M
Bechara, A., & Damasio, H. (2002). Decision-making and addiction (part
I): Impaired activation of somatic states in substance dependent in-
dividuals when pondering decisions with negative future consequences.
Neuropsychologia, 40(10), 1675–1689. https://doi.org/10.1016/S0028-
3932(02)00015-5
Bielak, A. A. M., Hatt, C. R., & Diehl, M. (2017). Cognitive performance in
adults’ daily lives: Is there a lab-life gap? Research in Human Development,
14(3), 219–233. https://doi.org/10.1080/15427609.2017.1340050
Bouchama, A., Dehbi, M., Mohamed, G., Matthies, F., Shoukri, M., &
Menne, B. (2007). Prognostic factors in heat wave–related deaths: A meta-
analysis. Archives of Internal Medicine, 167(20), 2170–2176. https://
doi.org/10.1001/archinte.167.20.ira70009
Brunner, E., & Munzel, U. (2000). The nonparametric Behrens-Fisher problem:
Asymptotic theory and a small-sample approximation. Biometrical Journal,
42(1), 17–25. https://doi.org/10.1002/(SICI)1521-4036(200001)42:1<17::
AID-BIMJ17>3.0.CO;2-U
Burgess, P. W., Alderman, N., Evans, J., Emslie, H., & Wilson, B. A. (1998).
The ecological validity of tests of executive function. Journal of the
International Neuropsychological Society, 4(6), 547–558. https://doi.org/
10.1017/S1355617798466037
Cicerone, K. D., Goldin, Y., Ganci, K., Rosenbaum, A., Wethe, J. V.,
Langenbahn, D. M., Malec, J. F., Bergquist, T. F., Kingsley, K., Nagele, D.,
Trexler, L., Fraas, M., Bogdanova, Y., & Harley, J. P. (2019). Evidence-
based cognitive rehabilitation: Systematic review of the literature from
2009 through 2014. Archives of Physical Medicine and Rehabilitation,
100(8), 1515–1533. https://doi.org/10.1016/j.apmr.2019.02.011
Clar, H. E. (1985). Disturbances of the hypothalamic thermoregulation. Acta
Neurochirurgica, 75(1–4), 106–112. https://doi.org/10.1007/BF01406330
Coon, E. A., & Low, P. A. (2018). Thermoregulation in Parkinson disease. In
A. A. Romanovsky (Ed.), Handbook of clinical neurology (Vol. 157, pp. 715–
725). Elsevier. https://doi.org/10.1016/B978-0-444-64074-1.00043-4
Cubelli, R. (2017). Definition: Spatial neglect. Cortex, 92, 320–321. https://
doi.org/10.1016/j.cortex.2017.03.021
Damasio, A. R. (1994). Descartes’ error: Emotion, reason and the human
brain. Putnam.
De Tanti, A., Gasperini, G., & Rossini, M. (2005). Paroxysmal episodic
hypothalamic instability with hypothermia after traumatic brain injury. Brain
Injury, 19(14), 1277–1283. https://doi.org/10.1080/02699050500309270
de Vetten, L., & Bocca, G. (2013). Systemic effects of hypothermia due to
hypothalamic dysfunction after resection of a craniopharyngioma: Case
report and review of literature. Neuropediatrics, 44(3), 159–162. https://
doi.org/10.1055/s-0032-1327773
Demakis, G. J. (2003). A meta-analytic review of the sensitivity of the
Wisconsin Card Sorting Test to frontal and lateralized frontal brain
damage. Neuropsychology, 17(2), 255–264. https://doi.org/10.1037/0894-
4105.17.2.255
DiMicco, J. A., & Zaretsky, D. V. (2007). The dorsomedial hypothalamus: A
new player in thermoregulation. American Journal of Physiology-
Regulatory, Integrative and Comparative Physiology, 292(1), R47–R63.
https://doi.org/10.1152/ajpregu.00498.2006
El-Gamal, N., & Frank, S. M. (1995). Perioperative thermoregulatory
dysfunction in a patient with a previous traumatic hypothalamic injury.
Anesthesia and Analgesia, 80(6), 1245–1247. https://doi.org/10.1097/
00000539-199506000-00032
Fellows, L. K., & Farah, M. J. (2007). The role of ventromedial prefrontal
cortex in decision making: Judgment under uncertainty or judgment per se?
Cerebral Cortex, 17(11), 2669–2674. https://doi.org/10.1093/cercor/bhl176
Fletcher, P. D., Downey, L. E., Golden, H. L., Clark, C. N., Slattery, C. F.,
Paterson, R. W., Rohrer, J. D., Schott, J. M., Rossor, M. N., & Warren,
J. D. (2015). Pain and temperature processing in dementia: A clinical and
neuroanatomical analysis. Brain, 138(11), 3360–3372. https://doi.org/10
.1093/brain/awv276
Fong, H., Zheng, J., & Kurrasch, D. (2023). The structural and functional
complexity of the integrative hypothalamus. Science, 382(6669), 388–
394. https://doi.org/10.1126/science.adh8488
Fricke, C., & Voderholzer, U. (2023). Endocrinology of underweight and
anorexia nervosa. Nutrients, 15(16), Article 3509. https://doi.org/10.3390/
nu15163509
Funayama, M., Koreki, A., Takata, T., Nakagawa, Y., & Mimura, M. (2024).
Post-stroke urinary incontinence is associated with behavior control
deficits and overactive bladder. Neuropsychologia, 201, Article 108942.
https://doi.org/10.1016/j.neuropsychologia.2024.108942
Funayama, M., Mimura, M., Koshibe, Y., & Kato, Y. (2010). Squalor
syndrome after focal orbitofrontal damage. Cognitive and Behavioral
Neurology, 23(2), 135–139. https://doi.org/10.1097/WNN.0b013e
3181d746ba
Gonzalez-Escamilla, G., Chirumamilla, V. C., Meyer, B., Bonertz, T., von
Grotthus, S., Vogt, J., Stroh, A., Horstmann, J. P., Tüscher, O., Kalisch, R.,
Muthuraman, M., & Groppa, S. (2018). Excitability regulation in the
dorsomedial prefrontal cortex during sustained instructed fear responses:
A TMS-EEG study. Scientific Reports, 8(1), Article 14506. https://doi.org/
10.1038/s41598-018-32781-9
Gowda, R., Jaffa, M., & Badjatia, N. (2018). Thermoregulation in brain
injury. In A. A. Romanovsky (Ed.), Handbook of clinical neurology (Vol.
157, pp. 789–797). Elsevier. https://doi.org/10.1016/B978-0-444-64074-1
.00049-5
Grafman, J., Schwab, K., Warden, D., Pridgen, A., Brown, H. R., & Salazar,
A. M. (1996). Frontal lobe injuries, violence, and aggression: A report of
the Vietnam Head Injury Study. Neurology, 46(5), 1231–1238. https://
doi.org/10.1212/WNL.46.5.1231
Haller, S., Kovari, E., Herrmann, F. R., Cuvinciuc, V., Tomm, A. M., Zulian,
G. B., Lovblad, K. O., Giannakopoulos, P., & Bouras, C. (2013). Do brain
T2/FLAIR white matter hyperintensities correspond to myelin loss in
normal aging? A radiologic-neuropathologic correlation study. Acta
Neuropathologica Communications, 1, Article 14. https://actaneuroco
mms.biomedcentral.com/articles/10.1186/2051-5960-1-14#citeas
Hornberger, M., Yew, B., Gilardoni, S., Mioshi, E., Gleichgerrcht, E.,
Manes, F., & Hodges, J. R. (2014). Ventromedial-frontopolar prefrontal
cortex atrophy correlates with insight loss in frontotemporal dementia and
Alzheimer’s disease. Human Brain Mapping, 35(2), 616–626. https://
doi.org/10.1002/hbm.22200
Ideno, Y., Takayama, M., Hayashi, K., Takagi, H., & Sugai, Y. (2012).
Evaluation of a Japanese version of the Mini-Mental State Examination in
elderly persons. Geriatrics & Gerontology International, 12(2), 310–316.
https://doi.org/10.1111/j.1447-0594.2011.00772.x
Imai, Y., & Hasegawa, K. (1994). The Revised Hasegawa’s Dementia Scale
(HDS-R)—Evaluation of its usefulness as a screening test for dementia.
Journal of the Hong Kong College of Psychiatrists, 4(Suppl. 2), 20–24. https://
www.easap.asia/index.php/advanced-search/item/503-v4n2-9402-p20-24
Jang, W., Sohn, Y., Park, J. H., Pai, H., Kim, D. S., & Kim, B. (2021).
Clinical characteristics of patients with adrenal insufficiency and fever.
Journal of Korean Medical Science, 36(23), Article e152. https://doi.org/
10.3346/jkms.2021.36.e152
Kado, Y., Sanada, S., Yanagihara, M., Ogino, T., Abiru, K., & Nakano, K.
(2004). Effect of development and aging on the modified Wisconsin Card
Sorting Test in normal subjects. No to Hattatsu, 36(6), 475–480.
Karnath, H. O., Sperber, C., Wiesen, D., & de Haan, B. (2019). Lesion-
behavior mapping in cognitive neuroscience: A practical guide to uni-
variate and multivariate approaches. In S. Pollmann (Ed.), Spatial learning
and attention guidance (pp. 209–238). Humana Press. https://doi.org/10
.1007/7657_2019_18
Kashima, H. (2003). The Japanese version of behavioural assessment of the
dysexecutive syndrome. Shinko Igaku Shuppansha.
Kashima, H., & Kato, M. (1995). Wisconsin Card Sorting Test (Keio
version). Brain Science and Mental Disorders, 6, 209–216.
Katoh, S., Shimogaki, H., Onodera, A., Ueda, H., Oikawa, K., Ikeda, K.,
Ueda-Ishibashi, H., Kosaka, K., Imai, K., & Hasegawa, K. (1991).
Development of the Revised Version of Hasegawa’s Dementia Scale
(HDS-R). Journal of Geriatric Psychiatry, 2, 1339–1347.
Kibayashi, K., & Shojo, H. (2003). Accidental fatal hypothermia in elderly
people with Alzheimer’s disease. Medicine, Science, and the Law, 43(2),
127–131. https://doi.org/10.1258/rsmmsl.43.2.127
Knoch, D., & Fehr, E. (2007). Resisting the power of temptations: The right
prefrontal cortex and self-control. Annals of the New York Academy of
Sciences, 1104(1), 123–134. https://doi.org/10.1196/annals.1390.004
Kong, J., White, N. S., Kwong, K. K., Vangel, M. G., Rosman, I. S., Gracely,
R. H., & Gollub, R. L. (2006). Using fMRI to dissociate sensory encoding
from cognitive evaluation of heat pain intensity. Human Brain Mapping,
27(9), 715–721. https://doi.org/10.1002/hbm.20213
Kothari, R. U., Brott, T., Broderick, J. P., Barsan, W. G., Sauerbeck, L. R.,
Zuccarello, M., & Khoury, J. (1996). The ABCs of measuring intrace-
rebral hemorrhage volumes. Stroke, 27(8), 1304–1305. https://doi.org/10
.1161/01.str.27.8.1304
Kugo, A., Terada, S., Ata, T., Ido, Y., Kado, Y., Ishihara, T., Hikiji, M.,
Fujisawa, Y., Sasaki, K., & Kuroda, S. (2007). Japanese version of the
Frontal Assessment Battery for dementia. Psychiatry Research, 153(1),
69–75. https://doi.org/10.1016/j.psychres.2006.04.004
Luby, M., Hong, J., Merino, J. G., Lynch, J. K., Hsia, A. W., Magadán, A.,
Song, S. S., Latour, L. L., & Warach, S. (2013). Stroke mismatch volume
with the use of ABC/2 is equivalent to planimetric stroke mismatch
volume. American Journal of Neuroradiology, 34(10), 1901–1907.
https://doi.org/10.3174/ajnr.A3476
Martínez Dubarbie, F., López-García, S., Andrés-Gómez, M., Lage, C.,
Pozueta, A., García-Martínez, M., Kazimierczak, M., Bravo, M., Jiménez-
Bonilla, J., Banzo, I., Rodríguez-Rodríguez, E., & Sánchez-Juan, P.
(2020). Fatal consequences of decreased sensitivity to pain and temper-
ature in a frontotemporal dementia patient. Neurocase, 26(6), 364–367.
https://doi.org/10.1080/13554794.2020.1842464
Medina, J., Kimberg, D. Y., Chatterjee, A., & Coslett, H. B. (2010).
Inappropriate usage of the Brunner–Munzel test in recent voxel-based
lesion-symptom mapping studies. Neuropsychologia, 48(1), 341–343.
https://doi.org/10.1016/j.neuropsychologia.2009.09.016
Menon, V., & Uddin, L. Q. (2010). Saliency, switching, attention and
control: A network model of insula function. Brain Structure & Function,
214(5–6), 655–667. https://doi.org/10.1007/s00429-010-0262-0
Moeller, T. B., & Reif, E. (2020). Japanese version of pocket atlas of
sectional anatomy: Computed tomography and magnetic resonance
imaging (T. Machida, Trans.; 4th ed.). Thieme.
Nurmi, M. E., & Jehkonen, M. (2015). Recognition and rehabilitation of
impaired awareness of illness, i.e. anosognosia in a patient with cere-
brovascular disease. Duodecim, 131(3), 228–234.
Osilla, E. V., Marsidi, J. L., Shumway, K. R., & Sharma, S. (2023). Physiology,
temperature regulation. In StatPearls [Internet]. StatPearls Publishing.
Pavlou, M. P., & Lachs, M. S. (2008). Self-neglect in older adults: A primer
for clinicians. Journal of General Internal Medicine, 23(11), 1841–1846.
https://doi.org/10.1007/s11606-008-0717-7
Pfeiffer, R. F. (1990). Bromocriptine-induced hypothermia. Neurology,
40(2), Article 383. https://doi.org/10.1212/WNL.40.2.383
Pickens, S., Burnett, J., Trail Ross, M. E., Jones, E., & Jefferson, F. (2023).
Meeting the challenges in conducting research in vulnerable older adults
with self-neglect-notes from a field team. Frontiers in Medicine, 10,
Article 1114895. https://doi.org/10.3389/fmed.2023.1114895
Ponsford, J., & Kinsella, G. (1991). The use of a rating scale of attentional
behaviour. Neuropsychological Rehabilitation, 1(4), 241–257. https://
doi.org/10.1080/09602019108402257
Ratcliffe, P. J., Bell, J. I., Collins, K. J., Frackowiak, R. S., & Rudge, P.
(1983). Late onset post-traumatic hypothalamic hypothermia. Journal of
Neurology, Neurosurgery & Psychiatry, 46(1), 72–74. https://doi.org/10
.1136/jnnp.46.1.72
Reeves, M. J., Bushnell, C. D., Howard, G., Gargano, J. W., Duncan, P. W.,
Lynch, G., Khatiwoda, A., & Lisabeth, L. (2008). Sex differences in stroke:
Epidemiology, clinical presentation, medical care, and outcomes. The Lancet
Neurology, 7(10), 915–926. https://doi.org/10.1016/S1474-4422(08)70193-5
Ren, L., Gang, X., Yang, S., Sun, M., & Wang, G. (2022). A new perspective
of hypothalamic disease: Shapiro’s syndrome. Frontiers in Neurology, 13,
Article 911332. https://doi.org/10.3389/fneur.2022.911332
Rial-Pensado, E., Rivas-Limeres, V., Grijota-Martínez, C., Rodríguez-
Díaz, A., Capelli, V., Barca-Mayo, O., Nogueiras, R., Mittag, J.,
Diéguez, C., & López, M. (2022). Temperature modulates systemic
and central actions of thyroid hormones on BAT thermogenesis.
Frontiers in Physiology, 13, Article 1017381. https://doi.org/10.3389/
fphys.2022.1017381
Rorden, C., Karnath, H. O., & Bonilha, L. (2007). Improving lesion-
symptom mapping. Journal of Cognitive Neuroscience, 19(7), 1081–
1088. https://doi.org/10.1162/jocn.2007.19.7.1081
Rudebeck, P. H., & Murray, E. A. (2014). The orbitofrontal oracle: Cortical
mechanisms for the prediction and evaluation of specific behavioral
outcomes. Neuron, 84(6), 1143–1156. https://doi.org/10.1016/j.neuron
.2014.10.049
Rueckert, L., & Grafman, J. (1996). Sustained attention deficits in patients
with right frontal lesions. Neuropsychologia, 34(10), 953–963. https://
doi.org/10.1016/0028-3932(96)00016-4
Savioli, G., Ceresa, I. F., Bavestrello Piccini, G., Gri, N., Nardone, A., La
Russa, R., Saviano, A., Piccioni, A., Ricevuti, G., & Esposito, C. (2023).
Hypothermia: Beyond the narrative review—The point of view of emer-
gency physicians and medico-legal considerations. Journal of Personalized
Medicine, 13(12), Article 1690. https://doi.org/10.3390/jpm13121690
Senzaki, A., Edakubo, T., Hoshi, K., & Kato, M. (1997). The reliability and
validity of a clinical attentional scale. Sogo Rehabilitation, 25, 567–573.
https://doi.org/10.11477/mf.1552108403
Silva, R. V., Reis, C. M. S., & Novaes, M. R. C. G. (2015). Risk factors of
burn injury and prevention methods in the elderly. Revista Brasileira de
Cirurgia Plástica, 30(3), 461–467. https://doi.org/10.5935/2177-1235
.2015RBCP0179
Spaccavento, S., Marinelli, C. V., Nardulli, R., Macchitella, L., Bivona, U.,
Piccardi, L., Zoccolotti, P., & Angelelli, P. (2019). Attention deficits in
stroke patients: The role of lesion characteristics, time from stroke, and
concomitant neuropsychological deficits. Behavioural Neurology, 2019,
Article 7835710. https://doi.org/10.1155/2019/7835710
Stuss, D. T., & Levine, B. (2002). Adult clinical neuropsychology: Lessons
from studies of the frontal lobes. Annual Review of Psychology, 53(1),
401–433. https://doi.org/10.1146/annurev.psych.53.100901.135220
Stuss, D. T., Picton, T. W., & Alexander, M. P. (2001). Consciousness, self-
awareness, and the frontal lobes. In S. P. Salloway, P. F. Malloy, & J. D.
Duffy (Eds.), The frontal lobes and neuropsychiatric illness (pp. 101–
109). American Psychiatric Publishing.
Sugishita, M., Hemmi, I., & Takeuchi, T. (2016). Reexamination of the
validity and reliability of the Japanese version of the Mini-Mental State
Examination (MMSE–J). Japanese Journal of Cognitive Neuroscience,
18, 168–183. https://doi.org/10.11253/ninchishinkeikagaku.18.168
Sugishita, M., Koshizuka, Y., Sudou, S., Sugishita, K., Hemmi, I., Karasawa,
H., Ihara, M., Asada, T., & Mihara, B. (2018). The validity and reliability
of the Japanese version of the Mini-Mental State Examination (MMSE-J)
with the original procedure of the attention and calculation task (2001).
Japanese Journal of Cognitive Neuroscience, 20(2), 91–110. https://
doi.org/10.11253/ninchishinkeikagaku.20.91
Terneusen, A., Winkens, I., van Heugten, C., Stapert, S., Jacobs, H. I. L.,
Ponds, R., & Quaedflieg, C. (2023). Neural correlates of impaired self-
awareness of deficits after acquired brain injury: A systematic review.
Neuropsychology Review, 33(1), 222–237. https://doi.org/10.1007/
s11065-022-09535-6
Tyler, M. P., Wright, B. J., Raison, C. L., Lowry, C. A., Evans, L., & Hale,
M. W. (2024). Greater severity of depressive symptoms is associated with
changes to perceived sweating, preferred ambient temperature, and
warmth-seeking behavior. Temperature, 11(3), 266–279. https://doi.org/
10.1080/23328940.2024.2374097
Uniform Data System for Medical Rehabilitation. (1997). Guide for the
uniform data set for medical rehabilitation (including the FIM instrument)
(Version 5.1). State University of New York at Buffalo.
van Marum, R. J., Wegewijs, M. A., Loonen, A. J., & Beers, E. (2007).
Hypothermia following antipsychotic drug use. European Journal of
Clinical Pharmacology, 63(6), 627–631. https://doi.org/10.1007/s00228-
007-0294-4
von Salis, S., Ehlert, U., & Fischer, S. (2021). Altered experienced ther-
moregulation in depression—No evidence for an effect of early life stress.
Frontiers in Psychiatry, 12, Article 620656. https://doi.org/10.3389/fpsyt
.2021.620656
Watanuki, T., Hara, H., Miyamori, T., & Etoh, F. (2002). The Rivermead
behavioural memory test in Japanese. Chiba Test Center.
Wen, H. T., Rhoton, A. L., Jr., de Oliveira, E., Cardoso, A. C., Tedeschi, H.,
Baccanelli, M., & Marino, R., Jr. (1999). Microsurgical anatomy of the
temporal lobe: Part 1: Mesial temporal lobe anatomy and its vascular
relationships as applied to amygdalohippocampectomy. Neurosurgery,
45(3), 549–591. https://doi.org/10.1097/00006123-199909000-00028
Wheeler, D. S., Wan, S., Miller, A., Angeli, N., Adileh, B., Hu, W., &
Holland, P. C. (2014). Role of lateral hypothalamus in two aspects of
attention in associative learning. European Journal of Neuroscience,
40(2), 2359–2377. https://doi.org/10.1111/ejn.12592
Wheeler, M., Williams, O. A., Johns, L., Chiu, E. G., Slavkovab, E. D., &
Demeyere, N. (2023). Unravelling the complex interactions between self-
awareness, cognitive change, and mood at 6-months post-stroke using the
Y-shaped model. Neuropsychological Rehabilitation, 33(4), 680–702.
https://doi.org/10.1080/09602011.2022.2042329
Wilke, M., de Haan, B., Juenger, H., & Karnath, H. O. (2011). Manual, semi-
automated, and automated delineation of chronic brain lesions: A com-
parison of methods. NeuroImage, 56(4), 2038–2046. https://doi.org/10
.1016/j.neuroimage.2011.04.014
Wilson, B. A., Alderman, N., Burgess, P. W., Emslie, H., & Evans, J. J.
(1996). Behavioural assessment of the dysexecutive syndrome. Thames
Valley Test Company.
Zald, D. H., & Andreotti, C. (2010). Neuropsychological assessment of the
orbital and ventromedial prefrontal cortex. Neuropsychologia, 48(12),
3377–3391. https://doi.org/10.1016/j.neuropsychologia.2010.08.012
Zilles, K., Eickhoff, S., & Palomero-Gallagher, N. (2013). The human
parietal cortex: A novel approach to its architectonic mapping. In A. M.
Siegel, R. A. Andersen, H. J. Freund, & D. D. Spencer (Eds.), The parietal
lobes (pp. 1–22). Lippincott Williams & Wilkins."""

test7 = """Agelink van Rentergem, J. A., de Vent, N. R., Schmand, B. A., Murre, J. M. J.,
Staaks, J. P. C., Huizenga, H. M., Consortium, A., & the ANDI Consortium.
(2020). The factor structure of cognitive functioning in cognitively healthy
participants: A meta-analysis and meta-analysis of individual participant data.
Neuropsychology Review, 30(1), 51–96. https://doi.org/10.1007/s11065-019-
09423-6
Albert, M. S., DeKosky, S. T., Dickson, D., Dubois, B., Feldman, H. H., Fox,
N. C., Gamst, A., Holtzman, D. M., Jagust, W. J., Petersen, R. C., Snyder,
P. J., Carrillo, M. C., Thies, B., & Phelps, C. H. (2011). The diagnosis of
mild cognitive impairment due to Alzheimer’s disease: Recommendations
from the National Institute on Aging-Alzheimer’s Association work-
groups on diagnostic guidelines for Alzheimer’s disease. Alzheimer’s &
Dementia, 7(3), 270–279. https://doi.org/10.1016/j.jalz.2011.03.008
Bruderer-Hofstetter, M., Dubbelman, M. A., Meichtry, A., Koehn, F.,
Münzer, T., Jutten, R. J., Scheltens, P., Sikkes, S. A. M., & Niedermann,
K. (2020). Cross-cultural adaptation and validation of the Amsterdam
Instrumental Activities of Daily Living Questionnaire short version
German for Switzerland. Health and Quality of Life Outcomes, 18(1),
Article 323. https://doi.org/10.1186/s12955-020-01576-w
Byrne, B. (1994). Structural equation modeling with EQS and EQS win-
dows: Basic concepts, applications, and programming. SAGE
Publications.
Dubbelman, M. A., Jutten, R. J., Tomaszewski Farias, S. E., Amariglio,
R. E., Buckley, R. F., Visser, P. J., Rentz, D. M., Johnson, K. A., Properzi,
M. J., Schultz, A., Donovan, N., Gatchell, J. R., Teunissen, C. E., Van
Berckel, B. N. M., Van der Flier, W. M., Sperling, R. A., Papp, K. V.,
Scheltens, P., Marshall, G. A., … the Alzheimer Disease Neuroimaging
Initiative, National Alzheimer’s Coordinating Center, the Harvard Aging
Brain Study, the Alzheimer Dementia Cohort. (2020). Decline in cog-
nitively complex everyday activities accelerates along the Alzheimer’s
disease continuum. Alzheimer’s Research & Therapy, 12(1), Article 138.
https://doi.org/10.1186/s13195-020-00706-2
Dubbelman, M. A., Sikkes, S. A. M., Ebenau, J. L., van Leeuwenstijn,
M. S. S. A., Kroeze, L. A., Trieu, C., van Berckel, B. N. M., Teunissen, C. E.,
van Harten, A. C., & van der Flier, W. M. (2023). Changes in self- and study
partner-perceived cognitive functioning in relation to amyloid status and
future clinical progression: Findings from the SCIENCe project. Alzheimer’s
& Dementia, 19(7), 2933–2942. https://doi.org/10.1002/alz.12931
Dubbelman, M. A., Terwee, C. B., Verrijp, M., Visser, L. N. C., Scheltens, P.,
& Sikkes, S. A. M. (2022). Giving meaning to the scores of the Amsterdam
instrumental activities of Daily Living Questionnaire: A qualitative study.
Health and Quality of Life Outcomes, 20(1), Article 47. https://doi.org/10
.1186/s12955-022-01958-2
Dubbelman, M. A., Verrijp, M., Facal, D., Sánchez-Benavides, G., Brown,
L. J. E., van der Flier, W. M., Jokinen, H., Lee, A., Leroi, I., Lojo-Seoane,
C., Miloševi´c, V., Molinuevo, J. L., Pereiro Rozas, A. X., Ritchie, C.,
Salloway, S., Stringer, G., Zygouris, S., Dubois, B., Epelbaum, S., …
Sikkes, S. A. M. (2020). The influence of diversity on the measurement of
functional impairment: An international validation of the Amsterdam IADL
Questionnaire in eight countries. Alzheimer’s & Dementia, 12(1), Article
e12021. https://doi.org/10.1002/dad2.12021
Duits, F. H., Teunissen, C. E., Bouwman, F. H., Visser, P. J., Mattsson, N.,
Zetterberg, H., Blennow, K., Hansson, O., Minthon, L., Andreasen, N.,
Marcusson, J., Wallin, A., Rikkert, M. O., Tsolaki, M., Parnetti, L.,
Herukka, S. K., Hampel, H., De Leon, M. J., Schröder, J., … van der Flier,
W. M. (2014). The cerebrospinal fluid “Alzheimer profile”: Easily said,
but what does it mean? Alzheimer’s & Dementia, 10(6), 713–723. https://
doi.org/10.1016/j.jalz.2013.12.023
Epskamp, S. (n.d.). GitHub—SachaEpskamp/semPlot: Path diagrams and
visual analysis of various SEM packages’ output. https://github.com/Sa
chaEpskamp/semPlot
Farias, S. T., Harrell, E., Neumann, C., & Houtz, A. (2003). The relationship
between neuropsychological performance and daily functioning in in-
dividuals with Alzheimer’s disease: Ecological validity of neuropsycho-
logical tests. Archives of Clinical Neuropsychology, 18(6), 655–672. https://
doi.org/10.1016/S0887-6177(02)00159-2
Galvin, J. E., Cummings, J. L., Benea, M. L., de Moor, C., Allegri, R. F., Atri,
A., Chertkow, H., Paquet, C., Porter, V. R., Ritchie, C. W., Sikkes, S. A. M.,
Smith, M. R., Grassi, C. M., & Rubino, I. (2024). Generating real-world
evidence in Alzheimer’s disease: Considerations for establishing a core
dataset. Alzheimer’s & Dementia, 20(6), 4331–4341. https://doi.org/10
.1002/alz.13785
Gavett, B. E., Stypulkowski, K., Johnson, L., Hall, J., & O’Bryant, S. E.
(2018). Factor structure and measurement invariance of a neuropsycho-
logical test battery designed for assessment of cognitive functioning in older
Mexican Americans. Alzheimer’s & Dementia, 10(1), 536–544. https://
doi.org/10.1016/j.dadm.2018.08.003
Gross, A. L., Rebok, G. W., Unverzagt, F. W., Willis, S. L., & Brandt, J. (2011).
Cognitive predictors of everyday functioning in older adults: Results from the
ACTIVE Cognitive Intervention Trial. The Journals of Gerontology, Series
B: Psychological Sciences and Social Sciences, 66B(5), 557–566. https://
doi.org/10.1093/geronb/gbr033
Harvey, P. D. (2019). Domains of cognition and their assessment. Dialogues in
Clinical Neuroscience, 21(3), 227–237. https://doi.org/10.31887/DCNS
.2019.21.3/pharvey
Jack, C. R., Jr., Andrews, J. S., Beach, T. G., Buracchio, T., Dunn, B., Graf, A.,
Hansson, O., Ho, C., Jagust, W., McDade, E., Molinuevo, J. L., Okonkwo,
O. C., Pani, L., Rafii, M. S., Scheltens, P., Siemers, E., Snyder, H. M.,
Sperling, R., Teunissen, C. E., & Carrillo, M. C. (2024). Revised criteria for
diagnosis and staging of Alzheimer’s disease: Alzheimer’s association
workgroup. Alzheimer’s & Dementia, 20(8), 5143–5169. https://doi.org/10
.1002/alz.13859
Jekel, K., Damian, M., Wattmo, C., Hausner, L., Bullock, R., Connelly,
P. J., Dubois, B., Eriksdotter, M., Ewers, M., Graessel, E., Kramberger,
M. G., Law, E., Mecocci, P., Molinuevo, J. L., Nygård, L., Olde-Rikkert,
M. G., Orgogozo, J. M., Pasquier, F., Peres, K., … Frölich, L. (2015).
Mild cognitive impairment and deficits in instrumental activities of daily
living: A systematic review. Alzheimer’s Research & Therapy, 7(1),
Article 17. https://doi.org/10.1186/s13195-015-0099-0
Jessen, F., Amariglio, R. E., Buckley, R. F., van der Flier, W. M., Han, Y.,
Molinuevo, J. L., Rabin, L., Rentz, D. M., Rodriguez-Gomez, O., Saykin,
A. J., Sikkes, S. A. M., Smart, C. M., Wolfsgruber, S., & Wagner, M. (2020). The characterisation of subjective cognitive decline. Lancet Neurology,
19(3), 271–278. https://doi.org/10.1016/S1474-4422(19)30368-0
Jessen, F., Amariglio, R. E., van Boxtel, M., Breteler, M., Ceccaldi, M.,
Chételat, G., Dubois, B., Dufouil, C., Ellis, K. A., van der Flier, W. M.,
Glodzik, L., van Harten, A. C., de Leon, M. J., McHugh, P., Mielke,
M. M., Molinuevo, J. L., Mosconi, L., Osorio, R. S., Perrotin, A., … the
Subjective Cognitive Decline Initiative (SCD-I) Working Group. (2014).
A conceptual framework for research on subjective cognitive decline in
preclinical Alzheimer’s disease. Alzheimer’s & Dementia, 10(6), 844–
852. https://doi.org/10.1016/j.jalz.2014.01.001
Jutten, R. J., Harrison, J. E., Brunner, A. J., Vreeswijk, R., van Deelen, R. A. J.,
de Jong, F. J., Opmeer, E. M., Ritchie, C. W., Aleman, A., Scheltens, P., &
Sikkes, S. A. M. (2020). The cognitive-functional composite is sensitive to
clinical progression in early dementia: Longitudinal findings from the
Catch-Cog study cohort. Alzheimer’s & Dementia, 6(1), Article e12020.
https://doi.org/10.1002/trc2.12020
Jutten, R. J., Peeters, C. F. W., Leijdesdorff, S. M. J., Visser, P. J., Maier,
A. B., Terwee, C. B., Scheltens, P., & Sikkes, S. A. M. (2017). Detecting
functional decline from normal aging to dementia: Development and
validation of a short version of the Amsterdam IADL Questionnaire.
Alzheimer’s & Dementia, 8(1), 26–35. https://doi.org/10.1016/j.dadm
.2017.03.002
Kang, H., & Ahn, J. W. (2021). Model setting and interpretation of results in
research using structural equation modeling: A checklist with guiding
questions for reporting. Asian Nursing Research, 15(3), 157–162. https://
doi.org/10.1016/j.anr.2021.06.001
Kessels, R. P. C., & Brands, A. M. A. (2010). Neuropsychological assessment.
In G. J. Biessels & J. A. Luchsinger (Eds.), Diabetes and the brain (pp. 77–
102). Humana Press.
Kleineidam, L., Wagner, M., Guski, J., Wolfsgruber, S., Miebach, L., Bickel,
H., König, H. H., Weyerer, S., Lühmann, D., Kaduszkiewicz, H., Luppa,
M., Röhr, S., Pentzek, M., Wiese, B., Maier, W., Scherer, M., Kornhuber, J.,
Peters, O., Frölich, L., … Heser, K. (2023). Disentangling the relationship
of subjective cognitive decline and depressive symptoms in the develop-
ment of cognitive decline and dementia. Alzheimer’s & Dementia, 19(5),
2056–2068. https://doi.org/10.1002/alz.12785
Lechowski, L., de Stampa, M., Denis, B., Tortrat, D., Chassagne, P., Robert,
P., Teillet, L., & Vellas, B. (2008). Patterns of loss of abilities in instru-
mental activities of daily living in Alzheimer’s disease: The REAL cohort
study. Dementia and Geriatric Cognitive Disorders, 25(1), 46–53. https://
doi.org/10.1159/000111150
Lezak, M., Howieson, D., Bigler, E., & Tranel, D. (2012). Neuropsychological
assessment. Oxford University Press.
Lindeboom, J., & Matto, D. (1994). Digit series and Knox cubes as con-
centration tests for elderly subjects. Tijdschrift Voor Gerontologie En
Geriatrie, 25(2), 63–68.
Lindeboom, J., Schmand, B., Tulner, L., Walstra, G., & Jonker, C. (2002).
Visual association test to detect early dementia of the Alzheimer type. Journal
of Neurology, Neurosurgery, and Psychiatry, 73(2), 126–133. https://doi.org/
10.1136/jnnp.73.2.126
Luteijn, F., & van der Ploeg, F. A. E. (1982). GIT: Groninger Intelligentie
Test [Groningen Intelligence Test]. Swets & Zeitlinger.
Marshall, G. A., Sikkes, S. A. M., Amariglio, R. E., Gatchel, J. R., Rentz,
D. M., Johnson, K. A., Langford, O., Sun, C. K., Donohue, M. C., Raman,
R., Aisen, P. S., Sperling, R. A., Galasko, D. R., & the Full listing of A4
Study team and site personnel available at A4STUDY.org. (2020).
Instrumental activities of daily living, amyloid, and cognition in cogni-
tively normal older adults screening for the A4 Study. Alzheimer’s &
Dementia, 12(1), Article e12118. https://doi.org/10.1002/dad2.12118
Martyr, A., Ravi, M., Gamble, L. D., Morris, R. G., Rusted, J. M., Pentecost,
C., Matthews, F. E., Clare, L., & the IDEAL Study Team. (2024).
Trajectories of cognitive and perceived functional decline in people with
dementia: Findings from the IDEAL Programme. Alzheimer’s & Dementia,
20(1), 410–420. https://doi.org/10.1002/alz.13448
McKhann, G. M., Knopman, D. S., Chertkow, H., Hyman, B. T., Jack, C. R.,
Jr., Kawas, C. H., Klunk, W. E., Koroshetz, W. J., Manly, J. J., Mayeux,
R., Mohs, R. C., Morris, J. C., Rossor, M. N., Scheltens, P., Carrillo, M. C.,
Thies, B., Weintraub, S., & Phelps, C. H. (2011). The diagnosis of
dementia due to Alzheimer’s disease: Recommendations from the
National Institute on Aging-Alzheimer’s Association workgroups on
diagnostic guidelines for Alzheimer’s disease. Alzheimer’s & Dementia,
7(3), 263–269. https://doi.org/10.1016/j.jalz.2011.03.005
Meyers, J. E., & Meyers, K. R. (1995). Rey complex figure test under four
different administration procedures. The Clinical Neuropsychologist, 9(1),
63–67. https://doi.org/10.1080/13854049508402059
Nikula, S., Jylhä, M., Bardage, C., Deeg, D. J., Gindin, J., Minicuci, N.,
Pluijm, S. M., Rodríguez-Laso, A., & the CLESA Working Group. (2003).
Are IADLs comparable across countries? Sociodemographic associates of
harmonized IADL measures. Aging Clinical and Experimental Research,
15(6), 451–459. https://doi.org/10.1007/BF03327367
Nosheny, R. L., Jin, C., Neuhaus, J., Insel, P. S., Mackin, R. S., Weiner,
M. W., & the Alzheimer’s Disease Neuroimaging Initiative Investigators.
(2019). Study partner-reported decline identifies cognitive decline and
dementia risk. Annals of Clinical and Translational Neurology, 6(12),
2448–2459. https://doi.org/10.1002/acn3.50938
Nuño, L., Gómez-Benito, J., Carmona, V. R., & Pino, O. (2021). A sys-
tematic review of executive function and information processing speed in
major depression disorder. Brain Sciences, 11(2), Article 147. https://
doi.org/10.3390/brainsci11020147
Perry, R. J., & Hodges, J. R. (1999). Attention and executive deficits in
Alzheimer’s disease: A critical review. Brain: A Journal of Neurology,
122(3), 383–404. https://doi.org/10.1093/brain/122.3.383
Pillai, J. A., Bonner-Jackson, A., Walker, E., Mourany, L., & Cummings, J. L.
(2014). Higher working memory predicts slower functional decline in
autopsy-confirmed Alzheimer’s disease. Dementia and Geriatric Cognitive
Disorders, 38(3–4), 224–233. https://doi.org/10.1159/000362715
Postema, M. C., Dubbelman, M. A., Claesen, J., Ritchie, C., Verrijp, M.,
Visser, L., Visser, P. J., Zwan, M. D., van der Flier, W. M., & Sikkes,
S. A. M. (2024). Facilitating clinical use of the Amsterdam Instrumental
Activities of Daily Living Questionnaire: Normative data and a diagnostic
cutoff value. Journal of the International Neuropsychological Society,
30(6), 615–620. https://doi.org/10.1017/S1355617724000031
R Core Team. (2023). R: A language and environment for statistical
computing. R Foundation for Statistical Computing. https://www.R-proje
ct.org/
Rahman, A., Schmitter-Edgecombe, M., Krishnan, A., Cunningham, R.,
Pare, N., Beadle, J., Warren, D. E., & Rabin, L. (2025). Concurrent
validity of performance-based measures of daily functioning with cognitive
measures and informant reported everyday functioning. Archives of Clinical
Neuropsychology, 40(3), 363–374. https://doi.org/10.1093/arclin/acae077
Raimo, S., Maggi, G., Ilardi, C. R., Cavallo, N. D., Torchia, V., Pilgrom,
M. A., Cropano, M., Roldán-Tapia, M. D., & Santangelo, G. (2024). The
relation between cognitive functioning and activities of daily living in
normal aging, mild cognitive impairment, and dementia: A meta-analysis.
Neurological Sciences, 45(6), 2427–2443. https://doi.org/10.1007/s10072-
024-07366-2
Reitan, R. M., & Wolfson, D. (1995). Category test and Trail Making Test as
measures of frontal-lobe functions. The Clinical Neuropsychologist, 9(1),
50–56. https://doi.org/10.1080/13854049508402057
Reppermund, S., Sachdev, P. S., Crawford, J., Kochan, N. A., Slavin, M. J.,
Kang, K., Trollor, J. N., Draper, B., & Brodaty, H. (2011). The rela-
tionship of neuropsychological function to instrumental activities of daily
living in mild cognitive impairment. International Journal of Geriatric
Psychiatry, 26(8), 843–852. https://doi.org/10.1002/gps.2612
Rizzo, M., Anderson, S. W., Dawson, J., Myers, R., & Ball, K. (2000).
Visual attention impairments in Alzheimer’s disease. Neurology, 54(10),
1954–1959. https://doi.org/10.1212/WNL.54.10.1954
Rosseel, Y. (2012). lavaan: An R package for structural equation modeling.
Journal of Statistical Software, 48(2), 1–36. https://doi.org/10.18637/jss
.v048.i02
Royall, D. R., Lauterbach, E. C., Kaufer, D., Malloy, P., Coburn, K. L., Black,
K. J., & the Committee on Research of the American Neuropsychiatric
Association. (2007). The cognitive correlates of functional status: A review
from the committee on research of the American Neuropsychiatric
Association. The Journal of Neuropsychiatry and Clinical Neurosciences,
19(3), 249–265. https://doi.org/10.1176/jnp.2007.19.3.249
Royall, D. R., Palmer, R., Chiodo, L. K., & Polk, M. J. (2005). Executive control
mediates memory’s association with change in instrumental activities of daily
living: The Freedom House Study. Journal of the American Geriatrics Society,
53(1), 11–17. https://doi.org/10.1111/j.1532-5415.2005.53004.x
Sabbagh, M. N., Hendrix, S., & Harrison, J. E. (2019). FDA position statement
“early Alzheimer’s disease: Developing drugs for treatment, guidance for
industry”. Alzheimer’s & Dementia, 5(1), 13–19. https://doi.org/10.1016/j
.trci.2018.11.004
Samejima, F. (1969). Estimation of latent ability using a response pattern of
graded scores. Psychometrika, 34(Suppl. 1), 1–97. https://doi.org/10.1007/
BF03372160
Sikkes, S. A., de Lange-de Klerk, E. S., Pijnenburg, Y. A., Gillissen, F.,
Romkes, R., Knol, D. L., Uitdehaag, B. M., & Scheltens, P. (2012). A new
informant-based questionnaire for instrumental activities of daily living
in dementia. Alzheimer’s & Dementia, 8(6), 536–543. https://doi.org/10
.1016/j.jalz.2011.08.006
Sikkes, S. A., de Lange-de Klerk, E. S., Pijnenburg, Y. A., Scheltens, P., &
Uitdehaag, B. M. (2009). A systematic review of instrumental activities
of daily living scales in dementia: Room for improvement. Journal of
Neurology, Neurosurgery, and Psychiatry, 80(1), 7–12. https://doi.org/
10.1136/jnnp.2008.155838
Sikkes, S. A., Knol, D. L., Pijnenburg, Y. A., de Lange-de Klerk, E. S.,
Uitdehaag, B. M., & Scheltens, P. (2013). Validation of the Amsterdam
IADL Questionnaire, a new tool to measure instrumental activities of daily
living in dementia. Neuroepidemiology, 41(1), 35–41. https://doi.org/10
.1159/000346277
Sikkes, S. A., Pijnenburg, Y. A., Knol, D. L., de Lange-de Klerk, E. S.,
Scheltens, P., & Uitdehaag, B. M. (2013). Assessment of instrumental
activities of daily living in dementia: Diagnostic value of the Amsterdam
Instrumental Activities of Daily Living Questionnaire. Journal of Geriatric
Psychiatry and Neurology, 26(4), 244–250. https://doi.org/10.1177/08919
88713509139
Sikkes, S. A., & Rotrou, J. (2014). A qualitative review of instrumental
activities of daily living in dementia: What’s cooking? Neurodegenerative
Disease Management, 4(5), 393–400. https://doi.org/10.2217/nmt.14.24
Sperling, R. A., Aisen, P. S., Beckett, L. A., Bennett, D. A., Craft, S., Fagan,
A. M., Iwatsubo, T., Jack, C. R., Jr., Kaye, J., Montine, T. J., Park, D. C.,
Reiman, E. M., Rowe, C. C., Siemers, E., Stern, Y., Yaffe, K., Carrillo,
M. C., Thies, B., Morrison-Bogorad, M., … Phelps, C. H. (2011). Toward
defining the preclinical stages of Alzheimer’s disease: Recommendations
from the National Institute on Aging-Alzheimer’s Association workgroups
on diagnostic guidelines for Alzheimer’s disease. Alzheimer’s & Dementia,
7(3), 280–292. https://doi.org/10.1016/j.jalz.2011.03.003
Stroop, J. R. (1935). Studies of interference in serial verbal reactions. Journal
of Experimental Psychology, 18(6), 643–662. https://doi.org/10.1037/
h0054651
Tijms, B. M., Willemse, E. A. J., Zwan, M. D., Mulder, S. D., Visser, P. J.,
van Berckel, B. N. M., van der Flier, W. M., Scheltens, P., & Teunissen,
C. E. (2018). Unbiased approach to counteract upward drift in
cerebrospinal fluid Amyloid-β 1–42 analysis results. Clinical Chemistry,
64(3), 576–585. https://doi.org/10.1373/clinchem.2017.281055
van Buuren, S., & Groothuis-Oudshoorn, K. (2011). mice: Multivariate
imputation by chained equations in R. Journal of Statistical Software,
45(3), 1–67. https://doi.org/10.18637/jss.v045.i03
van der Elst, W., van Boxtel, M. P., van Breukelen, G. J., & Jolles, J. (2005).
Rey’s verbal learning test: Normative data for 1855 healthy participants
aged 24–81 years and the influence of age, sex, education, and mode of
presentation. Journal of the International Neuropsychological Society,
11(3), 290–302. https://doi.org/10.1017/S1355617705050344
van der Elst, W., van Boxtel, M. P., van Breukelen, G. J., & Jolles, J. (2006). The
Letter Digit Substitution Test: Normative data for 1,858 healthy participants
aged 24–81 from the Maastricht Aging Study (MAAS): Influence of age,
education, and sex. Journal of Clinical and Experimental Neuropsychology,
28(6), 998–1009. https://doi.org/10.1080/13803390591004428
van der Flier, W. M., & Scheltens, P. (2018). Amsterdam dementia cohort:
Performing research to optimize care. Journal of Alzheimer’s Disease,
62(3), 1091–1111. https://doi.org/10.3233/JAD-170850
van Harten, A. C., Wiste, H. J., Weigand, S. D., Mielke, M. M., Kremers,
W. K., Eichenlaub, U., Dyer, R. B., Algeciras-Schimnich, A., Knopman,
D. S., Jack, C. R., Jr., & Petersen, R. C. (2022). Detection of Alzheimer’s
disease amyloid beta 1–42, p-tau, and t-tau assays. Alzheimer’s &
Dementia, 18(4), 635–644. https://doi.org/10.1002/alz.12406
Vergara, I., Bilbao, A., Orive, M., Garcia-Gutierrez, S., Navarro, G., &
Quintana, J. M. (2012). Validation of the Spanish version of the Lawton
IADL Scale for its application in elderly people. Health and Quality of Life
Outcomes, 10(1), Article 130. https://doi.org/10.1186/1477-7525-10-130
Verhage, F., & Van Der Werff, J. J. (1964). An analysis of variance based on
the Groninger Intelligence Test scores. Nederlands Tijdschrift Voor de
Psychologie En Haar Grensgebieden, 19, 497–509.
Verrijp, M., Dubbelman, M. A., Visser, L. N. C., Jutten, R. J., Nijhuis, E. W.,
Zwan, M. D., van Hout, H. P. J., Scheltens, P., van der Flier, W. M., &
Sikkes, S. A. M. (2022). Everyday functioning in a community-based
volunteer population: Differences between participant- and study partner-
report. Frontiers in Aging Neuroscience, 13, Article 761932. https://
doi.org/10.3389/fnagi.2021.761932
Warrington, E. K., & James, M. (1991). The visual object and space per-
ception battery. Thames Valley Test Company.
Willemse, E. A. J., van Maurik, I. S., Tijms, B. M., Bouwman, F. H., Franke,
A., Hubeek, I., Boelaarts, L., Claus, J. J., Korf, E. S. C., van Marum, R. J.,
Roks, G., Schoonenboom, N., Verwey, N., Zwan, M. D., Wahl, S., van der
Flier, W. M., & Teunissen, C. E. (2018). Diagnostic performance of
Elecsys immunoassays for cerebrospinal fluid Alzheimer’s disease bio-
markers in a nonacademic, multicenter memory clinic cohort: The ABIDE
project. Alzheimer’s & Dementia, 10(1), 563–572. https://doi.org/10
.1016/j.dadm.2018.08.006
Wilson, B. A., Alderman, N., Burguess, P. W., Emslie, H., & Evans, J. J.
(1996). Behavioural Assessment of the Dysexecutive Syndrome (BADS).
Cognição.
Zlatar, Z. Z., Muniz, M., Galasko, D., & Salmon, D. P. (2018). Subjective
cognitive decline correlates with depression symptoms and not with
concurrent objective cognition in a clinic-based sample of older adults.
The Journals of Gerontology, Series B: Psychological Sciences and Social
Sciences, 73(7), 1198–1202. https://doi.org/10.1093/geronb/gbw207"""


test8 = """Babakhanyan, I., McKenna, B. S., Casaletto, K. B., Nowinski, C. J., &
Heaton, R. K. (2018). National Institutes of Health Toolbox Emotion
Battery for English- and Spanish-speaking adults: Normative data and
factor-based summary scores. Patient Related Outcome Measures, 9, 115–
127. https://doi.org/10.2147/PROM.S151658
Bomyea, J. A., Parrish, E. M., Paolillo, E. W., Filip, T. F., Eyler, L. T., Depp,
C. A., & Moore, R. C. (2021). Relationships between daily mood states
and real-time cognitive performance in individuals with bipolar disorder
and healthy comparators: A remote ambulatory assessment study. Journal
of Clinical and Experimental Neuropsychology, 43(8), 813–824. https://
doi.org/10.1080/13803395.2021.1975656
Campbell, L. M., Paolillo, E. W., Heaton, A., Tang, B., Depp, C. A.,
Granholm, E., Heaton, R. K., Swendsen, J., Moore, D. J., & Moore, R. C.
(2020). Daily activities related to mobile cognitive performance in middle-
aged and older adults: An ecological momentary cognitive assessment
study. JMIR mHealth and uHealth, 8(9), Article e19579. https://doi.org/10
.2196/19579
Cherner, M., Marquine, M. J., Umlauf, A., Morlett Paredes, A., Rivera
Mindt, M., Suárez, P., Yassai-Gonzalez, D., Kamalyan, L., Scott, T.,
Heaton, A., Diaz-Santos, M., Gooding, A., Artiola i Fortuny, L., &
Heaton, R. K. (2021). Neuropsychological norms for the U.S.–Mexico
border region in Spanish (NP-NUMBRS) project: Methodology and
sample characteristics. The Clinical Neuropsychologist, 35(2), 253–268.
https://doi.org/10.1080/13854046.2019.1709661
Chronister, B. N. C., Yang, K., Yang, A. R., Lin, T., Tu, X. M., Lopez-
Paredes, D., Checkoway, H., Suarez-Torres, J., Gahagan, S., Martinez, D.,
Barr, D., Moore, R. C., & Suarez-Lopez, J. R. (2023). Urinary glyphosate,
2,4-D and DEET biomarkers in relation to neurobehavioral performance in
Ecuadorian adolescents in the ESPINA cohort. Environmental Health
Perspectives, 131(10), Article 107007. https://doi.org/10.1289/EHP11383
Espinosa da Silva, C., Gahagan, S., Suarez-Torres, J., Lopez-Paredes, D.,
Checkoway, H., & Suarez-Lopez, J. R. (2022). Time after a peak-pesticide
use period and neurobehavior among Ecuadorian children and adoles-
cents: The ESPINA study. Environmental Research, 204, Article 112325.
https://doi.org/10.1016/j.envres.2021.112325
Hawks, Z. W., Beck, E. D., Jung, L., Fonseca, L. M., Sliwinski, M. J.,
Weinstock, R. S., Grinspoon, E., Xu, I., Strong, R. W., Singh, S., Van
Dongen, H. P. A., Frumkin, M. R., Bulger, J., Cleveland, M. J., Janess, K.,
Kudva, Y. C., Pratley, R., Rickels, M. R., Rizvi, S. R., … Germine, L. T.
(2024). Dynamic associations between glucose and ecological momentary
cognition in Type 1 Diabetes. NPJ Digital Medicine, 7(1), Article 59.
https://doi.org/10.1038/s41746-024-01036-5
Hyun, J., Sliwinski, M. J., & Smyth, J. M. (2019). Waking up on the wrong
side of the bed: The effects of stress anticipation on working memory in
daily life. The Journals of Gerontology: Series B, 74(1), 38–46. https://
doi.org/10.1093/geronb/gby042
Karr, J. E., Rivera Mindt, M., & Iverson, G. L. (2024). Interpreting reliable
change on the Spanish-language NIH Toolbox Cognition Battery. Applied
Neuropsychology: Adult, 31(3), 229–237. https://doi.org/10.1080/23279095
.2021.2011726
Karr, J. E., Scott, T. M., Aghvinian, M., & Rivera Mindt, M. (2023).
Harmonization of the English and Spanish versions of the NIH Toolbox
Cognition Battery crystallized and fluid composite scores. Neuropsychology,
37(3), 258–267. https://doi.org/10.1037/neu0000822
Marquine, M. J., Rivera Mindt, M., Umlauf, A., Suárez, P., Kamalyan, L.,
Morlett Paredes, A., Yassai-Gonzalez, D., Scott, T. M., Heaton, A.,
Diaz-Santos, M., Gooding, A., Artiola i Fortuny, L., Heaton, R. K., &
Cherner, M. (2021). Introduction to the neuropsychological norms for
the US–Mexico border region in Spanish (NP-NUMBRS) project. The
Clinical Neuropsychologist, 35(2), 227–235. https://doi.org/10.1080/
13854046.2020.1751882
Moore, R. C., Ackerman, R. A., Russell, M. T., Campbell, L. M., Depp,
C. A., Harvey, P. D., & Pinkham, A. E. (2022). Feasibility and validity of
ecological momentary cognitive testing among older adults with mild
cognitive impairment. Frontiers in Digital Health, 4, Article 946685.
https://doi.org/10.3389/fdgth.2022.946685
Moore, R. C., Parrish, E. M., Van Patten, R., Paolillo, E., Filip, T. F.,
Bomyea, J., Lomas, D., Twamley, E. W., Eyler, L. T., & Depp, C. A.
(2022). Initial psychometric properties of 7 NeuroUX remote ecological
momentary cognitive tests among people with bipolar disorder: Validation
study. Journal of Medical Internet Research, 24(7), Article e36665.
https://doi.org/10.2196/36665
Morlett Paredes, A., Carrasco, J., Kamalyan, L., Cherner, M., Umlauf, A.,
Rivera Mindt, M., Suarez, P., Artiola i Fortuny, L., Franklin, D., Heaton,
R. K., & Marquine, M. J. (2021). Demographically adjusted normative data
for the Halstead Category Test in a Spanish-speaking adult population:
Results from the neuropsychological norms for the U.S.–Mexico border
region in Spanish (NP-NUMBRS). The Clinical Neuropsychologist, 35(2),
356–373. https://doi.org/10.1080/13854046.2019.1709660
National Center for Environmental Health, National Center for Health
Statistics, & National Health and Nutrition Examination Survey. (2021).
Fourth national report on human exposure to environmental chemicals.
U.S. Department of Health and Human Services, Centers for Disease
Control and Prevention. https://www.cdc.gov/biomonitoring/resources/na
tional-exposure-report.html
Nguyen, K. T., Yu, J., Hedlin, H., Phillips, A. T., Desai, S., Cheung, L.,
Kowey, P. R., Jain, S. S., Rumsfeld, J. S., Russo, A. M., Granger, C. B.,
Hills, M. T., Desai, M., Mahaffey, K. W., Turakhia, M. P., & Perez, M. V.
(2025). Racial and ethnic representation and study engagement in a siteless
digital clinical trial using a smartwatch: Findings from the Apple Heart
Study. Mayo Clinic Proceedings: Digital Health, 3(3), Article 100232.
https://doi.org/10.1016/j.mcpdig.2025.100232
Nicosia, J., Aschenbrenner, A. J., Balota, D. A., Sliwinski, M. J., Tahan, M.,
Adams, S., Stout, S. S., Wilks, H., Gordon, B. A., Benzinger, T. L. S.,
Fagan, A. M., Xiong, C., Bateman, R. J., Morris, J. C., & Hassenstab, J.
(2023). Unsupervised high-frequency smartphone-based cognitive assess-
ments are reliable, valid, and feasible in older adults at risk for Alzheimer’s
disease. Journal of the International Neuropsychological Society, 29(5),
459–471. https://doi.org/10.1017/S135561772200042X
NIH Toolbox. (2021). Toolbox scoring and interpretation guide for iPad
v1.7. https://nihtoolbox.org
Paolillo, E. W., Bomyea, J., Depp, C. A., Henneghan, A. M., Raj, A., &
Moore, R. C. (2024). Characterizing performance on a suite of English-
language NeuroUX mobile cognitive tests in a US adult sample: Ecological
momentary cognitive testing study. Journal of Medical Internet Research,
26, Article e51978. https://doi.org/10.2196/51978
Parajuli, R. P., Chronister, B. N. C., Barr, D. B., & Suárez-López, J. R. (2025).
Urinary pesticide biomarkers from adolescence to young adulthood in an agricultural setting in Ecuador: Study of secondary exposure to pesticides
among children, adolescents, and adults (ESPINA) 2016 and 2022
examination data. Data in Brief, 61, Article 111882. https://doi.org/10
.1016/j.dib.2025.111882
Rivera Mindt, M., Marquine, M. J., Aghvinian, M., Paredes, A. M., Kamalyan,
L., Suárez, P., Heaton, A., Scott, T. M., Gooding, A., Diaz-Santos, M.,
Umlauf, A., Taylor, M. J., Artiola i Fortuny, L., Heaton, R. K., & Cherner,
M. (2021). The neuropsychological norms for the U.S.–Mexico border
region in Spanish (NP-NUMBRS) project: Overview and considera-
tions for life span research and evidence-based practice. The Clinical
Neuropsychologist, 35(2), 466–480. https://doi.org/10.1080/13854046
.2020.1794046
Singh, S., Strong, R., Xu, I., Fonseca, L. M., Hawks, Z., Grinspoon, E., Jung,
L., Li, F., Weinstock, R. S., Sliwinski, M. J., Chaytor, N. S., & Germine,
L. T. (2023). Ecological momentary assessment of cognition in clinical
and community samples: Reliability and validity study. Journal of Medical
Internet Research, 25, Article e45028. https://doi.org/10.2196/45028
Sliwinski, M. J., Smyth, J. M., Hofer, S. M., & Stawski, R. S. (2006).
Intraindividual coupling of daily stress and cognition. Psychology and
Aging, 21(3), 545–557. https://doi.org/10.1037/0882-7974.21.3.545
Suárez, P. A., Marquine, M. J., Díaz-Santos, M., Gollan, T., Artiola I
Fortuny, L., Rivera Mindt, M., Heaton, R., & Cherner, M. (2021). Native
Spanish-speaker’s test performance and the effects of Spanish-English
bilingualism: Results from the neuropsychological norms for the U.S.–
Mexico border region in Spanish (NP-NUMBRS) project. The Clinical
Neuropsychologist, 35(2), 453–465. https://doi.org/10.1080/13854046
.2020.1861330
Suarez-Lopez, J. R., Checkoway, H., Jacobs, D. R., Jr., Al-Delaimy, W. K.,
& Gahagan, S. (2017). Potential short-term neurobehavioral alterations in
children associated with a peak pesticide spray season: The Mother’s Day
flower harvest in Ecuador. Neurotoxicology, 60, 125–133. https://doi.org/
10.1016/j.neuro.2017.02.002
Suarez-Lopez, J. R., Himes, J. H., Jacobs, D. R., Jr., Alexander, B. H., &
Gunnar, M. R. (2013). Acetylcholinesterase activity and neurodevelop-
ment in boys and girls. Pediatrics, 132(6), e1649–e1658. https://doi.org/
10.1542/peds.2013-0108
Suarez-Lopez, J. R., Jacobs, D. R., Jr., Himes, J. H., Alexander, B. H.,
Lazovich, D., & Gunnar, M. (2012). Lower acetylcholinesterase activity
among children living with flower plantation workers. Environmental
Research, 114, 53–59. https://doi.org/10.1016/j.envres.2012.01.007
Suárez-López, J. R., Nazeeh, N., Kayser, G., Suárez-Torres, J.,
Checkoway, H., López-Paredes, D., Jacobs, D. R., Jr., & Cruz, F. (2020).
Residential proximity to greenhouse crops and pesticide exposure (via
acetylcholinesterase activity) assessed from childhood through adolescence.
Environmental Research, 188, Article 109728. https://doi.org/10.1016/j
.envres.2020.109728
Tang, W., He, H., & Tu, X. M. (2023). Applied categorical and count data
analysis (2nd ed.). Chapman & Hall/CRC. https://doi.org/10.1201/
9781003109815
Weizenbaum, E. L., Fulford, D., Torous, J., Pinsky, E., Kolachalama,
V. B., & Cronin-Golomb, A. (2022). Smartphone-based neuropsy-
chological assessment in Parkinson’s disease: Feasibility, validity, and
contextually driven variability in cognition. Journal of the International
Neuropsychological Society, 28(4), 401–413. https://doi.org/10.1017/
S1355617721000503
Weizenbaum, E. L., Torous, J., & Fulford, D. (2020). Cognition in context:
Understanding the everyday predictors of cognitive performance in a new
era of measurement. JMIR mHealth and uHealth, 8(7), Article e14328.
https://doi.org/10.2196/14328
Wilks, H., Aschenbrenner, A. J., Gordon, B. A., Balota, D. A., Fagan, A. M.,
Musiek, E., Balls-Berry, J., Benzinger, T. L. S., Cruchaga, C., Morris,
J. C., & Hassenstab, J. (2021). Sharper in the morning: Cognitive time of
day effects revealed with high-frequency smartphone testing. Journal of
Clinical and Experimental Neuropsychology, 43(8), 825–837. https://
doi.org/10.1080/13803395.2021.2009447
Zhaoyang, R., Scott, S. B., Martire, L. M., & Sliwinski, M. J. (2021). Daily
social interactions related to daily performance on mobile cognitive tests
among older adults. PLOS ONE, 16(8), Article e0256583. https://doi.org/
10.1371/journal.pone.0256583
Zheng, B. (2000). Summarizing the goodness of fit of generalized linear
models for longitudinal data. Statistics in Medicine, 19(10), 1265–1275.
https://doi.org/10.1002/(SICI)1097-0258(20000530)19:10<1265::AID-
SIM486>3.0.CO;2-U
Zlatar, Z. Z., Campbell, L. M., Tang, B., Gabin, S., Heaton, A., Higgins, M.,
Swendsen, J., Moore, D. J., & Moore, R. C. (2022). Daily level association
of physical activity and performance on ecological momentary cognitive
tests in free-living environments: A mobile health observational study.
JMIR mHealth and uHealth, 10(1), Article e33747. https://doi.org/10
.2196/33747"""

test9 = """Akter, S., Arnob, R. H., Ashik, M. A. U., & Rahman, M. M. (2025). Exposure to adverse childhood experiences and mental
health issues in a young-adult sample of university students in Bangladesh: A cross-sectional study. Health Science
Reports, 8(4), e70712. https://doi.org/10.1002/hsr2.70712
Albers, L. D., Grigsby, T. J., Benjamin, S. M., Rogers, C. J., Unger, J. B., & Forster, M. (2022). Adverse childhood experiences
and sleep difficulties among young adult college students. Journal of Sleep Research, 31(5), e13595. https://doi.org/10.
1111/jsr.13595
Arnett, J. J. (2000). Emerging adulthood: A theory of development from the late teens through the twenties. American
Psychologist, 55(5), 469–480. https://doi.org/10.1037/0003-066X.55.5.469
Arnett, J. J. (2014). Emerging adulthood: The winding road from the late teens through the twenties (2nd ed.). Oxford
University Press.
Bartolomé-Valenzuela, M., Pereda, N., & Guilera, G. (2024). Patterns of adverse childhood experiences and associations
with lower mental well-being among university students. Child Abuse & Neglect, 152, 106770. https://doi.org/10.1016/j.
chiabu.2024.106770
Beck, A. T. (1987). Cognitive models of depression. Journal of Cognitive Psychotherapy, 1(1), 5–37.
Beck, A. T., Rush, A. J., Shaw, B. F., & Emery, G. (1979). Cognitive therapy of depression. The Guilford Press.
Beckham, E. E., Leber, W. R., Watkins, J. T., Boyer, J. L., & Cook, J. B. (1986). Development of an instrument to measure
Beck’s cognitive triad: The cognitive triad Inventory. Journal of Consulting and Clinical Psychology, 54(4), 566–567.
https://doi.org/10.1037/0022-006X.54.4.566
Bhattarai, A., King, N., Adhikari, K., Dimitropoulos, G., Devoe, D., Byun, J., Li, M., Rivera, D., Cunningham, S., Bulloch, A. G. M.,
Patten, S. B., & Duffy, A. (2023). Childhood adversity and mental health outcomes among university students:
A longitudinal study. Canadian Journal of Psychiatry Revue Canadienne de Psychiatrie, 68(7), 510–520. https://doi.org/
10.1177/07067437221111368
Braet, C., Wante, L., Van Beveren, M. L., & Theuwis, L. (2015). Is the cognitive triad a clear marker of depressive symptoms in
youngsters? European Child and Adolescent Psychiatry, 24(10), 1261–1268. https://doi.org/10.1007/s00787-015-0674-8
Briere, J. N., & Elliott, D. M. (1994). Immediate and long-term impacts of child sexual abuse. The Future of Children, 4(2),
54–69. https://doi.org/10.2307/1602523
Calegaro, G., Soares, P. S. M., Colman, I., Murray, J., Wehrmeister, F. C., Menezes, A. M. B., & Gonçalves, H. (2023). Adverse
childhood experiences (ACEs) and suicidal behaviors in emerging adulthood: The 1993 Pelotas birth cohort. Child
Abuse & Neglect, 146, 106517. https://doi.org/10.1016/j.chiabu.2023.106517
Chang, E., & Chen, R. (2018). A study of depression factors in Taiwanese students of Department of Design. EURASIA
Journal of Mathematics, Science and Technology Education, 14(1), 197–204. https://doi.org/10.12973/ejmste/79632
Chang, X. N., Jiang, X. Y., Mkandarwire, T., & Shen, M. (2019). Associations between adverse childhood experiences and
health outcomes in adults aged 18-59 years. PLOS ONE, 14(2), e0211850. https://doi.org/10.1371/journal.pone.0211850
Chen, H., Fan, Q. Y., Nicholas, S., & Maitland, E. (2022). The long arm of childhood: The prolonged influence of adverse
childhood experiences on depression during middle and old age in China. Journal of Health Psychology, 27(10),
2373–2389. https://doi.org/10.1177/13591053211037727
Cheong, E. V., Sinnott, C., Dahly, D., & Kearney, P. M. (2017). Adverse childhood experiences (ACEs) and later-life
depression: Perceived social support as a potential protective factor. BMJ Open, 7(9), e013228. https://doi.org/10.
1136/bmjopen-2016-013228
Chien, C. P., & Cheng, T. A. (1985). Depression in Taiwan: Epidemiological survey utilizing CES-D. Seishin Shinkeigaku
Zasshi - Psychiatria et Neurologia Japonica, 87(5), 335–338.
Cohrdes, C., & Mauz, E. (2020). Self-efficacy and emotional stability buffer negative effects of adverse childhood
experiences on young adult health-related quality of life. Journal of Adolescent Health, 67(1), 93–100. https://doi.org/
10.1016/j.jadohealth.2020.01.005
Connor, K. M., & Davidson, J. R. T. (2003). Development of a new resilience scale: The Connor - Davidson resilience scale
(CD-RISC). Depression and Anxiety, 18, 76–82. https://doi.org/10.1002/da.10113
Craig, F., Servidio, R., Calomino, M. L., Candreva, F., Nardi, L., Palermo, A., Polito, A., Spina, M. F., Tenuta, F., & Costabile, A.
(2023). Adverse childhood experiences and mental health among students seeking psychological counseling services.
International Journal of Environmental Research and Public Health, 20(10), 5906. https://doi.org/10.3390/
ijerph20105906
Desch, J., Mansuri, F., Tran, D., Schwartz, S. W., & Bakour, C. (2023). The association between adverse childhood
experiences and depression trajectories in the Add Health study. Child Abuse & Neglect, 137, 106034. https://doi.org/
10.1016/j.chiabu.2023.106034
Didriksen, M., Daníelsdottir, H., Bjarnadóttir, M. D., Overstreet, C., Choi, K. W., Christoffersen, L. A. N., Mikkelsen, C.,
Aspelund, T., Hauksdóttir, A., Thordardottir, E. B., Jakobsdóttir, J., Tómasson, G., Erikstrup, C., Aagaard, B., Bruun, M. T.,
Ullum, H., Sørensen, E., Fischer, I. C., Pietrzak, R. H., . . . Schork, A. J. (2025). Psychometric properties and
socio-demographic correlates of the Connor-Davidson resilience scale in three large population-based cohorts
including Danish and Icelandic adults. Journal of Mood & Anxiety Disorders, 10, 100112. https://doi.org/10.1016/j.
xjmad.2025.100112
Diehl, J. M., Smoski, M. J., & Zimmerman, M. (2022). Emotion regulation difficulties link trait resilience and symptoms of
depression and anxiety in psychiatric outpatients. Annals of Clinical Psychiatry, 34(4), 253–262. https://doi.org/10.
12788/acp.0086
Dong, Y., Dang, L., Li, S., & Yang, X. (2021). Effects of facets of mindfulness on college adjustment among first-year Chinese
college students: The mediating role of resilience. Psychology Research and Behavior Management, 22(14), 1101–1109.
https://doi.org/10.2147/PRBM.S319145
Färber, F., & Rosendahl, J. (2020). Trait resilience and mental health in older adults: A meta-analytic review. Personality and
Mental Health, 14(4), 361–375. https://doi.org/10.1002/pmh.1490
Feiler, T., Vanacore, S., & Dolbier, C. (2023). Relationships among adverse and benevolent childhood experiences, emotion
dysregulation, and psychopathology symptoms. Adversity and Resilience Science, 4(3), 1–17. https://doi.org/10.1007/
s42844-023-00094-0
Felitti, V. J., Anda, R. F., Nordenberg, D., Williamson, D. F., Spitz, A. M., Edwards, V., Koss, M. P., & Marks, J. S. (1998).
Relationship of childhood abuse and household dysfunction to many of the leading causes of death in adults: The
adverse childhood experiences (ACE) study. American Journal of Preventive Medicine, 14(4), 245–258. https://doi.org/10.
1016/S0749-3797(98)00017-8
Felitti, V. J., Anda, R. F., Nordenberg, D., Williamson, D. F., Spitz, A. M., Edwards, V., Koss, M. P., & Marks, J. S. (2019).
Relationship of childhood abuse and household dysfunction to many of the leading causes of death in adults: The
adverse childhood experiences (ACE) study. American Journal of Preventive Medicine, 56(6), 774–786. https://doi.org/10.
1016/j.amepre.2019.04.001
Gibb, B. E. (2002). Childhood maltreatment and negative cognitive styles. A quantitative and qualitative review. Clinical
Psychology Review, 22(2), 223–246. https://doi.org/10.1016/s0272-7358(01)00088-5
Guo, L.-N., Zauszniewski, J. A., Ding, X.-F., Liu, Y.-C., Huang, L.-J., & Liu, Y.-J. (2017). Psychometric assessment of the
depressive cognitions scale among older Chinese people. Archives of Psychiatric Nursing, 31(5), 477–482. https://doi.
org/10.1016/j.apnu.2017.06.008
Hatami, A., Ghalati, Z. K., Badrani, M., Jahangirimehr, R. A., & Hemmatipour, A. (2019). The relationship between resilience
and perceived social support with hope in hemodialysis patients: A cross-sectional study. Journal of Research in
Medical and Dental Science, 7(3), 14–20.
Hazzard, V. M., Yoon, C., Emery, R. L., Mason, S. M., Crosby, R. D., Wonderlich, S. A., & Neumark-Sztainer, D. (2021). Adverse
childhood experiences in relation to mood-, weight-, and eating-related outcomes in emerging adulthood: Does
self-compassion play a buffering role? Child Abuse & Neglect, 122, 105307. https://doi.org/10.1016/j.chiabu.2021.
105307
Hernandez, S. H. A., Morgan, B. J., & Parshall, M. B. (2016). Resilience, stress, stigma, and barriers to mental healthcare in
U.S. Air Force nursing personnel. Nursing Research, 65(6), 481–486. https://doi.org/10.1097/NNR.0000000000000182
Herzog, J. I., & Schmahl, C. (2018). Adverse childhood experiences and the consequences on neurobiological, psychoso-
cial, and somatic conditions across the lifespan. Frontiers in Psychiatry, 9, 420. https://doi.org/10.3389/fpsyt.2018.00420
Ho, G. W. K., Chan, A. C. Y., Chien, W. T., Bressington, D. T., & Karatzias, T. (2019). Examining patterns of adversity in Chinese
young adults using the adverse childhood experiences-international questionnaire (ACE-IQ). Child Abuse and Neglect,
88, 179–188. https://doi.org/10.1016/j.chiabu.2018.11.009
Humphreys, K. L., LeMoult, J., Wear, J. G., Piersiak, H. A., Lee, A., & Gotlib, I. H. (2020). Child maltreatment and depression: A
meta-analysis of studies using the childhood trauma questionnaire. Child Abuse & Neglect, 102, 104361. https://doi.org/
10.1016/j.chiabu.2020.104361
Jacobs, L., & Joseph, S. (1997). Cognitive triad inventory and its association with symptoms of depression and anxiety in
adolescents. Personality and Individual Differences, 22(5), 769–770. https://doi.org/10.1016/S0191-8869(96)00257-7
Kim, Y. H. (2017). Associations of adverse childhood experiences with depression and alcohol abuse among Korean
college students. Child Abuse & Neglect, 67, 338–348. https://doi.org/10.1016/j.chiabu.2017.03.009
Korotana, L. M., Dobson, K. S., Pusch, D., & Josephson, T. (2016). A review of primary care interventions to improve health
outcomes in adult survivors of adverse childhood experiences. Clinical Psychology Review, 46, 59–90. https://doi.org/
10.1016/j.cpr.2016.04.007
Li, Y., & Zheng, P. (2025). Trait resilience protects against social anxiety in college students through emotion regulation
and coping strategies. Scientific Reports, 15, 28143. https://doi.org/10.1038/s41598-025-13674-0
Lynne, S. D., Fagan, A. A., Counts, T. M., Bryan, J. L., Kidd, J., & Fogarty, K. (2025). Buffering effects of positive childhood
experiences on the association between adolescents’ adverse childhood experiences and delinquency: A statewide
study. Child Abuse & Neglect, 163, 107325. https://doi.org/10.1016/j.chiabu.2025.107325
Madigan, S., Deneault, A. A., Racine, N., Park, J., Thiemann, R., Zhu, J., Dimitropoulos, G., Williamson, T., Fearon, P.,
Cénat, J. M., McDonald, S., Devereux, C., & Neville, R. D. (2023). Adverse childhood experiences: A meta-analysis of
prevalence and moderators among half a million adults in 206 studies. World Psychiatry: Official Journal of the World
Psychiatric Association (WPA), 22(3), 463–471. https://doi.org/10.1002/wps.21122
Madigan, S., Thiemann, R., Deneault, A. A., Fearon, R. M. P., Racine, N., Park, J., Lunney, C. A., Dimitropoulos, G., Jenkins, S.,
Williamson, T., & Neville, R. D. (2025). Prevalence of adverse childhood experiences in child population samples:
A systematic review and meta-analysis. JAMA Pediatrics, 179(1), 19–33. https://doi.org/10.1001/jamapediatrics.2024.
4385
Mak, W. W. S., Ng, I. S. W., & Wong, C. C. Y. (2011). Resilience: Enhancing well-being through the positive cognitive triad.
Journal of Counseling Psychology, 58(4), 610–617. https://doi.org/10.1037/a0025195
Muwanguzi, M., Kaggwa, M. M., Najjuka, S. M., Mamun, M. A., Arinaitwe, I., Kajjimu, J., Nduhuura, E., & Ashaba, S. (2023).
Exploring adverse childhood experiences (ACEs) among Ugandan university students: Its associations with academic
performance, depression, and suicidal ideations. BMC Psychology, 11(1), Article 11. https://doi.org/10.1186/s40359-
023-01044-2
Oral, R., Ramirez, M., Coohey, C., Nakada, S., Walz, A., Kuntz, A., Benoit, J., & Peek-Asa, C. (2016). Adverse childhood
experiences and trauma informed care: The future of health care. Pediatric Research, 79(1), 227–233. https://doi.org/10.
1038/pr.2015.197
Peng, L., Cao, H.-W., Yu, Y., & Li, M. (2017). Resilience and cognitive bias in Chinese male medical freshmen. Frontiers in
Psychiatry, 30(8), 158. https://doi.org/10.3389/fpsyt.2017.00158
Peng, M. M., & Liang, Z. R. (2023). Longitudinal associations between multiple types of adverse childhood experiences
and depression trajectories in middle-aged and older Chinese adults: A growth mixture model. International Journal of
Mental Health and Addiction, 23(2), 1616–1634. https://doi.org/10.1007/s11469-023-01188-7
Perrins, S. P., Vermes, E., Cincotta, K., Xu, Y., Godoy-Garraza, L., Chen, M. S., Addison, R., Douglas, B., Yatco, A.,
Idaikkadar, N., & Willis, L. A. (2024). Understanding forms of childhood adversities and associations with adult health
outcomes: A regression tree analysis. Child Abuse & Neglect, 153, 106844. https://doi.org/10.1016/j.chiabu.2024.106844
Poletti, S., Colombo, C., & Benedetti, F. (2014). Adverse childhood experiences worsen cognitive distortion during adult
bipolar depression. Comprehensive Psychiatry, 55(8), 1803–1808. https://doi.org/10.1016/j.comppsych.2014.07.013
Radloff, L. S. (1977). The CES-D scale: A self-report depression scale for research in the general population. Applied
Psychological Measurement, 1, 385–401. https://doi.org/10.1177/014662167700100306
Raghunathan, R. S., Johnson, S. B., Voegtline, K. M., Sosnowski, D. W., Kuehn, M., Ialongo, N. S., & Musci, R. J. (2024).
Longitudinal patterns of adversity from childhood to adolescence: Examining associations with mental health through
emerging adulthood using a random-intercept latent transition analysis. Developmental Psychology, 60(5), 840–857.
https://doi.org/10.1037/dev0001717
Ran, L., Wang, W., Ai, M., Kong, Y., Chen, J., & Kuanga, L. (2020). Psychological resilience, depression, anxiety, and
somatization symptoms in response to COVID-19: A study of the general population in China at the peak of its
epidemic. Social Science & Medicine, 262, 113261. https://doi.org/10.1016/j.socscimed.2020.113261
Ryan, R. M., & Deci, E. L. (2000). Self-determination theory and the facilitation of intrinsic motivation, social development,
and well-being. American Psychologist, 55(1), 68–78. https://doi.org/10.1037/0003-066X.55.1.68
Satinsky, E. N., Kakuhikire, B., Baguma, C., Rasmussen, J. D., Ashaba, S., Cooper-Vince, C. E., Perkins, J. M., Kiconco, A.,
Namara, E. B., Bangsberg, D. R., & Tsai, A. C. (2021). Adverse childhood experiences, adult depression, and suicidal
ideation in rural Uganda: A cross-sectional, population-based study. PLOS Medicine, 18(5), e1003642. https://doi.org/
10.1371/journal.pmed.1003642
Schulenberg, J. E., & Maggs, J. L. (2002). A developmental perspective on alcohol use and heavy drinking during
adolescence and the transition to young adulthood. Journal of Studies on Alcohol, Supplement, 14(s14), 54–70.
https://doi.org/10.15288/jsas.2002.s14.54
Shebuski, K., Bowie, J.-A., & Ashby, J. S. (2020). Self-compassion, trait resilience, and trauma exposure in undergraduate
students. Journal of College Counseling, 23(1), 2–14. https://doi.org/10.1002/jocc.12145
Sinclair, K. R., Cole, D. A., Dukewich, T., Felton, J., Weitlauf, A. S., Maxwell, M. A., Tilghman-Osborne, C., & Jacky, A. (2012).
Impact of physical and relational peer victimization on depressive cognitions in children and adolescents. Journal of
Clinical Child and Adolescent Psychology, 41(5), 570–583. https://doi.org/10.1080/15374416.2012.704841
Skaldere-Darmudasa, G., & Sudraba, V. (2023). Connor-Davidson resilience scale (CD-RISC-25) adaptation in Latvian
sample. Society Integration Education Proceedings of the International Scientific Conference, 2, 488–497. https://doi.
org/10.17770/sie2023vol2.7172
Stapleton, P., Mackay, E., Chatwin, H., Murphy, D., Porter, B., Thibault, S., Sheldon, T., & Pidgeon, A. (2017). Effectiveness of
a school-based emotional freedom techniques intervention for promoting student wellbeing. Adolescent Psychiatry, 7
(2), 112–126. https://doi.org/10.2174/2210676607666171101165425
Stark, K. D., Schmidt, K. L., & Joiner, T. E., Jr. (1996). Cognitive triad: Relationship to depressive symptoms, parents’
cognitive triad, and perceived parental messages. Journal of Abnormal Child Psychology, 24(5), 615–631. https://doi.
org/10.1007/BF01670103
Tamura, S., Suzuki, K., Ito, Y., & Fukawa, A. (2021). Factors related to the resilience and mental health of adult cancer patients:
A systematic review. Supportive Care in Cancer, 29(7), 3471–3486. https://doi.org/10.1007/s00520-020-05943-7
Tran, Q. A., Dunne, M. P., Vo, T. V., & Luu, N. H. (2015). Adverse childhood experiences and the health of university students
in eight provinces of Vietnam. Asia Pacific Journal of Public Health, 27(8 Suppl), 26S–32S. https://doi.org/10.1177/
1010539515589812
Wagnild, G. M., & Young, H. M. (1993). Development and psychometric evaluation of the resilience scale. Journal of
Nursing Measurement, 1(2), 165–178.
Wang, D., Jiang, Q. Y., Yang, Z. Q., & Choi, J. K. (2021). The longitudinal influences of adverse childhood experiences and
positive childhood experiences at family, school, and neighborhood on adolescent depression and anxiety. Journal of
Affective Disorders, 292, 542–551. https://doi.org/10.1016/j.jad.2021.05.108
Watt, T., Kim, S., Ceballos, N., & Norton, C. (2022). People who need people: The relationship between adverse childhood
experiences and mental health among college students. Journal of American College Health, 70(4), 1265–1273. https://
doi.org/10.1080/07448481.2020.1791882
Wider, W., Fauzi, M. A., Gan, S. W., Yap, C. C., Akmal Bin Ahmad Khadri, M. W., & Maidin, S. S. (2023). A bibliometric analysis
of emerging adulthood in the context of higher education institutions: A psychological perspectives. Heliyon, 9(6),
e16988. https://doi.org/10.1016/j.heliyon.2023.e16988
Windle, M., Haardorfer, R., Getachew, B., Shah, J., Payne, J., Pillai, D., & Berg, C. (2018). A multivariate analysis of adverse
childhood experiences and health behaviors and outcomes among college students. Journal of American College
Health, 66(4), 246–251. https://doi.org/10.1080/07448481.2018.1431892
Wood, D., Crapnell, T., Lau, L., Bennett, A., Lotstein, D., Ferris, M., & Kuo, A. (2017). Emerging adulthood as a critical stage in
the life course. In N. Halfon, C. B. Forrest, R. M. Lerner, & E. M. Faustman (Eds.), Handbook of life course health
development (pp. 123–143). Springer. https://doi.org/10.1007/978-3-319-47143-3_7
World Health Organization. (n.d). Adverse childhood experiences international questionnaire (ACE-IQ). https://www.who.
int/publications/m/item/adverse-childhood-experiences-international-questionnaire-(ace-iq)
Wu, Y., Sang, Z. Q., Zhang, X. C., & Margraf, J. (2020). The relationship between resilience and mental health in Chinese
college students: A longitudinal cross-lagged analysis. Frontiers in Psychology, 11, 108. https://doi.org/10.3389/fpsyg.
2020.00108
Yin, H. J., Zhu, Y., Tan, L. M., Zhong, X. L., & Yang, Q. (2024). The impact of adverse childhood experiences on depression in
middle and late life: A national longitudinal study. Journal of Affective Disorders, 351, 331–340. https://doi.org/10.1016/
j.jad.2024.01.132
Ying, L., Wu, X., Lin, C., & Jiang, L. (2014). Traumatic severity and trait resilience as predictors of posttraumatic stress
disorder and depressive symptoms among adolescent survivors of the Wenchuan earthquake. PLOS ONE, 9(2), Article
e89401. https://doi.org/10.1371/journal.pone.0089401"""

test10 = """Al-Zain, A. O., & Abdulsalam, S. (2022). Impact of grit, resilience, and stress levels on burnout and well-being of dental
students. Journal of Dental Education, 86(4), 443–455. https://doi.org/10.1002/jdd.12819
American Psychological Association. (2020). The road to resilience. https://www.apa.org/helpcenter/road-resilience
Anastasi, G., Gravante, F., Barbato, P., Bambi, S., Stievano, A., & Latina, R. (2025). Moral injury and mental health outcomes
in nurses: A systematic review. Nursing Ethics, 32(3), 698–723. https://doi.org/10.1177/09697330241281376
Andales, R. C., Capuno, R. M., Cerbas, M. K., Mulit, J., Embradora, K. J., & Bacatan, J. (2025). Grit and resilience as predictors
of psychological well-being among students. European Journal of Public Health Studies, 8(1). https://doi.org/10.46827/
ejphs.v8i1.206
Asheghi, M., & Hashemi, E. (2019). The relationship of mindfulness with burnout and adaptive performance with the
mediatory role of resilience among Iranian employees. Annals of Military and Health Sciences Research, 17(1), 1–7.
https://doi.org/10.5812/amh.87797
Askari, A., Borjaki, J., Mahdinasab, L., & Salehi Sahl Abadi, A. (2023). Relationship between demographic and employment
parameters with job stress among employees of an oil field in Western Iran. Spektrum Industri, 21(1), 2131. https://doi.org/10.
12928/si.v21i1.115
Bashlide, K. (2014). Research methods and statistical analysis of research examples with AMOS and SPSS. Shahid Chamran
University of Ahvaz Pub.
Bastami, E., Sayeh Miri, K., Bastami, T., & Cheraghizadegan, B. (2020). Prevalence of burnout in Iran: A systematic review
and meta-analysis. Prevalence of burnout in Iran: A systematic review and meta-analysis. Journal of Health Safety Work,
10(3), 301–315.
Bayani, A. A., Kouchaki, A. M., & Bayani, A. (2008). Reliability and validity of Ryff’s Psychological Well-being Scales. Iranian
Journal of Psychiatry and Clinical Psychology, 14(2 (53)), 146–151. https://sid.ir/paper/16645/en
Beddoe, L., Davys, A., & Adamson, C. (2013). Educating resilient practitioners. Social Work Education, 32(1), 100–117.
https://doi.org/10.1080/02615479.2011.644532
Bentler, P. M., & Bonett, D. G. (1980). Significance tests and goodness of fit in the analysis of covariance structures.
Psychological Bulletin, 88(3), 588. https://doi.org/10.1037/0033-2909.88.3.588
Bowman, N. A., Hill, P. L., Denson, N., & Bronkema, R. (2015). Keep on truckin’ or stay the course? Exploring grit dimensions
as differential predictors of educational achievement, satisfaction, and intentions. Social Psychological and Personality
Science, 6(6), 639–645. https://doi.org/10.1177/1948550615574300
Brateanu, A., Switzer, B., Scott, S. C., Ramsey, J., Thomascik, J., Nowacki, A. S., & Colbert, C. Y. (2020). Higher grit scores
associated with less burnout in a cohort of internal medicine residents. The American Journal of the Medical Sciences,
360(4), 357–362. https://doi.org/10.1016/j.amjms.2020.05.045
Cassidy, S. (2015). Resilience building in students: The role of academic self-efficacy. Frontiers in Psychology, 6, 1781.
https://doi.org/10.3389/fpsyg.2015.01781
Connor, K. M., & Davidson, J. R. (2003). Development of a new resilience scale: The Connor-Davidson Resilience Scale
(CD-RISC). Depression and Anxiety, 18(2), 76–82. https://doi.org/10.1002/da.10113
Credé, M., Tynan, M. C., & Harms, P. D. (2017). Much ado about grit: A meta-analytic synthesis of the grit literature. Journal
of Personality and Social Psychology, 113(3), 492. https://doi.org/10.1037/pspp0000102
Dam, A., Perera, T., Jones, M., Haughy, M., & Gaeta, T. (2019). The relationship between grit, burnout, and well-being in
emergency medicine residents. AEM Education and Training, 3(1), 14–19. https://doi.org/10.1002/aet2.10311
Duckworth, A. (2016). Grit: The power of passion and perseverance (Vol. 234). Scribner.
Duckworth, A. L., & Gross, J. J. (2014). Self-control and grit. Current Directions in Psychological Science, 23(5), 319–325.
https://doi.org/10.1177/0963721414541462
Duckworth, A. L., Peterson, C., Matthews, M. D., & Kelly, D. R. (2007). Grit: Perseverance and passion for long-term goals.
Journal of Personality and Social Psychology, 92(6), 1087–1101. https://doi.org/10.1037/0022-3514.92.6.1087
Duckworth, A. L., & Quinn, P. D. (2009). Development and validation of the short grit scale (Grit-S). Journal of Personality
Assessment, 91(2), 166–174. https://doi.org/10.1080/00223890802634290
Dursun, P. (2012). The role of meaning in life, optimism, hope and coping styles in subjective well-being [Doctoral
dissertation]. Middle East Technical University (Turkey).
Feldman, D. B., Rand, K. L., & Kahle-Wrobleski, K. (2009). Hope and goal attainment: Testing a basic prediction of hope
theory. Journal of Social and Clinical Psychology, 28(4), 479–497. https://doi.org/10.1521/jscp.2009.28.4.479
Fredrickson, B. L. (2001). The role of positive emotions in positive psychology: The broaden-and-build theory of positive
emotions. American Psychologist, 56(3), 218. https://doi.org/10.1037/0003-066X.56.3.218
Garmezy, N. (1985). Stress-resistant children: The search for protective factors. Recent Research in Developmental
Psychopathology, 4(19), 213–233.
Georgoulas-Sherr, V., & Kelly, D. R. (2019). Resilience, grit, and hardiness: Determining the relationships amongst these
constructs through structural equation modeling techniques. Journal of Positive Psychology and Wellbeing, 3(1), 165–178.
Gravante, F., Pucciarelli, G., Sperati, F., Cecere, L., Anastasi, G., Mancin, S., & Latina, R. (2025). Risk factors of anxiety,
depression, stress, job burnout, and characteristics of sleep disorders in critical care nurses: An observational study.
Australian Critical Care, 38(3), 101165. https://doi.org/10.1016/j.aucc.2024.101165
Grotberg, E. H. (2003). What is resilience? How do you promote it? How do you use it. In Resilience for today: Gaining
strength from adversity (Vol. 2, pp. 1–30).
He, F. X., Turnbull, B., Kirshbaum, M. N., Phillips, B., & Klainin-Yobas, P. (2018). Assessing stress, protective factors and
psychological well-being among undergraduate nursing students. Nurse Education Today, 68, 4–12. https://doi.org/10.
1016/j.nedt.2018.05.013
Hefferon, K., & Boniwell, I. (2011). Positive psychology: Theory, research and applications. McGraw-Hill Education (UK).
Herrman, H., Stewart, D. E., Diaz-Granados, N., Berger, E. L., Jackson, B., & Yuen, T. (2011). What is resilience? The Canadian
Journal of Psychiatry, 56(5), 258–265. https://doi.org/10.1177/070674371105600504
Hill, P. L., Burrow, A. L., & Bronk, K. C. (2014). Persevering with positivity and purpose: An examination of purpose
commitment and positive affect as predictors of grit. Journal of Happiness Studies, 17, 257–269. https://doi.org/10.
1007/s10902-014-9593-5
Hoboubi, N., Choobineh, A., Kamari Ghanavati, F., Keshavarzi, S., & Hosseini, A. A. (2017). The impact of job stress and job
satisfaction on workforce productivity in an Iranian petrochemical industry. Safety and Health at Work, 8(1), 67–71.
https://doi.org/10.1016/j.shaw.2016.07.002
Ingram, R. E., & Price, J. M. (2001). The role of vulnerability in understanding psychopathology. Biological Psychiatry, 49(7),
624–636. https://doi.org/10.1016/s0006-3223(00)01024-6
Jaureguizar, J., Garaigordobil, M., & Bernaras, E. (2018). Self-concept, social skills, and resilience as moderators of the
relationship between stress and childhood depression. School Mental Health, 10(4), 488–499. https://doi.org/10.1007/
s12310-018-9268-1
Jin, B., & Kim, J. (2017). Grit, basic needs satisfaction, and subjective well-being. Journal of Individual Differences, 38(1),
29–35. https://doi.org/10.1027/1614-0001/a000219
Kardas, F., Zekeriya, C. A. M., Eskisu, M., & Gelibolu, S. (2019). Gratitude, hope, optimism and life satisfaction as predictors of
psychological well-being. Eurasian Journal of Educational Research, 19(82), 1–20. https://doi.org/10.14689/ejer.2019.82.5
Katsiroumpa, A., Moisoglou, I., Konstantakopoulou, O., Katsoulas, T., Gallos, P., & Galanis, P. (2023). Resilience and social
support decrease job burnout and COVID-19-related burnout in the general population, three years after the
COVID-19 pandemic. Internation Journal of Caring Sciences, 16, 1192–1204. https://doi.org/10.1016/j.jrp.2013.04.007
Kleiman, E. M., Adams, L. M., Kashdan, T. B., & Riskind, J. H. (2013). Gratitude and grit indirectly reduce risk of suicidal
ideations by enhancing meaning in life: Evidence for a mediated moderation model. Journal of Research in Personality,
47(5), 539–546. https://doi.org/10.1016/j.jrp.2013.04.007
Lee, H. H., & Cranford, J. A. (2008). Does resilience moderate the associations between parental problem drinking and
adolescents’ internalizing and externalizing behaviors? A study of Korean adolescents. Drug and Alcohol Dependence,
96(3), 213–221. https://doi.org/10.1016/j.drugalcdep.2008.03.007
Lee, Y. R., Lee, J. Y., Kim, J. M., Shin, I. S., Yoon, J. S., & Kim, S. W. (2019). A comparative study of burnout, stress, and
resilience among emotional workers. Psychiatry Investigation, 16(9), 686. https://doi.org/10.30773/pi.2019.07.10
Lewis, S. (2014). The rise: Creativity, the gift of failure, and the search for mastery. Simon & Schuster. https://doi.org/10.5860/
choice.186031
Li, Z. S., & Hasson, F. (2020). Resilience, stress, and psychological well-being in nursing students: A systematic review.
Nurse Education Today, 90, 104440. https://doi.org/10.1016/j.nedt.2020.104440
Luthans, F., Avolio, B. J., Avey, J. B., & Norman, S. M. (2007). Positive psychological capital: Measurement and relationship with
performance and satisfaction. Personnel Psychology, 60(3), 541–572. https://doi.org/10.1111/j.1744-6570.2007.00083.x
Marques, S. C., Pais-Ribeiro, J. L., & Lopez, S. J. (2011). The role of positive psychology constructs in predicting mental
health and academic achievement in children and adolescents: A two-year longitudinal study. Journal of Happiness
Studies, 12(6), 1049–1062. https://doi.org/10.1007/s10902-010-9244-4
Maslach, C., & Jackson, S. E. (1981). The measurement of experienced burnout. Journal of Organizational Behavior, 2(2),
99–113. https://doi.org/10.1002/job.4030020205
Maslach, C., & Jackson, S. E. (1984). Patterns of burnout among a national sample of public contact workers. Journal of
Health and Human Resources Administration, 189–212.
Masten, A. S. (2001). Ordinary magic: Resilience processes in development. American Psychologist, 56(3), 227. https://doi.
org/10.1037/0003-066X.56.3.227
Mohammadi, M. (2005). Comparison factors effect on resiliency on individuals at drug abuse risk [Doctoral dissertation, PhD
thesis]. Welfare and Rehabilitation University.
Mokarami, H., Cousins, R., & Choobineh, A. (2021). Understanding job stress in the Iranian oil industry: A qualitative
analysis based on the work systems model and macroergonomics approach. Applied Ergonomics, 94, 103407. https://
doi.org/10.1016/j.apergo.2021.103407
Nagarajan, R., Ramachandran, P., Dilipkumar, R., & Kaur, P. (2024). Global estimate of burnout among the public health
workforce: A systematic review and meta-analysis. Human Resources for Health, 22(1), 30. https://doi.org/10.1186/
s12960-024-00917-w
Nantsupawat, A., Kutney-Lee, A., Abhicharttibutra, K., Wichaikhum, O. A., & Poghosyan, L. (2024). Exploring the relationships
between resilience, burnout, work engagement, and intention to leave among nurses in the context of the COVID-19
pandemic: A cross-sectional study. BMC Nursing, 23(1), 290. https://doi.org/10.1186/s12912-024-01958-1
Reichard, R. J., Avey, J. B., Lopez, S., & Dollwet, M. (2013). Having the will and finding the way: A review and
meta‑analysis of hope at work. The Journal of Positive Psychology, 8(4), 292–304. https://doi.org/10.1080/17439760.
2013.800903
Ríos-Risquez, M. I., García-Izquierdo, M., Sabuco-Tebar, E. D. L. Á., Carrillo-Garcia, C., & Solano-Ruiz, C. (2018). Connections
between academic burnout, resilience, and psychological well-being in nursing students: A longitudinal study. Journal
of Advanced Nursing, 74(12), 2777–2784. https://doi.org/10.1111/jan.13794
Rogers, C. R. (1964). Toward a modern approach to values: The valuing process in the mature person. The Journal of
Abnormal and Social Psychology, 68(2), 160. https://doi.org/10.1037/h0046419
Ryff, C. D. (1989). Happiness is everything, or is it? Explorations on the meaning of psychological well-being. Journal of
Personality and Social Psychology, 57(6), 1069. https://doi.org/10.1037/0022-3514.57.6.1069
Ryff, C. D., & Singer, B. (2003). Flourishing under fire: Resilience as a prototype of challenged thriving.
Salles, A., Cohen, G. L., & Mueller, C. M. (2014). The relationship between grit and resident well-being. The American
Journal of Surgery, 207(2), 251–254. https://doi.org/10.1016/j.amjsurg.2013.09.006
Schaufeli, W. B., Maslach, C., & Marek, T. (2017). The future of burnout. In Professional burnout (pp. 253-259). Routledge.
Sheridan, Z., Boman, P., Mergler, A., & Furlong, M. J. (2015). Examining well-being, anxiety, and self-deception in university
students. Cogent Psychology, 2(1), 1–17. https://doi.org/10.1080/23311908.2014.993850
Snyder, C. R. (1994). The psychology of hope: You can get there from here. Simon and Schuster.
Snyder, C. R. (Ed.). (2000). Handbook of hope: Theory, measures, and applications. Academic Press.
Stoffel, J. M., & Cain, J. (2018). Review of grit and resilience literature within health professions education. American
Journal of Pharmaceutical Education, 82(2), 6150. https://doi.org/10.5688/ajpe6150
Strolin-Goltzman, J., Kollar, S., Shea, K., Walcott, C., & Ward, S. (2016). Building a landscape of resilience after workplace
violence in public child welfare. Children and Youth Services Review, 71, 250–256. https://doi.org/10.1016/j.childyouth.
2016.11.001
Tedeschi, R. G., Park, C. L., & Calhoun, L. G. (Eds.). (1998). Posttraumatic growth: Positive changes in the aftermath of crisis.
Routledge.
Vainio, M. M., & Daukantaitė, D. (2016). Grit and different aspects of well-being: Direct and indirect relationships via sense of
coherence and authenticity. Journal of Happiness Studies, 17(5), 2119–2147. https://doi.org/10.1007/s10902-015-9688-7
Vela, J. C., Smith, W. D., Whittenberg, J. F., Guardiola, R., & Savage, M. (2018). Positive psychology factors as predictors of
Latina/o college students’ psychological grit. Journal of Multicultural Counseling and Development, 46(1), 2–19. https://
doi.org/10.1002/jmcd.12089
Waxman, H. C., Gray, J. P., & Padron, Y. N. (2003). Review of research on educational resilience.
World Health Organization. (2024). Burn-out an “occupational phenomenon”: International Classification of Diseases.
Retrieved May 28, 2019, from https://www.who.int/news/item/28-05-2019-burn-out-an-occupational-phenomenon-
international-classification-of-disease
Yavas, U., Babakus, E., & Karatepe, O. M. (2013). Does hope moderate the impact of job burnout on frontline bank
employees’ in-role and extra-role performances? International Journal of Bank Marketing, 31(1), 56–70. https://doi.org/
10.1108/02652321311292056
Youssef, C. M., & Luthans, F. (2007). Positive organizational behavior in the workplace: The impact of hope, optimism, and
resilience. Journal of Management, 33(5), 774–800. https://doi.org/10.1177/0149206307305562"""

test11 = """Andersson, E., McIlduff, C., Turner, K. M., Carter, E., Hand, M., Thomas, S., Davies, J., Einfeld, S., & Elliott, E. J. (2024). Jandu
yani u (for all families): Evaluating Indigenous Triple P, a community-tailored parenting support program in remote
Aboriginal communities. Australian Psychologist, 59(3), 245–259. https://doi.org/10.1080/00050067.2023.2267159
Atkinson, J. (2002). Trauma trails, recreating song lines: The transgenerational effects of trauma in Indigenous Australia.
Spinifex Press.
Australian Institute of Family Studies. (1993). Aboriginal family issues. https://aifs.gov.au/research/family-matters/no-35/
aboriginal-family-issues
Australian Institute of Health and Welfare. (2024). Determinants of health for First Nations people. Australia’s Health.
Retrieved August 7, 2025, from https://www.aihw.gov.au/reports/australias-health/social-determinants-and-
indigenous-health
Bailey, N., & Clark, C. (2024). Exploring bonding and attachment in Aboriginal families. Australian Journal of Psychology, 76
(1), 2346117. https://doi.org/10.1080/00049530.2024.2356117
Barlo, S., Boyd, W. E., Pelizzon, A., & Wilson, S. (2020). Yarning as protected space: Principles and protocols. Alternative: An
International Journal of Indigenous Peoples, 16(2), 90–98. https://doi.org/10.1177/1177180120917480
Baxter, J. (2013). The family circumstances and wellbeing of Indigenous and non-Indigenous children. In Australian
Institute of Family Studies (Ed.), Growing up in Australia: The longitudinal study of Australian children: Annual statistical
report 2012 (pp. 149–171). Australian Institute of Family Studies. https://core.ac.uk/download/pdf/30676512.
pdf#page=161
Begay, V., & Klor, K. M. (2024). Provenance through storytelling: Application of Indigenous relationality toward arrange-
ment and description. Architectural Science, 24(4), 611–635. https://doi.org/10.1007/s10502-024-09451-z
Bishop, M. (2021). ‘Don’t tell me what to do’ encountering colonialism in the academy and pushing back with Indigenous
autoethnography. International Journal of Qualitative Studies in Education, 34(5), 367–378. https://doi.org/10.1080/
09518398.2020.1761475
Boulous Walker, M. (2022). Nature, obligation, and transcendence: Reading Luce Irigaray with Mary Graham. Sophia, 61(1),
187–201. https://doi.org/10.1007/s11841-022-00907-2
Bowes, J., & Grace, R. (2014). Review of early childhood parenting, education and health intervention programs for
indigenous children and families in Australia. Closing the Gap Clearinghouse. www.aihw.gov.au/closingthegap
Bufton, K., Bates, M., Fuller-Tyszkiewicz, M., Hamid, J., & Westrupp, E. (2024). Design mapping: A framework for
co-designing digital mental health programs in partnership with end-users. Health Expectations, 28. https://doi.org/
10.1111/hex.70385
Bullen, J., Hill-Wall, T., Anderson, K., Brown, A., Bracknell, C., Newnham, E. A., Garvey, G., & Waters, L. (2023). From deficit to
strength-based Aboriginal health research-moving toward flourishing. International Journal of Environmental Research
and Public Health, 20(7), 5395. https://doi.org/10.3390/ijerph20075395
Burgess, C. P., Johnston, F. H., Berry, H. L., McDonnell, J., Yibarbuk, D., Gunabarra, C., Mileran, A., & Bailie, R. S. (2009).
Healthy country, healthy people: The relationship between Indigenous health status and “caring for country”. Medical
Journal of Australia, 190(10), 567–572. https://doi.org/10.5694/j.1326-5377.2009.tb02566.x
Cameron, E. (2015). Is it art or knowledge? Deconstructing Australian Aboriginal creative making. Arts, 4(2), 68–74. https://
doi.org/10.3390/arts4020068
Canuto, K., Harfield, S. G., Canuto, K. J., & Brown, A. (2019). Aboriginal and Torres Strait Islander men and parenting:
A scoping review. Australian Journal of Primary Health, 26(1), 1–9. https://doi.org/10.1071/py19106
Clancy, E., Benstead, M., Little, K., Skvarc, D., Westrupp, E., Yap, M., Havighurst, S., & Toumbourou, J. W. (2019). Family
partnerships to support children and young people’s mental health: An Evidence Check rapid review brokered by the Sax
Institute for be you (Evidence Check rapid review). Sax Institute. https://beyou.edu.au/-/media/learn/supporting-
evidence/family-partnerships.pdf?la=en
Compas, B. E., Jaser, S. S., Bettis, A. H., Watson, K. H., Gruhn, M. A., Dunbar, J. P., Williams, E., & Thigpen, J. C. (2017). Coping,
emotion regulation, and psychopathology in childhood and adolescence: A meta-analysis and narrative review.
Psychological Bulletin, 143(9), 939–991. https://doi.org/10.1037/bul0000110
Darwin, L., Vervoort, S., Vollert, E., & Blustein, S. (2023). Intergenerational trauma and mental health. Australian
Government. https://www.indigenousmhspc.gov.au/publications/trauma
Dudgeon, P., Bray, A., Darlaston-Jones, D., & Walker, R. (2020). Aboriginal participatory action research: An Indigenous
research methodology strengthening decolonisation and social and emotional wellbeing. LOWITJA INSTITUTE. https://
researchportal.murdoch.edu.au/esploro/outputs/report/Aboriginal-participatory-action-research-An-Indigenous
/991005687466707891#file-0
Duke, D. L. M., Prictor, M., Ekinci, E., Hachem, M., & Burchill, L. J. (2021). Culturally adaptive governance-building a new
framework for equity in Aboriginal and Torres Strait Islander health research: Theoretical basis, ethics, attributes and
evaluation. International Journal of Environmental Research and Public Health, 18(15), 7943. https://doi.org/10.3390/
ijerph18157943
Dunstan, L., Hewitt, B., & Nakata, S. (2019). Indigenous family life in Australia: A history of difference and deficit. Australian
Journal of Social Issues, 55(3), 323–338. https://doi.org/10.1002/ajs4.90
England-Mason, G., Andrews, K., Atkinson, L., & Gonzalez, A. (2023). Emotion socialization parenting interventions
targeting emotional competence in young children: A systematic review and meta-analysis of randomized controlled
trials. Clinical Psychology Review, 100, 102252. https://doi.org/10.1016/j.cpr.2023.102252
Enns, J., Holmqvist, M., Wener, P., Halas, G., Rothney, J., Schultz, A., Goertzen, L., & Katz, A. (2016). Mapping interventions
that promote mental health in the general population: A scoping review of reviews. Preventative Medicine, 87, 70–80.
https://doi.org/10.1016/j.ypmed.2016.02.022
Frosch, C. A., Schoppe-Sullivan, S. J., & O’Banion, D. D. (2021). Parenting and child development: A relational health
perspective. American Journal of Lifestyle Medicine, 15(1), 45–59. https://doi.org/10.1177/1559827619849028
Gee, G., Dudgeon, P., Schultz, C., Hart, A., & Kelly, K. (2014). Aboriginal and Torres Strait Islander social and emotional
wellbeing. In P. Dudgeon, H. Milroy, & R. Walker (Eds.), Working together: Aboriginal and Torres Strait Islander mental
health and wellbeing principles and practice (2nd ed., pp. 55–68). Commonwealth of Australia. https://www.telethon
kids.org.au/globalassets/media/documents/aboriginal-health/working-together-second-edition/wt-part-1-chapt-
4-final.pdf
Gottman, J. M., Katz, L. F., & Hooven, C. (1996). Parental meta-emotion philosophy and the emotional life of families:
Theoretical models and preliminary data. Journal of Family Psychology, 10(3), 243–268. https://doi.org/10.1037/0893-
3200.10.3.243
Graham, M. (2023). The law of obligation, Aboriginal ethics: Australia becoming, Australia dreaming. Parrhesia: A Journal
of Critical Philosophy, 37, 1–27.
Gray, P., DarlastonJones, D., Dudgeon, P., Derry, K., Alexi, J., Smith, W., Hirvonen, T., Badcock, D., Kashyap, S., & Selkirk, B.
(2025). The contribution of evidencebased practice and the practicebased evidence approaches to contemporary
Australian psychology: Implications for culturally safe practice. Medical Journal of Australia, 223(6), 282–288. https://
doi.org/10.5694/mja2.70028
Guttorm, H., Kantonen, L., Kramvig, B., & Pyhälä, A. (2021). Decolonized research-storying: Bringing Indigenous ontologies
and care into the practices of research writing. In H. Guttorm, L. Kantonen, B. Kramvig, & A. Pyhälä (Eds.), Indigenous
research methodologies in Sámi and Nordic contexts (Vol. 11, pp. 113–143). Brill. https://doi.org/10.1163/
9789004463097
Havighurst, S. S., Kehoe, C. E., Harley, A. E., Radovini, A., & Thomas, R. (2022). A randomized controlled trial of an emotion
socialization parenting program and its impact on parenting, children’s behavior and parent and child stress cortisol:
Tuning in to toddlers. Behaviour Research and Therapy, 149, 104016. https://doi.org/10.1016/j.brat.2021.104016
Iwama, M., Marshall, M., Marshall, A., & Bartlett, C. (2009). Twoeyed seeing and the language of healing in commu-
nitybased research. Canadian Journal of Native Education, 32(2), 3–23. https://doi.org/10.14288/cjne.v32i2.196493
Jeong, J., Franchett, E. E., Ramos de Oliveira, C. V., Rehmani, K., & Yousafzai, A. K. (2021). Parenting interventions to
promote early child development in the first three years of life: A global systematic review and meta-analysis. PLOS
Med, 18(5), e1003602. https://doi.org/10.1371/journal.pmed.1003602
Kimmerer, R. W. (2013). Braiding sweetgrass: Indigenous wisdom, scientific knowledge and the teachings of plants. Milkweed
editions.
Lin, S. C., Kehoe, C., Pozzi, E., Liontos, D., & Whittle, S. (2024). Research review: Child emotion regulation mediates the
association between family factors and internalizing symptoms in children and adolescents-a meta-analysis. Journal of
Child Psychology and Psychiatry, 65(3), 260–274. https://doi.org/10.1111/jcpp.13894
Luke, J., Verbunt, E., Zhang, A., Bamblett, M., Johnson, G., Salamone, C., Thomas, D., Eades, S., Gubhaju, L., Kelaher, M., &
Jones, A. (2022). Questioning the ethics of evidence-based practice for Indigenous health and social settings in
Australia. BMJ Global Health, 7(6), e009167. https://doi.org/10.1136/bmjgh-2022-009167
MacDonald, J., Young, M., Barclay, B., McMullen, S., Knox, J., & Morgan, P. (2024). The participation of Aboriginal and
Torres Strait Islander parents in Australian trials of parenting programs for improving children’s health: A scoping
review. Medical Journal of Australia, 220(6), 331–335. https://doi.org/10.5694/mja2.52198
Morris, A. S., Criss, M. M., Silk, J. S., & Houltberg, B. J. (2017). The impact of parenting on emotion regulation during
childhood and adolescence. Child Development Perspectives, 11(4), 233–238. https://doi.org/10.1111/cdep.12238
Morris, A. S., Cui, L., Jespersen, J. E., Criss, M. M., & Cosgrove, K. T. (2022). Parenting and children’s social and emotional
development: Emotion socialization across childhood and adolescence. In A. S. Morris & J. MENDEZ. Smith (Eds.), The
Cambridge Handbook of Parenting: Interdisciplinary Research and Application (pp. 71–94). Cambridge University Press.
https://doi.org/10.1017/9781108891400.006
O’Shea, M., Klas, A., Hardy, T., Stone, J., Frangos, T., Jacobs, T., Mitchell, F., James, C., Jones, S., Thomas, J., & Ryan, K. (2024).
Weaving wayapa and cognitive behaviour therapy: Applying research topic yarning to explore a cultural interface
between Western and indigenous psychology practice in Australia. Australian Psychologist, 1–17. https://doi.org/10.
1080/00050067.2024.2322710
Pandey, A., Hale, D., Das, S., Goddings, A. L., Blakemore, S. J., & Viner, R. M. (2018). Effectiveness of universal
self-regulation-based interventions in children and adolescents: A systematic review and meta-analysis. JAMA
Pediatrics, 172(6), 566–575. https://doi.org/10.1001/jamapediatrics.2018.0232
Prehn, J., Guerzoni, M. A., & Peacock, H. (2020). ‘Learning her culture and growing up strong’: Aboriginal and/or Torres
Strait Islander fathers, children and the sharing of culture. Journal of Sociology, 57(3), 595–611. https://doi.org/10.1177/
1440783320934188
Priest, N., Baxter, J., & Hayes, L. (2012). Social and emotional outcomes of Australian children from Indigenous and
culturally and linguistically diverse backgrounds. Australian and New Zealand Journal of Public Health, 36(2), 183–190.
https://doi.org/10.1111/j.1753-6405.2011.00803.x
Roher, S. I. G., Yu, Z., Martin, D. H., & Benoit, A. C. (2021). How is Etuaptmumk/TwoEyed seeing characterized in Indigenous
health research? A scoping review. PLOS ONE, 16(7), Article e0254612. https://doi.org/10.1371/journal.pone.0254612
Sanders, M. R., & Mazzucchelli, T. G. (2013). The promotion of self-regulation through parenting interventions. Clinical
Child and Family Psychology Review, 16(1), 1–17. https://doi.org/10.1007/s10567-013-0129-z
Sherriff, S., & Gwynn, J. D. (2024). Yarning together: Toward targeted, co-designed parenting programs for Aboriginal
Australians. Medical Journal of Australia, 220(6), 313–314. https://doi.org/10.5694/mja2.52238
Sicouri, G., Tully, L., Collins, D., Burn, M., Sargeant, K., Frick, P., Anderson, V., Hawes, D., Kimonis, E., Moul, C., Lenroot, R., &
Dadds, M. (2018). Toward father-friendly parenting interventions: A qualitative study. Australian and New Zealand
Journal of Family Therapy, 39(2), 218–231. https://doi.org/10.1002/anzf.1307
Stuart, G., May, C., & Hammond, C. (2015). Engaging aboriginal fathers. Developing practice: The child. Youth and Family
Work Journal, 42, 4–17. https://doi.org/10.3316/ielapa.241220890134254
Tarrant, L., & Tarrant, J. (n.d.). Learning the wayapa way. Intertype Publish and Print.
Turner, K. M., Richards, M., & Sanders, M. R. (2007). Randomised clinical trial of a group parent education programme for
Australian Indigenous families. Journal of Paediatrics and Child Health, 43(4), 243–251. https://doi.org/10.1046/j.1440-
1754.2002.00077.x-i1
Ungunmerr-Baumann, M.-R., Groom, R. A., Schuberg, E. L., Atkinson, J., Atkinson, C., Wallace, R., & Morris, G. (2022). Dadirri:
An Indigenous place-based research methodology. AlterNative: An International Journal of Indigenous Peoples, 18(1),
94–103. https://doi.org/10.1177/11771801221085353
Walker, E. R., McGee, R. E., & Druss, B. G. (2015). Mortality in mental disorders and global disease burden implications:
A systematic review and meta-analysis. JAMA Psychiatry, 72(4), 334–341. https://doi.org/10.1001/jamapsychiatry.2014.
2502
Westrupp, E. M., Bates, M., Bufton, K. J., Berkowitz, T. B., Popple, M., King, G. L., Jones, S., Stone, J., Funke Kupper, J. J. C.,
Toumbourou, J. W., Karmakar, C., Havighurst, S. S., Kehoe, C. E., Angelova, M., O’Shea, M., Tarrant, L., Olive, L. S., Evans, S.
Ewald, S. . . . Fuller-Tyszkiewicz, M. (2025). Protocol for a randomized and a non-randomized controlled trial testing
daily growth: A personalised “ecological momentary intervention” parenting app for parents and carers of children
aged 2-5 years. BMC Psychology, 13(1), Article 704. https://doi.org/10.1186/s40359-025-03018-y
Westrupp, E. M., Youssef, G., Fuller-Tyszkiewicz, M., MacDonald, J. A., Havighurst, S., Kehoe, C. E., Olive, L., & Evans, S.
(2020). Using technology to tailor and personalise population level parenting interventions. Mental Health and
Prevention, 19, Article 200184. https://doi.org/10.1016/j.mhp.2020.200184
Wise, S. (2013). Improving the early life outcomes of indigenous children: Implementing early childhood development at the
local level. Closing the Gap Clearinghouse. https://www.aihw.gov.au/reports/indigenous-australians/improving-early-
life-outcomes-indigenous-australia/summary
Wright, A., Gray, P., Selkirk, B., Hunt, C., & Wright, R. (2023). Attachment and the (mis)apprehension of Aboriginal children:
Epistemic violence in child welfare interventions. Psychiatry, Psychology and Law, 1–25. https://doi.org/10.1080/
13218719.2023.2280537
Yunkaporta, T. (2020). Sand talk: How indigenous thinking can save the world. Text Publishing Company. http://ebookcen
tral.proquest.com/lib/scu/detail.action?docID=30182381
Zimmer-Gembeck, M. J., Rudolph, J., Kerin, J., & Bohadana-Brown, G. (2022). Parent emotional regulation: A meta-analytic
review of its association with parenting and child adjustment. International Journal of Behavioral Development, 46(1),
63–82. https://doi.org/10.1177/01650254211051086"""

test12 = """Allgaier, A.-K., Pietsch, K., Frühe, B., Prast, E., Sigl-Glöckner, J., & Schulte-Körne, G. (2012). Depression in pediatric care: Is
the WHO-Five Well-Being Index a valid screening instrument for children and adolescents? General Hospital Psychiatry,
34(3), 234–241. https://doi.org/10.1016/j.genhosppsych.2012.01.007
Alzahrani, H. (2022). Dose-response association between physical activity and health-related quality of life in general
population: A population-based pooled study. Healthcare, 10(8), 1460. https://www.mdpi.com/2227-9032/10/8/1460
Amireault, S., Godin, G., Lacombe, J., & Sabiston, C. M. (2015). The use of the Godin-Shephard Leisure-Time Physical
Activity Questionnaire in oncology research: A systematic review. BMC Medical Research Methodology, 15(1), 60.
https://doi.org/10.1186/s12874-015-0045-7
Andermo, S., Hallgren, M., Nguyen, T.-T.-D., Jonsson, S., Petersen, S., Friberg, M., Romqvist, A., Stubbs, B., & Elinder, L. S.
(2020). School-related physical activity interventions and mental health among children: A systematic review and
meta-analysis. Sports Medicine - Open, 6(1), 25. https://doi.org/10.1186/s40798-020-00254-x
Bech, P., Olsen, L. R., Kjoller, M., & Rasmussen, N. K. (2003). Measuring well-being rather than the absence of distress
symptoms: A comparison of the SF-36 Mental Health Subscale and the WHO-Five Well-Being Scale. International
Journal of Methods in Psychiatric Research, 12(2), 85–91. https://doi.org/10.1002/mpr.145
Chan, L., Liu, R. K. W., Lam, T. P., Chen, J. Y., Tipoe, G. L., & Ganotice, F. A. (2022). Validation of the World Health
Organization Well-Being Index (WHO-5) among medical educators in Hong Kong: A confirmatory factor analysis.
Medical Education Online, 27(1), 2044635. https://doi.org/10.1080/10872981.2022.2044635
Fuentealba-Urra, S., Rubio, A., González-Carrasco, M., Oyanedel, J. C., & Céspedes-Carreno, C. (2023). Mediation effect of
emotional self-regulation in the relationship between physical activity and subjective well-being in Chilean
adolescents. Scientific Reports, 13(1), 13386. https://doi.org/10.1038/s41598-023-39843-7
Fung, S., Kong, C. Y. W., Liu, Y., Huang, Q., Xiong, Z., Jiang, Z., Zhu, F., Chen, Z., Sun, K., & Zhao, H. (2022). Validity and
psychometric evaluation of the Chinese version of the 5-item WHO Well-Being Index. Frontiers in Public Health, 10,
872436. https://doi.org/10.3389/fpubh.2022.872436
Gilbert, P. (2014). Mindful compassion: How the science of compassion can help you understand your emotions, live in the
present, and connect deeply with others. New Harbinger Publications. https://books.google.com/books?hl=zh-TW&lr
=&id=5oIfAwAAQBAJ&oi=fnd&pg=PT12&dq=Gilbert,+P.+%26+Choden.+(2014).+Mindful+compassion:+How+the
+science+of+compassion+can+help+you+understand+your+emotions,+live+in+the+present,+and+connect+dee
ply+with+others.+New+Harbinger+Publications.&ots=d5LS7JeDaN&sig=WpxMJ5Y4Sv9yYjvsZdVhee2Ea4E
Gilbert, P. (2019). Explorations into the nature and function of compassion. Current Opinion in Psychology, 28, 108–114.
https://doi.org/10.1016/j.copsyc.2018.12.002
Gillman, A. S., & Bryan, A. D. (2020). Mindfulness versus distraction to improve affective response and promote
cardiovascular exercise behavior. Annals of Behavioral Medicine, 54(6), 423–435. https://doi.org/10.1093/abm/kaz059
Godin, G. (2011). The Godin-Shephard Leisure-Time Physical Activity Questionnaire. The Health & Fitness Journal of
Canada, 4(1), 18–22.
Hu, L., & Bentler, P. M. (1999). Cutoff criteria for fit indexes in covariance structure analysis: Conventional criteria versus
new alternatives. Structural Equation Modeling: A Multidisciplinary Journal, 6(1), 1–55. https://doi.org/10.1080/
10705519909540118
Huang, L., Chen, Z., Jiang, W., Qu, D., Wang, Y., Fang, X., Han, H., Huang, C., Li, Z., & Chi, X. (2022). Validation of the Chinese
version of Self-Compassion Scale for Youth (SCS-Y). Mindfulness, 13(12), 3166–3178. https://doi.org/10.1007/s12671-
022-02024-0
Jaccard, J., & Wan, C. K. (1996). Lisrel approaches to interaction effects in multiple regression. Sage. https://books.google.
com/books?hl=zh-TW&lr=&id=3CetibzlTCYC&oi=fnd&pg=PP7&dq=1.%09Jaccard,+J.+%26+Wan,+C.+K.+(1996).
+LISREL+approaches+to+interaction+effects+in+multiple+regression.+Sage+Publications,+Inc.+&ots=
vLl1byb4vW&sig=oEZtju-kPJuG53Yyz3z0ki_qBxc
Kullman, S. M., Simpson, K. M., Semenchuk, B. N., Taylor, D., & Strachan, S. M. (2024). Self-compassion, physical activity,
and psychological antecedents of physical activity: A scoping review of quantitative research. Sport, Exercise, and
Performance Psychology, 13(3), 254. https://doi.org/10.1037/spy0000349
Magnus, C. M. R., Kowalski, K. C., & McHugh, T.-L. F. (2010). The role of self-compassion in women’s self-determined
motives to exercise and exercise-related outcomes. Self and Identity, 9(4), 363–382. https://doi.org/10.1080/
15298860903135073
Morga, P., Cieślik, B., Sekułowicz, M., Bujnowska-Fedak, M., Drower, I., & Szczepańska-Gieracha, J. (2021). Low-intensity
exercise as a modifier of depressive symptoms and self-perceived stress level in women with metabolic syndrome.
Journal of Sports Science & Medicine, 20(2), 222. https://doi.org/10.52082/jssm.2021.222
Neff, K. (2003). Self-compassion: An alternative conceptualization of a healthy attitude toward oneself. Self and Identity, 2
(2), 85–101. https://doi.org/10.1080/15298860309032
Neff, K. D., Bluth, K., Tóth-Király, I., Davidson, O., Knox, M. C., Williamson, Z., & Costigan, A. (2021). Development and
validation of the Self-Compassion Scale for Youth. Journal of Personality Assessment, 103(1), 92–105. https://doi.org/10.
1080/00223891.2020.1729774
Neff, K. D., & Dahm, K. A. (2015). Self-compassion: What it is, what it does, and how it relates to mindfulness. In
B. D. Ostafin, M. D. Robinson, & B. P. Meier (Eds.), Handbook of mindfulness and self-regulation (pp. 121–137).
Springer New York. https://doi.org/10.1007/978-1-4939-2263-5_10
Neill, R. D., Lloyd, K., Best, P., & Tully, M. A. (2020). The effects of interventions with physical activity components on
adolescent mental health: Systematic review and meta-analysis. Mental Health and Physical Activity, 19, 100359.
https://doi.org/10.1016/j.mhpa.2020.100359
Pearce, M., Garcia, L., Abbas, A., Strain, T., Schuch, F. B., Golubic, R., Kelly, P., Khan, S., Utukuri, M., & Laird, Y. (2022).
Association between physical activity and risk of depression: A systematic review and meta-analysis. JAMA Psychiatry,
79(6), 550–559. https://doi.org/10.1001/jamapsychiatry.2022.0609
Phillips, W. J., & Hine, D. W. (2021). Self-compassion, physical health, and health behaviour: A meta-analysis. Health
Psychology Review, 15(1), 113–139. https://doi.org/10.1080/17437199.2019.1705872
Roychowdhury, D. (2021). Moving mindfully: The role of mindfulness practice in physical activity and health behaviours.
Journal of Functional Morphology and Kinesiology, 6(1), 19. https://doi.org/10.3390/jfmk6010019
Sirois, F. M., Kitner, R., & Hirsch, J. K. (2015). Self-compassion, affect, and health-promoting behaviors. Health Psychology,
34(6), 661. https://doi.org/10.1037/hea0000158
Solk, P., Auster-Gussman, L. A., Torre, E., Welch, W. A., Murphy, K., Starikovsky, J., Reading, J. M., Victorson, D. E., &
Phillips, S. M. (2023). Effects of mindful physical activity on perceived exercise exertion and other physiological and
psychological responses: Results from a within-subjects, counter-balanced study. Frontiers in Psychology, 14, 1285315.
https://doi.org/10.3389/fpsyg.2023.1285315
Sünbül, Z. A., & Özcan, N. A. (2022). The mediating role of negative mood states and body responsiveness in the
associations of mindfulness and self-compassion with life satisfaction. Studia Psychologica, 64(4), 343–355. https://doi.
org/10.31577/sp.2022.04.858
Ullrich-French, S., Cox, A., Cole, A., Rhoades Cooper, B., & Gotch, C. (2017). Initial validity evidence for the state
mindfulness scale for physical activity with youth. Measurement in Physical Education and Exercise Science, 21(4),
177–189. https://doi.org/10.1080/1091367X.2017.1321543
Von Elm, E., Altman, D. G., Egger, M., Pocock, S. J., Gøtzsche, P. C., Vandenbroucke, J. P., & Strobe Initiative. (2014). The
strengthening the reporting of observational studies in epidemiology (STROBE) statement: Guidelines for reporting
observational studies. International Journal of Surgery, 12(12), 1495–1499.
Wang, T., Nie, Y., Yao, X., Zhang, J., Li, Y., Sun, H., & Gao, J. (2025). The chain mediating role of emotion regulation and
stress perception in physical activity alleviating college students’ health anxiety. Scientific Reports, 15(1), 29189. https://
doi.org/10.1038/s41598-025-14481-3
Wong, M. Y. C., Chu, T. L., Mesquita-Garcia, A. C., Fung, H. W., Yuan, G. F., & Ullrich-French, S. (under review).
Redevelopment of the state mindfulness for physical activity with self-compassion: The mindful and compassionate
awareness scale for physical activity (MCA-PA). Manuscript under review.
Wong, M.-Y. C., Chung, P.-K., & Leung, K.-M. (2021). Examining the exercise and self-esteem model revised with
self-compassion among Hong Kong secondary school students using structural equation modeling. International
Journal of Environmental Research and Public Health, 18(7), 3661. https://doi.org/10.3390/ijerph18073661
Wong, M. Y. C., Chung, P.-K., & Leung, K.-M. (2021). The relationship between physical activity and self-compassion:
A systematic review and meta-analysis. Mindfulness, 12(3), 547–563. https://doi.org/10.1007/s12671-020-01513-4
Wong, M.-Y. C., Fung, H.-W., & Yuan, G. F. (2023). The association between physical activity, self-compassion, and mental
well-being after COVID-19: In the exercise and self-esteem model revised with self-compassion (EXSEM-SC)
perspective. Healthcare, 11(2), 233. https://www.mdpi.com/2227-9032/11/2/233
Zhang, S., Roscoe, C., & Pringle, A. (2023). Self-compassion and physical activity: The underpinning role of psychological
distress and barrier self-efficacy. International Journal of Environmental Research and Public Health, 20(2), 1480. https://
doi.org/10.3390/ijerph20021480"""

test13 = """Ancis, J. R., & Marshall, D. S. (2010). Using a multicultural framework to assess supervisees’ perceptions of culturally
competent supervision. Journal of Counseling and Development, 88(3), 277–284. https://doi.org/10.1002/j.1556-6678.
2010.tb00023.x
Arthur, N., & Januszkowski, T. (2001). The multicultural counselling competencies of Canadian counsellors. Canadian
Journal of Counselling, 35(1), 36–48.
Australian Bureau of Statistics. (2021). Migration, Australia. https://www.abs.gov.au/statistics/people/population/migra
tion-australia/latest-release
Bowker, P., & Richards, B. (2004). Speaking the same language? A qualitative study of therapists’ experiences of working
in English with proficient bilingual clients. Psychodynamic Practice: Individuals, Groups and Organisations, 10(4),
459–478. https://doi.org/10.1080/14753630412331313695
Castillo, L. G., Brossart, D. F., Reyes, C. J., Conoley, C. W., & Phoummarath, M. J. (2007). The influence of multicultural
training on perceived multicultural counseling competencies and implicit racial prejudice. Journal of Multicultural
Counseling and Development, 35(4), 243–254. https://doi.org/10.1002/j.2161-1912.2007.tb00064.x
Chu, W., Wippold, G., & Becker, K. D. (2022). A systematic review of cultural competence trainings for mental health
providers. Professional Psychology, Research and Practice, 53(4), 362–371. https://doi.org/10.1037/pro0000469
Commonwealth Government of Australia. (2010). The national standards for mental health services. https://www.health.
gov.au/sites/default/files/documents/2021/04/national-standards-for-mental-health-services-2010-and-
implementation-guidelines.pdf
Constantine, M. G. (2001). Predictors of observer ratings of multicultural counseling competence in Black, Latino, and
White American trainees. Journal of Counseling Psychology, 48(4), 456–462. https://doi.org/10.1037/0022-0167.48.4.456
Costa, B., & Dewaele, J.-M. (2014). Psychotherapy across languages: Beliefs, attitudes and practices of monolingual and
multilingual therapists with their multilingual patients. Counselling and Psychotherapy Research, 14(3), 235–244.
https://doi.org/10.1080/14733145.2013.838338
Drolet, M., Savard, J., Benot, J., Arcand, I., Savard, S., Lagacé, J., Lauzon, S., & Dubouloz, C. J. (2014). Health services for
linguistic minorities in a bilingual setting: Challenges for bilingual professionals. The Qualitative Health Research, 24(3),
295–305. https://doi.org/10.1177/1049732314523503
Dune, T., Chimoriya, R., Caputi, P., MacPhail, C., Olcon, K., & Ogbeide, A. (2022). White and non-white Australian mental
health care practitioners’ desirable responding, cultural competence, and racial/ethnic attitudes. BMC Psychology, 10
(1), 119. https://doi.org/10.1186/s40359-022-00818-4
Erkoreka, L., Ozamiz-Etxebarria, N., Ruiz, O., & Ballesteros, J. (2020). Assessment of psychiatric symptomatology in
bilingual psychotic patients: A systematic review and meta-analysis. International Journal of Environmental Research
and Public Health, 17(11), 4137. https://doi.org/10.3390/ijerph17114137
Falender, C. A., Burnes, T. R., & Ellis, M. V. (2013). Multicultural clinical supervision and benchmarks: Empirical support
informing practice and supervisor training. The Counseling Psychologist, 41(1), 8–27. https://doi.org/10.1177/
0011000012438417
Fuertes, J. N., & Brobst, K. (2002). Clients’ ratings of counselor multicultural competency. Cultural Diversity and Ethnic
Minority Psychology, 8(3), 214–223. https://doi.org/10.1037/1099-9809.8.3.214
Garcia de Blakeley, M., Ford, R., & Casey, L. (2017). Second language anxiety among Latino American immigrants in
Australia. International Journal of Bilingual Education and Bilingualism, 20(7), 759–772. https://doi.org/10.1080/
13670050.2015.1083533
Garcia de Blakeley, M., Stuart, J., & Sheeran, N. (2023). Development and initial validation of a measure of cross-lingual
practice among mental health practitioners. Psychother Research, 33(2), 251–263. https://doi.org/10.1080/10503307.
2022.2090300
Geerlings, L. R. C., Thompson, C. L., Bouma, R., & Hawkins, R. (2018). Cultural competence in clinical psychology training:
A qualitative investigation of student and academic experiences. Australian Psychologist, 53(2), 161–170. https://doi.
org/10.1111/ap.12291
Gonzales, H. M., Popis, B., Smith, P., & Antezana, G. (2022). Perceived multicultural counselling competencies amongst
Australian counsellors and psychologists. Australian Counselling Research Journal, 16(1), 4–11.
Hill, N. R., Vereen, L. G., McNeal, D., & Stotesbury, R. (2013). Multicultural awareness, knowledge, and skills among
American counselor trainees: Group differences in self-perceived competence based on dispositional and program-
matic variables. International Journal for the Advancement of Counselling, 35(4), 261–272. doi: https://doi.org/10.1007/
s10447-012-9181-5
Ho, N., & O’Donovan, A. (2018). An exploration of the experiences of culturally and/or linguistically diverse trainee
psychologists in Australian postgraduate programs: CALD trainee psychologists. Australian Psychologist, 53(6),
493–504. https://doi.org/10.1111/ap.12353
Ivers, N. N., & Villalba, J. A. (2015). The effect of bilingualism on self-perceived multicultural counseling competence. The
Professional Counselor, 5(3), 419–430. https://doi.org/10.15241/nni.5.3.419
Khawaja, N., Gomez, I., & Turner, G. (2009). Development of the multicultural mental health awareness scale. Australian
Psychologist, 44(2), 44. https://doi.org/10.1080/00050060802417801
Khawaja, N. G., & Stein, G. (2016). Psychological services for asylum seekers in the community: Challenges and solutions.
Australian Psychologist, 51(6), 463–471. https://doi.org/10.1111/ap.12149
Kheirzadeh, S., & Hajiabed, M. (2016). Differential language functioning of monolinguals and bilinguals on
positive-negative emotional expression. Journal of Psycholinguistic Research, 45(1), 55–69. https://doi.org/10.1007/
s10936-014-9326-2
Kokaliari, E., Catanzarite, G., & Berzoff, J. (2013). It is called a mother tongue for a reason: A qualitative study of therapists’
perspectives on bilingual psychotherapy-treatment implications. Smith College Studies in Social Work, 83(1), 97–118.
https://doi.org/10.1080/00377317.2013.747396
LaFromboise, T. D., Coleman, H. L. K., & Hernandez, A. (1991). Development and factor structure of the cross-cultural
counseling inventory-revised. Professional Psychology, Research and Practice, 22(5), 380–388. https://doi.org/10.1037/
0735-7028.22.5.380
Lee, A., & Khawaja, N. G. (2013). Multicultural training experiences as predictors of psychology students’ cultural
competence. Australian Psychologist, 48(3), 209–216. https://doi.org/10.1111/j.1742-9544.2011.00063.x
Menon, G., Sarma, H., Bestman, A., O’Callaghan, C., & Yadav, U. N. (2025). A scoping review to identify opportunities and
challenges for communities of South Asian origin in accessing mental health services and support in high-income
countries. BMC Public Health, 25(1), 3755. https://doi.org/10.1186/s12889-025-24619-7
Milner, K., & Khawaja, N. G. (2010). Sudanese refugees in Australia: The impact of acculturation stress. Journal of Pacific
Rim Psychology, 4(1), 19–29. https://doi.org/10.1375/prp.4.1.19
Minas, H., Kakuma, R., Too, L. S., Vayani, H., Orapeleng, S., Prasad Ildes, R., Turner, G., Procter, N., & Oehm, D. (2013). Mental
health research and evaluation in multicultural Australia: Developing a culture of inclusion. International Journal of
Mental Health Systems, 7(1), 23. https://doi.org/10.1186/1752-4458-7-23
Pettigrew, T. F., & Tropp, L. R. (2008). How does intergroup contact reduce prejudice? Meta-analytic tests of three
mediators. European Journal of Social Psychology, 38(6), 922–934. https://doi.org/10.1002/ejsp.504
Psychology Board of Australia. (2025a). Professional competencies for psychologists. Retrieved August 28, 2025, from
https://www.psychologyboard.gov.au/Standards-and-Guidelines/Professional-practice-standards/Professional-
competencies-for-psychologists.aspx
Psychology Board of Australia. (2025b). Psychology Board of Australia registrant data. AHPRA. https://www.psychology
board.gov.au/About/Statistics.aspx
Rolland, L., Costa, B., & Dewaele, J.-M. (2021). Negotiating the language(s) for psychotherapy talk: A mixed methods study
from the perspective of multilingual clients. Counselling and Psychotherapy Research, 21(1), 107–117. https://doi.org/
10.1002/capr.12369
Schroeder, S. R., & Marian, V. (2014). Bilingual episodic memory: How speaking two languages influences remembering. In
R. R. Heredia & J. Altarriba (Eds.), Foundations of bilingual memory (pp. 111–132). Springer New York. https://doi.org/10.
1007/978-1-4614-9218-4_6
Schwanberg, J. S. (2010). Does language of retrieval affect the remembering of trauma? Journal of Trauma and
Dissociation, 11(1), 44–56. https://doi.org/10.1080/15299730903143550
Šidák, Z. K. (1967). Rectangular confidence regions for the means of multivariate normal distributions. Journal of the
American Statistical Association, 62(318), 626–633. https://doi.org/10.1080/01621459.1967.10482935
Smith, T. B., Constantine, M. G., Dunn, T. W., Dinehart, J. M., & Montoya, J. A. (2006). Multicultural education in the mental
health professions: A meta-analytic review. Journal of Counseling Psychology, 53(1), 132–145. https://doi.org/10.1037/
0022-0167.53.1.132
Sodowsky, G., Kuo-Jackson, P., Richardson, M., & Corey, A. (1998). Correlates of self-reported multicultural competencies:
Counselor multicultural social desirability, race, social inadequacy, locus of control, racial ideology, and multicultural
training. Journal of Counseling Psychology, 45(3), 256–264. https://doi.org/10.1037/0022-0167.45.3.256
Sodowsky, G. R., Taffe, R. C., Gutkin, T. B., & Wise, S. L. (1994). Development of the multicultural Counseling Inventory: A
self-report measure of multicultural competencies. Journal of Counseling Psychology, 41(2), 137–148. https://doi.org/
10.1037/0022-0167.41.2.137
Stevens, S., & Holland, P. (2008). Counselling across a language gap: The therapist’s experience. Counselling Psychology
Review, 23(3), 231–240. https://doi.org/10.1002/capr.12187
Stratton, S. J. (2021). Population research: Convenience sampling strategies. Prehospital and Disaster Medicine, 36(4),
373–374. https://doi.org/10.1017/S1049023X21000649
Sue, D. W. (2001). Multidimensional facets of cultural competence. The Counseling Psychologist, 29(6), 790–821. https://
doi.org/10.1177/0011000001296002
Sue, S., Zane, N., Nagayama Hall, G. C., & Berger, L. K. (2009). The case for cultural competency in psychotherapeutic
interventions. Annual Review of Psychology, 60(1), 525–548. https://doi.org/10.1146/annurev.psych.60.110707.163651
Tan, L. L., & Denson, L. (2019). Bilingual and multilingual psychologists practising in Australia: An exploratory study of
their skills, training needs and experiences. Australian Psychologist, 54(1), 13–25. https://doi.org/10.1111/ap.12355
Verkerk, L., Fuller, J. M., Huiskes, M., & Schüppert, A. (2023). Expression and interpretation of emotions in multilingual
psychotherapy: A literature review. Counselling and Psychotherapy Research, 23(3), 617–626. https://doi.org/10.1002/
capr.12650
Wohler, Y., & Dantas, J. A. R. (2017). Barriers accessing mental health services among culturally and linguistically diverse
(CALD) immigrant women in Australia: Policy implications. Journal of Immigrant & Minority Health, 19(3), 697–701.
https://doi.org/10.1007/s10903-016-0402-6"""


test13 = """Agnew, R. (2001). Building on the foundation of general strain theory: Specifying the types of strain most likely to lead to
crime and delinquency. Journal of Research in Crime and Delinquency, 38(4), 319–361. https://doi.org/10.1177/
0022427801038004001
Bandura, A. (1977). Social learning theory. Prentice Hall.
Brannen, D. E., Wynn, S., Shuster, J., & Howell, M. (2023). Pandemic isolation and mental health among children. Disaster
Medicine and Public Health Preparedness, 17, e353. https://doi.org/10.1017/dmp.2023.7
Buss, A. H., & Perry, M. (1992). The Aggression Questionnaire. Journal of Personality and Social Psychology, 63(3), 452–459.
https://doi.org/10.1037/0022-3514.63.3.452
Caprara, G. V., Barbaranelli, C., Pastorelli, C., Bandura, A., & Zimbardo, P. G. (2000). Prosocial foundations of children’s
academic achievement. Psychological Science, 11(4), 302–306. https://doi.org/10.1111/1467-9280.00260
Conduct Problems Prevention Research Group. (2010). Fast track intervention effects on youth arrests and delinquency.
Journal of Experimental Criminology, 6(2), 131–157. https://doi.org/10.1007/s11292-010-9091-7
Cosentino, C., Sarli, A., Guasconi, M., Mozzarelli, F., Foà, C., De Simone, R., Argiropoulos, D., Artioli, G., & Bonacaro, A.
(2024). Measuring the psychosocial impact of COVID-19 by means of the “international student well-being study
questionnaire”: Evidence on Italian university students. Heliyon, 10(7), e28342. https://doi.org/10.1016//j.heliyon.2024.
e28342
Cuartas, J. (2021). The effect of maternal education on parenting and early childhood development during COVID-19
lockdowns: Evidence from Colombia. Developmental Psychology, 57(11), 1847–1857. https://doi.org/10.1037/
dev0001264
Dishion, T. J., Véronneau, M. H., & Myers, M. W. (2010). Cascading peer dynamics underlying the progression from
problem behavior to violence in early to late adolescence. Development and Psychopathology, 22(3), 603–619. https://
doi.org/10.1017/S0954579410000313
Durlak, J. A., Mahoney, J. L., & Boyle, A. E. (2022). What we know, and what we need to find out about universal,
school-based social and emotional learning programs for children and adolescents: A review of meta-analyses and
directions for future research. Psychological Bulletin, 148(11–12), 765–782. https://doi.org/10.1037/bul0000383
Ettekal, I., & Ladd, G. W. (2020). Development of aggressive-victims from childhood through adolescence: Associations
with emotion dysregulation, withdrawn behaviors, moral disengagement, peer rejection, and friendships.
Development and Psychopathology, 32(1), 271–291. https://doi.org/10.1017/S0954579419000063
Farrell, A. D., Thompson, E. L., & Mehari, K. R. (2020). Dimensions of peer influences and their relationship to adolescents’
aggression, other problem behaviors and prosocial behavior. Journal of Youth and Adolescence, 46(6), 1351–1369.
https://doi.org/10.1007/s10964-016-0601-4
Floridi, M., Ferretti, F., Canale, N., Marino, C., Uvelli, A., & Lazzeri, G. (2025). The effects of social isolation and problematic
social media use on well-being in a sample of young Italian gamblers. Journal of Preventive Medicine and Hygiene, 66(2),
E153–E163. https://doi.org/10.15167/2421-4248/jpmh2025.66.2.3581
Fossati, A., Maffei, C., Acquarini, E., & DiCeglie, A. (2003). Multigroup confirmatory component and factor analyses of the
Italian version of the Aggression Questionnaire. European Journal of Psychological Assessment, 19(1), 54–65. https://doi.
org/10.1027//1015-5759.19.1.54
Garofalo, C., & Velotti, P. (2017). Negative emotionality and aggression in violent offenders: The moderating role of
emotion dysregulation. Journal of Criminal Justice, 51, 9–16. https://doi.org/10.1016/j.jcrimjus.2017.05.015
Gomis-Pomares, A., Villanueva, L., & Basto-Pereira, M. (2022). Psychometric properties of the Deviant Behavior Variety
Scale in young Spanish adults. Psicothema, 34(2), 308–315. https://doi.org/10.7334/psicothema2021.317
Horner, R. H., Sugai, G., & Anderson, C. M. (2010). Examining the evidence base for school-wide positive behavior support.
Focus on Exceptional Children, 42(8), 1–14. https://doi.org/10.17161/foec.v42i8.6906
Hussong, A. M., Midgette, A. J., Thomas, T. E., Coffman, J. L., & Cho, S. (2021). Coping and mental health in early
adolescence during COVID-19. Research on Child and Adolescent Psychopathology, 49(9), 1113–1123. https://doi.org/
10.1007/s10802-021-00821-0
The jamovi project. (2024). Jamovi (Version 2.6) [Computer software]. https://www.jamovi.org
Jiang, S., Chen, Y., & Wang, L. (2024). Effectiveness of community-based programs on aggressive behavior among
children and adolescents: A systematic review and meta-analysis. Trauma, Violence, & Abuse, 25(4), 2845–2861.
https://doi.org/10.1177/15248380241227986
Loades, M. E., Chatburn, E., Higson-Sweeney, N., Reynolds, S., Shafran, R., Brigden, A., Linney, C., McManus, M. N.,
Borwick, C., & Crawley, E. (2020). Rapid systematic review: The impact of social isolation and loneliness on the mental
health of children and adolescents in the context of COVID-19. Journal of the American Academy of Child and
Adolescent Psychiatry, 59(11), 1218–1239.e3. https://doi.org/10.1016/j.jaac.2020.05.009
Lochman, J. E., & Wells, K. C. (2004). The coping power program for preadolescent aggressive boys and their parents:
Outcome effects at the 1-year follow-up. Journal of Consulting and Clinical Psychology, 72(4), 571–578. https://doi.org/
10.1037/0022-006X.72.4.571
Masten, A. S., & Motti-Stefanidi, F. (2020). Multisystem resilience for children and youth in disaster: Reflections in the
context of COVID-19. Adversity and Resilience Science, 1(2), 95–106. https://doi.org/10.1007/s42844-020-00010-w
Mazrekaj, D., & De Witte, K. (2024). The impact of school closures on learning and mental health of children: Lessons from
the COVID-19 pandemic. Perspectives on Psychological Science: A Journal of the Association for Psychological Science, 19
(4), 686–693. https://doi.org/10.1177/17456916231181108
McLaughlin, K. A., Weissman, D., & Bitrán, D. (2021). Childhood adversity and neural development: A systematic review.
Annual Review of Developmental Psychology, 1(1), 277–312. https://doi.org/10.1146/annurev-devpsych-121318-084950
Muñoz-Fernández, N., & Rodríguez-Meirinhos, A. (2021). Adolescents’ concerns, routines, peer activities, frustration, and
optimism in the time of COVID-19 confinement in Spain. Journal of Clinical Medicine, 10(4), 798. https://doi.org/10.
3390/jcm10040798
Murray-Close, D., Holterman, L. A., Breslend, N. L., & Sullivan, A. (2022). Psychophysiology of proactive and reactive
relational aggression. Biological Psychology, 130, 77–85. https://doi.org/10.1016/j.biopsycho.2017.10.005
Oosterhoff, B., Palmer, C. A., Wilson, J. S., & Shook, N. (2020). Adolescents’ motivations to engage in social distancing
during the COVID-19 pandemic: Associations with mental and social health. Journal of Adolescent Health, 67(2),
179–185. https://doi.org/10.1016/j.jadohealth.2020.05.004
Panchal, U., Salazar de Pablo, G., Franco, M., Moreno, C., Parellada, M., Arango, C., & Fusar-Poli, P. (2023). The impact of
COVID-19 lockdown on child and adolescent mental health: Systematic review. European Child & Adolescent Psychiatry,
32(7), 1151–1177. https://doi.org/10.1007/s00787-021-01856-w
Pastorelli, C., Lansford, J. E., Luengo Kanacri, B. P., Malone, P. S., DiGiunta, L., Bacchini, D., Bombi, A. S., Zelli, A.,
Miranda, M. C., Bornstein, M. H., Tapanya, S., Uribe Tirado, L. M., Alampay, L. P., Al-Hassan, S. M., Chang, L., Deater-
Deckard, K., Dodge, K. A., Oburu, P., Skinner, A. T., & Sorbring, E. (2016). Positive parenting and children’s prosocial
behavior in eight countries. Journal of Child Psychology and Psychiatry, 57(7), 824–834. https://doi.org/10.1111/jcpp.
12477
Prime, H., Wade, M., & Browne, D. T. (2020). Risk and resilience in family well-being during the COVID-19 pandemic.
American Psychologist, 75(5), 631–643. https://doi.org/10.1037/amp0000660
Ravens-Sieberer, U., Erhart, M., Devine, J., Gilbert, M., Reiss, F., Barkmann, C., Siegel, N. A., Simon, A. M., Hurrelmann, K.,
Schlack, R., Hölling, H., Wieler, L. H., & Kaman, A. (2022). Child and adolescent mental health during the COVID-19
pandemic: Results of the three-wave longitudinal CoPSY study. The Journal of Adolescent Health: Official Publication of
the Society for Adolescent Medicine, 71(5), 570–578. https://doi.org/10.1016/j.jadohealth.2022.06.022
Romeo, R. D. (2017). The impact of stress on the structure of the adolescent brain: Implications for adolescent mental
health. Brain Research, 1654, 185–191. https://doi.org/10.1016/j.brainres.2016.03.021
Saulle, R., De Sario, M., Bena, A., Capra, P., Culasso, M., Davoli, M., De Lorenzo, A., Lattke, L. S., Marra, M., Mitrova, Z.,
Paduano, S., Rabaglietti, E., Sartini, M., & Minozzi, S. (2022). School closures and mental health, wellbeing and health
behaviours among children and adolescents during the second COVID-19 wave: a systematic review of the literature.
Chiusura della scuola e salute mentale, benessere e comportamenti correlati alla salute in bambini e adolescenti durante la seconda ondata di COVID-19: una revisione sistematica della letteratura. Epidemiologia e prevenzione, 46
(5–6), 333–352. https://doi.org/10.19191/EP22.5-6.A542.089
Semple, R. J., Lee, J., Rosa, D., & Miller, L. F. (2010). A randomized trial of mindfulness-based cognitive therapy for children:
Promoting mindful attention to enhance social-emotional resiliency in children. Journal of Child and Family Studies, 19
(2), 218–229. https://doi.org/10.1007/s10826-009-9301-y
Singh, S., Roy, D., Sinha, K., Parveen, S., Sharma, G., & Joshi, G. (2020). Impact of COVID-19 and lockdown on mental health
of children and adolescents: A narrative review with recommendations. Psychiatry Research, 293, 113429. https://doi.
org/10.1016/j.psychres.2020.113429
Steinberg, L. (2013). The influence of neuroscience on US Supreme Court decisions about adolescents’ criminal
culpability. Nature Reviews Neuroscience, 14(7), 513–518. https://doi.org/10.1038/nrn3509
Steinhoff, A., Johnson-Ferguson, L., Bechtiger, L., Murray, A., Hepp, U., Ribeaud, D., Eisner, M., & Shanahan, L. (2023). Early
adolescent predictors of young adults’ distress and adaptive coping during the COVID-19 pandemic: Findings from
a longitudinal cohort study. Journal of Early Adolescence, 44(9), 1250–1280. https://doi.org/10.1177/
02724316231181660
Sukhodolsky, D. G., Smith, S. D., McCauley, S. A., Ibrahim, K., & Piasecka, J. B. (2016). Behavioral interventions for anger,
irritability, and aggression in children and adolescents. Journal of Child and Adolescent Psychopharmacology, 26(1),
58–64. https://doi.org/10.1089/cap.2015.0120
Tzankova, I., Compare, C., Marzana, D., Guarino, A., DiNapoli, I., Rochira, A., Calandri, E., Barbieri, I., Procentese, F., Gatti, F.,
Marta, E., Fedi, A., Aresi, G., & Albanesi, C. (2023). Emergency online school learning during COVID-19 lockdown:
A qualitative study of adolescents’ experiences in Italy. Current Psychology, 42, 12743–12755. https://doi.org/10.1007/
s12144-021-02674-8
Van de Weijer-Bergsma, E., Langenberg, G., Brandsma, R., Oort, F. J., & Bögels, S. M. (2014). The effectiveness of a
school-based mindfulness training as a program to prevent stress in elementary school children. Mindfulness, 5(3),
238–248. https://doi.org/10.1007/s12671-012-0171-9
Wang, Z., Li, C., & Ai, K. (2022). Family economic strain and adolescent aggression during the COVID-19 pandemic: Roles of
interparental conflict and parent-child conflict. Applied Research in Quality of Life, 17(4), 2369–2385. https://doi.org/10.
1007/s11482-022-10042-2
Weissman, D. G., Rodman, A. M., Rosen, M. L., Kasparek, S., Mayes, M., Sheridan, M. A., McLaughlin, K. A., Meltzoff, A. N., &
McLaughlin, K. A. (2021). Contributions of emotion regulation and brain structure and function to adolescent
internalizing problems and stress vulnerability during the COVID-19 pandemic: A longitudinal study. Biological
Psychiatry Global Open Science, 1(4), 272–282. https://doi.org/10.1016/j.bpsgos.2021.06.001
Wolf, K., & Schmitz, J. (2023). Scoping review: Longitudinal effects of the COVID-19 pandemic on child and adolescent
mental health. European Child & Adolescent Psychiatry, 33(5), 1257–1312. https://doi.org/10.1007/s00787-023-02206-8
Zurlo, M. C., Cattaneo Della Volta, M. F., & Vallone, F. (2020). COVID-19 student stress questionnaire: Development and
validation of a questionnaire to evaluate students’ stressors related to the coronavirus pandemic lockdown. Frontiers in
Psychology, 11, 576758. https://doi.org/10.3389/fpsyg.2020.576758"""

test14 = """Apostolou, M., Sullman, M., Birkás, B., Błachnio, A.,
Bushina, E., Calvo, F., Costello, W., Dujlovic, T.,
Hill, T., Lajunen, T. J., Lisun, Y., Manrique-
Millones, D., Manrique-Pino, O., Meskó, N., Nech-
telberger, M., Ohtsubo, Y., Ollhoff, C. K., Prze-
piórka, A., Putz, Á., … Font-Mayolas, S. (2023).
Mating performance and singlehood across 14
nations. Evolutionary Psychology, 21(1), Article
14747049221150169. https://doi.org/10.1177/147
47049221150169
Apostolou, M., Sullman, M., Błachnio, A., Burýšek,
O., Bushina, E., Calvo, F., Costello, W., Helmy,
M., Hill, T., Karageorgiou, M. G., Lisun, Y.,
Manrique-Millones, D., Manrique-Pino, O., Oht-
subo, Y., Przepiórka, A., Saar, O. C., Tekeş , B., Thomas, A. G., Wang, Y., & Font-Mayolas, S.
(2024). Emotional wellbeing and life satisfaction
of singles and mated people across 12 nations. Evo-
lutionary Psychological Science, 10(4), 352–369.
https://doi.org/10.1007/s40806-024-00416-0
Apter, D. (1980). Serum steroids and pituitary hor-
mones in female puberty: A partly longitudinal
study. Clinical Endocrinology, 12(2), 107–120.
https://doi.org/10.1111/j.1365-2265.1980.tb02125.x
Aung, T., & Williams, L. (2018). Lower waist-to-hip,
waist-to-stature, and waist-to-bust ratios predict
higher rankings of plus-size models in a naturalistic
condition. Human Ethology Bulletin, 33(4), 3–18.
https://doi.org/10.22330/heb/334/003-018
Awan, S. N. (2006). The aging female voice: Acoustic
and respiratory data. Clinical Linguistics & Phonet-
ics, 20(2–3), 171–180. https://doi.org/10.1080/02
699200400026918
Barrett, D. (2010). Supernormal stimuli: How primal
urges overran their evolutionary purpose. WW
Norton & Company.
Bird, A. R., Menz, H. B., & Hyde, C. C. (1999). The
effect of pregnancy on footprint parameters: A pro-
spective investigation. Journal of the American
Podiatric Medical Association, 89(8), 405–409.
https://doi.org/10.7547/87507315-89-8-405
Block, R. A., Hess, L. A., Timpano, E. V., & Serlo, C.
(1985). Physiologic changes in the foot during preg-
nancy. Journal of the American Podiatric Medical
Association, 75(6), 297–299. https://doi.org/10.75
47/87507315-75-6-297
Boot, A. M., Bouquet, J., De Ridder, M. A., Krenning,
E. P., & de Muinck Keizer-Schrama, S. M. (1997).
Determinants of body composition measured by
dual-energy X-ray absorptiometry in Dutch children
and adolescents. The American Journal of Clinical
Nutrition, 66(2), 232–238. https://doi.org/10.1093/
ajcn/66.2.232
Bovet, J. (2019). Evolutionary theories and men’s
preferences for women’s waist-to-hip ratio: Which
hypotheses remain? A systematic review. Frontiers
in Psychology, 10, Article 1221. https://doi.org/10
.3389/fpsyg.2019.01221
Bovet, J., & Raymond, M. (2015). Preferred women’s
waist-to-hip ratio variation over the last 2,500 years.
PLoS ONE, 10(4), Article e0123284. https://
doi.org/10.1371/journal.pone.0123284
Brase, G. L., & Dillon, M. H. (2022). Digging deeper
into the relationship between self-esteem and mate
value. Personality and Individual Differences, 185,
Article 111219. https://doi.org/10.1016/j.paid.2021
.111219
Brody, S., & Weiss, P. (2013). Slimmer women’s waist
is associated with better erectile function in men
independent of age. Archives of Sexual Behavior,
42(7), 1191–1198. https://doi.org/10.1007/s10508-
012-0058-9
Brooks, R. (2021). Artificial intimacy: Virtual friends,
digital lovers, and algorithmic matchmakers.
Columbia University Press.
Brooks, R., Shelly, J. P., Fan, J., Zhai, L., & Chau, D.
K. P. (2010). Much more than a ratio: Multivariate
selection on female bodies. Journal of Evolutionary
Biology, 23(10), 2238–2248. https://doi.org/10
.1111/j.1420-9101.2010.02088.x
Brooks, R. C., Shelly, J. P., Jordan, L. A., & Dixson,
B. J. W. (2015). The multivariate evolution of female
body shape in an artificial digital ecosystem. Evolu-
tion and Human Behavior, 36(5), 351–358. https://
doi.org/10.1016/j.evolhumbehav.2015.02.001
Brown, W. M., Price, M. E., Kang, J., Pound, N., Zhao,
Y., & Yu, H. (2008). Fluctuating asymmetry and
preferences for sex-typical bodily characteristics. Pro-
ceedings of the National Academy of Sciences,
105(35), 12938–12943. https://doi.org/10.1073/pnas
.0710420105
Bryant, G. A., & Haselton, M. G. (2009). Vocal cues of
ovulation in human females. Biology Letters, 5(1),
12–15. https://doi.org/10.1098/rsbl.2008.0507
Burch, R. L., & Johnsen, L. (2020). Captain Dorito
and the bombshell: Supernormal stimuli in comics
and film. Evolutionary Behavioral Sciences, 14(2),
115–131. https://doi.org/10.1037/ebs0000164
Burch, R. L., & Widman, D. R. (2021). The point of
nipple erection 1: The experience and projection of
perceived emotional states while viewing women
with and without erect nipples. Evolutionary Behav-
ioral Sciences, 15(3), 305–311. https://doi.org/10
.1037/ebs0000244
Burch, R. L., & Widman, D. R. (2023). Comic book
bodies are supernormal stimuli: Comparison of DC,
Marvel, and actual humans. Evolutionary Behavioral
Sciences, 17(3), 245–258. https://doi.org/10.1037/
ebs0000280
Burch, R. L., & Widman, D. R. (2024). The point of
nipple erection 3: Sexual and social expectations
of women with nipple erection. Evolutionary Behav-
ioral Sciences, 18(2), 119–131. https://doi.org/10
.1037/ebs0000312
Buss, D. M. (1989). Sex differences in human mate pref-
erences: Evolutionary hypotheses tested in 37 cul-
tures. Behavioral and Brain Sciences, 12(1), 1–14.
https://doi.org/10.1017/S0140525X00023992
Buss, D. M., Durkee, P. K., Shackelford, T. K., Bowdle,
B. F., Schmitt, D. P., Brase, G. L., Choe, J. C., & Tro-
fimova, I. (2020). Human status criteria: Sex differ-
ences and similarities across 14 nations. Journal of
Personality and Social Psychology, 119(5), 979–998.
https://doi.org/10.1037/pspa0000206
Buss, D. M., & Schmitt, D. P. (1993). Sexual strategies
theory: An evolutionary perspective on human mat-
ing. Psychological Review, 100(2), 204–232. https://
doi.org/10.1037/0033-295X.100.2.204
Butovskaya, M., Sorokowska, A., Karwowski, M., Sabi-
niewicz, A., Fedenok, J., Dronova, D., Negasheva, M., Selivanova, E., & Sorokowski, P. (2017).
Waist-to-hip ratio, body-mass index, age, and number
of children in seven traditional societies. Scientific
Reports, 7(1), Article 1622. https://doi.org/10.1038/
s41598-017-01916-9
Cameron, C., Oskamp, S., & Sparks, W. (1977).
Courtship American style: Newspaper ads. Family
Coordinator, 26(1), 27–30. https://doi.org/10.23
07/581857
Chantelau, E., & Gede, A. (2002). Foot dimensions
of elderly people with and without diabetes melli-
tus: A data basis for shoe design. Gerontology,
48(4), 241–244. https://doi.org/10.1159/000058357
Coe, K., & Steadman, L. B. (1995). The human breast
and the ancestral reproductive cycle: A preliminary
inquiry into breast cancer etiology. Human Nature,
6(3), 197–220. https://doi.org/10.1007/BF02734139
Connolly, J. M., Slaughter, V., & Mealey, L. (2004).
The development of preferences for specific body
shapes. Journal of Sex Research, 41(1), 5–15.
https://doi.org/10.1080/00224490409552209
Conroy-Beam, D., & Buss, D. M. (2019). Why is age so
important in human mating? Evolved age preferences
and their influences on multiple mating behaviors.
Evolutionary Behavioral Sciences, 13(2), 127–157.
https://doi.org/10.1037/ebs0000127
Costello, W., Rolon, V., Thomas, A. G., & Schmitt, D.
(2022). Levels of well-being among men who are
incel (involuntarily celibate). Evolutionary Psycho-
logical Science, 8(4), 375–390. https://doi.org/10
.1007/s40806-022-00336-x
Costello, W., Rolon, V., Thomas, A. G., & Schmitt, D.
P. (2024). The mating psychology of incels (involun-
tary celibates): Misfortunes, misperceptions, and
misrepresentations. The Journal of Sex Research,
61(7), 989–1000. https://doi.org/10.1080/00224499
.2023.2248096
Costello, W., Sedlacek, A. G. B., Durkee, P. K.,
Crosby, C. L., Hahnel-Peeters, R. K., & Buss, D.
M. (in press). Evolutionary psychology hypotheses
are testable and falsifiable. American Psychologist.
https://doi.org/10.1037/amp0001529
Costello, W., Whittaker, J., & Thomas, A. G. (2025).
The dual pathways hypothesis of incel harm: A
model of harmful attitudes and beliefs among invol-
untary celibates. Archives of Sexual Behavior, 54,
1815–1836. https://doi.org/10.1007/s10508-025-
03161-y
Courtiol, A., Raymond, M., Godelle, B., & Ferdy, J. B.
(2010). Mate choice and human stature: Homogamy
as a unified framework for understanding mating
preferences. Evolution, 64(8), 2189–2203. https://
doi.org/10.1111/j.1558-5646.2010.00985.x
Crossley, K. L., Cornelissen, P. L., & Tovée, M. J.
(2012). What is an attractive body? Using an interac-
tive 3D program to create the ideal body for you and
your partner. PLoS ONE, 7(11), Article e50601.
https://doi.org/10.1371/journal.pone.0050601
Davis, A. C., & Arnocky, S. (2022). An evolutionary
perspective on appearance enhancement behavior.
Archives of Sexual Behavior, 51(1), 3–37. https://
doi.org/10.1007/s10508-020-01745-4
Dixson, B. J., Dixson, A. F., Li, B., & Anderson, M. J.
(2007). Studies of human physique and sexual attrac-
tiveness: Sexual preferences of men and women in
China. American Journal of Human Biology, 19(1),
88–95. https://doi.org/10.1002/ajhb.20584
Dixson, B. J., Duncan, M., & Dixson, A. F. (2015).
The role of breast size and areolar pigmentation in
perceptions of women’s sexual attractiveness, repro-
ductive health, sexual maturity, maternal nurturing
abilities, and age. Archives of Sexual Behavior,
44(6), 1685–1695. https://doi.org/10.1007/s10508-
015-0516-2
Dixson, B. J., Grimshaw, G. M., Linklater, W. L., &
Dixson, A. F. (2011). Eye-tracking of men’s prefer-
ences for waist-to-hip ratio and breast size of
women. Archives of Sexual Behavior, 40(1), 43–50.
https://doi.org/10.1007/s10508-009-9523-5
Dixson, B. J., Sagata, K., Linklater, W. L., & Dixson,
A. F. (2010). Male preferences for female
waist-to-hip ratio and body mass index in the high-
lands of Papua New Guinea. American Journal of
Physical Anthropology, 141(4), 620–625. https://
doi.org/10.1002/ajpa.21181
Döring, N., & Pöschl, S. (2018). Sex toys, sex dolls,
sex robots: Our under-researched bed-fellows. Sex-
ologies, 27(3), e51–e55. https://doi.org/10.1016/j
.sexol.2018.05.009
Doyle, J. F., & Pazhoohi, F. (2012). Natural and aug-
mented breasts: Is what is not natural most attrac-
tive? Human Ethology Bulletin, 27(4), 4–14.
https://doi.org/10.22330/001c.89867
Dubé, S., & Anctil, D. (2021). Foundations of ero-
botics. International Journal of Social Robotics,
13(6), 1205–1233. https://doi.org/10.1007/s12369-
020-00706-0
Ellis, B. J. (2004). Timing of pubertal maturation in
girls: An integrated life history approach. Psycho-
logical Bulletin, 130(6), 920–958. https://doi.org/
10.1037/0033-2909.130.6.920
Ellison, P. T., Lager, C., & Calfee, J. (1987). Low pro-
files of salivary progesterone among college under-
graduate women. Journal of Adolescent Health
Care, 8(2), 204–207. https://doi.org/10.1016/0197-
0070(87)90266-X
Feinberg, D. R., DeBruine, L. M., Jones, B. C., & Per-
rett, D. I. (2008). The role of femininity and average-
ness of voice pitch in aesthetic judgments of women’s
voices. Perception, 37(4), 615–623. https://doi.org/10
.1068/p5514
Feinman, S., & Gill, G. W. (1978). Sex differences in
physical attractiveness preferences. The Journal of
Social Psychology, 105(1), 43–52. https://doi.org/
10.1080/00224545.1978.9924089
Ferguson, A. (2010). The sex doll: A history. McFarland.
Fessler, D. M., Haley, K. J., & Lal, R. D. (2005). Sex-
ual dimorphism in foot length proportionate to stat-
ure. Annals of Human Biology, 32(1), 44–59.
https://doi.org/10.1080/03014460400027581
Fessler, D. M., Nettle, D., Afshar, Y., Pinheiro, I. A.,
Bolyanatz, A., Mulder, M. B., Cravalho, M., Del-
gado, T., Gruzd, B., Correia, M. O., Khaltourina,
D., Korotayev, A., Marrow, J., de Souza, L. S., &
Zbarauskaite, A. (2005). A cross-cultural investiga-
tion of the role of foot size in physical attractiveness.
Archives of Sexual Behavior, 34(3), 267–276.
https://doi.org/10.1007/s10508-005-3115-9
Fink, B., Grammer, K., & Matts, P. J. (2006). Visible
skin color distribution plays a role in the perception
of age, attractiveness, and health in female faces. Evo-
lution and Human Behavior, 27(6), 433–442. https://
doi.org/10.1016/j.evolhumbehav.2006.08.007
Fink, B., Grammer, K., & Thornhill, R. (2001). Human
(Homo sapiens) facial attractiveness in relation to
skin texture and color. Journal of Comparative Psy-
chology, 115(1), 92–99. https://doi.org/10.1037/07
35-7036.115.1.92
Fink, B., Klappauf, D., Brewer, G., & Shackelford, T.
K. (2014). Female physical characteristics and intra-
sexual competition in women. Personality and Indi-
vidual Differences, 58, 138–141. https://doi.org/10
.1016/j.paid.2013.10.015
Fink, B., Neave, N., Brewer, G., & Pawlowski, B.
(2007). Variable preferences for sexual dimorphism
in stature (SDS): Further evidence for an adjustment
in relation to own height. Personality and Individual
Differences, 43(8), 2249–2257. https://doi.org/10
.1016/j.paid.2007.07.014
Fitzgerald, C. J., Horgan, T. G., & Himes, S. M. (2016).
Shaping men’s memory: The effects of a female’s
waist-to-hip ratio on men’s memory for her appear-
ance and biographical information. Evolution and
Human Behavior, 37(6), 510–516. https://doi.org/
10.1016/j.evolhumbehav.2016.05.004
Forbes, G. B., & Frederick, D. A. (2008). The UCLA
body project II: Breast and body dissatisfaction
among African, Asian, European, and Hispanic
American college women. Sex Roles, 58(7–8),
449–457. https://doi.org/10.1007/s11199-007-9362-6
Ford, C. S., & Beach, F. A. (1951). Patterns of sexual
behavior. Greenwood Press.
Forestell, C. A., Humphrey, T. M., & Stewart, S. H.
(2004). Involvement of body weight and shape factors
in ratings of attractiveness by women: A replication
and extension of Tassinary and Hansen (1998). Per-
sonality and Individual Differences, 36(2), 295–305.
https://doi.org/10.1016/S0191-8869(03)00085-0
Foti, T., Davids, J. R., & Bagley, A. (2000). A biome-
chanical analysis of gait during pregnancy. JBJS,
82(5), 625–632. https://doi.org/10.2106/00004623-
200005000-00003
Fraccaro, P. J., Jones, B. C., Vukovic, J., Smith, F. G.,
Watkins, C. D., Feinberg, D. R., Little, A. C., &
Debruine, L. M. (2011). Experimental evidence
that women speak in a higher voice pitch to men
they find attractive. Journal of Evolutionary Psy-
chology, 9(1), 57–67. https://doi.org/10.1556/jep.9
.2011.33.1
Frederick, D. A., & Jenkins, B. N. (2015). Height and
body mass on the mating market: Associations with
number of sex partners and extra-pair sex among
heterosexual men and women aged 18–65. Evolu-
tionary Psychology, 13(3), Article 14747049156
04563. https://doi.org/10.1177/1474704915604563
Frey, C., Thompson, F., Smith, J., Sanders, M., &
Horstman, H. (1993). American Orthopaedic Foot
and Ankle Society women’s shoe survey. Foot &
Ankle, 14(2), 78–81. https://doi.org/10.1177/107
110079301400204
Frisch, R. E. (1985). Fatness, menarche, and female
fertility. Perspectives in Biology and Medicine,
28(4), 611–633. https://doi.org/10.1353/pbm.1985
.0010
Furnham, A., Tan, T., & McManus, C. (1997).
Waist-to-hip ratio and preferences for body shape:
A replication and extension. Personality and Individ-
ual Differences, 22(4), 539–549. https://doi.org/10
.1016/S0191-8869(96)00241-3
Garza, R., Heredia, R. R., & Cieslicka, A. B. (2016).
Male and female perception of physical attractiveness:
An eye movement study. Evolutionary Psychology,
14(1), Article 1474704916631614. https://doi.org/
10.1177/1474704916631614
Garza, R., & Pazhoohi, F. (2023a). Breasts: Female
attractiveness. In T. K. Shackelford (Ed.), Ency-
clopedia of sexual psychology and behavior (pp.
1–7). Springer. https://doi.org/10.1007/978-3-031-
08956-5_570-1
Garza, R., & Pazhoohi, F. (2023b). Intrasexual compe-
tition in women’s likelihood of self-enhancement
and perceptions of breast morphology: A Hispanic
sample. Sexes, 4(1), 80–93. https://doi.org/10.3390/
sexes4010008
Garza, R., Pazhoohi, F., & Byrd-Craven, J. (2021).
Does ecological harshness influence men’s percep-
tions of breasts: Female attractiveness women’s
breast size, ptosis, and intermammary distance? Evo-
lutionary Psychological Science, 7(2), 174–183.
https://doi.org/10.1007/s40806-020-00262-w
Gawley, T., Perks, T., & Curtis, J. (2009). Height, gen-
der, and authority status at work: Analyses for a
national sample of Canadian workers. Sex Roles,
60(3–4), 208–222. https://doi.org/10.1007/s11199-
008-9520-5
Gillis, J. S., & Avis, W. E. (1980). The male-taller
norm in mate selection. Personality and Social Psy-
chology Bulletin, 6(3), 396–401. https://doi.org/10
.1177/014616728063010
Goetz, C. D., Pillsworth, E. G., Buss, D. M., & Conroy-
Beam, D. (2019). Evolutionary mismatch in mating. Frontiers in Psychology, 10, Article 2709. https://
doi.org/10.3389/fpsyg.2019.02709
Gould, S. J. (2008). A biological homage to Mickey
Mouse. Ecotone, 4(1–2), 333–340. https://doi.org/
10.1353/ect.2008.0045
Gray, P. B., & Frederick, D. A. (2012). Body image
and body type preferences in St. Kitts, Caribbean:
A cross-cultural comparison with US samples
regarding attitudes towards muscularity, body fat,
and breast size. Evolutionary Psychology, 10(3),
631–655. https://doi.org/10.1177/1474704912010
00319
Groyecka, A., Ż elaź niewicz, A., Misiak, M., Karwow-
ski, M., & Sorokowski, P. (2017). Breast shape (pto-
sis) as a marker of a woman’s breast attractiveness
and age: Evidence from Poland and Papua. Ameri-
can Journal of Human Biology, 29(4), Article
e22981. https://doi.org/10.1002/ajhb.22981
Gründl, M., Eisenmann-Klein, M., & Prantl, L.
(2009). Quantifying female bodily attractiveness
by a statistical analysis of body measurements. Plas-
tic and Reconstructive Surgery, 123(3), 1064–1071.
https://doi.org/10.1097/PRS.0b013e318199f7a6
Gunn, D. A., Rexbye, H., Griffiths, C. E., Murray, P.
G., Fereday, A., Catt, S. D., Tomlin, C. C., Strong-
itharm, B. H., Perrett, D. I., Catt, M., Mayes, A. E.,
Messenger, A. G., Green, M. R., van der Ouderaa,
F., Vaupel, J. W., & Christensen, K. (2009). Why
some women look young for their age. PLoS
ONE, 4(12), Article e8021. https://doi.org/10.137
1/journal.pone.0008021
Hanson, K. R., Döring, N., & Walter, R. (2024). Sex
doll specifications versus human body characteris-
tics. Archives of Sexual Behavior, 53(6), 2025–
2033. https://doi.org/10.1007/s10508-024-02871-z
Harper, C. A., Lievesley, R., & Wanless, K. (2023).
Exploring the psychological characteristics and
risk-related cognitions of individuals who own sex
dolls. The Journal of Sex Research, 60(2), 190–205.
https://doi.org/10.1080/00224499.2022.2031848
Haselton, M. G., & Buss, D. M. (2000). Error manage-
ment theory: A new perspective on biases in cross-
sex mind reading. Journal of Personality and Social
Psychology, 78(1), 81–91. https://doi.org/10.1037/
0022-3514.78.1.81
Haselton, M. G., & Gildersleeve, K. (2011). Can men
detect ovulation? Current Directions in Psycholog-
ical Science, 20(2), 87–92. https://doi.org/10.1177/
0963721411402668
Havlíček, J., Třebický, V., Valentova, J. V., Kleisner,
K., Akoko, R. M., Fialová, J., Jash, R., Koč nar,
T., Pereira, K. J., Ště rbová, Z., Varella, M. A. C.,
Vokurková, J., Vunan, E., & Roberts, S. C.
(2017). Men’s preferences for women’s breast size
and shape in four cultures. Evolution and Human
Behavior, 38(2), 217–226. https://doi.org/10.1016/
j.evolhumbehav.2016.10.002
Hewig, J., Trippe, R. H., Hecht, H., Straube, T., &
Miltner, W. H. R. (2008). Gender differences for
specific body regions when looking at men and
women. Journal of Nonverbal Behavior, 32(2),
67–78. https://doi.org/10.1007/s10919-007-0043-5
Hinde, R. A., & Barden, L. A. (1985). The evolution of
the teddy bear. Animal Behaviour, 33(4), 1371–1373.
https://doi.org/10.1016/S0003-3472(85)80205-0
Horvath, T. (1979). Correlates of physical beauty in
men and women. Social Behavior & Personality,
7(2), 145–151. https://doi.org/10.2224/sbp.1979.7
.2.145
Jackson, B. (1997). Splendid slippers: A thousand
years of an erotic tradition. Ten Speed Press.
Jasieńska, G., Ziomkiewicz, A., Ellison, P. T., Lipson,
S. F., & Thune, I. (2004). Large breasts and narrow
waists indicate high reproductive potential in
women. Proceedings of the Royal Society of London.
Series B: Biological Sciences, 271(1545), 1213–
1217. https://doi.org/10.1098/rspb.2004.2712
Jones, D., Brace, C. L., Jankowiak, W., Laland, K. N.,
Musselman, L. E., Langlois, J. H., Roggman, L. A.,
Pérusse, D., Schweder, B., & Symons, D. (1995).
Sexual selection, physical attractiveness, and facial
neoteny: Cross-cultural evidence and implications.
Current Anthropology, 36(5), 723–748. https://
doi.org/10.1086/204427
Judge, T. A., & Cable, D. M. (2004). The effect of
physical height on workplace success and income:
Preliminary test of a theoretical model. Journal of
Applied Psychology, 89(3), 428–441. https://doi.org/
10.1037/0021-9010.89.3.428
Karremans, J. C., Frankenhuis, W. E., & Arons, S.
(2010). Blind men prefer a low waist-to-hip ratio. Evo-
lution and Human Behavior, 31(3), 182–186. https://
doi.org/10.1016/j.evolhumbehav.2009.10.001
King, R. (2013). Baby got back: Some brief observa-
tions on obesity in ancient female figurines: Limited
support for waist to hip ratio constant as a signal of
fertility. Journal of Obesity and Weight Loss Ther-
apy, 03(01), Article 159. https://doi.org/10.4172/2
165-7904.1000159
Kirschner, M. A., & Samojlik, E. (1991). Sex hormone
metabolism in upper and lower body obesity. Inter-
national Journal of Obesity, 15(Suppl. 2), 101–108.
https://pubmed.ncbi.nlm.nih.gov/1794930/
Klassen, A. F., Pusic, A. L., Scott, A., Klok, J., &
Cano, S. J. (2009). Satisfaction and quality of life
in women who undergo breast surgery: A qualitative
study. BMC Women’s Health, 9(1), Article 11.
https://doi.org/10.1186/1472-6874-9-11
Knox, D., Huff, S., & Chang, I. J. (2017). Sex dolls—
Creepy or healthy?: Attitudes of undergraduates.
Journal of Positive Sexuality, 3(2), 32–37. https://
journalofpositivesexuality.org/wp-content/uploads/
2022/06/10.56181.1.323_Sex-dolls-attitudes-of-under
graduates-Knox-Huff-Chang.pdf; https://doi.org/10
.51681/1.323
Kościń ski, K. (2013). Attractiveness of women’s
body: Body mass index, waist–hip ratio, and their
relative importance. Behavioral Ecology, 24(4),
914–925. https://doi.org/10.1093/beheco/art016
Kościński, K. (2014). Assessment of waist-to-hip ratio
attractiveness in women: An anthropometric analysis
of digital silhouettes. Archives of Sexual Behavior,
43(5), 989–997. https://doi.org/10.1007/s10508-013-
0166-1
Kościń ski, K. (2019). Breast firmness is of greater
importance to women’ attractiveness than breast
size. Archives of Sexual Behavior, 31(5), Article
e23287. https://doi.org/10.1002/ajhb.23287
Kurzban, R., & Weeden, J. (2005). Hurrydate: Mate
preferences in action. Evolution and Human
Behavior, 26(3), 227–244. https://doi.org/10.101
6/j.evolhumbehav.2004.08.012
Larsen, U., & Yan, S. (2000). The age pattern of fecund-
ability: An analysis of French Canadian and Hutterite
birth histories. Social Biology, 47(1–2), 34–50.
https://doi.org/10.1080/19485565.2000.9989008
Lassek, W. D., & Gaulin, S. J. (2006). Changes in body
fat distribution in relation to parity in American
women: A covert form of maternal depletion. Ameri-
can Journal of Physical Anthropology, 131(2), 295–
302. https://doi.org/10.1002/ajpa.20394
Lassek, W. D., & Gaulin, S. J. (2007). Menarche is
related to fat distribution. American Journal of Physi-
cal Anthropology, 133(4), 1147–1151. https://doi.org/
10.1002/ajpa.20644
Lassek, W. D., & Gaulin, S. J. (2008). Waist-hip ratio
and cognitive ability: Is gluteofemoral fat a privi-
leged store of neurodevelopmental resources? Evo-
lution and Human Behavior, 29(1), 26–34. https://
doi.org/10.1016/j.evolhumbehav.2007.07.005
Lassek, W. D., & Gaulin, S. J. (2016). What makes
Jessica Rabbit sexy? Contrasting roles of waist and
hip size. Evolutionary Psychology, 14(2), Article
1474704916643459. https://doi.org/10.1177/1474
704916643459
Lassek, W. D., & Gaulin, S. J. (2018). Do the low
WHRs and BMIs judged most attractive indicate
higher fertility? Evolutionary Psychology, 16(4),
Article 1474704918800063. https://doi.org/10.117
7/1474704918800063
Lassek, W. D., & Gaulin, S. J. (2021). Does nubility
indicate more than high reproductive value? Nubile
primiparas’ pregnancy outcomes in evolutionary
perspective. Evolutionary Psychology, 19(3), Arti-
cle 14747049211039506. https://doi.org/10.1177/
14747049211039506
Lewis, D. M., Evans, K. C., & Al-Shawaf, L. (2022).
The logic of physical attractiveness: What people
find attractive, when, and why. In D. M. Buss
(Ed.), The Oxford handbook of human mating (pp.
178–205). Oxford University Press.
Lewis, D. M., Russell, E. M., Al-Shawaf, L., Ta, V.,
Senveli, Z., Ickes, W., & Buss, D. M. (2017).
Why women wear high heels: Evolution, lumbar
curvature, and attractiveness. Frontiers in Psychol-
ogy, 8, Article 1875. https://doi.org/10.3389/fpsyg
.2017.01875
Li, N. P. (2007). Mate preference necessities in long-
and short-term mating: People prioritize in them-
selves what their mates prioritize in them. Acta Psy-
chologica Sinica, 39(3), 528–535. https://ink.library.
smu.edu.sg/soss_research/723
Li, N. P., Bailey, J. M., Kenrick, D. T., & Linsenmeier,
J. A. (2002). The necessities and luxuries of mate
preferences: Testing the tradeoffs. Journal of Per-
sonality and Social Psychology, 82(6), 947–955.
https://doi.org/10.1037/0022-3514.82.6.947
Lievesley, R., Reynolds, R., & Harper, C. A. (2023).
The ‘perfect’ partner: Understanding the lived expe-
riences of men who own sex dolls. Sexuality & Cul-
ture, 27(4), 1419–1441. https://doi.org/10.1007/
s12119-023-10071-5
Lim, J. S., Hwang, J. S., Cheon, G. J., Lee, J. A., Kim,
D. H., Park, K. D., & Yi, K. H. (2009). Gender dif-
ferences in total and regional body composition
changes as measured by dual-energy x-ray absorpti-
ometry in Korean children and adolescents. Journal
of Clinical Densitometry, 12(2), 229–237. https://
doi.org/10.1016/j.jocd.2008.12.008
Lorenz, K. (1950). Wholeness and part in animal and
human society: A methodological discussion.
Springer.
Loucks, A. B. (2006). The response of luteinizing hor-
mone pulsatility to 5 days of low energy availability
disappears by 14 years of gynecological age. The
Journal of Clinical Endocrinology & Metabolism,
91(8), 3158–3164. https://doi.org/10.1210/jc.2006-
0570
Lynn, M., & Shurgot, B. A. (1984). Responses to lonely
hearts advertisements: Effects of reported physical
attractiveness, physique, and coloration. Personality
and Social Psychology Bulletin, 10(3), 349–357.
https://doi.org/10.1177/0146167284103002
Macgregor, S., Cornes, B. K., Martin, N. G., &
Visscher, P. M. (2006). Bias, precision and heritabil-
ity of self-reported and clinically measured height in
Australian twins. Human Genetics, 120(4), 571–580.
https://doi.org/10.1007/s00439-006-0240-z
Marković , S. (2017). Attractiveness of the female
body: Preference for the average or the supernor-
mal? Psihologija, 50(3), 403–426. https://doi.org/
10.2298/PSI1703403M
Marlowe, F. (1998). The nubility hypothesis: The
human breast as an honest signal of residual repro-
ductive value. Human Nature, 9(3), 263–271.
https://doi.org/10.1007/s12110-998-1005-2
Marlowe, F. W. (2005). Hunter-gatherers and human
evolution. Evolutionary Anthropology, 14(2), 54–67.
https://doi.org/10.1002/evan.20046
McEvoy, B. P., & Visscher, P. M. (2009). Genetics of
human height. Economics & Human Biology, 7(3),
294–306. https://doi.org/10.1016/j.ehb.2009.09.005
Montoya, R. M. (2007). Gender similarities and differ-
ences in preferences for specific body parts. Current
Research in Social Psychology, 13(11), 133–144.
https://psycnet.apa.org/record/2008-10307-001
Morán, C., Hernández, E., Ruíz, J. E., Fonseca, M. E.,
Bermúdez, J. A., & Zárate, A. (1999). Upper body
obesity and hyperinsulinemia are associated with
anovulation. Gynecologic and Obstetric Investiga-
tion, 47(1), 1–5. https://doi.org/10.1159/000010052
Morris, P. H., White, J., Morrison, E. R., & Fisher, K.
(2013). High heels as supernormal stimuli: How
wearing high heels affects judgments of female attrac-
tiveness. Evolution and Human Behavior, 34(3),
176–181. https://doi.org/10.1016/j.evolhumbehav.20
12.11.006
National Center for Health Statistics. (2023). National
Health and Nutrition Examination Survey (NHANES),
2021–2023 data. U.S. Department of Health &
Human Services, Centers for Disease Control and Pre-
vention. https://wwwn.cdc.gov/Nchs/Data/Nhanes/
Public/2021/DataFiles/BMX_L.htm
Nettle, D. (2002). Height and reproductive success in
a cohort of British men. Human Nature, 13(4),
473–491. https://doi.org/10.1007/s12110-002-1004-7
Pawlowski, B. (2003). Variable preferences for sexual
dimorphism in height as a strategy for increasing the
pool of potential partners in humans. Proceedings of
the Royal Society of London. Series B: Biological
Sciences, 270(1516), 709–712. https://doi.org/10
.1098/rspb.2002.2294
Pawlowski, B., Dunbar, R. I., & Lipowicz, A. (2000).
Tall men have more reproductive success. Nature,
403(6766), 156–156. https://doi.org/10.1038/3500
3107
Pawlowski, B., & Jasienska, G. (2005). Women’s
preferences for sexual dimorphism in height
depend on menstrual cycle phase and expected
duration of relationship. Biological Psychology,
70(1), 38–43. https://doi.org/10.1016/j.biopsycho
.2005.02.002
Pawlowski, B., & Koziel, S. (2002). The impact of traits
offered in personal advertisements on response rates.
Evolution and Human Behavior, 23(2), 139–149.
https://doi.org/10.1016/S1090-5138(01)00092-7
Pazhoohi, F., Arantes, J., Kingstone, A., & Pinal, D.
(2020). Waist to hip ratio and breast size modulate
the processing of female body silhouettes: An EEG
study. Evolution and Human Behavior, 41(2),
150–169. https://doi.org/10.1016/j.evolhumbehav
.2020.01.001
Pazhoohi, F., Garza, R., & Kingstone, A. (2020). Effects
of breast size, intermammary cleft distance (cleavage)
and ptosis on perceived attractiveness, health, fertility,
and age: Do life history, self-perceived mate value,
and sexism attitude play a role. Adaptive Human
Behavior and Physiology, 6(1), 75–92. https://
doi.org/10.1007/s40750-020-00129-1
Pipitone, R. N., & Gallup, G. G. (2008). Women’s
voice attractiveness varies across the menstrual
cycle. Evolution and Human Behavior, 29(4),
268–274. https://doi.org/10.1016/j.evolhumbehav
.2008.02.001
Pisanski, K., Fernandez-Alonso, M., Díaz-Simón, N.,
Oleszkiewicz, A., Sardinas, A., Pellegrino, R., Este-
vez, N., Mora, E. C., Luckett, C. R., & Feinberg,
D. R. (2022). Assortative mate preferences for height
across short-term and long-term relationship contexts
in a cross-cultural sample. Frontiers in Psychology,
13, Article 937146. https://doi.org/10.3389/fpsyg.20
22.937146
Platek, S. M., & Singh, D. (2010). Optimal
waist-to-hip ratios in women activate neural reward
centers in men. PLoS ONE, 5(2), Article e9042.
https://doi.org/10.1371/journal.pone.0009042
Pokrywka, L., Čabrić, M., & Krakowiak, H. (2006).
Body mass index and waist-to-hip ratio are not
enough to characterize female attractiveness. Percep-
tion, 35(12), 1693–1697. https://doi.org/10.1068/
p5506
Prantl, L., & Gründl, M. (2011). Males prefer a larger
bust size in women than females themselves: An
experimental study on female bodily attractiveness
with varying weight, bust size, waist width, hip
width, and leg length independently. Aesthetic Plas-
tic Surgery, 35(5), 693–702. https://doi.org/10.100
7/s00266-011-9669-0
Prokop, P., Dylewski, Ł., Woźna, J. T., & Tryjanow-
ski, P. (2020). Cues of woman’s fertility predict
prices for sex with prostitutes. Current Psychology,
39(3), 919–926. https://doi.org/10.1007/s12144-018-
9807-9
Puts, D. A. (2010). Beauty and the beast: Mechanisms of
sexual selection in humans. Evolution and Human
Behavior, 31(3), 157–175. https://doi.org/10.1016/j
.evolhumbehav.2010.02.005
Ray, P. (2016). ‘Synthetik Love Lasts Forever’: Sex dolls
and the (post?) human condition. In D. Banerji &
M. Paranjape (Eds.), Critical posthumanism and plan-
etary futures (pp. 91–112). Springer. https://doi.org/
10.1007/978-81-322-3637-5_6
Rilling, J. K., Kaufman, T. L., Smith, E. O., Patel, R.,
& Worthman, C. M. (2009). Abdominal depth
and waist circumference as influential determinants
of human female attractiveness. Evolution and
Human Behavior, 30(1), 21–31. https://doi.org/10
.1016/j.evolhumbehav.2008.08.007
Rinker, B., Veneracion, M., & Walsh, C. P. (2008).
The effect of breastfeeding on breast aesthetics. Aes-
thetic Surgery Journal, 28(5), 534–537. https://
doi.org/10.1016/j.asj.2008.07.004
Röder, S., Fink, B., & Jones, B. C. (2013). Facial,
olfactory, and vocal cues to female reproductive value. Evolutionary Psychology, 11(2), 392–404.
https://doi.org/10.1177/147470491301100209
Rozmus-Wrzesinska, M., & Pawlowski, B. (2005).
Men’s ratings of female attractiveness are influenced
more by changes in female waist size compared with
changes in hip size. Biological Psychology, 68(3),
299–308. https://doi.org/10.1016/j.biopsycho.2004
.04.007
Ryan, M. (2018). A taste for the beautiful: The evolu-
tion of attraction. Preton University Press.
Saad, G. (2008). Advertised waist-to-hip ratios of
online female escorts: An evolutionary perspective.
International Journal of e-Collaboration, 4(3), 40–50.
https://doi.org/10.4018/jec.2008070103
Saad, G. (2011). The consuming instinct: What juicy
burgers, Ferraris, pornography, and gift giving
reveal about human nature. Prometheus Books.
Salmon, C., Fisher, M. L., & Burch, R. L. (2020). The
internet is for porn: Evolutionary perspectives on
online pornography. In L. Workman, W. Reader, &
J. H. Barkow (Eds.), The Cambridge handbook
of evolutionary perspectives on human behavior
(pp. 548–557). Cambridge University Press. https://
doi.org/10.1017/9781108131797.046
Salska, I., Frederick, D. A., Pawlowski, B., Reilly, A.
H., Laird, K. T., & Rudd, N. A. (2008). Conditional
mate preferences: Factors influencing preferences
for height. Personality and Individual Differences,
44(1), 203–215. https://doi.org/10.1016/j.paid.2007
.08.008
Schmitt, D. P., & Pilcher, J. J. (2004). Evaluating evi-
dence of psychological adaptation: How do we
know one when we see one? Psychological Science,
15(10), 643–649. https://doi.org/10.1111/j.0956-
7976.2004.00734.x
Sear, R., & Marlowe, F. W. (2009). How universal are
human mate choices? Size does not matter when
Hadza foragers are choosing a mate. Biology
Letters, 5(5), 606–609. https://doi.org/10.1098/rsbl
.2009.0342
Sforza, C., Grandi, G., Binelli, M., Dolci, C., De
Menezes, M., & Ferrario, V. F. (2010). Age-and sex-
related changes in three-dimensional lip morphology.
Forensic Science International, 200(1–3), Article
182.e1. https://doi.org/10.1016/j.forsciint.2010.04
.050
Sherry, D. S., & Marlowe, F. W. (2007). Anthropomet-
ric data indicate nutritional homogeneity in Hadza
foragers of Tanzania. American Journal of Human
Biology, 19(1), 107–118. https://doi.org/10.1002/
ajhb.20591
Silventoinen, K., Kaprio, J., Lahelma, E., Viken, R. J.,
& Rose, R. J. (2001). Sex differences ingenetic and
environmental factors contributing to body-height.
Twin Research and Human Genetics, 4(1), 25–29.
https://doi.org/10.1375/twin.4.1.25
Singh, D. (1993a). Adaptive significance of female
physical attractiveness: Role of waist-to-hip ratio.
Journal of Personality and Social Psychology,
65(2), 293–307. https://doi.org/10.1037/0022-3514
.65.2.293
Singh, D. (1993b). Body shape and women’s attrac-
tiveness: The critical role of waist-to-hip ratio.
Human Nature, 4(3), 297–321. https://doi.org/10
.1007/BF02692203
Singh, D. (1994). Ideal female body shape: Role of
body weight and waist-to-hip ratio. International
Journal of Eating Disorders, 16(3), 283–288.
https://doi.org/10.1002/1098-108X(199411)16:3,
283::AID-EAT2260160309.3.0.CO;2-Q
Singh, D., Dixson, B. J., Jessop, T. S., Morgan, B., &
Dixson, A. F. (2010). Cross-cultural consensus for
waist–hip ratio and women’s attractiveness. Evolu-
tion and Human Behavior, 31(3), 176–181. https://
doi.org/10.1016/j.evolhumbehav.2009.09.001
Singh, D., & Randall, P. K. (2007). Beauty is in the eye
of the plastic surgeon: Waist–hip ratio (WHR) and
women’s attractiveness. Personality and Individual
Differences, 43(2), 329–340. https://doi.org/10.101
6/j.paid.2006.12.003
Sorokowski, P., & Butovskaya, M. L. (2012). Height
preferences in humans may not be universal: Evi-
dence from the Datoga people of Tanzania. Body
Image, 9(4), 510–516. https://doi.org/10.1016/j
.bodyim.2012.07.002
Stulp, G., Buunk, A. P., & Pollet, T. V. (2013).
Women want taller men more than men want shorter
women. Personality and Individual Differences,
54(8), 877–883. https://doi.org/10.1016/j.paid.201
2.12.019
Stulp, G., Buunk, A. P., Verhulst, S., & Pollet, T. V.
(2015). Human height is positively related to inter-
personal dominance in dyadic interactions. PLoS
ONE, 10(2), Article e0117860. https://doi.org/10
.1371/journal.pone.0117860
Stulp, G., Pollet, T. V., Verhulst, S., & Buunk, A. P.
(2012). A curvilinear effect of height on reproduc-
tive success in human males. Behavioral Ecology
and Sociobiology, 66(3), 375–384. https://doi.org/
10.1007/s00265-011-1283-2
Stulp, G., Simons, M. J., Grasman, S., & Pollet, T. V.
(2017). Assortative mating for human height: A
meta-analysis. American Journal of Human Biology,
29(1), Article e22917. https://doi.org/10.1002/ajhb
.22917
Sugiyama, L. S. (2015). Physical attractiveness in
adaptationist perspective. In D. M. Buss (Ed.), The
handbook of evolutionary psychology (2nd ed., pp.
292–343). Wiley.
Swami, V., Antonakopoulos, N., Tovée, M. J., & Furn-
ham, A. (2006). A critical test of the waist-to-hip
ratio hypothesis of women’s physical attractiveness
in Britain and Greece. Sex Roles, 54(3–4), 201–211.
https://doi.org/10.1007/s11199-006-9338-3
Swami, V., Caprario, C., Tovée, M. J., & Furnham, A.
(2006). Female physical attractiveness in Britain and Japan: A cross-cultural study. European Jour-
nal of Personality, 20(1), 69–81. https://doi.org/10
.1002/per.568
Swami, V., Neto, F., Tovée, M. J., & Furnham, A.
(2007). Preferences for female body weight and
shape in three European countries. European Psy-
chologist, 12(3), 220–228. https://doi.org/10.1027/
1016-9040.12.3.220
Swami, V., & Tovée, M. J. (2007). Perceptions of
female body weight and shape among indigenous
and urban Europeans. Scandinavian Journal of Psy-
chology, 48(1), 43–50. https://doi.org/10.1111/j
.1467-9450.2006.00526.x
Swami, V., & Tovée, M. J. (2013a). Men’s oppressive
beliefs predict their breast size preferences in women.
Archives of Sexual Behavior, 42(7), 1199–1207.
https://doi.org/10.1007/s10508-013-0081-5
Swami, V., & Tovée, M. J. (2013b). Resource security
impacts men’s female breast size preferences. PLoS
ONE, 8(3), Article e57623. https://doi.org/10.1371/
journal.pone.0057623
Symons, D. (1979). The evolution of human sexuality.
Oxford University Press.
Symons, D. (1995). Beauty is in the adaptations of the
beholder: The evolutionary psychology of human
female sexual attractiveness. https://psycnet.apa.org/
record/1995-97782-005
Taylor, R. W., Grant, A. M., Williams, S. M., &
Goulding, A. (2010). Sex differences in regional
body fat distribution from pre- to postpuberty. Obe-
sity, 18(7), 1410–1416. https://doi.org/10.1038/oby
.2009.399
Tinbergen, N. (1951). The study of instinct. Clarendon
Press/Oxford University Press.
Tinbergen, N., & Perdeck, A. C. (1951). On the stim-
ulus situation releasing the begging response in the
newly hatched Herring Gull chick. Behaviour, 3(1),
1–39. https://doi.org/10.1163/156853951X00197
Tooby, J., & Cosmides, L. (1990). The past explains
the present: Emotional adaptations and the structure
of ancestral environments. Ethology and Sociobiol-
ogy, 11(4–5), 375–424. https://doi.org/10.1016/
0162-3095(90)90017-Z
Tyrrell, J., Jones, S. E., Beaumont, R., Astley, C. M.,
Lovell, R., Yaghootkar, H., Tuke, M., Ruth, K. S.,
Freathy, R. M., Hirschhorn, J. N., Wood, A. R., Mur-
ray, A., Weedon, M. N., & Frayling, T. M. (2016).
Height, body mass index, and socioeconomic status:
Mendelian randomisation study in UK Biobank.
BMJ, 352, Article i582. https://doi.org/10.1136/bmj
.i582
Valverde, S. (2012). The modern sex doll-owner:
A descriptive analysis (Publication No. 30511100)
[Doctoral dissertation, California Polytechnic State
University]. ProQuest Dissertations and Theses
Global.
Van Hooff, M. H. A., Voorhorst, F. J., Kaptein,
M. B. H., Hirasing, R. A., Koppenaal, C., &
Schoemaker, J. (2000). Insulin, androgen, and
gonadotropin concentrations, body mass index, and
waist-to-hip ratio in the first years after menarche in
girls with regular menstrual cycles, irregular men-
strual cycles, or oligomenorrhea. The Journal of
Clinical Endocrinology & Metabolism, 85(4),
1394–1400. https://doi.org/10.1210/jcem.85.4.6543
Vaz, M., Hunsberger, S., & Diffey, B. (2002). Predic-
tion equations for handgrip strength in healthy
Indian male and female subjects encompassing a
wide age range. Annals of Human Biology, 29(2),
131–141. https://doi.org/10.1080/0301446011005
8962
Voracek, M., Fisher, M. L., Rupp, B., Lucas, D., &
Fessler, D. M. T. (2007). Sex differences in relative
foot length and perceived attractiveness of female
feet: Relationships among anthropometry, phy-
sique, and preference ratings. Perceptual and
Motor Skills, 104(3_Suppl.), 1123–1138. https://
doi.org/10.2466/pms.104.4.1123-1138
Wardle, J., Haase, A. M., & Steptoe, A. (2006). Body
image and weight control in young adults: Interna-
tional comparisons in university students from 22
countries. International Journal of Obesity, 30(4),
644–651. https://doi.org/10.1038/sj.ijo.0803050
Weinstein, M., Wood, J. W., Stoto, M. A., & Green-
field, D. D. (1990). Components of age-specific
fecundability. Population Studies, 44(3), 447–467.
https://doi.org/10.1080/0032472031000144846
Wells, J. C. (2007). Sexual dimorphism of body com-
position. Best Practice & Research Clinical Endo-
crinology & Metabolism, 21(3), 415–430. https://
doi.org/10.1016/j.beem.2007.04.007
Wheatley, J. R., Apicella, C. A., Burriss, R. P., Cárde-
nas, R. A., Bailey, D. H., Welling, L. L., & Puts,
D. A. (2014). Women’s faces and voices are cues
to reproductive potential in industrial and forager
societies. Evolution and Human Behavior, 35(4),
264–271. https://doi.org/10.1016/j.evolhumbehav.20
14.02.006
Williams, G. C. (1975). Sex and evolution. Princeton
University Press.
Williams, J. K., McClain, L., Rosemurgy, A. S., &
Colorado, N. M. (1990). Evaluation of blunt abdom-
inal trauma in the third trimester of pregnancy:
Maternal and fetal considerations. Obstetrics &
Gynecology, 75(1), 33–37.
Winegard, B. M., Winegard, B., & Geary, D. C.
(2013). If you’ve got it, flaunt it: Humans flaunt
attractive partners to enhance their status and desir-
ability. PLoS ONE, 8(8), Article e72000. https://
doi.org/10.1371/journal.pone.0072000
Winegard, B. M., Winegard, B., Reynolds, T., Geary,
D. C., & Baumeister, R. F. (2017). One’s better half:
Romantic partners function as social signals. Evolu-
tionary Psychological Science, 3(4), 294–305.
https://doi.org/10.1007/s40806-017-0095-7
Yancey, G., & Emerson, M. O. (2016). Does height
matter? An examination of height preferences in
romantic coupling. Journal of Family Issues, 37(1),
53–73. https://doi.org/10.1177/0192513X13519256
Yu, D. W., & Shepard, G. H., Jr. (1998). Is beauty in the
eye of the beholder? Nature, 396(6709), 321–322.
https://doi.org/10.1038/24512
Zaadstra, B. M., Seidell, J. C., Van Noord, P. A., te
Velde, E. R., Habbema, J. D., Vrieswijk, B., &
Karbaat, J. (1993). Fat and female fecundity: Pros-
pective study of effect of body fat distribution on
conception rates. British Medical Journal, 306(6876),
484–487. https://doi.org/10.1136/bmj.306.6876.484
Zelazniewicz, A. M., & Pawlowski, B. (2011). Female
breast size attractiveness for men as a function of
sociosexual orientation (restricted vs. unrestricted).
Archives of Sexual Behavior, 40(6), 1129–1135.
https://doi.org/10.1007/s10508-011-9850-1"""

test15 = """Aarsland, D., & Cummings, J. L. (2002). Depression in Parkinson’s disease.
Acta Psychiatrica Scandinavica, 106(3), 161–162. https://doi.org/10
.1034/j.1600-0447.2002.2e009.x
Ascherio, A., & Schwarzschild, M. A. (2016). The epidemiology of
Parkinson’s disease: Risk factors and prevention. The Lancet Neurology,
15(12), 1257–1272. https://doi.org/10.1016/S1474-4422(16)30230-7
Berardelli, I., Belvisi, D., Nardella, A., Falcone, G., Lamis, D. A., Fabbrini, G.,
Berardelli, A., Girardi, P., & Pompili, M. (2019). Suicide in Parkinson’s
disease: A systematic review. CNS & Neurological Disorders-Drug
Targets, 18(6), 466–477. https://doi.org/10.2174/1871527318666190
703093345
Connor, K. M., & Davidson, J. R. (2003). Development of a new resilience
scale: The Connor-Davidson Resilience Scale (CD-RISC). Depression
and Anxiety, 18(2), 76–82. https://doi.org/10.1002/da.10113
Dehn, L. B., & Beblo, T. (2019). Verstimmt, verzerrt, vergesslich: Das
Zusammenwirken emotionaler und kognitiver Dysfunktionen bei
Depression [Depressed, biased, forgetful: The interaction of emotional and
cognitive dysfunctions in depression]. Neuropsychiatrie, 33(4), 123–130.
https://doi.org/10.1007/s40211-019-0307-4
Donaldson, S. I., van Zyl, L. E., & Donaldson, S. I. (2022). PERMA+4: A
framework for work-related wellbeing, performance and positive orga-
nizational psychology 2.0. Frontiers in Psychology, 12, Article 817244.
https://doi.org/10.3389/fpsyg.2021.817244
Elsworth, J. D. (2020). Parkinson’s disease treatment: Past, present, and
future. Journal of Neural Transmission, 127(5), 785–791. https://doi.org/
10.1007/s00702-020-02167-1
He, Y. Y., Chen, Z. M., Hu, J. P., Yao, M. Q., & Xia, D. (2024). Effect of
positive psychological intervention based on PERMA model on stigma,
resilience and happiness of epileptic patients. Nursing and Rehabilitation,
23(1), 43–47. https://doi.org/10.3969/j.issn.1671-9875.2024.01.009
Khaw, J., Subramaniam, P., Abd Aziz, N. A., Ali Raymond, A., Wan Zaidi,
W. A., & Ghazali, S. E. (2021). Current update on the clinical utility of
MMSE and MoCA for stroke patients in Asia: A systematic review.
International Journal of Environmental Research and Public Health,
18(17), Article 8962. https://doi.org/10.3390/ijerph18178962
Luo, W., Gui, X. H., Wang, B., Zhang, W. Y., Ouyang, Z. Y., Guo, Y.,
Zhang, B. R., & Ding, M. P. (2010). Validity and reliability testing of
the Chinese (mainland) version of the 39-item Parkinson’s Disease
Questionnaire (PDQ-39). Journal of Zhejiang University Science B,
11(7), 531–538. https://doi.org/10.1631/jzus.B0900380
Maier, W., Buller, R., Philipp, M., & Heuser, I. (1988). The Hamilton
Anxiety Scale: Reliability, validity and sensitivity to change in anxiety
and depressive disorders. Journal of Affective Disorders, 14(1), 61–68.
https://doi.org/10.1016/0165-0327(88)90072-9
Marsh, L. (2013). Depression and Parkinson’s disease: Current knowledge.
Current Neurology and Neuroscience Reports, 13(12), Article 409. https://
doi.org/10.1007/s11910-013-0409-5
Niu, H. Y., Ni, J. Y., Zhang, L., Xu, J. J., & Tan, M. J. (2016). Study on
reliability and validity of nursing satisfaction scale in clinical inpatients.
Clinical Nursing Research, 30(1C), 287–290. https://doi.org/10.3969/j
.issn.1009-6493.2016.03.009
Radhakrishnan, S., & Goyal, V. (2018). Parkinson’s disease: A review.
Neurology India, 66(Suppl 1), S26–S35. https://doi.org/10.4103/0028-
3886.226451
Rakel, R. E. (1999). Depression. Primary Care, 26(2), 211–224. https://
doi.org/10.1016/S0095-4543(08)70003-4
Rostagni, O. M., & Stutts, L. A. (2023). Gratitude, self-efficacy, and health-
related quality of life in individuals with Parkinson’s disease. Psychology,
Health & Medicine, 28(5), 1160–1166. https://doi.org/10.1080/13548506
.2022.2058032
Seligman, M. E., Steen, T. A., Park, N., & Peterson, C. (2005). Positive
psychology progress: Empirical validation of interventions. American
Psychologist, 60(5), 410–421. https://doi.org/10.1037/0003-066X.60
.5.410
Shaghaghi, F., Abedian, Z., Forouhar, M., Esmaily, H., & Eskandarnia, E.
(2019). Effect of positive psychology interventions on psychological well-
being of midwives: A randomized clinical trial. Journal of Education and
Health Promotion, 8(1), Article 160. https://doi.org/10.4103/jehp.jehp_
17_19
Sin, N. L., & Lyubomirsky, S. (2009). Enhancing well-being and alleviating
depressive symptoms with positive psychology interventions: A practice-
friendly meta-analysis. Journal of Clinical Psychology, 65(5), 467–487.
https://doi.org/10.1002/jclp.20593
Starkstein, S. E., Brockman, S., & Hayhow, B. D. (2012). Psychiatric
syndromes in Parkinson’s disease. Current Opinion in Psychiatry, 25(6),
468–472. https://doi.org/10.1097/YCO.0b013e3283577ed1
Tysnes, O. B., & Storstein, A. (2017). Epidemiology of Parkinson’s disease.
Journal of Neural Transmission, 124(8), 901–905. https://doi.org/10
.1007/s00702-017-1686-y
Vescovelli, F., Minotti, S., & Ruini, C. (2021). Exploring post-traumatic
growth in Parkinson’s disease: A mixed method study. Journal of Clinical Psychology in Medical Settings, 28(2), 267–278. https://doi.org/10.1007/
s10880-020-09713-9
Wang, B., Xu, J., & Tang, X. M. (2009). Study on reliability and validity of
unified Parkinson’s disease rating scale. Shandong Yiyao, 49(28), 88–89.
https://doi.org/10.3969/j.issn.1002-266X.2009.28.045
Watson, D., Clark, L. A., & Tellegen, A. (1988). Development and validation
of brief measures of positive and negative affect: The PANAS scales.
Journal of Personality and Social Psychology, 54(6), 1063–1070. https://
doi.org/10.1037/0022-3514.54.6.1063
Yang, J., Wang, Q., Gu, Y. F., & Tang, Q. Q. (2023). Research progress of
PERMA model positive psychological intervention in nursing field.
Modern Healthcare, 23(14), 1045–1047. https://doi.org/10.3969/j.issn
.1671-0223(s).2023.14.002
Yao, Y., Wang, C. J., Yin, S. Y., Xu, G. Z., Cheng, Y. F., Huang, Q. Q., &
Jin, Y. (2024). Effects of positive psychology intervention based on the
PERMA model on psychological status and quality of life in patients with
Parkinson’s disease. Heliyon, 10(20), Article e36902. https://doi.org/10
.1016/j.heliyon.2024.e36902
Zimmerman, M., Martinez, J. H., Young, D., Chelminski, I., & Dalrymple,
K. (2013). Severity classification on the Hamilton depression rating scale.
Journal of Affective Disorders, 150(2), 384–388. https://doi.org/10.1016/j
.jad.2013.04.028
Zitser, J., Allen, I. E., Falgàs, N., Le, M. M., Neylan, T. C., Kramer, J. H., &
Walsh, C. M. (2022). Pittsburgh Sleep Quality Index (PSQI) responses are
modulated by total sleep time and wake after sleep onset in healthy older
adults. PLOS ONE, 17(6), Article e0270095. https://doi.org/10.1371/jou
rnal.pone.0270095"""


test16 = """Aiello, L. C., & Wheeler, P. (1995). The expensive-
tissue hypothesis: The brain and the digestive sys-
tem in human and primate evolution. Current Anthropology, 36(2), 199–221. https://doi.org/10
.1086/204350
Antón, S. C., Potts, R., & Aiello, L. C. (2014). Human
evolution: Evolution of early Homo—An integrated
biological perspective. Science, 345(6192), Article
1236828. https://doi.org/10.1126/science.1236828
Aoki, K. (2015). Modeling abrupt cultural regime
shifts during the Palaeolithic and Stone Age. Theo-
retical Population Biology, 100, 6–12. https://
doi.org/10.1016/j.tpb.2014.11.006
Arthur, W. B. (2009). The nature of technology: What
it is and how it evolves. Free Press.
Aunger, R., & Greenland, K. (2024). Testing the
human superorganism approach to morality. Culture
and Evolution, 20(1), 19–28. https://doi.org/10
.1556/2055.2022.00007
Bak, P., Tang, C., & Wiesenfeld, K. (1987). Self-
organized criticality: An explanation of the 1/f
noise. Physical Review Letters, 59(4), 381–384.
https://doi.org/10.1103/PhysRevLett.59.381
Barton, R. A. (2012). Embodied cognitive evolution
and the cerebellum. Philosophical Transactions of
the Royal Society B, 367(1599), 2097–2107.
https://doi.org/10.1098/rstb.2012.0112
Baumard, N. (2016). The origins of fairness: How evo-
lution explains our moral nature. Oxford University
Press.
Bluet, A., Reynaud, E., Federico, G., Bryche, C.,
Lesourd, M., Fournel, A., Lamberton, F., Ibarrola,
D., Rossetti, Y., & Osiurak, F. (2024). The
technical-reasoning network is recruited when peo-
ple observe others make or teach how to make tools:
An fMRI study. bioRxiv. https://doi.org/10.1101/
2024.03.21.586121
Bourke, A. F. G. (2011). Principles of social evolution
(Oxford series in ecology and evolution). Oxford
University Press. https://doi.org/10.1093/acprof:
oso/9780199231157.001.0001
Boyd, R., & Richerson, P. J. (1985). Culture and the
evolutionary process. University of Chicago Press.
Boyd, R., & Richerson, P. J. (2005). The origin and
evolution of cultures. Oxford University Press.
Boyd, R., Richerson, P. J., & Henrich, J. (2011). The
cultural niche: Why social learning is essential for
human adaptation. Proceedings of the National
Academy of Sciences of the United States of Amer-
ica, 108(supplement_2), 10918–10925. https://
doi.org/10.1073/pnas.1100290108
Brinkmann, L., Baumann, F., Bonnefon, J. F., Derex,
M., Müller, T. F., Nussberger, A. M., Czaplicka,
A., Acerbi, A., Griffiths, T. L., Henrich, J., Leibo,
J. Z., McElreath, R., Oudeyer, P.-Y., Stray, J., &
Rahwan, I. (2023). Machine culture. Nature
Human Behaviour, 7(11), 1855–1868. https://
doi.org/10.1038/s41562-023-01742-2
Brooks, R. C. (2024). How might artificial intelligence
influence human evolution? The Quarterly Review of
Biology, 99(4), 201–229. https://doi.org/10.1086/
733290
Brown, R. L. (2014). What evolvability really is. The
British Journal for the Philosophy of Science,
65(3), 549–572. https://doi.org/10.1093/bjps/axt014
Burt, A., & Trivers, R. (2006). Genes in conflict: The
biology of selfish genetic elements. Harvard Univer-
sity Press. https://ebookcentral.proquest.com/lib/
bu/detail.action?docID=3300059
Buskell, A., Enquist, M., & Jansson, F. (2019). A sys-
tems approach to cultural evolution. Palgrave Com-
munications, 5(1), Article 131. https://doi.org/10
.1057/s41599-019-0343-5
Carr, N. (2010). The shallows: How the internet is
changing the way we think, read, and remember.
Atlantic Books.
Castells, M. (2000). The Rise of the Network Society:
The age of information—Economy, society and cul-
ture (Vol. 1). Blackwell Publishers.
Cavalli-Sforza, L. L., & Feldman, M. W. (1981). Cul-
tural transmission and evolution: A quantitative
approach. Princeton University Press.
Chaisson, E. J. (2001). Cosmic evolution: The rise of
complexity in nature. Harvard University Press.
Chaisson, E. J. (2011). Energy rate density as a com-
plexity metric and evolutionary driver. Complexity,
16(3), 27–40. https://doi.org/10.1002/cplx.20323
Chrisley, R. (2003). Embodied artificial intelligence.
Artificial Intelligence, 149(1), 131–150. https://
doi.org/10.1016/S0004-3702(03)00055-9
Christakis, N. A., & Fowler, J. H. (2009). Connected: The
surprising power of our social networks and how they
shape our lives (1st ed.). Little, Brown and Co.
Christian, D. (2004). Maps of time: An introduction
to big history (California World History Library)
(Vol. 2). University of California Press. https://
www.publishersweekly.com/9780520235007
Chudek, M., Zhao, W., & Henrich, J. (2013). Culture-
gene coevolution, large-scale cooperation, and the
shaping of human social psychology. In K. Sterelny,
R. Joyce, B. Calcott, & B. Fraser (Eds.), Cooperation
and its evolution (pp. 425–457). The MIT Press.
Cisco. (2019). Cisco Visual Networking Index: Fore-
cast and trends, 2017–2022. https://twiki.cern.ch/
twiki/pub/HEPIX/TechwatchNetwork/HtwNetwork
Documents/white-paper-c11-741490.pdf
Clayton, R. B., Leshner, G., & Almond, A. (2015).
The extended iSelf: The impact of iPhone separa-
tion on cognition, emotion, and physiology. Jour-
nal of Computer-Mediated Communication, 20(2),
119–135. https://doi.org/10.1111/jcc4.12109
Cortês, M., Kauffman, S. A., Liddle, A. R., & Smolin,
L. (2024). The TAP equation: evaluating combina-
torial innovation in Biocosmology. https://arxiv
.org/abs/2204.14115.
Crespi, B., & Badcock, C. (2008). Psychosis and
autism as diametrical disorders of the social brain. Behavioral and Brain Sciences, 31(3), 241–261.
https://doi.org/10.1017/S0140525X08004214
Csibra, G., & Gergely, G. (2009). Natural pedagogy.
Trends in Cognitive Sciences, 13(4), 148–153.
https://doi.org/10.1016/j.tics.2009.01.005
Currie, T. E., Turchin, P., Bednar, J., Richerson, P. J.,
Schwesinger, G., Steinmo, S., & Wacziarg, R.
(2016). Evolution of institutions and organizations.
In D. S. Wilson & A. Kirman (Eds.), Complexity
and evolution: Toward a new synthesis for econom-
ics (Vol. 19, pp. 201–236). MIT Press.
Davison, D. R., & Michod, R. E. (2023). Steps to indi-
viduality in biology and culture. Philosophical
Transactions of the Royal Society B, 378(1872),
Article 20210407. https://doi.org/10.1098/rstb.20
21.0407
Deacon, T. W. (2011). Incomplete nature: How mind
emerged from matter. W. W. Norton & Company.
Deacon, T. W. (2021). How molecules became signs.
Biosemiotics, 14(3), 537–559. https://doi.org/10
.1007/s12304-021-09453-9
Dean, L. G., Kendal, R. L., Schapiro, S. J., Thierry, B.,
& Laland, K. N. (2012). Identification of the social
and cognitive processes underlying human cumula-
tive culture. Science, 335(6072), 1114–1118.
https://doi.org/10.1126/science.1213969
Derex, M., & Boyd, R. (2020). Technical reasoning
alone does not take humans this far. Behavioral
and Brain Sciences, 43, Article e612. https://
doi.org/10.1017/S0140525X20000266
de Vries, A. (2023). The growing energy footprint of
artificial intelligence. Joule, 7(10), 2191–2194.
https://doi.org/10.1016/j.joule.2023.09.004
Doan, R. N., Bae, B. I., Cubelos, B., Chang, C., Hos-
sain, A. A., Al-Saad, S., Mukaddes, N. M., Oner,
O., Al-Saffar, M., Balkhy, S., Gascon, G. G.,
Homozygosity Mapping Consortium for Autism,
Nieto, M., & Walsh, C. A. (2016). Mutations in
human accelerated regions disrupt cognition and
social behavior. Cell, 167(2), 341–354.e12. https://
doi.org/10.1016/j.cell.2016.08.071
Donald, M. (1991). Origins of the modern mind: Three
stages in the evolution of culture and cognition.
Harvard University Press.
Donald, M. (1993). Human cognitive evolution: What
we were, what we are becoming. Social Research,
60(1), 143–170. https://doi.org/10.2307/jj.18011432.6
Donald, M. (2001). A mind so rare: The evolution of
human consciousness (1st ed.). W.W. Norton.
Donald, M. (2018). Self-programming and the self-
domestication of the human species: Are we
approaching a fourth transition? In J. S. Jensen,
G. Ingvild Sælid, A. K. Petersen, L. H. Martin, &
J. Sørensen (Eds.), Evolution, cognition, and the
history of religion: A new synthesis (Vol. 13, pp.
159–174). BRILL.
Dunsworth, H. M. (2016). Thank your intelligent
mother for your big brain. Proceedings of the
National Academy of Sciences of the United States
of America, 113(25), 6816–6818. https://doi.org/
10.1073/pnas.1606596113
Epstein, S., Pacini, R., Denes-Raj, V., & Heier, H.
(1996). Individual differences in intuitive–experien-
tial and analytical–rational thinking styles. Journal
of Personality and Social Psychology, 71(2), 390–
405. https://doi.org/10.1037/0022-3514.71.2.390
Friston, K. (2009). The free-energy principle: A rough
guide to the brain? Trends in Cognitive Sciences,
13(7), 293–301. https://doi.org/10.1016/j.tics.2009
.04.005
Friston, K. (2018). Am I self-conscious? (Or does self-
organization entail self-consciousness?). Frontiers
in Psychology, 9, Article 579. https://doi.org/10
.3389/fpsyg.2018.00579
Froese, T., & Ziemke, T. (2009). Enactive artificial
intelligence: Investigating the systemic organization
of life and mind. Artificial Intelligence, 173(3-4),
466–500. https://doi.org/10.1016/j.artint.2008.12
.001
Gillings, M. R., Hilbert, M., & Kemp, D. J. (2016).
Information in the biosphere: Biological and digital
worlds. Trends in Ecology and Evolution, 31(3),
180–189. https://doi.org/10.1016/j.tree.2015.12.013
Goldenberg, G., & Spatt, J. (2009). The neural basis of
tool use. Brain, 132(6), 1645–1655. https://doi.org/
10.1093/brain/awp080
Gould, S. J., & Eldredge, N. (1972). Punctuated equi-
libria: The tempo and mode of evolution reconsid-
ered. Paleobiology, 3(2), 115–151. https://doi.org/
10.1017/S0094837300005224
Greengard, S. (2021). The Internet of Things. The MIT
Press.
Grinschgl, S., & Neubauer, A. C. (2022). Supporting
cognition with modern technology: Distributed cog-
nition today and in an AI-enhanced future. Frontiers
in Artificial Intelligence, 5, Article 908261. https://
doi.org/10.3389/frai.2022.908261
Guardiola-Ripoll, M., & Fatjó-Vilas, M. (2023). A
systematic review of the human accelerated regions
in schizophrenia and related disorders: Where the
evolutionary and neurodevelopmental hypotheses
converge. International Journal of Molecular Sci-
ences, 24(4), Article 3597. https://doi.org/10.3390/
ijms24043597
Gustafson, L. (2020). Big history and political science:
Science, the deep past, and the political. In C. Ben-
jamin, E. Quaedackers, & D. Baker (Eds.), The
Routledge companion to big history (pp. 180–201).
Routledge.
Haefner, K. (Ed.). (2012). Evolution of information
processing systems: An interdisciplinary approach
for a new understanding of nature and society.
Springer. https://doi.org/10.1007/978-3-642-22
913-9
Hamblin, S. (2013). On the practical usage of genetic
algorithms in ecology and evolution. Methods in Ecology and Evolution, 4(2), 184–194. https://
doi.org/10.1111/2041-210X.12000
Henrich, J. (2015). The secret of our success: How cul-
ture is driving human evolution, domesticating our
species, and making us smarter. Princeton Univer-
sity Press. https://doi.org/10.1515/9781400873296
Henrich, J., & McElreath, R. (2003). The evolution
of cultural evolution. Evolutionary Anthropology,
12(3), 123–135. https://doi.org/10.1002/evan.10110
Heyes, C. (2012). New thinking: The evolution
of human cognition. Philosophical Transactions of
the Royal Society of London. Series B. Biological
Sciences, 367(1599), 2091–2096. https://doi.org/
10.1098/rstb.2012.0111
Heylighen, F. (1995). (Meta)systems as constraints on
variation. World Futures: The Journal of General
Evolution, 45(1-4), 59–85. https://doi.org/10.1080/
02604027.1995.9972554
Heylighen, F. (1999). The growth of structural and func-
tional complexity during evolution. In F. Heylighen,
J. Bollen, & A. Riegler (Eds.), The evolution of com-
plexity (pp. 17–44). Kluwer Academic.
Heylighen, F. (2001). Bootstrapping knowledge repre-
sentations: From entailment meshes via semantic
nets to learning webs. Kybernetes, 30(5/6), 691–
725. https://doi.org/10.1108/EUM0000000005695
Heylighen, F. (2007). The global superorganism:
An evolutionary-cybernetic model of the emerging
network society. Social Evolution & History, 6(1),
58–119. https://pcp.vub.ac.be/papers/Superorganism
.pdf
Heylighen, F. (2015). Return to Eden? Promises and
perils on the road to a global superintelligence. In
B. Goertzel & T. Goertzel (Eds.), The end of the
beginning: Life, society and economy on the brink
of the singularity (pp. 35–53). Humanity+ Press.
Heylighen, F., & Campbell, D. T. (1995). Selection of
organisation at the social level. World Futures,
45(1-4), 181–212. https://doi.org/10.1080/026040
27.1995.9972560
Hofkirchner, W. (2007). A critical social systems view
of the Internet. Philosophy of the Social Sciences,
37(4), 471–500. https://doi.org/10.1177/00483931
07307664
Holland, J. H. (1992). Adaptation in natural and artifi-
cial systems: An introductory analysis with applica-
tions to biology, control, and artificial intelligence.
MIT Press.
Jablonka, E., & Lamb, M. J. (2006). The evolution of
information in the major transitions. Journal of The-
oretical Biology, 239(2), 236–246. https://doi.org/
10.1016/j.jtbi.2005.08.038
Jacob, M. S. (2023). Toward a Bio-Organon: A model
of interdependence between energy, information
and knowledge in living systems. BioSystems, 230,
Article 104939. https://doi.org/10.1016/j.biosystems
.2023.104939
Kaganer, E., Carmel, E., Hirschheim, R., & Olsen, T.
(2013). Managing the human cloud. MIT Sloan
Management Review, 54(2), 23–32. https://sloan
review.mit.edu/article/managing-the-human-cloud/
Kauffman, S. A. (1993). The origins of order: Self-
organization and selection in evolution. Oxford
University Press.
Kendal, R. L., Boogert, N. J., Rendell, L., Laland, K.
N., Webster, M., & Jones, P. L. (2018). Social learn-
ing strategies: Bridge-building between fields.
Trends in Cognitive Sciences, 22(7), 651–665.
https://doi.org/10.1016/j.tics.2018.04.003
Kesebir, S. (2012). The superorganism account of
human sociality: How and when human groups are
like beehives. Personality and Social Psychology
Review, 16(3), 233–261. https://doi.org/10.1177/
1088868311430834
Kirschner, M., & Gerhart, J. (2005). The plausibility of
life: Resolving Darwin’s dilemma. Yale University
Press.
Lane, N., & Martin, W. F. (2010). The energetics of
genome complexity. Nature, 467(7318), 929–934.
https://doi.org/10.1038/nature09486
Lane, N., Martin, W. F., Raven, J. A., & Allen, J. F.
(2013). Energy, genes and evolution: Introduction
to an evolutionary synthesis. Philosophical Trans-
actions of the Royal Society B, 368(1622), Article
20120253. https://doi.org/10.1098/rstb.2012.0253
Lindblom, J., & Ziemke, T. (2003). Social situatedness
of natural and artificial intelligence: Vygotsky and
beyond. Adaptive Behavior, 11(2), 79–96. https://
doi.org/10.1177/10597123030112002
Lingam, M., Frank, A., & Balbi, A. (2023). Planetary
scale information transmission in the biosphere and
technosphere: Limits and evolution. Life (Basel,
Switzerland), 13(9), Article 1850. https://doi.org/
10.3390/life13091850
Lior, Y. (2015). Kabbalah and neo-Confucianism: A
comparative morphology of medieval movements
[PhD dissertation, Boston University]. https://hdl
.handle.net/2144/15428
Lior, Y. (2022). Major transitions in cultural evolution:
A dynamic systems approach. In Y. Lior & J. Lane
(Eds.), The Routledge handbook of evolutionary
approaches to religion (pp. 426–428). Routledge.
Liu, J. H., & Macdonald, M. (2016). Towards a psy-
chology of global consciousness through an ethical
conception of self in society. Journal for the Theory
of Social Behaviour, 46(3), 310–334. https://
doi.org/10.1111/jtsb.12101
Lotka, A. J. (1925). Elements of physical biology.
Williams and Wilkins.
Lotman, Y. M. (2001). Universe of the mind: A semi-
otic theory of culture. I.B. Tauris.
Lotman, Y. M., & Clark, W. (2005). On the semio-
sphere. Sign Systems Studies, 33(1), 205–229.
https://doi.org/10.12697/sss.2005.33.1.09
Luke, L., Clare, I. C. H., Ring, H., Redley, M., &
Watson, P. (2012). Decision-making difficulties
experienced by adults with autism spectrum condi-
tions. Autism, 16(6), 612–621. https://doi.org/10
.1177/1362361311415876
Luppi, A. I., Mediano, P. A. M., Rosas, F. E., Holland,
N., Fryer, T. D., O’Brien, J. T., Rowe, J. B., Menon,
D. K., Bor, D., & Stamatakis, E. A. (2022). A syn-
ergistic core for human brain evolution and cogni-
tion. Nature Neuroscience, 25(6), 771–782.
https://doi.org/10.1038/s41593-022-01070-0
Magnani, L. (2021). Cognitive Niche construction and
extragenetic information: A sense of purposefulness
in evolution. Journal for General Philosophy of
Science, 52(2), 263–276. https://doi.org/10.1007/
s10838-019-09494-2
Martin, M., Beume, L., Kümmere, D., Schmidt,
C. S. M., Bormann, T., Dressing, A., Kaller, C. P.,
Kümmerer, D., Ludwig, V. M., Mader, I., Martin,
M., Rijntjes, M., Schmidt, C. S., Umarova, R. M.,
& Weiller, C. (2016). Differential roles of ventral
and dorsal streams for conceptual and production-
related components of tool use in acute stroke
patients. Cerebral Cortex, 26(9), 3754–3771.
https://doi.org/10.1093/cercor/bhv179
Maslej, N., Fattorini, L., Perrault, R., Parli, V., Reuel,
A., Brynjolfsson, E., Etchemendy, J., Ligett, K.,
Lyons, T., Manyika, J., Niebles, J. C., Shoham, Y.,
Wald, R., & Clark, J. (2024). The AI Index 2024
Annual Report. AI Index Steering Committee, Insti-
tute for Human-Centered AI, Stanford University.
Maturana, H. R., & Varela, F. J. (1972). Autopoiesis
and cognition: The realization of the living.
D. Reidel Pub. Co.
Maturana, H. R., & Varela, F. J. (1992). The tree of
knowledge: The biological roots of human under-
standing. Shambhala.
McCloskey, D. (2004). Review of the Cambridge eco-
nomic history of modern Britain. In R. Floud &
P. Johnson (Eds.), Times higher education supple-
ment (Vol. 15). https://deirdremccloskey.org/articles/
floud.php
McKinney, M. L., & McNamara, K. J. (2013). Hetero-
chrony: The evolution of ontogeny. Springer Sci-
ence & Business Media.
Michod, R. E. (1999). Darwinian dynamics: Evolu-
tionary transitions in fitness and individuality.
Princeton University Press.
Miller, J. (1978). Living systems. McGraw-Hill.
Miller, J. L., & Miller, J. G. (1992). Greater than the
sum of its parts. I. Subsystems which process both
matter-energy and information. Behavioral Science,
37(1), 1–9. https://doi.org/10.1002/bs.3830370102
Miller, R. C., Little, G., Bernstein, M., Bigham, J. P.,
Chilton, L. B., Goldman, M., Horton, J. J., &
Nayak, R. (2010). Heads in the cloud. XRDS: Cross-
roads, 17(2), 27–31. https://doi.org/10.1145/18690
86.1869095
Mitteroecker, P., & Fischer, B. (2016). Adult pelvic
shape change is an evolutionary side effect. Pro-
ceedings of the National Academy of Sciences,
113(26), Article E3596. https://doi.org/10.1073/
pnas.1607066113
Moore, J. D. (2009). Visions of culture: An intro-
duction to anthropological theories of theorists
(3rd ed.). AltaMira Press.
Muthukrishna, M. (2023). A theory of everyone: The
new science of who we are, how we got here, and
where we’re going. The MIT Press.
Navarrete, A., van Schaik, C. P., & Isler, K. (2011).
Energetics and the evolution of human brain size.
Nature, 480(7375), 91–93. https://doi.org/10.1038/
nature10629
Noda-Garcia, L., Liebermeister, W., Tawfik, D. S., &
Kornberg, R. (2018). Metabolite-enzyme coevolu-
tion: From single enzymes to metabolic pathways
and networks. Annual Review of Biochemistry,
87(1), 187–216. https://doi.org/10.1146/annurev-
biochem-062917-012023
Norenzayan, A., Shariff, A. F., Gervais, W. M., Wil-
lard, A. K., McNamara, R. A., Slingerland, E., &
Henrich, J. (2016). The cultural evolution of proso-
cial religions. The Behavioral and Brain Sciences,
39, Article e1. https://doi.org/10.1017/S0140525
X14001356
Omohundro, S. M. (2007). The nature of self-improving
artificial intelligence. Singularity Summit 2008.
https://steveomohundro.com/wpcontent/uploads/
2009/12/nature_of_self_improving_ai.pdf
Omohundro, S. M. (2008). The basic AI drives. In
P. Wang, B. Goertzel, & S. Franklin (Eds.), Pro-
ceedings of the 2008 conference on artificial gene-
ral intelligence (pp. 483–492). IOS Press.
Osiurak, F., Lasserre, S., Arbanti, J., Brogniart, J.,
Bluet, A., Navarro, J., & Reynaud, E. (2021). Tech-
nical reasoning is important for cumulative techno-
logical culture. Nature Human Behaviour, 5(12),
1643–1651. https://doi.org/10.1038/s41562-021-
01159-9
Osiurak, F., Lesourd, M., Navarro, J., & Reynaud, E.
(2020). Technition: When tools come out of the
closet. Perspectives on Psychological Science,
15(4), 880–897. https://doi.org/10.1177/1745691
620902145
Osiurak, F., & Reynaud, E. (2020). The elephant in the
room: What matters cognitively in cumulative tech-
nological culture. Behavioral and Brain Sciences,
43, Article e156. https://doi.org/10.1017/S01405
25X19003236
Ostwald, W. (1907). Energetische grundlagen der kul-
turwissenschaft [The energetics foundations of cul-
tural studies] (Vol. 16). W. Klinkhardt.
Pacini, R., & Epstein, S. (1999). The relation of ratio-
nal and experiential information processing styles to
personality, basic beliefs, and the ratio-bias phe-
nomenon. Journal of Personality and Social Psychology, 76(6), 972–987. https://doi.org/10.10
37/0022-3514.76.6.972
Pol, A. T. (1990). Life: Energy-information relation-
ship within material systems—I. General outline
of the concept. Computers and Mathematics with
Applications, 20(4-6), 269–285. https://doi.org/10
.1016/0898-1221(90)90333-F
Pollard, K. S. (2009). What makes us human? Scien-
tific American, 300(5), 44–49. https://doi.org/10
.1038/scientificamerican0509-44
Pollard, K. S., Salama, S. R., Lambert, N., Lambot,
M.-A., Coppens, S., Pedersen, J. S., Katzman, S.,
King, B., Onodera, C., Siepel, A., Kern, A. D.,
Dehay, C., Igel, H., Ares, M., Jr., Vanderhaeghen, P.,
& Haussler, D. (2006). An RNA gene expressed dur-
ing cortical development evolved rapidly in humans.
Nature, 443(7108), 167–172. https://doi.org/10.1038/
nature05113
Prigogine, I. (1955). Introduction to thermodynamics of
irreversible processes. Charles C Thomas Publisher.
Prigogine, I., & Stengers, I. (1984). Order out of chaos:
Man’s new dialogue with nature. Heinemann.
Rainey, P. B. (2023). Major evolutionary transitions in
individuality between humans and AI. Philosophical
Transactions of the Royal Society B, 378(1872),
Article 20210408. https://doi.org/10.1098/rstb.2021
.0408
Renom, M. A., Caramiaux, B., & Beaudouin-Lafon,
M. (2022, April 29–May 5). Exploring technical
reasoning in digital tool use. CHI conference on
human factors in computing systems (CHI ‘22),
New Orleans, LA, United States. ACM (17 pp.).
https://doi.org/10.1145/3491102.3501877
Richerson, P. J., & Boyd, R. (2005). Not by genes
alone:?How culture transformed human evolution.
University of Chicago Press.
Richerson, P. J., Boyd, R., & Efferson, C. (2024).
Agentic processes in cultural evolution: Relevance
to Anthropocene sustainability. Philosophical
Transactions of the Royal Society B, 379(1893),
Article 20220252. https://doi.org/10.1098/rstb.202
2.0252
Richerson, P. J., Boyd, R., & Henrich, J. (2010). Gene-
culture coevolution in the age of genomics. Pro-
ceedings of the National Academy of Sciences,
107(supplement_2), 8985–8992. https://doi.org/10
.1073/pnas.0914631107
Rightmire, G. P. (2004). Brain size and encephaliza-
tion in early to mid-Pleistocene Homo. American
Journal of Physical Anthropology, 124(2), 109–
123. https://doi.org/10.1002/ajpa.10346
Risko, E. F., & Gilbert, S. J. (2016). Cognitive offload-
ing. Trends in Cognitive Sciences, 20(9), 676–688.
https://doi.org/10.1016/j.tics.2016.07.002
Rosen, R. (2012). Anticipatory systems. In R. Rosen
(Ed.), Anticipatory systems: Philosophical, mathe-
matical, and methodological foundations (pp.
313–370). Springer.
Salazar-López, E., Schwaiger, B. J., & Hermsdörfer, J.
(2016). Lesion correlates of impairments in actual
tool use following unilateral brain damage. Neuro-
psychologia, 84, 167–180. https://doi.org/10.1016/
j.neuropsychologia.2016.02.007
Schrödinger, E. (1944). What is life? The physical
aspect of the living cell. Oxford University Press.
Shaffer, D. W., & Kaput, J. J. (1998). Mathematics and
virtual culture: An evolutionary perspective on tech-
nology and mathematics education. Educational
Studies in Mathematics, 37(2), 97–119. https://
doi.org/10.1023/A:1003590914788
Sherwin, W. B. (2024). Pan-Evo: The evolution of
information and biology’s part in this. Biology
(Basel, Switzerland), 13(7), Article 507. https://
doi.org/10.3390/biology13070507
Shilton, D., Breski, M., Dor, D., & Jablonka, E.
(2020). Human social evolution: Self-domestication
or self-control? Frontiers in Psychology, 11, Article
134. https://doi.org/10.3389/fpsyg.2020.00134
Slingerland, E., Henrich, J., & Norenzayan, A.
(2013). The evolution of prosocial religions. In
P. J. Richerson & M. H. Christiansen (Eds.),
Cultural evolution: Society, technology, language,
and religion (Vol. 12, 1st ed., pp. 335–348). The
MIT Press.
Smaldino, P. E. (2014). The cultural evolution of
emergent group-level traits. Behavioral and Brain
Sciences, 37(3), 243–254. https://doi.org/10.1017/
S0140525X13001544
Smart, A., & Smart, J. (2017). Posthumanism: Anthro-
pological insights. University of Toronto Press.
Smart, P. R. (2018). Human-extended machine cogni-
tion. Cognitive Systems Research, 49, 9–23. https://
doi.org/10.1016/j.cogsys.2017.11.001
Soddy, F. (1912). Matter and energy (Home Univer-
sity Series). Oxford University.
Staley, D. J. (2014). Brain, mind and internet: A deep
history and future. Palgrave Macmillan.
Stearns, S. C. (2007). Are we stalled part way through
a major evolutionary transition from individual to
group? Evolution, 61(10), 2275–2280. https://
doi.org/10.1111/j.1558-5646.2007.00202.x
Sterelny, K. (2012). Language, gesture, skill: The
coevolutionary foundations of language. Philosophical
Transactions of the Royal Society B, 367(1599),
2141–2151. https://doi.org/10.1098/rstb.2012.0116
Stock, G. (1993). Metaman: The merging of humans
and machines into a global superorganism. Simon
& Schuster.
Stonier, T. (1992). Beyond information: The natural
history of intelligence. Springer-Verlag.
Stothart, C., Mitchum, A., & Yehnert, C. J. (2015).
The attentional cost of receiving a cell phone
notification. Experimental Psychology: Human Per-
ception and Performance, 41(4), 893–897. https://
doi.org/10.1037/xhp0000100
Szathmáry, E. (2015). Toward major evolutionary
transitions theory 2.0. Proceedings of the National
Academy of Sciences, 112(33), 10104–10111.
https://doi.org/10.1073/pnas.1421398112
Szathmáry, E., & Smith, J. (1995). The major evolu-
tionary transitions. Nature, 374(6519), 227–232.
https://doi.org/10.1038/374227a0
Taylor, C. (1989). Sources of the self: the making of
the modern identity. Harvard University Press.
Taylor, C. (2007). A secular age. Harvard University
Press.
Taylor, H., Fernandes, B., & Wraight, S. (2022). The
evolution of complementary cognition: Humans
cooperatively adapt and evolve through a system
of collective cognitive search. Cambridge Archaeo-
logical Journal, 32(1), 61–77. https://doi.org/10
.1017/S0959774321000329
Torres-Sosa, C., Huang, S., & Aldana, M. (2012). Crit-
icality is an emergent property of genetic networks
that exhibit evolvability. PLoS Computational Biol-
ogy, 8(9), Article e1002669. https://doi.org/10
.1371/journal.pcbi.1002669
Toussaint, O., & Schneider, E. D. (1998). The thermo-
dynamics and evolution of complexity in biological
systems. Comparative Biochemistry and Physiology
Part A: Molecular & Integrative Physiology,
120(1), 3–9. https://doi.org/10.1016/S1095-6433
(98)10002-8
Turchin, P., Currie, T. E., Whitehouse, H., François, P.,
Feeney, K., Mullins, D., Hoyer, D., Collins, C.,
Grohmann, S., Savage, P., Mendel-Gleason, G.,
Turner, E., Dupeyron, A., Cioni, E., Reddish, J.,
Levine, J., Jordan, G., Brandl, E., Williams, A., …
Spencer, C. (2018). Quantitative historical analysis
uncovers a single dimension of complexity that
structures global variation in human social organi-
zation. Proceedings of the National Academy of Sci-
ences, 115(2), E144–E151. https://doi.org/10.1073/
pnas.1708800115
Turchin, V. (1977). The phenomenon of science: A
cybernetic approach to human evolution. Columbia
University Press.
Turner, V., Reinsel, D., Gantz, J., & Minton, S. (2014).
IDC. The digital universe of opportunities: Rich
data and the increasing value of the Internet of
Things. IDC Whitepaper. https://idcclients.cyclone
interactive.net/emc-digital-universe-iview-2014/
digital-universe-of-opportunities-vernon-turner.htm
Van der Leeuw, S. E. (1981). Information flows,
flow structures and the explanation of change in
human institutions. In S. E. Van der Leeuw (Ed.),
Archaeological approaches to the study of complex-
ity (pp. 230–329). Universiteit van Amsterdam,
Albert Egges van Giffen Instituut voor Prac- en
Protohistoric.
Vernadsky, W. I. (1945). The biosphere and the noö-
sphere. American Scientist, 33(1), xxii–12. https://
www.jstor.org/stable/27826043
Ward, A. F., Duke, K., Gneezy, A., & Bos, M. W. J.
(2017). Brain drain: The mere presence of one’s
own smartphone reduces available cognitive
capacity. Association for Consumer Research,
2(2), 140–154. https://doi.org/10.1086/691462
Wei, Y., de Lange, S. C., Scholtens, L. H., Watanabe,
K., Ardesch, D. J., Jansen, P. R., Savage, J. E., Li,
L., Preuss, T. M., Rilling, J. K., Posthuma, D., &
van den Heuvel, M. P. (2019). Genetic mapping
and evolutionary analysis of human-expanded cog-
nitive networks. Nature Communications, 10(1),
Article 4839. https://doi.org/10.1038/s41467-019-
12764-8
West, S. A., Fisher, R. M., Gardner, A., & Kiers, E. T.
(2015). Major evolutionary transitions in individu-
ality. Proceedings of the National Academy of Sci-
ences of the United States of America, 112(33),
10112–10119. https://doi.org/10.1073/pnas.1421
402112
Whalen, S., & Pollard, K. S. (2022). Enhancer func-
tion and evolutionary roles of human accelerated
regions. Annual Review of Genetics, 56(1), 423–
439. https://doi.org/10.1146/annurev-genet-071819-
103933
Whiten, A. (2019). Cultural evolution in animals.
Annual Review of Ecology, Evolution, and System-
atics, 50(1), 27–48. https://doi.org/10.1146/annurev-
ecolsys-110218-025040
Wilson, D. S., & Sober, E. (1989). Reviving the super-
organism. Journal of Theoretical Biology, 136(3),
337–356. https://doi.org/10.1016/S0022-5193(89)
80169-9
Wilson, D. S., Van Vugt, M., & O’Gorman, R. (2008).
Multilevel selection theory and major evolutionary
transitions: Implications for psychological science.
Current Directions in Psychological Science,
17(1), 6–9. https://doi.org/10.1111/j.1467-8721.200
8.00538.x
Wrangham, R. W. (2019). Hypotheses for the evolu-
tion of reduced reactive aggression in the context
of human self-domestication. Frontiers in Psychol-
ogy, 10, Article 1914. https://doi.org/10.3389/fpsyg
.2019.01914
Wrangham, R. W., Jones, J., Laden, G., Pilbeam, D., &
Conklin-Brittain, N. (1999). The raw and the stolen:
Cooking and the ecology of human origins. Current
Anthropology, 40(5), 567–594. https://doi.org/10
.1086/300083
Yudkowsky, E. (2008). Artificial intelligence as
a positive and negative factor in global risk.
Global Catastrophic Risks, 1(303), Article 184.
https://doi.org/10.1093/oso/9780198570509.003
.0021
Zhang, R. J., Liu, J. H., Lee, M., Lin, M. H., Xie, T.,
Chen, S. X., Leung, A. K., Lee, I. C., Hodgetts,
D., Valdes, E. A., & Choi, S. Y. (2024). Continuities
and discontinuities in the cultural evolution of
global consciousness. Philosophical Transactions of the Royal Society B: Biological Sciences,
379(1893), Article 20220263. https://doi.org/10
.1098/rstb.2022.0263
Zwolenski, M., & Weatherill, L. (2014). The digital
universe: Rich data and the increasing value of the
Internet of Things. Journal of Telecommunications
and the Digital Economy, 2(3), Article 9. https://
doi.org/10.18080/jtde.v2n3.285"""

test17 = """Agwuh, K. N., & MacGowan, A. (2006). Pharmacokinetics
and pharmacodynamics of the tetracyclines including
glycylcyclines. Journal of Antimicrobial Chemotherapy,
58(2), 256–265. https://doi.org/10.1093/jac/dkl224
Averill, L. A., Purohit, P., Averill, C. L., Boesl, M. A., Krystal,
J. H., & Abdallah, C. G. (2017). Glutamate dysregulation
and glutamatergic therapeutics for PTSD: Evidence from
human studies. Neuroscience Letters, 649, 147–155.
https://doi.org/10.1016/j.neulet.2016.11.064
Bach, D. R., Brown, S. A., Kleim, B., & Tyagarajan, S. K.
(2019). Extracellular matrix: A new player in memory
maintenance and psychiatric disorders. Swiss Medical
Weekly, 149(2122), w20060. https://doi.org/10.4414/
smw.2019.20060
Bach, D. R., Näf, M., Deutschmann, M., Tyagarajan, S. K., &
Quednow, B. B. (2019). Threat memory reminder under
matrix metalloproteinase 9 inhibitor doxycycline globally
reduces subsequent memory plasticity. The Journal of
Neuroscience, 39(47), 9424–9434. https://doi.org/10.
1523/JNEUROSCI.1285-19.2019
Bach, D. R., Tzovara, A., & Vunder, J. (2018). Blocking
human fear memory with the matrix metalloproteinase
inhibitor doxycycline. Molecular Psychiatry, 23(7),
1584–1589. https://doi.org/10.1038/mp.2017.65
Beroun, A., Mitra, S., Michaluk, P., Pijet, B., Stefaniuk, M., &
Kaczmarek, L. (2019). Mmps in learning and memory
and neuropsychiatric disorders. Cellular and Molecular
Life Sciences, 76(16), 3207–3228. https://doi.org/10.
1007/s00018-019-03180-8
Blackwell, S. E. (2021). Mental imagery in the science and
practice of cognitive behaviour therapy: Past, present,
and future perspectives. International Journal of
Cognitive Therapy, 14(1), 160–181. https://doi.org/10.
1007/s41811-021-00102-0
Blanchard, E. B., Hickling, E. J., Barton, K. A., Taylor, A. E.,
Loos, W. R., & Jones-Alexander, J. (1996). One-year pro-
spective follow-up of motor vehicle accident victims.
Behaviour Research and Therapy, 34(10), 775–786.
https://doi.org/10.1016/0005-7967(96)00038-1
Brady, K. T., Back, S. E., & Coffey, S. F. (2004). Substance
abuse and posttraumatic stress disorder. Current
Directions in Psychological Science, 13(5), 206–209.
https://doi.org/10.1111/j.0963-7214.2004.00309.x
Brewin, C. R. (2014). Episodic memory, perceptual memory,
and their interaction: Foundations for a theory of post-
traumatic stress disorder. Psychological Bulletin, 140(1),
69–97. https://doi.org/10.1037/a0033722
Brewin, C. R., Gregory, J. D., Lipton, M., & Burgess, N.
(2010). Intrusive images in psychological disorders:
Characteristics, neural mechanisms, and treatment impli-
cations. Psychological Review, 117(1), 210–232. https://
doi.org/10.1037/a0018113
Brewin, C. R., & Holmes, E. A. (2003). Psychological the-
ories of posttraumatic stress disorder. Clinical
Psychology Review, 23(3), 339–376. https://doi.org/10.
1016/S0272-7358(03)00033-3
Brown, T. E., Wilson, A. R., Cocking, D. L., & Sorg, B. A.
(2009). Inhibition of matrix metalloproteinase activity
disrupts reconsolidation but not consolidation of a fear
memory. Neurobiology of Learning and Memory, 91(1),
66–72. https://doi.org/10.1016/j.nlm.2008.09.003
Brunet, A., Saumier, D., Liu, A., Streiner, D. L., Tremblay, J.,
& Pitman, R. K. (2018). Reduction of PTSD symptoms
with pre-reactivation propranolol therapy: A randomized
controlled trial. American Journal of Psychiatry,
175(5), 427–433. https://doi.org/10.1176/appi.ajp.2017.
17050481
Corrigan, F. M., Fisher, J. J., & Nutt, D. J. (2011). Autonomic
dysregulation and the window of tolerance model of the
effects of complex emotional trauma. Journal of
Psychopharmacology, 25(1), 17–25. https://doi.org/10.
1177/0269881109354930
Cusack, K., Jonas, D. E., Forneris, C. A., Wines, C., & Sonis,
J. (2016). Psychological treatments for adults with post-
traumatic stress disorder: A systematic review and
meta-analysis. Clinical Psychology Review, 43, 128–141.
https://doi.org/10.1016/j.cpr.2015.10.003
Dalgleish, T., Black, M., Johnston, D., & Bevan, A. (2020).
Transdiagnostic approaches to mental health problems:
Current status and future directions. Journal of
Consulting and Clinical Psychology, 88(3), 179–195.
https://doi.org/10.1037/ccp0000482
Dewar, M., Paradis, A., & Fortin, C. A. (2019). Identifying
trajectories and predictors of response to psychotherapy
for post-traumatic stress disorder in adults: A systematic
review of literature. The Canadian Journal of Psychiatry,
65(2), 71–86. https://doi.org/10.1177/0706743719875602
Ehlers, A., & Clark, D. M. (2000). A cognitive model of post-
traumatic stress disorder. Behaviour Research and
Therapy, 38(4), 319–345. https://doi.org/10.1016/s0005-
7967(99)00123-0. PubMed PMID: 10761279.
Elsey, J. W. B., & Kindt, M. (2017). Breaking boundaries:
Optimizing reconsolidation-based interventions for
strong and old memories. Learning & Memory, 24(9),
472–479. https://doi.org/10.1101/lm.044156
Engeli, E. J. E., Zoelch, N., Hock, A., Nordt, C., Hulka, L. M.,
Kirschner, M., Scheidegger, M., Esposito, F.,
Baumgartner, M. R., Henning, A., Seifritz, E.,
Quednow, B. B., & Herdener, M. (2021). Impaired gluta-
mate homeostasis in the nucleus accumbens in human
cocaine addiction. Molecular Psychiatry, 26(9), 5277–
5285. https://doi.org/10.1038/s41380-020-0828-z
Enman, N. M., Arthur, K., Ward, S. J., Perrine, S. A., &
Unterwald, E. M. (2015). Anhedonia, reduced cocaine
reward, and dopamine dysfunction in a rat model of
posttraumatic stress disorder. Biological Psychiatry,
78(12), 871–879. https://doi.org/10.1016/j.biopsych.
2015.04.024
Fang, Q., Li, Z., Huang, G. D., Zhang, H. H., & Chen, Y. Y.
(2018). Traumatic stress produces distinct activations of
GABAergic and glutamatergic neurons in amygdala.
Frontiers in Neuroscience, 12(AUG), 387. https://doi.
org/10.3389/fnins.2018.00387
FDA. (2017). MINOCIN® (minocycline hydrochloride)
Pellet-Filled Capsules NDA 050649 [Internet].
Verfügbar unter. https://www.accessdata.fda.gov/
drugsatfda_docs/label/2017/050649s027lbl.pdf
Gawin, F. H. (1991). Cocaine addiction: Psychology and
neurophysiology. Science, 251(5001), 1580–1586. https://
doi.org/10.1126/science.2011738 PubMed PMID:
2011738
Gisquet-Verrier, P., & Le Dorze, C. (2019). Post traumatic
stress disorder and substance use disorder as two pathol-
ogies affecting memory reactivation: Implications for new
therapeutic approaches. Frontiers in Behavioral
Neuroscience, 13, 26. https://doi.org/10.3389/fnbeh.2019.
00026
Hackmann, A. (2011). Imagery rescripting in posttraumatic
stress disorder [Internet]. Report No. Verfügbar unter.
www.elsevier.com/locate/cabp
Hackmann, A., Ehlers, A., Speckens, A., & Clark, D. M.
(2004). Characteristics and content of intrusive memories
in PTSD and their changes with treatment. Journal of
Traumatic Stress, 17(3), 231–240. https://doi.org/10.
1023/B:JOTS.0000029266.88369.fd. PubMed PMID:
15253095.
Hinckley, J. D., & Danielson, C. K. (2022). Elucidating the
neurobiologic etiology of comorbid PTSD and substance
use disorders. Brain Sciences, 12(9), 1166. https://doi.org/
10.3390/brainsci12091166
Hopper, J. W., Frewen, P. A., Sack, M., Lanius, R. A., & van
der Kolk, B. A. (2007). The Responses to Script-Driven
Imagery Scale (RSDI): Assessment of state posttraumatic
symptoms for psychobiological and treatment research.
Journal of Psychopathology and Behavioral Assessment,
29(4), 249–268. https://doi.org/10.1007s10862-007-
9046-0
Iyadurai, L., Visser, R. M., Lau-Zhu, A., Porcheret, K., &
Horsch, A. (2019). Intrusive memories of trauma: A tar-
get for research bridging cognitive science and its clinical
application. Clinical Psychology Review, 69, 67–82.
https://doi.org/10.1016/j.cpr.2018.08.005
Kalivas, P. W., Gourley, S. L., & Paulus, M. P. (2023).
Intrusive thinking: Circuit and synaptic mechanisms of
a transdiagnostic psychiatric symptom. Neuroscience &
Biobehavioral Reviews, 150, 105196. https://doi.org/10.
1016/j.neubiorev.2023.105196
Kampman, K. M. (2019). The treatment of cocaine use dis-
order. Science Advances, 5(10), eaax1532. https://doi.org/
10.1126/sciadv.aax1532. PubMed PMID: 31663022;
PubMed Central PMCID: PMC6795516.
Kavanagh, D. J., May, J., & Andrade, J. (2009). Tests of the
elaborated intrusion theory of craving and desire:
Features of alcohol craving during treatment for an alco-
hol disorder. British Journal of Clinical Psychology, 48(Pt
3), 241–254. https://doi.org/10.1348/014466508X387071
PubMed PMID: 19364447.
Kindt, M. (2018). The surprising subtleties of changing fear
memory: A challenge for translational science.
Philosophical Transactions of the Royal Society B:
Biological Sciences, 373(1742), 20170033. https://doi.org/10.1098/rstb.2017.0033. PubMed PMID: 29352032;
PubMed Central PMCID: PMC5790831.
Kindt, M., & Elsey, J. W. B. (2023). A paradigm shift in
the treatment of emotional memory disorders:
Lessons from basic science. Brain Research Bulletin,
192, 168–174. https://doi.org/10.1016j.brainresbull.2022.
11.019
Kindt, M., Soeter, M., & Vervliet, B. (2009). Beyond extinc-
tion: Erasing human fear responses and preventing the
return of fear. Nature Neuroscience, 12(3), 256–258.
https://doi.org/10.1038/nn.2271
Koob, G. F., & Volkow, N. D. (2016). Neurobiology of
addiction: A neurocircuitry analysis. The Lancet
Psychiatry, 3(8), 760–773. https://doi.org/10.1016/
S2215-0366(16)00104-8. PubMed PMID: 27475769;
PubMed Central PMCID: PMC6135092.
Lanius, R. A., Bluhm, R., Lanius, U., & Pain, C. (2006). A
review of neuroimaging studies in PTSD: Heterogeneity
of response to symptom provocation. Journal of
Psychiatric Research, 40(8), 709–729. https://doi.org/10.
1016/j.jpsychires.2005.07.007
Lee, J. L. C., Nader, K., & Schiller, D. (2017). An update on
memory reconsolidation updating. Trends in Cognitive
Sciences, 21(7), 531–545. https://doi.org/10.1016/j.tics.
2017.04.006
María-Ríos, C. E., & Morrow, J. D. (2020). Mechanisms of
shared vulnerability to post-traumatic stress disorder
and substance use disorders. Frontiers in Behavioral
Neuroscience, 14, 6. https://doi.org/10.3389/fnbeh.2020.
00006. PubMed PMID: 32082127; PubMed Central
PMCID: PMC7006033.
Meister, L., Dietrich, A. C., Stefanovic, M., Bavato, F., Rosi-
Andersen, A., & Rohde, J., Offenhammer, B., Seifritz, E.,
Schäfer, I., Ehring, T., Barth, J., & Kleim, B. (2023).
Pharmacological memory modulation to augment
trauma-focused psychotherapy for PTSD: A systematic
review of randomised controlled trials. Translational
Psychiatry, 13(1), 207. https://doi.org/10.1038/s41398-
023-02495-2
Michaels, T. I., Stone, E., Singal, S., Novakovic, V., Barkin,
R. L., & Barkin, S. (2021). Brain reward circuitry: The
overlapping neurobiology of trauma and substance use
disorders. World Journal of Psychiatry, 11(6), 222–231.
https://doi.org/10.5498/wjp.v11.i6.222
Milton, A. L., & Everitt, B. J. (2012). The persistence of
maladaptive memory: Addiction, drug memories and
anti-relapse treatments. Neuroscience & Biobehavioral
Reviews, 36(4), 1119–1139. https://doi.org/10.1016/j.
neubiorev.2012.01.002. PubMed PMID: 22285426.
Modheji, M., Olapour, S., Khodayar, M. J., Jalili, A., &
Yaghooti, H. (2015). Minocycline is more potent than
tetracycline and doxycycline in inhibiting MMP-9 in
vitro. Jundishapur Journal of Natural Pharmaceutical
Products, 11(2), e27377. https://doi.org/10.17795/jjnpp-
27377
Nader, K., Schafe, G. E., & Le doux, J. E. (2000). The labile
nature of consolidation theory. Nature Reviews
Neuroscience, 1(3), 216–219. https://doi.org/10.1038/
35044580
Nagy, V., Bozdagi, O., Matynia, A., Balcerzyk, M., Okulski,
P., Dzwonek, J., Costa, R. M., Silva, A. J., Kaczmarek, L.,
& Huntley, G. W. (2006). Matrix metalloproteinase-9 is
required for hippocampal late-phase long-term poten-
tiation and memory. The Journal of Neuroscience. 26(7),
1923–1934. https://doi.org/10.1523/JNEUROSCI.4359-
05.2006 PubMed PMID: 16481424; PubMed Central
PMCID: PMC4428329.
Noël, X. (2023). A critical perspective on updating drug
memories through the integration of memory editing
and brain stimulation. Frontiers in Psychiatry, 14,
1161879. https://doi.org/10.3389/fpsyt.2023.1161879
O’Brien, S. T., Dozo, N., Hinton, J. D. X., Moeck, E. K.,
Susanto, R., & Jayaputera, G. T., Sinnott, R. O., Vu, D.,
Alvarez-Jimenez, M., Gleeson, J., & Koval, P. (2024).
SEMA3: A free smartphone platform for daily life sur-
veys. Behavior Research Methods, 56(7), 7691–7706.
https://doi.org/10.3758/s13428-024-02445-w
Panizzutti, B., Skvarc, D., Lin, S., Croce, S., Meehan, A.,
Bortolasci, C. C., Marx, W., Walker, A. J., Hasebe, K.,
Kavanagh, B. E., Morris, M. J., Mohebbi, M., Turner,
A., Gray, L., Berk, L., Walder, K., Berk, M., & Dean, O.
M. (2023). Minocycline as treatment for psychiatric and
neurological conditions: A systematic review and meta-
analysis. International Journal of Molecular Sciences,
24(6), 5250. https://doi.org/10.3390/ijms24065250
Peters, J., Kalivas, P. W., & Quirk, G. J. (2009). Extinction
circuits for fear and addiction overlap in prefrontal cor-
tex. Learning & Memory, 16(5), 279–288. https://doi.
org/10.1101/lm.1041309
Pietrzak, R. H., Goldstein, R. B., Southwick, S. M., & Grant,
B. F. (2011). Prevalence and Axis I comorbidity of full
and partial posttraumatic stress disorder in the United
States: Results from wave 2 of the National
Epidemiologic Survey on Alcohol and Related
Conditions. Journal of Anxiety Disorders, 25(3), 456–
465. https://doi.org/10.1016/j.janxdis.2010.11.010
Romero-Miguel, D., Lamanna-Rama, N., Casquero-Veiga, M.,
Gómez-Rangel, V., Desco, M., & Soto-Montenegro, M. L.
(2021). Minocycline in neurodegenerative and psychiatric
diseases: An update. European Journal of Neurology,
28(3), 1056–1081. https://doi.org/10.1111/ene.14642
Saladin, M. E., Gray, K. M., McRae-Clark, A. L., Larowe, S.
D., Yeatts, S. D., Baker, N. L., Hartwell, K. J., & Brady, K.
T. (2013). A double blind, placebo-controlled study of the
effects of post-retrieval propranolol on reconsolidation of
memory for craving and cue reactivity in cocaine depen-
dent humans. Psychopharmacology, 226(4), 721–737.
https://doi.org/10.1007/s00213-013-3039-3
Schmidt, H. D., & Pierce, R. C. (2010). Cocaine-induced
neuroadaptations in glutamate transmission. Annals of
the New York Academy of Sciences, 1187(1), 35–75.
https://doi.org/10.1111/j.1749-6632.2009.05144.x
PubMed PMID: 20201846; PubMed Central PMCID:
PMC5413205.
Schmucker, M., & Köster, R. (2025). Praxishandbuch
IRRT. 7. Aufl. Klett-Cotta.
Thome, J., Terpou, B. A., McKinnon, M. C., & Lanius, R. A.
(2020). The neural correlates of trauma-related autobio-
graphical memory in posttraumatic stress disorder: A
meta-analysis. Depression and Anxiety, 37(4), 321–345.
https://doi.org/10.1002/da.22977. PubMed PMID:
31815346.
Tiffany, S. T. (1993). The development of a cocaine craving
questionnaire. Drug and Alcohol Dependence, 34(1), 19–
28. https://doi.org/10.1016/0376-8716(93)90042-O
Wehrli, J. M., Xia, Y., Meister, L., Tursunova, S., Kleim, B.,
Bach, D. R., & Quednow, B. B. (2024). Forget me not: The
effect of doxycycline on human declarative memory.
European Neuropsychopharmacology, 89, 1–9. https://
doi.org/10.1016/j.euroneuro.2024.08.006
Wright, W. J., & Dong, Y. (2020). Psychostimulant-induced
adaptations in nucleus accumbens glutamatergic trans-
mission. Cold Spring Harbor Perspectives in Medicine,
10(12), a039255. https://doi.org/10.1101/cshperspect.a039255. PubMed PMID: 31964644; PubMed Central
PMCID: PMC7706579.
Xia, Y., Wehrli, J., Abivardi, A., Hostiuc, M., Kleim, B., &
Bach, D. R. (2024). Attenuating human fear memory
retention with minocycline: A randomized placebo-con-
trolled trial. Translational Psychiatry, 14(1), 1. https://
doi.org/10.1038/s41398-024-02732-2
Zacher, A., Dietiker, L., Häffner, V., Bavato, F., Kleim, B., &
Quednow, B. B. (2025). Substance-related intrusive
memories in cocaine use disorder are different
from, but associated with craving [Manuscript under
revision]. (Department of Psychology, University of
Zurich).
Zacher, A., Dietiker, L., Janousch, C., Rühlmann, C.,
Quednow, B., & Kleim, B. (2025). Shared and distinct fea-
tures of intrusive memories in posttraumatic stress dis-
order and cocaine use disorder: A transdiagnostic
ecological momentary assessment study [Manuscript
submitted for publication]. Located at: Departement of
Psychology, University of Zurich."""

test18 = """Adank, P., Davis, M. H., & Hagoort, P. (2012). Neural dissociation
in processing noise and accent in spoken language comprehension.
Neuropsychologia, 50(1), 77–84. https://doi.org/10.1016/j.neuropsycholo
gia.2011.10.024
American Psychiatric Association. (2013). Diagnostic and statistical
manual of mental disorders (5th ed.). https://doi.org/10.1176/appi.boo
ks.9780890425596
Arioli, M., Gianelli, C., & Canessa, N. (2021). Neural representation of
social concepts: A coordinate-based meta-analysis of fMRI studies.
Brain Imaging and Behavior, 15(4), 1912–1921. https://doi.org/10
.1007/s11682-020-00384-6
Baez, S., Pinasco, C., Roca, M., Ferrari, J., Couto, B., García-Cordero, I.,
Ibañez, A., Cruz, F., Reyes, P., Matallana, D., Manes, F., Cetcovich, M., &
Torralva, T. (2019). Brain structural correlates of executive and social
cognition profiles in behavioral variant frontotemporal dementia and
elderly bipolar disorder. Neuropsychologia, 126, 159–169. https://doi.org/
10.1016/j.neuropsychologia.2017.02.012
Banse, R., & Scherer, K. R. (1996). Acoustic profiles in vocal emotion
expression. Journal of Personality and Social Psychology, 70(3), 614–
636. https://doi.org/10.1037/0022-3514.70.3.614
Barbosa, I. G., Leite, F. D. M. C., Bertoux, M., Guimarães, H. C.,
Mariano, L. I., Gambogi, L. B., Teixeira, A. L., Caramelli, P., & de
Souza, L. C. (2023). Social cognition across bipolar disorder and
behavioral variant frontotemporal dementia: An exploratory study.
Revista Brasileira de Psiquiatria, 45(2), 132–136. https://doi.org/10
.47626/1516-4446-2022-2935
Bertoux, M., Delavest, M., de Souza, L. C., Funkiewiez, A., Lépine, J.-P.,
Fossati, P., Dubois, B., & Sarazin, M. (2012). Social Cognition and
Emotional Assessment differentiates frontotemporal dementia from
depression. Journal of Neurology, Neurosurgery, and Psychiatry, 83(4),
411–416. https://doi.org/10.1136/jnnp-2011-301849
Bertoux, M., Duclos, H., Caillaud, M., Segobin, S., Merck, C., de La Sayette,
V., Belliard, S., Desgranges, B., Eustache, F., & Laisney, M. (2020).
When affect overlaps with concept: Emotion recognition in semantic
variant of primary progressive aphasia. Brain: A Journal of Neurology,
143(12), 3850–3864. https://doi.org/10.1093/brain/awaa313
Bézy, C., Renard, A., & Pariente, J. (2016). Grémots. Evaluation du
langage dans les pathologies neurodégénératives—Catherine Bézy,
Antoine Renard, Jérémie Pariente. https://www.boutique-happyneuron
.com/neurologie-eval/72-gremots.html
Briggs, R. G., Tanglay, O., Dadario, N. B., Young, I. M., Fonseka, R. D.,
Hormovas, J., Dhanaraj, V., Lin, Y.-H., Kim, S. J., Bouvette, A.,
Chakraborty, A. R., Milligan, T. M., Abraham, C. J., Anderson, C. D.,
O’Donoghue, D. L., & Sughrue, M. E. (2021). The unique fiber anatomy of
middle temporal gyrus default mode connectivity. Operative Neurosurgery,
21(1), E8–E14. https://doi.org/10.1093/ons/opab109
Chiu, I., Piguet, O., Diehl-Schmid, J., Riedl, L., Beck, J., Leyhe, T.,
Holsboer-Trachsler, E., Kressig, R. W., Berres, M., Monsch, A. U., &
Sollberger, M. (2018). Facial emotion recognition performance differ-
entiates between behavioral variant frontotemporal dementia and major
depressive disorder. The Journal of Clinical Psychiatry, 79(1), Article
7076. https://doi.org/10.4088/JCP.16m11342
Clopper, C. G., & Smiljanic, R. (2011). Effects of gender and regional dialect
on prosodic patterns in American English. Journal of Phonetics, 39(2),
237–245. https://doi.org/10.1016/j.wocn.2011.02.006
Compton, M. T., Lunden, A., Cleary, S. D., Pauselli, L., Alolayan, Y.,
Halpern, B., Broussard, B., Crisafio, A., Capulong, L., Balducci, P. M.,
Bernardini, F., & Covington, M. A. (2018). The aprosody of schizo-
phrenia: Computationally derived acoustic phonetic underpinnings of
monotone speech. Schizophrenia Research, 197, 392–399. https://doi.org/
10.1016/j.schres.2018.01.007
Coppieters, R., Bouzigues, A., Jiskoot, L., Montembeault, M., Tee, B. L.,
Rohrer, J. D., Bruffaerts, R., & Genetic Frontotemporal dementia Initiative (GENFI). (2024). A systematic review of the quantitative markers of
speech and language of the frontotemporal degeneration spectrum and
their potential for cross-linguistic implementation. medRxiv. https://
doi.org/10.1101/2024.01.05.24300888
Cotter, J., Granger, K., Backx, R., Hobbs, M., Looi, C. Y., & Barnett, J. H.
(2018). Social cognitive dysfunction as a clinical marker: A systematic
review of meta-analyses across 30 clinical conditions. Neuroscience and
Biobehavioral Reviews, 84, 92–99. https://doi.org/10.1016/j.neubiorev
.2017.11.014
Coulombe, V., Joyal, M., Martel-Sauvageau, V., & Monetta, L. (2023).
Affective prosody disorders in adults with neurological conditions: A
scoping review. International Journal of Language & Communication
Disorders, 58(6), 1939–1954. https://doi.org/10.1111/1460-6984.12909
Couper-Kuhlen, E. (2011). 17. Pragmatics and prosody: Prosody as social action.
In W. Bublitz & N. R. Norrick (Eds.), Foundations of pragmatics (pp. 491–
510). De Gruyter Mouton. https://doi.org/10.1515/9783110214260.491
Cummins, N., Scherer, S., Krajewski, J., Schnieder, S., Epps, J., & Quatieri,
T. F. (2015). A review of depression and suicide risk assessment using
speech analysis. Speech Communication, 71, 10–49. https://doi.org/10
.1016/j.specom.2015.03.004
de Beer, C., Wartenburger, I., Huttenlauch, C., & Hanne, S. (2023). A
systematic review on production and comprehension of linguistic prosody
in people with acquired language and communication disorders resulting
from unilateral brain lesions. Journal of Communication Disorders, 101,
Article 106298. https://doi.org/10.1016/j.jcomdis.2022.106298
de Boer, J. N., Voppel, A. E., Brederoo, S. G., Wijnen, F. N. K., & Sommer,
I. E. C. (2020). Language disturbances in schizophrenia: The relation with
antipsychotic medication. NPJ Schizophrenia, 6(1), Article 24. https://
doi.org/10.1038/s41537-020-00114-3
Ding, H., & Zhang, Y. (2023). Speech prosody in mental disorders. Annual
Review of Linguistics, 9(9), pp. 335–355. https://doi.org/10.1146/annurev-
linguistics-030421-065139
Dodich, A., Crespi, C., Santi, G. C., Cappa, S. F., & Cerami, C. (2021).
Evaluation of discriminative detection abilities of social cognition mea-
sures for the diagnosis of the behavioral variant of frontotemporal
dementia: A systematic review. Neuropsychology Review, 31(2), 251–
266. https://doi.org/10.1007/s11065-020-09457-1
Dogil, G., Ackermann, H., Grodd, W., Haider, H., Kamp, H., Mayer, J.,
Riecker, A., & Wildgruber, D. (2002). The speaking brain: A tutorial
introduction to fMRI experiments in the production of speech, prosody
and syntax. Journal of Neurolinguistics, 15(1), 59–90. https://doi.org/10
.1016/S0911-6044(00)00021-X
Ducharme, S., Dols, A., Laforce, R., Devenney, E., Kumfor, F., van den
Stock, J., Dallaire-Théroux, C., Seelaar, H., Gossink, F., Vijverberg, E.,
Huey, E., Vandenbulcke, M., Masellis, M., Trieu, C., Onyike, C.,
Caramelli, P., de Souza, L. C., Santillo, A., Waldö, M. L., … Pijnenburg,
Y. (2020). Recommendations to distinguish behavioural variant fronto-
temporal dementia from psychiatric disorders. Brain: A Journal of
Neurology, 143(6), 1632–1650. https://doi.org/10.1093/brain/awaa018
Ducharme, S., Pearl-Dowler, L., Gossink, F., McCarthy, J., Lai, J.,
Dickerson, B. C., Chertkow, H., Rapin, L., Vijverberg, E., Krudop, W.,
Dols, A., & Pijnenburg, Y. (2019). The frontotemporal dementia versus
primary psychiatric disorder (FTD versus PPD) checklist: A bedside
clinical tool to identify behavioral variant FTD in patients with late-onset
behavioral changes. Journal of Alzheimer’s Disease, 67(1), 113–124.
https://doi.org/10.3233/JAD-180839
Eichhorn, J. T., Kent, R. D., Austin, D., & Vorperian, H. K. (2018). Effects of
aging on vocal fundamental frequency and vowel formants in men and
women. Journal of Voice, 32(5), 644.e1–644.e9. https://doi.org/10.1016/j
.jvoice.2017.08.003
Fieldhouse, J. L. P., Singleton, E. H., van Engelen, M. E., Van’t Hooft, J. J.,
de Boer, S. C. M., Froeling, V. E., Braun, M., Oudega, M. L., van
Grootheest, D., Kerssens, C., Duits, F. H., van Harten, A. C., Vijverberg,
E. G. B., & Pijnenburg, Y. A. L. (2023). Decreased emotion recognition
and reduced focus on facial hallmarks in behavioral variant frontotemporal
dementia compared to primary psychiatric disorders and controls.
European Journal of Neurology, 30(8), 2222–2229. https://doi.org/10
.1111/ene.15837
Geraudie, A., Battista, P., García, A. M., Allen, I. E., Miller, Z. A., Gorno-
Tempini, M. L., & Montembeault, M. (2021). Speech and language
impairments in behavioral variant frontotemporal dementia: A systematic
review. Neuroscience and Biobehavioral Reviews, 131, 1076–1095.
https://doi.org/10.1016/j.neubiorev.2021.10.015
Geraudie, A., Pressman, P. S., Pariente, J., Millanski, C., Palser, E. R.,
Ratnasiri, B. M., Battistella, G., Mandelli, M. L., Miller, Z. A., Miller,
B. L., Sturm, V., Rankin, K. P., Gorno-Tempini, M. L., & Montembeault,
M. (2023). Expressive prosody in patients with focal anterior temporal
neurodegeneration. Neurology, 101(8), e825–e835. https://doi.org/10
.1212/WNL.0000000000207516
Good, C. D., Johnsrude, I. S., Ashburner, J., Henson, R. N. A., Friston, K. J.,
& Frackowiak, R. S. J. (2001). A voxel-based morphometric study of
ageing in 465 normal adult human brains. NeuroImage, 14(1), 21–36.
https://doi.org/10.1006/nimg.2001.0786
Gossink, F., Schouws, S., Krudop, W., Scheltens, P., Stek, M., Pijnenburg,
Y., & Dols, A. (2018). Social cognition differentiates behavioral variant
frontotemporal dementia from other neurodegenerative diseases and
psychiatric disorders. The American Journal of Geriatric Psychiatry,
26(5), 569–579. https://doi.org/10.1016/j.jagp.2017.12.008
Goy, H., Fernandes, D. N., Pichora-Fuller, M. K., & van Lieshout, P. (2013).
Normative voice data for younger and older adults. Journal of Voice,
27(5), 545–555. https://doi.org/10.1016/j.jvoice.2013.03.002
Hanakawa, T. (2011). Rostral premotor cortex as a gateway between motor
and cognitive networks. Neuroscience Research, 70(2), 144–154. https://
doi.org/10.1016/j.neures.2011.02.010
Hanakawa, T., Dimyan, M. A., & Hallett, M. (2008). Motor planning,
imagery, and execution in the distributed motor network: A time-course
study with functional MRI. Cerebral Cortex, 18(12), 2775–2788. https://
doi.org/10.1093/cercor/bhn036
Hanakawa, T., Honda, M., Sawamoto, N., Okada, T., Yonekura, Y.,
Fukuyama, H., & Shibasaki, H. (2002). The role of rostral Brodmann area
6 in mental-operation tasks: An integrative neuroimaging approach.
Cerebral Cortex, 12(11), 1157–1170. https://doi.org/10.1093/cercor/12
.11.1157
Hsu, C.-W., Huang, C.-C., Hsu, C. H., Bi, Y., Tzeng, O. J.-L., & Lin, C.-P.
(2025). Revisiting human language and speech production network: A
meta-analytic connectivity modeling study. NeuroImage, 306, Article
121008. https://doi.org/10.1016/j.neuroimage.2025.121008
Ibanez, A. (2022). The mind’s golden cage and cognition in the wild. Trends
in Cognitive Sciences, 26(12), 1031–1034. https://doi.org/10.1016/j.tics
.2022.07.008
Ibanez, A., Kringelbach, M. L., & Deco, G. (2024). A synergetic turn in
cognitive neuroscience of brain diseases. Trends in Cognitive Sciences,
28(4), 319–338. https://doi.org/10.1016/j.tics.2023.12.006
Kramer, J. H., Mungas, D., Possin, K. L., Rankin, K. P., Boxer, A. L., Rosen,
H. J., Bostrom, A., Sinha, L., Berhel, A., & Widmeyer, M. (2014). NIH
EXAMINER: Conceptualization and development of an executive
function battery. Journal of the International Neuropsychological Society,
20(1), 11–19. https://doi.org/10.1017/S1355617713001094
Leroy, M., Bertoux, M., Skrobala, E., Mode, E., Adnet-Bonte, C., Le Ber, I.,
Bombois, S., Cassagnaud, P., Chen, Y., Deramecourt, V., Lebert, F.,
Mackowiak, M. A., Sillaire, A. R., Wathelet, M., Pasquier, F., Lebouvier,
T., Abied, R., Adnet, C., Barois, A., … Verpoort, C. (2021). Characteristics
and progression of patients with frontotemporal dementia in a regional
memory clinic network. Alzheimer’s Research & Therapy, 13(1), Article 19.
https://doi.org/10.1186/s13195-020-00753-9
Leyton, C. E., & Hillis, A. E. (2017). Affective prosody in frontotemporal
dementia: The importance of “pitching it right”. Neurology, 89(7), 644–
645. https://doi.org/10.1212/WNL.0000000000004245
Lopes da Cunha, P., Ruiz, F., Ferrante, F., Sterpin, L. F., Ibáñez, A.,
Slachevsky, A., Matallana, D., Martínez, Á., Hesse, E., & García, A. M.
(2024). Automated free speech analysis reveals distinct markers of
Alzheimer’s and frontotemporal dementia. PLOS ONE, 19(6), Article
e0304272. https://doi.org/10.1371/journal.pone.0304272
Lowit, A., & Kent, R. D. (2011). Assessment of motor speech disorders.
https://pureportal.strath.ac.uk/en/publications/assessment-of-motor-speech-
disorders
Martínez-Sánchez, F., Muela-Martínez, J. A., Cortés-Soto, P., García
Meilán, J. J., Vera Ferrándiz, J. A., Egea Caparrós, A., & Pujante
Valverde, I. M. (2015). Can the acoustic analysis of expressive prosody
discriminate schizophrenia? The Spanish Journal of Psychology, 18,
Article E86. https://doi.org/10.1017/sjp.2015.85
Meeter, L. H. H., Vijverberg, E. G., Del Campo, M., Rozemuller, A. J. M.,
Donker Kaat, L., de Jong, F. J., van der Flier, W. M., Teunissen, C. E., van
Swieten, J. C., & Pijnenburg, Y. A. L. (2018). Clinical value of neuro-
filament and phospho-tau/tau ratio in the frontotemporal dementia
spectrum. Neurology, 90(14), e1231–e1239. https://doi.org/10.1212/
WNL.0000000000005261
Nevler, N., Ash, S., Jester, C., Irwin, D. J., Liberman, M., & Grossman,
M. (2017). Automatic measurement of prosody in behavioral variant
FTD. Neurology, 89(7), 650–656. https://doi.org/10.1212/WNL.0000
000000004236
Pépiot, E. (2015). Voice, speech and gender: Male–female acoustic dif-
ferences and cross-language variation in English and French speakers.
Corela. Advance online publication. https://doi.org/10.4000/corela.3783
Petrides, M. (2023). On the evolution of polysensory superior temporal
sulcus and middle temporal gyrus: A key component of the semantic
system in the human brain. The Journal of Comparative Neurology,
531(18), 1987–1995. https://doi.org/10.1002/cne.25521
Pressman, P. S., Ross, E. D., Cohen, K. B., Chen, K.-H., Miller, B. L.,
Hunter, L. E., Gorno-Tempini, M. L., & Levenson, R. W. (2019).
Interpersonal prosodic correlation in frontotemporal dementia. Annals of
Clinical and Translational Neurology, 6(7), 1352–1357. https://doi.org/10
.1002/acn3.50816
Rascovsky, K., Hodges, J. R., Knopman, D., Mendez, M. F., Kramer, J. H.,
Neuhaus, J., van Swieten, J. C., Seelaar, H., Dopper, E. G. P., Onyike, C. U.,
Hillis, A. E., Josephs, K. A., Boeve, B. F., Kertesz, A., Seeley, W. W.,
Rankin, K. P., Johnson, J. K., Gorno-Tempini, M.-L., Rosen, H., … Miller,
B. L. (2011). Sensitivity of revised diagnostic criteria for the behavioural
variant of frontotemporal dementia. Brain: A Journal of Neurology, 134(9),
2456–2477. https://doi.org/10.1093/brain/awr179
Ross, E. D., & Monnot, M. (2008). Neurology of affective prosody and
its functional-anatomic organization in right hemisphere. Brain and
Language, 104(1), 51–74. https://doi.org/10.1016/j.bandl.2007.04.007
Schirmer, A., & Kotz, S. A. (2006). Beyond the right hemisphere: Brain
mechanisms mediating vocal emotional processing. Trends in Cognitive
Sciences, 10(1), 24–30. https://doi.org/10.1016/j.tics.2005.11.009
Schurz, M., Radua, J., Aichhorn, M., Richlan, F., & Perner, J. (2014).
Fractionating theory of mind: A meta-analysis of functional brain imaging
studies. Neuroscience and Biobehavioral Reviews, 42, 9–34. https://
doi.org/10.1016/j.neubiorev.2014.01.009
Singleton, E. H., Fieldhouse, J. L. P., van’t Hooft, J. J., Scarioni, M., van
Engelen, M. E., Sikkes, S. A. M., de Boer, C., Bocancea, D. I., van den
Berg, E., Scheltens, P., van der Flier, W. M., Papma, J. M., Pijnenburg,
Y. A. L., & Ossenkoppele, R. (2023). Social cognition deficits and
biometric signatures in the behavioural variant of Alzheimer’s disease.
Brain: A Journal of Neurology, 146(5), 2163–2174. https://doi.org/10
.1093/brain/awac382
Ukaegbe, O. C., Holt, B. E., Keator, L. M., Brownell, H., Blake, M. L., &
Lundgren, K. (2022). Aprosodia following focal brain damage: What’s
right and what’s left? American Journal of Speech-Language Pathology,
31(5S), 2313–2328. https://doi.org/10.1044/2022_AJSLP-21-00302
Ulugut, H., & Pijnenburg, Y. A. L. (2023). Frontotemporal dementia: Past,
present, and future. Alzheimer’s & Dementia, 19(11), 5253–5263. https://
doi.org/10.1002/alz.13363
Vijverberg, E. G. B., Dols, A., Krudop, W. A., Del Campo Milan, M.,
Kerssens, C. J., Gossink, F., Prins, N. D., Stek, M. L., Scheltens, P.,
Teunissen, C. E., & Pijnenburg, Y. A. L. (2017). Cerebrospinal fluid
biomarker examination as a tool to discriminate behavioral variant
frontotemporal dementia from primary psychiatric disorders. Alzheimer’s
& Dementia: Diagnosis, Assessment & Disease Monitoring, 7(1), 99–106.
https://doi.org/10.1016/j.dadm.2017.01.009
Vijverberg, E. G. B., Schouws, S., Meesters, P. D., Verwijk, E., Comijs, H.,
Koene, T., Schreuder, C., Beekman, A., Scheltens, P., Stek, M.,
Pijnenburg, Y., & Dols, A. (2017). Cognitive deficits in patients with
neuropsychiatric symptoms: A comparative study between behavioral
variant frontotemporal dementia and primary psychiatric disorders. The
Journal of Clinical Psychiatry, 78(8), e940–e946. https://doi.org/10.4088/
JCP.16m11019
Visser, M., Jefferies, E., & Lambon Ralph, M. A. (2010). Semantic pro-
cessing in the anterior temporal lobes: A meta-analysis of the functional
neuroimaging literature. Journal of Cognitive Neuroscience, 22(6), 1083–
1094. https://doi.org/10.1162/jocn.2009.21309
Vogel, A. P., Poole, M. L., Pemberton, H., Caverlé, M. W. J., Boonstra,
F. M. C., Low, E., Darby, D., & Brodtmann, A. (2017). Motor speech
signature of behavioral variant frontotemporal dementia: Refining the
phenotype. Neurology, 89(8), 837–844. https://doi.org/10.1212/WNL
.0000000000004248
Vonk, J. M. J., Morin, B. T., Pillai, J., Rosado Rolon, D., Bogley, R.,
Baquirin, D. P., Ezzes, Z., Tee, B. L., de Leon, J., Wauters, L., Lukic,
S., Montembeault, M., Younes, K., Miller, Z. A., García, A. M.,
Mandelli, M. L., Miller, B. L., Rosen, H. J., Rankin, K. P., … Gorno-
Tempini, M. L. (2025). Automated speech analysis to differentiate
frontal and right anterior temporal lobe atrophy in frontotemporal
dementia. Neurology, 104(9), Article e213556. https://doi.org/10
.1212/WNL.0000000000213556
Woolley, J. D., Khan, B. K., Murthy, N. K., Miller, B. L., & Rankin, K. P.
(2011). The diagnostic challenge of psychiatric symptoms in neurode-
generative disease: Rates of and risk factors for prior psychiatric diagnosis
in patients with early neurodegenerative disease. The Journal of Clinical
Psychiatry, 72(2), 126–133. https://doi.org/10.4088/JCP.10m06382oli"""

test19 = """Ansan Trauma Center. (2024). Health and social welfare
study on the victims of the Sewol ferry disaster. https://
www.ansantrauma.net/sub.php?menukey=27&mode=
view&idx=256&ctgr=2&srhctgr=&srhstr=
Atwoli, L., Stein, D. J., Koenen, K. C., & McLaughlin, K. A.
(2015). Epidemiology of posttraumatic stress disorder:
Prevalence, correlates and consequences. Current
Opinion in Psychiatry, 28(4), 307–311. https://doi.org/
10.1097/YCO.0000000000000167
Bartrop, R., Buckley, T., & Toﬂer, G. H. (2015).
Bereavement and the risk of cardiovascular disease. In
M. Alvarenga & D. Byrne (Eds.), Handbook of psychocar-
diology (pp. 1–18). Springer Singapore. https://doi.org/
10.1007/978-981-4560-53-5_18-1
Bhandari, A., & Wagner, T. (2006). Self-reported utilization
of health care services: Improving measurement and
accuracy. Medical Care Research and Review, 63(2),
217–235. https://doi.org/10.1177/1077558705285298
Chae, J. H., Huh, H. J., & Choi, W. J. (2018). Embitterment
and bereavement: The sewol ferry accident example.
Psychological Trauma, 10(1), 46–50. https://doi.org/10.
1037/tra0000308
Choi, H., & Cho, S.-m. (2020). Posttraumatic stress disorder
and complicated grief in bereaved parents of the sewol
ferry disaster exposed to injustice following the loss.
International Journal of Social Psychiatry, 66(2), 163–
170. https://doi.org/10.1177/0020764019894607
Chung, J.-B., Choi, E., Kim, L., & Kim, B. J. (2022).
Politicization of a disaster and victim blaming: Analysis
of the Sewol ferry case in Korea. International Journal
of Disaster Risk Reduction, 69, 102742. https://doi.org/
10.1016/j.ijdrr.2021.102742
Cozza, S. J., Fisher, J. E., Fetchet, M. A., Chen, S., Zhou, J.,
Fullerton, C. S., & Ursano, R. J. (2019). Patterns of
comorbidity among bereaved family members 14 years
after the September 11th, 2001, terrorist attacks. Journal
of Traumatic Stress, 32(4), 526–535. https://doi.org/10.
1002/jts.22407
Cozza, S. J., Fisher, J. E., Zhou, J., Harrington-LaMorie, J., La
Flair, L., Fullerton, C. S., & Ursano, R. J. (2017). Bereaved
military dependent spouses and children: Those left
behind in a decade of War (2001–2011). Military
Medicine, 182(3), e1684–e1690. https://doi.org/10.7205/
milmed-d-16-00101
Donnelly, R., Lin, Z., & Umberson, D. (2023). Parental
death across the life course, social isolation, and health
in later life: Racial/ethnic disadvantage in the U.S.
Social Forces, 102(2), 586–608. https://doi.org/10.1093/
sf/soad027
Dorn, T., Yzermans, C. J., Kerssens, J. J., Spreeuwenberg, P.
M., & van der Zee, J. (2006). Disaster and subsequent
healthcare utilization: A longitudinal study among vic-
tims, their family members, and control subjects.
Medical Care, 44(6), 581–589. https://doi.org/10.1097/
01.mlr.0000215924.21326.37
Goenjian, A. K., Walling, D., Steinberg, A. M., Roussos, A.,
Goenjian, H. A., & Pynoos, R. S. (2009). Depression and
PTSD symptoms among bereaved adolescents 6(1/2)
years after the 1988 Spitak earthquake. Journal of
Aﬀective Disorders, 112(1-3), 81–84. https://doi.org/10.
1016/j.jad.2008.04.006
Health Council of the Nethelands. (2006). The medium and
long-term health impact of disasters.
Heo, S. J., Kim, Y. A., Lee, D. H., & Shin, J. Y. (2024). How
bereaved parents experience public, self stigma years after a
child’s death. OMEGA – Journal of Death and Dying, 90(1),
194–224. https://doi.org/10.1177/00302228221100902
Jadhav, A., & Weir, D. (2018). Widowhood and depression in a
cross-national perspective: Evidence from the United States,
Europe, Korea, and China. The Journals of Gerontology.
Series B, Psychological Sciences and Social Sciences, 73(8),
e143–e153. https://doi.org/10.1093/geronb/gbx021
Kapfhammer, H. P. (2018). Acute and long-term mental and
physical sequelae in the aftermath of traumatic exposure
– Some remarks on “the body keeps the score”.
Psychiatria Danubina, 30(3), 254–272. https://doi.org/
10.24869/psyd.2018.254
Kohn, R., & Levav, I. (1990). Bereavement in disaster: An
overview of the research. International Journal of
Mental Health, 19(2), 61–76. https://doi.org/10.1080/
00207411.1990.11449163
Kristensen, P., Weisaeth, L., Hussain, A., & Heir, T. (2015).
Prevalence of psychiatric disorders and functional
impairment after loss of a family member: A longitudinal
study after the 2004 Tsunami. Depression and Anxiety,
32(1), 49–56. https://doi.org/10.1002/da.22269
Kristensen, P., Weisæth, L., & Heir, T. (2012). Bereavement
and mental health after sudden and violent losses: A
review. Psychiatry: Interpersonal and Biological Processes,
75(1), 76–97. https://doi.org/10.1521/psyc.2012.75.1.76
Lee, H. J. (2023). The right to health of victims, citizens, and
parents: a study of families bereaved by the sewol ferry
disaster. Journal of Korean Anthropology Review, 7, 1–30.
Lee, M.-S., Huh, H. J., Oh, J., & Chae, J.-H. (2022).
Comparative analysis of the psychosocial symptoms and
experiences of bereaved parents and parents of children
who survived the sewol ferry accident after 5 years: A
qualitative interview study. Journal of Korean Medical
Science, 37(19), e150. https://doi.org/10.3346/jkms.2022.
37.e150
Levav, I., Kohn, R., Iscovich, J., Abramson, J. H., Tsai, W. Y.,
& Vigdorovich, D. (2000). Cancer incidence and survival
following bereavement. American Journal of Public
Health, 90(10), 1601–1607. https://doi.org/10.2105/ajph.
90.10.1601
Li, J., Johansen, C., & Olsen, J. (2003). Cancer survival in
parents who lost a child: A nationwide study in
Denmark. British Journal of Cancer, 88(11), 1698–1701.
https://doi.org/10.1038/sj.bjc.6600948
Lu, D., Sundstrom, K., Sparen, P., Fall, K., Sjolander, A.,
Dillner, J., Helm, N. Y., Adami, H. O., Valdimarsdottir,
U., & Fang, F. (2016). Bereavement is associated with
an increased risk of HPV infection and cervical cancer:
An epidemiological study in Sweden. Cancer Research,
76(3), 643–651. https://doi.org/10.1158/0008-5472.
CAN-15-1788
McFarlane, A. C., & Van Hoof, M. (2015). The counterintui-
tive eﬀect of a disaster: The need for a long-term perspec-
tive. Australian & New Zealand Journal of Psychiatry,
49(4), 313–314. https://doi.org/10.1177/0004867415576393
Nordström, E. L., Kaltiala, R., Kristensen, P., & Thimm, J. C.
(2024). Somatic symptoms and insomnia among bereaved
parents and siblings eight years after the Utøya terror
attack. European Journal of Psychotraumatology, 15(1),
2300585. https://doi.org/10.1080/20008066.2023.2300585
Nordström, E. L., Thimm, J. C., Kaltiala, R., & Kristensen, P.
(2022). Prolonged grief, post-traumatic stress, and func-
tional impairment in parents and siblings 8 years after the 2011 Utøya terror attack. European Journal of
Psychotraumatology, 13(2), 2152930. https://doi.org/10.
1080/20008066.2022.2152930
Olsen, J., Li, J., & Precht, D. H. (2005). Hospitalization
because of diabetes and bereavement: A national cohort
study of parents who lost a child. Diabetic Medicine,
22(10), 1338–1342. https://doi.org/10.1111/j.1464-5491.
2005.01642.x
Prigerson, H. G., Bierhals, A. J., Kasl, S. V., Reynolds, C. F.,
3rd, Shear, M. K., Day, N., Beery, L. C., Newsom, J. T., &
Jacobs, S. (1997). Traumatic grief as a risk factor for men-
tal and physical morbidity. American Journal of
Psychiatry, 154(5), 616–623. https://doi.org/10.1176/ajp.
154.5.616
Prigerson, H. G., Silverman, G. K., Jacobs, S. C.,
Maciejewski, P. K., Kasl, S. V., & Rosenheck, R. A.
(2001). Disability, traumatic grief, and the underutiliza-
tion ofhealth services: A preliminary examination.
Primary Psychiatry, 8, 61–69.
Puri, P. R., & Dimsdale, J. E. (2011). Health care utilization
and poor reassurance: Potential predictors of somato-
form disorders. Psychiatric Clinics of North America,
34(3), 525–544. https://doi.org/10.1016/j.psc.2011.05.011
Schoo, C., Azhar, Y., Mughal, S., & Rout, P. (2025). Grief
and prolonged grief disorder. In Statpearls [Internet].
StatPearls Publishing.
Seiler, A., von Kanel, R., & Slavich, G. M. (2020). The psy-
chobiology of bereavement and health: A conceptual
review from the perspective of social signal transduction
theory of depression. Frontiers in Psychiatry, 11, 565239.
https://doi.org/10.3389/fpsyt.2020.565239
Shin, M. (2024, April 1). The sewol ferry disaster, 10 years
later: Despite two changes in the South Korean presi-
dency, bereaved families say their questions remain
unanswered. The Diplomat.
Stahl, S. T., & Schulz, R. (2014). Changes in routine health
behaviors following late-life bereavement: A systematic
review. Journal of Behavioral Medicine, 37(4), 736–755.
https://doi.org/10.1007/s10865-013-9524-7
Stroebe, M., Schut, H., & Stroebe, W. (2007). Health out-
comes of bereavement. The Lancet, 370(9603), 1960–
1973. https://doi.org/10.1016/S0140-6736(07)61816-9
Thoresen, S., Birkeland, M. S., Arnberg, F. K., Wentzel-
Larsen, T., & Blix, I. (2019). Long-term mental health
and social support in victims of disaster: Comparison
with a general population sample. BJPsych Open, 5(1),
e2. https://doi.org/10.1192/bjo.2018.74
Thorpe, R. J., Kelley-Moore, J. A., & Whitﬁeld, K. E. (2015).
Methodological considerations when comparing
bereaved and non-bereaved individuals in population
studies. Social Psychiatry and Psychiatric Epidemiology,
50(9), 1413–1421. https://doi.org/10.1007/s00127-015-
1067-7
Xu, Y., Herrman, H., Tsutsumi, A., & Fisher, J. (2013).
Psychological and social consequences of losing a child
in a natural or human-made disaster: A review of the evi-
dence. Asia-Paciﬁc Psychiatry, 5(4), 237–248. https://doi.
org/10.1111/appy.12013"""

test20 = """Australian Bureau of Statistics. (2021). Service with the Australian Defence Force: Census. ABS. https://www.abs.gov.au/
statistics/people/people-and-communities/service-australian-defence-force-census/2021
Bentler, P. M. (1990). Comparative fit indexes in structural models. Psychological Bulletin, 107(2), 238–246. https://doi.org/
10.1037/0033-2909.107.2.238
Brooks, S. K., & Greenberg, N. (2022). Mental health and psychological wellbeing of maritime personnel: A systematic
review. BMC Psychology, 10(1), 139. https://doi.org/10.1186/s40359-022-00850-4
Browne, M. W., & Cudeck, R. (1993). Alternative ways of assessing model fit. In K. A. Bollen & J. S. Long (Eds.), Testing
structural equation models (pp. 136–162). Sage.
Buckman, J. E. J., Forbes, H. J., Clayton, T., Jones, M., Jones, N., Greenberg, N., Sundin, J., Hull, L., Wessely, S., & Fear, N. T.
(2013). Early service leavers: A study of the factors associated with premature separation from the UK Armed Forces
and the mental health of those that leave early. European Journal of Public Health, 23(3), 410–415. https://doi.org/10.
1093/eurpub/cks042
Burdett, H., Fear, N., Wessely, S., & Rona, R. (2021). Military and demographic predictors of mental ill-health and
socioeconomic hardship among UK veterans. BMC Psychiatry, 21(1), 1–11. https://doi.org/10.1186/s12888-021-
03296-x
Carra, K., Curtin, M., Fortune, T., & Gordon, B. (2023). Service and demographic factors, health, trauma exposure, and
participation are associated with adjustment for former Australian Defense Force members. Military Psychology, 35(5),
480–492. https://doi.org/10.1080/08995605.2022.2120312
Carrington, J. G. (2023). Review of international practice in the reintegration of veterans: Considerations for Ukraine in the
war and post-war context. United Nations Development Programme (UNDP) in Ukraine. https://www.undp.org/ukraine/
publications/review-international-practice-reintegration-veterans-considerations-ukraine-war-and-post-war-context
Elnitsky, C. A., Fisher, M. P., & Blevins, C. L. (2017). Military service member and veteran reintegration: A conceptual
analysis, unified definition, and key domains. Frontiers in Psychology, 8(369). https://doi.org/10.3389/fpsyg.2017.00369
Enggasser, J. L., Livingston, N. A., Ameral, V., Brief, D. J., Rubin, A., Helmuth, E., Roy, M., Solhan, M., Litwack, S.,
Rosenbloom, D., & Keane, T. M. (2021). Public implementation of a web-based program for veterans with risky alcohol
use and PTSD: A RE-AIM evaluation of VetChange. Journal of Substance Abuse Treatment, 122, 108242. https://doi.org/
10.1016/j.jsat.2020.108242
Geretto, M., Ferrari, M., De Angelis, R., Crociata, F., Sebastiani, N., Pulliero, A., Au, W., & Izzotti, A. (2021). Occupational
exposures and environmental health hazards of military personnel. International Journal of Environmental Research
and Public Health, 18(10), 5395. https://doi.org/10.3390/ijerph18105395
Glasgow, R. E., Vogt, T. M., & Boles, S. M. (1999). Evaluating the public health impact of health promotion interventions:
The RE-AIM framework. American Journal of Public Health, 89(9), 1322–1327. https://doi.org/10.2105/ajph.89.9.1322
Greenhalgh, T., Wherton, J., Papoutsi, C., Lynch, J., Hughes, G., A’Court, C., Hinder, S., Fahy, N., Procter, R., & Shaw, S. (2017).
Beyond adoption: A new framework for theorizing and evaluating nonadoption, abandonment, and challenges to the
scale-up, spread, and sustainability of health and care technologies. Journal of Medical Internet Research, 19(11), e367.
https://doi.org/10.2196/jmir.8775
Hu, L., & Bentler, P. M. (1999). Cutoff criteria for fit indexes in covariance structure analysis: Conventional criteria versus
new alternatives. Structural Equation Modeling, 6(1), 1–55. https://doi.org/10.1080/10705519909540118
Kerr, N. C., Lane, S. J., Plotnikoff, R. C., & Ashby, S. (2023). The “transition” to civilian life from the perspective of former
serving Australian Defence Force members. Journal of Veterans Studies, 9(1), 129–142. https://doi.org/10.21061/jvs.
v9i1.407
Lieberman, D. A. (2012). Digital games for health behavior change: Research, design, and future directions. In S. M. Noar &
N. G. Harrington (Eds.), eHealth applications: Promising strategies for behavior change (pp. 110–127). Routledge.
Livieri, G., Mangina, E., Protopapadakis, E. D., & Panayiotou, A. G. (2025). The gaps and challenges in digital health
technology use as perceived by patients: A scoping review and narrative meta-synthesis. Frontiers in Digital Health, 7,
1474956. https://doi.org/10.3389/fdgth.2025.1474956
MacLean, M. B., Van Til, L., Thompson, J. M., Sweet, J., Poirier, A., Sudom, K., & Pedlar, D. J. (2014). Postmilitary adjustment
to civilian life: Potential risks and protective factors. Physical Therapy, 94(8), 1186–1195. https://doi.org/10.2522/ptj.
20120107
Mair, J. L., Hashim, J., Thai, L., Tai, E. S., Ryan, J. C., Kowatsch, T., Müller-Riemenschneider, F., & Edney, S. M. (2025).
Understanding and overcoming barriers to digital health adoption: A patient and public involvement study.
Translational Behaviour Medicine, 15(1). https://doi.org/10.1093/tbm/ibaf010
McCaslin, S. E., Becket-Davenport, C., Dinh, J. V., Lasher, B., Kim, M., Choucroun, G., & Herbst, E. (2021). Military
acculturation and readjustment to the civilian context. Psychological Trauma, 13(6), 611–620. https://doi.org/10.
1037/tra0000999
McGinty, E. E., Alegria, M., Beidas, R. S., Braithwaite, J., Kola, L., Leslie, D. L., Moise, N., Mueller, B., Pincus, H. A., Shidhaye, R.,
Simon, K., Singer, S. J., Stuart, E. A., & Eisenberg, M. D. (2024). The Lancet Psychiatry Commission: Transforming mental
health implementation research. Lancet Psychiatry, 11(5), 368–396. https://doi.org/10.1016/s2215-0366(24)00040-3
Pedlar, D., Thompson, J. M., & Andrew Castro, C. (2019). Chapter 3 - Military-to-civilian transition theories and frameworks.
In C. A. Castro & S. Dursun (Eds.), Military veteran reintegration (pp. 21–50). Academic Press. https://doi.org/10.1016/
B978-0-12-815312-3.00003-6
Ravindran, C., Morley, S. W., Stephens, B. M., Stanley, I. H., & Reger, M. A. (2020). Association of suicide risk with transition
to civilian life among US military service members. JAMA Network Open, 3(9), e2016261. https://doi.org/10.1001/
jamanetworkopen.2020.16261
Riva, G., Terruzzi, T., & Anolli, L. (2003). The use of the internet in psychological research: Comparison of online and offline
questionnaires. Cyber Psychology & Behavior, 6(1), 73–80. https://doi.org/10.1089/109493103321167983
Romaniuk, M., Fisher, G., Kidd, C., & Batterham, P. J. (2020). Assessing psychological adjustment and cultural reintegration
after military service: Development and psychometric evaluation of the post-separation Military-Civilian Adjustment
and Reintegration Measure (M-CARM). BMC Psychiatry, 20(1), 531. https://doi.org/10.1186/s12888-020-02936-y
Romaniuk, M., & Kidd, C. (2018). The psychological adjustment experience of reintegration following discharge from
military service: A systematic review. Journal of Military and Veterans Health, 26(2), 60–73. https://doi.org/10.2021/
33613133/JMVHVol26No2
Royal Commission into Defence and Veteran Suicide. (2024). Final report (volumes 1-9). Commonwealth of Australia.
Runnals, J. J., Garovoy, N., McCutcheon, S. J., Robbins, A. T., Mann-Wrobel, M. C., & Elliott, A. (2014). Systematic review of
women veterans’ mental health. Womens Health Issues, 24(5), 485–502. https://doi.org/10.1016/j.whi.2014.06.012
Sachdev, S., & Dixit, S. (2024). Military to civilian cultural transition experiences of retired military personnel: A systematic
meta-synthesis. Military Psychology, 36(6), 579–592. https://doi.org/10.1080/08995605.2023.2237835
Stevens, J. P. (2012). Applied multivariate statistics for the social sciences. Routledge.
Van Hooff, M., Lawrence-Wood, E., McFarlane, A., & Van Til, L. (2018). The Australian Defence Force mental health
prevalence and wellbeing study. The Medical Journal of Australia, 209(7), 305–310. https://doi.org/10.5694/mja17.
01152
Yentes, R., & Wilhelm, F. (2023). Procedures for computing indices of careless responding. https://cran.r-project.org/web/
packages/careless/refman/careless.html
Zhao, Y., Summers, R., Gathara, D., & English, M. (2024). Conducting cross-cultural, multi-lingual or multi-country scale
development and validation in health care research: A 10-step framework based on a scoping review. Journal of Global
Health, 14, 04151. https://doi.org/10.7189/jogh.14.04151
Zimmerman, M. (2024). The value and limitations of self-administered questionnaires in clinical practice and epidemio-
logical studies. World Psychiatry, 23(2), 210–212. https://doi.org/10.1002/wps.21191"""

test21 = """Alisic, E., Zalta, A. K., van Wesel, F., Larsen, S. E., Hafstad, G.
S., Hassanpour, K., & Smid, G. E. (2014). Rates of post-
traumatic stress disorder in trauma-exposed children and
adolescents: Meta-analysis. British Journal of Psychiatry,
204(5), 335–340. https://doi.org/10.1192/bjp.bp.113.131227
Australian Institute of Health and Welfare. AIHW. (2025
[cited 2025 Aug 18]). Alcohol, tobacco & other drugs in
Australia, Younger people. Available from: https://www.
aihw.gov.au/reports/alcohol/alcohol-tobacco-other-
drugs-australia/contents/priority-populations/younger-
people
Back, S. E., Brady, K. T., Sonne, S. C., & Verduin, M. L.
(2006). Symptom improvement in co-occurring PTSD
and alcohol dependence. Journal of Nervous & Mental
Disease, 194(9), 690–696. https://doi.org/10.1097/01.
nmd.0000235794.12794.8a
Back, S. E., Killeen, T., Badour, C. L., Flanagan, J. C., Allan, N.
P., Ana, E. S., Lozano, B., Foa, E.B., & Brady, K. T. (2019).
Concurrent treatment of substance use disorders and
PTSD using prolonged exposure: A randomized clinical
trial in military veterans. Addictive Behaviors, 90, 369–
377. https://doi.org/10.1016/j.addbeh.2018.11.032
Back, S. E., Killeen, T., Foa, E. B., Santa Ana, E. J., Gros, D.
F., & Brady, K. T. (2012). Use of an integrated therapy
with prolonged exposure to treat PTSD and comorbid
alcohol dependence in an Iraq veteran. American
Journal of Psychiatry, 169(7), 688–691. https://doi.org/
10.1176/appi.ajp.2011.11091433
Back, S. E., Killeen, T. K., Teer, A. P., Hartwell, E. E.,
Federline, A., Beylotte, F., & Cox, E. (2014). Substance
use disorders and PTSD: An exploratory study of treat-
ment preferences among military veterans. Addictive
Behaviors, 39(2), 369–373. https://doi.org/10.1016/j.
addbeh.2013.09.017
Badour, C. L., Flanagan, Julianne C., Allan, N. P., Gilmore,
A. K., Gros, D. F., Killeen, T., Korte, K. J., Brown Delisa
G., Kolnogorova, K., & Back, S. E. (2022). Temporal
dynamics of symptom change among veterans receiving
an integrated treatment for posttraumatic stress disorder
and substance use disorders. Journal of Traumatic Stress,
35(2), 546–558. https://doi.org/10.1002/jts.22769
Barrett, E. L., Teesson, M., & Mills, K. L. (2014).
Associations between substance use, post-traumatic stress
disorder and the perpetration of violence: A longitudinal
investigation. Addictive Behaviors, 39(6), 1075–1080.
https://doi.org/10.1016/j.addbeh.2014.03.003
Basedow, L. A., Kuitunen-Paul, S., Roessner, V., & Golub, Y.
(2020). Traumatic events and substance use disorders in
adolescents. Frontiers in Psychiatry, 11, 559. https://doi.
org/10.3389/fpsyt.2020.00559
Blanco, C., Xu, Y., Brady, K., Pérez-Fuentes, G., Okuda, M.,
& Wang, S. (2013). Comorbidity of posttraumatic stress
disorder with alcohol dependence among US adults:
Results from national epidemiological survey on alcohol
and related conditions. Drug and Alcohol Dependence,
132(3), 630–638. https://doi.org/10.1016/j.drugalcdep.
2013.04.016
Borah, E. V., Holder, N., & Chen, K. (2017). Providers’ use
of evidence-based treatments for posttraumatic stress dis-
order: The influence of training, attitudes, and barriers in
military and private treatment settings. Best Practices in
Mental Health, 13(1), 34–46. https://doi.org/10.70256/
997168psfxuw
Brady, K. T., & Back, S. E. (2012). Childhood trauma, post-
traumatic stress disorder, and alcohol dependence.
Alcohol Research: Current Reviews, 34(4), 408–413.
https://doi.org/10.35946/arcr.v34.4.05
Brady, K. T., Dansky, B. S., Back, S. E., Foa, E. B., & Carroll,
K. M. (2001). Exposure therapy in the treatment of PTSD
among cocaine-dependent individuals. Journal of
Substance Abuse Treatment, 21(1), 47–54. https://doi.
org/10.1016/S0740-5472(01)00182-9
Callaghan, R. C., Sanches, M., Benny, C., Stockwell, T.,
Sherk, A., & Kish, S. J. (2019). Who consumes most of
the cannabis in Canada? Profiles of cannabis consump-
tion by quantity. Drug and Alcohol Dependence, 205,
107587. https://doi.org/10.1016/j.drugalcdep.2019.
107587
Castro-Schilo, L., & Grimm, K. (2018). Using residualized
change versus difference scores for longitudinal research.
Journal of Social and Personal Relationships, 35(1), 32–58.
https://doi.org/10.1177/0265407517718387
Danielson, C. K., Adams, Z., McCart, M. R., Chapman, J. E.,
Sheidow, A. J., Walker, J., Smalling, A., & d Arellano,
M. A. (2020). Safety and efficacy of exposure-based risk
reduction through family therapy for co-occurring sub-
stance use problems and posttraumatic stress disorder
symptoms among adolescents. JAMA Psychiatry, 77(6),
574–586. https://doi.org/10.1001/jamapsychiatry.2019.
4803
Darnell, D., Flaster, A., Hendricks, K., Kerbrat, A., &
Comtois, K. A. (2019). Adolescent clinical populations
and associations between trauma and behavioral and
emotional problems. Psychological Trauma: Theory,
Research, Practice, and Policy, 11(3), 266–273. https://
doi.org/10.1037/tra0000371
Dawson, D., Stjepanovic, D., Lorenzetti, V., Hall, W. D., &
Leung, J. (2024). How much cannabis is used in a joint
in Australia? An experimental investigation into use by
potency and frequency. Drug and Alcohol Dependence,
43(1), 226–232.
Deacon, B. J., Farrell, N. R., Kemp, J. J., Dixon, L. J., Sy, J. T.,
Zhang, A. R., & McGrath, P. B. (2013). Assessing thera-
pist reservations about exposure therapy for anxiety dis-
orders: The therapist beliefs about exposure scale.
Journal of Anxiety Disorders, 27(8), 772–780. https://
doi.org/10.1016/j.janxdis.2013.04.006
Dube, S. R., Anda, R. F., Felitti, V. J., Chapman, D. P.,
Williamson, D. F., & Giles, W. H. (2001). Childhood
abuse, household dysfunction, and the risk of attempted
suicide throughout the life span. JAMA, 286(24), 3089–
3096. https://doi.org/10.1001/jama.286.24.3089
Ehlers, A., Bisson, J., Clark, D. M., Creamer, M., Pilling, S.,
Richards, D., Shnurr, P. P., Turner, S., & Yule, W. (2010).
Do all psychological treatments really work the same in
posttraumatic stress disorder? Clinical Psychology
Review, 30(2), 269–276. https://doi.org/10.1016/j.cpr.
2009.12.001
Freeman, T. P., & Lorenzetti, V. (2020). ‘Standard THC
units’: A proposal to standardize dose across all cannabis
products and methods of administration. Addiction,
115(7), 1207–1216. https://doi.org/10.1111/add.14842
Gielen, N., Havermans, R. C., Tekelenburg, M., & Jansen, A.
(2012). Prevalence of post-traumatic stress disorder among
patients with substance use disorder: It is higher than clin-
icians think it is. European Journal of Psychotraumatology,
3(1), 17734. https://doi.org/10.3402/ejpt.v3i0.17734
Gielen, N., Krumeich, A., Tekelenburg, M., Nederkoorn, C.,
& Havermans, R. C. (2016). How patients perceive the
relationship between trauma, substance abuse, craving,
and relapse: A qualitative study. Journal of Substance
Use, 21(5), 466–470. https://doi.org/10.3109/14659891.
2015.1063717
Gilhooly, T., Bergman, A. J., Stieber, J., & Brown, E. J.
(2018). Posttraumatic stress disorder symptoms, family
environment, and substance abuse symptoms in emer-
ging adults. Journal of Child & Adolescent Substance
Abuse, 27(3), 196–209. https://doi.org/10.1080/
1067828X.2018.1446861
Gunsolley, J. C., Getchell, C., & Chinchilli, V. M. (1995).
Small sample characteristics of generalized estimating
equations. Communications in Statistics - Simulation
and Computation, 24(4), 869–878. https://doi.org/10.
1080/03610919508813280
Hall, W. D., Patton, G., Stockings, E., Weier, M., Lynskey,
M., Morley, K. I., & Degenhardt, L. (2016). Why young
people’s substance use matters for global health. The
Lancet Psychiatry, 3(3), 265–279. https://doi.org/10.
1016/S2215-0366(16)00013-4
Hawn, S. E., Cusack, S. E., & Amstadter, A. B. (2020). A sys-
tematic review of the self-medication hypothesis in the
context of posttraumatic stress disorder and comorbid
problematic alcohol Use. Journal of Traumatic Stress,
33(5), 699–708. https://doi.org/10.1002/jts.22521
Hien, D. A., Gette, J. A., Blakey, S. M., Piccirillo, M. L., Back,
S. E., Bauer, A. G., Ebrahimi, C .T., Ellis, R. A., Killen, T.
K., Lehinger, E. A., Lopez-Castro, T., Norman, S. B.,
Ruglass, L. M., Saraiya, T. C., Saavedra, L. M., &
Morgan-López, A. A. (2025). How changes in post-trau-
matic stress disorder (PTSD) severity mediate substance
use disorder (SUD) severity during and after treatment
for co-occurring PTSD and SUD: Results from project
harmony. Addiction, 120(11), 2245–2257. https://doi.
org/10.1111/add.70126
Hien, D. A., Jiang, H., Campbell, A. N., Hu, M. C., Miele, G.
M., Cohen, L. R., Brigham, G. S., Capstick, C., Kulaga, A.,
Robinson, J., & Suarez-Morales, L. (2010). Do treatment
improvements in PTSD severity affect substance use out-
comes? A secondary analysis from a randomized clinical
trial in NIDA’s clinical trials network. American Journal
of Psychiatry, 167(1), 95–101. https://doi.org/10.1176/
appi.ajp.2009.09091261
Hien, D. A., Papini, S., Saavedra, L. M., Bauer, A. G.,
Ruglass, L. M., Ebrahimi, C. T., Fitzpatrick, S., López-
Castro, T., Norman, S. B., Killeen, T. K., Back, S. E., &
Morgan-López, A. A. (2024). Project harmony: A sys-
tematic review and network meta-analysis of psychother-
apy and pharmacologic trials for comorbid posttraumatic
stress, alcohol, and other drug use disorders.
Psychological Bulletin, 150(3), 319–353. https://doi.org/
10.1037/bul0000409
Hien, D. A., Smith, K. Z., Owens, M., López-Castro, T.,
Ruglass, L. M., & Papini, S. (2018). Lagged effects of sub-
stance use on PTSD severity in a randomized controlled
trial with modified prolonged exposure and relapse pre-
vention. Journal of Consulting and Clinical Psychology,
86(10), 810–819. https://doi.org/10.1037/ccp0000345
Hien, D. A., Wells, E. A., Jiang, H., Suarez-Morales, L.,
Campbell, A. N., Cohen, L. R., Miele, G. M., Killeen, T.,
Brigham, G. S., Zhang, Y., & Hansen, C. (2009).
Multisite randomized trial of behavioral interventions
for women with co-occurring PTSD and substance use
disorders. Journal of Consulting and Clinical Psychology,
77(4), 607–619. https://doi.org/10.1037/a0016227
Kaczkurkin, A. N., Asnaani, A., Alpert, E., & Foa, E. B.
(2016). The impact of treatment condition and the lagged
effects of PTSD symptom severity and alcohol use on
changes in alcohol craving. Behaviour Research and
Therapy, 79, 7–14. https://doi.org/10.1016/j.brat.2016.
02.001
Kaplow, J. B., Rolon-Arroyo, B., Layne, C. M., Rooney, E.,
Oosterhoff, B., Hill, R., Steinberg, A. M., Lotterman, J.,
Gallagher, K. A., & Pynoos, R. S. (2020). Validation of
the UCLA PTSD reaction index for DSM-5: A develop-
mentally informed assessment tool for youth. Journal of
the American Academy of Child & Adolescent
Psychiatry, 59(1), 186–194. https://doi.org/10.1016/j.
jaac.2018.10.019
Kay-Lambkin, F. J., Baker, A. L., Kelly, B., & Lewin, T. J.
(2011). Clinician-assisted computerised versus thera-
pist-delivered treatment for depressive and addictive dis-
orders: A randomised controlled trial. Medical Journal of
Australia, 195(S3), S44–S50. https://doi.org/10.5694/j.
1326-5377.2011.tb03265.x
Kazdin, A. E. (2009). Understanding how and why psy-
chotherapy leads to change. Psychotherapy Research,
19(4-5), 418–428. https://doi.org/10.1080/1050330080
2448899
Knight, J. R., Shrier, L. A., Bravender, T. D., Farrell, M., Bilt,
V., Shaffer, J., & J, H. (1999). A new brief screen for ado-
lescent substance abuse. Archives of Pediatrics &
Adolescent Medicine, 153(6), 591–596. https://doi.org/
10.1001/archpedi.153.6.591
Laurenceau, J. P., Hayes, A. M., & Feldman, G. C. (2007).
Some methodological and statistical issues in the study
of change processes in psychotherapy. Clinical
Psychology Review, 27(6), 682–695. https://doi.org/10.
1016/j.cpr.2007.01.007
Liang, K. Y., & Zeger, S. (1986). Longitudinal data analysis
using generalized linear models. Biometrika, 73(1), 13–
22. https://doi.org/10.1093/biomet/73.1.13
Mancl, L. A., & DeRouen, T. A. (2001). A covariance estima-
tor for GEE with improved small-sample properties.
Biometrics, 57(1), 126–134. https://doi.org/10.1111/j.
0006-341X.2001.00126.x
Martin, G., & Copeland, J. (2008). The adolescent cannabis
check-up: Randomized trial of a brief intervention for
young cannabis users. Journal of Substance Abuse
Treatment, 34(4), 407–414. https://doi.org/10.1016/j.jsat.
2007.07.004
McGovern, M. P., Lambert-Harris, C., Acquilano, S., Xie,
H., Alterman, A. I., & Weiss, R. D. (2009). A cognitive
behavioral therapy for co-occurring substance use and
posttraumatic stress disorders. Addictive Behaviors,
34(10), 892–897. https://doi.org/10.1016/j.addbeh.2009.
03.009
McLaughlin, K. A., Koenen, K. C., Hill, E. D., Petukhova,
M., Sampson, N. A., Zaslavsky, A. M., & Kessler, R. C.
(2013). Trauma exposure and posttraumatic stress dis-
order in a national sample of adolescents. Journal of the
American Academy of Child & Adolescent Psychiatry,
52(8), 815–830.e14. https://doi.org/10.1016/j.jaac.2013.
05.011
Mefodeva, V., Carlyle, M., Walter, Z., & Hides, L. (2023).
Client and staff perceptions of the integration of trauma
informed care and specialist posttraumatic stress disorder treatment in residential treatment facilities for substance
use: A qualitative study. Drug and Alcohol Dependence,
42(1), 181–192.
Meyer, J. M., Farrell, N. R., Kemp, J. J., Blakey, S. M., &
Deacon, B. J. (2014). Why do clinicians exclude anxious
clients from exposure therapy? Behaviour Research and
Therapy, 54, 49–53. https://doi.org/10.1016/j.brat.2014.
01.004
Miles, S. R., Hale, W. J., Mintz, J., Wachen, J. S., Litz, B. T.,
Dondanville, K. A., Yarvis, J. S., Hembree, E. A., Young-
McCaughan, S., Peterson, A. L., & Resick, P. A. (2023).
Hyperarousal symptoms linger after successful PTSD
treatment inactive duty military.. Psychological Trauma:
Theory, Research, Practice, AndPolicy, 15(8), 1398–1405.
https://doi.org/10.1037/tra0001292
Mills, K. L., Barrett, E., Back, S. E., Cobham, V. E., Bendall,
S., Perrin, S., Brady, K. T., Ross, J., Peach, N., Kihas, I., &
Cassar, J. (2020). Randomised controlled trial of inte-
grated trauma-focused psychotherapy for traumatic
stress and substance use among adolescents: Trial proto-
col. BMJ Open, 10(11), e043742. https://doi.org/10.1136/
bmjopen-2020-043742
Mills, K. L., Peach, N., Dobinson, K. A., Kihas, I., Cassar, J.
Isik, A., Bezzina, L., Schollar-Root, O., Cobham, V.E.,
Barrett, E.L. Perrin, S., Back, S.E., Brady, K., Milne, B.,
& Teesson, M. Integrated exposure-based therapy for
co-occurring post-traumatic stress and substance use
among young people: A randomized controlled Trial
(in preparation).
Mills, K. L., Teesson, M., Back, S. E., Brady, K. T., Baker, A.
L., Hopwood, S., Sannibale, C., Barrett, E. L., Merz, S.,
Rosenfeld, J., & Ewer, P. L. (2012). Integrated exposure-
based therapy for co-occurring posttraumatic stress dis-
order and substance dependence. JAMA, 308(7), 690–
699. https://doi.org/10.1001/jama.2012.9071
Murray, H., Grey, N.,Warnock-Parkes, E., Kerr, A.,Wild, J.,
Clark, D. M., & Ehlers, A. (2022). Ten misconceptions
about trauma-focused CBT for PTSD. The Cognitive
Behaviour Therapist, 15, e33. https://doi.org/10.1017/
S1754470X22000307
Nader, K., Kriegler, K. A., Blake, D. D., Pynoos, R. S.,
Newman, E., & Weathers, F. W. Clinician-administered
PTSD scale for children and adolescents [Internet].
2013 [cited 2025 Jun 14]. Available from: https://doi.
apa.org/doi/10.1037t08962-000
National Health and Medical Research Council. (2020).
Australian Guidelines to Reduce Health Risks from
Drinking Alcohol [Internet]. Canberra: Commonwealth
of Australia; 2020 [cited 2025 Sep 24]. Available from:
https://www.nhmrc.gov.au/about-us/publications/
australian-guidelines-reduce-health-risks-drinking-
alcohol#block-views-block-file-attachments-content-
block-1
Nooner, K. B., Linares, L. O., Batinjane, J., Kramer, R. A.,
Silva, R., & Cloitre, M. (2012). Factors related to posttrau-
matic stress disorder in adolescence. Trauma, Violence, &
Abuse, 13(3), 153–166. https://doi.org/10.1177/
1524838012447698
Norman, S. B., Haller, M., Hamblen, J. L., Southwick, S. M.,
& Pietrzak, R. H. (2018). The burden of co-occurring
alcohol use disorder and PTSD in U.S. Military veterans:
Comorbidities, functioning, and suicidality.. Psychology
of Addictive Behaviors, 32(2), 224–229. https://doi.org/
10.1037/adb0000348
Oprel, D. A. C., Hoeboer, C. M., Schoorl, M., Kleine, R. A.
de, Cloitre, M., Wigard, I. G., van Minnen, A., & van der
Does, W. Effect of prolonged exposure, intensified
prolonged exposure and STAIR+prolonged exposure in
patients with PTSD related to childhood abuse: A ran-
domized controlled trial + Prolonged exposure in
patients with PTSD related to childhood abuse: A ran-
domized controlled trial. European Journal of
Psychotraumatology. 2021;12(1):1851511. https://doi.
org/10.1080/20008198.2020.1851511
Ouimette, P., Goodwin, E., & Brown, P. J. (2006). Health
and well being of substance use disorder patients with
and without posttraumatic stress disorder. Addictive
Behaviors, 31(8), 1415–1423. https://doi.org/10.1016/j.
addbeh.2005.11.010
Ouimette, P., Read, J. P., Wade, M., & Tirone, V. (2010).
Modeling associations between posttraumatic stress
symptoms and substance use. Addictive Behaviors,
35(1), 64–67. https://doi.org/10.1016/j.addbeh.2009.08.
009
Patrick ME, Miech RA, Johnston LD, O’Malley PM.
Monitoring the Future Panel Study annual report:
national data on substance use among adults ages 19 to
65, 1976–2023 [Internet]. Arbor (MI): Institute for
Social Research; 2024 [cited 2025 Aug 18]. Available
from: https://monitoringthefuture.org/mtfpanelvol2/
Peach, N., Kihas, I., Isik, A., Cassar, J., Barrett, E. L.,
Cobham, V., Back, S. E., Perrin, S., Bendall, S., Brady,
K., Ross, J., Teesson, M., Bezzina, L., Dobinson, K. A.,
Schollar-Root, O., Milne, B., & Mills, K. L. Clinical
characteristics of adolescents and emerging adults pre-
senting for integrated posttraumatic stress and substance
use treatment. Advances in Dual Diagnosis.
2024;17(2):54–71. https://doi.org/10.1108/ADD-11-
2023-0021
Peirce, J. M., Schacht, R. L., & Brooner, R. K. (2020). The
effects of prolonged exposure on substance use in patients
with posttraumatic stress disorder and substance use dis-
orders. Journal of Traumatic Stress, 33(4), 465–476.
https://doi.org/10.1002/jts.22546
Renaud, F., Jakubiec, L., Swendsen, J., & Fatseas, M. (2021).
The impact of Co-occurring post-traumatic stress dis-
order and substance use disorders on craving: A systema-
tic review of the literature. Frontiers in Psychiatry, 12.
Roberts, N. P., Roberts, P. A., Jones, N., & Bisson, J. I.
(2016). Psychological therapies for post-traumatic stress
disorder and comorbid substance use disorder.
Cochrane Database of Systematic Reviews, 2016(4).
https://doi.org/10.1002/14651858.CD010204.pub2
Robinson, L. D., & Deane, F. P. (2022). Substance use dis-
order and anxiety, depression, eating disorder, PTSD,
and phobia comorbidities among individuals attending
residential substance use treatment settings. Journal of
Dual Diagnosis, 18(3), 165–176. https://doi.org/10.1080/
15504263.2022.2090648
Rodriguez L, Jenzer T, Read JP. Physical and mental health
and other functional outcomes in co-occurring PTSD and
substance use disorders. In: Posttraumatic stress and sub-
stance use disorders. Routledge; 2019.
Ruglass, L. M., Gette, J. A., Morgan-López, A. A., Ye, A.,
Smith, K. Z., Fitzpatrick, S., López-Castro, T., Saavedra,
L. M., Norman, S. B., Killeen, T. K., & Back, S. E.
(2025). Indirect effects of seeking safety plus sertraline
on alcohol use: The mediating role of reductions in post-
traumatic stress disorder symptom severity. Journal of
Traumatic Stress, 1–10.
Ruglass LM, Lopez-Castro T, Papini S, Killeen T, Back SE,
Hien DA. Concurrent treatment with prolonged
exposure for Co-occurring full or subthreshold posttrau-
matic stress disorder and substance Use disorders: A randomized clinical trial. Psychotherapy and
Psychosomatics. 2017;86(3):150–161. https://doi.org/10.
1159/000462977
Saunders, B. E., & Adams, Z. W. (2014). Epidemiology of
traumatic experiences in childhood. Child and
Adolescent Psychiatric Clinics of North America, 23(2),
167–184. https://doi.org/10.1016/j.chc.2013.12.003
Schollar-Root, O., Cassar, J., Peach, N., Cobham, V. E.,
Milne, B., Barrett, E., Back, S. E., Bendall, S., Perrin, S.,
Brady, K., Ross, J., Teesson, M., Kihas, I., Dobinson, K.
A., & Mills, K. L. (2022). Integrated trauma-focused psy-
chotherapy for traumatic stress and substance use: Two
adolescent case studies. Clinical Case Studies, 21(3),
192–208. https://doi.org/10.1177/15346501211046054
Shaffer D, Fisher P, Lucas CP, Dulcan MK, Schwab-
stone ME. NIMH diagnostic interview schedule for
children version IV (NIMH DISC-IV): Description,
differences from previous versions, and reliability of
some common diagnoses. Journal of the American
Academy of Child & Adolescent Psychiatry.
2000;39(1):28–38. https://doi.org/10.1097/00004583-
200001000-00014
Sheehan, D. V., Sheehan, K. H., Shytle, R. D., Janavs, J.,
Bannon, Y., Rogers, J. E., Milo, K. M., Stock, S. L., &
Wilkinson, B. (2010). Reliability and validity of the
mini international neuropsychiatric interview for chil-
dren and adolescents (MINI-KID). The Journal of
Clinical Psychiatry, 71(03|3), 313–326. https://doi.org/
10.4088/JCP.09m05305whi
Simmons, S., & Suárez, L. (2016). Substance abuse and
trauma. Child and Adolescent Psychiatric Clinics of
North America, 25(4), 723–734. https://doi.org/10.1016/
j.chc.2016.05.006
Sobell LC, Sobell MB. Timeline follow-back: A technique for
assessing self-reported alcohol consumption. In:
Measuring alcohol consumption: Psychosocial and bio-
chemical methods. Springer; 1992. p. 41–72.
Stein, M. B., Campbell-Sills, L., Gelernter, J., He, F., Heeringa, S.
G., Nock, M. K., Sampson, N. A., Sun, X., Jain, S., Kessler, R.
C., & Ursano, R. J. (2017). Alcohol misuse and co-occurring
mental disorders among new soldiers in the U.S. Army.
Alcoholism: Clinical and Experimental Research, 41(1),
139–148. https://doi.org/10.1111/acer.13269
Steinberg, A. M., Brymer, M. J., Kim, S., Briggs, E. C., Ippen,
C. G., Ostrowski, S. A., Gully, K. J., & Pynoos, R. S.
(2013). Psychometric properties of the UCLA PTSD
reaction index: Part I. Journal of Traumatic Stress,
26(1), 1–9. https://doi.org/10.1002/jts.21780
Swift, W., Wong, A., Li, K. M., Arnold, J. C., & McGregor, I.
S. (2013). Analysis of cannabis seizures in NSW,
Australia: Cannabis potency and cannabinoid profile.
PLoS One, 8(7), e70052. https://doi.org/10.1371/journal.
pone.0070052
Tripp, J. C., Worley, M. J., Straus, E., Angkaw, A. C., Trim,
R. S., & Norman, S. B. (2020). Bidirectional relationship
of posttraumatic stress disorder (PTSD) symptom sever-
ity and alcohol use over the course of integrated treat-
ment.. Psychology of Addictive Behaviors, 34(4), 506–
511. https://doi.org/10.1037/adb0000564
Tucker, J. S., Rodriguez, A., Davis, J. P., Klein, D. J., Amico,
D., & J, E. (2021). Simultaneous trajectories of alcohol
and cannabis use from adolescence to emerging adult-
hood: Associations with role transitions and functional
outcomes. Psychology of Addictive Behaviors, 35(6),
628–637. https://doi.org/10.1037/adb0000744
van Vliet, N. I., Huntjens, R. J. C., van Dijk, M. K., Bachrach,
N., Meewisse, M. L., & de Jongh, A. (2021). Phase-based
treatment versus immediate trauma-focused treatment
for post-traumatic stress disorder due to childhood
abuse: Randomised clinical trial. BJPsych Open, 7(6),
e211. https://doi.org/10.1192/bjo.2021.1057
Tanner JL, Arnett JJ. The emergence of emerging adulthood:
The new life stage between adolescence and young adult-
hood. In: Routledge handbook of youth and young adult-
hood. 2nd edn. Routledge; 2016. p. 50–56.
Skirbekk, V., Tamnes, C. K., Júlíusson, P. B., Jugessur, A., &
von Soest, T. (2025). Diverging trends in the age of social
and biological transitions to adulthood. Advances in Life
Course Research, 65, 100690. https://doi.org/10.1016/j.
alcr.2025.100690
Sawyer, S. M., Azzopardi, P. S., Wickremarathne, D., &
Patton, G. C. (2018). The age of adolescence. The
Lancet Child & Adolescent Health, 2(3), 223–228.
https://doi.org/10.1016/S2352-4642(18)30022-1
Twenge, J. M., & Park, H. (2019). The decline in adult activities
among U.S. adolescents, 1976-2016. Child Development,
90(2), 638–654. https://doi.org/10.1111/cdev.12930
Steinberg, A. M., Brymer, M. J., Decker, K. B., & Pynoos, R.
S. (2004). The University of California at Los Angeles
post-traumatic stress disorder reaction index. Current
Psychiatry Reports, 6(2), 96–100. https://doi.org/10.
1007/s11920-004-0048-2"""

test22 = """Adams, S., Houston-Kolnik, J., & Reichert, J. (2017, July 25).
Trauma-informed and evidence-based practices and pro-
grams to address trauma in correctional settings. Illinois
Criminal Justice Information Authority. https://icjia.
illinois.gov/researchhub/articles/trauma-informed-and-e
vidence-based-practices-and-programs-to-address-trau
ma-in-correctional-settings.
Anderson, J. D., Pitner, R. O., & Wooten, N. R. (2020). A
gender-specific model of trauma and victimization in
incarcerated women. Journal of Human Behavior in the
Social Environment, 30(2), 191–212. https://doi.org/10.
1080/10911359.2019.1673272
Ardino, V. (2012). Offending behaviour: The role of trauma
and PTSD. European Journal of Psychotraumatology, 3,
18968. https://doi.org/10.3402/ejpt.v3i0.18968
Ardino, V., Milani, L., & Di Blasio, P. (2013). PTSD and re-
offending risk: The mediating role of worry and a nega-
tive perception of other people’s support. European
Journal of Psychotraumatology, 4, 21382. https://doi.org/
10.3402/ejpt.v4i0.21382
Arora, I. H., Woscoboinik, G. G., Mokhtar, S., Quagliarini,
B., Bartal, A., Jagodnik, K. M., Barry, R. L., Edlow, A.
G., Orr, S. P., & Dekel, S. (2024). A diagnostic question-
naire for childbirth related posttraumatic stress disorder:
A validation study. American Journal of Obstetrics and
Gynecology, 231(1), 134.e1–134.e13. https://doi.org/10.
1016/j.ajog.2023.11.1229
Aurizki, G. E., & Wilson, I. (2022). Nurse-led task-shifting
strategies to substitute for mental health specialists in pri-
mary care: A systematic review. International Journal of
Nursing Practice, 28(5), e13046. https://doi.org/10.1111/
ijn.13046
Baker, D. E., Hill, M., Chamberlain, K., Hurd, L., Karlsson,
M., Zielinski, M., Calvert, M., & Bridges, A. J. (2021).
Interpersonal vs. Non-interpersonal cumulative traumas
and psychiatric symptoms in treatment-seeking
incarcerated women. Journal of Trauma & Dissociation:
The Official Journal of the International Society for the
Study of Dissociation (ISSD), 22(3), 249–264. https://doi.
org/10.1080/15299732.2020.1760172
Baranyi, G., Cassidy, M., Fazel, S., Priebe, S., & Mundt, A. P.
(2018). Prevalence of posttraumatic stress disorder in
prisoners. Epidemiologic Reviews, 40(1), 134–145.
https://doi.org/10.1093/epirev/mxx015
Bridges, A. J., Baker, D. E., Hurd, L. E., Chamberlain, K. D.,
Hill, M. A., Karlsson, M., & Zielinski, M. J. (2020). How
does timing affect trauma treatment for women Who Are
incarcerated? An empirical analysis. Criminal Justice and
Behavior, 47(6), 631–648. https://doi.org/10.1177/
0093854820903071
Briere, J., Agee, E., & Dietrich, A. (2016). Cumulative
trauma and current posttraumatic stress disorder status
in general population and inmate samples. Psychological
Trauma: Theory, Research, Practice and Policy, 8(4),
439–446. https://doi.org/10.1037/tra0000107
Brock, M. (2024, July 23). Mothers in prison and the cycle
of incarceration. Scholars Strategy Network. https://
scholars.org/contribution/mothers-prison-and-cycle-inc
arceration
Catani, C., Kohiladevy, M., Ruf, M., Schauer, E., Elbert, T., &
Neuner, F. (2009). Treating children traumatized by war
and tsunami: A comparison between exposure therapy
and meditation-relaxation in north-east Sri Lanka. BMC
Psychiatry, 9, 22. https://doi.org/10.1186/1471-244X-9-22
Department of Veterans Affairs (VA)/Department of Defense
(DoD), Management of Posttraumatic Stress Disorder and
Acute Stress Disorder Work Group. (2023). VA/DoD
clinical practice guideline for management of posttrau-
matic stress disorder and acute stress disorder. https://
www.healthquality.va.gov/guidelines/MH/ptsd/.
Dholakia, N. (2021, May 17). Women’s incarceration rates are
skyrocketing. These advocates are trying to change that.
Vera Institute of Justice. https://www.vera.org/news/
womens-incarceration-rates-are-skyrocketing.
Dickins, K. (2025). Ethical considerations for conducting
community-engaged research with women experiencing
homelessness and incarcerated women. Ethics &
Human Research, 47(1), 20–33. https://doi.org/10.1002/
eahr.60005
Dickins, K. A. (2024). Improving traumatic stress with jus-
tice-impacted women and women experiencing home-
lessness: A pilot study of narrative exposure therapy.
Issues in Mental Health Nursing, 45(2), 121–141.
https://doi.org/10.1080/01612840.2023.2238091
Dickins, K. A., Houlihan, M. C. K., Kim, A., Dixon, I., Reed,
M., & Karnik, N. S. (2025). Traumatic stress Among
women who are incarcerated: A community engaged
approach to determining needs and opportunities for
intervention. Journal of Health Care for the Poor and
Underserved, 36(1), 295–326. https://doi.org/10.1353/
hpu.2025.a951598
Dickins, K. A., Reed, M., Paun, O., Swanson, B., & Karnik,
N. S. (2023). Biopsychosocial model of traumatic stress
symptoms in women experiencing homelessness: A
qualitative descriptive study. Issues in Mental Health
Nursing, 44(6), 482–493. https://doi.org/10.1080/
01612840.2023.2205522
Ervin, S., Jagannath, J., Zweig, J., Willison, J. B., Jones, K. B.,
Maskolunas, K., Agha, C., & Cajarty, B. (2020).
Addressing trauma and victimization in women’s prisons:
Executive summary. Urban Institute. https://www.urban.
org/research/publication/addressing-trauma-and-victimi
zation-womens-prisons.
Facer-Irwin, E., Blackwood, N. J., Bird, A., Dickson, H.,
McGlade, D., Alves-Costa, F., & MacManus, D. (2019).
PTSD in prison settings: A systematic review and meta-
analysis of comorbid mental disorders and problematic
behaviours. PLoS One, 14(9), Article e0222407. https://
doi.org/10.1371/journal.pone.0222407
Fair, H., & Walmsley, R. (2025). World female imprisonment
list (6th ed.). Institute for Crime & Justice Policy
Research, Birkbeck, University of London. https://www.
prisonstudies.org/sites/default/files/resources/downloads/
world_female_imprisonment_list_6th_edition.pdf.
Fazel, S., Hayes, A. J., Bartellas, K., Clerici, M., & Trestman,
R. (2016). Mental health of prisoners: Prevalence, adverse
outcomes, and interventions. The Lancet. Psychiatry, 3(9),
871–881. https://doi.org/10.1016/S2215-0366(16)30142-0
Friedman, S. H., Tamburello, A. C., Kaempf, A., & Hall,
R. C. W. (2019). Prescribing for women in corrections.
The Journal of the American Academy of Psychiatry and
the Law, 47(4), 476–485. https://doi.org/10.29158/
JAAPL.003885-19
Gajewski-Nemes, J., & Messina, N. (2021). Exploring and
healing invisible wounds: Perceptions of trauma-specific
treatment from incarcerated men and women. Journal
of Trauma & Treatment, 10(5), 1–8.
Gibbons, R. D., Hedeker, D. R., & Davis, J. M. (1993).
Estimation of effect size from a series of experiments
involving paired comparisons. Journal of Educational
Statistics, 18(3), 271–279.
Gray, M. J., Litz, B. T., Hsu, J. L., & Lombardo, T. W. (2004).
Psychometric properties of the life events checklist.
Assessment, 11(4), 330–341. https://doi.org/10.1177/
1073191104269954
Gryczynski, J., McNeely, J., Wu, L. T., Subramaniam, G. A.,
Svikis, D. S., Cathers, L. A., Sharma, G., King, J., Jelstrom,
E., Nordeck, C. D., Sharma, A., Mitchell, S. G., O’Grady,
K. E., & Schwartz, R. P. (2017). Validation of the TAPS-1:
A four-item screening tool to identify unhealthy substance
use in primary care. Journal of General Internal Medicine,
32(9), 990–996. doi:10.1007/s11606-017-4079-x
Guina, J., Nahhas, R. W., Sutton, P., & Farnsworth, S.
(2018). The influence of trauma type and timing on
PTSD symptoms. The Journal of Nervous and Mental
Disease, 206(1), 72–76. https://doi.org/10.1097/NMD.
0000000000000730
Hamilton, C. M., Strader, L. C., Pratt, J. G., Maiese, D.,
Hendershot, T., Kwok, R. K., & Haines, J. (2011). The
PhenX toolkit: Get the most from your measures.
American Journal of Epidemiology, 174(3), 253–260.
https://doi.org/10.1093/aje/kwr193
Hijazi, A. M., Lumley, M. A., Ziadni, M. S., Haddad, L., Rapport,
L. J., & Arnetz, B. B. (2014). Brief narrative exposure therapy
for posttraumatic stress in Iraqi refugees: A preliminary ran-
domized clinical trial. Journal of Traumatic Stress, 27(3),
314–322. https://doi.org/10.1002/jts.21922
Ibrahim, B. (2015). Lay counselors experiences with coun-
seling their peers; the impact of being a lay counselor
and providing therapy to traumatized Sudanese refugees
in Cairo [Master’s Thesis, American University in Cairo].
https://fount.aucegypt.edu/etds/163.
Jeste, D. V., Palmer, B. W., Appelbaum, P. S., Golshan, S.,
Glorioso, D., Dunn, L. B., Kim, K., Meeks, T., &
Kraemer, H. C. (2007). A new brief instrument for asses-
sing decisional capacity for clinical research. Archives of
General Psychiatry, 64(8), 966–974. https://doi.org/10.
1001/archpsyc.64.8.966
Jones, M. S. (2020). Exploring coercive control, PTSD, and
the use of physical violence in the pre-prison heterosexual
relationships of incarcerated women. Criminal Justice
and Behavior, 47(10), 1299–1318. https://doi.org/10.
1177/0093854820920661
Kajstura, A., & Sawyer, W. (2024, March 5). Women’s
mass incarceration: The whole pie 2024. Prison Policy
Initiative. https://www.prisonpolicy.org/reports/pie2024
women.html.
Karlsson, M. E., Zielinski, M. J., & Bridges, A. J. (2020).
Replicating outcomes of survivors healing from abuse:
Recovery through exposure (SHARE): A brief exposure-
bassed group treatment for incarcerated survivors of sex-
ual violence. Psychological Trauma:Theory, Research,
Practice and Policy, 12(3), 300–305.
Karlsson, M. E., Zielinski, M. J., Calvert, M., & Bridges, A. J.
(2022). Decreases in psychiatric symptoms persist following
exposure-based group therapy for sexual violence victimi-
zation among incarcerated women. Psychological Services,
19(3), 534–540. https://doi.org/10.1037/ser0000570
Kehle-Forbes, S. M., Meis, L. A., Spoont, M. R., & Polusny,
M. A. (2016). Treatment initiation and dropout from pro-
longed exposure and cognitive processing therapy in a
VA outpatient clinic. Psychological Trauma : Theory,
Research, Practice and Policy, 8(1), 107–114. https://doi.
org/10.1037/tra0000065
Kelman, J., Gribble, R., Harvey, J., Palmer, L., & MacManus, D.
(2024). How does a history of trauma affect the experience
of imprisonment for individuals in women’s prisons: A
qualitative exploration. Women & Criminal Justice, 34(3),
171–191. https://doi.org/10.1080/08974454.2022.2071376
Killeen, T. K., Wen, C.-C., Neelon, B., & Baker, N. (2023).
Predictors of treatment completion among women
receiving integrated treatment for comorbid posttrau-
matic stress and substance use disorders. Substance Use
& Misuse, 58(4), 500–511. https://doi.org/10.1080/
10826084.2023.2170183
Kohler, R. E., Roncarati, J. S., Aguiar, A., Chatterjee, P., Gaeta,
J., Viswanath, K., & Henry, C. (2021). Trauma and cervical
cancer screening among women experiencing homeless-
ness: A call for trauma-informed care. Women’s Health,
17, 1–10. https://doi.org/10.1177/17455065211029238
Kroenke, K., Spitzer, R. L., & Williams, J. B. W. (2001). The
PHQ-9: Validity of a brief depression severity measure.
Journal of General Internal Medicine, 16(9), 606–613.
Maercker, A., Cloitre, M., Bachem, R., Schlumpf, Y. R.,
Khoury, B., Hitchcock, C., & Bohus, M. (2022).
Complex post–traumatic stress disorder. Lancet
(London, England), 400(10345), 60–72. https://doi.org/
10.1016/S0140-6736(22)00821-2
Malik, N., Facer-Irwin, E., Dickson, H., Bird, A., &
MacManus, D. (2023). The effectiveness of trauma-focused
interventions in prison settings: A systematic review and
meta-analysis. Trauma, Violence, & Abuse, 24(2), 844–
857. https://doi.org/10.1177/15248380211043890
Marx, B. P., Lee, D. J., Norman, S. B., Bovin, M. J., Sloan, D.
M., Weathers, F. W., Keane, T. M., & Schnurr, P. P.
(2022). Reliable and clinically significant change in the
Clinician-Administered PTSD Scale for DSM-5 and
PTSD Checklist for DSM-5 among male veterans.
Psychological Assessment, 34(2), 197–203. https://doi.
org/10.037/pas0001098
McLeod, K. E., Wong, K. A., Rajaratnam, S., Guyatt, P.,
DiPelino, S., Zaki, N., Akbari, H., Kerrigan, C., Jones,
R., Norris, E., Liauw, J., Butler, A., Kish, N., Plugge, E.,
Harriott, P., & Kouyoumdjian, F. G. (2025). Health con-
ditions among women in prisons: A systematic review.
The Lancet Public Health, 10(7), e609–e624. https://doi.
org/10.1016/S2468-2667(25)00092-1
National Council of State Boards of Nursing. (2026). Active
RN licenses: A profile of nursing licensure in the U.S.
https://www.ncsbn.org/active-rn-licenses.
National Institute of Justice. (2024, April 9). Five things to
know about women and reentry. https://nij.ojp.gov/topics/
articles/five-things-know-about-women-and-reentry.
Neuner, F., Catani, C., Ruf, M., Schauer, E., Schauer, M., &
Elbert, T. (2008). Narrative exposure therapy for the treat-
ment of traumatized children and adolescents (KidNET):
from neurocognitive theory to field intervention. Child
and Adolescent Psychiatric Clinics of North America,
17(3), 641–x. https://doi.org/10.1016/j.chc.2008.03.001
Neuner, F., Schauer, M., & Elbert, T. (2002). A narrative
exposure treatment as intervention in a refugee camp:
Two case reports. Behavioural and Cognitive
Psychotherapy, 30(2), 205–209.
Neuner, F., Schauer, M., Klaschik, C., Karunakara, U., &
Elbert, T. (2004). A comparison of narrative exposure
therapy, supportive counseling, and psychoeducation for
treating posttraumatic stress disorder in an African refugee
settlement. Journal of Consulting and Clinical Psychology,
72(4), 579–587. https://doi.org/10.1037/0022-006X.72.4.579
Olff, M., Langeland, W., Draijer, N., & Gersons, B. P. (2007).
Gender differences in posttraumatic stress disorder.
Psychological Bulletin, 133(2), 183–204. https://doi.org/
10.1037/0033-2909.133.2.183
Pettus, C. A. (2023). Trauma and prospects for reentry.
Annual Review of Criminology, 6, 423–446. https://doi.
org/10.1146/annurev-criminol-041122-111300
Piper, A., & Berle, D. (2019). The association between trauma
experienced during incarceration and PTSD outcomes: A
systematic review and meta-analysis. The Journal of
Forensic Psychiatry & Psychology, 30(5), 854–875. https://
doi.org/10.1080/14789949.2019.1639788
Quandt, K. R., & Jones, A. (2021, May 13). Research
roundup: Incarceration can cause lasting damage to men-
tal health. Prison Policy Initiative. https://www.
prisonpolicy.org/blog/2021/05/13/mentalhealthimpacts/.
Roberts, N. P., Kitchiner, N. J., Lewis, C. E., Downes, A. J., &
Bisson, J. I. (2021). Psychometric properties of the PTSD
checklist for DSM-5 in a sample of trauma exposed men-
tal health service users. European Journal of
Psychotraumatology, 12(1), 1863578. https://doi.org/10.
1080/20008198.2020.1863578
Robjant, K., & Fazel, M. (2010). The emerging evidence for
narrative exposure therapy: A review. Clinical Psychology
Review, 30(8), 1030–1039. https://doi.org/10.1016/j.cpr.
2010.07.004
Robjant, K., Koebach, A., Schmitt, S., Chibashimba, A.,
Carleial, S., & Elbert, T. (2019). The treatment of post-
traumatic stress symptoms and aggression in female for-
mer child soldiers using adapted narrative exposure
therapy—A RCT in Eastern Democratic Republic of
Congo. Behaviour Research and Therapy, 123, 103482.
https://doi.org/10.1016/j.brat.2019.103482
Saad, L. (2025). Americans’ ratings of U.S. professions stay his-
torically low. Gallup. https://news.gallup.com/poll/655106/
americans-ratings-professions-stay-historically-low.aspx.
Schauer, M., Neuner, F., & Elbert, T. (2025). Narrative
exposure therapy (NET) For survivors of traumatic stress
(3rd ed.). Hogrefe Publishing.
Shalev, N. (2009). From public to private care the historical
trajectory of medical services in a New York city jail.
American Journal of Public Health, 99(6), 988–995.
https://doi.org/10.2105/AJPH.2007.123265
Simon, L., Beckmann, D., Stone, M., Williams, R., Cohen,
M., & Tobey, M. (2020). Clinician experiences of care
provision in the correctional setting: A scoping review.
Journal of Correctional Health Care, 26(4), 301–314.
https://doi.org/10.1177/1078345820953154
Smith, J. R., Workneh, A., & Yaya, S. (2020). Barriers and
facilitators to help-seeking for individuals with posttraumatic
stress disorder: A systematic review. Journal of Traumatic
Stress, 33(2), 137–150. https://doi.org/10.1002/jts.22456
Smith, S., Muse, M. V., & Phillips, J. M. (2021). Addressing
moral distress in correctional nursing: A call to action.
Journal of Correctional Health Care, 27(2), 75–80.
https://doi.org/10.1089/jchc.20.04.0029
Spitzer, R. L., Kroenke, K., Williams, J. B. W., & Löwe, B.
(2006). A brief measure for assessing generalized anxiety
disorder: The GAD-7. Archives of Internal Medicine,
166(10), 1092–1097.
Strijk, P. J., Nijdam, M. J., Klaassens, E. R., Bedawi, V., De la
Rie, S., & Jongedijk, R. A. (2025). Feasibility and prelimi-
nary effectiveness of a highly intensive inpatient treat-
ment programme with narrative exposure therapy for
patients with posttraumatic stress disorder. Frontiers in
Psychology, 16, 1516144.
Strijk, P., Jongedijk, R. A., & Bedawi, V. (2020). A new treat-
ment approach for PTSD: High-intensive narrative
exposure therapy (HI-NET). Maltrattamento e abuso
all’infanzia, 22(3), 51–62.
Swavola, E., Riley, K., & Subramanian, R. (2016).
Overlooked: Women and jails in an era of reform. Vera
Institute of Justice. https://www.vera.org/publications/
overlooked-women-and-jails-report.
Szafranski, D. D., Snead, A., Allan, N. P., Gros, D. F.,
Killeen, T., Flanagan, J., Pericot-Valverde, I., & Back, S.
E. (2017). Integrated, exposure-based treatment for
PTSD and comorbid substance use disorders: Predictors
of treatment dropout. Addictive Behaviors, 73, 30–35.
https://doi.org/10.1016/j.addbeh.2017.04.005
Tripodi, S. J., Killian, M. O., Gilmour, M., Curley, E., &
Herod, L. (2022). Trauma-informed care groups with
incarcerated women: An alternative treatment design
comparing seeking safety and STAIR. Journal of the
Society for Social Work and Research, 13(3), 511–531.
https://doi.org/10.1086/712732
Turgoose, D., Ashwick, R., & Murphy, D. (2018). Systematic
review of lessons learned from delivering tele-therapy to
veterans with post-traumatic stress disorder. Journal of
Telemedicine and Telecare, 24(9), 575–585. https://doi.
org/10.1177/1357633X17730443
Wang, L. (2022). Both sides of the bars: How mass incarcera-
tion punishes families. Prison Policy Initiative. https://
www.prisonpolicy.org/blog/2022/08/11/parental_incarce
ration/.
Weathers, F. W., Blake, D. D., Schnurr, P. P., Kaloupek, D.
G., Marx, B. P., & Keane, T. M. (2013). The Life Events
Checklist for DSM-5 (LEC-5) –Standard. https://www.
ptsd.va.gov/professional/assessment/te-measures/life_ev
ents_checklist.asp.
Weathers, F. W., Litz, B. T., Keane, T. M., Palmieri, P. A.,
Marx, B. P., & Schnurr, P. P. (2013). The PTSD Checklist
for DSM-5 (PCL-5) – Standard. https://www.ptsd.va.gov/
professional/assessment/adult-sr/ptsd-checklist.asp.
Wilkins C. H. (2018). Effective engagement requires trust and
being trustworthy. Medical Care, 56 Suppl 1(10 Suppl 1),
S6–S8. https://doi.org/10.1097/MLR.0000000000000953
Zhong, S., Zhu, X., Mellsop, G., Zhou, J., & Wang, X. (2021).
Correlates of presence and remission of post-trauma
stress disorder in incarcerated women: A case-control
study design. Frontiers in Psychiatry, 12, Article 748518.
https://doi.org/10.3389/fpsyt.2021.748518"""

test23 = """Alisic, E., Zalta, A. K., van Wesel, F., Larsen, S. E., Hafstad, G.
S., Hassanpour, K., & Smid, G. E. (2014). Rates of post-
traumatic stress disorder in trauma-exposed children and
adolescents: Meta-analysis. British Journal of Psychiatry,
204(5), 335–340. https://doi.org/10.1192/bjp.bp.113.131227
Australian Institute of Health and Welfare (AIHW). (2025). Alcohol, tobacco & other drugs in
Australia, Younger people.[cited 2025 Aug 18] Available from: https://www.
aihw.gov.au/reports/alcohol/alcohol-tobacco-other-
drugs-australia/contents/priority-populations/younger-
people
Back, S. E., Brady, K. T., Sonne, S. C., & Verduin, M. L.
(2006). Symptom improvement in co-occurring PTSD
and alcohol dependence. Journal of Nervous & Mental
Disease, 194(9), 690–696. https://doi.org/10.1097/01.
nmd.0000235794.12794.8a
Back, S. E., Killeen, T., Badour, C. L., Flanagan, J. C., Allan, N.
P., Ana, E. S., Lozano, B., Foa, E.B., & Brady, K. T. (2019).
Concurrent treatment of substance use disorders and
PTSD using prolonged exposure: A randomized clinical
trial in military veterans. Addictive Behaviors, 90, 369–
377. https://doi.org/10.1016/j.addbeh.2018.11.032
Back, S. E., Killeen, T., Foa, E. B., Santa Ana, E. J., Gros, D.
F., & Brady, K. T. (2012). Use of an integrated therapy
with prolonged exposure to treat PTSD and comorbid
alcohol dependence in an Iraq veteran. American
Journal of Psychiatry, 169(7), 688–691. https://doi.org/
10.1176/appi.ajp.2011.11091433
Back, S. E., Killeen, T. K., Teer, A. P., Hartwell, E. E.,
Federline, A., Beylotte, F., & Cox, E. (2014). Substance
use disorders and PTSD: An exploratory study of treat-
ment preferences among military veterans. Addictive
Behaviors, 39(2), 369–373. https://doi.org/10.1016/j.
addbeh.2013.09.017
Badour, C. L., Flanagan, Julianne C., Allan, N. P., Gilmore,
A. K., Gros, D. F., Killeen, T., Korte, K. J., Brown Delisa
G., Kolnogorova, K., & Back, S. E. (2022). Temporal
dynamics of symptom change among veterans receiving
an integrated treatment for posttraumatic stress disorder
and substance use disorders. Journal of Traumatic Stress,
35(2), 546–558. https://doi.org/10.1002/jts.22769
Barrett, E. L., Teesson, M., & Mills, K. L. (2014).
Associations between substance use, post-traumatic stress
disorder and the perpetration of violence: A longitudinal
investigation. Addictive Behaviors, 39(6), 1075–1080.
https://doi.org/10.1016/j.addbeh.2014.03.003
Basedow, L. A., Kuitunen-Paul, S., Roessner, V., & Golub, Y.
(2020). Traumatic events and substance use disorders in
adolescents. Frontiers in Psychiatry, 11, 559. https://doi.
org/10.3389/fpsyt.2020.00559
Blanco, C., Xu, Y., Brady, K., Pérez-Fuentes, G., Okuda, M.,
& Wang, S. (2013). Comorbidity of posttraumatic stress
disorder with alcohol dependence among US adults:
Results from national epidemiological survey on alcohol
and related conditions. Drug and Alcohol Dependence,
132(3), 630–638. https://doi.org/10.1016/j.drugalcdep.
2013.04.016
Borah, E. V., Holder, N., & Chen, K. (2017). Providers’ use
of evidence-based treatments for posttraumatic stress dis-
order: The influence of training, attitudes, and barriers in
military and private treatment settings. Best Practices in
Mental Health, 13(1), 34–46. https://doi.org/10.70256/
997168psfxuw
Brady, K. T., & Back, S. E. (2012). Childhood trauma, post-
traumatic stress disorder, and alcohol dependence.
Alcohol Research: Current Reviews, 34(4), 408–413.
https://doi.org/10.35946/arcr.v34.4.05
Brady, K. T., Dansky, B. S., Back, S. E., Foa, E. B., & Carroll,
K. M. (2001). Exposure therapy in the treatment of PTSD
among cocaine-dependent individuals. Journal of
Substance Abuse Treatment, 21(1), 47–54. https://doi.
org/10.1016/S0740-5472(01)00182-9
Callaghan, R. C., Sanches, M., Benny, C., Stockwell, T.,
Sherk, A., & Kish, S. J. (2019). Who consumes most of
the cannabis in Canada? Profiles of cannabis consump-
tion by quantity. Drug and Alcohol Dependence, 205,
107587. https://doi.org/10.1016/j.drugalcdep.2019.
107587
Castro-Schilo, L., & Grimm, K. (2018). Using residualized
change versus difference scores for longitudinal research.
Journal of Social and Personal Relationships, 35(1), 32–58.
https://doi.org/10.1177/0265407517718387
Danielson, C. K., Adams, Z., McCart, M. R., Chapman, J. E.,
Sheidow, A. J., Walker, J., Smalling, A., & d Arellano,
M. A. (2020). Safety and efficacy of exposure-based risk
reduction through family therapy for co-occurring sub-
stance use problems and posttraumatic stress disorder
symptoms among adolescents. JAMA Psychiatry, 77(6),
574–586. https://doi.org/10.1001/jamapsychiatry.2019.
4803
Darnell, D., Flaster, A., Hendricks, K., Kerbrat, A., &
Comtois, K. A. (2019). Adolescent clinical populations
and associations between trauma and behavioral and
emotional problems. Psychological Trauma: Theory,
Research, Practice, and Policy, 11(3), 266–273. https://
doi.org/10.1037/tra0000371
Dawson, D., Stjepanovic, D., Lorenzetti, V., Hall, W. D., &
Leung, J. (2024). How much cannabis is used in a joint
in Australia? An experimental investigation into use by
potency and frequency. Drug and Alcohol Dependence,
43(1), 226–232.
Deacon, B. J., Farrell, N. R., Kemp, J. J., Dixon, L. J., Sy, J. T.,
Zhang, A. R., & McGrath, P. B. (2013). Assessing thera-
pist reservations about exposure therapy for anxiety dis-
orders: The therapist beliefs about exposure scale.
Journal of Anxiety Disorders, 27(8), 772–780. https://
doi.org/10.1016/j.janxdis.2013.04.006
Dube, S. R., Anda, R. F., Felitti, V. J., Chapman, D. P.,
Williamson, D. F., & Giles, W. H. (2001). Childhood
abuse, household dysfunction, and the risk of attempted
suicide throughout the life span. JAMA, 286(24), 3089–
3096. https://doi.org/10.1001/jama.286.24.3089
Ehlers, A., Bisson, J., Clark, D. M., Creamer, M., Pilling, S.,
Richards, D., Shnurr, P. P., Turner, S., & Yule, W. (2010).
Do all psychological treatments really work the same in
posttraumatic stress disorder? Clinical Psychology
Review, 30(2), 269–276. https://doi.org/10.1016/j.cpr.
2009.12.001
Freeman, T. P., & Lorenzetti, V. (2020). ‘Standard THC
units’: A proposal to standardize dose across all cannabis
products and methods of administration. Addiction,
115(7), 1207–1216. https://doi.org/10.1111/add.14842
Gielen, N., Havermans, R. C., Tekelenburg, M., & Jansen, A.
(2012). Prevalence of post-traumatic stress disorder among
patients with substance use disorder: It is higher than clin-
icians think it is. European Journal of Psychotraumatology,
3(1), 17734. https://doi.org/10.3402/ejpt.v3i0.17734
Gielen, N., Krumeich, A., Tekelenburg, M., Nederkoorn, C.,
& Havermans, R. C. (2016). How patients perceive the
relationship between trauma, substance abuse, craving,
and relapse: A qualitative study. Journal of Substance
Use, 21(5), 466–470. https://doi.org/10.3109/14659891.
2015.1063717
Gilhooly, T., Bergman, A. J., Stieber, J., & Brown, E. J.
(2018). Posttraumatic stress disorder symptoms, family
environment, and substance abuse symptoms in emer-
ging adults. Journal of Child & Adolescent Substance
Abuse, 27(3), 196–209. https://doi.org/10.1080/
1067828X.2018.1446861
Gunsolley, J. C., Getchell, C., & Chinchilli, V. M. (1995).
Small sample characteristics of generalized estimating
equations. Communications in Statistics - Simulation
and Computation, 24(4), 869–878. https://doi.org/10.
1080/03610919508813280
Hall, W. D., Patton, G., Stockings, E., Weier, M., Lynskey,
M., Morley, K. I., & Degenhardt, L. (2016). Why young
people’s substance use matters for global health. The
Lancet Psychiatry, 3(3), 265–279. https://doi.org/10.
1016/S2215-0366(16)00013-4
Hawn, S. E., Cusack, S. E., & Amstadter, A. B. (2020). A sys-
tematic review of the self-medication hypothesis in the
context of posttraumatic stress disorder and comorbid
problematic alcohol Use. Journal of Traumatic Stress,
33(5), 699–708. https://doi.org/10.1002/jts.22521
Hien, D. A., Gette, J. A., Blakey, S. M., Piccirillo, M. L., Back,
S. E., Bauer, A. G., Ebrahimi, C .T., Ellis, R. A., Killen, T.
K., Lehinger, E. A., Lopez-Castro, T., Norman, S. B.,
Ruglass, L. M., Saraiya, T. C., Saavedra, L. M., &
Morgan-López, A. A. (2025). How changes in post-trau-
matic stress disorder (PTSD) severity mediate substance
use disorder (SUD) severity during and after treatment
for co-occurring PTSD and SUD: Results from project
harmony. Addiction, 120(11), 2245–2257. https://doi.
org/10.1111/add.70126
Hien, D. A., Jiang, H., Campbell, A. N., Hu, M. C., Miele, G.
M., Cohen, L. R., Brigham, G. S., Capstick, C., Kulaga, A.,
Robinson, J., & Suarez-Morales, L. (2010). Do treatment
improvements in PTSD severity affect substance use out-
comes? A secondary analysis from a randomized clinical
trial in NIDA’s clinical trials network. American Journal
of Psychiatry, 167(1), 95–101. https://doi.org/10.1176/
appi.ajp.2009.09091261
Hien, D. A., Papini, S., Saavedra, L. M., Bauer, A. G.,
Ruglass, L. M., Ebrahimi, C. T., Fitzpatrick, S., López-
Castro, T., Norman, S. B., Killeen, T. K., Back, S. E., &
Morgan-López, A. A. (2024). Project harmony: A sys-
tematic review and network meta-analysis of psychother-
apy and pharmacologic trials for comorbid posttraumatic
stress, alcohol, and other drug use disorders.
Psychological Bulletin, 150(3), 319–353. https://doi.org/
10.1037/bul0000409
Hien, D. A., Smith, K. Z., Owens, M., López-Castro, T.,
Ruglass, L. M., & Papini, S. (2018). Lagged effects of sub-
stance use on PTSD severity in a randomized controlled
trial with modified prolonged exposure and relapse pre-
vention. Journal of Consulting and Clinical Psychology,
86(10), 810–819. https://doi.org/10.1037/ccp0000345
Hien, D. A., Wells, E. A., Jiang, H., Suarez-Morales, L.,
Campbell, A. N., Cohen, L. R., Miele, G. M., Killeen, T.,
Brigham, G. S., Zhang, Y., & Hansen, C. (2009).
Multisite randomized trial of behavioral interventions
for women with co-occurring PTSD and substance use
disorders. Journal of Consulting and Clinical Psychology,
77(4), 607–619. https://doi.org/10.1037/a0016227
Kaczkurkin, A. N., Asnaani, A., Alpert, E., & Foa, E. B.
(2016). The impact of treatment condition and the lagged
effects of PTSD symptom severity and alcohol use on
changes in alcohol craving. Behaviour Research and
Therapy, 79, 7–14. https://doi.org/10.1016/j.brat.2016.
02.001
Kaplow, J. B., Rolon-Arroyo, B., Layne, C. M., Rooney, E.,
Oosterhoff, B., Hill, R., Steinberg, A. M., Lotterman, J.,
Gallagher, K. A., & Pynoos, R. S. (2020). Validation of
the UCLA PTSD reaction index for DSM-5: A develop-
mentally informed assessment tool for youth. Journal of
the American Academy of Child & Adolescent
Psychiatry, 59(1), 186–194. https://doi.org/10.1016/j.
jaac.2018.10.019
Kay-Lambkin, F. J., Baker, A. L., Kelly, B., & Lewin, T. J.
(2011). Clinician-assisted computerised versus thera-
pist-delivered treatment for depressive and addictive dis-
orders: A randomised controlled trial. Medical Journal of
Australia, 195(S3), S44–S50. https://doi.org/10.5694/j.
1326-5377.2011.tb03265.x
Kazdin, A. E. (2009). Understanding how and why psy-
chotherapy leads to change. Psychotherapy Research,
19(4-5), 418–428. https://doi.org/10.1080/1050330080
2448899
Knight, J. R., Shrier, L. A., Bravender, T. D., Farrell, M., Bilt,
V., Shaffer, J., & J, H. (1999). A new brief screen for ado-
lescent substance abuse. Archives of Pediatrics &
Adolescent Medicine, 153(6), 591–596. https://doi.org/
10.1001/archpedi.153.6.591
Laurenceau, J. P., Hayes, A. M., & Feldman, G. C. (2007).
Some methodological and statistical issues in the study
of change processes in psychotherapy. Clinical
Psychology Review, 27(6), 682–695. https://doi.org/10.
1016/j.cpr.2007.01.007
Liang, K. Y., & Zeger, S. (1986). Longitudinal data analysis
using generalized linear models. Biometrika, 73(1), 13–
22. https://doi.org/10.1093/biomet/73.1.13
Mancl, L. A., & DeRouen, T. A. (2001). A covariance estima-
tor for GEE with improved small-sample properties.
Biometrics, 57(1), 126–134. https://doi.org/10.1111/j.
0006-341X.2001.00126.x
Martin, G., & Copeland, J. (2008). The adolescent cannabis
check-up: Randomized trial of a brief intervention for
young cannabis users. Journal of Substance Abuse
Treatment, 34(4), 407–414. https://doi.org/10.1016/j.jsat.
2007.07.004
McGovern, M. P., Lambert-Harris, C., Acquilano, S., Xie,
H., Alterman, A. I., & Weiss, R. D. (2009). A cognitive
behavioral therapy for co-occurring substance use and
posttraumatic stress disorders. Addictive Behaviors,
34(10), 892–897. https://doi.org/10.1016/j.addbeh.2009.
03.009
McLaughlin, K. A., Koenen, K. C., Hill, E. D., Petukhova,
M., Sampson, N. A., Zaslavsky, A. M., & Kessler, R. C.
(2013). Trauma exposure and posttraumatic stress dis-
order in a national sample of adolescents. Journal of the
American Academy of Child & Adolescent Psychiatry,
52(8), 815–830.e14. https://doi.org/10.1016/j.jaac.2013.
05.011
Mefodeva, V., Carlyle, M., Walter, Z., & Hides, L. (2023).
Client and staff perceptions of the integration of trauma
informed care and specialist posttraumatic stress disorder treatment in residential treatment facilities for substance
use: A qualitative study. Drug and Alcohol Dependence,
42(1), 181–192.
Meyer, J. M., Farrell, N. R., Kemp, J. J., Blakey, S. M., &
Deacon, B. J. (2014). Why do clinicians exclude anxious
clients from exposure therapy? Behaviour Research and
Therapy, 54, 49–53. https://doi.org/10.1016/j.brat.2014.
01.004
Miles, S. R., Hale, W. J., Mintz, J., Wachen, J. S., Litz, B. T.,
Dondanville, K. A., Yarvis, J. S., Hembree, E. A., Young-
McCaughan, S., Peterson, A. L., & Resick, P. A. (2023).
Hyperarousal symptoms linger after successful PTSD
treatment inactive duty military. Psychological Trauma:
Theory, Research, Practice, AndPolicy, 15(8), 1398–1405.
https://doi.org/10.1037/tra0001292
Mills, K. L., Barrett, E., Back, S. E., Cobham, V. E., Bendall,
S., Perrin, S., Brady, K. T., Ross, J., Peach, N., Kihas, I., &
Cassar, J. (2020). Randomised controlled trial of inte-
grated trauma-focused psychotherapy for traumatic
stress and substance use among adolescents: Trial proto-
col. BMJ Open, 10(11), e043742. https://doi.org/10.1136/
bmjopen-2020-043742
Mills, K. L., Peach, N., Dobinson, K. A., Kihas, I., Cassar, J.
Isik, A., Bezzina, L., Schollar-Root, O., Cobham, V.E.,
Barrett, E.L. Perrin, S., Back, S.E., Brady, K., Milne, B.,
& Teesson, M. (n.d.) Integrated exposure-based therapy for
co-occurring post-traumatic stress and substance use
among young people: A randomized controlled Trial
(in preparation).
Mills, K. L., Teesson, M., Back, S. E., Brady, K. T., Baker, A.
L., Hopwood, S., Sannibale, C., Barrett, E. L., Merz, S.,
Rosenfeld, J., & Ewer, P. L. (2012). Integrated exposure-
based therapy for co-occurring posttraumatic stress dis-
order and substance dependence. JAMA, 308(7), 690–
699. https://doi.org/10.1001/jama.2012.9071
Murray, H., Grey, N.,Warnock-Parkes, E., Kerr, A.,Wild, J.,
Clark, D. M., & Ehlers, A. (2022). Ten misconceptions
about trauma-focused CBT for PTSD. The Cognitive
Behaviour Therapist, 15, e33. https://doi.org/10.1017/
S1754470X22000307
Nader, K., Kriegler, K. A., Blake, D. D., Pynoos, R. S.,
Newman, E., & Weathers, F. W. (2013). Clinician-administered
PTSD scale for children and adolescents [Internet].
2013 [cited 2025 Jun 14]. Available from: https://doi.
apa.org/doi/10.1037t08962-000
National Health and Medical Research Council. (2020).
Australian Guidelines to Reduce Health Risks from
Drinking Alcohol [Internet]. Canberra: Commonwealth
of Australia; 2020 [cited 2025 Sep 24]. Available from:
https://www.nhmrc.gov.au/about-us/publications/
australian-guidelines-reduce-health-risks-drinking-
alcohol#block-views-block-file-attachments-content-
block-1
Nooner, K. B., Linares, L. O., Batinjane, J., Kramer, R. A.,
Silva, R., & Cloitre, M. (2012). Factors related to posttrau-
matic stress disorder in adolescence. Trauma, Violence, &
Abuse, 13(3), 153–166. https://doi.org/10.1177/
1524838012447698
Norman, S. B., Haller, M., Hamblen, J. L., Southwick, S. M.,
& Pietrzak, R. H. (2018). The burden of co-occurring
alcohol use disorder and PTSD in U.S. Military veterans:
Comorbidities, functioning, and suicidality.. Psychology
of Addictive Behaviors, 32(2), 224–229. https://doi.org/
10.1037/adb0000348
Oprel, D. A., Hoeboer, C. M., Schoorl, M., Kleine, R. A. D., Cloitre, M., Wigard, I. G., ... & van der Does, W. (2021). Effect of prolonged exposure, intensified prolonged exposure and STAIR+ prolonged exposure in patients with PTSD related to childhood abuse: A randomized controlled trial. European journal of psychotraumatology, 12(1), 1851511. https://doi.org/10.1080/20008198.2020.1851511
Ouimette, P., Goodwin, E., & Brown, P. J. (2006). Health
and well being of substance use disorder patients with
and without posttraumatic stress disorder. Addictive
Behaviors, 31(8), 1415–1423. https://doi.org/10.1016/j.
addbeh.2005.11.010
Ouimette, P., Read, J. P., Wade, M., & Tirone, V. (2010).
Modeling associations between posttraumatic stress
symptoms and substance use. Addictive Behaviors,
35(1), 64–67. https://doi.org/10.1016/j.addbeh.2009.08.
009
Patrick ME, Miech RA, Johnston LD, O’Malley PM. (2024).
Monitoring the Future Panel Study annual report:
national data on substance use among adults ages 19 to
65, 1976–2023 [Internet]. Arbor (MI): Institute for
Social Research; 2024 [cited 2025 Aug 18]. Available
from: https://monitoringthefuture.org/mtfpanelvol2/
Peach, N., Kihas, I., Isik, A., Cassar, J., Barrett, E. L., Cobham, V., ... & Mills, K. L. (2024). Clinical characteristics of adolescents and emerging adults presenting for integrated posttraumatic stress and substance use treatment. Advances in Dual Diagnosis, 17(2), 54-71. https://doi.org/10.1108/ADD-11-
2023-0021
Peirce, J. M., Schacht, R. L., & Brooner, R. K. (2020). The
effects of prolonged exposure on substance use in patients
with posttraumatic stress disorder and substance use dis-
orders. Journal of Traumatic Stress, 33(4), 465–476.
https://doi.org/10.1002/jts.22546
Renaud, F., Jakubiec, L., Swendsen, J., & Fatseas, M. (2021).
The impact of Co-occurring post-traumatic stress dis-
order and substance use disorders on craving: A systema-
tic review of the literature. Frontiers in Psychiatry, 12.
Roberts, N. P., Roberts, P. A., Jones, N., & Bisson, J. I.
(2016). Psychological therapies for post-traumatic stress
disorder and comorbid substance use disorder.
Cochrane Database of Systematic Reviews, 2016(4).
https://doi.org/10.1002/14651858.CD010204.pub2
Robinson, L. D., & Deane, F. P. (2022). Substance use dis-
order and anxiety, depression, eating disorder, PTSD,
and phobia comorbidities among individuals attending
residential substance use treatment settings. Journal of
Dual Diagnosis, 18(3), 165–176. https://doi.org/10.1080/
15504263.2022.2090648
Rodriguez L, Jenzer T, Read JP. (2019). Physical and mental health
and other functional outcomes in co-occurring PTSD and
substance use disorders. In: Posttraumatic stress and sub-
stance use disorders. Routledge; 2019.
Ruglass, L. M., Gette, J. A., Morgan-López, A. A., Ye, A.,
Smith, K. Z., Fitzpatrick, S., López-Castro, T., Saavedra,
L. M., Norman, S. B., Killeen, T. K., & Back, S. E.
(2025). Indirect effects of seeking safety plus sertraline
on alcohol use: The mediating role of reductions in post-
traumatic stress disorder symptom severity. Journal of
Traumatic Stress, 1–10.
Ruglass, L. M., Lopez-Castro, T., Papini, S., Killeen, T., Back, S. E., & Hien, D. A. (2017). Concurrent treatment with prolonged exposure for co-occurring full or subthreshold posttraumatic stress disorder and substance use disorders: A randomized clinical trial. Psychotherapy and psychosomatics, 86(3), 150-161. https://doi.org/10.1159/000462977
Saunders, B. E., & Adams, Z. W. (2014). Epidemiology of
traumatic experiences in childhood. Child and
Adolescent Psychiatric Clinics of North America, 23(2),
167–184. https://doi.org/10.1016/j.chc.2013.12.003
Schollar-Root, O., Cassar, J., Peach, N., Cobham, V. E.,
Milne, B., Barrett, E., Back, S. E., Bendall, S., Perrin, S.,
Brady, K., Ross, J., Teesson, M., Kihas, I., Dobinson, K.
A., & Mills, K. L. (2022). Integrated trauma-focused psy-
chotherapy for traumatic stress and substance use: Two
adolescent case studies. Clinical Case Studies, 21(3),
192–208. https://doi.org/10.1177/15346501211046054
Shaffer, D., Fisher, P., Lucas, C. P., Dulcan, M. K., & Schwab-Stone, M. E. (2000). NIMH Diagnostic Interview Schedule for Children Version IV (NIMH DISC-IV): Description, differences from previous versions, and reliability of some common diagnoses. Journal of the American Academy of Child & Adolescent Psychiatry, 39(1), 28-38. https://doi.org/10.1097/00004583-200001000-00014
Sheehan, D. V., Sheehan, K. H., Shytle, R. D., Janavs, J.,
Bannon, Y., Rogers, J. E., Milo, K. M., Stock, S. L., &
Wilkinson, B. (2010). Reliability and validity of the
mini international neuropsychiatric interview for chil-
dren and adolescents (MINI-KID). The Journal of
Clinical Psychiatry, 71(03|3), 313–326. https://doi.org/
10.4088/JCP.09m05305whi
Simmons, S., & Suárez, L. (2016). Substance abuse and
trauma. Child and Adolescent Psychiatric Clinics of
North America, 25(4), 723–734. https://doi.org/10.1016/
j.chc.2016.05.006
Sobell LC, Sobell MB. (1992). Timeline follow-back: A technique for
assessing self-reported alcohol consumption. In:
Measuring alcohol consumption: Psychosocial and bio-
chemical methods. Springer; 1992. p. 41–72.
Stein, M. B., Campbell-Sills, L., Gelernter, J., He, F., Heeringa, S.
G., Nock, M. K., Sampson, N. A., Sun, X., Jain, S., Kessler, R.
C., & Ursano, R. J. (2017). Alcohol misuse and co-occurring
mental disorders among new soldiers in the U.S. Army.
Alcoholism: Clinical and Experimental Research, 41(1),
139–148. https://doi.org/10.1111/acer.13269
Steinberg, A. M., Brymer, M. J., Kim, S., Briggs, E. C., Ippen,
C. G., Ostrowski, S. A., Gully, K. J., & Pynoos, R. S.
(2013). Psychometric properties of the UCLA PTSD
reaction index: Part I. Journal of Traumatic Stress,
26(1), 1–9. https://doi.org/10.1002/jts.21780
Swift, W., Wong, A., Li, K. M., Arnold, J. C., & McGregor, I.
S. (2013). Analysis of cannabis seizures in NSW,
Australia: Cannabis potency and cannabinoid profile.
PLoS One, 8(7), e70052. https://doi.org/10.1371/journal.
pone.0070052
Tripp, J. C., Worley, M. J., Straus, E., Angkaw, A. C., Trim,
R. S., & Norman, S. B. (2020). Bidirectional relationship
of posttraumatic stress disorder (PTSD) symptom sever-
ity and alcohol use over the course of integrated treat-
ment. Psychology of Addictive Behaviors, 34(4), 506–
511. https://doi.org/10.1037/adb0000564
Tucker, J. S., Rodriguez, A., Davis, J. P., Klein, D. J., Amico,
D., & J, E. (2021). Simultaneous trajectories of alcohol
and cannabis use from adolescence to emerging adult-
hood: Associations with role transitions and functional
outcomes. Psychology of Addictive Behaviors, 35(6),
628–637. https://doi.org/10.1037/adb0000744
van Vliet, N. I., Huntjens, R. J. C., van Dijk, M. K., Bachrach,
N., Meewisse, M. L., & de Jongh, A. (2021). Phase-based
treatment versus immediate trauma-focused treatment
for post-traumatic stress disorder due to childhood
abuse: Randomised clinical trial. BJPsych Open, 7(6),
e211. https://doi.org/10.1192/bjo.2021.1057
Tanner JL, Arnett JJ. (2016). The emergence of emerging adulthood:
The new life stage between adolescence and young adult-
hood. In: Routledge handbook of youth and young adult-
hood. 2nd edn. Routledge; 2016. p. 50–56.
Skirbekk, V., Tamnes, C. K., Júlíusson, P. B., Jugessur, A., &
von Soest, T. (2025). Diverging trends in the age of social
and biological transitions to adulthood. Advances in Life
Course Research, 65, 100690. https://doi.org/10.1016/j.
alcr.2025.100690
Sawyer, S. M., Azzopardi, P. S., Wickremarathne, D., &
Patton, G. C. (2018). The age of adolescence. The
Lancet Child & Adolescent Health, 2(3), 223–228.
https://doi.org/10.1016/S2352-4642(18)30022-1
Twenge, J. M., & Park, H. (2019). The decline in adult activities
among U.S. adolescents, 1976-2016. Child Development,
90(2), 638–654. https://doi.org/10.1111/cdev.12930
Steinberg, A. M., Brymer, M. J., Decker, K. B., & Pynoos, R.
S. (2004). The University of California at Los Angeles
post-traumatic stress disorder reaction index. Current
Psychiatry Reports, 6(2), 96–100. https://doi.org/10.
1007/s11920-004-0048-2"""

test24 = """Adams, S., Houston-Kolnik, J., & Reichert, J. (2017, July 25).
Trauma-informed and evidence-based practices and pro-
grams to address trauma in correctional settings. Illinois
Criminal Justice Information Authority. https://icjia.
illinois.gov/researchhub/articles/trauma-informed-and-e
vidence-based-practices-and-programs-to-address-trau
ma-in-correctional-settings.
Anderson, J. D., Pitner, R. O., & Wooten, N. R. (2020). A
gender-specific model of trauma and victimization in
incarcerated women. Journal of Human Behavior in the
Social Environment, 30(2), 191–212. https://doi.org/10.
1080/10911359.2019.1673272
Ardino, V. (2012). Offending behaviour: The role of trauma
and PTSD. European Journal of Psychotraumatology, 3,
18968. https://doi.org/10.3402/ejpt.v3i0.18968
Ardino, V., Milani, L., & Di Blasio, P. (2013). PTSD and re-
offending risk: The mediating role of worry and a nega-
tive perception of other people’s support. European
Journal of Psychotraumatology, 4, 21382. https://doi.org/
10.3402/ejpt.v4i0.21382
Arora, I. H., Woscoboinik, G. G., Mokhtar, S., Quagliarini,
B., Bartal, A., Jagodnik, K. M., Barry, R. L., Edlow, A.
G., Orr, S. P., & Dekel, S. (2024). A diagnostic question-
naire for childbirth related posttraumatic stress disorder:
A validation study. American Journal of Obstetrics and
Gynecology, 231(1), 134.e1–134.e13. https://doi.org/10.
1016/j.ajog.2023.11.1229
Aurizki, G. E., & Wilson, I. (2022). Nurse-led task-shifting
strategies to substitute for mental health specialists in pri-
mary care: A systematic review. International Journal of
Nursing Practice, 28(5), e13046. https://doi.org/10.1111/
ijn.13046
Baker, D. E., Hill, M., Chamberlain, K., Hurd, L., Karlsson,
M., Zielinski, M., Calvert, M., & Bridges, A. J. (2021).
Interpersonal vs. Non-interpersonal cumulative traumas
and psychiatric symptoms in treatment-seeking
incarcerated women. Journal of Trauma & Dissociation:
The Official Journal of the International Society for the
Study of Dissociation (ISSD), 22(3), 249–264. https://doi.
org/10.1080/15299732.2020.1760172
Baranyi, G., Cassidy, M., Fazel, S., Priebe, S., & Mundt, A. P.
(2018). Prevalence of posttraumatic stress disorder in
prisoners. Epidemiologic Reviews, 40(1), 134–145.
https://doi.org/10.1093/epirev/mxx015
Bridges, A. J., Baker, D. E., Hurd, L. E., Chamberlain, K. D.,
Hill, M. A., Karlsson, M., & Zielinski, M. J. (2020). How
does timing affect trauma treatment for women Who Are
incarcerated? An empirical analysis. Criminal Justice and
Behavior, 47(6), 631–648. https://doi.org/10.1177/
0093854820903071
Briere, J., Agee, E., & Dietrich, A. (2016). Cumulative
trauma and current posttraumatic stress disorder status
in general population and inmate samples. Psychological
Trauma: Theory, Research, Practice and Policy, 8(4),
439–446. https://doi.org/10.1037/tra0000107
Brock, M. (2024). Mothers in prison and the cycle
of incarceration. Scholars Strategy Network. https://
scholars.org/contribution/mothers-prison-and-cycle-inc
arceration
Catani, C., Kohiladevy, M., Ruf, M., Schauer, E., Elbert, T., &
Neuner, F. (2009). Treating children traumatized by war
and tsunami: A comparison between exposure therapy
and meditation-relaxation in north-east Sri Lanka. BMC
Psychiatry, 9, 22. https://doi.org/10.1186/1471-244X-9-22
Department of Veterans Affairs (VA)/Department of Defense
(DoD), Management of Posttraumatic Stress Disorder and
Acute Stress Disorder Work Group. (2023). VA/DoD
clinical practice guideline for management of posttrau-
matic stress disorder and acute stress disorder. https://
www.healthquality.va.gov/guidelines/MH/ptsd/.
Dholakia, N. (2021, May 17). Women’s incarceration rates are
skyrocketing. These advocates are trying to change that.
Vera Institute of Justice. https://www.vera.org/news/
womens-incarceration-rates-are-skyrocketing.
Dickins, K. (2025). Ethical considerations for conducting
community-engaged research with women experiencing
homelessness and incarcerated women. Ethics &
Human Research, 47(1), 20–33. https://doi.org/10.1002/
eahr.60005
Dickins, K. A. (2024). Improving traumatic stress with jus-
tice-impacted women and women experiencing home-
lessness: A pilot study of narrative exposure therapy.
Issues in Mental Health Nursing, 45(2), 121–141.
https://doi.org/10.1080/01612840.2023.2238091
Dickins, K. A., Houlihan, M. C. K., Kim, A., Dixon, I., Reed,
M., & Karnik, N. S. (2025). Traumatic stress Among
women who are incarcerated: A community engaged
approach to determining needs and opportunities for
intervention. Journal of Health Care for the Poor and
Underserved, 36(1), 295–326. https://doi.org/10.1353/
hpu.2025.a951598
Dickins, K. A., Reed, M., Paun, O., Swanson, B., & Karnik,
N. S. (2023). Biopsychosocial model of traumatic stress
symptoms in women experiencing homelessness: A
qualitative descriptive study. Issues in Mental Health
Nursing, 44(6), 482–493. https://doi.org/10.1080/
01612840.2023.2205522
Ervin, S., Jagannath, J., Zweig, J., Willison, J. B., Jones, K. B.,
Maskolunas, K., Agha, C., & Cajarty, B. (2020).
Addressing trauma and victimization in women’s prisons:
Executive summary. Urban Institute. https://www.urban.
org/research/publication/addressing-trauma-and-victimi
zation-womens-prisons.
Facer-Irwin, E., Blackwood, N. J., Bird, A., Dickson, H.,
McGlade, D., Alves-Costa, F., & MacManus, D. (2019).
PTSD in prison settings: A systematic review and meta-
analysis of comorbid mental disorders and problematic
behaviours. PLoS One, 14(9), Article e0222407. https://
doi.org/10.1371/journal.pone.0222407
Fair, H., & Walmsley, R. (2025). World female imprisonment
list (6th ed.). Institute for Crime & Justice Policy
Research, Birkbeck, University of London. https://www.
prisonstudies.org/sites/default/files/resources/downloads/
world_female_imprisonment_list_6th_edition.pdf.
Fazel, S., Hayes, A. J., Bartellas, K., Clerici, M., & Trestman,
R. (2016). Mental health of prisoners: Prevalence, adverse
outcomes, and interventions. The Lancet. Psychiatry, 3(9),
871–881. https://doi.org/10.1016/S2215-0366(16)30142-0
Friedman, S. H., Tamburello, A. C., Kaempf, A., & Hall,
R. C. W. (2019). Prescribing for women in corrections.
The Journal of the American Academy of Psychiatry and
the Law, 47(4), 476–485. https://doi.org/10.29158/
JAAPL.003885-19
Gajewski-Nemes, J., & Messina, N. (2021). Exploring and
healing invisible wounds: Perceptions of trauma-specific
treatment from incarcerated men and women. Journal
of Trauma & Treatment, 10(5), 1–8.
Gibbons, R. D., Hedeker, D. R., & Davis, J. M. (1993).
Estimation of effect size from a series of experiments
involving paired comparisons. Journal of Educational
Statistics, 18(3), 271–279.
Gray, M. J., Litz, B. T., Hsu, J. L., & Lombardo, T. W. (2004).
Psychometric properties of the life events checklist.
Assessment, 11(4), 330–341. https://doi.org/10.1177/
1073191104269954
Gryczynski, J., McNeely, J., Wu, L. T., Subramaniam, G. A.,
Svikis, D. S., Cathers, L. A., Sharma, G., King, J., Jelstrom,
E., Nordeck, C. D., Sharma, A., Mitchell, S. G., O’Grady,
K. E., & Schwartz, R. P. (2017). Validation of the TAPS-1:
A four-item screening tool to identify unhealthy substance
use in primary care. Journal of General Internal Medicine,
32(9), 990–996. doi:10.1007/s11606-017-4079-x
Guina, J., Nahhas, R. W., Sutton, P., & Farnsworth, S.
(2018). The influence of trauma type and timing on
PTSD symptoms. The Journal of Nervous and Mental
Disease, 206(1), 72–76. https://doi.org/10.1097/NMD.
0000000000000730
Hamilton, C. M., Strader, L. C., Pratt, J. G., Maiese, D.,
Hendershot, T., Kwok, R. K., & Haines, J. (2011). The
PhenX toolkit: Get the most from your measures.
American Journal of Epidemiology, 174(3), 253–260.
https://doi.org/10.1093/aje/kwr193
Hijazi, A. M., Lumley, M. A., Ziadni, M. S., Haddad, L., Rapport,
L. J., & Arnetz, B. B. (2014). Brief narrative exposure therapy
for posttraumatic stress in Iraqi refugees: A preliminary ran-
domized clinical trial. Journal of Traumatic Stress, 27(3),
314–322. https://doi.org/10.1002/jts.21922
Ibrahim, B. (2015). Lay counselors experiences with coun-
seling their peers; the impact of being a lay counselor
and providing therapy to traumatized Sudanese refugees
in Cairo [Master’s Thesis, American University in Cairo].
https://fount.aucegypt.edu/etds/163.
Jeste, D. V., Palmer, B. W., Appelbaum, P. S., Golshan, S.,
Glorioso, D., Dunn, L. B., Kim, K., Meeks, T., &
Kraemer, H. C. (2007). A new brief instrument for asses-
sing decisional capacity for clinical research. Archives of
General Psychiatry, 64(8), 966–974. https://doi.org/10.
1001/archpsyc.64.8.966
Jones, M. S. (2020). Exploring coercive control, PTSD, and
the use of physical violence in the pre-prison heterosexual
relationships of incarcerated women. Criminal Justice
and Behavior, 47(10), 1299–1318. https://doi.org/10.
1177/0093854820920661
Kajstura, A., & Sawyer, W. (2024). Women’s
mass incarceration: The whole pie 2024. Prison Policy
Initiative. https://www.prisonpolicy.org/reports/pie2024
women.html.
Karlsson, M. E., Zielinski, M. J., & Bridges, A. J. (2020).
Replicating outcomes of survivors healing from abuse:
Recovery through exposure (SHARE): A brief exposure-
bassed group treatment for incarcerated survivors of sex-
ual violence. Psychological Trauma:Theory, Research,
Practice and Policy, 12(3), 300–305.
Karlsson, M. E., Zielinski, M. J., Calvert, M., & Bridges, A. J.
(2022). Decreases in psychiatric symptoms persist following
exposure-based group therapy for sexual violence victimi-
zation among incarcerated women. Psychological Services,
19(3), 534–540. https://doi.org/10.1037/ser0000570
Kehle-Forbes, S. M., Meis, L. A., Spoont, M. R., & Polusny,
M. A. (2016). Treatment initiation and dropout from pro-
longed exposure and cognitive processing therapy in a
VA outpatient clinic. Psychological Trauma : Theory,
Research, Practice and Policy, 8(1), 107–114. https://doi.
org/10.1037/tra0000065
Kelman, J., Gribble, R., Harvey, J., Palmer, L., & MacManus, D.
(2024). How does a history of trauma affect the experience
of imprisonment for individuals in women’s prisons: A
qualitative exploration. Women & Criminal Justice, 34(3),
171–191. https://doi.org/10.1080/08974454.2022.2071376
Killeen, T. K., Wen, C.-C., Neelon, B., & Baker, N. (2023).
Predictors of treatment completion among women
receiving integrated treatment for comorbid posttrau-
matic stress and substance use disorders. Substance Use
& Misuse, 58(4), 500–511. https://doi.org/10.1080/
10826084.2023.2170183
Kohler, R. E., Roncarati, J. S., Aguiar, A., Chatterjee, P., Gaeta,
J., Viswanath, K., & Henry, C. (2021). Trauma and cervical
cancer screening among women experiencing homeless-
ness: A call for trauma-informed care. Women’s Health,
17, 1–10. https://doi.org/10.1177/17455065211029238
Kroenke, K., Spitzer, R. L., & Williams, J. B. W. (2001). The
PHQ-9: Validity of a brief depression severity measure.
Journal of General Internal Medicine, 16(9), 606–613.
Maercker, A., Cloitre, M., Bachem, R., Schlumpf, Y. R.,
Khoury, B., Hitchcock, C., & Bohus, M. (2022).
Complex post–traumatic stress disorder. Lancet
(London, England), 400(10345), 60–72. https://doi.org/
10.1016/S0140-6736(22)00821-2
Malik, N., Facer-Irwin, E., Dickson, H., Bird, A., &
MacManus, D. (2023). The effectiveness of trauma-focused
interventions in prison settings: A systematic review and
meta-analysis. Trauma, Violence, & Abuse, 24(2), 844–
857. https://doi.org/10.1177/15248380211043890
Marx, B. P., Lee, D. J., Norman, S. B., Bovin, M. J., Sloan, D.
M., Weathers, F. W., Keane, T. M., & Schnurr, P. P.
(2022). Reliable and clinically significant change in the
Clinician-Administered PTSD Scale for DSM-5 and
PTSD Checklist for DSM-5 among male veterans.
Psychological Assessment, 34(2), 197–203. https://doi.
org/10.037/pas0001098
McLeod, K. E., Wong, K. A., Rajaratnam, S., Guyatt, P.,
DiPelino, S., Zaki, N., Akbari, H., Kerrigan, C., Jones,
R., Norris, E., Liauw, J., Butler, A., Kish, N., Plugge, E.,
Harriott, P., & Kouyoumdjian, F. G. (2025). Health con-
ditions among women in prisons: A systematic review.
The Lancet Public Health, 10(7), e609–e624. https://doi.
org/10.1016/S2468-2667(25)00092-1
National Council of State Boards of Nursing. (2026). Active
RN licenses: A profile of nursing licensure in the U.S.
https://www.ncsbn.org/active-rn-licenses.
National Institute of Justice. (2024, April 9). Five things to
know about women and reentry. https://nij.ojp.gov/topics/
articles/five-things-know-about-women-and-reentry.
Neuner, F., Catani, C., Ruf, M., Schauer, E., Schauer, M., &
Elbert, T. (2008). Narrative exposure therapy for the treat-
ment of traumatized children and adolescents (KidNET):
from neurocognitive theory to field intervention. Child
and Adolescent Psychiatric Clinics of North America,
17(3), 641–x. https://doi.org/10.1016/j.chc.2008.03.001
Neuner, F., Schauer, M., & Elbert, T. (2002). A narrative
exposure treatment as intervention in a refugee camp:
Two case reports. Behavioural and Cognitive
Psychotherapy, 30(2), 205–209.
Neuner, F., Schauer, M., Klaschik, C., Karunakara, U., &
Elbert, T. (2004). A comparison of narrative exposure
therapy, supportive counseling, and psychoeducation for
treating posttraumatic stress disorder in an African refugee
settlement. Journal of Consulting and Clinical Psychology,
72(4), 579–587. https://doi.org/10.1037/0022-006X.72.4.579
Olff, M., Langeland, W., Draijer, N., & Gersons, B. P. (2007).
Gender differences in posttraumatic stress disorder.
Psychological Bulletin, 133(2), 183–204. https://doi.org/
10.1037/0033-2909.133.2.183
Pettus, C. A. (2023). Trauma and prospects for reentry.
Annual Review of Criminology, 6, 423–446. https://doi.
org/10.1146/annurev-criminol-041122-111300
Piper, A., & Berle, D. (2019). The association between trauma
experienced during incarceration and PTSD outcomes: A
systematic review and meta-analysis. The Journal of
Forensic Psychiatry & Psychology, 30(5), 854–875. https://
doi.org/10.1080/14789949.2019.1639788
Quandt, K. R., & Jones, A. (2021). Research
roundup: Incarceration can cause lasting damage to men-
tal health. Prison Policy Initiative. https://www.
prisonpolicy.org/blog/2021/05/13/mentalhealthimpacts/.
Roberts, N. P., Kitchiner, N. J., Lewis, C. E., Downes, A. J., &
Bisson, J. I. (2021). Psychometric properties of the PTSD
checklist for DSM-5 in a sample of trauma exposed men-
tal health service users. European Journal of
Psychotraumatology, 12(1), 1863578. https://doi.org/10.
1080/20008198.2020.1863578
Robjant, K., & Fazel, M. (2010). The emerging evidence for
narrative exposure therapy: A review. Clinical Psychology
Review, 30(8), 1030–1039. https://doi.org/10.1016/j.cpr.
2010.07.004
Robjant, K., Koebach, A., Schmitt, S., Chibashimba, A.,
Carleial, S., & Elbert, T. (2019). The treatment of post-
traumatic stress symptoms and aggression in female for-
mer child soldiers using adapted narrative exposure
therapy—A RCT in Eastern Democratic Republic of
Congo. Behaviour Research and Therapy, 123, 103482.
https://doi.org/10.1016/j.brat.2019.103482
Saad, L. (2025). Americans’ ratings of U.S. professions stay his-
torically low. Gallup. https://news.gallup.com/poll/655106/
americans-ratings-professions-stay-historically-low.aspx.
Schauer, M., Neuner, F., & Elbert, T. (2025). Narrative
exposure therapy (NET) For survivors of traumatic stress
(3rd ed.). Hogrefe Publishing.
Shalev, N. (2009). From public to private care the historical
trajectory of medical services in a New York city jail.
American Journal of Public Health, 99(6), 988–995.
https://doi.org/10.2105/AJPH.2007.123265
Simon, L., Beckmann, D., Stone, M., Williams, R., Cohen,
M., & Tobey, M. (2020). Clinician experiences of care
provision in the correctional setting: A scoping review.
Journal of Correctional Health Care, 26(4), 301–314.
https://doi.org/10.1177/1078345820953154
Smith, J. R., Workneh, A., & Yaya, S. (2020). Barriers and
facilitators to help-seeking for individuals with posttraumatic
stress disorder: A systematic review. Journal of Traumatic
Stress, 33(2), 137–150. https://doi.org/10.1002/jts.22456
Smith, S., Muse, M. V., & Phillips, J. M. (2021). Addressing
moral distress in correctional nursing: A call to action.
Journal of Correctional Health Care, 27(2), 75–80.
https://doi.org/10.1089/jchc.20.04.0029
Spitzer, R. L., Kroenke, K., Williams, J. B. W., & Löwe, B.
(2006). A brief measure for assessing generalized anxiety
disorder: The GAD-7. Archives of Internal Medicine,
166(10), 1092–1097.
Strijk, P. J., Nijdam, M. J., Klaassens, E. R., Bedawi, V., De la
Rie, S., & Jongedijk, R. A. (2025). Feasibility and prelimi-
nary effectiveness of a highly intensive inpatient treat-
ment programme with narrative exposure therapy for
patients with posttraumatic stress disorder. Frontiers in
Psychology, 16, 1516144.
Strijk, P., Jongedijk, R. A., & Bedawi, V. (2020). A new treat-
ment approach for PTSD: High-intensive narrative
exposure therapy (HI-NET). Maltrattamento e abuso
all’infanzia, 22(3), 51–62.
Swavola, E., Riley, K., & Subramanian, R. (2016).
Overlooked: Women and jails in an era of reform. Vera
Institute of Justice. https://www.vera.org/publications/
overlooked-women-and-jails-report.
Szafranski, D. D., Snead, A., Allan, N. P., Gros, D. F.,
Killeen, T., Flanagan, J., Pericot-Valverde, I., & Back, S.
E. (2017). Integrated, exposure-based treatment for
PTSD and comorbid substance use disorders: Predictors
of treatment dropout. Addictive Behaviors, 73, 30–35.
https://doi.org/10.1016/j.addbeh.2017.04.005
Tripodi, S. J., Killian, M. O., Gilmour, M., Curley, E., &
Herod, L. (2022). Trauma-informed care groups with
incarcerated women: An alternative treatment design
comparing seeking safety and STAIR. Journal of the
Society for Social Work and Research, 13(3), 511–531.
https://doi.org/10.1086/712732
Turgoose, D., Ashwick, R., & Murphy, D. (2018). Systematic
review of lessons learned from delivering tele-therapy to
veterans with post-traumatic stress disorder. Journal of
Telemedicine and Telecare, 24(9), 575–585. https://doi.
org/10.1177/1357633X17730443
Wang, L. (2022). Both sides of the bars: How mass incarcera-
tion punishes families. Prison Policy Initiative. https://
www.prisonpolicy.org/blog/2022/08/11/parental_incarce
ration/.
Weathers, F. W., Blake, D. D., Schnurr, P. P., Kaloupek, D.
G., Marx, B. P., & Keane, T. M. (2013). The Life Events
Checklist for DSM-5 (LEC-5) –Standard. https://www.
ptsd.va.gov/professional/assessment/te-measures/life_ev
ents_checklist.asp.
Weathers, F. W., Litz, B. T., Keane, T. M., Palmieri, P. A.,
Marx, B. P., & Schnurr, P. P. (2013). The PTSD Checklist
for DSM-5 (PCL-5) – Standard. https://www.ptsd.va.gov/
professional/assessment/adult-sr/ptsd-checklist.asp
Wilkins, C. H. (2018). Effective engagement requires trust and
being trustworthy. Medical Care, 56 Suppl 1(10 Suppl 1),
S6–S8. https://doi.org/10.1097/MLR.0000000000000953
Zhong, S., Zhu, X., Mellsop, G., Zhou, J., & Wang, X. (2021).
Correlates of presence and remission of post-trauma
stress disorder in incarcerated women: A case-control
study design. Frontiers in Psychiatry, 12, Article 748518.
https://doi.org/10.3389/fpsyt.2021.748518"""

test25 = """Angelakis, I., Gillespie, E. L., & Panagioti, M. (2019).
Childhood maltreatment and adult suicidality: A compre-
hensive systematic review with meta-analysis.
Psychological Medicine, 49(7), 1057–1078.
Ben-Ezra, M., Karatzias, T., Hyland, P., Brewin, C. R.,
Cloitre, M., Bisson, J. I., Roberts, N. P., Lueger-
Schuster, B., & Shevlin, M. (2018). Posttraumatic stress
disorder (PTSD) and complex PTSD (CPTSD) as per
ICD-11 proposals: A population study in Israel.
Depression and Anxiety, 35(3), 264–274. https://doi.org/
10.1002/da.22723
Bernstein, D. P., Stein, J. A., Newcomb, M. D., Walker, E.,
Pogge, D., Ahluvalia, T., Stokes, J., Handelsman, L.,
Medrano, M., Desmond, D., & Zule, W. (2003).
Development and validation of a brief screening version
of the Childhood Trauma Questionnaire. Child Abuse
& Neglect, 27(2), 169–190. https://doi.org/10.1016/
S0145-2134(02)00541-0
Brewin, C. R., Cloitre, M., Hyland, P., Shevlin, M.,
Maercker, A., Bryant, R. A., Humayun, A., Jones, L. M.,
Kagee, A., Rousseau, C., Somasundaram, D., Suzuki, Y.,
Wessely, S., Van Ommeren, M., & Reed, G. M. (2017).
A review of current evidence regarding the ICD-11 pro-
posals for diagnosing PTSD and complex PTSD.
Clinical Psychology Review, 58, 1–15. https://doi.org/10.
1016/j.cpr.2017.09.001
Brewin, C. R., Dalgleish, T., & Joseph, S. (1996). A dual rep-
resentation theory of posttraumatic stress disorder.
Psychological Review, 103, 670–686.
Cloitre, M. (2020). ICD-11 complex post-traumatic stress
disorder: Simplifying diagnosis in trauma populations.
The British Journal of Psychiatry, 216(3), 129–131.
Cloitre, M., Garvert, D. W., Brewin, C. R., Bryant, R. A., &
Maercker, A. (2013). Evidence for proposed ICD-11
PTSD and complex PTSD: A latent profile analysis.
European Journal of Psychotraumatology, 4, 20706.
https://doi.org/10.3402/ejpt.v4i0.20706
Cloitre, M., Hyland, P., Bisson, J. I., Brewin, C. R., Roberts,
N. P., Karatzias, T., & Shevlin, M. (2019). ICD-
11Posttraumatic Stress Disorder and Complex
Posttraumatic Stress Disorder in the United States: A
Population-Based Study. Journal of Traumatic Stress,
32(6), 833–842. https://doi.org/10.1002/jts.22454
Cloitre, M., Shevlin, M., Brewin, C. R., Bisson, J. I., Roberts,
N. P., Maercker, A., Karatzias, T., & Hyland, P. (2018).
The International Trauma Questionnaire: development
of a self-report measure of ICD-11 PTSD and complex
PTSD. Acta Psychiatrica Scandinavica, 138(6), 536–546.
https://doi.org/10.1111/acps.12956
Coates, S. W., & Moore, M. S. (1997). The complexity of
early trauma: Representation and transformation.
Psychoanalytic Inquiry, 17(3), 286–311.
Davies, J. M. (2019). Truth and consequence: Alternative
facts and discordant realities. Psychoanalytic Dialogues,
29(2), 165–171. https://doi.org/10.1080/10481885.2019.
1587986
Ehlers, A., & Clark, D. M. (2000). A cognitive model of post-
traumatic stress disorder. Behaviour Research and
Therapy, 38(4), 319–345. https://doi.org/10.1016/S0005-
7967(99)00123-0
Ferenczi, S. (1932). The clinical diary of Sandor Ferenczi (J.
Dupont, Ed.; M. Balint & NZ Jackson, Trans.). Harvard
University Press.
Ferenczi, S. (1933). Confusion of tongues between adults
and the child (E. Mosbacher, Trans.). In M. Balint
(Ed.), Final contributions to the problems and methods
of psycho-analysis. Karnac Books.
Foa, E. B., Ehlers, A., Clark, D. M., Tolin, D. F., & Orsillo, S.
M. (1999). The Posttraumatic Cognitions Inventory
(PTCI): Development and validation. Psychological
Assessment, 11(3), 303–314. https://doi.org/10.1037/
1040-3590.11.3.303
Ford, J. D., & Courtois, C. A. (2014). Complex PTSD, affect
dysregulation, and borderline personality disorder.
Borderline personality disorder and emotion dysregula-
tion, 1(1), 1–9. http://www.bpded.com/content/1/1/9.
Ford, J. D., & Gómez, J. M. (2015). The relationship of
psychological trauma and dissociative and posttraumatic
stress disorders to nonsuicidal self-injury and suicidality:
A review. Journal of Trauma & Dissociation, 16(3), 232–
271.
Frankel, J. (2002). Exploring Ferenczi’s concept of identifi-
cation with the aggressor: Its role in trauma, everyday
life, and the therapeutic relationship. Psychoanalytic
Dialogues, 12(1), 101–139.
Frankel, J. (2018). Psychological enslavement through
identification with the aggressor. In A. Dimitrijevic, G.
Cassullo, & J. Frankel (Eds.), Ferenczi’s influence on con-
temporary psychoanalytic traditions (pp. 134–139).
Routledge.
Gewirtz-Meydan, A., & Lahav, Y. (2020a). Sexual dysfunc-
tion and distress among childhood sexual abuse survi-
vors: The role of post-traumatic stress disorder. The Journal of Sexual Medicine, 17(11), 2267–2278. https://
doi.org/10.1016/j.jsxm.2020.07.016
Gewirtz-Meydan, A., & Lahav, Y. (2020b). Childhood
Sexual Abuse and Sexual Motivations – The Role of
Dissociation. The Journal of Sex Research, 58(9), 1151–
1160. https://doi.org/10.1080/00224499.2020.1808564
Gómez de La Cuesta, G., Schweizer, S., Diehle, J., Young, J.,
& Meiser-Stedman, R. (2019). The relationship between
maladaptive appraisals and posttraumatic stress disorder:
A meta-analysis. European Journal of
Psychotraumatology, 10(1), 1620084. https://doi.org/10.
1080/20008198.2019.1620084
Greenblatt-Kimron, L., Karatzias, T., Yonatan, M., Shoham,
A., Hyland, P., Ben-Ezra, M., & Shevlin, M. (2023). Early
maladaptive schemas and ICD -11 CPTSD symptoms:
Treatment considerations. Psychology and
Psychotherapy: Theory. Research and Practice, 96(1),
117–128. https://doi.org/10.1111/papt.12429
Harsey, S. J., Zurbriggen, E. L., & Freyd, J. J. (2017).
Perpetrator responses to victim confrontation: DARVO
and victim self-blame. Journal of Aggression,
Maltreatment & Trauma, 26(6), 644–663. https://doi.
org/10.1080/10926771.2017.1320777
Herman, J. L. (1992). Trauma and recovery: The aftermath of
violence—From domestic abuse to political terror. Basic
Books.
Hyland, P., Karatzias, T., Shevlin, M., Cloitre, M., & Ben-
Ezra, M. (2020). A longitudinal study of ICD-11 PTSD
and complex PTSD in the general population of Israel.
Psychiatry Research, 286, 112871. https://doi.org/10.
1016/j.psychres.2020.112871
Hyland, P., Shevlin, M., Brewin, C. R., Cloitre, M., Downes,
A. J., Jumbe, S., Karatzias, T., Bisson, J. I., & Roberts, N. P.
(2017). Validation of post-traumatic stress disorder
(PTSD) and complex PTSD using the International
Trauma Questionnaire. Acta Psychiatrica Scandinavica,
136(3), 313–322. https://doi.org/10.1111/acps.12771
Hyland, P., Shevlin, M., Fyvie, C., Cloitre, M., & Karatzias,
T. (2020). The relationship between ICD-11 PTSD, com-
plex PTSD and dissociative experiences. Journal of
Trauma & Dissociation, 21(1), 62–72. https://doi.org/10.
1080/15299732.2019.1675113
Hyland, P., Vallières, F., Cloitre, M., Ben-Ezra, M.,
Karatzias, T., Olff, M., Murphy, J., & Shevlin, M.
(2021). Trauma, PTSD, and complex PTSD in the
Republic of Ireland: Prevalence, service use, comorbidity,
and risk factors. Social Psychiatry and Psychiatric
Epidemiology, 56(4), 649–658. https://doi.org/10.1007/
s00127-020-01912-x
Jackson, S., Newall, E., & Backett-Milburn, K. (2015).
Children’s narratives of sexual abuse. Child & Family
Social Work, 20(3), 322–332. https://doi.org/10.1111/cfs.
12080
Karatzias, T., Shevlin, M., Cloitre, M., Busuttil, W., Graham,
K., Hendrikx, L., Hyland, P., Biscoe, N., & Murphy, D.
(2024). Enhanced skills training in affective and interper-
sonal regulation versus treatment as usual for ICD-11
complex PTSD: A pilot randomised controlled trial (The
RESTORE Trial). Psychotherapy and Psychosomatics,
93(3), 203–215. https://doi.org/10.1159/000538428
Karatzias, T., Shevlin, M., Ford, J. D., Fyvie, C., Grandison,
G., Hyland, P., & Cloitre, M. (2022). Childhood
trauma, attachment orientation, and complex PTSD
(CPTSD) symptoms in a clinical sample:
Implications for treatment. Development and
Psychopathology, 34(3), 1192–1197. https://doi.org/10.
1017/S0954579420001509
Kazlauskas, E., Gegieckaite, G., Hyland, P., Zelviene, P., &
Cloitre, M. (2018). The structure of ICD-11 PTSD and
complex PTSD in Lithuanian mental health services.
European Journal of Psychotraumatology, 9(1), 1414559.
https://doi.org/10.1080/20008198.2017.1414559
Kolk, B. A., & Fisler, R. (1995). Dissociation and the frag-
mentary nature of traumatic memories: Overview and
exploratory study. Journal of Traumatic Stress, 8(4),
505–525. https://doi.org/10.1007/BF02102887
Kucharska, J. (2017). Sex differences in the appraisal of trau-
matic events and psychopathology. Psychological
Trauma: Theory, Research, Practice, and Policy, 9(5),
575–582. https://doi.org/10.1037/tra0000244
Lahav, Y. (2021a). Painful bonds: Identification with the
aggressor and distress among IPV survivors. Journal of
Psychiatric Research, 144, 26–31.
Lahav, Y. (2021b). Suicidality in childhood abuse survivors–
The contribution of identification with the aggressor.
Journal of Affective Disorders, 804–810.
Lahav, Y. (2023). Hyper-sensitivity to the perpetrator and
the likelihood of returning to abusive relationships.
Journal of Interpersonal Violence, 38(1–2), 1815–1841.
https://doi.org/10.1177/08862605221092075
Lahav, Y., Allende, S., Talmon, A., Ginzburg, K., & Spiegel,
D. (2020). Identification with the aggressor and inward
and outward aggression in abuse survivors. Journal of
Interpersonal Violence, 1–24.
Lahav, Y., Avidor, S., Gafter, L., & Lotan, A. (forthcoming).
Cast with uncertainty: Doubt regarding abuse-related
appraisals and trauma-related distress in the face of inti-
mate partner violence. Journal of Trauma & Dissociation.
Lahav, Y., Cloitre, M., Hyland, P., Shevlin, M., Ben-Ezra, M.,
& Karatzias, T. (2025). Complex PTSD and identification
with the aggressor among survivors of childhood abuse.
Child Abuse & Neglect, 160, 107196. https://doi.org/10.
1016/j.chiabu.2024.107196
Lahav, Y., Huberman, M., Bøgelund Dokkedahl, S., &
Gafter, L. (2025). Agonizing uncertainty: The develop-
ment and psychometric evaluation of the Abuse Doubt
Scale. Journal of Interpersonal Violence,
08862605251372577.
Lahav, Y., Seligman, Z., & Solomon, Z. (2017).
Countertransference in the face of growth: Reenactment
of the trauma. In D. R. Aleksandrowicz & A. O.
Aleksandrowicz (Eds.), Countertransference in perspec-
tive: The double-edged sword of the patient-therapist
emotional relationship (pp. 57–79). Academic Press.
Lahav, Y., Talmon, A., & Ginzburg, K. (2019). Knowing the
abuser inside and out: The development and psycho-
metric evaluation of the Identification With the
Aggressor Scale. Journal of Interpersonal Violence,
36(19-20), 9725–9748. https://doi.org/10.1177/
0886260519872306
Lahav, Y., Talmon, A., Ginzburg, K., & Spiegel, D. (2019).
Reenacting past abuse–Identification with the aggressor
and sexual revictimization. Journal of Trauma and
Dissociation, 20(4), 378–391. https://doi.org/10.1080/
15299732.2019.1572046
Leiva-Bianchi, M., Nvo-Fernandez, M., Villacura-Herrera,
C., Miño-Reyes, V., & Parra Varela, N. (2023). What
are the predictive variables that increase the risk of devel-
oping a complex trauma? A meta-analysis. Journal of
Affective Disorders, 343, 153–165. https://doi.org/10.
1016/j.jad.2023.10.002
Lindert, J., von Ehrenstein, O. S., Grashow, R., Gal, G.,
Braehler, E., & Weisskopf, M. G. (2014). Sexual and phys-
ical abuse in childhood is associated with depression and anxiety over the life course: Systematic review and meta-
analysis. International Journal of Public Health, 59(2),
359–372.
Maercker, A., Brewin, C. R., Bryant, R. A., Cloitre, M., Reed,
G. M., van Ommeren, M., … Saxena, S. (2013). Diagnosis
and classification of disorders specifically associated with
stress: Proposals for ICD-11. World Psychiatry, 12(3),
198–206. https://doi.org/10.1002/wps.20057
Maercker, A., Cloitre, M., Bachem, R., Schlumpf, Y. R.,
Khoury, B., Hitchcock, C., & Bohus, M. (2022).
Complex post-traumatic stress disorder. The Lancet,
400(10345), 60–72. https://doi.org/10.1016/S0140-
6736(22)00821-2
Maercker, A., Hecker, T., Augsburger, M., & Kliem, S.
(2018). ICD-11 Prevalence rates of posttraumatic stress
disorder and complex posttraumatic stress disorder in a
German nationwide sample. Journal of Nervous &
Mental Disease, 206(4), 270–276. https://doi.org/10.
1097/NMD.0000000000000790
Messman-Moore, T. L., & Bhuptani, P. H. (2017). A review
of the long-term impact of child maltreatment on post-
traumatic stress disorder and its comorbidities: An
emotion dysregulation perspective.. Clinical Psychology:
Science and Practice, 24(2), 154–169. https://doi.org/10.
1111/cpsp.12193
Møller, L., Augsburger, M., Elklit, A., Søgaard, U., &
Simonsen, E. (2020). Traumatic experiences, ICD-11
PTSD, ICD-11 complex PTSD, and the overlap with
ICD-10 diagnoses. Acta Psychiatrica Scandinavica,
141(5), 421–431. https://doi.org/10.1111/acps.13161
Nelson, J., Klumparendt, A., Doebler, P., & Ehring, T.
(2017). Childhood maltreatment and characteristics of
adult depression: Meta-analysis. The British Journal of
Psychiatry, 210(2), 96–104.
Niwa, M., Kato, T., Narita-Ohtaki, R., Otomo, R., Suga, Y.,
Sugawara, M., Narita, Z., Hori, H., Kamo, T., & Kim, Y.
(2022). Skills training in affective and interpersonal
regulation narrative therapy for women with ICD-11
complex PTSD related to childhood abuse in Japan: A
pilot study. European Journal of Psychotraumatology,
13(1), 2080933. https://doi.org/10.1080/20008198.2022.
2080933
Ogle, C. M., Rubin, D. C., & Siegler, I. C. (2016). Maladaptive
trauma appraisals mediate the relation between attach-
ment anxiety and PTSD symptom severity.. Psychological
Trauma: Theory, Research, Practice, and Policy, 8(3),
301–309. https://doi.org/10.1037/tra0000112
Porat-Moeller, E., Keidar, A., Gafter, L., & Lahav, Y. (2025).
Shadows of doubt: Ambivalent acknowledgment of abuse
and identification with the aggressor. Child Abuse &
Neglect, 163, 107401. https://doi.org/10.1016/j.chiabu.
2025.107401
Resick, P. A., Bovin, M. J., Calloway, A. L., Dick, A. M.,
King, M. W., Mitchell, K. S., … Wolf, E. J. (2012). A criti-
cal evaluation of the complex PTSD literature:
Implications forDSM-5. Journal of Traumatic Stress,
25(3), 241–251. https://doi.org/10.1002/jts.21699
Rosenberg, T., Lahav, Y., & Ginzburg, K. (2023). Child
abuse and eating disorder symptoms: Shedding light on
the contribution of identification with the aggressor.
Child Abuse & Neglect, 135, 105988. https://doi.org/10.
1016/j.chiabu.2022.105988
Sahle, B. W., Reavley, N. J., Li, W., Morgan, A. J., Yap,
M. B. H., Reupert, A., & Jorm, A. F. (2022). The associ-
ation between adverse childhood experiences and
common mental disorders and suicidality: An umbrella
review of systematic reviews and meta-analyses.
European Child & Adolescent Psychiatry, 31(10), 1489–
1499. https://doi.org/10.1007/s00787-021-01745-2
Serier, K. N., Zelkowitz, R. L., Smith, B. N., Vogt, D., &
Mitchell, K. S. (2023). The Posttraumatic Cognitions
Inventory (PTCI): Psychometricevaluation in veteran
men and women with trauma exposure.. Psychological
Assessment, 35(2), 140–151. https://doi.org/10.1037/
pas0001190
Shahar, G., Noyman, G., Schnidel-Allon, I., & Gilboa-
Schechtman, E. (2013). Do PTSD symptoms and
trauma-related cognitions about the self constitute a
vicious cycle? Evidence for both cognitive vulnerability
and scarring models. Psychiatry Research, 205(1–2), 79–
84. https://doi.org/10.1016/j.psychres.2012.07.053
Siegel, A., Shaked, E., & Lahav, Y. (2024). A complex
relationship: Intimate partner violence, identification
with the aggressor, and guilt. Violence Against Women,
30(2), 445–459. https://doi.org/10.1177/1077801222
1137917
Stoltenborgh, M., Bakermans-Kranenburg, M. J., Alink,
L. R. A., & van IJzendoorn, M. H. (2015). The
prevalence of child maltreatment across the globe:
Review of a series of meta-analyses. Child Abuse
Review, 24(1), 37–50.
Sultana, E. A., & Lahav, Y. (2023). Posttraumatic growth,
dissociation and identification with the aggressor
among childhood abuse survivors. Journal of Trauma &
Dissociation, 24(3), 410–425. https://doi.org/10.1080/
15299732.2023.2181478
Tietjen, G. E., Brandes, J. L., Peterlin, B. L., Eloff, A., Dafer,
R. M., Stein, M. R., Drexler, E., Martin, V. T.,
Hutchinson, S., Aurora, S. K., Recober, A., Herial, N.
A., Utley, C., White, L., & Khuder, S. A. (2010).
Childhood maltreatment and migraine (Part I).
Prevalence and adult revictimization: A multicenter
headache clinic survey. Headache: The Journal of Head
and Face Pain, 50(1), 20–31. https://doi.org/10.1111/j.
1526-4610.2009.01556.x
van der Kolk, B. A. (2005). Developmental trauma disorder:
Toward a rational diagnosis for children with complex
trauma histories. Psychiatric Annals, 35(5), 401–408.
https://doi.org/10.3928/00485713-20050501-06
van Dijke, A., Hopman, J. A. B., & Ford, J. D. (2018). Affect
dysregulation, psychoform dissociation, and adult rela-
tional fears mediate the relationship between childhood
trauma and complex posttraumatic stress disorder inde-
pendent of the symptoms of borderline personality dis-
order. European Journal of Psychotraumatology, 9(1),
1400878. https://doi.org/10.1080/20008198.2017.1400878
Vonderlin, R., Kleindienst, N., Alpers, G. W., Bohus, M.,
Lyssenko, L., & Schmahl, C. (2018). Dissociation in vic-
tims of childhood abuse or neglect: A meta-analytic
review. Psychological Medicine, 48(15), 2467–2476.
Wang, S.-J., Chang, J.-J., Cao, L.-L., Li, Y.-H., Yuan, M.-Y.,
Wang, G.-F., & Su, P.-Y. (2023). The Relationship
Between Child Sexual Abuse and Sexual Dysfunction in
Adults: A Meta-Analysis. Trauma, Violence, & Abuse,
24(4), 2772–2788. https://doi.org/10.1177/1524838022
1113780
Wegman, H. L., & Stetler, C. (2009). A meta-analytic review
of the effects of childhood abuse on medical outcomes in
adulthood. Psychosomatic Medicine, 71(8), 805–812.
https://doi.org/10.1097/PSY.0b013e3181bb2b46"""

test26 = """Altman, D. G., & Royston, P. (2006). The cost of dichoto-
mising continuous variables. BMJ, 332(7549), 1080.
https://doi.org/10.1136/bmj.332.7549.1080
American Psychiatric Association. (1994). Diagnostic and
statistical manual of mental disorders. American
Psychiatric Publishing, Inc.
American Tinnitus Association. (n.d.). Measuring tinnitus.
https://www.ata.org/about-tinnitus/why-are-my-ears-
ringing/measuring-tinnitus/.
Ausland, J. H.-L., Engdahl, B., Oftedal, B., Steingrímsdóttir,
ÓA, Nielsen, C. S., Hopstock, L. A., Johnsen, M., Friborg,
O., Rosenvinge, J. H., Eggen, A. E., & Krog, N. H. (2021).
Tinnitus and associations with chronic pain: The popu-
lation-based Tromsø Study (2015–2016). PLoS One,
16(3), e0247880. https://doi.org/10.1371/journal.pone.
0247880
Baigi, A., Oden, A., Almlid-Larsen, V., Barrenäs, M.-L., &
Holgers, K.-M. (2011). Tinnitus in the general population
with a focus on noise and stress: A public health study.
Ear and Hearing, 32(6), 787–789. https://doi.org/10.
1097/AUD.0b013e31822229bd
Bauer, C. A. (2018). Tinnitus. New England Journal of
Medicine, 378(13), 1224–1231. https://doi.org/10.1056/
NEJMcp1506631
Benedict, R. (1997). Brief visuospatial memory test – Revised:
Professional manual. Psychological Assessment
Resources Inc.
Benedict, T. M., Keenan, P. G., Nitz, A. J., & Moeller-
Bertram, T. (2020). Post-traumatic stress disorder symp-
toms contribute to worse pain and health outcomes in
veterans with PTSD compared to those without: A sys-
tematic review with meta-analysis. Military Medicine,
185(9-10), e1481–e1491. https://doi.org/10.1093/
milmed/usaa052
Benjamini, Y., & Hochberg, Y. (1995). Controlling the false
discovery rate – A practical and powerful approach to
multiple testing. Journal of the Royal Statistical Society
Series B (Methodological, 57(1), 289–300. https://doi.
org/10.1111/j.2517-6161.1995.tb02031.x
Bhatt, J. M., Lin, H. W., & Bhattacharyya, N. (2016).
Prevalence, severity, exposures, and treatment patterns
of tinnitus in the United States. JAMA Otolaryngology-
Head & Neck Surgery, 142(10), 959–965. https://doi.org/
10.1001/jamaoto.2016.1700
Biswas, R., Genitsaridi, E., Trpchevska, N., Lugo, A., Schlee,
W., Cederroth, C. R., Gallus, S., & Hall, D. A. (2023). Low
evidence for tinnitus risk factors: A systematic review and
meta-analysis. Journal of the Association for Research in
Otolaryngology, 24(1), 81–94. https://doi.org/10.1007/
s10162-022-00874-y
Blake, D. D., Weathers, F. W., Nagy, L. M., Kaloupek, D. G.,
Gusman, F. D., Charney, D. S., & Keane, T. M. (1995).
The development of a clinician-administered PTSD
Scale. Journal of Traumatic Stress, 8(1), 75–90. https://
doi.org/10.1002/jts.2490080106
Buysse, D. J., Reynolds, C. F., Monk, T. H., Berman, S. R., &
Kupfer, D. J. (1989). The Pittsburgh Sleep Quality Index:
A new instrument for psychiatric practice and research.
Psychiatry Research, 28(2), 193–213. https://doi.org/10.
1016/0165-1781(89)90047-4
Carlson, K. F., Gilbert, T. A., O’Neil, M. E., Zaugg,
T. L., Manning, C. A., Kaelin, C., Thielman, E. J.,
Reavis, K. M., & Henry, J. A. (2019). Health care
utilization and mental health diagnoses among veterans with tinnitus. American Journal of Audiology, 28(1S),
181–190. https://doi.org/10.1044/2018_AJA-TTR17-18-
0042
Christensen, H., Mackinnon, A. J., Korten, A. E., Jorm, A. F.,
Henderson, A. S., Jacomb, P., & Rodgers, B. (1999). An
analysis of diversity in the cognitive performance of
elderly community dwellers: Individual differences in
change scores as a function of age. Psychology and
Aging, 14(3), 365–379. https://doi.org/10.1037/0882-
7974.14.3.365
Clarke, N. A., Henshaw, H., Akeroyd, M. A., Adams, B., &
Hoare, D. J. (2020). Associations between subjective tin-
nitus and cognitive performance: Systematic review and
meta-analyses. Trends in Hearing, 24, 23312165209
18416. https://doi.org/10.1177/2331216520918416
Coco, L., Hooker, E. R., Gilbert, T. A., Harker, G. R., Clark,
K. D., Reavis, K. M., Henry, J. A., Zaugg, T. L., & Carlson,
K. F. (2024a). The impact of tinnitus severity on work
functioning among U.S. military veterans with tinnitus.
Seminars in Hearing, 45((01|1)), 40–54. https://doi.org/
10.1055/s-0043-1770152
Coco, L., Hooker, E. R., Gilbert, T. A., Prewitt, A. L., Reavis,
K. M., O’Neil, M. E., Clark, K. D., Henry, J. A., Zaugg, T.,
& Carlson, K. F. (2024b). Associations between traumatic
brain injury and severity of tinnitus-related functional
impairment among US military veterans: A national,
population-based study. The Journal of Head Trauma
Rehabilitation, 39(3), 218–230. https://doi.org/10.1097/
HTR.0000000000000896
de Gruy, J. A., Laurenzo, W. W., Vu, T.-H., Paul, O., Lee, C.,
& Spankovich, C. (2024). Prevalence and predictors of
problematic tinnitus. International Journal of Audiology,
1–7. https://doi.org/10.1080/14992027.2024.2378804
Delis, D. C., Kaplan, E., & Kramer, G. L. (2001). D-KEFS
examiner’s and technical manual. Pearson Education.
Delis, D. C., Kramer, J., Kaplan, E., & Ober, B. (2000).
California verbal learning test – Second Edition. The
Psychological Corporation.
Fagelson, M. (2022). Tinnitus and traumatic memory. Brain
Sciences, 12(11), 1585. https://doi.org/10.3390/brainsci
12111585
Fagelson, M. A. (2007). The association between tinnitus
and posttraumatic stress disorder. American Journal of
Audiology, 16(2), 107–117. https://doi.org/10.1044/1059-
0889(2007/015)
Federici, S., Bracalenti, M., Meloni, F., & Luciano, J. V.
(2017). World Health Organization disability assessment
schedule 2.0: An international systematic review.
Disability and rehabilitation, 39(23), 2347–2380. https://
doi.org/10.1080/09638288.2016.1223177
Folmer, R., Mcmillan, G., Austin, D., & Henry, J. (2011).
Audiometric thresholds and prevalence of tinnitus
among male veterans in the United States: Data from
the National Health and Nutrition Examination Survey,
1999–2006. Journal of Rehabilitation Research and
Development, 48(5), 503–516. https://doi.org/10.1682/
JRRD.2010.07.0138
Fortier, C. B., Amick, M. M., Grande, L., McGlynn, S.,
Kenna, A., Morra, L., Clark, A., Milberg, W. P., &
McGlinchey, R. E. (2014). The Boston Assessment of
Traumatic Brain Injury–Lifetime (BAT-L) semistruc-
tured interview: Evidence of research utility and validity.
The Journal of Head Trauma Rehabilitation, 29(1), 89–98.
https://doi.org/10.1097/HTR.0b013e3182865859
Goldberg, J., Magruder, K. M., Forsberg, C. W., Kazis, L. E.,
Ustün, T. B., Friedman, M. J., Litz, B. T., Vaccarino, V.,
Heagerty, P. J., Gleason, T. C., Huang, G. D., & Smith,
N. L. (2014). The association of PTSD with physical
and mental health functioning and disability (VA
Cooperative Study #569: The course and consequences
of posttraumatic stress disorder in Vietnam-era veteran
twins). Quality of Life Research: An International
Journal of Quality of Life Aspects of Treatment, Care
and Rehabilitation, 23(5), 1579–1591. https://doi.org/10.
1007/s11136-013-0585-4
Green, P. (2003). Green’s medical symptom validity test
(MSVT) for windows: User’s manual. Green’s Publishing.
Gu, H., Kong, W., Yin, H., & Zheng, Y. (2022). Prevalence of
sleep impairment in patients with tinnitus: A systematic
review and single-arm meta-analysis. European Archives
of Oto-Rhino-Laryngology, 279(5), 2211–2221. https://
doi.org/10.1007/s00405-021-07092-x
Hawker, G. A., Mian, S., Kendzerska, T., & French, M.
(2011). Measures of adult pain: Visual Analog Scale
for Pain (VAS Pain), Numeric Rating Scale for Pain
(NRS Pain), McGill Pain Questionnaire (MPQ), Short-
Form McGill Pain Questionnaire (SF-MPQ), Chronic
Pain Grade Scale (CPGS), Short Form-36 Bodily Pain
Scale (SF-36 BPS), and Measure of Intermittent and
Constant Osteoarthritis Pain (ICOAP). Arthritis Care
& Research, 63(S11), S240–S252. https://doi.org/10.
1002/acr.20543
Henry, G. K. (2005). Probable malingering and performance
on the test of variables of attention. The Clinical
Neuropsychologist, 19(1), 121–129. https://doi.org/10.
1080/13854040490516604
Henry, J. A., Griest, S. E., Blankenship, C., Thielman, E. J.,
Theodoroff, S. M., Hammill, T., & Carlson, K. F.
(2019). Impact of tinnitus on military service members.
Military Medicine, 184(Suppl. 1), 604–614. https://doi.
org/10.1093/milmed/usy328
Henry, J. A., Griest, S., Reavis, K. M., Grush, L., Theodoroff,
S. M., Young, S., Thielman, E. J., & Carlson, K. F. (2021).
Noise Outcomes in Servicemembers Epidemiology
(NOISE) study: Design, methods, and baseline results.
Ear and Hearing, 42(4), 870–885. https://doi.org/10.
1097/AUD.0000000000000974
Hinton, D. E., Chhean, D., Pich, V., Hofmann, S. G., &
Barlow, D. H. (2006). Tinnitus among Cambodian refu-
gees: Relationship to PTSD severity. Journal of
Traumatic Stress, 19(4), 541–546. https://doi.org/10.
1002/jts.20138
Holm, S. (1979). A simple sequentially rejective multiple
test procedure. Scandinavian Journal of Statistics, 6(2),
65–70.
Karch, S. J., Capó-Aponte, J. E., McIlwain, D. S., Lo, M.,
Krishnamurti, S., Staton, R. N., & Jorgensen-Wagers, K.
(2016). Hearing loss and tinnitus in military personnel
with deployment-related mild traumatic brain injury.
U.S. Army Medical Department Journal, (3–16), 52–63.
Kim, H.-J., Lee, H.-J., An, S.-Y., Sim, S., Park, B., Kim, S. W.,
Lee, J. S., Hong, S. K., & Choi, H. G. (2015). Analysis of
the prevalence and associated risk factors of tinnitus in
adults. PLoS One, 10(5), e0127578. https://doi.org/10.
1371/journal.pone.0127578
Knoll, R. M., Lubner, R. J., Brodsky, J. R., Wong, K., Jung, D.
H., Remenschneider, A. K., Herman, S. D., & Kozin, E. D.
(2020). Auditory quality-of-life measures in patients with
traumatic brain injury and normal pure tone audiometry.
Otolaryngology–Head and Neck Surgery, 163(6), 1250–
1254. https://doi.org/10.1177/0194599820933886
Kuchinsky, S. E., Eitel, M. M., Lange, R. T., French, L. M.,
Brickell, T. A., Lippa, S. M., & Brungart, D. S. (2020).
Objective and subjective auditory effects of traumatic brain injury and blast exposure in service members and
veterans. Frontiers in Neurology, 11, 613. https://doi.
org/10.3389/fneur.2020.00613
Langguth, B., & Gilles, A. (2024). Tinnitus questionnaires.
In W. Schlee, B. Langguth, D. De Ridder, S. Vanneste,
T. Kleinjung, & A. R. Møller (Eds.), Textbook of tinnitus
(pp. 329–343). Springer International Publishing. https://
doi.org/10.1007/978-3-031-35647-6_27
Lawrence, K. A., Garcia-Willingham, N. E., Slade, E.,
DeBeer, B. B., Meyer, E. C., & Morissette, S. B. (2023).
Associations among PTSD, cognitive functioning, and
health-promoting behavior in post-9/11 veterans.
Military Medicine, 188(7-8), e2284–e2291. https://doi.
org/10.1093/milmed/usad035
Le, M., Šarkić, B., & Anderson, R. (2024). Prevalence of tin-
nitus following non-blast related traumatic brain injury:
A systematic review of literature. Brain Injury, 38(11),
859–868. https://doi.org/10.1080/02699052.2024.2353798
Lind, M. J., Brown, E., Farrell-Carnahan, L., Brown, R. C.,
Hawn, S., Berenz, E., McDonald, S., Pickett, T.,
Danielson, C. K., Thomas, S., & Amstadter, A. B.
(2017). Sleep disturbances in OEF/OIF/OND veterans:
Associations with PTSD, personality, and coping.
Journal of Clinical Sleep Medicine, 13(2), 291–299.
https://doi.org/10.5664/jcsm.6466
MacGregor, A. J., Joseph, A. R., & Dougherty, A. L. (2020).
Prevalence of tinnitus and association with self-rated
health among military personnel injured on combat
deployment. Military Medicine, 185(9–10), e1608–
e1614. https://doi.org/10.1093/milmed/usaa103
Martz, E., Jelleberg, C., Dougherty, D. D., Wolters, C., &
Schneiderman, A. (2018). Tinnitus, depression, anxiety,
and suicide in recent veterans: A retrospective analysis.
Ear and Hearing, 39(6), 1046–1056. https://doi.org/10.
1097/AUD.0000000000000573
McCormack, A., Edmondson-Jones, M., Somerset, S., &
Hall, D. (2016). A systematic review of the reporting of
tinnitus prevalence and severity. Hearing Research, 337,
70–79. https://doi.org/10.1016/j.heares.2016.05.009
McGlinchey, R. E., Milberg, W. P., Fonda, J. R., & Fortier, C.
B. (2017). A methodology for assessing deployment
trauma and its consequences in OEF/OIF/OND veterans:
The TRACTS longitudinal prospective cohort study.
International Journal of Methods in Psychiatric
Research, 26(3), e1556. https://doi.org/10.1002/mpr.1556
Meikle, M. B., Henry, J. A., Griest, S. E., Stewart, B. J.,
Abrams, H. B., McArdle, R., Myers, P. J., Newman, C.
W., Sandridge, S., Turk, D. C., Folmer, R. L., Frederick,
E. J., House, J. W., Jacobson, G. P., Kinney, S. E., Martin,
W. H., Nagler, S. M., Reich, G. E., Searchfield, G., …
Vernon, J. A. (2012). The tinnitus functional index:
Development of a new clinical measure for chronic, intru-
sive tinnitus. Ear and Hearing, 33(2), 153–176. https://doi.
org/10.1097/AUD.0b013e31822f67c0
Melzack, R. (1975). The McGill Pain questionnaire: Major
properties and scoring methods. Pain, 1(3), 277–299.
https://doi.org/10.1016/0304-3959(75)90044-5
Melzack, R. (1987). The short-form McGill Pain question-
naire. Pain, 30(2), 191–197. https://doi.org/10.1016/
0304-3959(87)91074-8
Mohamad, N., Hoare, D. J., & Hall, D. A. (2016). The
consequences of tinnitus and tinnitus severity on
cognition: A review of the behavioural evidence. Hearing
Research, 332, 199–209. https://doi.org/10.1016/j.heares.
2015.10.001
Moring, J. C., Peterson, A. L., & Kanzler, K. E. (2018).
Tinnitus, traumatic brain injury, and posttraumatic stress
disorder in the military. International Journal of
Behavioral Medicine, 25(3), 312–321. https://doi.org/10.
1007/s12529-017-9702-z
Moring, J. C., Resick, P. A., Peterson, A. L., Husain, F. T.,
Esquivel, C., Young-McCaughan, S., Granato, E., & Fox,
P. T. (2022a). Treatment of posttraumatic stress disorder
alleviates tinnitus-related distress among veterans: A pilot
study. American Journal of Audiology, 31(4), 1293–1298.
https://doi.org/10.1044/2022_AJA-21-00241
Moring, J. C., Straud, C. L., Penzien, D. B., Resick, P. A.,
Peterson, A. L., Jaramillo, C. A., Eapen, B. C., McGeary,
C. A., Mintz, J., Litz, B. T., Young-McCaughan, S.,
Keane, T. M., & McGeary, D. D. (2022b). PTSD symp-
toms and tinnitus severity: An analysis of veterans with
posttraumatic headaches. Health Psychology, 41(3), 178–
183. https://doi.org/10.1037/hea0001113
National Institute on Deafness and Other Communication
Disorders. (2023, May 1). What is tinnitus? Causes and
treatment. https://www.nidcd.nih.gov/health/tinnitus.
Newman, C. W., Jacobson, G. P., & Spitzer, J. B. (1996).
Development of the tinnitus handicap inventory.
Archives of Otolaryngology–Head & Neck Surgery,
122(2), 143–148. https://doi.org/10.1001/archotol.1996.
01890140029007
Newman, C. W., Sandridge, S. A., & Jacobson, G. P. (1998).
Psychometric adequacy of the tinnitus handicap inven-
tory (THI) for evaluating treatment outcome. Journal of
the American Academy of Audiology, 9(2), 153–160.
Park, H.-M., Jung, J., Kim, J.-K., & Lee, Y.-J. (2022).
Tinnitus and its association with mental health and
health-related quality of life in an older population: A
nationwide cross-sectional study. Journal of Applied
Gerontology: The Official Journal of the Southern
Gerontological Society, 41(1), 181–186. https://doi.org/
10.1177/0733464820966512
Perneger, T. V. (1998). What’s wrong with Bonferroni
adjustments. BMJ, 316(7139), 1236–1238. https://doi.
org/10.1136/bmj.316.7139.1236
Prewitt, A., Harker, G., Gilbert, T. A., Hooker, E., O’Neil, M.
E., Reavis, K. M., Henry, J. A., & Carlson, K. F. (2021).
Mental health symptoms among veteran VA users by tin-
nitus severity: A population-based survey. Military
Medicine, 186(Suppl. 1), 167–175. https://doi.org/10.
1093/milmed/usaa288
Reisinger, L., Schmidt, F., Benz, K., Vignali, L., Roesch, S.,
Kronbichler, M., & Weisz, N. (2023). Ageing as risk fac-
tor for tinnitus and its complex interplay with hearing
loss – Evidence from online and NHANES data. BMC
Medicine, 21(1), 283. https://doi.org/10.1186/s12916-
023-02998-1
Rossiter, S., Stevens, C., & Walker, G. (2006). Tinnitus and
its effect on working memory and attention. Journal of
Speech, Language, and Hearing Research: JSLHR, 49(1),
150–160. https://doi.org/10.1044/1092-4388(2006/012)
Royston, P., Altman, D. G., & Sauerbrei, W. (2006).
Dichotomizing continuous predictors in multiple
regression: A bad idea. Statistics in Medicine, 25(1),
127–141. https://doi.org/10.1002/sim.2331
Shea, K., Vartanian, O., Rhind, S. G., Tenn, C., &
Nakashima, A. (2025). Impact of low-level blast exposure
from military training and career cumulation on hearing
outcomes. Military Medicine, 190(9–10), e1999–e2006.
https://doi.org/10.1093/milmed/usaf055
Stegeman, I., Eikelboom, R. H., Smit, A. L., Baguley, D. M.,
Bucks, R. S., Stokroos, R. J., Bennett, R. J., Tegg-Quinn, S.,
Hunter, M., & Atlas, M. D. (2021). Tinnitus and its
associations with general health, mental health and hearing loss. Progress in Brain Research, 262, 431–450.
https://doi.org/10.1016/bs.pbr.2021.01.023
Stuss, D. T., Ely, P., Hugenholtz, H., Richard, M. T.,
LaRochelle, S., Poirier, C. A., & Bell, I. (1985). Subtle neu-
ropsychological deficits in patients with good recovery
after closed head injury. Neurosurgery, 17(1), 41–47.
https://doi.org/10.1227/00006123-198507000-00007
Swan, A. A., Nelson, J. T., Swiger, B., Jaramillo, C. A., Eapen,
B. C., Packer, M., & Pugh, M. J. (2017). Prevalence of
hearing loss and tinnitus in Iraq and Afghanistan veter-
ans: A chronic effects of neurotrauma consortium
study. Hearing Research, 349, 4–12. https://doi.org/10.
1016/j.heares.2017.01.013
Terhaag, S., Phelps, A., Howard, A., O’Donnell, M., &
Cowlishaw, S. (2021). A longitudinal exploration of self-
reported hearing loss, tinnitus, and posttraumatic stress
disorder treatment outcomes in Australian veterans.
Psychosomatic Medicine, 83(8), 863–869. https://doi.org/
10.1097/PSY.0000000000000978
Theodoroff, S., Lewis, M., Folmer, R., Henry, J., & Carlson, J.
(2015). Hearing impairment and tinnitus: Prevalence,
risk factors, and outcomes in US service members and
veterans deployed to the Iraq and Afghanistan wars.
Epidemiologic Reviews, 37(1), 71–85. https://doi.org/10.
1093/epirev/mxu005
Theodoroff, S. M., & Konrad-Martin, D. (2020). Noise.
Otolaryngologic Clinics of North America, 53(4), 543–
553. https://doi.org/10.1016/j.otc.2020.03.004
U.S. Department of Veterans Affairs. (2024). Veterans
benefits administration annual benefits report fiscal year
2024. https://www.benefits.va.gov/REPORTS/abr/.
Üstün, T. B., Chatterji, S., Kostanjsek, N., Rehm, J.,
Kennedy, C., Epping-Jordan, J., Saxena, S., von Korff,
M., & Pull, C. (2010a). Developing the World Health
Organization disability assessment schedule 2.0. Bulletin
of the World Health Organization, 88(11), 815–823.
https://doi.org/10.2471/BLT.09.067231
Üstün, T. B., Kostanjsek, N., Chatterji, S., & Rhehm, J.
(Eds.). (2010b). Measuring health and disability:
Manual for WHO disability assessment schedule
(WHODAS 2.0). WHO Press.
Weathers, F. W., Bovin, M. J., Lee, D. J., Sloan, D. M., Schnurr,
P. P., Kaloupek, D. G., Keane, T. M., & Marx, B. P. (2018).
The clinician-administered PTSD scale for DSM-5 (CAPS-
5): Development and initial psychometric evaluation in
military veterans. Psychological Assessment, 30(3), 383–
395. https://doi.org/10.1037/pas0000486
Wechsler, D. (2008). Wechsler adult intelligence scale (man-
ual) (4th ed.). Psychological Corporation.
Weingarten, J. A., Islam, A., Dubrovsky, B., Gharanei, M., &
Coelho, D. H. (2024). The association of subjective and
objective sleep measures with chronic tinnitus. Journal
of Clinical Sleep Medicine, 20(3), 399–405. https://doi.
org/10.5664/jcsm.10882
Wolf, E. J., Hawn, S. E., Sullivan, D. R., Miller, M. W.,
Sanborn, V., Brown, E., Neale, Z., Fein-Schaffer, D.,
Zhao, X., Logue, M. W., Fortier, C. B., McGlinchey, R.
E., & Milberg, W. P. (2023). Neurobiological and genetic
correlates of the dissociative subtype of PTSD. Journal of
Psychopathology and Clinical Science, 132(4), 409–427.
https://doi.org/10.1037/abn0000795
Yang, D., Zhang, D., Zhang, X., & Li, X. (2024). Tinnitus-
associated cognitive and psychological impairments: A
comprehensive review meta-analysis. Frontiers in
Neuroscience, 18, 1275560. https://doi.org/10.3389/fnins.
2024.1275560"""

test27 = """Antal, C. J., Byrnes, J., Denton-Borhaug, K. & Saul, J. (2024).
Military moral injury: Current controversies and future
care. Current Treatment Options in Psychiatry, 11, 106–
122. https://doi.org/10.1007/s40501-024-00317-w
Antal, C. J., Yeomans, P. D., East, R., Hickey, D. W.,
Kalkstein, S., Brown, K. M., & Kaminstein, D. S. (2019).
Transforming veteran identity through community
engagement: A Chaplain–psychologist collaboration to
address moral injury. Journal of Humanistic Psychology,
63(6). https://doi.org/10.1177/0022167819844071
Backholm, K., & Idås, T. (2015). Ethical dilemmas, work-
related guilt, and posttraumatic stress reactions of news
journalists covering the terror attack in Norway in
2011. Journal of Traumatic Stress, 28(2), 142–148.
https://doi.org/10.1002/jts.22001
Belton, I., MacDonald, A., Wright, G., & Hamlin, I. (2019).
Improving the practical application of the Delphi method
in group-based judgment: A six-step prescription for a
well-founded and defensible process. Technological
Forecasting and Social Change, 147, 72–82. https://doi.
org/10.1016/j.techfore.2019.07.002
Berke, D. S., Carney, J. R., & Lebowitz, L. (2022). The role of
anger in traumatic harm and recovery for sexual violence
survivors. Journal of Trauma & Dissociation, 23(1), 24–
36. https://doi.org/10.1080/15299732.2021.1934937
Birch, M. J., Inhaber, J., & Ashbaugh, A. R. (2025). Morally
uncertain: The influence of intolerance of uncertainty
and perceived responsibility on moral pain. Anxiety,
Stress, & Coping, 38(4), 423–435. https://doi.org/10.
1080/10615806.2024.2423436
Borges, L. M., Barnes, S. M., Farnsworth, J. K., Drescher, K.
D., & Walser, R. D. (2022). Case conceptualizing in
acceptance and commitment therapy for moral injury:
An active and ongoing approach to understanding and
intervening on moral injury. Frontiers in Psychiatry, 13,
910414. https://doi.org/10.3389/fpsyt.2022.910414
Braun, V., & Clarke, V. (2006). Using thematic analysis in
psychology. Qualitative Research in Psychology, 3(2),
77–101. https://doi.org/10.1191/1478088706qp063oa
Brennan, C., & Cole, J. (2024). Post-traumatic embitterment
disorder in UK authorised firearms officers following
post-incident procedures: A cross-sectional web survey.
Journal of Police and Criminal Psychology, 39, 303–310.
https://doi.org/10.1007/s11896-023-09635-w
Brewin, C. R., Atwoli, L., Bisson, J. I., Galea, S., Koenen, K.,
& Lewis-Fernández, R. (2025). Post-traumatic stress dis-
order: Evolving conceptualization and evidence, and
future research directions. World Psychiatry, 24(1), 52–
80. https://doi.org/10.1002/wps.21269
Carmona-Perera, M., Marti-Garcia, C., Pérez-García, M., &
Verdejo-García, A. (2013). Valence of emotions and
moral decision-making: Increased pleasantness to plea-
sant images and decreased unpleasantness to unpleasant
images are associated with utilitarian choices in healthy adults. Frontiers in Human Neuroscience, 7, 626. https://
doi.org/10.3389/fnhum.2013.00626
Chalmers, J., & Armour, M. (2018). The Delphi technique.
In P. Liamputtong (Ed.), Handbook of research methods
in health social sciences (pp. 1–21). Springer. https://doi.
org/10.1007/978-981-10-2779-6_99-1
Cheng, J. S., Ottati, V. C., & Price, E. D. (2013). The arousal
model of moral condemnation. Journal of Experimental
Social Psychology, 49(6), 1012–1018. doi:10.1016/j.jesp.
2013.06.006
Courtois, C. A., & Brown, L. S. (2019). Guideline orthodoxy
and resulting limitations of the American Psychological
Association’s Clinical Practice Guideline for the
Treatment of PTSD in Adults. Psychotherapy, 56(3),
329–339. https://doi.org/10.1037/pst0000239
de la Viña, L., Garcia-Burgos, D., Okan, Y., Cándido, A., &
González, F. (2015). Disentangling the effect of valence
and arousal on judgments concerning moral transgres-
sions. The Spanish Journal of Psychology, 18, E61.
https://doi.org/10.1017/sjp.2015.66
Dohrenwend, B. P. (2010). Toward a typology of high-risk
major stressful events and situations in posttraumatic
stress disorder and related psychopathology.
Psychological Injury and Law, 3, 89–99. https://doi.org/
10.1007/s12207-010-9072-1
Easterbrook, B., Plouffe, R. A., Houle, S. A., Liu, A.,
McKinnon, M. C., Ashbaugh, A. R., Mota, N., Afifi, T.
O., Enns, M. W., Richardson, J. D., & Nazarov, A.
(2021). Moral injury associated with increased odds of
past-year mental health disorders: A Canadian Armed
Forces examination. European Journal of
Psychotraumatology, 14(1), 2192622. https://doi.org/10.
1080/20008066.2023.2192622
Ehring, T., & Quack, D. (2010). Emotion regulation difficul-
ties in trauma survivors: The role of trauma type and
PTSD symptom severity. Behavior Therapy, 41(4), 587–
598. doi:10.1016/j.beth.2010.04.004
Elbasheir, A., Bond, R., Harnett, N. G., Guelfo, A., Karkare,
M. C., Fulton, T. M., Ely, T. D., McDermott, T. J., Lanius,
R. A., Ahluwalia, V., Bradley, B., Siegle, G. J., & Fani, N.
(2024). Racial discrimination-Related interoceptive
network disruptions: A pathway to
disconnection. Biological Psychiatry: Cognitive
Neuroscience and Neuroimaging. https://doi.org/10.
1016/j.bpsc.2024.12.011
Farnsworth, J. K., Drescher, K. D., Evans, W., & Walser, R.
D. (2017). A functional approach to understanding and
treating military-related moral injury. Journal of
Contextual Behavioral Science, 6(4), 391–397. doi:10.
1016/j.jcbs.2017.07.003
Forbes, D., Elhai, J. D., Lockwood, E., Creamer, M., Frueh,
B. C., & Magruder, K. M. (2012). The structure of post-
traumatic psychopathology in veterans attending primary
care. Journal of Anxiety Disorders, 26(1), 95–101. https://
doi.org/10.1016/j.janxdis.2011.09.004
Frame, T. (2018). Moral injury and the influence of
Christian religious conviction. In R. E. Meagher, & D.
A. Pryer (Eds.), War and moral injury: A reader (pp.
187–196). Cascade Books.
Frankfurt, S. B., DeBeer, B. B., Morissette, S. B., Kimbrel, N.
A., Bash, L., Meyer, H., & C, E. (2018). Mechanisms of
moral injury following military sexual trauma and com-
bat in post-9/11 U.S. war Veterans. Frontiers in
Psychiatry, 9, 520. https://doi.org/10.3389/fpsyt.2018.
00520
Griffin, B. J., Purcell, N., Burkman, K., Litz, B. T., Bryan, C.
J., Schmitz, M., Villierme, C., Walsh, J., & Maguen, S.
(2019). Moral injury: An integrative review. Journal
of Traumatic Stress, 32(3), 350–362. doi:10.1002/jts.
22362
Griffin Weber, M. C., Hinkson, K. D., Jendro, A. M., Pyne, J.
M., Smith, A. J., Usset, T., Cucciare, M. A., Norman, S. B.,
Khan, A., Purcell, N., & Maguen, S. (2023). Toward a
dimensional contextual model of moral injury: A scoping
review on healthcare workers. Current Treatment Options
in Psychiatry, 10, 199–216. https://doi.org/10.1007/
s40501-023-00296-4
Haight, W., Sugrue, E. P., & Calhoun, M. (2017). Moral
injury among child protection professionals:
Implications for the ethical treatment and retention of
workers. Children and Youth Services Review, 82, 27–41.
https://doi.org/10.1016/j.childyouth.2017.08.030
Hall, N. A., Everson, A. T., Billingsley, M. R., & Miller, M. B.
(2022). Moral injury, mental health and behavioural
health outcomes: A systematic review of the literature.
Clinical Psychology & Psychotherapy, 29, 92–110.
https://doi.org/10.1002/cpp.2607
Herman, J. L. (2015). Trauma and recovery: The aftermath of
violence – from domestic abuse to political terror (2015
ed.). Basic Books.
Hertz, U., Snider, K. L., Levy, A., Canetti, D., & Gross, M. L.
(2022). To shoot or not to shoot: Experiments on moral
injury in the context of West Bank checkpoints and
COVID-19 restrictions enforcement. European Journal
of Psychotraumatology, 13(1), 2013651. https://doi.org/
10.1080/20008198.2021.2013651
Hoge, C. W., Chard, K. M., & Yehuda, R. (2024). US
Veterans affairs and department of defense 2023 clinical
guideline for PTSD—devolving not evolving. JAMA
Psychiatry, 81(3), 223–224. https://doi.org/10.1001/
jamapsychiatry.2023.4920
Houle, S. A., Ein, N., Gervasio, J., Plouffe, R. A., Litz, B. T.,
Carleton, R. N., Hansen, K. T., Liu, J. J. W., Ashbaugh, A.
R., Callaghan, W., Thompson, M. M., Easterbrook, B.,
Smith-MacDonald, L., Rodrigues, S., Bélanger, S. A. H.,
Bright, K., Lanius, R. A., Baker, C., Younger, W., …
Nazarov, A. (2024). Measuring moral distress and
moral injury: A systematic review and content analysis
of existing scales. Clinical Psychology Review, 108,
102377. https://doi.org/10.1016/j.cpr.2023.102377
Jordan, A. H., Eisen, E., Bolton, E., Nash, W. P., & Litz, B. T.
(2017). Distinguishing war-related PTSD resulting from
perpetration- and betrayal-based morally injurious
events.. Psychological Trauma: Theory, Research,
Practice, and Policy, 9(6), 627–634. https://doi.org/10.
1037/tra0000249
King, H. A., Perry, K. R., Ferguson, S., Hicken, B. L.,
Jackson, G. L., Lynch, C., Woolson, S. L., Wortmann, J.
H., Nieuwsma, J. A., & Parry, K. J. (2023). Identifying
potentially morally injurious events from the Veteran
perspective: A qualitative descriptive study. Journal of
Military, Veteran and Family Health, 9(2), 27–39.
https://doi.org/10.3138/jmvfh-2022-0049
Litz, B. T. (2025). Moral injury: State of the Science. Journal
of Traumatic Stress, 38(2), 187–199. https://doi.org/10.
1002/jts.23125
Litz, B. T., & Kerig, P. K. (2019). Introduction to the special
issue on moral injury: Conceptual challenges, methodo-
logical issues, and clinical applications. Journal of
Traumatic Stress, 32(3), 341–349. https://doi.org/10.
1002/jts.22405
Litz, B. T., & Walker, H. E. (2025). Moral injury: An over-
view of conceptual, definitional, assessment, and treat-
ment issues. Annual Review of Clinical Psychology, 21(1), 251–277. https://doi.org/10.1146/annurev-clinpsy-
081423-022604
Litz, B. T., Plouffe, R. A., Nazarov, A., Murphy, D., Phelps,
A., Coady, A., Houle, S. A., Dell, L., Frankfurt, S., Zerach,
G., Levi-Belz, Y., & the Moral Injury Outcome Scale
Consortium. (2022). Moral injury outcome scale consor-
tium. Defining and assessing the syndrome of moral
injury: Initial findings of the moral injury outcome
scale consortium. Frontiers in Psychiatry, 13. https://
www.frontiersin.org/articles/10.3389fpsyt.2022.923928
Litz, B. T., Stein, N., Delaney, E., Lebowitz, L., Nash, W. P.,
Silva, C., & Maguen, S. (2009). Moral injury and moral
repair in war veterans: A preliminary model and inter-
vention strategy. Clinical Psychology Review, 29(8), 695–
706. doi:10.1016/j.cpr.2009.07.003
Maguen, S., Griffin, B. J., Vogt, D., Hoffmire, C. A.,
Blosnich, J. R., Bernhard, P. A., Akhtar, F. Z., Cypel, Y.
S., & Schneiderman, A. I. (2023). Moral injury and
peri- and post-military suicide attempts among post-9/
11 veterans. Psychological Medicine, 53, 3200–3291.
https://doi.org/10.1017/S0033291721005274
Marx, B. P., Hall-Clark, B., Friedman, M. J., Holtzheimer, P.,
& Schnurr, P. P. (2024). The PTSD Criterion A debate: A
brief history, current status, and recommendations for
moving forward. Journal of Traumatic Stress, 37, 5–15.
https://doi.org/10.1002/jts.23007
McDonald, M. M., Defever, A. M., & Navarrete, C. D.
(2017). Killing for the greater good: Action aversion
and the emotional inhibition of harm in moral dilemmas.
Evolution and Human Behavior, 38(6), 770–778. doi:10.
1016/j.evolhumbehav.2017.06.001
Molendijk, T., Verkoren, W., Drogendijk, A., Elands, M.,
Kramer, E., Smit, A., & Verweij, D. (2022). Contextual
dimensions of moral injury: An interdisciplinary review.
Military Psychology, 34(6), 742–753. https://doi.org/10.
1080/08995605.2022.2035643
Morley, G., Ives, J., Bradbury-Jones, C., & Irvine, F. (2019).
What is ‘moral distress’? A narrative synthesis of the lit-
erature. Nursing Ethics, 26(3), 646–662. https://doi.org/
10.1177/0969733017724354
Nazarov, A., Fikretoglu, D., Liu, A., Thompson, M., &
Zamorski, M. A. (2018). Greater prevalence of post-trau-
matic stress disorder and depression in deployed
Canadian Armed Forces personnel at risk for moral
injury. Acta Psychiatrica Scandinavica, 137(4), 342–354.
https://doi.org/10.1111/acps.12866
Nazarov, A., Forchuk, C. A., Houle, S. A., Hansen, K. T.,
Plouffe, R. A., Liu, J. J. W., Dempster, K. S., Le, T.,
Kocha, I., Hosseiny, F., Heesters, A., & Richardson, J.
D. (2024). Exposure to moral stressors and associated
outcomes in healthcare workers: Prevalence, correlates,
and impact on job attrition. European Journal of
Psychotraumatology, 15(1), 2306102. https://doi.org/10.
1080/20008066.2024.2306102
Nickerson, A., Murphy, D., Phelps, A., Bryant, R. A.,
O’Donnell, M., Specker, P., Byrow, Y., Mau, V.,
McMahon, T., & Liddell, B. J. (2025). Moral injury
appraisals and complex PTSD in refugees: A longitudinal
study. Psychological Trauma: Theory, Research, Practice,
and Policy, 17(5), 1013–1022. https://doi.org/10.1037/
tra0001739
Niederberger, M., & Spranger, J. (2020). Delphi technique in
health sciences: A map. Frontiers in Public Health, 8, 457.
https://doi.org/10.3389/fpubh.2020.00457
Nordstrand, A. E., Noll, L. K., Huffman, A. H., Gjerstad, C. L.,
Tveitstul, T., Reichelt, J. G., Bakker, L.-P., Kennair, L. E. O.,
Kristoffersen, R. H., Bøe, H. J., & Wickham, R. E. (2025).
Killing in combat as a potentially morally injurious
event: The diverging psychological impact of killing on
peacekeepers and combat-oriented troops. Armed Forces
& Society (OnlineFirst). https://doi.org/10.1177/
0095327X251321389
Norman, S. B., Griffin, B. J., Pietrzak, R. H., McLean, C.,
Hamblen, J. L., & Maguen, S. (2024). The Moral Injury
and Distress Scale: Psychometric evaluation and initial
validation in three high-risk populations. Psychological
Trauma: Theory, Research, Practice, and Policy, 16(2),
280–291. https://doi.org/10.1037/tra0001533
O’Brien, S. F., Baptista, I., & Szeszko, P. R. (2024).
Enhancing conceptual clarity regarding the construct of
moral injury. Psychotherapy and Psychosomatics, 93(6),
376–385. https://doi.org/10.1159/000540030
Phelps, A. J., Adler, A. B., Belanger, S. A. H., Bennett, C.,
Cramm, H., Dell, L., Fikretoglu, D., Forbes, D., Heber,
A., Hosseiny, F., Morganstein, J. C., Murphy, D.,
Nazarov, A., Pedlar, D., Richardson, J. D., Sadler, N.,
Williamson, V., Greenberg, N, & Jetly, R. (2024).
Addressing moral injury in the military. BMJ Military
Health, 170, 51–55. https://doi.org/10.1136/bmjmilitary-
2022-002128
Purcell, N., Griffin, B. J., Burkman, K., & Maguen, S. (2018).
“Opening a door to a new life”: The role of forgiveness in
healing from moral injury. Frontiers in Psychiatry, 9, 498.
https://doi.org/10.3389/fpsyt.2018.00498
QSR International. (2017). NVivo (Version 12) [Qualitative
data analysis software].
Rachman, S. (2010). Betrayal: A psychological analysis.
Behaviour Research and Therapy, 48(4), 304–311.
https://doi.org/10.1016/j.brat.2009.12.002
Richardson, N. M., Lamson, A. L., Smith, M., Eagan, S. M.,
Zvonkovic, A. M., & Jensen, J. (2020). Defining moral
injury among military populations: A systematic review.
Journal of Traumatic Stress, 33(4), 575–586. https://doi.
org/10.1002/jts.22553
Sarkissian, M. L., & Yalch, M. M. (2024). Association
between betrayal trauma and typologies of anger and
aggression. European Journal of Trauma &
Dissociation, 8(4), 100466. https://doi.org/10.1016/j.
ejtd.2024.100466
Shay, J. (2014). Moral injury. Psychoanalytic Psychology,
31(2), 182–191. https://doi.org/10.1037/a0036090
Talbert, M., & Wolfendale, J. (2023). Moral injury, Moral
Suffering, and Moral Health. In J. T. McDaniel (Ed.),
Preventing and treating the invisible wounds of war:
Combat trauma, moral injury, and psychological health
(pp. 154–174). Oxford University Press.
ter Heide, J. J. (2020). Empathy is key in the development of
moral injury. European Journal of Psychotraumatology,
11(1), 1843261. https://doi.org/10.1080/20008198.2020.
1843261
ter Heide, J. J., & Olff, M. (2023). Widening the scope:
Defining and treating moral injury in diverse
populations. European Journal of Psychotraumatology,
14(2), 2196899. https://doi.org/10.1080/20008066.2023.
2196899
Tuomisto, M. T., & Roche, J. E. (2018). Beyond PTSD and
Fear-based conditioning: Anger-related responses follow-
ing experiences of forced migration—A systematic
review. Frontiers in Psychology, 9, 2592. https://doi.org/
10.3389/fpsyg.2018.02592
Turgoose, D., & Murphy, D. (2024). Associations between
adverse childhood experiences (ACEs) and complex-
PTSD, moral injury and perceived social support: A latent
class analysis. European Journal of Trauma & Dissociation, 8(4), 100463. https://doi.org/10.1016/j.ejtd.
2024.100463
Vermetten, E., Jones, C., MacDonald, S., ter Heide, J. J.,
Greenshaw, J. A., Brémault-Phillips, A. J. (2023).
Editorial: Emerging treatments and approaches for
moral injury and moral distress. Frontiers in Psychiatry,
14, 1125161. https://doi.org/10.3389/fpsyt.2023.1125161
Webb, E. L., Ireland, J. L., & Lewis, M. (2025). Defining and
identifying potentially morally injurious experiences for
secure mental healthcare workers: A Delphi study.
Journal of Criminological Research, Policy and Practice,
11(1), 64–80. https://doi.org/10.1108/JCRPP-03-2024-0021
Williamson, V., Murphy, D., Phelps, A., Forbes, D., &
Greenberg, N. (2021). Moral injury: The effect on mental
health and implications for treatment. The Lancet
Psychiatry, 8(6), 453–455. https://doi.org/10.1016/
S2215-0366(21)00113-9
Williamson, V., Stevelink, S. A. M., & Greenberg, N. (2018).
Occupational moral injury and mental health: Systematic
review and meta-analysis. The British Journal of
Psychiatry, 212(6), 339–346. doi:10.1192/bjp.2018.55
Zasiekina, L., Zasiekin, S., & ... Kuperman, V. (2023). Post-
traumatic stress disorder and moral injury among
Ukrainian Civilians during the ongoing War. Journal of
Community Health, 48(5), 784–792. https://doi.org/10.
1007/s10900-023-01225-5
Ziv, T. R. (2023). “I’m Trapped Here”: Ethnography, struc-
tural violence, and moral injury. Medicine Anthropology
Theory, 10(1), 1–13. https://doi.org/10.17157/mat.10.1.
6871"""

test28 = """Akinwunmi, B., Adeyanju, A. S., Arora, I. H., Quagliarini,
B., Agwu, O., Oladokun, A., & Dekel, S. (2025).
Peritraumatic dissociation during childbirth in Nigeria:
A preliminary study. International Journal of
Gynecology & Obstetrics, 171(1), 460–463. https://doi.
org/10.1002/ijgo.70214
Australian Capital Territory. (2021). The legislative assembly
for the Australian Capital Territory work health and safety
amendment bill 2021. https://www.legislation.act.gov.au/
a/2021-19/.
Australian Government. (2021). The framework surround-
ing the prevention, investigation and prosecution of indus-
trial deaths in Australia. https://www.aph.gov.au/
Parliamentary_Business/Committees/Senate/Education_
and_Employment/IndustrialdeathsinAus.
Barlé, N., Wortman, C. B., & Latack, J. A. (2017). Traumatic
bereavement: Basic research and clinical implications.
Journal of Psychotherapy Integration, 27(2), 127–139.
https://doi.org/10.1037/int0000013
Boelen, P. A., Olff, M., & Smid, G. E. (2019). Traumatic loss:
Mental health consequences and implications for treat-
ment and prevention. European Journal of
Psychotraumatology, 10(1), 1591331. https://doi.org/10.
1080/20008198.2019.1591331
Bolton, E., Holohan, D. R., King, L. A., & King, D. W.
(2004). Acute and post-traumatic stress disorder. In J.
C. Thomas (Ed.), Psychopathology in the workplace:
Recognition and adaptation (pp. 119–131). Brunner-
Routledge.
Brooks, S., Rubin, G. J., & Greenberg, N. (2019a). Managing
traumatic stress in the workplace. Occupational Medicine,
69(1), 2–4. https://doi.org/10.1093/occmed/kqy146
Brooks, S., Rubin, G. J., & Greenberg, N. (2019b). Traumatic
stress within disaster-exposed occupations: Overview of
the literature and suggestions for the management of
traumatic stress in the workplace. British Medical
Bulletin, 129(1), 35–51. https://doi.org/10.1093/bmb/
ldy040
Butler, L. D., Critelli, F. M., & Rinfrette, E. S. (2011, Juni 3).
Trauma-informed care and mental health. Directions in
Psychiatry, 31(3), 197–212.
Carlson, E. B., & Dalenberg, C. J. (2000). A conceptual
framework for the impact of traumatic experiences.
Trauma, Violence, & Abuse, 1(1), 4–28. https://doi.org/
10.1177/1524838000001001002
Carlson, E. B., Palmieri, P. A., Vogt, D., Macia, K., &
Lindley, S. E. (2023). Development and cross-validation
of a veterans mental health risk factor screen. PLoS
One, 18(2), e0272599. https://doi.org/10.1371/journal.
pone.0272599
Djelantik, A. A. A. M. J., Smid, G. E., Mroz, A., Kleber, R. J.,
& Boelen, P. A. (2020). The prevalence of prolonged grief
disorder in bereaved individuals following unnatural
losses: Systematic review and meta regression analysis.
Journal of Affective Disorders, 265, 146–156. https://doi.
org/10.1016/j.jad.2020.01.034
Huang, J. H., et al. (2013). Post-Traumatic stress disorder
status in a rescue group after the Wenchuan earthquake
relief. Neural Regeneration Research [MUMBAI], 8(20),
1898–1906. https://doi.org/10.3969/j.issn.1673-5374.
2013.20.009
International Labor Organisation. (2023). Safety & Health at
Work. https://www.ilo.org/global/topics/safety-and-
health-at-work/lang–en/index.htm.
Jordan, N. N., Hoge, C. W., Tobler, S. K., Wells, J., Dydek,
G. J., & Egerton, W. E. (2004). Mental health impact of
9/11 Pentagon attack. American Journal of Preventive
Medicine, 26(4), 284–293. https://doi.org/10.1016/j.
amepre.2004.01.005
Katz, S. (2022). We need to talk about trauma:
Integratingtrauma-Informedpractice into the family law
classroom. Family Court Review, 60(4), 757–776.
https://doi.org/10.1111/fcre.12674
Labra-Valerdi, P., Chacón-Moscoso, S., & Sanduvete-
Chaves, S. (2021). Predictive factors of mental health in
survivors of intimate partner violence in Chile. Journal
of Interpersonal Violence, 37(21-22), NP19447–
NP19467. https://doi.org/10.1177/08862605211042810
Lacerte, S., Guay, S., Beaulieu-Prévost, D., Belleville, G., &
Marchand, A. (2017). Quality of life in workplace trauma
victims seeking treatment for posttraumatic stress dis-
order. Journal of Workplace Behavioral Health, 32(4),
249–266. https://doi.org/10.1080/15555240.2017.1370379
Lewis, G. W. (2012). Critical incident stress and trauma in
the workplace: Recognition, response, recovery. Routledge.
Matthews, L. R., Bohle, P., Quinlan, M., & Rawlings-Way,
O. (2012). Traumatic death at work: Consequences for
surviving families. International Journal of Health
Services, 42(4), 647–666. https://doi.org/10.2190/HS.42.
4.e
Matthews, L. R., Finney Lamb, C. F., Jessup, G. M., Ngo, M.,
& Quinlan, M. (2024). Family accounts of their experi-
ences and expectations of authorities following sudden
workplace death in Queensland, Australia. Victims &
Offenders, 19(7), 1320–1349. https://doi.org/10.1080/
15564886.2022.2053257
McCready, A. M., Rowan-Kenyon, H. T., Barone, N. I., &
Martínez Alemán, A. M. (2021). Students of color,
mental health, and racialized aggressions on social
media. Journal of Student Affairs Research and
Practice, 58(2), 179–195. https://doi.org/10.1080/
19496591.2020.1853555
Northern Territory of Australia. (2022). Northern Territory
of Australia work health and safety amendment act 2019.
https://legislation.nt.gov.au/en/Bills/Work-Health-and-
Safety-National-Uniform-Legislation-Amendment-Bill-
2019-S-103?format=assented.
Oxburgh, G. E., Myklebust, T., & Grant, T. (2010). The ques-
tion of question types in police interviews: A review of the
literature from a psychological and linguistic perspective.
International Journal of Speech, Language and the Law,
17(1), 45–66. https://doi.org/10.1558/ijsll.v17i1.45
Parliament of Victoria. (2021). Occupational health and
safety act 2004. https://www.legislation.vic.gov.au/in-
force/acts/occupational-health-and-safety-act-2004/037.
Rawlings, J., Muir, C., & Ayton, D. (2025). Beyond the inci-
dent: Examining criminal and coronial court documents
to explore the impact of workplace fatalities on
coworkers. Illness, Crisis & Loss, https://doi.org/10.
1177/10541373251321154
Reicherter, D., Wang, S. R., Ohrtman, T. N., Ndukwe, N.,
Vaatainen, S., Alcalay, S., & Brown, L. M. (2022).
Implementation of trauma-informed best practices for
international criminal investigations conducted by the
United Nations investigative team to promote account-
ability for crimes committed by da’esh/ISIL (UNITAD).
Psychological Injury and Law, 15(4), 319–329. https://
doi.org/10.1007/s12207-022-09457-x
Safe Work Australia. (2021). Implementation of WHS
Ministers’ Agreed Response to the Review of the Model
WHS Laws. https://www.safeworkaustralia.gov.au/law-
and-regulation/model-whs-laws/implementation-whs-
ministers-agreed-response-review-model-whs-laws.
Safe work Australia. (2022). Work-Related Traumatic Injury
Fatality Time Series. https://www.safeworkaustralia.gov.
au/doc/work-related-traumatic-injury-fatality-time-series.
Senate Education and Employment Committees. (2018).
They never came home—The framework surrounding
the prevention, investigation and prosecution of
industrial deaths in Australia. https://www.aph.gov.au/
Parliamentary_Business/Committees/Senate/Education_
and_Employment/IndustrialdeathsinAus/Report.
Shalev, A. Y., & Barbano, A. C. (2019). PTSD: Risk assess-
ment and early management. Psychiatric Annals, 49(7),
299–306. https://doi.org/10.3928/00485713-20190605-01
Soueid, M., et al. (2018). The survivor-centred approach
to transitional justice: Why a trauma-informed handling of
witness testimony is a necessary component. George
Washington International Law Review, 50(1), 125–179.
Spivack, L. P., & Saini, M. (2025). Reimagining family
courts: Integrating trauma-informed care for healthier
legal outcomes. Juvenile and Family Court Journal,
https://doi.org/10.1111/jfcj.70015
State of New South Wales. (2024). Work health and
safety amendment (industrial manslaughter) act 2024
No 43. https://legislation.nsw.gov.au/view/pdf/asmade/act-
2024-43.
State of Queensland. (2024). Queensland work health and
safety act 2011. https://www.legislation.qld.gov.au/view/
pdf/inforce/current/act-2011-018.
State of South Australia. (2024). Industrial manslaughter.
https://www.safework.sa.gov.au/enforcement/industrial-
manslaughter.
State of Tasmania. (2024). New industrial manslaughter
laws 2024. https://worksafe.tas.gov.au/topics/laws-and-
compliance/acts-and-regulations/new-industrial-mans
laughter-laws-2024.
State of Western Australia. (2020). Work health and safety
act 2020. https://www.legislation.wa.gov.au/legislation/
statutes.nsf/law_a147282.html.
Tehrani, N. (2004). Workplace trauma: Concepts, assessment
and interventions. Brunner-Routledge.
Thompson, N. (2009). Loss, grief, and trauma in the work-
place (1st ed.). Baywood Publishing.
Thompson, N., & Bevan, D. (2015). Death and the work-
place. Illness, Crisis & Loss, 23(3), 211–225. https://doi.
org/10.1177/1054137315585445
Vivona, B. D., & Ty, R. (2011). Traumatic death in the work-
place: Why should human resource development care?
Advances in Developing Human Resources, 13(1), 99–
113. https://doi.org/10.1177/1523422311410654
Wilson, P., Dzansi, G., & Ohene, L. A. (2020). ‘I don’t want
to think about it’: Psychosocial experiences of road traffic
accident survivors in Ghana. International Emergency
Nursing, 53, 100935. https://doi.org/10.1016/j.ienj.2020.
100935
World Health Organization. (2021a). WHO/ILO: Almost 2
Million people die from work related causes each year.
https://www.who.int/news/item/17-09-2021-who-ilo-
almost-2-million-people-die-from-work-related-causes-
each-year.
World Health Organization. (2021b). WHO/ILO Joint
Estimates of the Work-Related Burden of Disease and
Injury, 2000–2016: Global monitoring report. https://iris.
who.int/bitstream/handle/10665/345242/9789240034945-
eng.pdf."""

test29 = """Aldao, A., Nolen-Hoeksema, S., & Schweizer, S. (2010).
Emotion-regulation strategies across psychopathology:
A meta-analytic review. Clinical Psychology Review,
30(2), 217–237. https://doi.org/10.1016/j.cpr.2009.11.004
American Psychiatric Association. (2013). Diagnostic and
statistical manual of mental disorders (5th ed.).
American Psychiatric Publishing.
Berking, M. & Whitley, B. (2014). The adaptive coping with
emotions model (ACE Model). In: Affect regulation train-
ing. New York, NY: Springer. https://doi.org/10.1007/
978-1-4939-1022-9_3.
Braet, C., Cracco, E., Theuwis, L., Grob, A., & Smolenski, C.
(2013). FEEL-KJ: vragenlijst over emotieregulatie bij kin-
deren en jongeren. Hogrefe.
Brooks, S. K., Weston, D., Wessely, S., & Greenberg, N.
(2021). Effectiveness and acceptability of brief psychoe-
ducational interventions after potentially traumatic
events: A systematic review. European Journal of
Psychotraumatology, 12(1), 1–13. https://doi.org/10.
1080/20008198.2021.1923110
Burns, B. J., Phillips, S. D., Wagner, H. R., Barth, R. P.,
Kolko, D. J., Campbell, Y., & Landsverk, J. (2004).
Mental health need and access to mental health services
by youths involved with child welfare: A national survey.
Journal of the American Academy of Child and Adolescent
Psychiatry, 43, 960–970. https://doi.org/10.1097/01.chi.
0000127590.95585.65
Children’s Bureau. (2025). Adoption and Foster Care
Analysis and Reporting System (AFCARS), Foster Care
AB File 2024 (Version 1) [Data set]. National Data
Archive on Child Abuse and Neglect. https://doi.org/10.
34681/6SQY-9149.
Cohen, J. A., Mannarino, A. P., & Deblinger, E. (2021).
Behandeling van trauma bij kinderen en adolescenten. Met
de methode Traumagerichte Cognitieve Gedragstherapie.
BSL.
Coppens, L., & Kregten, C. (2018). Zorgen voor getraumati-
seerde kinderen: een training voor opvoeders. BSL.
Cracco, E., Van Durme, K., & Braet, C. (2015). Validation
of the FEEL-KJ: An instrument to measure emotion
regulation strategies in children and adolescents. PLoS
One, 10(9), 1–18. https://doi.org/10.1371/journal.pone.
0137080
Deblinger, E., Mannarino, A. P., Cohen, J. A., Runyon, M.
K., & Steer, R. A. (2011). Trauma-focused cognitive
behavioral therapy for children: impact of the trauma
narrative and treatment length. Depression and Anxiety,
28(1), 67–75.
DeNigris, P. N. (2008). Trauma in youth: Reactions and
interventions. The Journal of Psychiatry & Law, 36(2),
211–243. https://doi.org/10.1177/009318530803600204
Diehle, J., Opmeer, B. C., Boer, F., Mannarino, A. P., &
Lindauer, R. J. (2015). Trauma-focused cognitive behav-
ioral therapy or eye movement desensitization and repro-
cessing: What works in children with posttraumatic stress
symptoms? A randomized controlled trial. European
Child & Adolescent Psychiatry, 24(2), 227–236. https://
doi.org/10.1007/s00787-014-0572-5
Dorsey, S., McLaughlin, K. A., Kerns, S. E. U., Harrison, J.
P., Lambert, H. K., Briggs, E., Revillion Cox, J., &
Amaya-Jackson, L. (2016). Evidence base update for psy-
chosocial treatments for children and adolescents
exposed to traumatic events. Journal of Clinical Child &
Adolescent Psychology, 46(3), 303–330. https://doi.org/
10.1080/15374416.2016.1220309
Dubner, A. E., & Motta, R. W. (1999). Sexually and phys-
ically abused foster care children and posttraumatic stress
disorder. Journal of Consulting and Clinical Psychology,
67(3), 367–373. https://doi.org/10.1037/0022-006X.67.3.
367
Ehring, T., Welboren, R., Morina, N., Wicherts, J. M.,
Freitag, J., & Emmelkamp, P. M. (2014). Meta-analysis
of psychological treatments for posttraumatic stress dis-
order in adult survivors of childhood abuse. Clinical
Psychology Review, 34(8), 645–657. https://doi.org/10.
1016/j.cpr.2014.10.004
Felitti, V. J., Anda, R. F., Nordenberg, D., Williamson, D. F.,
Spitz, A. M., Edwards, V., & Marks, J. S. (1998).
Relationship of childhood abuse and household dysfunc-
tion to many of the leading causes of death in adults: The
Adverse Childhood Experiences (ACE) Study. American
Journal of Preventive Medicine, 14(4), 245–258. https://
doi.org/10.1016/S0749-3797(98)00017-8
Gigengack, M. R., Hein, I. M., Lindeboom, R., & Lindauer,
R. J. L. (2017). Increasing resource parents’ sensi-
tivity towards child posttraumatic stress symptoms: A
descriptive study on a trauma-informed resource parent
training. Journal of Child & Adolescent Trauma, 12(1),
23–29. https://doi.org/10.1007/s40653-017-0162-z
Greenwald, R. (2013). Behandeling van gedragsproblemen.
Een traumageorienteerde behandering. LanooCampus.
Grob, A., & Smolenski, C. (2005). Fragebogen zur Erhebung
der Emotionsregulation bei Kindern und Jugendlichen
(FEEL-KJ). Verlag Hans Huber. http://edoc.unibas.ch/
dok/A6223168.
Holt, T., Cohen, J., Mannarino, A., & Jensen, T. K. (2014).
Parental emotional response to children’s traumas.
Journal of Aggression, Maltreatment & Trauma, 23(10),
1057–1071. https://doi.org/10.1080/10926771.2014.953717
ISTSS Guidelines Commitee. (2019). ISTSS PTSD guidelines,
methodology and recommendations.
Junghänel, M., Wand, H., Dose, C., Thöne, A. K., Treier, A.
K., Hanisch, C., Ritschel, A., Kölch, M., Lincke, L.,
Roessner, V., Kohls, G., Ravens-Sieberer, U., Kaman,
A., Banaschewski, T., Aggensteier, P. M., Görtz-Dorten,
A., & Döpfner, M. (2022). Validation of a new emotion
regulation self-report questionnaire for children. BMC
Psychiatry, 22(1), 820. https://doi.org/10.1186/s12888-
022-04440-x
Knipschild, R., Hein, I., Pieters, S., Lindauer, R., Bicanic, I.
A., Staal, W., de Jongh, A., & Klip, H. (2024).
Childhood adversity in a youth psychiatric population:
Prevalence and associated mental health problems.
European Journal of Psychotraumatology, 15(1), 1–9.
https://doi.org/10.1080/20008066.2024.2330880
Konijn, C., Admiraal, S., Baart, J., van Rooij, F., Stams, G. J.,
Colonnesi, C., Lindauer, R. J. L., & Assink, M. (2019).
Foster care placement instability: A meta-analytic review.
Children and Youth Services Review, 96, 483–499. https://
doi.org/10.1016/j.childyouth.2018.12.002
Kooij, L. H., Hein, I. M., Sachser, C., Bouwmeester, S., Bosse,
M., & Lindauer, R. J. L. (2025). Psychometric accuracy of
the Dutch Child and Adolescent Trauma Screener.
European Journal of Psychotraumatology, 16(1), 1–15.
https://doi.org/10.1080/20008066.2025.2450985
Kooij, L. H., Van der Pol, T. M., Daams, J. G., Hein, I. M., &
Lindauer, R. J. (2022). Common elements of evidence-
based trauma therapy for children and adolescents.
European Journal of Psychotraumatology, 13(1), 1–12.
https://doi.org/10.1080/20008198.2022.2079845
Liming, K. W., Akin, B., & Brook, J. (2021). Adverse
childhood experiences and foster care placement stability. Pediatrics, 148(6), 1–9. https://doi.org/10.1542/peds.202
1-052700
Lindauer, R. J. L., & De Boer, F. (2020). Trauma bij kinde-
ren. LannooCampus.
Lorbeer, N., Knaevelsrud, C., & Niemeyer, H. (2023). STAIR
and STAIR/NT as a treatment for posttraumatic stress: A
systematic review. Verhaltenstherapie, 33(2-3), 53–63.
https://doi.org/10.1159/000526592
Lotty, M., Dunn-Galvin, A., & Bantry-White, E. (2020 Apr).
Effectiveness of a trauma-informed care psychoeduca-
tional program for foster carers - evaluation of the
Fostering Connections Program. Child Abuse & Neglect,
102, 104390. https://doi.org/10.1016/j.chiabu.2020.
104390. Epub 2020 Feb 7. PMID: 32036290.
Morris, A. S., Silk, J. S., Steinberg, L., Myers, S. S., &
Robinson, L. R. (2007). The role of the family context
in the development of emotion regulation. Social
Development, 16(2), 361–388. https://doi.org/10.1111/j.
1467-9507.2007.00389.x
Muris, P., Meesters, C., & Van den Berg, F. (2003). The
Strengths and Difficulties Questionnaire (SDQ). Further
evidence for its reliability and validity in a community
sample of Dutch children and adolescents. European
Child & Adolescent Psychiatry, 12(1), 1–8. https://doi.
org/10.1007/s00787-003-0298-2
National Institute for Health and Care Excellence (NICE).
(2018). Post-traumatic stress disorder (NICE guideline
NG116). https://www.nice.org.uk/guidance/ng116
Ormhaug, S. M., & Jensen, T. K. (2016). Investigating
treatment characteristics and first-session relationship
variables as predictors of dropout in the treatment
of traumatized youth. Psychotherapy Research, 28(2),
235–249. https://doi.org/10.1080/10503307.2016.1189617
Ormhaug, S. M., & Jensen, T. K. (2018). Investigating
treatment characteristics and first-session relationship
variables as predictors of dropout in the treatment
of traumatized youth. Psychotherapy Research,
28(2), 235–249. https://doi.org/10.1080/10503307.2016.
1189617
Oswald, S. H., Heil, K., & Goldbeck, L. (2010). History of
maltreatment and mental health problems in foster chil-
dren: A review of the literature. Journal of Pediatric
Psychology, 35(5), 462–472. https://doi.org/10.1093/
jpepsy/jsp114
Pace, C. S., Muzi, S., Moretti, M., & Barone, L. (2024 February
8). Supporting adoptive and foster parents of adolescents
through the trauma-informed e-Connect parent group:
A preliminary descriptive study. Frontiers in Psychology,
15, 1266930. https://doi.org/10.3389/fpsyg.2024.1266930.
PMID: 38390418; PMCID: PMC10882096.
Petruccelli, K., Davis, J., & Berman, T. (2019). Adverse child-
hood experiences and associated health outcomes: A sys-
tematic review and meta-analysis. Child Abuse & Neglect,
97, 104127. https://doi.org/10.1016/j.chiabu.2019.104127
Pineles, S. L., Mostoufi, S. M., Ready, C. B., Street, A. E.,
Griffin, M. G., & Resick, P. A. (2011). Trauma reactivity,
avoidant coping, and PTSD symptoms: A moderating
relationship? Journal of Abnormal Psychology, 120(1),
240. https://doi.org/10.1037/a0022123
Pleegzorg Nederland. (2024). Factsheet Pleegzorg 2023 [Fact
sheet]. https://www.pleegzorg.nl/bibliotheek/1-wat-is-ple
egzorg/37-feiten-en-cijfers-over-pleegzorg.
Sachser, C., Berliner, L., Holt, T., Jensen, T. K., Jungbluth,
N., Risc, E., Rosner, R., & Goldbeck, L. (2017).
International development and psychometric properties
of the Child and Adolescent Trauma Screen (CATS).
Journal of Affective Disorders, 210, 189–195. https://doi.
org/10.1016/j.jad.2016.12.040
Schlattmann, N., Goris, M., Regoli-Bakker, S., & Lindauer,
R. J. L. (2023a). Tem je Draak: Versterkende groepstrain-
ing voor getraumatiseerde kinderen. Levvel.
Schlattmann, N., van der Hoeven, M. L., & Hein, I. M.
(2023b). IGT-K. Integratieve gehechtheidsbevorderende
traumabehandeling voor kinderen. BSL.
Strijker, J., Knorth, E. J., & Knot-Dickscheit, J. (2008).
Placement history of foster children. Child Welfare,
87(5), 107–124. https://www.jstor.org/stable/48623168.
Struik, A. (2018). The Sleeping Dog Method to overcome
children’s resistance to EMDR Therapy: A case series.
Journal of EMDR Practice and Research, 12(4), 224–241.
https://doi.org/10.1891/1933-3196.12.4.224
Struik, A. (2021). Slapende Honden? Wakker maken! Een
behandelmethode voor chronisch getraumatiseerde kinde-
ren. Pearson.
Teculeasa, F., Golu, F., & Gorbănescu, A. (2023 June 30).
The effectiveness of psychological interventions on the
impact of trauma exposure in foster care: A meta-analy-
sis. Journal of Child & Adolescent Trauma, 16(4), 917–
932. https://doi.org/10.1007/s40653-023-00563-9. PMID:
38045839; PMCID: PMC10689601.
Thornback, K., & Muller, R. T. (2015). Relationships among
emotion regulation and symptoms during trauma-
focused CBT for school-aged children. Child Abuse &
Neglect, 50, 182–192.
van der Hoeven, M. L., Assink, M., Stams, G. J. J., Daams, J.
G., Lindauer, R. J., & Hein, I. M. (2023a). Victims of child
abuse dropping out of trauma-focused treatment: A
meta-analysis of risk factors. Journal of Child &
Adolescent Trauma, 16(2), 269–283. https://doi.org/10.
1007/s40653-022-00500-2
van der Hoeven, M. L., Plukaard, S. C., Schlattmann, N. E.,
Lindauer, R. J., & Hein, I. M. (2023b). An integrative treat-
ment model of EMDR and family therapy for children
with severe symptomatology after child abuse and neglect:
A SCED study. Children and Youth Services Review, 152,
107064. https://doi.org/10.1016/j.childyouth.2023.107064
Van Widenfelt, B. M., Goedhart, A. W., Treffers, P. D. A., &
Goodman, R. (2003). Dutch version of the strengths and
difficulties questionnaire (SDQ). European Child &
Adolescent Psychiatry, 12(6), 281–289. https://doi.org/
10.1007/s00787-003-0341-3
Visser, I., van der Mheen, M., Dorsman, H., Knipschild, R.,
Staaks, J., Hein, I., Van Dongen, N., Staal, W., Assink, M.,
& Lindauer, R. J. L. (2025). Post-traumatic stress disorder
rates in trauma-exposed children and adolescents:
Updated three-level meta-analysis. The British Journal
of Psychiatry, 2025, 1–9. https://doi.org/10.1192/bjp.
2025.30
Yasinski, C., Hayes, A. M., Alpert, E., McCauley, T., Ready,
C. B., Webb, C., & Deblinger, E. (2018). Treatment
processes and demographic variables as predictors of
dropout from trauma-focused cognitive behavioral
therapy (TF-CBT) for youth. Behaviour Research and
Therapy, 107, 10–18. https://doi.org/10.1016/j.brat.2018.
05.008
Zeanah, C. H., Scheeringa, M., Boris, N. W., Heller, S. S.,
Smyke, A. T., & Trapani, J. (2004). Reactive attachment
disorder in maltreated toddlers. Child Abuse & Neglect,
28(8), 877–888. https://doi.org/10.1016/j.chiabu.2004.01.010"""

test30 = """Agyapong, B., Obuobi-Donkor, G., Burback, L., & Wei, Y.
(2022). Stress, burnout, anxiety and depression among
teachers: A scoping review. International Journal of
Environmental Research and Public Health, 19(17),
10706. https://doi.org/10.3390/ijerph191710706
American Psychiatric Association. (2013). Diagnostic and
statistical manual of mental disorders. https://doi.org/10.
1176/appi.books.9780890425596
Anderson, T. (2021). Chapter 4: Indigenous youth in
Canada. In Portrait of youth in Canada: Data report
(pp. 1–18). https://www150.statcan.gc.ca/n1/en/pub/42-
28-0001/2021001/article/00004-eng.pdf?st = VhXLzzOM
Banaji, M. R., Fiske, S. T., & Massey, D. S. (2021). Systemic
racism: Individuals and interactions, institutions and
society. Cognitive Research: Principles and Implications,
6(1), 82. https://doi.org/10.1186/s41235-021-00349-3
Braveman, P. A., Arkin, E., Proctor, D., Kauh, T., & Holm,
N. (2022). Systemic and structural racism: Definitions,
examples, health damages, and approaches to disman-
tling. Health Affairs, 41(2), 171–178. https://doi.org/10.
1377/hlthaff.2021.01394
Brondolo, E., Libretti, M., Rivera, L., & Walsemann, K. M.
(2012). Racism and social capital: The implications for
social and physical well-being. Journal of Social Issues, 68(2), 358–384. https://doi.org/10.1111/j.1540-4560.
2012.01752.x
Brown, D. L., & Tylka, T. L. (2011). Racial discrimination
and resilience in African American young adults:
Examining racial socialization as a moderator. Journal
of Black Psychology, 37(3), 259–285. https://doi.org/10.
1177/0095798410390689
Carter, P. L. (2022). Systemic racism in education requires
multidimensional solutions. In Systemic racism in
America (pp. 73–91). Routledge.
Carter, R. T. (2007). Racism and psychological and
emotional injury: Recognizing and assessing race-based
traumatic stress. The Counseling Psychologist, 35(1), 13–
105. https://doi.org/10.1177/0011000006292033
Carter, R. T., Kirkinis, K., & Johnson, V. E. (2020).
Relationships between trauma symptoms and race-
based traumatic stress. Traumatology, 26(1), 11–18.
https://doi.org/10.1037/trm0000217
Cénat, J. M. (2023). Complex racial trauma: Evidence, the-
ory, assessment, and treatment. Perspectives on
Psychological Science, 18(3), 675–687. https://doi.org/10.
1177/17456916221120428
Cénat, J. M., Blais, M., Hébert, M., Lavoie, F., & Guerrier, M.
(2015). Correlates of bullying in Quebec high school stu-
dents: The vulnerability of sexual-minority youth. Journal
of Affective Disorders, 183, 315–321. https://doi.org/10.
1016/j.jad.2015.05.011
Cénat, J. M., Broussard, C., Jacob, G., Kogan, C., Corace, K.,
Ukwu, G., Onesi, O., Furyk, S. E., Bekarkhanechi, F. M.,
Williams, M., Chomienne, M.-H., Grenier, J., & Labelle,
P. R. (2024). Antiracist training programs for mental
health professionals: A scoping review. Clinical
Psychology Review, 108, Article 102373. https://doi.org/
10.1016/j.cpr.2023.102373
Cénat, J. M., Haeny, A. M., & Williams, M. T. (2024).
Providing antiracist cognitive-behavioral therapy:
Guidelines, tools, and tips. Psychiatry Research, 339,
Article 116054. https://doi.org/10.1016/j.psychres.2024.
116054
Cénat, J. M., Hajizadeh, S., Dalexis, R. D., Ndengeyingoma,
A., Guerrier, M., & Kogan, C. (2022). Prevalence and
effects of daily and major experiences of racial discrimi-
nation and microaggressions among black individuals
in Canada. Journal of Interpersonal Violence, 37(17–18),
NP16750–NP16778. https://doi.org/10.1177/0886260521
1023493
Cénat, J. M., Kogan, C., Noorishad, P., Hajizadeh, S.,
Dalexis, R. D., Ndengeyingoma, A., & Guerrier, M.
(2021). Prevalence and correlates of depression among
Black individuals in Canada: The major role of everyday
racial discrimination. Depression and Anxiety, 38(9),
886–895. https://doi.org/10.1002/da.23158
Cénat, J. M., Manoni-Millar, S., David, A., Darius, W. P.,
Kogan, C. S., & Dalexis, R. D. (2025). Barriers to mental
health care for Black youth in Canada: A socioecological
perspective. Canadian Psychology / Psychologie
Canadienne. https://doi.org/10.1037/cap0000419
Cénat, J. M., Moshirian Farahi, S. M. M., & Dalexis, R. D.
(2023). Prevalence and determinants of depression,
anxiety, and stress symptoms among Black individuals
in Canada in the context of the COVID-19 pandemic.
Psychiatry Research, 326, 1–9. https://doi.org/10.1016/j.
psychres.2023.115341
Chapman-Hilliard, C., Abdullah, T., Denton, E., Holman,
A., & Awad, G. (2020). The index of race-related stress-
brief: Further validation, cross-validation, and item
response theory-based evidence. Journal of Black
Psychology, 46(6–7), 550–580. https://doi.org/10.1177/
0095798420947508
Chavez-Dueñas, N. Y., Adames, H. Y., Perez-Chavez, J. G.,
& Salas, S. P. (2019). Healing ethno-racial trauma in
Latinx immigrant communities: Cultivating hope, resist-
ance, and action. American Psychologist, 74(1), 49–62.
https://doi.org/10.1037/amp0000289
Chen, S. M., Zhang, Y., & Wang, Y. B. (2019). Individual
differences in relative fertility costs and fertility benefits
and their effects on fertility desire for a second child in
China: A latent profile analysis. Reproductive Health,
16(1), 1–9. https://doi.org/10.1186/s12978-019-0770-1
Clark, E. C., Cranston, E., Polin, T., Ndumbe-Eyoh, S.,
MacDonald, D., Betker, C., & Dobbins, M. (2022).
Structural interventions that affect racial inequities and
their impact on population health outcomes: A systema-
tic review. BMC Public Health, 22(1), 2162. https://doi.
org/10.1186/s12889-022-14603-w
Comas-Díaz, L. (2016). Racial trauma recovery: A race-
informed therapeutic approach to racial wounds. In The
cost of racism for people of color: Contextualizing experiences
of discrimination (pp. 249–272). American Psychological
Association. https://doi.org/10.1037/14852-012
Comas-Díaz, L., Hall, G. N., & Neville, H. A. (2019). Racial
trauma: Theory, research, and healing: Introduction to
the special issue. American Psychologist, 74(1), 1–5.
https://doi.org/10.1037/amp0000442
Dalexis, R. D., Muray, M., Kibret, T. C., Farahi, S. M. M. M.,
& Cénat, J. M. (2025). Factors related to COVID-19 vac-
cine effectiveness perception in racially diverse adults in
Canada. Vaccine, 62, Article 127498. https://doi.org/10.
1016/j.vaccine.2025.127498
Dean, L. T., & Thorpe, R. J. (2022). What structural racism is
(or is not) and how to measure it: Clarity for public health
and medical researchers. American Journal of
Epidemiology, 191(9), 1521–1526. https://doi.org/10.
1093/aje/kwac112
ElTohamy, A., Hyun, S., Rastogi, R., Finneas Wong, G. T.,
Kim, G. S., Chae, D. H., Hahm, H. “C.”, & Liu, C. H.
(2024). Effect of vicarious discrimination on race-based
stress symptoms among Asian American young adults
during the COVID-19 pandemic. Psychological Trauma:
Theory, Research, Practice, and Policy, 16(2), 217–224.
https://doi.org/10.1037/tra0001480
Fitzgerald, H. E., Johnson, D. J., Allen, J., Villarruel, F. A., &
Qin, D. B. (2021). Historical and race-based trauma:
Resilience through family and community. Adversity
and Resilience Science, 2(4), 215–223. https://doi.org/10.
1007/s42844-021-00048-4
Frost, D. M., & Meyer, I. H. (2023). Minority stress theory:
Application, critique, and continued relevance. Current
Opinion in Psychology, 51, Article 101579. https://doi.
org/10.1016/j.copsyc.2023.101579
Gangloff, E. J., & Greenberg, N. (2023). Biology of stress. In
C. Warwick, P. C. Arena, & G. M. Burghardt (Eds.),
Health and welfare of captive reptiles (pp. 93–142).
Springer International Publishing.
Harrell, S. P. (2000). A multidimensional conceptualization
of racism-related stress: Implications for the well-being of
people of color. American Journal of Orthopsychiatry,
70(1), 42–57. https://doi.org/10.1037/h0087722
Havnen, A., Anyan, F., Hjemdal, O., Solem, S., Gurigard
Riksfjord, M., & Hagen, K. (2020). Resilience moderates
negative outcome from stress during the COVID-19 pan-
demic: A moderated-mediation approach. International
Journal of Environmental Research and Public Health,
17(18), 6461. https://doi.org/10.3390/ijerph17186461
Hobson, J. M., Moody, M. D., Sorge, R. E., & Goodin, B. R.
(2022). The neurobiology of social stress resulting from
racism: Implications for pain disparities among racialized
minorities. Neurobiology of Pain, 12, Article 100101.
https://doi.org/10.1016/j.ynpai.2022.100101
Holmes, S. C., Zare, M., Haeny, A. M., & Williams, M. T.
(2024). Racial stress, racial trauma, and evidence-based
strategies for coping and empowerment.. Annual
Review of Clinical Psychology, 20(1), 77–95. https://doi.
org/10.1146/annurev-clinpsy-081122-020235
Huang, C.-J., Webb, H. E., Zourdos, M. C., & Acevedo, E. O.
(2013). Cardiovascular reactivity, stress, and physical
activity. Frontiers in Physiology, 4, 1–13. https://doi.org/
10.3389/fphys.2013.00314
Jones, J. M. (2023). Surviving while black: Systemic racism
and psychological resilience. Annual Review of
Psychology, 74(1), 1–25. https://doi.org/10.1146/
annurev-psych-020822-052232
Jones, S. C. T., Simon, C. B., Yadeta, K., Patterson, A., &
Anderson, R. E. (2023). When resilience is not enough:
Imagining novel approaches to supporting Black youth
navigating racism. Development and Psychopathology,
35(5), 2132–2140. https://doi.org/10.1017/S095457942
3000986
Khachatryan, K., Otten, D., Beutel, M. E., Speerforck, S.,
Riedel-Heller, S. G., Ulke, C., & Brähler, E. (2023).
Mental resources, mental health and sociodemography:
A cluster analysis based on a representative population
survey in a large German city. BMC Public Health,
23(1), 1827. https://doi.org/10.1186/s12889-023-16714-4
Kogan, C. S., Noorishad, P.-G., Ndengeyingoma, A.,
Guerrier, M., & Cénat, J. M. (2022). Prevalence and cor-
relates of anxiety symptoms among Black people in
Canada: A significant role for everyday racial discrimi-
nation and racial microaggressions. Journal of Affective
Disorders, 308, 545–553. https://doi.org/10.1016/j.jad.
2022.04.110
Lee, R. T., Perez, A. D., Boykin, C. M., & Mendoza-Denton,
R. (2019). On the prevalence of racial discrimination in
the United States. PLoS One, 14(1), e0210698. https://
doi.org/10.1371/journal.pone.0210698
Lovibond, P. F., & Lovibond, S. H. (1995). Manual for the
depression anxiety stress scales (2nd ed.). Psychology
Foundation.
Markin, R. D., Kivlighan, M., Pérez-Rojas, A. E., & Phelps,
R. (2023). Introduction to special section: Addressing
racism, anti-blackness, and racial trauma in psychother-
apy. Psychotherapy, 60(1), 24–26. https://doi.org/10.
1037/pst0000470
McEwen, B. S. (2017). Neurobiological and systemic effects
of chronic stress. Chronic Stress, 1, 1–11. https://doi.org/
10.1177/2470547017692328
McVittie, J., & Ansloos, J. (2025). Feeling the structural:
School-based educators’ perspectives on indigenous
child suicidality in Canada. International Journal of
Social Determinants of Health and Health Services, 55(3),
318–329. https://doi.org/10.1177/27551938251327904
Meyer, I. H. (2003). Prejudice, social stress, and mental
health in lesbian, gay, and bisexual populations:
Conceptual issues and research evidence. Psychological
Bulletin, 129(5), 674–697. https://doi.org/10.1037/0033-
2909.129.5.674
Moshirian Farahi, S. M. M., & Cénat, J. M. (2025). Racial
disparities in the prevalence and determinants of anxiety
symptoms among Arab, Asian, Black, Indigenous, White
and mixed-racial individuals in Canada: The major role
of racial discrimination. Psychiatry Research, 353,
Article 116710. https://doi.org/10.1016/j.psychres.2025.
116710
Moshirian Farahi, S. M. M., Dalexis, R. D., Beogo, I.,
Gakima, L., & Cénat, J. M. (2025). COVID-19 vaccine
confidence among parents of racially diverse
children aged 0–12 years old in Canada: The role of
major experience of racial discrimination, health literacy,
and conspiracy beliefs. Human Vaccines &
Immunotherapeutics, 21(1), Article 2484895. https://doi.
org/10.1080/21645515.2025.2484895
Moshirian Farahi, S. M. M., Xu, Y., Dort, J., Caulley, L.,
Beogo, I., Dalexis, R. D., & Cénat, J. M. (2025).
Factors associated with COVID-19 vaccine confidence
among Arab, Asian, Black, Indigenous, and White indi-
viduals in Canada: Latent profile analyses. Vaccine, 61,
Article 127358. https://doi.org/10.1016/j.vaccine.2025.
127358
Pager, D., & Shepherd, H. (2008). The sociology of discrimi-
nation: Racial discrimination in employment, housing,
credit, and consumer markets. Annual Review of
Sociology, 34(1), 181–209. https://doi.org/10.1146/
annurev.soc.33.040406.131740
Rowe, S., & Ansloos, J. P. (2024). Understanding suicide
from an indigenous cultural lens: Insights from elders
in Canada. Journal of Religion and Health, 63(2), 1038–
1057. https://doi.org/10.1007/s10943-024-02022-7
Saleem, F. T., Anderson, R. E., & Williams, M. (2020).
Addressing the “myth” of racial trauma: Developmental
and ecological considerations for youth of color.
Clinical Child and Family Psychology Review, 23(1), 1–
14. https://doi.org/10.1007/s10567-019-00304-1
Samuels-Wortley, K. (2021). To serve and protect whom?
Using composite counter-storytelling to explore black
and indigenous youth experiences and perceptions of
the police in Canada. Crime & Delinquency, 67(8),
1137–1164. https://doi.org/10.1177/0011128721989077
Selye, H. (2013). Stress in health and disease. Butterworth-
Heinemann.
Spence, N. D., Wells, S., Graham, K., & George, J. (2016).
Racial discrimination, cultural resilience, and stress. The
Canadian Journal of Psychiatry, 61(5), 298–307. https://
doi.org/10.1177/0706743716638653
St John, V. J., & Nemati, D. (2024). Fortifying physical
and psychological wellbeing: Leveraging capital for
resilience against racism and adversity across racial
groups. Journal of Racial and Ethnic Health Disparities,
12(6), 4227–4261. https://doi.org/10.1007/s40615-024-
02215-6
Sternthal, M. J., Slopen, N., & Williams, D. R. (2011). Racial
disparities in health. Du Bois Review: Social Science
Research on Race, 8(1), 95–113. https://doi.org/10.1017/
S1742058X11000087
Taylor, R. J., Forsythe-Brown, I., Mouzon, D. M., Keith, V.
M., Chae, D. H., & Chatters, L. M. (2019). Prevalence and
correlates of everyday discrimination among black
Caribbeans in the United States: The impact of nativity
and country of origin. Ethnicity & Health, 24(5), 463–
483. https://doi.org/10.1080/13557858.2017.1346785
Tibshirani, R., Walther, G., & Hastie, T. (2001). Estimating
the number of clusters in a data set via the gap statistic.
Journal of the Royal Statistical Society Series B:
Statistical Methodology, 63(2), 411–423. https://doi.org/
10.1111/1467-9868.00293
Utsey, S. O., & Ponterotto, J. G. (1996). Development and
validation of the Index of Race-Related Stress (IRRS).
Journal of Counseling Psychology, 43(4), 490–501.
https://doi.org/10.1037/0022-0167.43.4.490
Vaishnavi, S., Connor, K., & Davidson, J. R. T. (2007). An
abbreviated version of the Connor-Davidson Resilience
Scale (CD-RISC), the CD-RISC2: Psychometric proper-
ties and applications in psychopharmacological trials.
Psychiatry Research, 152(2–3), 293–297. https://doi.org/
10.1016/j.psychres.2007.01.006
Waddimba, A. C., Baker, B. M., Pogue, J. R., McAuliffe, M.
P., Bennett, M. M., Baxter, R. D., Mohr, D. C., & Warren,
A. M. (2022). Psychometric validity and reliability of the
10- and 2-item Connor–Davidson Resilience Scales
among a national sample of Americans responding to
the COVID-19 pandemic: An item response theory
analysis. Quality of Life Research, 31(9), 2819–2836.
https://doi.org/10.1007/s11136-022-03125-y
Waelde, L. C., Pennington, D., Mahan, C., Mahan, R.,
Kabour, M., & Marquett, R. (2010). Psychometric proper-
ties of the Race-Related Events Scale. Psychological
Trauma: Theory, Research, Practice, and Policy, 2(1), 4–
11. https://doi.org/10.1037/a0019018
Wilcox, M. M. (2023). Oppression is not “culture”: The need
to center systemic and structural determinants to address
anti-Black racism and racial trauma in psychotherapy.
Psychotherapy, 60(1), 76–85. https://doi.org/10.1037/
pst0000446
Williams, D. R. (2018). Stress and the mental health of popu-
lations of color: Advancing our understanding of race-
related stressors. Journal of Health and Social Behavior,
59(4), 466–485. https://doi.org/10.1177/0022146518814251
Williams, D. R., & Etkins, O. S. (2021). Racism and mental
health. World Psychiatry, 20(2), 194–195. https://doi.org/
10.1002/wps.20845
Williams, D. R., & Mohammed, S. A. (2009).
Discrimination and racial disparities in health:
Evidence and needed research. Journal of Behavioral
Medicine, 32(1), 20–47. https://doi.org/10.1007/s10865-
008-9185-0
Williams, M. T., Faber, S. C., & Duniya, C. (2022). Being
an anti-racist clinician. The Cognitive Behaviour
Therapist, 15, e19. https://doi.org/10.1017/S1754470X22
000162
Williams, M. T., Metzger, I. W., Leins, C., & DeLapp, C.
(2018). Assessing racial trauma within a DSM-5 frame-
work: The UConn Racial/Ethnic Stress & Trauma
Survey. Practice Innovations, 3(4), 242–260. https://doi.
org/10.1037/pri0000076
Wong, C. F., Schrager, S. M., Holloway, I. W., Meyer, I. H.,
& Kipke, M. D. (2014). Minority stress experiences and
psychological well-being: The impact of support from
and connection to social networks within the Los
Angeles house and ball communities. Prevention
Science, 15(1), 44–55. https://doi.org/10.1007/s11121-
012-0348-4
Yip, T., Gee, G. C., & Takeuchi, D. T. (2008). Racial dis-
crimination and psychological distress: The impact of
ethnic identity and age among immigrant and United
States-born Asian adults. Developmental Psychology,
44(3), 787–800. https://doi.org/10.1037/0012-1649.44.3.
787
Youssef, N. A., Belew, D., Hao, G., Wang, X., Treiber, F. A.,
Stefanek, M., Yassa, M., Boswell, E., McCall, W. V., & Su,
S. (2017). Racial/ethnic differences in the association of
childhood adversities with depression and the role of resi-
lience. Journal of Affective Disorders, 208, 577–581.
https://doi.org/10.1016/j.jad.2016.10.024
Zanon, C., Brenner, R. E., Baptista, M. N., Vogel, D. L.,
Rubin, M., Al-Darmaki, F. R., Gonçalves, M., Heath, P.
J., Liao, H.-Y., Mackenzie, C. S., Topkaya, N., Wade, N.
G., & Zlati, A. (2021). Examining the dimensionality,
reliability, and invariance of the Depression, Anxiety,
and Stress Scale–21 (DASS-21) across eight countries.
Assessment, 28(6), 1531–1544. https://doi.org/10.1177/
1073191119887449"""

test31 = """Amato, M. P., Goretti, B., Ghezzi, A., Lori, S., Zipoli, V., Moiola, L.,
Falautano, M., De Caro, M. F., Viterbo, R., Patti, F., Vecchio, R., Pozzilli,
C., Bianchi, V., Roscio, M., Martinelli, V., Comi, G., Portaccio, E.,
Trojano, M., & the Multiple Sclerosis Study Group of the Italian
Neurological Society. (2010). Cognitive and psychosocial features in
childhood and juvenile MS: Two-year follow-up. Neurology, 75(13),
1134–1140. https://doi.org/10.1212/WNL.0b013e3181f4d821
Amato, M. P., Goretti, B., Ghezzi, A., Lori, S., Zipoli, V., Portaccio, E., Moiola,
L., Falautano, M., De Caro, M. F., Lopez, M., Patti, F., Vecchio, R., Pozzilli,
C., Bianchi, V., Roscio, M., Comi, G., Trojano, M., & the Multiple Sclerosis
Study Group of the Italian Neurological Society. (2008). Cognitive and
psychosocial features of childhood and juvenile MS. Neurology, 70(20),
1891–1897. https://doi.org/10.1212/01.wnl.0000312276.23177.fa
Amato, M. P., Ponziani, G., Siracusa, G., & Sorbi, S. (2001). Cognitive
dysfunction in early-onset multiple sclerosis: A reappraisal after 10 years.
Archives of Neurology, 58(10), 1602–1606. https://doi.org/10.1001/
archneur.58.10.1602
Amunts, J., Camilleri, J. A., Eickhoff, S. B., Heim, S., & Weis, S. (2020).
Executive functions predict verbal fluency scores in healthy participants.
Scientific Reports, 10(1), Article 11141. https://doi.org/10.1038/s41598-
020-65525-9
Arnett, P. A., Smith, M. M., Barwick, F. H., Benedict, R. H. B., & Ahlstrom,
B. P. (2008). Oralmotor slowing in multiple sclerosis: Relationship to
neuropsychological tasks requiring an oral response. Journal of the
International Neuropsychological Society, 14(3), 454–462. https://
doi.org/10.1017/S1355617708080508
Arroyo-Anlló, E. M., Lorber, M., Rigaleau, F., & Gil, R. (2012). Verbal
fluency in Alzheimer’s disease and Aphasia. Dementia, 11(1), 5–18.
https://doi.org/10.1177/1471301211416609
Baciu, M., Boudiaf, N., Cousin, E., Perrone-Bertolotti, M., Pichat, C.,
Fournet, N., Chainay, H., Lamalle, L., & Krainik, A. (2016). Functional
MRI evidence for the decline of word retrieval and generation during
normal aging. Age, 38(1), Article 3. https://doi.org/10.1007/s11357-015-
9857-y
Barabási, A.-L. (2016). Network science. Cambridge University Press.
Beatty, W. W., Goodkin, D. E., Beatty, P. A., & Monson, N. (1989). Frontal
lobe dysfunction and memory impairment in patients with chronic pro-
gressive multiple sclerosis. Brain and Cognition, 11(1), 73–86. https://
doi.org/10.1016/0278-2626(89)90006-7
Belke, E., Meyer, A. S., & Damian, M. F. (2005). Refractory effects in
picture naming as assessed in a semantic blocking paradigm. Quarterly
Journal of Experimental Psychology A: Human Experimental Psychology,
58(4), 667–692. https://doi.org/10.1080/02724980443000142
Benton, A. L., Hamsher, K., & Sivan, A. B. (1983). Controlled oral word
association test (COWAT). Multilingual aphasia examination (3rd ed.).
AJA Associates.
Brandstadter, R., Fabian, M., Leavitt, V. M., Krieger, S., Yeshokumar,
A., Katz Sand, I., Klineova, S., Riley, C. S., Lewis, C., Pelle, G.,
Lublin, F. D., Miller, A. E., & Sumowski, J. F. (2020). Word-finding
difficulty is a prevalent disease-related deficit in early multiple scle-
rosis. Multiple Sclerosis, 26(13), 1752–1764. https://doi.org/10.1177/
1352458519881760
Burke, D. M., MacKay, D. G., & James, L. E. (2000). Theoretical approaches
to language and aging. In T. J. Perfect & E. A. Maylor (Eds.), Models of
cognitive aging (pp. 204–237). Oxford University Press. https://doi.org/10
.1093/oso/9780198524380.003.0008
Burke, D. M., MacKay, D. G., Worthley, J. S., & Wade, E. (1991). On the tip
of the tongue: What causes word finding failures in young and older
adults? Journal of Memory and Language, 30(5), 542–579. https://
doi.org/10.1016/0749-596X(91)90026-G
Castro, N. (2022). Methodological considerations for incorporating clinical
data into a network model of retrieval failures. Topics in Cognitive
Science, 14(1), 111–126. https://doi.org/10.1111/tops.12531
Castro, N., & Vitevitch, M. S. (2023). Using network science and psy-
cholinguistic megastudies to examine the dimensions of phonological
similarity. Language and Speech, 66(1), 143–174. https://doi.org/10
.1177/00238309221095455
Chen, Q., & Mirman, D. (2012). Competition and cooperation among similar
representations: Toward a unified account of facilitative and inhibitory
effects of lexical neighbors. Psychological Review, 119(2), 417–430.
https://doi.org/10.1037/a0027175
Chiaravalloti, N. D., & DeLuca, J. (2008). Cognitive impairment in multiple
sclerosis. The Lancet Neurology, 7(12), 1139–1151. https://doi.org/10
.1016/S1474-4422(08)70259-X
Chiaravalloti, N. D., Moore, N. B., Nikelshpur, O. M., & DeLuca, J. (2013).
An RCT to treat learning impairment in multiple sclerosis: The
MEMREHAB trial. Neurology, 81(24), 2066–2072. https://doi.org/10
.1212/01.wnl.0000437295.97946.a8
Cosgrove, A. L., Beaty, R. E., Diaz, M. T., & Kenett, Y. N. (2023). Age
differences in semantic network structure: Acquiring knowledge shapes
semantic memory. Psychology and Aging, 38(2), 87–102. https://doi.org/
10.1037/pag0000721
Cosgrove, A. L., Kenett, Y. N., Beaty, R. E., & Diaz, M. T. (2021).
Quantifying flexibility in thought: The resiliency of semantic networks
differs across the lifespan. Cognition, 211, Article 104631. https://doi.org/
10.1016/j.cognition.2021.104631
Diaz, M. T., Karimi, H., Troutman, S. B. W., Gertel, V. H., Cosgrove, A. L.,
& Zhang, H. (2021). Neural sensitivity to phonological characteristics is
stable across the lifespan. NeuroImage, 225, Article 117511. https://
doi.org/10.1016/j.neuroimage.2020.117511
Diaz, M. T., Zhang, H., Cosgrove, A. L., Gertel, V. H., Troutman, S. B. W.,
& Karimi, H. (2022). Neural sensitivity to semantic neighbors is stable
across the adult lifespan. Neuropsychologia, 171, Article 108237. https://
doi.org/10.1016/j.neuropsychologia.2022.108237
Dubossarsky, H., De Deyne, S., & Hills, T. T. (2017). Quantifying the
structure of free association networks across the life span. Developmental
Psychology, 53(8), 1560–1570. https://doi.org/10.1037/dev0000347
Dvorak, E., Levy, S., Anderson, J. R., & Sumowski, J. F. (2024). Phonemic
processing is below expectations and linked to word-finding difficulty in
multiple sclerosis. Multiple Sclerosis, 30(10), 1374–1378. https://doi.org/
10.1177/13524585241259648
Eijlers, A. J. C., Dekker, I., Steenwijk, M. D., Meijer, K. A., Hulst, H. E.,
Pouwels, P. J. W., Uitdehaag, B. M. J., Barkhof, F., Vrenken, H.,
Schoonheim, M. M., & Geurts, J. J. G. (2019). Cortical atrophy accelerates
as cognitive decline worsens in multiple sclerosis. Neurology, 93(14),
e1348–e1359. https://doi.org/10.1212/WNL.0000000000008198
El-Wahsh, S., Bogaardt, H., Kumfor, F., & Ballard, K. (2020). Development
and validation of the communication and language assessment ques-
tionnaire for persons with multiple sclerosis (CLAMS). Multiple Sclerosis
and Related Disorders, 43, Article 102206. https://doi.org/10.1016/j.msa
rd.2020.102206
Friesen, D. C., Luo, L., Luk, G., & Bialystok, E. (2015). Proficiency and
control in verbal fluency performance across the lifespan for monolinguals
and bilinguals. Language, Cognition and Neuroscience, 30(3), 238–250.
https://doi.org/10.1080/23273798.2014.918630
Galioto, R., Macaron, G., Lace, J. W., Ontaneda, D., & Rao, S. M. (2021). Is
computerized screening for processing speed impairment sufficient for
identifying MS-related cognitive impairment in a clinical setting? Multiple
Sclerosis and Related Disorders, 54, Article 103106. https://doi.org/10
.1016/j.msard.2021.103106
Gordon, J. K., Young, M., & Garcia, C. (2018). Why do older adults have
difficulty with semantic fluency? Aging, Neuropsychology, and Cognition,
Neuropsychology and Cognition, 25(6), 803–828. https://doi.org/10.1080/
13825585.2017.1374328
Gray, K., Anderson, S., Chen, E. E., Kelly, J. M., Christian, M. S., Patrick, J.,
Huang, L., Kenett, Y. N., & Lewis, K. (2019). “Forward flow”: A new
measure to quantify free thought and predict creativity. American
Psychologist, 74(5), 539–554. https://doi.org/10.1037/amp0000391
Grezmak, T., Lace, J. W., Nakamura, K., Ontaneda, D., & Galioto, R. (2023).
“It’s on the tip of my tongue!” exploring confrontation naming difficulties
in patients with multiple sclerosis. Multiple Sclerosis and Related
Disorders, 71, Article 104579. https://doi.org/10.1016/j.msard.2023
.104579
Grigoriadis, P., Bakirtzis, C., Nteli, E., Boziki, M.-K., Kotoumpa, M.,
Theotokis, P., Kesidou, E., & Stavrakaki, S. (2024). Morphosyntactic
abilities and cognitive performance in multiple sclerosis. Brain Sciences,
14(3), Article 237. https://doi.org/10.3390/brainsci14030237
Henry, J. D., & Beatty, W. W. (2006). Verbal fluency deficits in multiple
sclerosis. Neuropsychologia, 44(7), 1166–1174. https://doi.org/10.1016/j
.neuropsychologia.2005.10.006
Horakova, D., Dwyer, M. G., Havrdova, E., Cox, J. L., Dolezal, O.,
Bergsland, N., Rimes, B., Seidl, Z., Vaneckova, M., & Zivadinov, R.
(2009). Gray matter atrophy and disability progression in patients with
early relapsing-remitting multiple sclerosis: A 5-year longitudinal study.
Journal of the Neurological Sciences, 282(1–2), 112–119. https://doi.org/
10.1016/j.jns.2008.12.005
Howard, D., Nickels, L., Coltheart, M., & Cole-Virtue, J. (2006). Cumulative
semantic inhibition in picture naming: Experimental and computational
studies. Cognition, 100(3), 464–482. https://doi.org/10.1016/j.cognition
.2005.02.006
Iva, P., Fielding, J., Clough, M., White, O., Godic, B., Martin, R., & Rajan,
R. (2020). Speech discrimination tasks: A sensitive sensory and cognitive
measure in early and mild multiple sclerosis. Frontiers in Neuroscience,
14, Article 604991. https://doi.org/10.3389/fnins.2020.604991
Jakimovski, D., Weinstock-Guttman, B., Roy, S., Jaworski, M., III,
Hancock, L., Nizinski, A., Srinivasan, P., Fuchs, T. A., Szigeti, K.,
Zivadinov, R., & Benedict, R. H. B. (2019). Cognitive profiles of aging in
multiple sclerosis. Frontiers in Aging Neuroscience, 11, Article 105.
https://doi.org/10.3389/fnagi.2019.00105
Kavé, G. (2005). Phonemic fluency, semantic fluency, and difference scores:
Normative data for adult Hebrew speakers. Journal of Clinical and
Experimental Neuropsychology, 27(6), 690–699. https://doi.org/10.1080/
13803390490918499
Kavé, G., & Halamish, V. (2015). Doubly blessed: Older adults know more
vocabulary and know better what they know. Psychology and Aging,
30(1), 68–73. https://doi.org/10.1037/a0038669
Kavé, G., & Knafo-Noam, A. (2015). Lifespan development of phonemic
and semantic fluency: Universal increase, differential decrease. Journal of
Clinical and Experimental Neuropsychology, 37(7), 751–763. https://
doi.org/10.1080/13803395.2015.1065958
Kroll, J. F., & Stewart, E. (1994). Category interference in translation and
picture naming: Evidence for asymmetric connection between bilingual
memory representations. Journal of Memory and Language, 33(2), 149–
174. https://doi.org/10.1006/jmla.1994.1008
Lacour, A., De Seze, J., Revenco, E., Lebrun, C., Masmoudi, K., Vidry,
E., Rumbach, L., Chatel, M., Verier, A., & Vermersch, P. (2004). Acute
aphasia in multiple sclerosis: A multicenter study of 22 patients.
Neurology, 62(6), 974–977. https://doi.org/10.1212/01.WNL.0000115169.
23421.5D
Lebkuecher, A. L., Chiaravalloti, N. D., & Strober, L. B. (2021). The role of
language ability in verbal fluency of individuals with multiple sclerosis.
Multiple Sclerosis and Related Disorders, 50, Article 102846. https://
doi.org/10.1016/j.msard.2021.102846
Lebkuecher, A. L., Cosgrove, A. L., Strober, L. B., Chiaravalloti, N. D., &
Diaz, M. T. (2024). Multiple sclerosis is associated with differences in
semantic memory structure. Neuropsychology, 38(1), 42–57. https://
doi.org/10.1037/neu0000924
Martzoukou, M., Nousia, A., Messinis, L., Konstantopoulos, K., & Nasios,
G. (2025). Language and cognitive impairments in multiple sclerosis: A
comparative study of RRMS and SPMS patients. Archives of Clinical
Neuropsychology, 40(4), 775–782. https://doi.org/10.1093/arclin/ac
ae110
Mirman, D. (2011). Effects of near and distant semantic neighbors on word
production. Cognitive, Affective & Behavioral Neuroscience, 11(1), 32–
43. https://doi.org/10.3758/s13415-010-0009-7
Mirman, D., & Magnuson, J. S. (2008). Attractor dynamics and semantic
neighborhood density: Processing is slowed by near neighbors and
speeded by distant neighbors. Journal of Experimental Psychology:
Learning, Memory, and Cognition, 34(1), 65–79. https://doi.org/10.1037/
0278-7393.34.1.65
Monsch, A. U., Bondi, M. W., Butters, N., Salmon, D. P., Katzman, R.,
& Thal, L. J. (1992). Comparisons of verbal fluency tasks in the
detection of dementia of the Alzheimer type. Archives of Neurology,
49(12), 1253–1258. https://doi.org/10.1001/archneur.1992.0053036
0051017
Pitteri, M., Vannucci, M., Dapor, C., Guandalini, M., Daffinà, A., Marastoni,
D., & Calabrese, M. (2023). Prominent role of executive functioning on
the phonemic fluency test in people with multiple sclerosis. Journal of the
International Neuropsychological Society, 29(9), 902–906. https://
doi.org/10.1017/S1355617723000139
Rahimifar, P., Isazadeh, R., Soltani, M., Ghobadi, R., Boazar, A., Abaeian,
G., Aliabdi, L., Majdinasab, N., & Amini, P. (2025). Examination of high-
level language skills in 2 phases of multiple sclerosis (relapsing-remitting
& secondary progressive) in comparison with healthy counterparts.
Medical Journal of the Islamic Republic of Iran, 39, Article 22. https://
doi.org/10.47176/mjiri.39.22
Rahnemayan, S., Fathalizadeh, A., Behroozi, M., Talebi, M., Naseri, A.,
& Mehdizadehfar, E. (2025). FMRI insights into the neural alterations
and clinical correlates in multiple sclerosis: A comprehensive over-
view of systematic reviews and meta-analyses. Brain Research
Bulletin, 223, Article 111278. https://doi.org/10.1016/j.brainresbull
.2025.111278
Rao, S. M., Leo, G. J., Bernardin, L., & Unverzagt, F. (1991). Cognitive
dysfunction in multiple sclerosis. I. Frequency, patterns, and prediction.
Neurology, 41(5), 685–691. https://doi.org/10.1212/WNL.41.5.685
Revelle, W. (2025). psych: Procedures for psychological, psychometric, and
personality research (R package, Version 2.5.3) [Computer software].
https://CRAN.R-project.org/package=psych
Rinehardt, E., Eichstaedt, K., Schinka, J. A., Loewenstein, D. A., Mattingly,
M., Fils, J., Duara, R., & Schoenberg, M. R. (2014). Verbal fluency
patterns in mild cognitive impairment and Alzheimer’s disease. Dementia
and Geriatric Cognitive Disorders, 38(1–2), 1–9. https://doi.org/10.1159/
000355558
Rossum, G. V., & Drake, F. L. (2009). Python 3 reference manual.
CreateSpace.
Ruff, R. M., Light, R. H., Parker, S. B., & Levin, H. S. (1996). Benton
controlled oral word association test: Reliability and updated norms.
Archives of Clinical Neuropsychology, 11(4), 329–338. https://doi.org/10
.1093/arclin/11.4.329
Schnur, T., Schwartz, M., Brecher, A., & Hodgson, C. (2006). Semantic
interference during blocked-cyclic naming: Evidence from aphasia.
Journal of Memory and Language, 54(2), 199–227. https://doi.org/10
.1016/j.jml.2005.10.002
Sepulcre, J., Peraita, H., Goni, J., Arrondo, G., Martincorena, I., Duque, B.,
Velez de Mendizabal, N., Masdeu, J. C., & Villoslada, P. (2011). Lexical
access changes in patients with multiple sclerosis: A two-year follow-up
study. Journal of Clinical and Experimental Neuropsychology, 33(2),
169–175. https://doi.org/10.1080/13803395.2010.499354
Shao, Z., Janse, E., Visser, K., & Meyer, A. S. (2014). What do verbal
fluency tasks measure? Predictors of verbal fluency performance in older
adults. Frontiers in Psychology, 5, Article 772. https://doi.org/10.3389/
fpsyg.2014.00772
Smith, M. M., & Arnett, P. A. (2007). Dysarthria predicts poorer perfor-
mance on cognitive tasks requiring a speeded oral response in an MS
population. Journal of Clinical and Experimental Neuropsychology,
29(8), 804–812. https://doi.org/10.1080/13803390601064493
Sporns, O. (2011). Networks of the brain. MIT Press.
Steyvers, M., & Tenenbaum, J. B. (2005). The large-scale structure of
semantic networks: Statistical analyses and a model of semantic growth.
Cognitive Science, 29(1), 41–78. https://doi.org/10.1207/s15516709co
g2901_3
Šubert, M., Novotný, M., Tykalová, T., Srpová, B., Friedová, L., Uher, T.,
Horáková, D., & Rusz, J. (2023). Lexical and syntactic deficits analyzed
via automated natural language processing: The new monitoring tool in
multiple sclerosis. Therapeutic Advances in Neurological Disorders, 16,
1–13. https://doi.org/10.1177/17562864231180719
Tiberio, M., Chard, D. T., Altmann, D. R., Davies, G., Griffin, C. M., Rashid,
W., Sastre-Garriga, J., Thompson, A. J., & Miller, D. H. (2005). Gray and
white matter volume changes in early RRMS: A 2-year longitudinal
study. Neurology, 64(6), 1001–1007. https://doi.org/10.1212/01.WNL
.0000154526.22878.30
Tombaugh, T. N., Kozak, J., & Rees, L. (1999). Normative data stratified by
age and education for two measures of verbal fluency: FAS and animal
naming. Archives of Clinical Neuropsychology, 14(2), 167–177. https://
doi.org/10.1093/arclin/14.2.167
Troyer, A. K. (2000). Normative data for clustering and switching on verbal
fluency tasks. Journal of Clinical and Experimental Neuropsychology,
22(3), 370–378. https://doi.org/10.1076/1380-3395(200006)22:3;1-V;FT370
Vaden, K. I., Halpin, H. R., & Hickok, G. S. (2009). Irvine phonotactic
online dictionary (Version 2.0) [Data set]. https://www.iphod.com
Verhaeghen, P. (2003). Aging and vocabulary scores: A meta-analysis.
Psychology and Aging, 18(2), 332–339. https://doi.org/10.1037/0882-
7974.18.2.332
Vitevitch, M. S. (2008). What can graph theory tell us about word learning
and lexical retrieval? Journal of Speech, Language, and Hearing
Research, 51(2), 408–422. https://doi.org/10.1044/1092-4388(2008/030)
Vitevitch, M. S. (2022). What can network science tell us about phonology
and language processing? Topics in Cognitive Science, 14(1), 127–142.
https://doi.org/10.1111/tops.12532
Vitevitch, M. S., Castro, N., Mullin, G. J. D., & Kulphongpatana, Z. (2023).
The resilience of the phonological network may have implications for
developmental and acquired disorders. Brain Sciences, 13(2), Article 188.
https://doi.org/10.3390/brainsci13020188
Wachowius, U., Talley, M., Silver, N., Heinze, H. J., & Sailer, M. (2007).
Cognitive impairment in primary and secondary progressive multiple
sclerosis. Journal of Clinical and Experimental Neuropsychology, 27(1),
65–77. https://doi.org/10.1080/138033990513645
Wulff, D. U., De Deyne, S., Jones, M. N., Mata, R., & the Aging Lexicon
Consortium. (2019). New perspectives on the aging lexicon. Trends in
Cognitive Sciences, 23(8), 686–698. https://doi.org/10.1016/j.tics.2019
.05.003
Wulff, D. U., Hills, T. T., & Mata, R. (2022). Structural differences in the
semantic networks of younger and older adults. Scientific Reports, 12,
Article 21459. https://doi.org/10.1038/s41598-022-11698-4"""


text32 = "Prolonged Grief Disorder (PGD), in recent years codified in ICD-11 and DSM-5-TR (American Psy- chiatric Association, 2022; World Health Organiz- ation., 2018), refers to persistent and impairing grief reactions characterised by intense yearning, disbelief about the death, and functional disruption that extend beyond culturally expected timeframes. Roughly 5– 10 % of bereaved adults develop PGD Lundorff et al. (2017), with elevated rates following unexpected or violent loss (e.g. homicide, accidents) (Djelantik et al., 2020) or the death of a child or partner (Smith & Ehlers, 2020). PGD is highly comorbid with PTSD, depression, and anxiety, and associated with poorer physical health and reduced quality of life (Killikelly et al., 2025). Although grief-focused cognitive – behavioural therapies have demonstrated moderate to large effects on PGD, depression, anxiety, and PTSD symptoms (Komischke-Konnerup et al., 2024), access to specialised treatment remains limited. Within the UK’s National Health Service (NHS), there is currently no routine service offering PGD-specific therapy, and this gap is mirrored internationally, despite consistent recommendations that grief- focused psychotherapy is the first-line intervention (LaPlante et al., 2024). A core feature of cognitive approaches to psycho- logical disorders is their emphasis on identifying and targeting maintaining cognitive and behavioural fac- tors of distress. For example, Ehlers and Clark’s (2000) cognitive model of PTSD proposes that post-trauma negative appraisals and disjointed trauma memories give rise to a sense of internal or external current threat. This threat drives control strategies intended to reduce reexperiencing and emotional distress, but, that in fact, block memory updating and the self-correction of negative apprai- sals. Cognitive therapy for PTSD (Ehlers et al., 2005), which builds on this model, including its internet-delivered version (iCT-PTSD, Ehlers et al., 2023), has shown strong outcomes, with pre- to post-treatment effect sizes around 2.5 and recovery rates between 70 and 77%. Treatment is tailored to the individual case formulation of the patient’s unhelpful appraisals, memory features and control strategies and modifies them with a range of targeted techniques. This includes testing patients’ predic- tions and beliefs in real life situations. Building on these principles, the Oxford Grief Study (Smith 2018) aimed to characterise the cog- nitive mechanisms specifically implicated in PGD. This study identified maladaptive memory charac- teristics, negative appraisals, unhelpful coping strategies, and a sense of social disconnection as predictors and maintaining factors of grief. It also led to the development of four new questionnaires measuring these cognitive concepts, and longitudi- nal studies confirmed their role as key mechanisms in PGD (Smith & Ehlers, 2020; Smith et al., 2022; Smith et al., 2024; Smith et al., 2020). These findings lend strong empirical and theoretical sup- port for applying trauma – inspired cognitive therapy techniques to prolonged grief (Smith & Ehlers, 2023). Several therapist-assisted digital treatments for PGD have shown significant and strong effects in reducing symptoms (Kaiser et al., 2022; Lenferink et al., 2023; Treml et al., 2021). However, recovery is typically only observed by approximately half of treat- ment completers (Kaiser et al., 2022; Kersting et al., 2013; Treml et al., 2021). This is markedly lower than what is observed in digital treatments for PTSD, which have included individuals who have experienced traumatic bereavement (Bisson et al., 2022; Ehlers et al., 2023; Ivarsson et al., 2014; Knae- velsrud & Maercker, 2007; Litz et al., 2007). One reason may be that digital approaches for PGD often rely on manualised protocols delivered uniformly, whereas some programmes developed for PTSD, specifically iCT-PTSD, was designed as a flexible, for- mulation-driven approach. In iCT-PTSD, therapists and patients select from a library of modules that can be tailored to the individual’s presentation, ensur- ing a highly personalised route through treatment. While a core set of modules is recommended for all, the order of delivery and adjunct modules can be adapted to suit each patient’s individual case formu- lation (Wild et al., 2016). Building on these foundations, the current study aimed to develop and provide initial empirical support for internet cognitive therapy for Prolonged Grief (iCT – PG). Adapted from iCT-PTSD (Ehlers et al., 2023; Wild et al., 2016), a digitally-assisted version of cognitive therapy for PTSD (Ehlers et al., 2005), iCT – PG was co-designed with patient and public involvement (PPI) and reviewed by two clinical test cases before proceeding to the current stage of development. The developmental case series represents a key step in the iterative design and refinement of iCT- PG. One aim of this phase was to extend the initial development work by including a broader range of participants (for example, those with differing loss types and circumstances) to ensure that the inter- vention was suitable and comprehensible across diverse bereavement experiences. The programme includes modules addressing the loss memory and memory triggers, negative appraisals, a sense of social disconnection, and unhelpful coping such as avoidance, rumination, proximity seeking, and relapse prevention. This developmental case series (N = 8) explores feasibility, acceptability, clinical outcomes, and changes in proposed mechanisms of treatment efficacy. It also sought feedback from participants and therapists to identify content requiring clarifica- tion, elements in need of further explanation or refinement, and technical aspects that could be improved ahead of a potential randomised con- trolled trial."

test32 = """American Psychiatric Association. (2000). Diagnostic stat-
istical manual of mental disorders (Revised 4th ed. Text
Revision).
American Psychiatric Association. (2022). Diagnostic and
statistical manual of mental disorders (5th ed., text rev.).
https://doi.org/10.1176/appi.books.9780890425787
Bisson, J. I., Ariti, C., Cullen, K., Kitchiner, N., Lewis, C.,
Roberts, N. P., Simon, N., Smallman, K., Addison, K., &
Bell, V. (2022). Guided, internet based, cognitive behav-
ioural therapy for post-traumatic stress disorder:
Pragmatic, multicentre, randomised controlled non-
inferiority trial (RAPID). Bmj, e069405. https://doi.org/
10.1136/bmj-2021-069405
Blevins, C. A., Weathers, F., Davis, M. T., Witte, T. K., &
Domino, J. L. (2015). The Posttraumatic Stress Disorder
Checklist for DSM-5 (PCL-5): Development and initial
psychometric evaluation. Journal of Traumatic Stress,
28(6), 489–498. https://doi.org/10.1002/jts.22059
Boelen, P. A., van den Hout, M. A., & van den Bout, J.
(2006). .A cognitive-behavioral conceptualization of
complicated grief Clinical Psychology: Science and
Practice, 13(2), 109–128. https://doi.org/10.1111/j.1468-
2850.2006.00013.x
Clark, D. M., Wild, J., Warnock-Parkes, E., Stott, R., Grey,
N., Thew, G., & Ehlers, A. (2023). More than doubling
the clinical benefit of each hour of therapist time: A ran-
domised controlled trial of internet cognitive therapy for
social anxiety disorder. Psychological Medicine, 53(11),
5022–5032. https://doi.org/10.1017/S0033291722002008
Cohen, J. (1988). Statistical power analysis for the behavioral
sciences. Routledge.
Djelantik, A. M. J., Smid, G. E., Mroz, A., Kleber, R. J., &
Boelen, P. A. (2020). The prevalence of Prolonged Grief
Disorder in bereaved individuals following unnatural
losses: Systematic review and meta regression analysis.
Journal of Affective Disorders, 265, 146–156. https://doi.
org/10.1016/j.jad.2020.01.034
Duffy, M., & Wild, J. (2023). Living with loss: A cognitive
approach to prolonged grief disorder – incorporating
complicated, enduring and traumatic grief. Behavioural
and Cognitive Psychotherapy, 645–658. https://doi.org/
10.1017/s1352465822000674
Ehlers, A., & Clark, D. M. (2000). A cognitive model of post-
traumatic stress disorder. Behaviour Research and
Therapy, 38(4), 319–345. https://doi.org/10.1016/S0005-
7967(99)00123-0
Ehlers, A., Clark, D. M., Hackmann, A., McManus, F., &
Fennell, M. (2005). Cognitive therapy for post-traumatic
stress disorder: Development and evaluation. Behaviour
Research and Therapy, 43(4), 413–431. https://doi.org/
10.1016/j.brat.2004.03.006
Ehlers, A., Wild, J., Warnock-Parkes, E., Grey, N., Murray,
H., Kerr, A., Rozental, A., Thew, G., Janecka, M., & Beierl, E. T. (2023). Therapist-assisted online psychologi-
cal therapies differing in trauma focus for post-traumatic
stress disorder (STOP-PTSD): A UK-based, single-blind,
randomised controlled trial. The Lancet Psychiatry, 10(8),
608–622. https://doi.org/10.1016/S2215-0366(23)00181-5
First, M. B., Williams, J. B., Benjamin, L. S., & Spitzer, R. L.
(2016). SCID-5-PD: Structured clinical interview for DSM-
5® personality disorders. American Psychiatric
Association Publishing.
First, M. B., Williams, J. B., Karg, R. S., & Spitzer, R. L.
(2016). User’s guide for the SCID-5-CV structured clinical
interview for DSM-5® disorders: Clinical version.
American Psychiatric Publishing, Inc.
Goff, S., Carson, J., Ladwa, A., Colletta, M., Topciu, R.,
Shear, K., & Dunn, B. D. (2025). An evaluation of a
pilot high-intensity treatment pathway for prolonged
grief reactions in a Devon NHS Talking Therapies ser-
vice. The Cognitive Behaviour Therapist, 18, e10. https://
doi.org/10.1017/S1754470X25000030
Hedges, L. V., & Olkin, I. (2014). Statistical methods for
meta-analysis. Academic Press.
Ivarsson, D., Blom, M., Hesser, H., Carlbring, P., Enderby,
P., Nordberg, R., & Andersson, G. (2014). Guided inter-
net-delivered cognitive behavior therapy for post-trau-
matic stress disorder: A randomized controlled trial.
Internet Interventions, 1(1), 33–40. https://doi.org/10.
1016/j.invent.2014.03.002
Jacobson, N. S., & Truax, P. (1992). Clinical significance: A
statistical approach to defining meaningful change in psy-
chotherapy research.
Kaiser, J., Nagl, M., Hoffmann, R., Linde, K., & Kersting, A.
(2022). Therapist-assisted web-based intervention for
prolonged grief disorder after cancer bereavement:
Randomized controlled trial. JMIR Mental Health, 9(2),
e27642. https://doi.org/10.2196/27642
Kersting, A., Dölemeyer, R., Steinig, J., Walter, F., Kroker,
K., Baust, K., & Wagner, B. (2013). Brief Internet-based
intervention reduces posttraumatic stress and prolonged
grief in parents after the loss of a child during pregnancy:
a randomized controlled trial. Psychotherapy and
Psychosomatics, 82(6), 372–381. https://doi.org/10.1159/
000348713
Killikelly, C., Smith, K. V., Zhou, N., Prigerson, H. G.,
O’Connor, M.-F., Kokou-Kpolou, C. K., Boelen, P. A.,
& Maercker, A. (2025). Prolonged grief disorder. The
Lancet, 405 (10489), 1621–1632. https://doi.org/10.1016/
S0140-6736(25)00354-X
Killikelly, C., Zhou, N., Merzhvynska, M., Stelzer, E. M.,
Dotschung, T., Rohner, S., Sun, L. H., & Maercker, A.
(2020). Development of the international prolonged
grief disorder scale for the ICD-11: Measurement of
core symptoms and culture items adapted for Chinese
and German-speaking samples. Journal of Affective
Disorders, 277, 568–576. https://doi.org/10.1016/j.jad.
2020.08.057
Knaevelsrud, C., & Maercker, A. (2007). Internet-based
treatment for PTSD reduces distress and facilitates the
development of a strong therapeutic alliance: A random-
ized controlled clinical trial. BMC Psychiatry, 7(1), 13.
https://doi.org/10.1186/1471-244X-7-13
Komischke-Konnerup, K. B., O’Connor, M., Hoijtink, H., &
Boelen, P. A. (2025). Cognitive-behavioral therapy for
complicated grief reactions: Treatment protocol and pre-
liminary findings from a naturalistic setting. Cognitive
and Behavioral Practice, 32(1), 29–43. https://doi.org/
10.1016/j.cbpra.2023.11.001
Komischke-Konnerup, K. B., Zachariae, R., Boelen, P. A.,
Marello, M. M., & O’Connor, M. (2024). Grief-focused
cognitive behavioral therapies for prolonged grief symp-
toms: A systematic review and meta-analysis. Journal of
Consulting and Clinical Psychology, 92(4), 236–248.
https://doi.org/10.1037/ccp0000884
Kroenke, K., Spitzer, R., & Williams, J. (2001). The PHQ-9:
Validity of a brief depression severity measure. Journal of
General Internal Medicine, 16(9), 606–613. https://doi.
org/10.1046/j.1525-1497.2001.016009606.x
LaPlante, C. D., Hardt, M. M., Maciejewski, P. K., &
Prigerson, H. G. (2024). State of the science:
Psychotherapeutic interventions for prolonged grief dis-
order. Behavior Therapy, 55(6), 1303–1317. https://doi.
org/10.1016/j.beth.2024.07.002
Leigh, E., & Clark, D. M. (2023). Internet-delivered thera-
pist-assisted cognitive therapy for adolescent social
anxiety disorder (OSCA): A randomised controlled trial
addressing preliminary efficacy and mechanisms of
action. Journal of Child Psychology and Psychiatry,
64(1), 145–155. https://doi.org/10.1111/jcpp.13680
Lenferink, L. I. M., Eisma, M. C., Buiter, M. Y., de Keijser, J.,
& Boelen, P. A. (2023). Online cognitive behavioral
therapy for prolonged grief after traumatic loss: A ran-
domized waitlist-controlled trial. Cognitive Behaviour
Therapy, 52(5), 508–522. https://doi.org/10.1080/
16506073.2023.2225744
Litz, B. T., Engel, C. C., Bryant, R. A., & Papa, A. (2007). A
randomized, controlled proof-of-concept trial of an
Internet-based, therapist-assisted self-management treat-
ment for posttraumatic stress disorder. American Journal
of Psychiatry, 164(11), 1676–1684. https://doi.org/10.
1176/appi.ajp.2007.06122057
Litz, B. T., Schorr, Y., Delaney, E., Au, T., Papa, A., Fox, A.
B., Morris, S., Nickerson, A., Block, S. D., & Prigerson, H.
G. (2014). A randomized controlled trial of an internet-
based therapist-assisted indicated preventive intervention
for prolonged grief disorder. Behaviour Research and
Therapy, 61, 23–34. https://doi.org/10.1016/j.brat.2014.
07.005
Lundorff, M., Holmgren, H., Zachariae, R., Farver-
Vestergaard, I., & O’Connor, M. (2017). Prevalence of
prolonged grief disorder in adult bereavement: A sys-
tematic review and meta-analysis. Journal of Affective
Disorders, 212, 138–149. https://doi.org/10.1016/j.jad.
2017.01.030
Maccallum, F., & Bryant, R. A. (2013). A cognitive attach-
ment model of prolonged grief: Integrating attachments,
memory, and identity [Research Support, Non-U.S.
Clinical Psychology Review, 33(6), 713–727. https://doi.
org/10.1016/j.cpr.2013.05.001
Mundt, J. C., Marks, I. M., Shear, M. K., & Greist, J. M.
(2002). The Work and Social Adjustment Scale: A simple
measure of impairment in functioning. British Journal of
Psychiatry, 180(5), 461–464. https://doi.org/10.1192/bjp.
180.5.461
Murray, H., Kerr, A., Warnock-Parkes, E., Wild, J., Grey, N.,
Clark, D. M., & Ehlers, A. (2022). What do others think?
The why, when and how of using surveys in CBT. The
Cognitive Behaviour Therapist, 15, e42. https://doi.org/
10.1017/s1754470 ( 22000393
NHS England. (2024). NHS talking therapies for anxiety and
depression manual. The National Collaborating Centre
for Mental Health. https://www.england.nhs.uk/
publication/the-improving-access-to-psychological-
therapies-manual/.
Prigerson, H. G., Boelen, P. A., Xu, J., Smith, K. V., &
Maciejewski, P. K. (2021). Validation of the new DSM-
5-TR criteria for prolonged grief disorder and the PG-
13-Revised (PG-13-R) scale. World Psychiatry, 20(1),
96–106. https://doi.org/10.1002/wps.20823
Prigerson, H. G., Viola, M., Lichtenthal, W., Rogers, M.,
Derry, H. M., Jou She, W., Gordon-Elliott, J., &
Maciejewski, P. K. (2022). STRUCTURED CLINICAL
INTERVIEW FOR PROLONGED GRIEF DISORDER
(SCIP). https://endoflife.weill.cornell.edu/sites/default/
files/file_uploads/structured_clinical_interview_for.pdf.
Reitsma, L., Boelen, P. A., de Keijser, J., & Lenferink, L. I. M.
(2023). Self-guided online treatment of disturbed grief,
posttraumatic stress, and depression in adults bereaved
during the COVID-19 pandemic: A randomized con-
trolled trial. Behaviour Research and Therapy, 163,
104286. https://doi.org/10.1016/j.brat.2023.104286
Reitsma, L., Boelen, P. A., Van Ee, E., de Keijser, J., &
Lenferink, L. (2024). Therapist-guided versus self-guided
online cognitive behavioral therapy for prolonged grief
after losses during the COVID-19 Pandemic: A con-
trolled trial [preprint]. https://doi.org/10.13140/RG.2.2.
23768.71688
Shear, M. K., Monk, T., Houck, P., Melhem, N., Frank, E.,
Reynolds, C., & Sillowash, R. (2007). An attachment-based
model of complicated grief including the role of avoidance.
European Archives of Psychiatry and Clinical Neuroscience,
257(8), 453–461. https://doi.org/10.1007/s00406-007-0745-z
Smith, K. V. (2018). Memories, appraisals, and coping strat-
egies in prolonged grief disorder. University of Oxford].
Smith, K. V., & Ehlers, A. (2020). Cognitive predictors of
grief trajectories in the first months of loss: A latent
growth mixture model. Journal of Consulting and
Clinical Psychology, 88(2), 93–105. https://doi.org/10.
1037/ccp0000438
Smith, K. V., & Ehlers, A. (2023). Coping strategies as a causal
mediator of the effect of loss-related memory characteristics
and negative loss-related appraisals on symptoms of PGD,
PTSD and depression. Psychological Medicine, 53(4),
1542–1551. https://doi.org/10.1017/S0033291721003123
Smith, K. V., Wild, J., & Ehlers, A. (2020). The masking of
mourning: Social disconnection and its relationship to
psychological distress after loss. Clinical Psychological
Science., 8(3), 464–476. https://doi.org/10.1177/
2167702620902748
Smith, K. V., Wild, J., & Ehlers, A. (2022). Psychometric
characteristics of the oxford grief memory characteristics
scale and its relationship with symptoms of ICD-11 and
DSM-5-TR Prolonged Grief Disorder [Original
Research]. Frontiers in Psychiatry, 13, 814171. https://
doi.org/10.3389/fpsyt.2022.814171
Smith, K. V., Wild, J., & Ehlers, A. (2024). From loss to dis-
order: The influence of maladaptive coping on prolonged
grief. Psychiatry Research, 339, 116060. https://doi.org/10.
1016/j.psychres.2024.116060
Spitzer, R. L., Kroenke, K., Williams, J. B. W., & Löwe, B.
(2006). A brief measure for assessing generalized anxiety
disorder: The GAD-7. Archives of Internal Medicine,
166(10), 1092–1097. https://doi.org/10.1001/archinte.
166.10.1092
Treml, J., Nagl, M., Linde, K., Kündiger, C., Peterhänsel, C.,
& Kersting, A. (2021). Efficacy of an Internet-based cog-
nitive-behavioural grief therapy for people bereaved by
suicide: a randomized controlled trial. European Journal
of Psychotraumatology, 12(1), 1926650. https://doi.org/
10.1080/20008198.2021.1926650
Weathers, F., Litz, B. T., Keane, T. M., Palmieri, P. A., Marx,
B. P., & Schnurr, P. P. (2013). The PTSD Checklist for
DSM-5 (PCL-5). http://www.ptsd.va.gov.
Wild, J., Duffy, M., & Ehlers, A. (2023). Moving forward
with the loss of a loved one: Treating PTSD following
traumatic bereavement with cognitive therapy. The
Cognitive Behaviour Therapist, 16, e12. https://doi.org/
10.1017/S1754470X23000041
Wild, J., Warnock-Parkes, E., Grey, N., Stott, R.,
Wiedemann, M., Canvin, L., Rankin, H., Shepherd, E.,
Forkert, A., Clark, D. M., & Ehlers, A. (2016). Internet-
delivered cognitive therapy for PTSD: A development
pilot series. European Journal of Psychotraumatology, 7(1),
31019. https://doi.org/10.3402/ejpt.v7.31019
World Health Organization. (2018). International
Classification of Diseases 11th Revision (ICD-11) –
Mental, behavioural or neurodevelopmental disorders.
Retrieved Retrieved May 18, 2018 from http://www.
who.int/classifications/icd/revision/en/, from.
Yao, D., Qian, F., Tung, T.-H., Shi, H., & Bi, D. (2025). The
effectiveness of web-based grief intervention for adults
who lost a loved one: A systematic review and meta-
analysis. Bmc Palliative Care, 24(1), 61. https://doi.org/
10.1186/s12904-025-01679-5"""


text33 = "Human cooperation rests on a rich set of social-cognitive capacities that emerge early and are shaped through experience. A key mech- anism enabling such cooperation is reciprocity, that is, the tendency to respond to others in kind, which underlies fairness, obligation, and trust (Bowles & Gintis, 2011; Trivers, 1971; Warneken, 2018). Yet, reciprocity does not operate in a social vacuum. From a young age, children attend to group boundaries and use them to guide decisions about whom to help, trust, or exclude (Rhodes & Mandalaywala, 2017). Some group-based boundaries, such as gender or ethnicity, are shaped by intuitive beliefs that these categories reflect stable and natural differences (Gelman, 2003). For others, such as language or socioeconomic status (SES), expectations are more strongly influenced by culturally transmitted norms (Bigler & Liben, 2007; Kinzler & Dautel, 2012). Here, we examine how children’s reciprocal behavior is shaped by both group membership and inter- group contact, focusing on Arab and Jewish children in Jerusalem— two groups growing up in culturally distinct yet socially overlapping contexts. By around 5 years of age, children begin to engage in contingent reciprocity and respond to others’ actions based on whether they have been kind or unkind, examined in both repeated and one-shot inter- actions, in contexts with or without personal cost. At this developmental stage, they increasingly expect benefits to be returned and recognize fairness and obligation as guiding principles in social exchange (Blake et al., 2015; Chernyak et al., 2019; House et al., 2019, 2020; Paulus, 2016). (House et al., 2019, 2020). However, studies diverge on when and how these reciprocal tendencies emerge. Computerized paradigms with American children suggest that negative reciprocity (“unkindness for unkindness”) emerges earlier than positive reciprocity (“kindness for kindness”; Chernyak et al., 2019). In a different context, naturalistic studies among familiar peers show a more balanced pattern, with children reciprocating both prosocial and antisocial behaviors in kind (House et al., 2013). When the same method was used in Fiji, another pattern emerged, underscoring the influence of cultural norms and local social ecologies (House, 2017). More recent studies using a semicontrolled paradigm with unfamiliar peers (e.g., video-based presentations) offer also a hybrid perspective. For instance, 5-year-old children in Germany show both positive and negative reciprocity when there is no personal cost. Yet, when reciprocity becomes costly, gender differences emerge, showing that girls, not boys, reciprocate fairness at high rates (Benozio et al., 2023, 2024). These findings highlight that children’s reciprocity is context- sensitive, shaped by methodological features, partner familiarity, and cultural setting. Extending this work, the present studies examine whether an additional factor, namely, group membership, influences children’s willingness to reciprocate fairness. Social group cues, such as ethnicity or language, guide children’s information seeking and behavior (Diesendruck & Menahem, 2015; Nasie et al., 2022). Indeed, children’s moral and prosocial behavior is often structured by group boundaries. For example, preschoolers favor in-group members in sharing, hold them to higher standards of fairness, and judge out- group norm violators more harshly (Dunham et al., 2011; Jordan et al., 2014; Rutland & Killen, 2017). Thus, understanding how children integrate such cues with a partner’s prior behavior may illuminate the early developmental mechanisms supporting reciprocity in intergroup contexts. The emergence of such group-based behaviors has been linked to children’s developing essentialist beliefs about social categories. Around the same developmental window, children begin to exhibit heightened intergroup bias, often adopting essentialist beliefs about social categories such as ethnicity, gender, or nationality (Chalik et al., 2017; Gelman, 2003; Raabe & Beelmann, 2011). These beliefs portray such categories as natural, stable, and predictive of behavior, fueling early in-group favoritism even without explicit out-group hostility (Bigler & Liben, 2006; Brewer, 1999; Diesendruck & Menahem, 2015; Misch et al., 2022). Such cognitive commitments may also explain why children preferentially direct prosocial behavior toward in-group members and feel responsible for their group’s negative actions (Over, 2018; Over et al., 2016). Several theoretical frameworks offer complementary perspectives on the origins of these biases. According to social identity theory (SIT; Tajfel & Turner, 1986), cognitive categorization underlies group bias, which, coupled with a motivation to maintain positive self-esteem and group distinctiveness, fosters both in-group favor- itism and out-group bias. In contrast, other scholars reverse the causal direction, suggesting that children may favor in-groups because they already hold a positive self-concept and project it onto their group (Dunham, 2013; Otten, 2003). Developmental intergroup theory (Bigler & Liben, 2007), unlike SIT, emphasizes children’s tendency to categorize based on salient features (e.g., race, gender) and how environmental reinforcement of these categories shapes the devel- opment of bias (Segall et al., 2015). Unlike these cognitively driven accounts, evolutionary perspectives such as bounded generalized reciprocity (BGR; Yamagishi & Kiyonari, 2000; Yamagishi & Mifune, 2008) offer a functional explanation for group-based cooperation. From this perspective, humans attend to group cues (e.g., language, group symbols) as heuristics for identifying trustworthy partners and avoiding exploitation. Similar to SIT and developmental intergroup theory, BGR therefore predicts a default tendency toward in-group favoritism in novel interactions. However, BGR also specifies conditions under which this bias can be weakened, specifically when individuals have repeated opportunities for cooperative contact across group lines. While these frameworks are introduced here for conceptual framing rather than direct testing, they could yield different emphases in the context of a one-shot interaction: SIT and developmental intergroup theory highlight the strength and persistence of identity-driven biases, whereas BGR highlights conditions under which biases may be attenuated, namely, when future interaction is anticipated. Intergroup bias can be reduced when group members interact under optimal conditions: equal status, cooperative interactions, shared goals, and institutional support—principles outlined in Allport’s (1954) “Contact Hypothesis” and further elaborated in subsequent research with adults, youth, and young children (see Dovidio et al., 2017; Rutland & Killen, 2015; Tropp et al., 2022, for in-depth re- views). Empirical studies have also supported the effectiveness of these conditions in school-based settings. First, perceptions of equal status can be shaped by classroom composition and language practices. For instance, White children in bilingual, ethnically mixed classrooms, where both English and Spanish were spoken, showed no ethnic bias compared to peers in monolingual, majority-dominant settings (Wright & Tropp, 2005). Second, cooperative structures that emphasize shared goals, such as the jigsaw classroom (Aronson, 2002) and peer-based learning (White et al., 2014), have been shown to promote interdependence and improve intergroup attitudes across diverse cultural contexts (Berger et al., 2015; Walker & Crogan, 1998). Third, institutional support is also critical, as children are more likely to pursue cross-group friendships when they perceive support from teachers and school leadership (Jugert et al., 2011; Tropp et al., 2016), particularly in classrooms that engage openly with issues of fairness, race, and diversity (Aboud & Fenwick, 1999). Despite this strong evidence, optimal “contact” conditions are rarely fully met in real-world settings. Everyday intergroup encounters often occur under unequal status, ambiguous social norms, or lack of institutional support, all of which can blunt the positive effects of contact (Guffler & Wagner, 2017; Schäfer et al., 2021). Children from minority and majority groups may also differ in how they express their intergroup bias (Dunham et al., 2007; Newheiser & Olson, 2012), and children in integrated versus homogeneous educational environments show different levels of in-group preference (Rutland et al., 2005). Notably, children living in historically homogenous adjacent neigh- borhoods sometimes show stronger in-group preferences, suggesting that proximity alone does not guarantee positive contact (O’Driscoll et al., 2018). In light of these findings, the present studies examine Arab and Jewish children living in Jerusalem, a city where several distinct ethnic groups share a single urban environment. While economic- social daily contact is present, structured integration varies wildly. This setting offers a natural test case for exploring the relationship between degrees of intergroup contact and reciprocal behavior in early childhood. Although Arab and Jewish children in Jerusalem share a common urban space, their daily experiences are often shaped by cultural separation as they attend different schools, speak different languages, and grow up in largely homogeneous neighborhoods. More than 70% of children in the city are enrolled in ethnically homogeneous edu- cational settings (Khamaisi et al., 2009; Shwed et al., 2014). Group membership is deeply intertwined with broader, debatable social and political narratives. In this context, Jewish–Arab divisions become culturally salient early in childhood and are reinforced through family discourse, educational content, and broader public life (Bar-Tal & Teichman, 2005; Segall et al., 2015). These influences contribute to children’s early intuitive thinking about ethnic categories and heighten their awareness of group boundaries. By preschool age, many children distinguish between Jews and Arabs, associate these labels with conflict, and exhibit emotional responses such as fear, threat, or distrust (Bar-Tal & Teichman, 2005; Connolly & Zeelenberg, 2002; Diesendruck & Menahem, 2015). These early representations are shaped not only by cultural narratives but also by asymmetrical power relations. For example, Arab children, who often grow up as a minority within a majority-Jewish state, tend to show greater out-group negativity than their Jewish peers, particularly when group identity is salient (Nassir & Diesendruck, 2024). Consequently, biases between real groups tend to be stronger than those toward arbitrary groups, as they reflect not only mere membership but also accumulated knowledge, stereotypes, and status differences (Dunham, 2018). Yet even within this divided context, positive intergroup change in attitudes and behaviors remains within reach. Prior work suggests that when Arab and Jewish children engage in meaningful, inclusive interactions—especially in integrated educational settings—they may begin to view group boundaries as more flexible and develop more positive attitudes toward out-group peers (Deeb et al., 2011). The present research examines how children’s reciprocal behavior is shaped not only by group membership but also by the degree of intergroup contact they experience within the ethnically segregated yet geographically shared environment of Jerusalem. Here, we examined how children’s reciprocal behavior toward in- group versus out-group peers varied depending on their everyday exposure to intergroup interaction. We focused on three socio- geographic contexts, each characterized by a different level of routine contact between Arab and Jewish children. For clarity, we refer to these as a low-contact setting (distant, ethnically homogeneous neighborhoods), a medium-contact setting (adjacent, ethnically homogeneous neighborhoods), and a high-contact setting (a bilingual, integrated school where daily interaction is the norm; Figure 1). These contexts approximate varying degrees of alignment with Allport’s contact hypothesis: The low-contact setting lacks the optimal con- ditions theorized to reduce bias, whereas the high-contact setting comes closest to fulfilling them. Across all three contexts, we assessed children’s willingness to reciprocate fairness in a one-shot, costly interaction toward an unfamiliar in- or out-group peer. To ensure a consistent yet socially engaging stimulus, peer interactions were presented via prerecorded videos, allowing us to standardize stimuli while preserving key social cues. In summary, our two main hypotheses regarding reciprocity, group bias, and social context would be that (1) if reciprocal behavior is largely independent of social context, then the degree of intergroup bias (whether low or high) should remain consistent across low-, medium-, and high-contact settings. (2) Conversely, if contact plays a formative role, we expect that the strongest intergroup bias in re- ciprocity will occur in the low-contact setting and the weakest bias in the high-contact, integrated environments. While our primary focus is on the relationship between inter- group bias, contact, and reciprocal behavior, our design and sample also permit exploration of two secondary questions raised by prior research. First, intergroup contact may not affect all children equally: Studies suggest that majority-group children often derive greater benefit from contact than their minority-group peers (e.g., Feddes et al., 2009). Second, gender differences in reciprocity have been reported in similar paradigms, with girls tending to reciprocate more than boys (e.g., Benozio et al., 2024). We therefore examined whether (a) intergroup contact influences reciprocity differently for majority- and minority-group children and (b) the observed gender differences persist when reciprocity involves an out-group partner under varying contact conditions."

test33 = """Aboud, F. E., & Fenwick, V. (1999). Exploring and evaluating school-based\ninterventions to reduce prejudice. Journal of Social Issues, 55(4), 767–\n785. https://doi.org/10.1111/0022-4537.00146\nAllport, G. W. (1954). The nature of prejudice. Addison-Wesley. https://facu\nlty.washington.edu/caporaso/courses/203/readings/allport_Nature_of_pre\njudice.pdf\nAronson, E. (2002). Building empathy, compassion, and achievement in the\njigsaw classroom. In J. Aronson (Ed.), Improving academic achievement (pp.\n209–225). Elsevier. https://doi.org/10.1016/B978-012064455-1/50013-0\nBar-Tal, D., & Teichman, Y. (2005). Stereotypes and prejudice in conflict:\nRepresentations of Arabs in Israeli Jewish society. Cambridge University\nPress. https://doi.org/10.1017/CBO9780511499814.002\nBenozio, A., House, B. R., & Tomasello, M. (2023). Apes reciprocate food\npositively and negatively. Proceedings of the Royal Society B: Biological\nSciences, 290(1998). https://doi.org/10.1098/rspb.2022.2541\nBenozio, A., House, B. R., & Tomasello, M. (2024). Gender and cultural\ndifferences in the development of reciprocity in young children. Deve-\nlopmental Psychology, 60(6), 1082–1096. https://doi.org/10.1037/de\nv0001734\nBerger, R., Abu-Raiya, H., & Gelkopf, M. (2015). The art of living together:\nReducing stereotyping and prejudicial attitudes through the Arab-Jewish\nClass Exchange Program (CEP). Journal of Educational Psychology,\n107(3), 678–688. https://doi.org/10.1037/edu0000015\nBigler, R. S., & Liben, L. S. (2006). A developmental intergroup theory of\nsocial stereotypes and prejudice. Advances in Child Development and\nBehavior, 34, 39–89. https://doi.org/10.1016/S0065-2407(06)80004-2\nBigler, R. S., & Liben, L. S. (2007). Developmental intergroup theory.\nCurrent Directions in Psychological Science, 16(3), 162–166. https://\ndoi.org/10.1111/j.1467-8721.2007.00496.x\nBlake, P. R., McAuliffe, K., Corbit, J., Callaghan, T. C., Barry, O., Bowie,\nA., Kleutsch, L., Kramer, K. L., Ross, E., Vongsachang, H., Wrangham,\nR., & Warneken, F. (2015). The ontogeny of fairness in seven societies.\nNature, 528(7581), 258–261. https://doi.org/10.1038/nature15703\nBowles, S., & Gintis, H. (2011). A cooperative species. Princeton University\nPress. https://doi.org/10.23943/princeton/9780691151250.003.0001\nBrewer, M. B. (1999). The psychology of prejudice: Ingroup love and\noutgroup hate? Journal of Social Issues, 55(3), 429–444. https://doi.org/10\n.1111/0022-4537.00126\nChalik, L., Leslie, S.-J., & Rhodes, M. (2017). Cultural context shapes\nessentialist beliefs about religion. Developmental Psychology, 53(6), 1178–\n1187. https://doi.org/10.1037/dev0000301\nChernyak, N., Leimgruber, K. L., Dunham, Y. C., Hu, J., & Blake, P. R.\n(2019). Paying back people who harmed us but not people who helped us:\nDirect negative reciprocity precedes direct positive reciprocity in early\ndevelopment. Psychological Science, 30(9), 1273–1286. https://doi.org/\n10.1177/0956797619854975\nConnolly, T., & Zeelenberg, M. (2002). Regret in decision making. Current\nDirections in Psychological Science, 11(6), 212–216. https://doi.org/10\n.1111/1467-8721.00203\nDeeb, I., Segall, G., Birnbaum, D., Ben-Eliyahu, A., & Diesendruck, G.\n(2011). Seeing isn’t believing: The effect of intergroup exposure on chil-\ndren’s essentialist beliefs about ethnic categories. Journal of Personality\nand Social Psychology, 101(6), 1139–1156. https://doi.org/10.1037/\na0026107\nDiesendruck, G., & Menahem, R. (2015). Essentialism promotes children’s\ninter-ethnic bias. Frontiers in Psychology, 6, Article 1180. https://doi.org/\n10.3389/fpsyg.2015.01180\nDovidio, J. F., Love, A., Schellhaas, F. M. H., & Hewstone, M. (2017).\nReducing intergroup bias through intergroup contact: Twenty years of\nprogress and future directions. Group Processes & Intergroup Relations,\n20(5), 606–620. https://doi.org/10.1177/1368430217712052\nDunham, Y. (2013). Balanced identity in the minimal groups paradigm.\nPLOS ONE, 8(12), Article e84205. https://doi.org/10.1371/journal.pone\n.0084205\nDunham, Y. (2018). Mere membership. Trends in Cognitive Sciences, 22(9),\n780–793. https://doi.org/10.1016/j.tics.2018.06.004\nDunham, Y., Baron, A. S., & Banaji, M. R. (2007). Children and social\ngroups: A developmental analysis of implicit consistency in hispanic\nAmericans. Self and Identity, 6(2–3), 238–255. https://doi.org/10.1080/\n15298860601115344\nDunham, Y., Baron, A. S., & Carey, S. (2011). Consequences of “minimal”\ngroup affiliations in children. Child Development, 82(3), 793–811. https://\ndoi.org/10.1111/j.1467-8624.2011.01577.x\nFeddes, A. R., Noack, P., & Rutland, A. (2009). Direct and extended\nfriendship effects on minority and majority children’s interethnic attitudes: A longitudinal study. Child Development, 80(2), 377–390. https://doi.org/\n10.1111/j.1467-8624.2009.01266.x\nGelman, S. A. (2003). The essential child: Origins of essentialism in\neveryday thought. Oxford University Press. https://doi.org/10.1093/acpro\nf:oso/9780195154061.001.0001\nGuffler, K., & Wagner, U. (2017). Backfire of good intentions: Unexpected\nlong-term contact intervention effects in an intractable conflict area. Peace\nand Conflict: Journal of Peace Psychology, 23(4), 383–391. https://\ndoi.org/10.1037/pac0000264\nHamed, C. (2023). Exploring Palestinian culture and its educational practices\nthrough Hofstede’s lens. International Journal of Humanities and Social\nScience Invention, 12(10), 49–53. https://www.ijhssi.org/papers/vo\nl12(10)/12104954.pdf\nHofstede, G., Hofstede, G. J., & Minkov, M. (2010). Cultures and orga-\nnizations: Software of the mind (3rd ed.). McGraw-Hill.\nHouse, B. R. (2017). Diverse ontogenies of reciprocal and prosocial behavior:\nCooperative development in Fiji and the United States. Developmental\nScience, 20(6), Article e12466. https://doi.org/10.1111/desc.12466\nHouse, B. R., Henrich, J., Sarnecka, B., & Silk, J. B. (2013). The development\nof contingent reciprocity in children. Evolution and Human Behavior, 34(2),\n86–93. https://doi.org/10.1016/j.evolhumbehav.2012.10.001\nHouse, B. R., Kanngiesser, P., Barrett, H. C., Broesch, T., Cebioglu, S.,\nCrittenden, A. N., Erut, A., Lew-Levy, S., Sebastian-Enesco, C., Smith,\nA. M., Yilmaz, S., & Silk, J. B. (2019). Universal norm psychology leads to\nsocietal diversity in prosocial behaviour and development. Nature Human\nBehaviour, 4(1), 36–44. https://doi.org/10.1038/s41562-019-0734-z\nHouse, B. R., Kanngiesser, P., Barrett, H. C., Yilmaz, S., Smith, A. M.,\nSebastian-Enesco, C., Erut, A., & Silk, J. B. (2020). Social norms and cultural\ndiversity in the development of third-party punishment. Proceedings of the\nRoyal Society B: Biological Sciences, 287(1925), Article 20192794. https://\ndoi.org/10.1098/rspb.2019.2794\nJordan, J. J., McAuliffe, K., & Warneken, F. (2014). Development of in-group\nfavoritism in children’s third-party punishment of selfishness. Proceedings\nof the National Academy of Sciences of the United States of America,\n111(35), 12710–12715. https://doi.org/10.1073/pnas.1402280111\nJugert, P., Noack, P., & Rutland, A. (2011). Friendship preferences among\nGerman and Turkish preadolescents. Child Development, 82(3), 812–829.\nhttps://doi.org/10.1111/j.1467-8624.2010.01528.x\nKhamaisi, R., Brooks, R., Margalit, M., Nasrallah, R., Yunan, M., & Owais,\nA. (2009). Jerusalem. The old city. The urban fabric and geopolitical\nimplications. https://www.ipcc-jerusalem.org/attachment/15/IPCC_Jeru\nsalem_the_Old_City_Urban_Fabric_and_Geopolitical_Implications.pdf\nKinzler, K. D., & Dautel, J. B. (2012). Children’s essentialist reasoning about\nlanguage and race. Developmental Science, 15(1), 131–138. https://\ndoi.org/10.1111/j.1467-7687.2011.01101.x\nLi, J., & Tomasello, M. (2018). The development of intention-based so-\nciomoral judgment and distribution behavior from a third-party stance.\nJournal of Experimental Child Psychology, 167, 78–92. https://doi.org/10\n.1016/j.jecp.2017.09.021\nMajolo, B., & Maréchal, L. (2017). Between-group competition elicits\nwithin-group cooperation in children. Scientific Reports, 7(1), Article\n43277. https://doi.org/10.1038/srep43277\nMartin, A. E., & Slepian, M. L. (2021). The primacy of gender: Gendered\ncognition underlies the big two dimensions of social cognition. Perspectives\non Psychological Science, 16(6), 1143–1158. https://doi.org/10.1177/\n1745691620904961\nMisch, A., Dunham, Y., & Paulus, M. (2022). The developmental trajectories\nof racial and gender intergroup bias in 5- to 10-year-old children: The\nimpact of general psychological tendencies, contextual factors, and\nindividual propensities. Acta Psychologica, 229, Article 103709. https://\ndoi.org/10.1016/j.actpsy.2022.103709\nNasie, M., Ben Yaakov, O., Nassir, Y., & Diesendruck, G. (2022). Children’s\nbiased preference for information about in- and out-groups. Developmental\nPsychology, 58(3), 493–509. https://doi.org/10.1037/dev0001304\nNassir, Y., & Diesendruck, G. (2024). Priming group identities affects\nchildren’s resource distribution among groups. Child Development, 95(2),\n409–427. https://doi.org/10.1111/cdev.13995\nNewheiser, A.-K., & Olson, K. R. (2012). White and Black American chil-\ndren’s implicit intergroup bias. Journal of Experimental Social Psychology,\n48(1), 264–270. https://doi.org/10.1016/j.jesp.2011.08.011\nO’Driscoll, D., Taylor, L. K., & Dautel, J. B. (2018). Intergroup resource\ndistribution among children living in segregated neighborhoods amid\nprotracted conflict. Peace and Conflict: Journal of Peace Psychology,\n24(4), 464–474. https://doi.org/10.1037/pac0000348\nOtten, S. (2003). “Me and us” or “us and them”? The self as a heuristic for\ndefining minimal ingroups. European Review of Social Psychology, 13(1),\n1–33. https://doi.org/10.1080/10463280240000028\nOver, H. (2018). The influence of group membership on young children’s\nprosocial behaviour. Current Opinion in Psychology, 20, 17–20. https://\ndoi.org/10.1016/j.copsyc.2017.08.005\nOver, H., Vaish, A., & Tomasello, M. (2016). Do young children accept\nresponsibility for the negative actions of ingroup members? Cognitive\nDevelopment, 40, 24–32. https://doi.org/10.1016/j.cogdev.2016.08.004\nPaulus, M. (2016). It’s payback time: Preschoolers selectively request re-\nsources from someone they had benefitted. Developmental Psychology,\n52(8), 1299–1306. https://doi.org/10.1037/dev0000150\nPettigrew, T. F., & Tropp, L. R. (2008). How does intergroup contact reduce\nprejudice? Meta-analytic tests of three mediators. European Journal of\nSocial Psychology, 38(6), 922–934. https://doi.org/10.1002/ejsp.504\nRaabe, T., & Beelmann, A. (2011). Development of ethnic, racial, and\nnational prejudice in childhood and adolescence: A multinational meta-\nanalysis of age differences. Child Development, 82(6), 1715–1737. https://\ndoi.org/10.1111/j.1467-8624.2011.01668.x\nRhodes, M., & Mandalaywala, T. M. (2017). The development and\ndevelopmental consequences of social essentialism. WIREs Cognitive\nScience, 8(4), Article e1437. https://doi.org/10.1002/wcs.1437\nRutland, A., Cameron, L., Bennett, L., & Ferrell, J. (2005). Interracial\ncontact and racial constancy: A multi-site study of racial intergroup\nbias in 3–5 year old Anglo-British children. Journal of Applied\nDevelopmental Psychology, 26(6), 699–713. https://doi.org/10.1016/j\n.appdev.2005.08.005\nRutland, A., & Killen, M. (2015). A developmental science approach to\nreducing prejudice and social exclusion: Intergroup processes, social-\ncognitive development, and moral reasoning. Social Issues and Policy\nReview, 9(1), 121–154. https://doi.org/10.1111/sipr.12012\nRutland, A., & Killen, M. (2017). Fair resource allocation among children\nand adolescents: The role of group and developmental processes. Child\nDevelopment Perspectives, 11(1), 56–62. https://doi.org/10.1111/cde\np.12211\nSchäfer, S. J., Kauff, M., Prati, F., Kros, M., Lang, T., & Christ, O. (2021).\nDoes negative contact undermine attempts to improve intergroup rela-\ntions? Deepening the understanding of negative contact and its con-\nsequences for intergroup contact research and interventions. Journal of\nSocial Issues, 77(1), 197–216. https://doi.org/10.1111/josi.12422\nSegall, G., Birnbaum, D., Deeb, I., & Diesendruck, G. (2015). The inter-\ngenerational transmission of ethnic essentialism: How parents talk counts\nthe most. Developmental Science, 18(4), 543–555. https://doi.org/10.1111/\ndesc.12235\nShutts, K., Kinzler, K. D., Katz, R. C., Tredoux, C., & Spelke, E. S. (2011). Race\npreferences in children: Insights from South Africa. Developmental Science,\n14(6), 1283–1291. https://doi.org/10.1111/j.1467-7687.2011.01072.x\nShwed, U., Shavit, Y., Dallashi, M., & Ofek, M. (2014). Integration of Arab\nIsraelis and Jews in schools in Israel. Taub Center for Social Policy\nStudies in Israel. https://taubcenter.org.il/integration-of-arab-israelis-and-\njews-in-schools-in-israel/\nTajfel, H., & Turner, J. C. (1986). The social identity theory of intergroup\nbehavior. In S. Worchel & W. G. Austin (Eds.), Psychology of intergroup\nrelations (pp. 7–24). Nelson-Hall.\nTrivers, R. L. (1971). The evolution of reciprocal altruism. The Quarterly\nReview of Biology, 46(1), 35–57. https://doi.org/10.1086/406755\nTropp, L. R., O’Brien, T. C., González Gutierrez, R., Valdenegro, D.,\nMigacheva, K., de Tezanos-Pinto, P., Berger, C., & Cayul, O. (2016). How\nschool norms, peer norms, and discrimination predict interethnic ex-\nperiences among ethnic minority and majority youth. Child Development,\n87(5), 1436–1451. https://doi.org/10.1111/cdev.12608\nTropp, L. R., White, F., Rucinski, C. L., & Tredoux, C. (2022). Intergroup\ncontact and prejudice reduction: Prospects and challenges in changing\nyouth attitudes. Review of General Psychology, 26(3), 342–360. https://\ndoi.org/10.1177/10892680211046517\nVaish, A., & Oostenbroek, J. (2022). Preferential forgiveness: The impact of\ngroup membership and remorse on preschoolers’ forgiveness. Journal of\nExperimental Psychology: General, 151(5), 1132–1140. https://doi.org/10\n.1037/xge0001114\nVezzali, L., Stathi, S., Crisp, R. J., & Capozza, D. (2015). Comparing direct\nand imagined intergroup contact among children: Effects on outgroup\nstereotypes and helping intentions. International Journal of Intercultural\nRelations, 49, 46–53. https://doi.org/10.1016/j.ijintrel.2015.06.009\nWalker, I., & Crogan, M. (1998). Academic performance, prejudice, and the\njigsaw classroom: New pieces to the puzzle. Journal of Community &\nApplied Social Psychology, 8(6), 381–393. https://doi.org/10.1002/(SICI)\n1099-1298(199811/12)8:6<381::AID-CASP457>3.0.CO;2-6\nWarneken, F. (2018). How children solve the two challenges of cooperation.\nAnnual Review of Psychology, 69(1), 205–229. https://doi.org/10.1146/\nannurev-psych-122216-011813\nWhite, F. A., Abu-Rayya, H. M., & Weitzel, C. (2014). Achieving twelve-\nmonths of intergroup bias reduction: The dual identity-electronic contact\n(DIEC) experiment. International Journal of Intercultural Relations, 38,\n158–163. https://doi.org/10.1016/j.ijintrel.2013.08.002\nWright, S. C., & Tropp, L. R. (2005). Language and intergroup contact:\nInvestigating the impact of bilingual instruction on children’s intergroup\nattitudes. Group Processes & Intergroup Relations, 8(3), 309–328. https://\ndoi.org/10.1177/1368430205053945\nYamagishi, T., & Kiyonari, T. (2000). The group as the container of\ngeneralized reciprocity. Social Psychology Quarterly, 63(2), Article 116.\nhttps://doi.org/10.2307/2695887\nYamagishi, T., & Mifune, N. (2008). Does shared group membership promote\naltruism?: Fear, greed, and reputation. Rationality and Society, 20(1), 5–30.\nhttps://doi.org/10.1177/1043463107085442"""

text34 = "By age 18, 7% of all children in the Global North have lost a parent or sibling (Burns et al., 2020). One in ten bereaved children is at risk of Prolonged Grief Dis- order (PGD) (Melhem et al., 2011). Similar rates have been found in bereaved adults (Lundorff et al., 2017). Unlike typical bereavement responses, which are characterized by stable, healthy functioning after a loss or by a brief period of distress in the first weeks following bereavement (Nielsen et al., 2019; Nij- borg, Westerhof, et al., 2025; Pociunaite et al., 2023), people with PGD experience prolonged and intense bereavement-related distress that impairs functioning (Killikelly et al., 2025). PGD has only recently been recognized as a mental disorder. It was included in the text-revised fifth edi- tion of the Diagnostic and Statistical Manual of Mental Disorders (DSM-5-TR; American Psychiatric Associ- ation, 2022) and in the eleventh edition of the Inter- national Classification of Diseases (ICD-11; World Health Organization, 2018). It is characterized by per- sistent separation distress (e.g. preoccupation with thoughts or memories of the deceased) alongside cog- nitive, behavioural, and emotional symptoms (e.g. intense loneliness as a result of the death). PGD symp- toms are distinct from posttraumatic stress and depression symptoms in children and adults (Boelen et al., 2017; Geronazzo-Alman et al., 2019; Heeke et al., 2022, 2023; Lenferink et al., 2021). PGD can be diagnosed six months after a loss in children (and 12 months after a loss in adults). Without treatment, PGD severity tends to remain stable and may continue to hinder children’s functioning (Melhem et al., 2011). PGD intensity in children and adolescents is com- monly assessed using self-report measures. Several instruments are available to assess PGD severity based on prior conceptualizations of disturbed grief, such as the Traumatic Grief Inventory for Children (Dyregrov et al., 2001), Inventory of Prolonged Grief for Children and for Adolescents (Spuij et al., 2012), Inventory for Complicated Grief-Revised for Children (Melhem et al., 2013), and the Persistent Complex Bereavement Disorder Checklist (Kaplow et al., 2018). These existing instruments do not capture all DSM-5-TR and ICD-11 PGD criteria, such as an inability to experience positive mood, feelings of blame, denial, and emotional numbness. Moreover, they include items assessing grief reactions that are not part of the DSM-5-TR or ICD-11 PGD criteria, such as sleep difficulties, hearing the voice of the deceased, or seeing the deceased. Recently, the Traumatic Grief Inventory-Kids- Clinician-Administered (TGI-K-CA) was developed, with input from bereaved children, adolescents, and experts. The TGI-K-CA assesses interview-based PGD intensity and probable caseness in children (aged 8–18) based on the most recent PGD criteria as defined in DSM-5-TR and ICD-11 (Van Dijk et al., 2023). An initial psychometric evaluation of the 16-item TGI-K-CA in 90 Dutch bereaved children (8–18) shows strong internal consistency for items assessing DSM-5-TR and ICD-11 PGD, although some items showed poor factor loadings. The latter pertains to items assessing the symptoms about marked sense of disbelief (in DSM-5-TR), denial (in ICD-11), avoidance (in DSM-5-TR), blame, guilt, and anger (all in ICD-11). These items also showed floor effects, which may indicate that these symptoms are either rare in this age group or not optimally cap- tured by the current item formulations, suggesting a need for further refinement of age-tailored wording. Furthermore, strong convergent validity, but weak temporal stability, was found, pointing to the possi- bility that grief in children fluctuates considerably over time. Optimal cut-off scores for detecting prob- able PGD caseness for DSM-5-TR and ICD-11 PGD items (when summed separately) were ≥29 and ≥33, respectively. These cut-off scores were ≥45 and ≥53 when summing all 16 items (van Dijk et al., 2026). To date, instruments assessing PGD intensity in children have relied primarily on self-report. How- ever, parents or caretakers may observe behavioural and emotional changes, such as anger, that children themselves may not recognize (Kassam-Adams et al., 2006). Moreover, some children may also be unable or unwilling to share their feelings due to factors like stigma (Breen et al., 2025). In addition, direct assessment of children and adolescents is not always feasible or practical. For instance, parents often initiate help-seeking on behalf of their children, and children are generally a hard-to-reach population in research. Parental or caregiver reports, therefore, pro- vide a valuable alternative and can play a crucial role in screening for PGD in children and adolescents (Stover & Keeshin, 2018). To the best of our knowledge, only one instrument to date has been developed to assess caregiver- reported ICD-11 PGD intensity in children, namely the caregiver-report version of the International Grief Questionnaire (IGQ-CG) (Redican et al., 2024). In a sample of 639 Ukrainian caregivers, sup- port was found for a correlated two-factor latent struc- ture of the ICD-11 PGD items. Separation distress (factor 1) and cognitive, behavioural, and emotional items (factor 2) loaded on two separate, but strongly related, factors. The items showed acceptable internal consistency and convergent validity (as indicated by expected associations with other mental health out- comes, time since loss, and PGD intensity in care- takers). This 5-item measure assesses seven out of 12 ICD-11 PGD symptoms, i.e. items assessing the symp- toms ‘denial’, ‘blame’, ‘feeling one has lost a part of one’s self’, ‘an inability to experience positive mood’, and ‘difficulty in engaging with social or other activi- ties’ are lacking. Moreover, some of the items assess two symptoms simultaneously (e.g. ‘they feel guilty or angry about their loss’). To capture the full spectrum of PGD symptom intensity in children through caregiver-reports, a care- giver-report version of the TGI-K-CA was developed. This instrument intends to assess caregiver-ratings of PGD symptom intensity in children per DSM-5-TR and ICD-11. This enables comparisons of diagnostic performances of these criteria-sets. In this initial vali- dation study, we evaluated the psychometric proper- ties of the Traumatic Grief Inventory-Kids- Caregiver-report (TGI-K-CR). As found in prior vali- dation research on caregiver-report measures for PGD intensity (Redican et al., 2024), we expected to find support for a two-factor structure and strong internal consistency. In terms of known-groups validity, we expected that, similar to research on trauma symp- toms in children (Egberts et al., 2018; Kassam- Adams et al., 2006), that caregivers who identify as women (vs. man) and those who reported higher PGD intensity themselves would report higher PGD intensity in their child. Moreover, based on literature reviews (Alvis et al., 2022; Falala et al., 2024), we anticipated higher caregiver-ratings of PGD intensity in children, when the child was identified as a girl (vs. boy), the loss was more recent, due to a potential traumatic circumstance (i.e. accident, homicide, suicide), and when the child had lost a nuclear family member (parent or sibling vs. other loss). Lastly, percentages of probable caseness for DSM-5-TR and ICD PGD were calculated, and provisional cut-offs for both criteria-sets were determined, enabling the distinction of probable PGD cases from non-cases."

final_paragraph = replacer(text34).lower().replace("- ", "")
final_paragraph = replace_multi_citations(final_paragraph)
print(final_paragraph)
#7, 9, 11
#test_refs = convert_to_ref_list(test33)
##print(test_refs)
##print(len(test_refs))
#test_ref_index = build_reference_index(test_refs)
#
#pro_paragraph, pro_citations = replace_citations_with_indices(text33, test33)
#
#print(pro_paragraph)
#ind = 1
#for ref in pro_citations:
#    print(f"{ind}: {ref}")
#    ind += 1
#
#ind = 1
#for ref in test_refs:
#    print(f"{ind}: {ref}")
#    ind += 1


#print(test29)
#'''