import re
import types
from types import NoneType

from typing_extensions import deprecated
import datetime
import doi_lookup as dl
import unpaywall as upw
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
        citation_infos = []
        for ref, info in references.items():
            #print(info)
            if info["has_doi"]:
                doi = info["doi"]
                unpaywall_result = lookup_unpaywall([doi])
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
                    "StoreDate" : datetime.date.today().isoformat()
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
        citation_infos = []
        unpaywall_results = lookup_unpaywall(doi)
        # this is a pd dataframe, we need to iterate over the rows
        for index, row in unpaywall_results.iterrows():
            result = row.to_dict()
            #print(result)
            if result:
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

'''
cits = """Al-Zain, A. O., & Abdulsalam, S. (2022). Impact of grit, resilience, and stress levels on burnout and well-being of dental
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

para = """Employees in Iran’s industrial sector, particularly in the oil and petrochemical industries, face high levels of occupational stress due to demanding workloads, shift schedules, and safety-critical responsibilities (Askari et al., 2023; Hoboubi et al., 2017; Mokarami et al., 2021). Workers in these industries often operate under challenging conditions that may lead to job burnout and reduced psychological well-being. Job burnout has increasingly been recognised as a major global occupational health concern. A recent meta-analysis of public health workers, encompassing a total sample of 215,787 individuals across multiple countries, estimated the overall prevalence of burnout to be 39% (95% CI: 25–53%) (Nagarajan et al., 2024). In Iran, Bastami et al. (2020) reported high burnout rates across different occupational groups: 67% among librarians, 51% among university staff, and 72% among dentists. The World Health Organization (2024) has classified burnout as an “occupational phenomenon”, emphasising its widespread prevalence across diverse sectors. Burnout has been associated with substantial organisational and economic consequences, including reduced productiv- ity, increased absenteeism, and higher turnover intentions. Given this global and national evidence – and considering that the present study focuses on employees of the Iran Petroleum Pipelines & Telecommunications Company, who operate in high-stress, safety-critical industrial roles – investigating psychological resources that may buffer burnout and support well-being is both timely and essential. Positive psychological resources, including hope, resilience, and grit, are important for coping with work- place stress and maintaining adaptive functioning. hope is defined as the determination to achieve goals and the belief that alternative pathways exist to reach them (Hefferon & Boniwell, 2011). Conceptually related to optimism, hope reflects an individual’s perceived capability to generate multiple pathways towards desired goals despite obstacles, as well as the motivational drive to pursue those pathways (Snyder, 2000). Another key personality trait influencing occupational and psychological outcomes is resilience. This capacity, which varies among individuals, allows employees to withstand and recover from workplace stressors, navigate challenging or hazardous environments, and adapt effectively to adverse experiences (Grotberg, 2003). Similarly, grit represents an important personal resource in the workplace. Beyond mere perseverance, grit reflects a sustained and often unseen form of determination that enables individuals to persist through obstacles, continuously strive for improvement in specific domains, and maintain long-term commitment to their goals (Lewis, 2014). Duckworth et al. (2007) examined the influence of passion and perseverance for long-term goals – collectively known as grit – to understand why some individuals of similar ability levels achieve greater success than others. Their findings highlighted grit as a key predictor of achievement across multiple domains of performance. It is proposed that these dispositional tendencies are more crucial than intellectual abilities in predicting long-term success. Generally, individuals with high levels of grit demon- strate the capacity to pursue personally meaningful goals over extended periods – weeks, months, or even years – despite facing obstacles, failures, or temporary setbacks (Duckworth et al., 2007). Conversely, individuals with lower grit tend to abandon or redirect their efforts towards alternative goals when confronted with similar barriers or lack of progress (Duckworth & Gross, 2014). Considering the link between hope and grit, it has been proposed that counsellors and practitioners may foster individuals’ sense of hope, which in turn can enhance their levels of grit. Georgoulas-Sherr and Kelly (2019), using structural equation modelling to examine the interrelations among resilience, grit, and stubbornness, reported a positive association between resilience and grit. Both grit and resilience – concepts broadly referring to the capacity to persevere through challenges to achieve goals – have gained attention in both popular discourse and academic literature (Stoffel & Cain, 2018). These constructs are frequently highlighted as critical factors in coping with psychological stressors (Waxman et al., 2003). While grit and resilience are sometimes used interchangeably, they represent distinct constructs. Specifically, grit is char- acterised by sustained passion and persistence towards long-term objectives, reflecting a continuous commitment to pursue and complete tasks despite encountering failures, obstacles, or adversity (Duckworth et al., 2007). To address the significant challenge of job burnout and psychological well-being among employees in high-stress Iranian industries, this study focused on three key psychological resources: hope, resilience, and grit. Hope, defined as the motivation and perceived ability to pursue goals despite obstacles (Hefferon & Boniwell, 2011; Snyder, 2000), has been shown to reduce burnout (Luthans et al., 2007; Reichard et al., 2013; Youssef & Luthans, 2007) and enhance well-being (Dursun, 2012; Kardas et al., 2019). Resilience, the capacity to adapt and recover from adversity (Grotberg, 2003), has similarly been shown to reduce burnout (Asheghi & Hashemi, 2019; Beddoe et al., 2013; Katsiroumpa et al., 2023; Lee et al., 2019; Nantsupawat et al., 2024; Strolin-Goltzman et al., 2016) and improve well-being in organisa- tional environments (Andales et al., 2025; He et al., 2018; Ríos-Risquez et al., 2018; Lee & Hasson, 2020). Grit, representing sustained passion and perseverance towards long-term goals (Duckworth et al., 2007; Lewis, 2014), not only strengthens the effects of hope and resilience but can also directly influence burnout and well-being. By examining both the direct effects and the indirect effects mediated by grit, this study aims to clarify how these psychological resources operate in reducing burnout and promoting well-being, addressing gaps in prior research that have largely overlooked their combined role in occupational environments.     According to Snyder’s Hope Theory (Snyder, 1994), hope consists of two components: agency, the determi- nation to achieve goals, and pathways, the perceived ability to find ways to reach them. Employees with higher levels of hope are more likely to stay motivated, set clear goals, and overcome obstacles at work. Hope functions as a psychological resource that enhances well-being and protects employees from burnout. Research shows that hope positively relates to job satisfaction and commitment, while reducing stress and exhaustion (Luthans et al., 2007; Reichard et al., 2013; Youssef & Luthans, 2007). In demanding work environments – like those in many Iranian organisations with limited resources and high workload – hope helps employees maintain purpose and emotional stability. Thus, hopeful employees tend to experience less burnout and greater psychological well-being. Research also indicates that hope can contribute to enhanced psychological well-being (Dursun, 2012; Kardas et al., 2019). Essentially, hope refers to having the motivation to pursue one’s goals and the ability to plan effectively to achieve them. From this perspective, goal-directed motivation and planning are expected to play a significant role in improving an individual’s quality of life and, consequently, enhancing well-being. Therefore, hope is a key variable closely linked to psychological well-being (Kardas et al., 2019) and has a negative relationship with burnout (Yavas et al., 2013). It appears that hope plays a significant role in guiding an individual’s cognitive processes and behaviours. Due to the general tendency of hopeful individuals to repeatedly experience positive mood states and goal- oriented positive outlooks, hopeful employees may be less susceptible to job burnout. On the other hand, because of their inherent tendency to find ways to overcome challenges, they may perform effectively even in the face of burnout. As the broad and constructive effects of hope accumulate and interact over time, higher levels of hope can foster positive change, making individuals more resilient and effective (Yavas et al., 2013).    Resilience has been defined in multiple ways (Cassidy, 2015), yet it is generally understood as an individual’s capacity to maintain or restore psychological well-being following exposure to adversity (Herrman et al., 2011). It represents a dynamic process through which individuals adapt positively to challenging or adverse experiences (Masten, 2001). Frequently, resilience is also described using terms such as “stress resistance” (Garmezy, 1985) or “post-traumatic growth” (Tedeschi et al., 1998), reflecting the spectrum of responses individuals exhibit when confronted with psychological trauma. In this context, resilience is recognised not only as an outcome but also as a cognitive process that facilitates adaptation and recovery (Ingram & Price, 2001). According to the American Psychological Association (2020), resilience refers to the dynamic process through which individuals effectively adjust to challenging circumstances such as trauma, threats, or major stressors. Similarly, Lee and Cranford (2008) describe it as the ability to successfully manage substantial life changes, obstacles, or risks, while Connor and Davidson (2003) consider it a personal resource that allows individuals to maintain growth and functioning in the face of hardship. Empirical studies further show that resilience contributes to reducing employee burnout (Asheghi & Hashemi, 2019; Beddoe et al., 2013; Katsiroumpa et al., 2023; Lee et al., 2019; Nantsupawat et al., 2024; Strolin-Goltzman et al., 2016). and improving well-being in Organisational environment (He et al., 2018; Ríos-Risquez et al., 2018, Lee & Hasson, 2020; Andales et al., 2025). burnout arises from prolonged exposure to occupational stress and is defined as a syndrome characterised by emotional exhaustion, depersonalisation, and a diminished sense of personal accomplishment (Schaufeli et al., 2017). It represents a chronic emotional condition often accompanied by fatigue, psychological depletion, and cognitive exhaustion. Employees experiencing burnout typically exhibit reduced motivation and impaired professional efficacy. However, resilient individuals tend to recover more rapidly from such conditions, maintaining psychological equilibrium and better emotional and physical health despite demanding circumstances (Jaureguizar et al., 2018). Under such circumstances, resilient individuals experience lower levels of burnout. Moreover, resilience has been shown to enhance psychological well-being (He et al., 2018; Ríos-Risquez et al., 2018; Lee & Hasson, 2020). Fredrickson (2001) suggested that resilience plays a crucial role in promoting psychological well-being by enabling individuals to build and sustain positive emotional resources. Similarly, Ryff and Singer (2003) argued that resilient individuals are generally better able to preserve their physical and mental health and recover more rapidly from stressful life events. Consequently, resilience contributes to greater overall psychological well-being."""

import paragraph_processor as pap

pro_paragraph, pro_citations = pap.replace_citations_with_indices(para, cits)
fin_citations = has_apa_dois(pro_citations)
print(fin_citations)
citation_infos = get_citation_infos_from_dois(fin_citations)
print(citation_infos)
#'''