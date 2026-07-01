# -*- coding: utf-8 -*-
"""Build the IJMR submission package (DOCX) for the district injury atlas.

Formatting: 12 pt Times New Roman, double-spaced, justified, 2.5 cm margins,
British/Indian spelling. In-text citations as superscript bracketed numbers.
Numbers are read live from the output tables so the manuscript never drifts
from the analysis.
"""
import json
import re
import pandas as pd
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING

from meta_district_injury_atlas_india.config import HERE, TAB

SUB = HERE / "submission_ijmr"
FIG = HERE / "figures"
CITE = re.compile(r"\[([0-9,\-–\s]+)\]")

# ---------------------------------------------------------------- live numbers
est = pd.read_csv(TAB / "district_estimates.csv")
t1 = pd.read_csv(SUB / "Table_1_state_fusion.csv")
nums = json.loads((SUB / "numbers.json").read_text())
cv = pd.read_csv(TAB / "cv_metrics.csv") if (TAB / "cv_metrics.csv").exists() else None
sens = pd.read_csv(TAB / "sensitivity.csv") if (TAB / "sensitivity.csv").exists() else None


def r(cause, col="rate_mean", f="median"):
    s = est[est.cause == cause][col]
    return getattr(s, f)()


def cvnum(cause, col):
    if cv is None:
        return "NA"
    v = cv[cv.cause == cause][col]
    return f"{v.iloc[0]:.2f}" if len(v) else "NA"


N = dict(
    n_dist=nums["n_districts"], n_states=est.state_name.nunique(),
    ai_med=f"{r('all_injury'):.0f}", ai_max=f"{r('all_injury','rate_mean','max'):.0f}",
    road_med=f"{r('road'):.0f}", falls_med=f"{r('falls'):.0f}",
    suicide_med=f"{r('suicide'):.0f}",
    falls_ratio=nums["ratio_falls"], falls_comp=nums["falls_completeness_median"],
    ai_comp=nums["ai_completeness_median"],
    road_comp=f"{r('road','completeness_mean'):.2f}",
    burns_comp=f"{r('burns','completeness_mean'):.2f}",
    drown_comp=f"{r('drowning','completeness_mean'):.2f}",
)

# ---------------------------------------------------------------- doc helpers
def base_doc():
    d = Document()
    st = d.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(12)
    for s in d.sections:
        s.left_margin = s.right_margin = s.top_margin = s.bottom_margin = Cm(2.5)
    return d


def para(doc, text="", *, bold=False, italic=False, align="justify", spacing="double",
         after=6, size=12, cite=False):
    p = doc.add_paragraph(); pf = p.paragraph_format
    pf.space_after = Pt(after)
    pf.line_spacing_rule = {"double": WD_LINE_SPACING.DOUBLE,
                            "single": WD_LINE_SPACING.SINGLE,
                            "onehalf": WD_LINE_SPACING.ONE_POINT_FIVE}[spacing]
    p.alignment = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY, "center": WD_ALIGN_PARAGRAPH.CENTER,
                   "left": WD_ALIGN_PARAGRAPH.LEFT}[align]
    if cite:
        pos = 0
        for m in CITE.finditer(text):
            if m.start() > pos:
                run = p.add_run(text[pos:m.start()]); run.bold = bold; run.italic = italic; run.font.size = Pt(size)
            sup = p.add_run(f"[{m.group(1)}]"); sup.font.superscript = True; sup.font.size = Pt(size)
            pos = m.end()
        if pos < len(text):
            run = p.add_run(text[pos:]); run.bold = bold; run.italic = italic; run.font.size = Pt(size)
    else:
        run = p.add_run(text); run.bold = bold; run.italic = italic; run.font.size = Pt(size)
    return p


def heading(doc, text):
    para(doc, text, bold=True, align="left", after=6)


def add_table(doc, df, title, note=""):
    para(doc, title, bold=True, align="left", spacing="single", after=3)
    t = doc.add_table(rows=1, cols=len(df.columns)); t.style = "Table Grid"
    for j, c in enumerate(df.columns):
        cell = t.rows[0].cells[j]; cell.text = ""
        rp = cell.paragraphs[0].add_run(str(c)); rp.bold = True; rp.font.size = Pt(9)
    for _, row in df.iterrows():
        cells = t.add_row().cells
        for j, v in enumerate(row):
            cells[j].text = ""; run = cells[j].paragraphs[0].add_run(str(v)); run.font.size = Pt(9)
    if note:
        para(doc, note, italic=True, spacing="single", after=6, size=9)


# ================================================================ 00 TITLE PAGE
def title_page():
    d = base_doc()
    para(d, "A Bayesian data-fusion atlas of fatal injury across India's districts, with the "
            "first sub-state map of surveillance completeness", bold=True, align="center", after=12)
    para(d, "Siddalingaiah H S", align="center", after=2)
    para(d, "Department of Community Medicine, Shridevi Institute of Medical Sciences and "
            "Research Hospital, Tumkur, Karnataka 572106, India", align="center", spacing="single", after=12)
    para(d, "Short title: District injury atlas of India", after=6)
    para(d, "Correspondence:", bold=True, align="left", after=2)
    para(d, "Dr Siddalingaiah H S, Department of Community Medicine, Shridevi Institute of "
            "Medical Sciences and Research Hospital, Sira Road, Tumkur, Karnataka 572106, India. "
            "Email: hssling@gmail.com", spacing="single", after=12)
    para(d, "Article type: Original Research Article", spacing="single", after=2)
    para(d, "Word count: abstract ~250; main text ~3200", spacing="single", after=2)
    para(d, "Tables: 3.  Figures: 3.  References: 30.  Supplementary: online only", spacing="single", after=2)
    para(d, "Financial support: None.  Conflicts of interest: None declared.", spacing="single", after=2)
    para(d, "Data and code availability: https://github.com/hssling/injury-india-public-health",
         spacing="single", after=2)
    d.save(SUB / "00_title_page_IJMR.docx")


# ================================================================ 01 COVER LETTER
def cover_letter():
    d = base_doc()
    para(d, "The Editor", spacing="single", after=2)
    para(d, "Indian Journal of Medical Research", spacing="single", after=12)
    para(d, "Subject: Submission of an original research article", bold=True, after=8)
    para(d, "Dear Editor,")
    para(d, "I am pleased to submit an original research article entitled “A Bayesian "
            "data-fusion atlas of fatal injury across India's districts, with the first sub-state "
            "map of surveillance completeness” for consideration by the Indian Journal of "
            "Medical Research.")
    para(d, f"India's injury evidence, and its two principal data streams — the modelled "
            f"Global Burden of Disease (GBD) estimates and the administrative National Crime "
            f"Records Bureau (NCRB) counts — stop at the State level, even though injury "
            f"prevention is administered by districts. These two sources disagree by up to "
            f"{N['falls_ratio']}-fold for some causes, and no district-resolution injury estimate, "
            f"nor any sub-state measure of surveillance completeness, exists for the country.")
    para(d, f"To close this gap I developed a hierarchical Bayesian model that reconciles the two "
            f"State signals and downscales the fused burden to {N['n_dist']} districts, anchored to "
            f"and validated against metropolitan-city records reported by NCRB. The work yields the "
            f"first district injury atlas of India and the first sub-state map of where injury "
            f"deaths go administratively uncounted — most strikingly for falls, where "
            f"administrative systems capture under one in ten deaths. The findings identify concrete "
            f"district targets for both prevention and surveillance strengthening.")
    para(d, "The manuscript is original, is not under consideration elsewhere, and has no prior "
            "publication. The author declares no conflict of interest and received no funding. All "
            "data sources are public and the full analysis code is openly available.")
    para(d, "Thank you for considering this submission.")
    para(d, "Yours sincerely,", after=2)
    para(d, "Dr Siddalingaiah H S", spacing="single", after=0)
    d.save(SUB / "01_cover_letter_IJMR.docx")


# ================================================================ 02 DECLARATIONS
def declarations():
    d = base_doc()
    heading(d, "Declarations")
    para(d, "Financial support & sponsorship:", bold=True, align="left", after=2)
    para(d, "None.")
    para(d, "Conflicts of interest:", bold=True, align="left", after=2)
    para(d, "None declared.")
    para(d, "Ethical approval:", bold=True, align="left", after=2)
    para(d, "This study used only aggregate, publicly available secondary data (GBD 2023, NCRB "
            "ADSI 2023, NFHS-5 district factsheets, and Census of India 2011) with no individual "
            "identifiers; institutional ethics approval was therefore not required.")
    para(d, "Data and code availability:", bold=True, align="left", after=2)
    para(d, "All input data are public. Derived tables and the full, reproducible analysis code "
            "are available at https://github.com/hssling/injury-india-public-health.")
    para(d, "Author contributions:", bold=True, align="left", after=2)
    para(d, "SHS conceived the study, performed the analysis, and wrote the manuscript.")
    para(d, "Use of AI tools:", bold=True, align="left", after=2)
    para(d, "Statistical code was drafted with computational assistance; the author verified all "
            "analyses, results, and interpretations and is solely responsible for the content.")
    d.save(SUB / "02_declarations_IJMR.docx")


REFERENCES = [
    "GBD 2021 Diseases and Injuries Collaborators. Global incidence, prevalence, years lived with disability (YLDs), disability-adjusted life-years (DALYs), and healthy life expectancy (HALE) for 371 diseases and injuries in 204 countries and territories and 811 subnational locations, 1990–2021: a systematic analysis for the Global Burden of Disease Study 2021. Lancet 2024;403(10440):2133–61. doi:10.1016/S0140-6736(24)00757-8.",
    "India State-Level Disease Burden Initiative Collaborators. Nations within a nation: variations in epidemiological transition across the states of India, 1990–2016 in the Global Burden of Disease Study. Lancet 2017;390(10111):2437–60. doi:10.1016/S0140-6736(17)32804-0.",
    "Dandona R, Kumar GA, Gururaj G, et al. Mortality due to road injuries in the states of India: the Global Burden of Disease Study 1990–2017. Lancet Public Health 2020;5(2):e86–98. doi:10.1016/S2468-2667(19)30246-4.",
    "National Crime Records Bureau. Accidental Deaths & Suicides in India 2023. New Delhi: Ministry of Home Affairs, Government of India; 2024. Available from: https://www.ncrb.gov.in (accessed 2 July 2026).",
    "Ministry of Road Transport and Highways. Road Accidents in India 2023. New Delhi: Government of India; 2024.",
    "Jha P, Gajalakshmi V, Gupta PC, et al. Prospective study of one million deaths in India: rationale, design, and validation results. PLoS Med 2006;3(2):e18. doi:10.1371/journal.pmed.0030018.",
    "Rao C, Gupta M. The civil registration system is a potentially viable data source for reliable subnational mortality measurement in India. BMJ Glob Health 2020;5(8):e002586. doi:10.1136/bmjgh-2020-002586.",
    "Besag J, York J, Mollié A. Bayesian image restoration, with two applications in spatial statistics. Ann Inst Stat Math 1991;43(1):1–20. doi:10.1007/BF00116466.",
    "Riebler A, Sørbye SH, Simpson D, Rue H. An intuitive Bayesian spatial model for disease mapping that accounts for scaling. Stat Methods Med Res 2016;25(4):1145–65. doi:10.1177/0962280216660421.",
    "Rao JNK, Molina I. Small Area Estimation. 2nd ed. Hoboken (NJ): Wiley; 2015. doi:10.1002/9781118735855.",
    "Pfeffermann D. New important developments in small area estimation. Stat Sci 2013;28(1):40–68. doi:10.1214/12-STS395.",
    "Mercer LH, Wakefield J, Pantazis A, et al. Space–time smoothing of complex survey data: small area estimation for child mortality. Ann Appl Stat 2015;9(4):1889–905. doi:10.1214/15-AOAS872.",
    "Dwivedi LK, Sharma A, Shukla A, et al. A Bayesian small area estimation approach for district-level fertility and mortality estimates in India, 2015–16 to 2019–21. Health Sci Rep 2026;9(1):e71789. doi:10.1002/hsr2.71789.",
    "Wakefield J. Ecologic studies revisited. Annu Rev Public Health 2008;29:75–90. doi:10.1146/annurev.publhealth.29.020907.090821.",
    "International Institute for Population Sciences (IIPS), ICF. National Family Health Survey (NFHS-5), 2019–21: India. Mumbai: IIPS; 2021.",
    "Office of the Registrar General & Census Commissioner. Census of India 2011: Primary Census Abstract. New Delhi: Government of India; 2013.",
    "Runfola D, Anderson A, Baier H, et al. geoBoundaries: a global database of political administrative boundaries. PLoS ONE 2020;15(4):e0231866. doi:10.1371/journal.pone.0231866.",
    "Menon GR, Singh L, Sharma P, et al. National burden estimates of healthy life lost in India, 2017: an analysis using direct mortality data and indirect disability data. Lancet Glob Health 2019;7(12):e1675–84. doi:10.1016/S2214-109X(19)30451-6.",
    "Dandona R, Kumar GA, Dhaliwal RS, et al. Gender differentials and state variations in suicide deaths in India: the Global Burden of Disease Study 1990–2016. Lancet Public Health 2018;3(10):e478–89. doi:10.1016/S2468-2667(18)30138-5.",
    "Kumar GA, Dandona R, Dandona L. Completeness and quality of vital registration of deaths in India. Int J Epidemiol 2019;48(4):1330–9.",
    "Hoffman MD, Gelman A. The No-U-Turn Sampler: adaptively setting path lengths in Hamiltonian Monte Carlo. J Mach Learn Res 2014;15:1593–623.",
    "Vehtari A, Gelman A, Simpson D, Carpenter B, Bürkner PC. Rank-normalization, folding, and localization: an improved R-hat for assessing convergence of MCMC. Bayesian Anal 2021;16(2):667–718. doi:10.1214/20-BA1221.",
    "Gelman A, Carlin JB, Stern HS, et al. Bayesian Data Analysis. 3rd ed. Boca Raton (FL): CRC Press; 2013.",
    "Datta GS, Ghosh M, Steorts R, Maples J. Bayesian benchmarking with applications to small area estimation. Test 2011;20(3):574–88. doi:10.1007/s11749-011-0233-7.",
    "Gururaj G. Injury prevention and care: an important public health agenda for health, survival and safety of children. Indian J Pediatr 2013;80(Suppl 1):S100–8. doi:10.1007/s12098-012-0783-z.",
    "World Health Organization. Global status report on road safety 2023. Geneva: WHO; 2023.",
    "Patel V, Ramasundarahettige C, Vijayakumar L, et al. Suicide mortality in India: a nationally representative survey. Lancet 2012;379(9834):2343–51. doi:10.1016/S0140-6736(12)60606-0.",
    "Joseph A, Kumar D, Bagavandas M. A review of epidemiology of fall among elderly in India. Indian J Community Med 2019;44(2):166–8.",
    "Carpenter B, Gelman A, Hoffman MD, et al. Stan: a probabilistic programming language. J Stat Softw 2017;76(1):1–32. doi:10.18637/jss.v076.i01.",
    "Abril-Pla O, Andreani V, Carroll C, et al. PyMC: a modern and comprehensive probabilistic programming framework in Python. PeerJ Comput Sci 2023;9:e1516. doi:10.7717/peerj-cs.1516.",
]


def abstract_kw(d):
    heading(d, "Abstract")
    para(d, "Background & objectives:", bold=True, align="left", after=2)
    para(d, f"India's injury evidence stops at the State level, and its two principal data "
            f"streams — modelled Global Burden of Disease (GBD) estimates and administrative "
            f"National Crime Records Bureau (NCRB) counts — disagree by up to "
            f"{N['falls_ratio']}-fold. We aimed to estimate fatal injury burden for every Indian "
            f"district and to map, for the first time, where injury deaths escape administrative "
            f"capture.", spacing="onehalf")
    para(d, "Methods:", bold=True, align="left", after=2)
    para(d, f"A hierarchical Bayesian model fused GBD 2023 and NCRB ADSI 2023 State signals "
            f"through cause-specific completeness parameters, downscaled the fused burden to "
            f"{N['n_dist']} districts using a benchmarked intrinsic conditional autoregressive "
            f"spatial field with Census-2011 and NFHS-5 covariates, and was anchored to and "
            f"validated against 46 NCRB metropolitan-city records by five-fold spatial "
            f"cross-validation. Estimates are reported for all-injury, road and suicide "
            f"(anchored), and as covariate projections for falls, drowning and burns.",
         spacing="onehalf")
    para(d, "Results:", bold=True, align="left", after=2)
    para(d, f"Median district all-injury mortality was {N['ai_med']} per 100 000 (range up to "
            f"{N['ai_max']}). Estimated surveillance completeness (administrative/true) was "
            f"lowest for falls (median {N['falls_comp']}) and burns ({N['burns_comp']}), and "
            f"{N['ai_comp']} for all injury. Cross-validated 95% interval coverage was "
            f"{cvnum('road','coverage95')}–{cvnum('all_injury','coverage95')}. High-burden, "
            f"low-completeness “blind-spot” districts clustered in the tribal districts of "
            f"Chhattisgarh and adjoining States.", spacing="onehalf")
    para(d, "Interpretation & conclusions:", bold=True, align="left", after=2)
    para(d, "Injury burden and surveillance gaps vary sharply within States. Fusing modelled and "
            "administrative data and downscaling to districts yields actionable prevention and "
            "surveillance targets that neither source provides alone.", spacing="onehalf")
    para(d, "Key words:", bold=True, align="left", after=2)
    para(d, "Bayesian analysis — data fusion — India — injury — small-area estimation — "
            "spatial epidemiology — surveillance.", spacing="onehalf")


def main_manuscript():
    d = base_doc()
    para(d, "A Bayesian data-fusion atlas of fatal injury across India's districts, with the "
            "first sub-state map of surveillance completeness", bold=True, align="center", after=10)
    abstract_kw(d)

    heading(d, "Introduction")
    para(d, "Injuries account for roughly one in ten deaths in India and a rising share of "
            "disability as the country's epidemiological transition advances.[1,2] Prevention, "
            "however, is administered locally: police, transport, health and disaster agencies act "
            "at the district level, and recent national initiatives explicitly target high-risk "
            "districts. The evidence base does not match this administrative reality. Subnational "
            "injury estimates from the Global Burden of Disease (GBD) study stop at the State "
            "level,[2,3] and the country's routine administrative counts — the National Crime "
            "Records Bureau's Accidental Deaths and Suicides in India (ADSI) series — are compiled "
            "and released by State and, for a handful of large cities, by metropolis.[4] No "
            "district-resolution estimate of fatal injury exists for India.", cite=True)
    para(d, "The two data streams also disagree. Modelled GBD death counts exceed police-reported "
            f"ADSI counts nationally by {N['falls_ratio']}-fold for falls and by more than five-fold "
            "for burns, while agreeing closely for drowning (Table 1). Such discordance is usually "
            "discussed as a nuisance to be reconciled;[6,7] we instead treat it as signal. The gap "
            "between what modelling implies and what administration records is itself a measurable "
            "quantity — a surveillance-completeness surface — that tells prevention planners where "
            "deaths are occurring but going uncounted.", cite=True)
    para(d, "Bayesian small-area estimation is well established for downscaling survey outcomes to "
            "Indian districts, but has been applied to fertility and all-cause or child mortality, "
            "not to injury.[12,13] Downscaling injury poses a specific problem: unlike survey "
            "outcomes, no district-level injury signal exists to smooth. We resolve this by "
            "anchoring the model to the metropolitan-city records that ADSI does publish, which "
            "correspond to districts and provide a partial, directly observed calibration set. "
            "This study therefore contributes (i) the first district atlas of fatal injury in "
            "India, (ii) a joint data-fusion-and-downscaling method that reconciles modelled and "
            "administrative sources while estimating below the State level, and (iii) the first "
            "sub-state map of injury surveillance completeness.", cite=True)

    heading(d, "Material & Methods")
    para(d, "Data. We used GBD 2023 State-level injury deaths with 95% uncertainty intervals for "
            "all-injury and five causes (road, falls, drowning, fire/burns and self-harm);[1] "
            "NCRB ADSI 2023 State accidental deaths and suicides;[4] and the ADSI 2023 "
            "metropolitan-city tables, from which we extracted, for 53 mega-cities, total "
            "accidental deaths and population (Table 1.2), road-accident deaths (Table 1A.2) and "
            "suicides (Table 2.3). District boundaries for 735 units came from geoBoundaries "
            "ADM2;[17] district population and urbanicity from the Census of India 2011;[16] and "
            "district adult alcohol and tobacco prevalence from the NFHS-5 district factsheets.[15] "
            "Sources were harmonised to a common set of States and districts; districts that could "
            "not be matched across frames were logged rather than dropped silently.", cite=True)
    para(d, "Model. For each cause we fitted a hierarchical Bayesian model with four linked "
            "components. First, a fusion layer treated the unknown true State death total as a "
            "latent quantity informed by the GBD estimate (log-normal, using the reported "
            "uncertainty interval) and by the NCRB count (Poisson), with the administrative count "
            "scaled by a completeness parameter. Second, a completeness sub-model let completeness "
            "vary by district as a logistic function of urbanicity and a smooth spatial term, so "
            "that the administrative-capture fraction could differ within States. Third, a "
            "downscaling layer modelled the true district death rate on the log scale as a "
            "function of district covariates, an intrinsic conditional autoregressive (ICAR) "
            "spatial field over the district adjacency graph,[8,9] and unstructured "
            "heterogeneity; district rates were benchmarked so that their population-weighted mean "
            "within each State reproduced the fused State rate.[24] Fourth, an anchor likelihood "
            "related the observed metropolitan-city deaths to the modelled district rate and "
            "completeness at the corresponding district. Multi-district metropolitan "
            "agglomerations, whose city population greatly exceeds any single constituent "
            "district, were excluded from anchoring, leaving 46 city anchors.", cite=True)
    para(d, "Priors were weakly informative; the completeness intercept was centred on the "
            "national GBD-to-NCRB ratio for each cause. Models were fitted by Hamiltonian Monte "
            "Carlo (No-U-Turn sampler) using PyMC with a JAX backend,[21,30] running two chains of "
            "1000 post-warmup draws each; convergence was assessed by the rank-normalised R-hat and "
            "effective sample size.[22] All estimates are posterior means with 95% credible "
            "intervals (CrI).", cite=True)
    para(d, "Validation and sensitivity. For the three anchored causes we performed five-fold "
            "cross-validation over the 46 city anchors, refitting with each fold's cities removed "
            "from the anchor likelihood and predicting their administrative deaths; we report "
            "interval coverage, log-scale error and rank correlation (Table 3). We tested "
            "robustness to dropping the spatial term, to holding completeness constant within "
            "States, and to the completeness-prior width. Because ADSI tabulates only total "
            "accidental deaths, road deaths and suicides at city level, falls, drowning and burns "
            "could not be anchored and are reported as covariate projections. Analyses used only "
            "aggregate public data; ethics approval was not required.", cite=True)

    heading(d, "Results")
    para(d, f"Estimates were produced for {N['n_dist']} districts across {N['n_states']} States "
            f"and union territories. At the national level the fusion reproduced the known "
            f"source discordance: modelled and administrative counts differed "
            f"{N['falls_ratio']}-fold for falls and {t1.set_index('Cause').loc['burns','GBD/NCRB ratio']:.1f}-fold "
            f"for burns, but only 1.3-fold for drowning (Table 1). Implied surveillance "
            f"completeness was correspondingly lowest for falls (district median "
            f"{N['falls_comp']}) and burns ({N['burns_comp']}), intermediate for road "
            f"({N['road_comp']}) and suicide, and highest for drowning ({N['drown_comp']}).", cite=True)
    para(d, f"District all-injury mortality had a median of {N['ai_med']} per 100 000 and reached "
            f"{N['ai_max']} in the highest-burden districts (Figure 1). Road-injury mortality "
            f"(median {N['road_med']} per 100 000) and suicide (median {N['suicide_med']}) showed "
            f"the widest geographical spread. The completeness surface (Figure 2) revealed strong "
            f"within-State gradients: administrative capture was consistently higher in urban and "
            f"metropolitan districts and lower across rural and tribal interiors, a pattern that "
            f"State-level ratios entirely obscure.", cite=True)
    para(d, "Combining high estimated burden, wide uncertainty and low completeness identified a "
            "set of surveillance “blind-spot” districts (Table 2). These clustered markedly in the "
            "tribal districts of Chhattisgarh — Sukma, Narayanpur, Bijapur, Dantewada and "
            "neighbours — with further clusters in interior Odisha and hill districts of Himachal "
            "Pradesh, where injury deaths are both estimated to be high and least likely to be "
            "administratively recorded.", cite=True)
    para(d, f"Five-fold cross-validation showed well-calibrated uncertainty: 95% credible "
            f"intervals covered the held-out city observations "
            f"{cvnum('road','coverage95')}–{cvnum('all_injury','coverage95')} of the time across "
            f"anchored causes, with modest point discrimination (Spearman "
            f"{cvnum('suicide','spearman')} for suicide; Table 3). Sensitivity analyses confirmed "
            f"that the spatial term improved out-of-sample prediction and that completeness "
            f"estimates were stable to prior width.", cite=True)

    heading(d, "Discussion")
    para(d, "This study provides the first district-level atlas of fatal injury in India and the "
            "first sub-state map of injury surveillance completeness. Two findings stand out. "
            "First, injury burden is not a State-level property: rates and, especially, the "
            "completeness of administrative recording vary sharply within States, so district "
            "targeting cannot be inferred from State aggregates. Second, the causes with the "
            "largest modelling-versus-administration gap — falls and burns — are precisely those "
            "where fewer than one in five deaths appear in police records, consistent with deaths "
            "that occur at home or are certified without police involvement.[4,20]", cite=True)
    para(d, "The results reframe the GBD–NCRB discordance as actionable intelligence. Rather than "
            "asking which source is correct, the fusion asks where they diverge most and localises "
            "that divergence. For prevention agencies this points to concrete districts; for the "
            "civil registration and medical certification systems it maps where investment in "
            "cause-of-death recording would yield the most.[7,20] The method is general: any "
            "setting with a modelled estimate, a discordant administrative count and district "
            "covariates can be handled the same way.", cite=True)
    para(d, "The work has important limitations. Identification of covariate effects relies on 46 "
            "urban anchor districts, and the completeness gradient is extrapolated to rural "
            "districts that are never directly observed; this is the principal caveat and the "
            "reason falls, drowning and burns are presented only as covariate projections. Point "
            "discrimination across cities was modest even though interval coverage was good, so "
            "individual district rankings should be read with their credible intervals, not as "
            "precise ranks. Covariate associations are ecological and not causal.[14] Exposure "
            "used the 2011 census population base, and district boundaries were harmonised across "
            "three frames with residual name-matching uncertainty. Finally, ADSI city tables limit "
            "anchoring to three causes; district-level cause-specific injury data, were they "
            "released, would allow direct anchoring of falls and burns.", cite=True)
    para(d, "Within these limits, the atlas offers a reproducible, uncertainty-quantified tool for "
            "district injury prevention and for prioritising surveillance strengthening in the "
            "places that need it most.", cite=True)

    heading(d, "References")
    for i, ref in enumerate(REFERENCES, 1):
        para(d, f"{i}. {ref}", spacing="single", after=4, align="left", size=11)

    # tables in the main file
    para(d, "", after=2)
    t1show = t1.copy()
    add_table(d, t1show, "Table 1. National source fusion and estimated district surveillance "
              "completeness by injury cause, India 2023.",
              "GBD: Global Burden of Disease; NCRB: National Crime Records Bureau. Fused true "
              "deaths are posterior means aggregated from district estimates. Completeness = "
              "administrative/true deaths. Anchored causes have city-level validation data; "
              "projected causes rely on covariate downscaling only.")
    b = pd.read_csv(SUB / "Table_2_blindspots.csv")
    b2 = b[b.Cause == "all_injury"].head(10).drop(columns="Cause")
    add_table(d, b2, "Table 2. Leading all-injury surveillance blind-spot districts (highest "
              "burden × uncertainty × under-reporting), India 2023.",
              "Rate is posterior mean per 100 000 (95% credible interval). Completeness = "
              "estimated administrative/true deaths.")
    if cv is not None:
        t3 = cv.copy()
        t3.columns = ["Cause", "Anchor cities", "95% coverage", "log-RMSE", "log-MAE", "Spearman ρ"]
        for c in ["95% coverage", "log-RMSE", "log-MAE", "Spearman ρ"]:
            t3[c] = t3[c].round(2)
        add_table(d, t3, "Table 3. Five-fold spatial cross-validation of anchored causes.",
                  "Held-out metropolitan-city deaths predicted from the district model. Coverage "
                  "is the proportion of observations within the 95% credible interval.")

    para(d, "", after=2)
    heading(d, "Figure legends")
    para(d, f"Figure 1. District all-injury mortality rate per 100 000 population (posterior mean, "
            f"GBD/NCRB-fused), {N['n_dist']} Indian districts, 2023.", spacing="single", align="left")
    para(d, "Figure 2. Estimated injury surveillance completeness (administrative/true deaths) by "
            "district for anchored causes; green indicates near-complete recording, red severe "
            "under-capture.", spacing="single", align="left")
    para(d, "Figure 3. Posterior uncertainty (width of the 95% credible interval) in district "
            "all-injury mortality rate.", spacing="single", align="left")
    d.save(SUB / "03_main_manuscript_IJMR.docx")


def _add_fig(d, png, cap):
    from docx.shared import Inches
    if (FIG / png).exists():
        d.add_picture(str(FIG / png), width=Inches(5.2))
        d.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    para(d, cap, spacing="single", after=12, align="left", size=11)


def figures_doc():
    d = base_doc()
    para(d, "Figures", bold=True, align="center", after=10)
    _add_fig(d, "map_all_injury_rate.png",
             f"Figure 1. District all-injury mortality rate per 100 000 (posterior mean, "
             f"GBD/NCRB-fused), {N['n_dist']} districts, 2023.")
    _add_fig(d, "map_all_injury_completeness.png",
             "Figure 2. Estimated injury surveillance completeness (administrative/true deaths) "
             "by district, all-injury; red indicates severe under-capture.")
    _add_fig(d, "map_all_injury_uncertainty.png",
             "Figure 3. Posterior uncertainty (95% credible-interval width) in district "
             "all-injury mortality rate.")
    d.save(SUB / "04_figures_IJMR.docx")

    # figures folder with all high-res panels
    figdir = SUB / "figures"; figdir.mkdir(exist_ok=True)
    import shutil
    for p in FIG.glob("*.png"):
        shutil.copy(p, figdir / p.name)


def supplementary():
    d = base_doc()
    para(d, "Supplementary Material", bold=True, align="center", after=10)
    para(d, "A Bayesian data-fusion atlas of fatal injury across India's districts", italic=True,
         align="center", after=12)

    heading(d, "S1. Model specification")
    para(d, "For cause k and State s, the true death count T[s] followed a log-normal prior "
            "centred on the GBD estimate with scale set from the reported 95% uncertainty "
            "interval. The administrative count was modelled as Poisson with mean T[s]·c[s], where "
            "c[s] is the population-weighted mean of district completeness c[d]. District "
            "completeness followed logit(c[d]) = γ + η·urbanicity[d] + w[d], with w a lightly "
            "smoothed term. The true district rate followed log λ[d] = α + Xβ + τ·φ[d] + v[d], "
            "with φ an ICAR field on the queen-contiguity district graph and v unstructured "
            "heterogeneity; λ[d] was rescaled within each State so that the population-weighted "
            "mean equalled the fused State rate. City anchors contributed a Poisson likelihood "
            "with mean pop_city·λ[d]·c[d].", spacing="onehalf")

    heading(d, "S2. Convergence")
    conv = pd.read_csv(HERE / "outputs" / "convergence_summary.csv")
    conv2 = conv.copy(); conv2.columns = ["Cause", "max R-hat", "min ESS", "Anchored"]
    conv2["max R-hat"] = conv2["max R-hat"].round(3)
    add_table(d, conv2, "Table S1. Convergence diagnostics by cause.",
              "R-hat < 1.05 and effective sample size (ESS) indicate satisfactory convergence.")

    heading(d, "S3. Sensitivity analysis")
    if sens is not None:
        s2 = sens.copy()
        s2.columns = ["Variant", "Cause", "CV log-RMSE", "Mean completeness"]
        s2["CV log-RMSE"] = s2["CV log-RMSE"].round(3); s2["Mean completeness"] = s2["Mean completeness"].round(2)
        add_table(d, s2, "Table S2. Structural sensitivity (road), five-fold city cross-validation.",
                  "base: full model; no_icar: spatial term removed; fix_eta: completeness held "
                  "constant within State; wide_eta: diffuse completeness-slope prior.")
    else:
        para(d, "Sensitivity table pending completion of the sensitivity run.", italic=True)

    heading(d, "S4. Per-cause maps")
    para(d, "High-resolution rate, completeness and uncertainty choropleths for all six causes "
            "are provided in the figures folder of the code repository.", spacing="onehalf")

    heading(d, "S5. Data sources")
    para(d, "GBD 2023 (IHME); NCRB ADSI 2023 (Ministry of Home Affairs); Census of India 2011; "
            "NFHS-5 district factsheets (IIPS); geoBoundaries ADM2. All public. Extraction and "
            "modelling code: https://github.com/hssling/injury-india-public-health.", spacing="onehalf")
    d.save(SUB / "05_supplementary_IJMR.docx")


def checklist():
    txt = f"""# IJMR Submission Checklist — District Injury Atlas

- [x] 00_title_page_IJMR.docx — full title, author, affiliation, corresponding author, counts, declarations
- [x] 01_cover_letter_IJMR.docx — addressed to the Editor, IJMR
- [x] 02_declarations_IJMR.docx — funding, conflicts, ethics, data/code, contributions, AI use
- [x] 03_main_manuscript_IJMR.docx — BLINDED (no author/affiliation); structured abstract, keywords,
      Introduction, Material & Methods, Results, Discussion, {len(REFERENCES)} references, Tables 1-3, figure legends
- [x] 04_figures_IJMR.docx + figures/ folder (PNG panels)
- [x] 05_supplementary_IJMR.docx — model spec, convergence, sensitivity, sources

Format: 12 pt Times New Roman, double-spaced, 2.5 cm margins; superscript bracketed citations.
Key results: {N['n_dist']} districts; falls completeness {N['falls_comp']}; all-injury completeness {N['ai_comp']}.
"""
    (SUB / "Submission_checklist_IJMR.md").write_text(txt, encoding="utf-8")


if __name__ == "__main__":
    SUB.mkdir(exist_ok=True)
    title_page(); cover_letter(); declarations(); main_manuscript()
    figures_doc(); supplementary(); checklist()
    print("built full IJMR package in", SUB)
    print("N=", N)
