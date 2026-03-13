import re


def replace_citations_with_indices(paragraph, references):
    final_paragraph = convert_to_flow(paragraph).lower()

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

        m_author = re.match(r'\s*([a-zA-Z\-]+)\s*,', ref)
        m_year = re.search(r'\((\d{4}[a-z]?)\)', ref)

        if m_author and m_year:
            surname = m_author.group(1).lower()
            year = m_year.group(1)

            index[(surname, year)] = ref

    return index


def parse_citation(citation):

    c = citation.lower()

    author = re.match(r'([a-z\-]+)', c)
    year = re.search(r'(\d{4}[a-z]?)', c)

    if author and year:
        return author.group(1), year.group(1)

    return None


def match_citations(citations, ref_index):
    results = {}

    for citation in citations:
        print(citation.lower())
        key = parse_citation(citation)

        if not key:
            results[citation] = None
            continue

        name, year = key
        match = None

        for ref, item in ref_index.items():
            print(name)
            print(item)
            print("---")
            item_l = item.lower()
            if item_l.startswith(name) and f"({year})" in item_l:
                match = item
                break

        results[citation] = match

    return results



def convert_to_flow(paragraph):
    return paragraph.replace('-\n', '').replace('\n', ' ')


def convert_to_ref_list(citations):
    pattern = r'(?=^([a-zA-Z -]{3,}, [a-zA-Z]{1}\.+))'
    splits = re.split(pattern, citations, flags=re.MULTILINE)
    refs = []
    for i in range(2, len(splits), 2):
        refs.append(replacer(splits[i]))
    return refs


def replacer(citation):
    cit = citation.replace('-\n', '-')
    cit = cit.replace('\n.', '.')
    cit = cit.replace('/\n', '/')
    cit = cit.replace(')\n', ')')
    cit = re.sub(r'(\d)\n(\d)', r'\1\2', cit)
    cit = re.sub(r'(/[a-zA-Z0-9]*)\n([a-zA-Z0-9]*/)', r'\1\2', cit)
    cit = cit.replace('\n', ' ')
    return cit.strip()

#text = """abid, g., contreras, F., ahmed, s., & Qazi, t. (2019). contextual factors and organizational commitment: examining
#the mediating role of thriving at work. Sustainability, 11(17), 4686. https://doi.org/10.3390/su11174686
#abid, g., sajjad, I., elahi, n. s., Farooqi, s., & nisar, a. (2018). the influence of prosocial motivation and civility on work
#engagement: the mediating role of thriving at work. Cogent Business & Management, 5(1), 1493712. https://doi.org/10.1080/23311975.2018.1493712
#abid, g., ahmed, a., & Butt, t. h. (2022a). tri-dimensional thriving scale (tts): Measurement and construct validation.
#International Journal of Business Excellence, 28(2), 139–156. https://doi.org/10.1504/IJBeX.2020.10035475
#abid, g., ahmed, a., Qazi, t. F., ahmed, s., & Islam, t. (2022b). relationships between curiosity, thriving, and incivility:
#Implications for constructive voice behaviour. International Journal of Business Excellence, 27(4), 479–501. scopus -
#Q2- X https://doi.org/10.1504/IJBeX.2022.125106
#abid, g., & contreras, F. (2022). Mapping thriving at work as a growing concept: review and directions for future
#studies. Information, 13(8), 383. scopus - Q2 – X https://doi.org/10.3390/info13080383
#adair erickson, r., & roloff, M. e. (2008). reducing attrition after downsizing: analyzing the effects of organizational
#support, supervisor support, and gender on organizational commitment. International Journal of Organizational
#Analysis, 15(1), 35–55. https://doi.org/10.1108/19348830710860147
#agarwala, t., arizkuren-eleta, a., del castillo, e., Muñiz-Ferrer, M., & gartzia, l. (2014). Influence of managerial support
#on work–life conflict and organizational commitment: an international comparison for India, Peru and spain. The International Journal of Human Resource Management, 25(10), 1460–1483. https://doi.org/10.1080/09585192.2013.870315
#ahlf, h., horak, s., klein, a., & yoon, s. W. (2019). demographic homophily, communication and trust in
#intra-organizational business relationships. Journal of Business & Industrial Marketing, 34(2), 474–487. https://doi.org/10.1108/jbim-03-2018-0093
#alfes, k., truss, c., soane, e. c., rees, c., & gatenby, M. (2013). the relationship between line manager behavior, per-
#ceived hrM practices, and individual performance: examining the mediating role of engagement. Human Resource
#Management, 52(6), 839–859. https://doi.org/10.1002/hrm.21512
#anderson, s. e., coffey, B. s., & Byerly, r. t. (2002). Formal organizational initiatives and informal workplace practices:
#links to work-family conflict and job-related outcomes. Journal of Management, 28(6), 787–810. https://doi.org/10.1177/014920630202800605
#arrow, h., Mcgrath, J. e., & Berdahl, J. l. (2000). Small groups as complex systems: Formation, coordination, development,
#and adaptation. sage Publications.
#arshad, M., abid, g., & khan, M. M. (2020). Impact of employee’s environmental concern on ecological green behav-
#ior: Mediation mechanism of employee customer oriented ocB and organizational commitment. International
#Journal of Innovation, Creativity and Change, 14(12), 614–633.
#arshad, M., abid, g., contreras, F., elahi, n. s., & athar, M. a. (2021). Impact of prosocial motivation on organiza-
#tional citizenship behavior and organizational commitment: the mediating role of managerial support. European
#Journal of Investigation in Health, Psychology and Education, 11(2), 436–449. https://doi.org/10.3390/ejihpe11020032
#Blau, P. M. (1964a). social exchange theory. 3(2007), 62.
#Blau, P. M. (1964b). Exchange and power in social life. John Wiley and sons.
#Bliese, P. d. (2000). Within-group agreement, non-independence, and reliability: Implications for data aggregation and
#analysis. In k. J. klein & s. W. J. kozlowski (eds.), Multi-level theory, research, and methods in organizations:
#Foundations, extensions, and new directions (349–381). Jossey-Bass.
#Boudreau, J. W., Jesuthasan, r., & creelman, d. (2015). Lead the work: Navigating a world beyond employment. John
#Wiley & sons.
#cai, z., huo, y., lan, J., chen, z., & lam, W. (2019). When do frontline hospitality employees take charge? Prosocial
#motivation, taking charge, and job performance: the moderating role of job autonomy. Cornell Hospitality Quarterly,
#60(3), 237–248. https://doi.org/10.1177/1938965518797081
#campbell, d. t., & Fiske, d. W. (1959). convergent and discriminant validation by the multitrait-multimethod matrix.
#Psychological Bulletin, 56(2), 81–105. https://doi.org/10.1037/h0046016
#carmeli, a., & spreitzer, g. M. (2009). trust, connectivity, and thriving: Implications for innovative behaviors at work.
#The Journal of Creative Behavior, 43(3), 169–191. https://doi.org/10.1002/j.2162-6057.2009.tb01313.x
#eisenberger, r., karagonlar, g., stinglhamber, F., neves, P., Becker, t. e., gonzalez-Morales, M. g., & steiger-Mueller, M.
#(2010). leader–member exchange and affective organizational commitment: the contribution of supervisor’s orga-
#nizational embodiment. The Journal of Applied Psychology, 95(6), 1085–1103. https://doi.org/10.1037/a0020858
#eisenberger, r., rhoades shanock, l., & Wen, X. (2020). Perceived organizational support: Why caring about employees counts. Annual Review of Organizational Psychology and Organizational Behavior, 7(1), 101–124. https://doi.org/10.1146/annurev-orgpsych-012119-044917
#emerson, r. M. (1976). social exchange theory. Annual Review of Sociology, 2, 335–362. https://doi.org/10.1146/annurev.so.02.080176.002003
#Firth, r. (1967). Themes in economic anthropology. tavistock.
#george, J. M., & Bettenhausen, k. (1990). understanding prosocial behavior, sales performance, and turnover: a group-level
#analysis in a service context. Journal of Applied Psychology, 75(6), 698–709. https://doi.org/10.1037/0021-9010.75.6.698
#grant, a. M. (2007). relational job design and the motivation to make a prosocial difference. Academy of Management
#Review, 32, 393–417. https://doi.org/10.5465/amr.2007.24351328
#grant, a. M., & Mayer, d. M. (2009). good soldiers and good actors: Prosocial and impression management motives
#as interactive predictors of affiliative citizenship behaviors. The Journal of Applied Psychology, 94(4), 900–912.
#https://doi.org/10.1037/a0013770
#grant, a. M., & sumanth, J. J. (2009). Mission possible? the performance of prosocially motivated employees de-
#pends on manager trustworthiness. The Journal of Applied Psychology, 94(4), 927–944. https://doi.org/10.1037/a0014391
#gallup, P. B. (2016). The 2013 Gallup-Hope Index.
#hair, J. F., celsi, M., ortinau, d. J., & Bush, r. P. (2010). Essentials of marketing research. (Vol. 2). Mcgraw-hill/Irwin.
#James, d. l., demaree, r. g., & Wolf, g. (1984). estimating within-group interrater reliability with and without re-
#sponse bias. Journal of Applied Psychology, 69(1), 85–98. https://doi.org/10.1037/0021-9010.69.1.85
#kelloway, e. k., & day, a. l. (2005). Building healthy workplaces: What we know so far. Canadian Journal of Behavioural
#Science / Revue Canadienne Des Sciences du Comportement, 37(4), 223–235. https://doi.org/10.1037/h0087259
#khan, s. u. k. (2005). Macro determinants of total Factor Productivity in Pakistan. Published in. SBP Research Bulletin,
#2(2), 383–401.
#khan, n. a., khan, a. n., soomro, M. a., & khan, s. k. (2020). transformational leadership and civic virtue behavior:
#Valuing act of thriving and emotional exhaustion in the hotel industry. Asia Pacific Management Review, 25(4),
#216–225. https://doi.org/10.1016/j.apmrv.2020.05.001
#klein, h. J., Molloy, J. c., & Brinsfield, c. t. (2012). reconceptualizing workplace commitment to redress a stretched
#construct: revisiting assumptions and removing confounds. Academy of Management Review, 37(1), 130–151.
#https://doi.org/10.5465/arma.2010.0018
#kleine, a. k., rudolph, c. W., & zacher, h. (2019). thriving at work: a meta‐analysis. Journal of Organizational Behavior,
#40(9-10), 973–999. https://doi.org/10.1002/job.2375
#kozlowski, s. W. J., & klein, k. J. (2000). a multi-level approach to theory and research in organizations: contextual,
#temporal, and emergent processes. In k. J. klein & s. W. J. kozlowski (eds.), Multi-level theory, research, and methods
#in organizations: Foundations, extensions, and new directions. (pp. 3–90). Jossey-Bass.
#lawler, e. J. (2001). an affect theory of social exchange. American Journal of Sociology, 107(2), 321–352. https://doi.org/10.1086/324071
#leBreton, J. M., & senter, J. l. (2008). answers to 20 questions about interrater reliability and interrater agreement.
#Organizational Research Methods, 11(4), 815–852. https://doi.org/10.1177/1094428106296642
#li, J. (2015). the mediating roles of job crafting and thriving in the lMX-employee outcomes relationship. Japanese
#Journal of Administrative Science, 28(1), 39–51. https://doi.org/10.5651/jaas.28.39
#liao, h., liu, d., & loi, r. (2010). looking at both sides of the social exchange coin: a social cognitive perspective on
#the joint effects of relationship quality and differentiation on creativity. Academy of Management Journal, 53(5),
#1090–1109. https://doi.org/10.5465/amj.2010.54533207
#Mowday, r. t., steers, r. M., & Porter, l. W. (1979). the measurement of organizational commitment. Journal of
#Vocational Behavior, 14(2), 224–247. https://doi.org/10.1016/0001-8791(79)90072-1
#nawaz, M., abid, g., & Quartey-Papafio, t. k. (2022). relation of workplace incivility, prosocial motivation and emo-
#tional exhaustion to thriving of nurses. Nursing: Research and Reviews, ume 12, 207–222. https://doi.org/10.2147/nrr.s373694
#niessen, c., sonnentag, s., & sach, F. (2012). thriving at work-a diary study. Journal of Organizational Behavior, 33(4),
#468–487. https://doi.org/10.1002/job.763
#noranee, s., amir Ishak, n., raja Mustapha, r. M., & Mohamad Besir, M. s. (2016). employee Prosocial Motivation and
#Interpersonal citizenship Behavior: the supervisor rating of leader-Member exchange Quality as a Mediator. In
#Proceedings of the 1st AAGBS International Conference on Business Management 2014 (AiCoBM 2014). (pp. 221–233).
#springer singapore.
#ong, J. F. B., tan, J. M. t., Villareal, r. F. c., & chiu, J. l. (2019). Impact of quality work life and prosocial motivation
#on the organizational commitment and turnover intent of public health practitioners. Review of Integrative Business
#and Economics Research, 8, 24–43.
#Paterson, t. a., luthans, F., & Jeung, W. (2014). thriving at work: Impact of psychological capital and supervisor sup-
#port. Journal of Organizational Behavior, 35(3), 434–446. https://doi.org/10.1002/job.1907
#Podsakoff, P. M., Mackenzie, s. B., lee, J. y., & Podsakoff, n. P. (2003). common method biases in behavioral research:
#a critical review of the literature and recommended remedies. The Journal of Applied Psychology, 88(5), 879–903.
#https://doi.org/10.1037/0021-9010.88.5.879
#Porath, c., spreitzer, g., gibson, c., & garnett, F. g. (2012). thriving at work: toward its measurement, construct val-
#idation, and theoretical refinement. Journal of Organizational Behavior, 33(2), 250–275. https://doi.org/10.1002/job.756
#Prem, r., ohly, s., kubicek, B., & korunka, c. (2017). thriving on challenge stressors? exploring time pressure and
#learning demands as antecedents of thriving at work. Journal of Organizational Behavior, 38(1), 108–123. https://doi.org/10.1002/job.2115
#rioux, s. M., & Penner, l. a. (2001). the causes of organizational citizenship behavior: a motivational analysis. The
#Journal of Applied Psychology, 86(6), 1306–1314. https://doi.org/10.1037/0021-9010.86.6.1306
#saleem, M., abid, g., & Butt, t. h. (2025). Mediating mechanism of thriving at work between family motivation, abu-
#sive supervision and organizational commitment. European J. of International Management, 26(1), 140–159. https://doi.org/10.1504/eJIM.2025.145410
#settoon, r. P., Bennett, n., & liden, r. c. (1996). social exchange in organizations: Perceived organizational support,
#leader–member exchange, and employee reciprocity. Journal of Applied Psychology, 81(3), 219–227. https://doi.org/10.1037/0021-9010.81.3.219
#siemsen, e., roth, a., & oliveira, P. (2010). common method bias in regression models with linear, quadratic, and
#interaction effects. Organizational Research Methods, 13(3), 456–476. https://doi.org/10.1177/1094428109351241
#shao, B., cardona, P., ng, I., & trau, r. n. (2017). are prosocially motivated employees more committed to their orga-
#nization? the roles of supervisors’ prosocial motivation and perceived corporate social responsibility. Asia Pacific
#Journal of Management, 34(4), 951–974. https://doi.org/10.1007/s10490-017-9512-5
#sonenshein, s., dutton, J. e., grant, a. M., spreitzer, g. M., & sutcliffe, k. M. (2013). growing at work: employees’ in-
#terpretations of progressive -change in organizations. Organization Science, 24(2), 552–570. https://doi.org/10.1287/orsc.1120.0749
#spreitzer, g., & Porath, c. (2012). creating sustainable performance. Harvard Business Review, 90(1), 92–99, 152.
#spreitzer, g. M., & Porath, c. (2014). 15 -determination as for thriving: Building an Integrative Model of human
#growth at Work. The Oxford Handbook of Work Engagement, Motivation, and Self-Determination Theory, 245.
#spreitzer, g. M., & sutcliffe, k. M. (2007). thriving in organizations. Positive Organizational Behavior, 33, 74–85.
#spreitzer, g. M., sutcliffe, k., dutton, J., sonenshein, s., & grant, a. M. (2005). a socially embedded model of thriving
#at work. Organization Science, 16(5), 537–549. https://doi.org/10.1287/orsc.1050.0153
#thakur, M., Bansal, a., stokes, P (2016). the role of thriving and training in merger success: an integrative learning
#perspective. In c. l. cooper 998 kleIne., et al. & s. Finkelstein (eds.), Advances in Mergers and Acquisitions. (pp.
#1–35). emerald.
#tse, h. h., & dasborough, M. t. (2008). a study of exchange and emotions in team member relationships. Group &
#Organization Management, 33(2), 194–215. https://doi.org/10.1177/1059601106293779
#ullah, I., elahi, n. s., abid, g., & Butt, M. u. (2020). the impact of perceived organizational support and proactive
#personality on affective commitment: Mediating role of prosocial motivation. Business, Management and Economics
#Engineering, 18(2), 183–205. https://doi.org/10.3846/bme.2020.12189
#utz, s., Muscanell, n., & göritz, a. s. (2014). give, match, or take: a new personality construct predicts resource and
#information sharing. Personality and Individual Differences, 70, 11–16. https://doi.org/10.1016/j.paid.2014.06.011
#Van der Voet, J., steijn, B., & kuipers, B. s. (2017). What’s in it for others? the relationship between prosocial motiva-
#tion and commitment to change among youth care professionals. Public Management Review, 19(4), 443–462.
#https://doi.org/10.1080/14719037.2016.1183699
#Vivek, s. a., & raveeendran, d. (2017). thriving at workplace by bank managers: an empirical study of public and
#private sector banks. International Journal of Entrepreneurship and Development Studies, 5(1), 1–11.
#Wallace, J. c., Butts, M. M., Johnson, P. d., stevens, F. g., & smith, M. B. (2016). a multi-level model of employee
#innovation: understanding the effects of regulatory focus, thriving, and employee involvement climate. Journal of
#Management, 42(4), 982–1004. https://doi.org/10.1177/0149206313506462
#Walumbwa, F. o., avolio, B. J., gardner, W. l., Wernsing, t. s., & Peterson, s. J. (2008). authentic leadership:
#development and validation of a theory-based measure. Journal of Management, 34(1), 89–126. https://doi.org/10.1177/0149206307308913
#Walumbwa, F. o., hartnell, c. a., & Misati, e. (2017). does ethical leadership enhance group learning behavior?
#examining the mediating influence of group ethical conduct, justice climate, and peer justice. Journal of Business
#Research, 72, 14–23. https://doi.org/10.1016/j.jbusres.2016.11.013
#Walumbwa, F. o., hartnell, c. a., & oke, a. (2010). servant leadership, procedural justice climate, service climate,
#employee attitudes, and organizational citizenship behavior: a cross-level investigation. The Journal of Applied
#Psychology, 95(3), 517–529. https://doi.org/10.1037/a0018867
#Walumbwa, F. o., Muchiri, M. k., Misati, e., Wu, c., & Meiliani, M. (2016). Fired up to perform: a multi-level examina-
#tion of antecedents and consequences of thriving at work. In Academy of Management Proceedings. (Vol. 2016, no.
#1, p. 10494). 10510: academy of Management. https://doi.org/10.5465/ambpp.2016.79
#Walumbwa, F. o., Muchiri, M. k., Misati, e., Wu, c., & Meiliani, M. (2018). Inspired to perform: a multi-level investiga-
#tion of antecedents and consequences of thriving at work. Journal of Organizational Behavior, 39(3), 249–261.
#https://doi.org/10.1002/job.2216"""
#
#text2 = """cakirpaloglu, P., Šmahaj, J., cakirpaloglu, s., & Zielina, M. (2016). Workplace bullying in the Czech Republic: Theory,
#research, and practice. Palacký University olomouc. (original work published in czech).
#chytilová, e., yorgová, y., & Kušnirová, R. (2025). impact of HRM digitalisation on companies’ performance.
#Entrepreneurship and Sustainability Issues, 13(1), 259–273. https://doi.org/10.9770/t2484277887
#coyne, i., Farley, s., axtell, c., sprigg, c., Best, l., & Kwok, o. (2017). Understanding the relationship between experienc-
#ing workplace cyberbullying, employee mental strain and job satisfaction: a dysempowerment approach. The
#International Journal of Human Resource Management, 28(7), 945–972. https://doi.org/10.1080/09585192.2015.1116454
#Demerouti, e., Bakker, a. B., Nachreiner, F., & schaufeli, W. B. (2001). the Job Demands–Resources model of burnout.
#Journal of Applied Psychology, 86(3), 499–512. https://doi.org/10.1037/0021-9010.86.3.499
#einarsen, s., Hoel, H., & Notelaers, g. (2009). Measuring exposure to bullying and harassment at work: Validity, factor
#structure and psychometric properties of the Negative acts Questionnaire–Revised. Work & Stress, 23(1), 24–44.
#https://doi.org/10.1080/02678370902815673
#einarsen, s., Hoel, H., Zapf, D., & cooper, c. l. (2011). Bullying and harassment in the workplace: Developments in
#theory, research, and practice. cRc Press.
#einarsen, s. V., Hoel, H., Zapf, D., & cooper, c. l. (eds.) (2020). Bullying and harassment in the workplace: Theory,
#research and practice (3rd ed.). cRc Press.
#einarsen, s. V., skogstad, a., & Nielsen, M. B. (2020). the measurement of workplace bullying: Key issues and recom-
#mendations. Frontiers in Psychology, 11, 583510. https://doi.org/10.3389/fpsyg.2020.583510
#Hassard, J., teoh, K. R., Visockaite, g., Dewe, P., & cox, t. (2018). the cost of work-related stress to society: a system-
#atic review. Journal of Occupational Health Psychology, 23(1), 1–17. https://doi.org/10.1037/ocp0000069
#Hogh, a., Hoel, H., & carneiro, i. g. (2011). Bullying and employee turnover among healthcare workers: a three-wave
#prospective study. Journal of Nursing Management, 19(6), 742–751. https://doi.org/10.1111/j.1365-2834.2011.01264.x
#Khan, M. s., elahi, N. s., & abid, g. (2021). Workplace incivility and job satisfaction: Mediation of subjective well-being
#and moderation of forgiveness climate in the health care sector. European Journal of Investigation in Health,
#Psychology and Education, 11(4), 1107–1119. https://doi.org/10.3390/ejihpe11040082
#Kline, R., & lewis, D. (2019). the price of fear: estimating the financial cost of bullying and harassment to the NHs
#in england. Public Money & Management, 39(3), 166–174. https://doi.org/10.1080/09540962.2018.1535044
#lever, i., Dyball, D., greenberg, N., & stevelink, s. a. M. (2019). Health consequences of bullying in the healthcare
#workplace: a systematic review. Journal of Advanced Nursing, 75(12), 3195–3209. https://doi.org/10.1111/jan.13986
#løvvik, c., Øverland, s., Nielsen, M. B., Jacobsen, H. B., & Reme, s. e. (2022). associations between workplace bullying
#and later benefit recipiency among workers with common mental disorders. International Archives of Occupational
#and Environmental Health, 95(4), 791–798. https://doi.org/10.1007/s00420-021-01764-1
#Machul, M., Krasucka, K. N., Pelc, D., & Dziurka, M. (2024). impact of workplace bullying on nursing care quality: a
#comprehensive review. Medical Science Monitor: International Medical Journal of Experimental and Clinical Research,
#30, e944815. https://doi.org/10.12659/MsM.944815
#Mikšík, o. (2004). Dotazník sUPso – postihování a hodnocení struktury a dynamiky subjektivních prožitků a stavů –
#příručka [sUPso Questionnaire – assessment and evaluation of the structure and dynamics of subjective experi-
#ences and states: Manual]. Psychodiagnostika, s. r. o.
#Nielsen, M. B., & einarsen, s. V. (2018). What we know, what we do not know, and what we should and could have
#known about workplace bullying: an overview of the literature and agenda for future research. Aggression and
#Violent Behavior, 42, 71–83. https://doi.org/10.1016/j.avb.2018.06.007
#Nielsen, M. B., Matthiesen, s. B., & einarsen, s. (2010). the impact of methodological moderators on prevalence rates
#of workplace bullying: a meta-analysis. Journal of Occupational and Organizational Psychology, 83(4), 955–979.
#https://doi.org/10.1348/096317909x481256
#Piri, s., Jalali, R., & Khatony, a. (2024). consequences of workplace bullying from nurses’ perspectives: a qualitative
#descriptive study in iran. Nursing Open, 11(10), e70060. https://doi.org/10.1002/nop2.70060
#Porath, c. l., & Pearson, c. M. (2013). the price of incivility. Harvard Business Review, 91(1–2), 114–121. https://
#pubmed.ncbi.nlm.nih.gov/23390745/
#Ribeiro, N., semedo, a. s., gomes, D., Bernardino, R., & singh, s. (2022). the effect of workplace bullying on burnout:
#the mediating role of affective well-being. Management Research Review, 45(6), 824–840. https://doi.org/10.1108/mrr-07-2021-0514
#samsudin, e. Z., isahak, M., & Rampal, s. (2021). Measuring exposure to workplace bullying among Malaysian junior
#doctors: Psychometric properties of the Negative acts Questionnaire–Revised. Journal of Health and Translational
#Medicine, 24(2), 110–116. https://doi.org/10.22452/jummec.vol24no2.15
#smith, l. M., andrusyszyn, M. a., & spence laschinger, H. K. (2010). effects of workplace incivility and empowerment
#on newly graduated nurses’ organizational commitment. Journal of Nursing Management, 18(8), 1004–1015. https://doi.org/10.1111/j.1365-2834.2010.01165.x
#statsoft inc. (2013). Electronic statistics textbook. statsoft.
#szarek, s., & szarek, e. (2018). economic effects of mobbing and violence in the workplace. Przedsiębiorczość i
#Zarządzanie, 19(3.2), 255–269.
#Vessey, J. a., DeMarco, R. F., gaffney, D. a., & Budin, W. c. (2009). Bullying of staff registered nurses in the workplace.
#Journal of Professional Nursing, 25(5), 299–306. https://pubmed.ncbi.nlm.nih.gov/19751935/
#World Health organization. (2022). Mental health at work fact sheet. Retrieved from https://www.who.int/news-room/
#factsheets/detail/mental-health-at-work
#yang, N. y., & choi, s. B. (2021). influence of personality factors and the perceived nursing organizational culture on
#workplace bullying of nurses. Journal of Korean Academic Society of Home Health Care Nursing, 28(2), 124–134.
#https://doi.org/10.5977/jkasne.2024.30.3.242"""
#
#
#test = """nowadays, organizations are operating in increasingly volatile environments, and to achieve a sustainable
#competitive advantage, they can encourage workplace behaviors that foster a favorable psychological
#and social climate by enabling employees to thrive in their work environment (abid et al., 2022a, abid & contreras, 2022; saleem et al., 2025). the presence of a thriving workforce is imperative for ensuring
#competitiveness and sustainable performance in contemporary organizational contexts characterized by
#continual growth (Prem et al., 2017). the thriving workforce provides a competitive edge for organiza-
#tions in growth phases and contributes significantly to the development of a psychologically healthy
#workplace. gallup’s (2016) survey estimates that 32% of the workforce is engaged, 51% is not engaged,
#and 17% is actively disengaged. the result is a workforce that does not perform well, often stays absent,
#and tends to leave the job. at the same time, the new millennial seeks more meaning, flexibility in their
#work (Boudreau et al., 2015), and a healthy workplace. kelloway and day (2005) define a healthy work-
#place as one that reduces stress and negative demands, promoting individuals’ overall well-being. In
#other words, employees want a working environment that provides them with opportunities to thrive
#rather than merely survive (spreitzer & Porath, 2012).
#spreitzer and her coauthors describe workplace thriving as “a positive and desirable psychological
#state in which employees experience a sense of vitality and learning.” spreitzer et al. (2005) have defined
#vitality, the primary dimension of thriving, as “a positive feeling of having energy and feeling alive.”
#authors define the second dimension of learning as “a sense that they are acquiring and applying valu-
#able knowledge and skills.” the presence of vitality and learning in employees is a crucial prerequisite for
#thriving in the workplace. a thriving workforce is associated with significant organizational outcomes,
#including lower levels of burnout, reduced absenteeism, increased job satisfaction, greater engagement
#and commitment, increased resilience, and the display of more innovative work behavior (abid et al., 2019).
#over the last two decades, significant research has been conducted on thriving; however, the existing
#corpus of knowledge is fragmented, and there is a need for research on systematic and theory-based
#synthesis (abid & contreras, 2022). Moreover, this construct has been examined predominantly at the
#individual level; there remains a paucity of research addressing collective thriving. the current literature
#on collective thriving at work lacks extensive information on identifying the most basic antecedents and
#consequences, and it lacks a framework for future study and organizational practice (kleine et al., 2019).
#second, while many studies have demonstrated the empirical validation of thriving (spreitzer & Porath,
#2012), research on workplace thriving remains limited (niessen et al., 2012). this study aims to fill this
#gap by investigating the antecedents and consequences of collective thriving.
#evidence from empirical studies has shown that organizational commitment is fostered by trust, per-
#ceptions of fairness, managerial coaching (abid et al., 2019), managerial support (agarwala et al., 2014;
#arshad et al., 2021), and prosocial motivation (ullah et al., 2020). however, the mechanism underlying
#the relationship is still in its infancy at the group level. We suggest that collective thriving at work serves
#as a mediating mechanism that transforms the impact of managerial support and prosocial motivation
#on the building of collective affective organizational commitment.
#organizational and/or Managerial support fosters an environment where employees feel valued, cared
#for, and encouraged to contribute beyond their formal roles (eisenberger et al., 2020). When managers
#recognize, provide guidance, and support, the subordinates are more likely to internalize organizational
#goals and develop stronger prosocial motives to benefit others (ullah et al., 2020) and the collective unit.
#Moreover, a supportive managerial climate enhances employees’ psychological safety and access to
#resources, promoting both vitality and learning—the two key dimensions of thriving at work. supportive
#managers empower teams and create development opportunities, leading to higher collective thriving.
#Prosocial motivation promotes the sense of learning and vitality (abid et al., 2018; nawaz et al., 2022).
#similarly, groups characterized by high prosocial motivation tend to engage in helping behaviors, posi-
#tive interactions, and mutual learning, which strengthen team vitality and learning. When employees are
#motivated to benefit others, they collectively experience greater energy and growth, resulting in higher
#group-level thriving. employees who experience learning and vitality at the workplace at the collective
#level are more likely to demonstrate organizational commitment at the collective level also.
#this study will contribute by providing a deeper insight into the role of managerial support and pro-
#social motivation, which will help employers create an environment where employees can thrive.
#Furthermore, we respond to Walumbwa et al. (2017) call, which encourages future studies to investigate
#the predictors and outcomes of workplace thriving at the group level of investigation. Finally, our study
#at the group level extends the literature on positive psychology by investigating the role that thriving at
#work serves as a self-regulatory mediating mechanism between antecedents (i.e. managerial support and
#prosocial motivation) and consequences (i.e. affective organizational commitment)."""
#
#
#processor = ParagraphProcessor()
#finals, links = processor.replace_citations_with_indices(test, text)
#
#print(finals)
#print(links)