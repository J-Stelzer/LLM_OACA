import re
import difflib

def replace_citations_with_indices(paragraph, references):
    final_paragraph = replacer(paragraph).lower()

    cits = extract_individual_citations(final_paragraph)
    refs = convert_to_ref_list(references)
    ref_index = build_reference_index(refs)
    linked = match_citations(cits, ref_index)
    print(linked)
    for cit, ref in linked.items():
        if ref:
            index = refs.index(ref) + 1
            final_paragraph = final_paragraph.replace(f'{cit.lower()}', f'R{index}')
            # add the index to the linked dict
            linked[cit] = {"reference": ref, "index": index}

    return final_paragraph, linked


def find_in_text_citations(paragraph):
    pattern = re.compile(r'\([a-zA-Z,.;&0-9 ]*[0-9]{4}[a-g]?\)')
    matches = pattern.findall(paragraph)
    return matches

def extract_individual_citations(paragraph):
    matches = find_in_text_citations(paragraph)
    full_refs = []
    for match in matches:
        match = match.strip('()')
        #print(match)
        pattern = r'([a-zA-Z .&]{3,}, [0-9]{4}[a-g]?)' #([a-zA-Z .&]{3,}, [0-9]{4}[a-g]?)|([0-9]{4}[a-g]?)
        refs = re.findall(pattern, match, flags=re.MULTILINE)
        for ref in refs:
            ref = ref.strip().lower()
            full_refs.append(ref)

    #print(full_refs)
    return full_refs


def build_reference_index(references):

    index = {}

    for ref in references:

        ref_l = ref.lower()

        year_match = re.search(r'\((\d{4}[a-z]?)\)', ref_l)
        if not year_match:
            continue

        year = year_match.group(1)

        authors_part = ref_l.split("(")[0]
        authors = re.findall(r'([a-z\-]+)\s*,', authors_part)

        if not authors:
            continue

        if len(authors) == 1:
            key = f"{authors[0]}, {year}"

        elif len(authors) == 2:
            key = f"{authors[0]} & {authors[1]}, {year}"

        else:
            key = f"{authors[0]} et al., {year}"

        index[key] = ref

    return index



def parse_citation(citation):

    c = citation.lower()
    c = re.sub(r'\s+', ' ', c)

    return c.strip()


def match_citations(citations, ref_index):

    results = {}

    for citation in citations:

        key = parse_citation(citation)
        results[citation] = ref_index.get(key)

    return results



def convert_to_flow(paragraph):
    return paragraph.replace('-\n', '').replace('\n', ' ')


def convert_to_ref_list(citations):
    citations = re.sub(r'-\n\s*', '', citations)
    citations = re.sub(r'\n+', '\n', citations)
    pattern = r'(?=^([a-zA-Z_\u00C0-\u02AF\u00B4 \-]+,\s+[a-zA-Z_\u00C0-\u02A0\u00B4]\.|[a-zA-Z_\u00C0-\u02AF\u00B4 ]{3,}\.\s+\(\d{4}\)))'

    splits = re.split(pattern, citations, flags=re.MULTILINE)
    print(len(splits))
    refs = []
    for i in range(1, len(splits), 2):
        refs.append(replacer(splits[i+1]))
    x = 0
    print_each(refs)
    while x < len(refs):
        if refs[x] and refs[x].endswith(('.,', '-', '., &', '., & the')):
            refs[x] = refs[x] + " " + refs[x+1]
            del refs[x+1]
        else:
            x += 1
    return refs


def combine_refs(refs):
    i = 0
    while i < len(refs) - 1:
        ref = refs[i]

        if ref.endswith(('.,\n', '-\n', '., &\n', '., & the\n')):
            refs[i] = ref + refs[i + 1]
            del refs[i + 1]
            # stay on same index to re-check merged result
        else:
            i += 1

    return refs


def remove_duplicate_refs(ref, refs):
    i = refs.index(ref)

    while i > 0:
        prev = refs[i - 1]

        # Only merge if prev is literally a prefix of ref
        if ref.startswith(prev[:30]):  # stricter than last-10-chars
            if prev not in ref:
                ref = prev + ref[len(prev):]
                refs[i] = ref
            del refs[i - 1]
            i -= 1
        else:
            break

    return refs



def replacer(citation):
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

text = """abid, g., contreras, F., ahmed, s., & Qazi, t. (2019). contextual factors and organizational commitment: examining
the mediating role of thriving at work. Sustainability, 11(17), 4686. https://doi.org/10.3390/su11174686
abid, g., sajjad, I., elahi, n. s., Farooqi, s., & nisar, a. (2018). the influence of prosocial motivation and civility on work
engagement: the mediating role of thriving at work. Cogent Business & Management, 5(1), 1493712. https://doi.org/10.1080/23311975.2018.1493712
abid, g., ahmed, a., & Butt, t. h. (2022a). tri-dimensional thriving scale (tts): Measurement and construct validation.
International Journal of Business Excellence, 28(2), 139–156. https://doi.org/10.1504/IJBeX.2020.10035475
abid, g., ahmed, a., Qazi, t. F., ahmed, s., & Islam, t. (2022b). relationships between curiosity, thriving, and incivility:
Implications for constructive voice behaviour. International Journal of Business Excellence, 27(4), 479–501. scopus -
Q2- X https://doi.org/10.1504/IJBeX.2022.125106
abid, g., & contreras, F. (2022). Mapping thriving at work as a growing concept: review and directions for future
studies. Information, 13(8), 383. scopus - Q2 – X https://doi.org/10.3390/info13080383
adair erickson, r., & roloff, M. e. (2008). reducing attrition after downsizing: analyzing the effects of organizational
support, supervisor support, and gender on organizational commitment. International Journal of Organizational
Analysis, 15(1), 35–55. https://doi.org/10.1108/19348830710860147
agarwala, t., arizkuren-eleta, a., del castillo, e., Muñiz-Ferrer, M., & gartzia, l. (2014). Influence of managerial support
on work–life conflict and organizational commitment: an international comparison for India, Peru and spain. The International Journal of Human Resource Management, 25(10), 1460–1483. https://doi.org/10.1080/09585192.2013.870315
ahlf, h., horak, s., klein, a., & yoon, s. W. (2019). demographic homophily, communication and trust in
intra-organizational business relationships. Journal of Business & Industrial Marketing, 34(2), 474–487. https://doi.org/10.1108/jbim-03-2018-0093
alfes, k., truss, c., soane, e. c., rees, c., & gatenby, M. (2013). the relationship between line manager behavior, per-
ceived hrM practices, and individual performance: examining the mediating role of engagement. Human Resource
Management, 52(6), 839–859. https://doi.org/10.1002/hrm.21512
anderson, s. e., coffey, B. s., & Byerly, r. t. (2002). Formal organizational initiatives and informal workplace practices:
links to work-family conflict and job-related outcomes. Journal of Management, 28(6), 787–810. https://doi.org/10.1177/014920630202800605
arrow, h., Mcgrath, J. e., & Berdahl, J. l. (2000). Small groups as complex systems: Formation, coordination, development,
and adaptation. sage Publications.
arshad, M., abid, g., & khan, M. M. (2020). Impact of employee’s environmental concern on ecological green behav-
ior: Mediation mechanism of employee customer oriented ocB and organizational commitment. International
Journal of Innovation, Creativity and Change, 14(12), 614–633.
arshad, M., abid, g., contreras, F., elahi, n. s., & athar, M. a. (2021). Impact of prosocial motivation on organiza-
tional citizenship behavior and organizational commitment: the mediating role of managerial support. European
Journal of Investigation in Health, Psychology and Education, 11(2), 436–449. https://doi.org/10.3390/ejihpe11020032
Blau, P. M. (1964a). social exchange theory. 3(2007), 62.
Blau, P. M. (1964b). Exchange and power in social life. John Wiley and sons.
Bliese, P. d. (2000). Within-group agreement, non-independence, and reliability: Implications for data aggregation and
analysis. In k. J. klein & s. W. J. kozlowski (eds.), Multi-level theory, research, and methods in organizations:
Foundations, extensions, and new directions (349–381). Jossey-Bass.
Boudreau, J. W., Jesuthasan, r., & creelman, d. (2015). Lead the work: Navigating a world beyond employment. John
Wiley & sons.
cai, z., huo, y., lan, J., chen, z., & lam, W. (2019). When do frontline hospitality employees take charge? Prosocial
motivation, taking charge, and job performance: the moderating role of job autonomy. Cornell Hospitality Quarterly,
60(3), 237–248. https://doi.org/10.1177/1938965518797081
campbell, d. t., & Fiske, d. W. (1959). convergent and discriminant validation by the multitrait-multimethod matrix.
Psychological Bulletin, 56(2), 81–105. https://doi.org/10.1037/h0046016
carmeli, a., & spreitzer, g. M. (2009). trust, connectivity, and thriving: Implications for innovative behaviors at work.
The Journal of Creative Behavior, 43(3), 169–191. https://doi.org/10.1002/j.2162-6057.2009.tb01313.x
eisenberger, r., karagonlar, g., stinglhamber, F., neves, P., Becker, t. e., gonzalez-Morales, M. g., & steiger-Mueller, M.
(2010). leader–member exchange and affective organizational commitment: the contribution of supervisor’s orga-
nizational embodiment. The Journal of Applied Psychology, 95(6), 1085–1103. https://doi.org/10.1037/a0020858
eisenberger, r., rhoades shanock, l., & Wen, X. (2020). Perceived organizational support: Why caring about employees counts. Annual Review of Organizational Psychology and Organizational Behavior, 7(1), 101–124. https://doi.org/10.1146/annurev-orgpsych-012119-044917
emerson, r. M. (1976). social exchange theory. Annual Review of Sociology, 2, 335–362. https://doi.org/10.1146/annurev.so.02.080176.002003
Firth, r. (1967). Themes in economic anthropology. tavistock.
george, J. M., & Bettenhausen, k. (1990). understanding prosocial behavior, sales performance, and turnover: a group-level
analysis in a service context. Journal of Applied Psychology, 75(6), 698–709. https://doi.org/10.1037/0021-9010.75.6.698
grant, a. M. (2007). relational job design and the motivation to make a prosocial difference. Academy of Management
Review, 32, 393–417. https://doi.org/10.5465/amr.2007.24351328
grant, a. M., & Mayer, d. M. (2009). good soldiers and good actors: Prosocial and impression management motives
as interactive predictors of affiliative citizenship behaviors. The Journal of Applied Psychology, 94(4), 900–912.
https://doi.org/10.1037/a0013770
grant, a. M., & sumanth, J. J. (2009). Mission possible? the performance of prosocially motivated employees de-
pends on manager trustworthiness. The Journal of Applied Psychology, 94(4), 927–944. https://doi.org/10.1037/a0014391
gallup, P. B. (2016). The 2013 Gallup-Hope Index.
hair, J. F., celsi, M., ortinau, d. J., & Bush, r. P. (2010). Essentials of marketing research. (Vol. 2). Mcgraw-hill/Irwin.
James, d. l., demaree, r. g., & Wolf, g. (1984). estimating within-group interrater reliability with and without re-
sponse bias. Journal of Applied Psychology, 69(1), 85–98. https://doi.org/10.1037/0021-9010.69.1.85
kelloway, e. k., & day, a. l. (2005). Building healthy workplaces: What we know so far. Canadian Journal of Behavioural
Science / Revue Canadienne Des Sciences du Comportement, 37(4), 223–235. https://doi.org/10.1037/h0087259
khan, s. u. k. (2005). Macro determinants of total Factor Productivity in Pakistan. Published in. SBP Research Bulletin,
2(2), 383–401.
khan, n. a., khan, a. n., soomro, M. a., & khan, s. k. (2020). transformational leadership and civic virtue behavior:
Valuing act of thriving and emotional exhaustion in the hotel industry. Asia Pacific Management Review, 25(4),
216–225. https://doi.org/10.1016/j.apmrv.2020.05.001
klein, h. J., Molloy, J. c., & Brinsfield, c. t. (2012). reconceptualizing workplace commitment to redress a stretched
construct: revisiting assumptions and removing confounds. Academy of Management Review, 37(1), 130–151.
https://doi.org/10.5465/arma.2010.0018
kleine, a. k., rudolph, c. W., & zacher, h. (2019). thriving at work: a meta‐analysis. Journal of Organizational Behavior,
40(9-10), 973–999. https://doi.org/10.1002/job.2375
kozlowski, s. W. J., & klein, k. J. (2000). a multi-level approach to theory and research in organizations: contextual,
temporal, and emergent processes. In k. J. klein & s. W. J. kozlowski (eds.), Multi-level theory, research, and methods
in organizations: Foundations, extensions, and new directions. (pp. 3–90). Jossey-Bass.
lawler, e. J. (2001). an affect theory of social exchange. American Journal of Sociology, 107(2), 321–352. https://doi.org/10.1086/324071
leBreton, J. M., & senter, J. l. (2008). answers to 20 questions about interrater reliability and interrater agreement.
Organizational Research Methods, 11(4), 815–852. https://doi.org/10.1177/1094428106296642
li, J. (2015). the mediating roles of job crafting and thriving in the lMX-employee outcomes relationship. Japanese
Journal of Administrative Science, 28(1), 39–51. https://doi.org/10.5651/jaas.28.39
liao, h., liu, d., & loi, r. (2010). looking at both sides of the social exchange coin: a social cognitive perspective on
the joint effects of relationship quality and differentiation on creativity. Academy of Management Journal, 53(5),
1090–1109. https://doi.org/10.5465/amj.2010.54533207
Mowday, r. t., steers, r. M., & Porter, l. W. (1979). the measurement of organizational commitment. Journal of
Vocational Behavior, 14(2), 224–247. https://doi.org/10.1016/0001-8791(79)90072-1
nawaz, M., abid, g., & Quartey-Papafio, t. k. (2022). relation of workplace incivility, prosocial motivation and emo-
tional exhaustion to thriving of nurses. Nursing: Research and Reviews, ume 12, 207–222. https://doi.org/10.2147/nrr.s373694
niessen, c., sonnentag, s., & sach, F. (2012). thriving at work-a diary study. Journal of Organizational Behavior, 33(4),
468–487. https://doi.org/10.1002/job.763
noranee, s., amir Ishak, n., raja Mustapha, r. M., & Mohamad Besir, M. s. (2016). employee Prosocial Motivation and
Interpersonal citizenship Behavior: the supervisor rating of leader-Member exchange Quality as a Mediator. In
Proceedings of the 1st AAGBS International Conference on Business Management 2014 (AiCoBM 2014). (pp. 221–233).
springer singapore.
ong, J. F. B., tan, J. M. t., Villareal, r. F. c., & chiu, J. l. (2019). Impact of quality work life and prosocial motivation
on the organizational commitment and turnover intent of public health practitioners. Review of Integrative Business
and Economics Research, 8, 24–43.
Paterson, t. a., luthans, F., & Jeung, W. (2014). thriving at work: Impact of psychological capital and supervisor sup-
port. Journal of Organizational Behavior, 35(3), 434–446. https://doi.org/10.1002/job.1907
Podsakoff, P. M., Mackenzie, s. B., lee, J. y., & Podsakoff, n. P. (2003). common method biases in behavioral research:
a critical review of the literature and recommended remedies. The Journal of Applied Psychology, 88(5), 879–903.
https://doi.org/10.1037/0021-9010.88.5.879
Porath, c., spreitzer, g., gibson, c., & garnett, F. g. (2012). thriving at work: toward its measurement, construct val-
idation, and theoretical refinement. Journal of Organizational Behavior, 33(2), 250–275. https://doi.org/10.1002/job.756
Prem, r., ohly, s., kubicek, B., & korunka, c. (2017). thriving on challenge stressors? exploring time pressure and
learning demands as antecedents of thriving at work. Journal of Organizational Behavior, 38(1), 108–123. https://doi.org/10.1002/job.2115
rioux, s. M., & Penner, l. a. (2001). the causes of organizational citizenship behavior: a motivational analysis. The
Journal of Applied Psychology, 86(6), 1306–1314. https://doi.org/10.1037/0021-9010.86.6.1306
saleem, M., abid, g., & Butt, t. h. (2025). Mediating mechanism of thriving at work between family motivation, abu-
sive supervision and organizational commitment. European J. of International Management, 26(1), 140–159. https://doi.org/10.1504/eJIM.2025.145410
settoon, r. P., Bennett, n., & liden, r. c. (1996). social exchange in organizations: Perceived organizational support,
leader–member exchange, and employee reciprocity. Journal of Applied Psychology, 81(3), 219–227. https://doi.org/10.1037/0021-9010.81.3.219
siemsen, e., roth, a., & oliveira, P. (2010). common method bias in regression models with linear, quadratic, and
interaction effects. Organizational Research Methods, 13(3), 456–476. https://doi.org/10.1177/1094428109351241
shao, B., cardona, P., ng, I., & trau, r. n. (2017). are prosocially motivated employees more committed to their orga-
nization? the roles of supervisors’ prosocial motivation and perceived corporate social responsibility. Asia Pacific
Journal of Management, 34(4), 951–974. https://doi.org/10.1007/s10490-017-9512-5
sonenshein, s., dutton, J. e., grant, a. M., spreitzer, g. M., & sutcliffe, k. M. (2013). growing at work: employees’ in-
terpretations of progressive -change in organizations. Organization Science, 24(2), 552–570. https://doi.org/10.1287/orsc.1120.0749
spreitzer, g., & Porath, c. (2012). creating sustainable performance. Harvard Business Review, 90(1), 92–99, 152.
spreitzer, g. M., & Porath, c. (2014). 15 -determination as for thriving: Building an Integrative Model of human
growth at Work. The Oxford Handbook of Work Engagement, Motivation, and Self-Determination Theory, 245.
spreitzer, g. M., & sutcliffe, k. M. (2007). thriving in organizations. Positive Organizational Behavior, 33, 74–85.
spreitzer, g. M., sutcliffe, k., dutton, J., sonenshein, s., & grant, a. M. (2005). a socially embedded model of thriving
at work. Organization Science, 16(5), 537–549. https://doi.org/10.1287/orsc.1050.0153
thakur, M., Bansal, a., stokes, P (2016). the role of thriving and training in merger success: an integrative learning
perspective. In c. l. cooper 998 kleIne., et al. & s. Finkelstein (eds.), Advances in Mergers and Acquisitions. (pp.
1–35). emerald.
tse, h. h., & dasborough, M. t. (2008). a study of exchange and emotions in team member relationships. Group &
Organization Management, 33(2), 194–215. https://doi.org/10.1177/1059601106293779
ullah, I., elahi, n. s., abid, g., & Butt, M. u. (2020). the impact of perceived organizational support and proactive
personality on affective commitment: Mediating role of prosocial motivation. Business, Management and Economics
Engineering, 18(2), 183–205. https://doi.org/10.3846/bme.2020.12189
utz, s., Muscanell, n., & göritz, a. s. (2014). give, match, or take: a new personality construct predicts resource and
information sharing. Personality and Individual Differences, 70, 11–16. https://doi.org/10.1016/j.paid.2014.06.011
Van der Voet, J., steijn, B., & kuipers, B. s. (2017). What’s in it for others? the relationship between prosocial motiva-
tion and commitment to change among youth care professionals. Public Management Review, 19(4), 443–462.
https://doi.org/10.1080/14719037.2016.1183699
Vivek, s. a., & raveeendran, d. (2017). thriving at workplace by bank managers: an empirical study of public and
private sector banks. International Journal of Entrepreneurship and Development Studies, 5(1), 1–11.
Wallace, J. c., Butts, M. M., Johnson, P. d., stevens, F. g., & smith, M. B. (2016). a multi-level model of employee
innovation: understanding the effects of regulatory focus, thriving, and employee involvement climate. Journal of
Management, 42(4), 982–1004. https://doi.org/10.1177/0149206313506462
Walumbwa, F. o., avolio, B. J., gardner, W. l., Wernsing, t. s., & Peterson, s. J. (2008). authentic leadership:
development and validation of a theory-based measure. Journal of Management, 34(1), 89–126. https://doi.org/10.1177/0149206307308913
Walumbwa, F. o., hartnell, c. a., & Misati, e. (2017). does ethical leadership enhance group learning behavior?
examining the mediating influence of group ethical conduct, justice climate, and peer justice. Journal of Business
Research, 72, 14–23. https://doi.org/10.1016/j.jbusres.2016.11.013
Walumbwa, F. o., hartnell, c. a., & oke, a. (2010). servant leadership, procedural justice climate, service climate,
employee attitudes, and organizational citizenship behavior: a cross-level investigation. The Journal of Applied
Psychology, 95(3), 517–529. https://doi.org/10.1037/a0018867
Walumbwa, F. o., Muchiri, M. k., Misati, e., Wu, c., & Meiliani, M. (2016). Fired up to perform: a multi-level examina-
tion of antecedents and consequences of thriving at work. In Academy of Management Proceedings. (Vol. 2016, no.
1, p. 10494). 10510: academy of Management. https://doi.org/10.5465/ambpp.2016.79
Walumbwa, F. o., Muchiri, M. k., Misati, e., Wu, c., & Meiliani, M. (2018). Inspired to perform: a multi-level investiga-
tion of antecedents and consequences of thriving at work. Journal of Organizational Behavior, 39(3), 249–261.
https://doi.org/10.1002/job.2216"""

text2 = """cakirpaloglu, P., Šmahaj, J., cakirpaloglu, s., & Zielina, M. (2016). Workplace bullying in the Czech Republic: Theory,
research, and practice. Palacký University olomouc. (original work published in czech).
chytilová, e., yorgová, y., & Kušnirová, R. (2025). impact of HRM digitalisation on companies’ performance.
Entrepreneurship and Sustainability Issues, 13(1), 259–273. https://doi.org/10.9770/t2484277887
coyne, i., Farley, s., axtell, c., sprigg, c., Best, l., & Kwok, o. (2017). Understanding the relationship between experienc-
ing workplace cyberbullying, employee mental strain and job satisfaction: a dysempowerment approach. The
International Journal of Human Resource Management, 28(7), 945–972. https://doi.org/10.1080/09585192.2015.1116454
Demerouti, e., Bakker, a. B., Nachreiner, F., & schaufeli, W. B. (2001). the Job Demands–Resources model of burnout.
Journal of Applied Psychology, 86(3), 499–512. https://doi.org/10.1037/0021-9010.86.3.499
einarsen, s., Hoel, H., & Notelaers, g. (2009). Measuring exposure to bullying and harassment at work: Validity, factor
structure and psychometric properties of the Negative acts Questionnaire–Revised. Work & Stress, 23(1), 24–44.
https://doi.org/10.1080/02678370902815673
einarsen, s., Hoel, H., Zapf, D., & cooper, c. l. (2011). Bullying and harassment in the workplace: Developments in
theory, research, and practice. cRc Press.
einarsen, s. V., Hoel, H., Zapf, D., & cooper, c. l. (eds.) (2020). Bullying and harassment in the workplace: Theory,
research and practice (3rd ed.). cRc Press.
einarsen, s. V., skogstad, a., & Nielsen, M. B. (2020). the measurement of workplace bullying: Key issues and recom-
mendations. Frontiers in Psychology, 11, 583510. https://doi.org/10.3389/fpsyg.2020.583510
Hassard, J., teoh, K. R., Visockaite, g., Dewe, P., & cox, t. (2018). the cost of work-related stress to society: a system-
atic review. Journal of Occupational Health Psychology, 23(1), 1–17. https://doi.org/10.1037/ocp0000069
Hogh, a., Hoel, H., & carneiro, i. g. (2011). Bullying and employee turnover among healthcare workers: a three-wave
prospective study. Journal of Nursing Management, 19(6), 742–751. https://doi.org/10.1111/j.1365-2834.2011.01264.x
Khan, M. s., elahi, N. s., & abid, g. (2021). Workplace incivility and job satisfaction: Mediation of subjective well-being
and moderation of forgiveness climate in the health care sector. European Journal of Investigation in Health,
Psychology and Education, 11(4), 1107–1119. https://doi.org/10.3390/ejihpe11040082
Kline, R., & lewis, D. (2019). the price of fear: estimating the financial cost of bullying and harassment to the NHs
in england. Public Money & Management, 39(3), 166–174. https://doi.org/10.1080/09540962.2018.1535044
lever, i., Dyball, D., greenberg, N., & stevelink, s. a. M. (2019). Health consequences of bullying in the healthcare
workplace: a systematic review. Journal of Advanced Nursing, 75(12), 3195–3209. https://doi.org/10.1111/jan.13986
løvvik, c., Øverland, s., Nielsen, M. B., Jacobsen, H. B., & Reme, s. e. (2022). associations between workplace bullying
and later benefit recipiency among workers with common mental disorders. International Archives of Occupational
and Environmental Health, 95(4), 791–798. https://doi.org/10.1007/s00420-021-01764-1
Machul, M., Krasucka, K. N., Pelc, D., & Dziurka, M. (2024). impact of workplace bullying on nursing care quality: a
comprehensive review. Medical Science Monitor: International Medical Journal of Experimental and Clinical Research,
30, e944815. https://doi.org/10.12659/MsM.944815
Mikšík, o. (2004). Dotazník sUPso – postihování a hodnocení struktury a dynamiky subjektivních prožitků a stavů –
příručka [sUPso Questionnaire – assessment and evaluation of the structure and dynamics of subjective experi-
ences and states: Manual]. Psychodiagnostika, s. r. o.
Nielsen, M. B., & einarsen, s. V. (2018). What we know, what we do not know, and what we should and could have
known about workplace bullying: an overview of the literature and agenda for future research. Aggression and
Violent Behavior, 42, 71–83. https://doi.org/10.1016/j.avb.2018.06.007
Nielsen, M. B., Matthiesen, s. B., & einarsen, s. (2010). the impact of methodological moderators on prevalence rates
of workplace bullying: a meta-analysis. Journal of Occupational and Organizational Psychology, 83(4), 955–979.
https://doi.org/10.1348/096317909x481256
Piri, s., Jalali, R., & Khatony, a. (2024). consequences of workplace bullying from nurses’ perspectives: a qualitative
descriptive study in iran. Nursing Open, 11(10), e70060. https://doi.org/10.1002/nop2.70060
Porath, c. l., & Pearson, c. M. (2013). the price of incivility. Harvard Business Review, 91(1–2), 114–121. https://
pubmed.ncbi.nlm.nih.gov/23390745/
Ribeiro, N., semedo, a. s., gomes, D., Bernardino, R., & singh, s. (2022). the effect of workplace bullying on burnout:
the mediating role of affective well-being. Management Research Review, 45(6), 824–840. https://doi.org/10.1108/mrr-07-2021-0514
samsudin, e. Z., isahak, M., & Rampal, s. (2021). Measuring exposure to workplace bullying among Malaysian junior
doctors: Psychometric properties of the Negative acts Questionnaire–Revised. Journal of Health and Translational
Medicine, 24(2), 110–116. https://doi.org/10.22452/jummec.vol24no2.15
smith, l. M., andrusyszyn, M. a., & spence laschinger, H. K. (2010). effects of workplace incivility and empowerment
on newly graduated nurses’ organizational commitment. Journal of Nursing Management, 18(8), 1004–1015. https://doi.org/10.1111/j.1365-2834.2010.01165.x
statsoft inc. (2013). Electronic statistics textbook. statsoft.
szarek, s., & szarek, e. (2018). economic effects of mobbing and violence in the workplace. Przedsiębiorczość i
Zarządzanie, 19(3.2), 255–269.
Vessey, J. a., DeMarco, R. F., gaffney, D. a., & Budin, W. c. (2009). Bullying of staff registered nurses in the workplace.
Journal of Professional Nursing, 25(5), 299–306. https://pubmed.ncbi.nlm.nih.gov/19751935/
World Health organization. (2022). Mental health at work fact sheet. Retrieved from https://www.who.int/news-room/
factsheets/detail/mental-health-at-work
yang, N. y., & choi, s. B. (2021). influence of personality factors and the perceived nursing organizational culture on
workplace bullying of nurses. Journal of Korean Academic Society of Home Health Care Nursing, 28(2), 124–134.
https://doi.org/10.5977/jkasne.2024.30.3.242"""


test = """nowadays, organizations are operating in increasingly volatile environments, and to achieve a sustainable
competitive advantage, they can encourage workplace behaviors that foster a favorable psychological
and social climate by enabling employees to thrive in their work environment (abid et al., 2022a, abid & contreras, 2022; saleem et al., 2025). the presence of a thriving workforce is imperative for ensuring
competitiveness and sustainable performance in contemporary organizational contexts characterized by
continual growth (Prem et al., 2017). the thriving workforce provides a competitive edge for organiza-
tions in growth phases and contributes significantly to the development of a psychologically healthy
workplace. gallup’s (2016) survey estimates that 32% of the workforce is engaged, 51% is not engaged,
and 17% is actively disengaged. the result is a workforce that does not perform well, often stays absent,
and tends to leave the job. at the same time, the new millennial seeks more meaning, flexibility in their
work (Boudreau et al., 2015), and a healthy workplace. kelloway and day (2005) define a healthy work-
place as one that reduces stress and negative demands, promoting individuals’ overall well-being. In
other words, employees want a working environment that provides them with opportunities to thrive
rather than merely survive (spreitzer & Porath, 2012).
spreitzer and her coauthors describe workplace thriving as “a positive and desirable psychological
state in which employees experience a sense of vitality and learning.” spreitzer et al. (2005) have defined
vitality, the primary dimension of thriving, as “a positive feeling of having energy and feeling alive.”
authors define the second dimension of learning as “a sense that they are acquiring and applying valu-
able knowledge and skills.” the presence of vitality and learning in employees is a crucial prerequisite for
thriving in the workplace. a thriving workforce is associated with significant organizational outcomes,
including lower levels of burnout, reduced absenteeism, increased job satisfaction, greater engagement
and commitment, increased resilience, and the display of more innovative work behavior (abid et al., 2019).
over the last two decades, significant research has been conducted on thriving; however, the existing
corpus of knowledge is fragmented, and there is a need for research on systematic and theory-based
synthesis (abid & contreras, 2022). Moreover, this construct has been examined predominantly at the
individual level; there remains a paucity of research addressing collective thriving. the current literature
on collective thriving at work lacks extensive information on identifying the most basic antecedents and
consequences, and it lacks a framework for future study and organizational practice (kleine et al., 2019).
second, while many studies have demonstrated the empirical validation of thriving (spreitzer & Porath,
2012), research on workplace thriving remains limited (niessen et al., 2012). this study aims to fill this
gap by investigating the antecedents and consequences of collective thriving.
evidence from empirical studies has shown that organizational commitment is fostered by trust, per-
ceptions of fairness, managerial coaching (abid et al., 2019), managerial support (agarwala et al., 2014;
arshad et al., 2021), and prosocial motivation (ullah et al., 2020). however, the mechanism underlying
the relationship is still in its infancy at the group level. We suggest that collective thriving at work serves
as a mediating mechanism that transforms the impact of managerial support and prosocial motivation
on the building of collective affective organizational commitment.
organizational and/or Managerial support fosters an environment where employees feel valued, cared
for, and encouraged to contribute beyond their formal roles (eisenberger et al., 2020). When managers
recognize, provide guidance, and support, the subordinates are more likely to internalize organizational
goals and develop stronger prosocial motives to benefit others (ullah et al., 2020) and the collective unit.
Moreover, a supportive managerial climate enhances employees’ psychological safety and access to
resources, promoting both vitality and learning—the two key dimensions of thriving at work. supportive
managers empower teams and create development opportunities, leading to higher collective thriving.
Prosocial motivation promotes the sense of learning and vitality (abid et al., 2018; nawaz et al., 2022).
similarly, groups characterized by high prosocial motivation tend to engage in helping behaviors, posi-
tive interactions, and mutual learning, which strengthen team vitality and learning. When employees are
motivated to benefit others, they collectively experience greater energy and growth, resulting in higher
group-level thriving. employees who experience learning and vitality at the workplace at the collective
level are more likely to demonstrate organizational commitment at the collective level also.
this study will contribute by providing a deeper insight into the role of managerial support and pro-
social motivation, which will help employers create an environment where employees can thrive.
Furthermore, we respond to Walumbwa et al. (2017) call, which encourages future studies to investigate
the predictors and outcomes of workplace thriving at the group level of investigation. Finally, our study
at the group level extends the literature on positive psychology by investigating the role that thriving at
work serves as a self-regulatory mediating mechanism between antecedents (i.e. managerial support and
prosocial motivation) and consequences (i.e. affective organizational commitment)."""


text3 = """cossman, J. s., & street, d. (2009). Mississippi burnout. Part i: Personal characteristics and practice context. Journal
of the Mississippi State Medical Association, 50(9), 306–310.
El-hashash, E., & shiekh, R. (2022). a comparison of the Pearson, spearman rank and Kendall tau correlation coeffi-
cients using quantitative variables. Asian Journal of Probability and Statistics, 20(3), 36–48. https://doi.org/10.9734/ajpas/2022/v20i3425
Elo, a., leppänen, a., & Jahkola, a. (2003). Validity of a single-item measure of stress symptoms. Scandinavian Journal
of Work, Environment & Health, 29(6), 444–451. https://doi.org/10.5271/sjweh.752
Fernández-arata, M., dominguez-lara, s. a., & Merino-soto, c. (2017). Ítem único de burnout académico y su relación
con autoeficacia académica en estudiantes universitarios. Enfermería Clínica, 27(1), 60–61. https://doi.org/10.1016/j.enfcli.2016.07.001
Kendall, M. g., & gibbons, J. d. (1990). Rank correlation methods (5th ed.). Edward arnold.
Kilic, R., nasello, J. a., Melchior, V., & triffaux, J. M. (2021). academic burnout among medical students: Respective
importance of risk and protective factors. Public Health, 198, 187–195. https://doi.org/10.1016/j.puhe.2021.07.025
Koropets, o., Fedorova, a., & Kacane, i. (2019). Emotional and academic burnout of students combining education
and work. in Proceedings of EdulEaRn19 11th International Conference on Education and New Learning Technologies
(pp. 8227–8232). iatEd. https://doi.org/10.21125/edulearn.2019.2038
Koutsimani, P., Montgomery, a., & georganta, K. (2019). the relationship between burnout, depression, and anxiety:
a systematic review and meta-analysis. Frontiers in Psychology, 10, 284. https://doi.org/10.3389/fpsyg.2019.00284
Kristensen, t. s., Borritz, M., Villadsen, E., & christensen, K. B. (2005). the copenhagen burnout inventory: a new tool
for the assessment of burnout. Work & Stress, 19(3), 192–207. https://doi.org/10.1080/02678370500297720
Kroenke, K., spitzer, R. l., & Williams, J. B. (2003). the patient health questionnaire-2: Validity of a two-item depression
screener. Medical Care, 41(11), 1284–1292. https://doi.org/10.1097/01.MlR.0000093487.78664.3c
Kroenke, K., spitzer, R. l., Williams, J. B., & löwe, B. (2009). an ultra-brief screening scale for anxiety and depression:
the PhQ-4. Psychosomatics, 50(6), 613–621. https://doi.org/10.1016/s0033-3182(09)70864-3
Kroenke, K., spitzer, R. l., Williams, J. B., Monahan, P. o., & löwe, B. (2007). anxiety disorders in primary care:
Prevalence, impairment, comorbidity, and detection. Annals of Internal Medicine, 146(5), 317–325. https://doi.org/10.7326/0003-4819-146-5-200703060-00004
lin, s.-h., & huang, y.-c. (2014). life stress and academic burnout. Active Learning in Higher Education, 15(1), 77–90.
https://doi.org/10.1177/1469787413514651
Maslach, c., & leiter, M. P. (2016). understanding the burnout experience: Recent research and its implications for
psychiatry. World Psychiatry, 15(2), 103–111. https://doi.org/10.1002/wps.20311
Menacho-Rivera, J., castro-Ramirez, l., yarasca-Berrocal, E., huamani-Echaccaya, J., hernández-Vergara, c.,
ladera-castañeda, M., & cayo-Rojas, c. (2025). academic burnout syndrome associated with anxiety, stress, depres-
sion, and quality of life in Peruvian dentistry students: an analysis using a multivariable regression model. BMC
Medical Education, 25(1), 998. https://doi.org/10.1186/s12909-025-07604-x
Merino-soto, c., & Fernández-arata, J. M. (2020). Ítem único de burnout académico: correlato con MBi-s en el nivel
de los ítems. Educación Médica, 21(1), 61–62. https://doi.org/10.1016/j.edumed.2018.10.004
Merino-soto, c., & Fernández-arata, M. (2017). Ítem único de burnout en estudiantes de educación superior: Estudio
de validez de contenido. Educación Médica, 18(3), 195–198. https://doi.org/10.1016/j.edumed.2016.06.019
Merino-soto, c., angulo-Ramos, M., llaja-Rojas, V., & chans, g. M. (2024). academic performance, emotional intelli-
gence, and academic burnout: a cross-sectional study of a mediational effect in nursing students. Nurse Education
Today, 139, 106221. https://doi.org/10.1016/j.nedt.2024.106221
Merino-soto, c., Juárez-garcía, a., salinas-Escudero, g., & toledano-toledano, F. (2022). item-level psychometric anal-
ysis of the Psychosocial Processes at Work scale (PRoPsit) in workers. International Journal of Environmental
Research and Public Health, 19(13), 7972. https://doi.org/10.3390/ijerph1907972
Popa-Velea, o., stoian-Bǎlǎşoiu, i. R., Mihai, a., Mihǎilescu, a. i., & diaconescu, l. V. (2025). Prevention strategies
against academic burnout: the perspective of Romanian health sciences students in the aftermath of the coVid-19
pandemic. Frontiers in Psychology, 16, 1465807. https://doi.org/10.3389/fpsyg.2025.1465807
Puig-lagunes, a. a., Mendez-lara, l. a., & ortiz-cruz, F. (2025). academic burnout in Mexican medical students: a
critical review of prevalence, risk factors, and gaps in intervention. International Journal of Medical Students, 13(1),
73–86. https://doi.org/10.5195/ijms.2025.2461
Puth, M., neuhäuser, M., & Ruxton, g. (2015). Effective use of spearman’s and Kendall’s correlation coefficients for
association between two measured traits. Animal Behaviour, 102, 77–84. https://doi.org/10.1016/j.anbehav.2015.01.010
Reyna-castillo, M., Pulgarín-Rodríguez, M. a., Ríos-serna, a. h., & santiago, a. (2022). Pls-sEM validation for burnout
measures in latino college students: a socially sustainable educational return. Sustainability, 14(21), 14635. https://doi.org/10.3390/su142114635
Rohland, B. M., Kruse, g. R., & Rohrer, J. E. (2004). Validation of a single‐item measure of burnout against the Maslach
Burnout inventory among physicians. Stress and Health, 20(2), 75–79. https://doi.org/10.1002/smi.1002
samejima, F. (1980). Research on the multiple-choice test item in Japan: Toward the validation of mathematical models
(Technical Report No. 79-4). department of the navy, office of naval Research. https://apps.dtic.mil/sti/citations/tr/ada087127
schaufeli, W. B., & taris, t. W. (2005). the conceptualization and measurement of burnout: common ground and
worlds apart. Work & Stress, 19(3), 256–262. https://doi.org/10.1080/02678370500385913
Wilson, E. B. (1927). Probable inference, the law of succession, and statistical inference. Journal of the American
Statistical Association, 22(158), 209–212. https://doi.org/10.1080/01621459.1927.10502953
schaufeli, W. B., leiter, M. P., & Maslach, c. (2009). Burnout: 35 years of research and practice. Career Development
International, 14(3), 204–220. https://doi.org/10.1108/13620430910966406
schaufeli, W. B., Martínez, i. M., Pinto, a. M., salanova, M., & Bakker, a. B. (2002). Burnout and engagement in univer-
sity students: a cross-national study. Journal of Cross-Cultural Psychology, 33(5), 464–481. https://doi.org/10.1177/0022022102033005003
World health organization. (2019). Burn-out an “occupational phenomenon”: International classification of diseases.
https://www.who.int/news/item/28-05-2019-burn-out-an-occupational-phenomenon-international-classificati
on-of-diseases
Xu, W., hou, y., hung, y. s., & Zou, y. (2013). a comparative analysis of spearman’s rho and Kendall’s tau in normal
and contaminated normal models. Signal Processing, 93(1), 261–276. https://doi.org/10.1016/j.sigpro.2012.08.005"""

text4 = """Akram, M., Cerin, E., Lamb, K. E., & White, S. R. (2023). Modelling count,
bounded and skewed continuous outcomes in physical activity research:
Beyond linear regression models. International Journal of Behavioral
Nutrition and Physical Activity, 20(1), Article 57. https://doi.org/10.1186/
s12966-023-01460-y
Alviarez-Schulze, V., Cattaneo, G., Pacho´n-García, C., Solana-Sánchez, J.,
Tormos, J. M., Pascual-Leone, A., & Bartrés-Faz, D. (2022). Validation
and normative data of the Spanish version of the Rey Auditory Verbal
Learning Test and associated long-term forgetting measures in middle-
aged adults. Frontiers in Aging Neuroscience, 14, Article 809019. https://
doi.org/10.3389/fnagi.2022.809019
Arango-Lasprilla, J. C., Rivera, D., Ramos-Usuga, D., Vergara-Moragues, E.,
Montero-Lo´pez, E., Adana Díaz, L. A., Aguayo Arelis, A., García-
Guerrero, C. E., García de la Cadena, C., Llerena Espezúa, X., Lara, L.,
Padilla-Lo´pez, A., Rodriguez-Irizarry, W., Alcazar Tebar, C., Irías Escher,
M. J., Llibre Guerra, J. J., Torales Cabrera, N., Rodríguez-Agudelo, Y., &
Ferrer-Cascales, R. (2017). Trail Making Test: Normative data for the Latin
American Spanish-speaking pediatric population. NeuroRehabilitation,
41(3), 627–637. https://doi.org/10.3233/NRE-172247
Austin, P. C., & Steyerberg, E. W. (2015). The number of subjects per
variable required in linear regression analyses. Journal of Clinical
Epidemiology, 68(6), 627–636. https://doi.org/10.1016/j.jclinepi.2014
.12.014
Bonete-Lo´pez, B., Oltra-Cucarella, J., Marín, M., Anto´n, C., Balao, N.,
Lo´pez, E., & Macià, E. S. (2021). Validation and norms for a recognition
task for the Spanish version of the Free and Cued Selective Reminding
Test. Archives of Clinical Neuropsychology, 36(6), 954–964. https://
doi.org/10.1093/arclin/acaa117
Caldero´n-Rubio, E., Oltra-Cucarella, J., Bonete-Lo´pez, B., Iñesta, C., &
Sitges-Maciá, E. (2021). Regression-based normative data for independent
and cognitively active Spanish older adults: Free and Cued Selective
Reminding Test, Rey-Osterrieth Complex Figure Test and Judgement of
Line Orientation. International Journal of Environmental Research and
Public Health, 18(24), Article 12977. https://doi.org/10.3390/ijerph1824
12977
Campo, P., & Morales, M. (2004). Normative data and reliability for a Spanish
version of the verbal Selective Reminding Test. Archives of Clinical
Neuropsychology, 19(3), 421–435. https://doi.org/10.1016/S0887-6177(03)
00075-1
Campos-Magdaleno, M., Nieto-Vieites, A., Frades-Payo, B., Montenegro-
Peña, M., Facal, D., Lojo-Seoane, C., & Delgado-Losada, M. L. (2024).
Normative data for the Spanish versions of the CVLT, WMS-Logical
Memory, and RBMT from a sample of middle-aged and old participants.
Psychological Assessment, 36(2), 114–123. https://doi.org/10.1037/
pas0001292
Cohen, J. (1960). A coefficient of agreement for nominal scales. Educational
and Psychological Measurement, 20(1), 37–46. https://doi.org/10.1177/
001316446002000104
Crawford, J. R., & Garthwaite, P. H. (2007). Using regression equations built
from summary data in the neuropsychological assessment of the individual
case. Neuropsychology, 21(5), 611–620. https://doi.org/10.1037/0894-
4105.21.5.611
Crawford, J. R., & Garthwaite, P. H. (2012). Single-case research in neu-
ropsychology: A comparison of five forms of t-test for comparing a case to
controls. Cortex, 48(8), 1009–1016. https://doi.org/10.1016/j.cortex.2011
.06.021
Crawford, J. R., Garthwaite, P. H., Denham, A. K., & Chelune, G. J. (2012).
Using regression equations built from summary data in the psychological
assessment of the individual case: Extension to multiple regression.
Psychological Assessment, 24(4), 801–814. https://doi.org/10.1037/
a0027699
Crawford, J. R., Garthwaite, P. H., & Slick, D. J. (2009). On percentile norms
in neuropsychology: Proposed reporting standards and methods for
quantifying the uncertainty over the percentile ranks of test scores. The
Clinical Neuropsychologist, 23(7), 1173–1195. https://doi.org/10.1080/
13854040902795018
De Andrade Moral, R., Díaz-Orueta, U., & Oltra-Cucarella, J. (2022).
Logistic versus linear regression-based reliable change index: A simu-
lation study with implications for clinical studies with different sample
sizes. Psychological Assessment, 34(8), 731–741. https://doi.org/10.1037/
pas0001138
delCacho-Tena, A., Christ, B. R., Arango-Lasprilla, J. C., Perrin, P. B.,
Rivera, D., & Olabarrieta-Landa, L. (2024). Normative data estimation
in neuropsychological tests: A systematic review. Archives of Clinical
Neuropsychology, 39(3), 383–398. https://doi.org/10.1093/arclin/
acad084
Delgado-Losada, M. L., Lo´pez-Higes, R., Rubio-Valdehita, S., Facal, D.,
Lojo-Seoane, C., Montenegro-Peña, M., Frades-Payo, B., & Fernández-
Blázquez, M. A. (2021). Spanish consortium for ageing normative data
(SCAND): Screening tests (MMSE, GDS-15 and MFE). Psicothema,
33(1), 70–76. https://doi.org/10.7334/psicothema2020.304
Demétrio, C. G. B., Hinde, J., & Moral, R. A. (2014). Models for over-
dispersed data in entomology. In C. P. Ferreira & W. A. C. Godoy (Eds.),
Ecological modelling applied to entomology (pp. 219–259). Springer.
https://doi.org/10.1007/978-3-319-06877-0_9
Dubois, B., Feldman, H. H., Jacova, C., Hampel, H., Molinuevo, J. L.,
Blennow, K., DeKosky, S. T., Gauthier, S., Selkoe, D., Bateman, R.,
Cappa, S., Crutch, S., Engelborghs, S., Frisoni, G. B., Fox, N. C., Galasko,
D., Habert, M.-O., Jicha, G. A., Nordberg, A., … Cummings, J. L. (2014).
Advancing research diagnostic criteria for Alzheimer’s disease: The IWG-
2 criteria. The Lancet Neurology, 13(6), 614–629. https://doi.org/10.1016/
S1474-4422(14)70090-0
Duff, K., Hammers, D. B., Dalley, B. C. A., Suhrie, K. R., Atkinson, T. J.,
Rasmussen, K. M., Horn, K. P., Beardmore, B. E., Burrell, L. D., Foster,
N. L., & Hoffman, J. M. (2017). Short-term practice effects and amyloid
deposition: Providing information above and beyond baseline cognition.
The Journal of Prevention of Alzheimer’s Disease, 4(2), 87–92. https://
doi.org/10.14283/jpad.2017.9
Ehrenreich, J. H. (1995). Normative data for adults on a short form of the
Selective Reminding Test. Psychological Reports, 76(2), 387–390. https://
doi.org/10.2466/pr0.1995.76.2.387
Fleiss, J. L., Levin, B., & Paik, M. C. (2003). Statistical methods for rates
and proportions (3rd ed.). Wiley. https://doi.org/10.1002/0471445428
Folstein, M. F., Folstein, S. E., & McHugh, P. R. (1975). “Mini-mental
state”: A practical method for grading the cognitive state of patients for the
clinician. Journal of Psychiatric Research, 12(3), 189–198. https://
doi.org/10.1016/0022-3956(75)90026-6
Gamer, M., Lemon, J., Fellows, I., & Singh, P. (2019). irr: Various coef-
ficients of interrater reliability and agreement (Version 0.84.1) [Computer
software]. https://CRAN.R-project.org/package=irr
García-Herranz, S., Díaz-Mardomingo, M. D. C., Suárez-Falco´n, J. C.,
Rodríguez-Fernández, R., Peraita, H., & Venero, C. (2022). Normative
data for the Spanish version of the California Verbal Learning Test
(TAVEC) from older adults. Psychological Assessment, 34(1), 91–97.
https://doi.org/10.1037/pas0001070
Girtler, N., De Carli, F., Amore, M., Arnaldi, D., Bosia, L. E., Bruzzaniti, C.,
Cappa, S. F., Cocito, L., Colazzo, G., Ghio, L., Magi, E., Mancardi, G. L.,
Nobili, F., Pardini, M., Picco, A., Rissotto, R., Serrati, C., & Brugnolo, A.
(2015). A normative study of the Italian printed word version of the Free
and Cued Selective Reminding Test. Neurological Sciences, 36(7), 1127–
1134. https://doi.org/10.1007/s10072-015-2237-7
Grau-Guinea, L., Pérez Enríquez, C., García-Escobar, G., Arrondo Elizarán, C.,
Pereira Cutiño, B., Florido Santiago, M., Piqué Candini, J., Planas, A., Paez,
M., Peña Casanova, J., & Sánchez-Benavides, G. (2021). Development,
equivalence study, and normative data of version B of the Spanish-language
Free and Cued Selective Reminding Test. Neurologia, 36(5), 353–360.
https://doi.org/10.1016/j.nrleng.2018.02.001
Guàrdia-Olmos, J., Pero´-Cebollero, M., Rivera, D., & Arango-Lasprilla, J. C.
(2015). Methodology for the development of normative data for ten
Spanish-language neuropsychological tests in eleven Latin American
countries. NeuroRehabilitation, 37(4), 493–499. https://doi.org/10.3233/
NRE-151277
Harrington, K. D., Lim, Y. Y., Ames, D., Hassenstab, J., Rainey-Smith, S.,
Robertson, J., Salvado, O., Masters, C. L., Maruff, P., & the AIBL Research
Group. (2017). Using robust normative data to investigate the neuropsy-
chology of cognitive aging. Archives of Clinical Neuropsychology, 32(2),
142–154. https://doi.org/10.1093/arclin/acw106
Iñesta, C., Oltra-Cucarella, J., Bonete-Lo´pez, B., Caldero´n-Rubio, E., &
Sitges-Maciá, E. (2021). Regression-based normative data for inde-
pendent and cognitively active Spanish older adults: Digit Span, Letters
and Numbers, Trail Making Test and Symbol Digit Modalities Test.
International Journal of Environmental Research and Public Health,
18(19), Article 9958. https://doi.org/10.3390/ijerph18199958
Iñesta, C., Oltra-Cucarella, J., & Sitges-Maciá, E. (2022). Regression-based
normative data for independent and cognitively active Spanish older
adults: Verbal fluency tests and Boston Naming Test. International
Journal of Environmental Research and Public Health, 19(18), Article
11445. https://doi.org/10.3390/ijerph191811445
Ivnik, R. J., Malec, J. F., Smith, G. E., Tangalos, E. G., & Petersen, R. C.
(1996). Neuropsychological tests’ norms above age 55: COWAT, BNT,
MAE token, WRAT-R reading, AMNART, STROOP, TMT, and JLO.
The Clinical Neuropsychologist, 10(3), 262–278. https://doi.org/10.1080/
13854049608406689
Ivnik, R. J., Malec, J. F., Smith, G. E., Tangalos, E. G., Petersen, R. C.,
Kokmen, E., & Kurland, L. T. (1992a). Mayo’s older Americans
normative studies: Updated AVLT norms for ages 56 to 97. Clinical
Neuropsychologist, 6(Suppl. 1), 83–104. https://doi.org/10.1080/1385
4049208401880
Ivnik, R. J., Malec, J. F., Smith, G. E., Tangalos, E. G., Petersen, R. C.,
Kokmen, E., & Kurland, L. T. (1992b). Mayo’s older Americans
normative studies: WAIS-R norms for ages 56 to 97. Clinical Neuro-
psychologist, 6(Suppl. 1), 1–30. https://doi.org/10.1080/13854049208
401877
Ivnik, R. J., Smith, G. E., Lucas, J. A., Tangalos, E. G., Kokmen, E., &
Petersen, R. C. (1997). Free and Cued Selective Reminding Test: MOANS
norms. Journal of Clinical and Experimental Neuropsychology, 19(5),
676–691. https://doi.org/10.1080/01688639708403753
Karstens, A. J., Christianson, T. J., Lundt, E. S., Machulda, M. M., Mielke,
M. M., Fields, J. A., Kremers, W. K., Graff-Radford, J., Vemuri, P., Jack,
C. R., Jr., Knopman, D. S., Petersen, R. C., & Stricker, N. H. (2024). Mayo
normative studies: Regression-based normative data for ages 30–91 years
with a focus on the Boston Naming Test, Trail Making Test and Category
Fluency. Journal of the International Neuropsychological Society, 30(4),
389–401. https://doi.org/10.1017/S1355617723000760
Kéry, M., & Hatfield, J. S. (2003). Normality of raw data in general linear
models: The most widespread myth in statistics. Bulletin of the Ecological
Society of America, 84(2), 92–94. https://doi.org/10.1890/0012-9623(2003)
84[92:NORDIG]2.0.CO;2
Kiselica, A. M., Kaser, A. N., Webber, T. A., Small, B. J., & Benge, J. F.
(2020). Development and preliminary validation of standardized regression-
based change scores as measures of transitional cognitive decline. Archives
of Clinical Neuropsychology, 35(7), 1168–1181. https://doi.org/10.1093/
arclin/acaa042
Klein, N. (2024). Distributional regression for data analysis. Annual Review
of Statistics and Its Application, 11(1), 321–346. https://doi.org/10.1146/
annurev-statistics-040722-053607
Koo, T. K., & Li, M. Y. (2016). A guideline of selecting and reporting
intraclass correlation coefficients for reliability research. Journal of
Chiropractic Medicine, 15(2), 155–163. https://doi.org/10.1016/j.jcm
.2016.02.012
Larrabee, G. J., Trahan, D. E., & Levin, H. S. (2000). Normative data for a
six-trial administration of the Verbal Selective Reminding Test. The
Clinical Neuropsychologist, 14(1), 110–118. https://doi.org/10.1076/
1385-4046(200002)14:1;1-8;FT110
Lucas, J. A., Ivnik, R. J., Smith, G. E., Ferman, T. J., Willis, F. B., Petersen,
R. C., & Graff-Radford, N. R. (2005). Mayo’s older African Americans
normative studies: Norms for Boston Naming Test, Controlled Oral Word
Association, Category Fluency, Animal Naming, Token Test, WRAT-3
Reading, Trail Making Test, Stroop Test, and Judgment of Line Orientation.
The Clinical Neuropsychologist, 19(2), 243–269. https://doi.org/10.1080/
13854040590945337
McCullagh, P., & Nelder, J. A. (1989). Generalized linear models. Chapman
& Hall.
McKhann, G. M., Knopman, D. S., Chertkow, H., Hyman, B. T., Jack, C. R.,
Jr., Kawas, C. H., Klunk, W. E., Koroshetz, W. J., Manly, J. J., Mayeux, R.,
Mohs, R. C., Morris, J. C., Rossor, M. N., Scheltens, P., Carrillo, M. C.,
Thies, B., Weintraub, S., & Phelps, C. H. (2011). The diagnosis of dementia
due to Alzheimer’s disease: Recommendations from the National Institute
on Aging-Alzheimer’s Association workgroups on diagnostic guidelines for
Alzheimer’s disease. Alzheimer’s & Dementia, 7(3), 263–269. https://
doi.org/10.1016/j.jalz.2011.03.005
Morlett Paredes, A., Tarraf, W., Gonzalez, K., Stickel, A. M., Graves,
L. V., Salmon, D. P., Kaur, S. S., Gallo, L. C., Isasi, C. R., Lipton, R. B.,
Lamar, M., Goodman, Z. T., & González, H. M. (2024). Normative data
for the Digit Symbol Substitution for diverse Hispanic/Latino adults:
Results from the Study of Latinos-Investigation of Neurocognitive
Aging (SOL-INCA). Alzheimer’s & Dementia: Diagnosis, Assessment
& Disease Monitoring, 16(2), Article e12573. https://doi.org/10.1002/
dad2.12573
Mungas, D., Marshall, S. C., Weldon, M., Haan, M., & Reed, B. R. (1996).
Age and education correction of Mini-Mental State Examination for
English and Spanish-speaking elderly. Neurology, 46(3), 700–706. https://
doi.org/10.1212/WNL.46.3.700
Oltra-Cucarella, J. (2025). Research files. Universidad Miguel Hernández
de Elche. https://sabiex.umh.es/lineas-de-investigacion/neuropsicologia-y-
envejecimiento-files/
Oltra-Cucarella, J., Sánchez-SanSegundo, M., Ferrer-Cascales, R., & the
Alzheimer Disease Neuroimaging Initiative. (2022). Predicting Alzheimer’s
disease with practice effects, APOE genotype and brain metabolism.
Neurobiology of Aging, 112, 111–121. https://doi.org/10.1016/j.neurobio
laging.2021.12.011
Pek, J., Wong, O., & Wong, C. M. (2017). Data transformations for inference
with linear regression: Clarifications and recommendations. Practical
Assessment, Research, and Evaluation, 22(1), Article 9. https://doi.org/10
.7275/2w3n-0f07
Peña-Casanova, J., Blesa, R., Aguilar, M., Gramunt-Fombuena, N., Go´mez-
Anso´n, B., Oliva, R., Molinuevo, J. L., Robles, A., Barquero, M. S.,
Antúnez, C., Martínez-Parra, C., Frank-García, A., Fernández, M., Alfonso,
V., Sol, J. M., & the NEURONORMA Study Team. (2009). Spanish
multicenter normative studies (NEURONORMA project): Methods and
sample characteristics. Archives of Clinical Neuropsychology, 24(4), 307–
319. https://doi.org/10.1093/arclin/acp027
Peña-Casanova, J., Gramunt-Fombuena, N., Quiñones-Ubeda, S., Sánchez-
Benavides, G., Aguilar, M., Badenes, D., Molinuevo, J. L., Robles, A.,
Barquero, M. S., Payno, M., Antúnez, C., Martínez-Parra, C., Frank-
García, A., Fernández, M., Alfonso, V., Sol, J. M., Blesa, R., & the
NEURONORMA Study Team. (2009). Spanish multicenter normative
studies (NEURONORMA project): Norms for the Rey-Osterrieth com-
plex figure (copy and memory), and Free and Cued Selective Reminding
Test. Archives of Clinical Neuropsychology, 24(4), 371–393. https://
doi.org/10.1093/arclin/acp041
Peña-Casanova, J., Quiñones-Ubeda, S., Gramunt-Fombuena, N., Aguilar, M.,
Casas, L., Molinuevo, J. L., Robles, A., Rodríguez, D., Barquero, M. S.,
Antúnez, C., Martínez-Parra, C., Frank-García, A., Fernández, M., Molano,
A., Alfonso, V., Sol, J. M., Blesa, R., & the NEURONORMA Study Team.
(2009). Spanish multicenter normative studies (NEURONORMA project):
Norms for Boston Naming Test and Token Test. Archives of Clinical
Neuropsychology, 24(4), 343–354. https://doi.org/10.1093/arclin/acp039
Petersen, R. C. (2004). Mild cognitive impairment as a diagnostic entity.
Journal of Internal Medicine, 256(3), 183–194. https://doi.org/10.1111/j.1365-2796.2004.01388.x
R Core Team. (2024). R: A language and environment for statistical com-
puting. R Foundation for Statistical Computing. https://www.R-project.org/
Rivera, D., & Arango-Lasprilla, J. C. (2017). Methodology for the devel-
opment of normative data for Spanish-speaking pediatric populations.
NeuroRehabilitation, 41(3), 581–592. https://doi.org/10.3233/NRE-
172275
Schmidt, A. F., & Finan, C. (2018). Linear regression and the normality
assumption. Journal of Clinical Epidemiology, 98, 146–151. https://doi.org/
10.1016/j.jclinepi.2017.12.006
Shirk, S. D., Mitchell, M. B., Shaughnessy, L. W., Sherman, J. C.,
Locascio, J. J., Weintraub, S., & Atri, A. (2011). A web-based nor-
mative calculator for the uniform data set (UDS) neuropsychological
test battery. Alzheimer’s Research & Therapy, 3(6), Article 32. https://
doi.org/10.1186/alzrt94
Steinberg, B. A., Bieliauskas, L. A., Smith, G. E., Langellotti, C., & Ivnik,
R. J. (2005). Mayo’s older Americans normative studies: Age- and IQ-
adjusted norms for the Boston Naming Test, the MAE Token Test, and the
Judgment of Line Orientation Test. The Clinical Neuropsychologist,
19(3–4), 280–328. https://doi.org/10.1080/13854040590945229
Strauss, E., Sherman, E. M. S., Spreen, O., & Spreen, O. (2006). A com-
pendium of neuropsychological tests: Administration, norms, and com-
mentary (3rd ed.). Oxford University Press.
Stricker, N. H., Christianson, T. J., Lundt, E. S., Alden, E. C., Machulda,
M. M., Fields, J. A., Kremers, W. K., Jack, C. R., Jr., Knopman, D. S.,
Mielke, M. M., & Petersen, R. C. (2021). Mayo normative studies:
Regression-based normative data for the Auditory Verbal Learning Test
for ages 30–91 years and the importance of adjusting for sex. Journal of
the International Neuropsychological Society, 27(3), 211–226. https://
doi.org/10.1017/S1355617720000752
Tabachnick, B. G., & Fidell, L. S. (2013). Using multivariate statistics
(6th ed.). Pearson.
Uttl, B. (2005). Measurement of individual differences: Lessons from memory
assessment in research and clinical practice. Psychological Science, 16(6),
460–467. https://doi.org/10.1111/j.0956-7976.2005.01557.x
Weisberg, S. (2014). Applied linear regression (4th ed.). Wiley.
Williams, M. N., Go´mez Grajales, C. A., & Kurkiewicz, D. (2013).
Assumptions of multiple regression: Correcting two misconceptions.
Practical Assessment, Research, and Evaluation, 18(1), Article 11.
https://doi.org/10.7275/55hn-wk47
Williamson, M., Maruff, P., Schembri, A., Cummins, H., Bird, L., Rosenich,
E., & Lim, Y. Y. (2022). Validation of a Digit Symbol Substitution Test
for use in supervised and unsupervised assessment in mild Alzheimer’s
disease. Journal of Clinical and Experimental Neuropsychology, 44(10),
768–779. https://doi.org/10.1080/13803395.2023.2179977
Winblad, B., Palmer, K., Kivipelto, M., Jelic, V., Fratiglioni, L., Wahlund,
L.-O., Nordberg, A., Bäckman, L., Albert, M., Almkvist, O., Arai, H.,
Basun, H., Blennow, K., de Leon, M., DeCarli, C., Erkinjuntti, T.,
Giacobini, E., Graff, C., Hardy, J., … Petersen, R. C. (2004). Mild
cognitive impairment—Beyond controversies, towards a consensus:
Report of the International Working Group on Mild Cognitive Impairment.
Journal of Internal Medicine, 256(3), 240–246. https://doi.org/10.1111/j.1365-2796.2004.01380.x"""


#finals, links = replace_citations_with_indices(test, text)

#print(finals)
#print(links)

def print_each(in_text):
    for i in range(len(in_text)):
        if in_text[i]:
            print(str(i) + ": " + in_text[i])
        else:
            print(str(i) + ": NONE")

print(text3)
x = 0
for i in convert_to_ref_list(text3):
     x += 1
     print(str(x) + ":  " + i)

print(x)
