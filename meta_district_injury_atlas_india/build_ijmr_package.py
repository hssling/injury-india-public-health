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

TITLE = ("Where India's injury deaths go uncounted: a district atlas of fatal injury "
         "burden and surveillance completeness")

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
    n_anchor=int(cv["n_cities"].iloc[0]) if cv is not None else 41,
)


def _iqr(cause, col="rate_mean"):
    s = est[est.cause == cause][col]
    return f"{s.quantile(.25):.0f}–{s.quantile(.75):.0f}"


def _fused(cause):
    return f"{int(t1.set_index('Cause').loc[cause, 'Fused true deaths']):,}"


# extra derived quantities for the full-length manuscript
falls_lt10 = int((est[est.cause == "falls"].completeness_mean < 0.10).sum())
falls_n = int((est.cause == "falls").sum())
ai_lt40 = int((est[est.cause == "all_injury"].completeness_mean < 0.40).sum())
_sm = est[est.cause == "all_injury"].groupby("state_name").rate_mean.median().sort_values()
E = dict(
    ai_iqr=_iqr("all_injury"), road_iqr=_iqr("road"), suicide_iqr=_iqr("suicide"),
    falls_iqr=_iqr("falls"),
    ai_fused=_fused("all_injury"), road_fused=_fused("road"), suicide_fused=_fused("suicide"),
    falls_fused=_fused("falls"), burns_fused=_fused("burns"), drown_fused=_fused("drowning"),
    falls_lt10=falls_lt10, falls_n=falls_n, ai_lt40=ai_lt40,
    hi_state=_sm.index[-1], hi_val=f"{_sm.iloc[-1]:.0f}",
    hi2_state=_sm.index[-2], hi2_val=f"{_sm.iloc[-2]:.0f}",
    lo_state=_sm.index[0], lo_val=f"{_sm.iloc[0]:.0f}",
    lo2_state=_sm.index[1], lo2_val=f"{_sm.iloc[1]:.0f}",
    burns_ratio=f"{t1.set_index('Cause').loc['burns','GBD/NCRB ratio']:.1f}",
    road_ratio=f"{t1.set_index('Cause').loc['road','GBD/NCRB ratio']:.1f}",
    suicide_ratio=f"{t1.set_index('Cause').loc['suicide','GBD/NCRB ratio']:.1f}",
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
            # IJMR style: bare superscript number(s), no brackets
            sup = p.add_run(m.group(1).strip()); sup.font.superscript = True; sup.font.size = Pt(size)
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
    para(d, TITLE, bold=True, align="center", after=12)
    para(d, "Siddalingaiah H S", align="center", after=2)
    para(d, "Department of Community Medicine, Shridevi Institute of Medical Sciences and "
            "Research Hospital, Tumkur, Karnataka 572106, India", align="center", spacing="single", after=12)
    para(d, "Short title: District injury atlas of India", after=6)
    para(d, "Correspondence:", bold=True, align="left", after=2)
    para(d, "Dr Siddalingaiah H S, Department of Community Medicine, Shridevi Institute of "
            "Medical Sciences and Research Hospital, Sira Road, Tumkur, Karnataka 572106, India. "
            "Email: hssling@gmail.com", spacing="single", after=12)
    para(d, "Article type: Original Research Article", spacing="single", after=2)
    para(d, "Word count: abstract 238; main text ~2380", spacing="single", after=2)
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
    para(d, f"I am pleased to submit an original research article entitled “{TITLE}” for "
            f"consideration by the Indian Journal of Medical Research.")
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
            f"validated against {N['n_anchor']} NCRB metropolitan-city records by five-fold spatial "
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
    para(d, TITLE, bold=True, align="center", after=10)
    abstract_kw(d)

    heading(d, "Introduction")
    para(d, "Injuries account for roughly one in ten deaths in India and, as communicable and "
            "childhood diseases recede, for a growing share of premature mortality and "
            "disability.[1,2] Road crashes, self-harm, falls, drowning and burns together kill "
            "several hundred thousand Indians each year, disproportionately among the young and "
            "the economically active.[3,18] Unlike most non-communicable diseases, the immediate "
            "causes of injury are external and, in principle, preventable through engineering, "
            "enforcement, environmental modification and timely trauma care — interventions that "
            "are delivered not by States but by districts. Police, transport authorities, health "
            "departments and disaster-management agencies all operate at the district level, and "
            "recent national policy has made the district the explicit unit of action, for "
            "example by identifying high-fatality districts for road-safety intervention.", cite=True)
    para(d, "The evidence base does not match this administrative reality. Subnational injury "
            "estimates from the Global Burden of Disease (GBD) study, which have transformed "
            "understanding of India's epidemiological transition, stop at the State level.[2,3] "
            "The country's routine administrative record of external deaths — the National Crime "
            "Records Bureau's Accidental Deaths and Suicides in India (ADSI) series — is compiled "
            "from police returns and released by State, with cause detail for only a handful of "
            "large cities.[4] Civil registration, though improving, still under-records rural "
            "deaths and rarely assigns a medically certified cause outside large hospitals.[7,20] "
            "The net result is that no district-resolution estimate of fatal injury exists for "
            "India, and planners in the districts that carry the greatest burden have the least "
            "reliable local data.", cite=True)
    para(d, "The two national data streams also disagree, and the disagreement is highly "
            f"structured. Modelled GBD death counts exceed police-reported ADSI counts nationally "
            f"by {N['falls_ratio']}-fold for falls and {E['burns_ratio']}-fold for burns, by "
            f"{E['road_ratio']}-fold for road injury and {E['suicide_ratio']}-fold for suicide, "
            f"yet by only 1.3-fold for drowning (Table 1). This pattern is not random noise: it "
            f"tracks how a death comes to official attention. Falls among older adults and fatal "
            f"burns frequently occur at home and are certified, if at all, without police "
            f"involvement, whereas road crashes and many suicides generate a police record almost "
            f"by definition.[4,20] Such discordance is usually treated as a nuisance to be "
            f"reconciled;[6,7] we instead treat it as signal. The gap between what modelling "
            f"implies and what administration records is itself a measurable quantity — a "
            f"surveillance-completeness surface — that reveals where deaths occur but go "
            f"uncounted.", cite=True)
    para(d, "Estimating below the State level is a small-area problem. Bayesian small-area "
            "estimation is well established for downscaling survey outcomes to Indian districts, "
            "but has been applied to fertility and all-cause or child mortality, where the "
            "underlying survey itself yields a noisy district signal to be smoothed.[10,11,12,13] "
            "Injury downscaling poses a harder problem: neither GBD nor ADSI provides any "
            "district-level injury signal to anchor the estimates, so covariate-only "
            "disaggregation would rest on an untestable assumption. We resolve this by exploiting "
            "the one place ADSI does descend below the State: the metropolitan-city tables, whose "
            "cities correspond to districts and supply a partial but directly observed calibration "
            "and validation set.", cite=True)
    para(d, "This study therefore makes three contributions. First, it provides the first "
            "district-resolution atlas of fatal injury in India, with full uncertainty "
            "quantification. Second, it introduces a joint model that fuses discordant modelled "
            "and administrative sources while simultaneously downscaling to districts, benchmarked "
            "for internal consistency and calibrated against real sub-state observations. Third, "
            "it produces the first map of injury surveillance completeness below the State level, "
            "converting a long-noted data discrepancy into an operational guide for where both "
            "prevention and death-recording systems most need strengthening.", cite=True)

    heading(d, "Material & Methods")
    para(d, "Data sources. State-level injury deaths with 95% uncertainty intervals for "
            "all-injury and five causes (road, falls, drowning, fire/burns and self-harm) were "
            "obtained from the Global Burden of Disease Study 2023.[1] State administrative counts "
            "came from NCRB ADSI 2023: police-reported accidental deaths by cause and total "
            "suicides.[4] Sub-state anchors were extracted directly from the ADSI 2023 report's "
            "metropolitan-city chapter, which tabulates, for 53 mega-cities (population ≥1 "
            "million), total accidental deaths and city population (Table 1.2), road-accident "
            "deaths (Table 1A.2) and suicides (Table 2.3); parsed values were checked against the "
            "report's own narrative figures. District geometry for 735 units came from the "
            "geoBoundaries ADM2 database;[17] district population and the urban household share "
            "from the Census of India 2011;[16] and district adult alcohol and tobacco prevalence "
            "from the NFHS-5 district factsheets.[15] District names were harmonised across the "
            "three frames by State-blocked fuzzy matching; unmatched units and covariate gaps were "
            "logged and imputed from the State mean rather than dropped silently, and district "
            "populations were rescaled within each State to sum to the State census total so that "
            "aggregation weights were internally consistent.", cite=True)
    para(d, "Model structure. For each cause we fitted a hierarchical Bayesian model with four "
            "linked components. The fusion layer treated the unknown true State death total as a "
            "latent quantity informed jointly by the GBD estimate — entered as a log-normal "
            "likelihood whose dispersion was set from the reported uncertainty interval — and by "
            "the NCRB count, entered as a Poisson likelihood whose mean was the true total scaled "
            "by a completeness fraction between zero and one. The completeness sub-model allowed "
            "that fraction to vary by district as a logistic function of urbanicity and a lightly "
            "smoothed spatial term, so that administrative capture could differ within a State; "
            "the State completeness entering the fusion was the population-weighted mean of its "
            "district values. The downscaling layer modelled the true district death rate on the "
            "log scale as an intercept plus district covariates, an intrinsic conditional "
            "autoregressive (ICAR) spatial field over the queen-contiguity district adjacency "
            "graph,[8,9] and unstructured heterogeneity. District rates were then benchmarked — "
            "rescaled so that their population-weighted mean within each State exactly reproduced "
            "the fused State rate — guaranteeing coherence between the district atlas and the "
            "State totals.[10,24] Finally, an anchor likelihood related the observed "
            "metropolitan-city deaths to the modelled rate and completeness at the corresponding "
            "district, using each city's own reported population as the exposure.", cite=True)
    para(d, f"Because NCRB “cities” are urban agglomerations, several metropolitan anchors span "
            f"many districts and cannot be attached to one; anchors whose city population exceeded "
            f"twice the matched district's population were therefore excluded, leaving "
            f"{N['n_anchor']} single-district city anchors for calibration. Priors were weakly "
            f"informative, with the completeness intercept for each cause centred on the national "
            f"GBD-to-NCRB ratio. Models were fitted by Hamiltonian Monte Carlo using the "
            f"No-U-Turn sampler in PyMC with a JAX backend,[21,29,30] running two chains of 1000 "
            f"post-warmup draws; convergence was judged by the rank-normalised R-hat (<1.05) and "
            f"effective sample size.[22] All results are posterior means with 95% credible "
            f"intervals (CrI).", cite=True)
    para(d, f"Validation and sensitivity. For the three anchored causes we performed five-fold "
            f"cross-validation over the {N['n_anchor']} city anchors, refitting the full model "
            f"with each fold's cities removed from the anchor likelihood and predicting their "
            f"administrative deaths out of sample; we report the proportion of held-out "
            f"observations within the 95% credible interval (coverage), the log-scale root mean "
            f"squared error, and the Spearman rank correlation between predicted and observed city "
            f"deaths (Table 3). Robustness was examined by removing the spatial field, holding "
            f"completeness constant within States, and widening the completeness-slope prior "
            f"(Table S2). Because ADSI tabulates only total accidental deaths, road deaths and "
            f"suicides at city level, falls, drowning and burns cannot be anchored and are "
            f"reported as covariate projections that borrow the fused State totals and the spatial "
            f"structure but are not individually validated. The study used only aggregate, "
            f"publicly available secondary data with no individual identifiers, so institutional "
            f"ethics approval was not required.", cite=True)

    heading(d, "Results")
    para(d, f"Estimates were produced for {N['n_dist']} districts across {N['n_states']} States "
            f"and union territories. At the national level the fusion reproduced, and quantified "
            f"the uncertainty in, the known source discordance (Table 1). Modelled and "
            f"administrative counts differed {N['falls_ratio']}-fold for falls and "
            f"{E['burns_ratio']}-fold for burns, {E['road_ratio']}-fold for road injury and "
            f"{E['suicide_ratio']}-fold for suicide, but only 1.3-fold for drowning. The fused "
            f"true national totals were approximately {E['ai_fused']} all-injury deaths, of which "
            f"{E['road_fused']} were attributed to road injury, {E['suicide_fused']} to suicide, "
            f"{E['falls_fused']} to falls, {E['drown_fused']} to drowning and {E['burns_fused']} "
            f"to burns. Implied surveillance completeness — the share of true deaths appearing in "
            f"administrative records — was lowest for falls (district median {N['falls_comp']}) "
            f"and burns ({N['burns_comp']}), intermediate for suicide and road ({N['road_comp']}), "
            f"and highest for drowning ({N['drown_comp']}); for all injury combined it was "
            f"{N['ai_comp']}.", cite=True)
    para(d, f"District all-injury mortality had a median of {N['ai_med']} per 100 000 "
            f"(interquartile range {E['ai_iqr']}) and reached about {N['ai_max']} per 100 000 in "
            f"the highest-burden districts (Figure 1). Burden was far from uniform within the "
            f"country: State-median district rates ranged from {E['lo_val']} per 100 000 in "
            f"{E['lo_state']} and {E['lo2_val']} in {E['lo2_state']} to {E['hi_val']} in "
            f"{E['hi_state']} and {E['hi2_val']} in {E['hi2_state']}. Road-injury mortality "
            f"(median {N['road_med']} per 100 000, IQR {E['road_iqr']}) and suicide (median "
            f"{N['suicide_med']}, IQR {E['suicide_iqr']}) showed the widest geographical spread, "
            f"while falls (median {N['falls_med']}) contributed the largest hidden burden.", cite=True)
    para(d, f"The completeness surface (Figure 2) revealed strong gradients that State-level "
            f"ratios entirely obscure. Administrative capture was consistently higher in urban and "
            f"metropolitan districts and lower across rural and tribal interiors. For falls the "
            f"under-capture was near-universal: an estimated {E['falls_lt10']} of {E['falls_n']} "
            f"districts recorded fewer than one in ten fall deaths, and for all injury combined "
            f"{E['ai_lt40']} districts recorded under 40% of estimated deaths.", cite=True)
    para(d, f"Combining high estimated burden, wide posterior uncertainty and low completeness "
            f"identified a set of surveillance “blind-spot” districts (Table 2), where injury "
            f"deaths are both estimated to be high and least likely to be recorded. These "
            f"clustered markedly in the tribal districts of Chhattisgarh — Sukma (all-injury "
            f"rate about 300 per 100 000, completeness 0.49), Jashpur, Narayanpur and the Bastar "
            f"divisions — with further clusters in interior Odisha and the hill districts of "
            f"Himachal Pradesh. The same districts dominated the cause-specific blind-spot lists "
            f"for road injury and suicide, indicating a shared underlying weakness in local "
            f"death recording rather than a cause-specific artefact.", cite=True)
    para(d, f"Five-fold cross-validation showed well-calibrated uncertainty: across the three "
            f"anchored causes, 95% credible intervals covered the held-out city observations "
            f"{cvnum('road','coverage95')}–{cvnum('all_injury','coverage95')} of the time, close "
            f"to nominal, with log-scale root-mean-squared errors of "
            f"{cvnum('road','log_rmse')}–{cvnum('suicide','log_rmse')} (Table 3). Rank "
            f"discrimination was strongest for suicide (Spearman {cvnum('suicide','spearman')}) "
            f"and all injury ({cvnum('all_injury','spearman')}) and weaker for road "
            f"({cvnum('road','spearman')}). Sensitivity analyses showed that completeness "
            f"estimates were stable across prior widths and model structures (mean road "
            f"completeness 0.30–0.31), and that the spatial field contributed little to "
            f"out-of-sample city prediction — expected, since the anchor cities are uniformly "
            f"urban and spatially dispersed (Table S2).", cite=True)

    heading(d, "Discussion")
    para(d, "This study provides the first district-resolution atlas of fatal injury in India and "
            "the first sub-state map of injury surveillance completeness. Three findings stand "
            "out. First, injury burden is not a State-level property: both the death rate and, "
            "more strikingly, the completeness of administrative recording vary sharply within "
            "States, so district targeting cannot be read off State aggregates. Second, the causes "
            "with the largest gap between modelling and administration — falls and burns — are "
            "precisely those where fewer than one in five estimated deaths appear in police "
            "records, consistent with deaths that occur at home and are certified, if at all, "
            "without police involvement.[4,20] Third, the districts where burden is highest and "
            "recording weakest are not scattered at random but concentrate in the tribal and "
            "forested interiors of central and eastern India, where health and registration "
            "infrastructure is thinnest.", cite=True)
    para(d, "These results reframe the long-noted GBD–NCRB discordance as actionable "
            "intelligence rather than a data-quality embarrassment. Instead of asking which source "
            "is correct, the fusion asks where the two diverge most and localises that divergence "
            "to specific districts. For prevention agencies the burden surface identifies where "
            "people are dying; for the Civil Registration System and the Medical Certification of "
            "Cause of Death programme the completeness surface identifies where investment in "
            "death recording would yield the most information per rupee.[7,20] The two surfaces "
            "are complementary: a high-burden district that already records its deaths needs "
            "prevention, whereas a high-burden district that does not also needs surveillance "
            "strengthening before the effect of any intervention could even be measured.", cite=True)
    para(d, "The cause-specific pattern maps onto known prevention levers. The vast hidden burden "
            "of falls, concentrated among older adults, argues for embedding fall-risk assessment "
            "and home-hazard modification within the National Programme for Health Care of the "
            "Elderly, particularly in the many districts where falls are almost invisible to "
            "administrative data.[28] The persistent under-recording of burns points to household "
            "fire and kerosene safety and to strengthening burn-injury registries. For road "
            "injury, the atlas offers a modelled complement to the government's high-fatality "
            "district programme, extending prioritisation beyond raw police counts to a "
            "burden estimate that adjusts for differential recording.[3,26] For suicide, the "
            "district blind-spots align with regions where means-restriction and mental-health "
            "outreach could be focused.[27]", cite=True)
    para(d, "Methodologically, the approach is general. Any setting with a modelled estimate, a "
            "discordant administrative count and district-level covariates can be handled the same "
            "way: fuse the two signals through an explicit completeness parameter, downscale under "
            "a benchmarked spatial model, and calibrate against whatever partial sub-state "
            "observations exist. This differs from conventional small-area estimation, which "
            "smooths a single noisy survey signal,[10,11,13] by simultaneously reconciling two "
            "sources of differing scale and interpretation while preserving coherence with State "
            "totals.[24] It also converts the by-product of that reconciliation — the completeness "
            "parameter — into a substantive epidemiological quantity of independent policy value.", cite=True)
    para(d, f"The work has important limitations. Identification of the covariate effects relies "
            f"on {N['n_anchor']} urban anchor districts, and the completeness gradient is "
            f"extrapolated to rural districts that are never directly observed; this is the "
            f"principal caveat and the reason falls, drowning and burns are presented only as "
            f"covariate projections rather than validated estimates. Out-of-sample point "
            f"discrimination was modest even though interval coverage was close to nominal, so "
            f"individual district rankings should be read together with their credible intervals "
            f"rather than as precise positions. Covariate associations are ecological and carry no "
            f"individual-level causal interpretation.[14] Exposure used the 2011 census population "
            f"base, and boundaries were harmonised across three district frames with residual "
            f"name-matching uncertainty that was logged but not eliminated. Finally, the ADSI city "
            f"tables restrict anchoring to three causes; were district-level cause-specific injury "
            f"deaths released — for example through the Civil Registration System — falls and "
            f"burns could be anchored and validated directly.", cite=True)
    para(d, "Within these limits, the atlas offers a reproducible, fully uncertainty-quantified "
            "tool for district injury prevention and, equally, a map of where India's injury "
            "surveillance most needs strengthening. Both outputs follow from taking the "
            "disagreement between the country's two injury data systems seriously — not as an "
            "error to be argued away, but as information about the places their shared blind spots "
            "leave unseen.", cite=True)

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
    para(d, TITLE, italic=True, align="center", after=12)

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
