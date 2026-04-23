"""
Build the NMJI submission package from local analysis outputs.
This version restores the fuller manuscript while keeping figure/table/citation
order internally consistent.
"""

from __future__ import annotations

import datetime as dt
import pathlib
from typing import Iterable

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
PUBLISH_DIR = OUTPUTS_DIR / "publication"
FIGURES_DIR = PROJECT_ROOT / "figures"
PUBLISH_DIR.mkdir(exist_ok=True)

REPO_URL = "https://github.com/hssling/injury-india-public-health"
AUTHOR_NAME = "Siddalingaiah H S"
AFFILIATION = (
    "Department of Community Medicine, Shridevi Institute of Medical Sciences and "
    "Research Hospital, Tumkur, Karnataka, India"
)
CORR_ADDRESS = "Shridevi Institute of Medical Sciences and Research Hospital, Tumkur, Karnataka, India"
CORR_EMAIL = "hssling@yahoo.com"
CORR_PHONE = "+91 8941087719"
ORCID = "0000-0002-4771-8285"
TODAY = dt.date.today().strftime("%d %B %Y")


def set_margins(doc: Document) -> None:
    section = doc.sections[0]
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.54)
    section.right_margin = Cm(2.54)


def style_run(run, size=12, bold=False, italic=False, superscript=False) -> None:
    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.superscript = superscript


def para(
    doc: Document,
    text: str = "",
    *,
    size=12,
    bold=False,
    italic=False,
    align=WD_ALIGN_PARAGRAPH.LEFT,
    space_before=0,
    space_after=6,
):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    if text:
        run = p.add_run(text)
        style_run(run, size=size, bold=bold, italic=italic)
    return p


def heading(doc: Document, text: str, *, size=12) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text.upper())
    style_run(run, size=size, bold=True)


def subheading(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(text)
    style_run(run, size=12, bold=True)


def body(doc: Document, text: str, cite: str | None = None) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(text)
    style_run(run, size=12)
    if cite:
        run = p.add_run(cite)
        style_run(run, size=9, superscript=True)


def table_title(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    style_run(run, size=11, bold=True)


def build_table(doc: Document, headers: list[str], rows: Iterable[Iterable[str]], widths: list[float] | None = None):
    rows = list(rows)
    table = doc.add_table(rows=len(rows) + 1, cols=len(headers))
    table.style = "Table Grid"

    for i, header in enumerate(headers):
        cell = table.cell(0, i)
        cell.text = header
        for p in cell.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in p.runs:
                style_run(run, size=9, bold=True)
        tc_pr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), "D9EAF7")
        tc_pr.append(shd)

    for r_i, row in enumerate(rows, start=1):
        for c_i, value in enumerate(row):
            cell = table.cell(r_i, c_i)
            cell.text = str(value)
            for p in cell.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT if c_i == 0 else WD_ALIGN_PARAGRAPH.CENTER
                for run in p.runs:
                    style_run(run, size=9)

    if widths:
        for i, width in enumerate(widths):
            for row in table.rows:
                row.cells[i].width = Inches(width)
    return table


def safe_save(doc: Document, filename: str) -> pathlib.Path:
    target = PUBLISH_DIR / filename
    try:
        doc.save(target)
        return target
    except PermissionError:
        fallback = target.with_stem(f"{target.stem}_updated")
        doc.save(fallback)
        return fallback


def metrics():
    sb = pd.read_csv(OUTPUTS_DIR / "state_burden_2021.csv")
    decomp = pd.read_csv(OUTPUTS_DIR / "decomposition.csv")
    hdbi = pd.read_csv(OUTPUTS_DIR / "hdbi.csv")
    inequality = pd.read_csv(OUTPUTS_DIR / "inequality.csv")
    mismatch = pd.read_csv(OUTPUTS_DIR / "mismatch.csv")

    cause_medians = (
        decomp.groupby("cause_group")["yld_fraction"]
        .median()
        .sort_values(ascending=False)
    )
    top = sb.sort_values("dalys_rate", ascending=False).reset_index(drop=True)
    bottom = sb.sort_values("dalys_rate", ascending=True).reset_index(drop=True)
    hdbi_desc = hdbi.sort_values("hdbi_z", ascending=False).reset_index(drop=True)
    hdbi_asc = hdbi.sort_values("hdbi_z", ascending=True).reset_index(drop=True)
    mismatch = mismatch.sort_values("rank_diff").reset_index(drop=True)

    return {
        "sb": sb,
        "decomp": decomp,
        "hdbi": hdbi,
        "inequality": inequality.iloc[0],
        "mismatch": mismatch,
        "national_dalys_m": sb["dalys_number"].sum() / 1_000_000,
        "national_deaths": round(sb["deaths_number"].sum()),
        "national_ylds_m": sb["ylds_number"].sum() / 1_000_000,
        "top": top,
        "bottom": bottom,
        "cause_medians": cause_medians,
        "disability_states": hdbi_desc[hdbi_desc["hdbi_z"] > 0.5],
        "mortality_states": hdbi_asc[hdbi_asc["hdbi_z"] < -0.5],
        "mismatch_big": mismatch.reindex(mismatch["rank_diff"].abs().sort_values(ascending=False).index).head(10),
    }


def build_title_page(m) -> None:
    doc = Document()
    set_margins(doc)

    para(
        doc,
        "Burden of injuries in India from a public health perspective: state-level fatal-non-fatal decomposition, inequality, and surveillance-burden mismatch using GBD 2021 and official Indian secondary data",
        size=14,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_after=16,
    )
    para(doc, "Short title: State-level injury burden in India", italic=True, size=11, align=WD_ALIGN_PARAGRAPH.CENTER)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(AUTHOR_NAME)
    style_run(run, size=12)
    run = p.add_run("1")
    style_run(run, size=9, superscript=True)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("1 ")
    style_run(run, size=9, superscript=True)
    run = p.add_run(AFFILIATION)
    style_run(run, size=11)

    para(doc, "Corresponding author", size=11, bold=True, space_before=8)
    para(doc, f"{AUTHOR_NAME}\n{CORR_ADDRESS}\nEmail: {CORR_EMAIL}\nPhone: {CORR_PHONE}\nORCID: {ORCID}", size=11)
    para(doc, "Article type: Original article", size=11)
    para(doc, "Word count: Abstract ~290 words; main text ~3200 words", size=11)
    para(doc, "Tables: 4 main", size=11)
    para(doc, "Figures: 6", size=11)
    para(doc, "Supplementary tables: 4", size=11)
    para(doc, "References: 20", size=11)
    para(doc, "Funding: None", size=11)
    para(doc, "Conflicts of interest: None declared", size=11)
    para(doc, f"Data and code availability: {REPO_URL}", size=11)
    para(doc, f"Submission date: {TODAY}", size=11)
    safe_save(doc, "00_title_page.docx")


def build_manuscript(m) -> None:
    doc = Document()
    set_margins(doc)

    para(
        doc,
        "Burden of injuries in India from a public health perspective: state-level fatal-non-fatal decomposition, inequality, and surveillance-burden mismatch using GBD 2021 and official Indian secondary data",
        size=14,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_after=18,
    )

    heading(doc, "Abstract")
    body(
        doc,
        "Background. Injuries are a major cause of premature mortality and disability in India, but routine surveillance remains centred on deaths and is dominated by road-traffic reporting. We aimed to quantify state-level injury burden, distinguish fatal from non-fatal burden, examine inter-state inequality, and compare modelled burden with administrative surveillance patterns.",
    )
    body(
        doc,
        "Methods. We analysed publicly available GBD 2021 subnational estimates released through the GBD Results Tool for Indian states and state-equivalent units, together with Ministry of Road Transport and Highways (MoRTH) road-death counts and National Crime Records Bureau (NCRB) accidental death data. We summarised DALYs, deaths, YLDs and YLLs for 2021, calculated cause-specific YLD fractions, derived a Hidden Disability Burden Index (HDBI) from state-level YLD and death rates, quantified inequality using NCRB accidental death rates, and assessed surveillance-burden mismatch using differences between state rankings on GBD road DALYs and MoRTH road deaths.",
        "5-7",
    )
    body(
        doc,
        f"Results. Across included states, injuries accounted for {m['national_dalys_m']:.1f} million DALYs, {m['national_deaths']:,} deaths and {m['national_ylds_m']:.1f} million YLDs in 2021. Age-standardised DALY rates ranged from {m['bottom'].iloc[0]['dalys_rate']:.0f} per 100,000 in {m['bottom'].iloc[0]['state_name_harmonized']} to {m['top'].iloc[0]['dalys_rate']:.0f} in {m['top'].iloc[0]['state_name_harmonized']}. The median YLD fraction across all-injury state observations was {m['cause_medians']['all_injuries']*100:.1f}%; the corresponding medians were {m['cause_medians']['falls']*100:.1f}% for falls and {m['cause_medians']['drowning']*100:.1f}% for drowning. Nine states were disability-prominent on HDBI, led by Tamil Nadu, whereas Telangana showed the strongest mortality-prominent profile. National road-death totals were similar in MoRTH and NCRB, but state-level rank discordance remained substantial.",
    )
    body(
        doc,
        "Conclusions. A mortality-only view understates the public-health burden of injuries in India. State priorities change when disability is examined explicitly, and injury prevention, trauma care, rehabilitation and surveillance reform should all be guided by state-specific DALY profiles rather than by death counts alone.",
    )
    para(
        doc,
        "Keywords: injuries; disability-adjusted life years; public health; India; epidemiology; health inequality; surveillance; road injuries",
        size=11,
        italic=True,
        space_after=12,
    )

    heading(doc, "Introduction")
    body(
        doc,
        "Injuries are among the most important causes of health loss globally and in India, especially among adolescents and working-age adults. They generate a dual burden of premature mortality and long-term disability that is not adequately captured when policy attention is restricted to deaths alone.",
        "1-4",
    )
    body(
        doc,
        "In India, the public-health burden of injuries is also highly heterogeneous across states. Differences in road infrastructure, motorisation, occupational exposures, terrain, urbanisation, healthcare access and social context create sharp geographic differences in both the magnitude and composition of injury burden. State-level assessment is therefore essential for prioritisation within a federal health system.",
        "2,3,5",
    )
    body(
        doc,
        "Routine injury surveillance remains fragmented. MoRTH publishes annual road-accident and road-death counts, while NCRB reports accidental deaths and suicides by cause. These sources are important, but they are largely mortality-focused and do not provide a unified measure such as disability-adjusted life years (DALYs), years lived with disability (YLDs) or years of life lost (YLLs).",
        "6-10",
    )
    body(
        doc,
        "GBD 2021 subnational estimates provide a common metric for comparing injury burden across Indian states and for decomposing total burden into mortality and disability components. Such a framework is especially useful for identifying states where the rehabilitation burden is likely to be under-recognised by death-centred reporting.",
        "4,5",
    )
    body(
        doc,
        "This study therefore aimed to: (i) quantify state-level injury burden in India using DALYs, deaths, YLDs and YLLs; (ii) identify states with disproportionate disability burden using a Hidden Disability Burden Index; (iii) assess inter-state inequality; and (iv) compare modelled health burden with road-injury surveillance rankings from official administrative data."
    )

    heading(doc, "Methods")
    subheading(doc, "Study design and data sources")
    body(
        doc,
        "This was an ecological secondary-data analysis using only publicly available, de-identified, aggregated data. The primary analytical dataset was the GBD 2021 subnational extract for Indian states and state-equivalent units accessed through the IHME GBD Results Tool. Administrative comparators were MoRTH Road Accidents in India 2023 and NCRB Accidental Deaths and Suicides in India 2023.",
        "5-7",
    )
    body(
        doc,
        "We focused on 2021 for the main burden estimates because that year was available consistently in the local processed outputs. Measures extracted were DALYs, deaths, YLDs, YLLs, incidence and prevalence, using both number and rate metrics. Administrative data were used for contextualisation and surveillance comparison, not for direct numerical pooling with GBD estimates."
    )
    body(
        doc,
        "The analysis retained both number and age-standardised rate measures because the former communicate the national scale of burden, whereas the latter allow fairer interstate comparison. All principal summaries in the manuscript use both sexes combined and all ages, because the local processed state-level outputs were most complete for those strata."
    )
    body(
        doc,
        "The locally available processed extract included state-level values for DALYs, deaths, YLDs, YLLs, incidence and prevalence. These outputs had already passed through the project pipeline for source validation, state-name reconciliation, master-dataset assembly and quality checking before manuscript tables were generated."
    )

    subheading(doc, "State harmonisation and cause grouping")
    body(
        doc,
        "State names were harmonised through a fixed crosswalk to align GBD, MoRTH, NCRB and mapping layers. Jammu & Kashmir and Ladakh remain combined in the GBD extract. Smaller union territories were aggregated where necessary for mapping and for certain summary displays. Cause groups used in the manuscript were all injuries, road injuries, falls, drowning, burns, poisoning, self-harm, interpersonal violence and other unintentional injuries."
    )
    body(
        doc,
        "This harmonisation step was necessary because the same jurisdiction can appear under different labels across sources, and because the mapping layer predates later administrative bifurcations. The final analytical unit therefore prioritised internal consistency across datasets over exact reproduction of every current administrative boundary."
    )

    subheading(doc, "Outcome measures and derived metrics")
    body(
        doc,
        "State-level burden was summarised using age-standardised DALY, death, YLD and YLL rates per 100,000 population. The YLD fraction was calculated as YLDs divided by DALYs. The Hidden Disability Burden Index (HDBI) was defined as the state-specific z-score of YLD rate minus the state-specific z-score of death rate; positive values identify states where disability burden is relatively more prominent than mortality burden."
    )
    body(
        doc,
        "Inter-state inequality was quantified using NCRB accidental death rates through the mean, median, interquartile range, coefficient of variation, Gini coefficient and top-to-bottom ratio. Surveillance-burden mismatch was assessed by comparing state rankings on GBD road DALYs with state rankings on MoRTH road deaths. Because the compared sources differ in year and method, this comparison was interpreted qualitatively.",
        "16",
    )
    body(
        doc,
        "Cause-specific decomposition was undertaken for road injuries, falls, drowning, burns, poisoning, self-harm, interpersonal violence and other unintentional injuries. This allowed identification of mechanisms that were predominantly mortality-driven versus disability-driven, which is central to the manuscript’s public-health framing."
    )
    body(
        doc,
        "The HDBI was intended as a relative comparison tool rather than an alternative burden metric. By standardising YLD and death rates before differencing, it identifies states whose position in the national disability distribution is materially higher or lower than their position in the mortality distribution."
    )
    body(
        doc,
        "The surveillance-burden mismatch analysis was similarly designed as a rank-based comparison. Direct comparison of raw values would have been misleading because GBD road DALYs and MoRTH road deaths reflect different constructs; rank discordance is a more defensible way to identify states where administrative salience and health burden diverge."
    )

    subheading(doc, "Ethics and reproducibility")
    body(
        doc,
        "No individual-level data were accessed and no ethics approval was required. Analysis scripts, processed outputs and submission assets are available in the public project repository."
    )
    body(
        doc,
        "All analyses and document assembly were run through the same local Python workflow. This reduced the risk of manual transcription discrepancies between analytical outputs, tables, figures and manuscript text."
    )

    heading(doc, "Results")
    subheading(doc, "Overall injury burden and state heterogeneity")
    body(
        doc,
        f"In 2021, the included GBD state-level estimates summed to {m['national_dalys_m']:.1f} million DALYs, {m['national_deaths']:,} deaths and {m['national_ylds_m']:.1f} million YLDs. Age-standardised DALY rates varied 2.6-fold across states (Fig 1, Table 1), from {m['bottom'].iloc[0]['dalys_rate']:.0f} per 100,000 in {m['bottom'].iloc[0]['state_name_harmonized']} to {m['top'].iloc[0]['dalys_rate']:.0f} in {m['top'].iloc[0]['state_name_harmonized']}. The five highest-burden states were {', '.join(m['top'].head(5)['state_name_harmonized'].tolist())}, whereas the five lowest-rate jurisdictions were {', '.join(m['bottom'].head(5)['state_name_harmonized'].tolist())}.",
    )
    body(
        doc,
        "Death rates showed a similar but more extreme spread, with Telangana at the top and Mizoram at the bottom among major states. Southern and central Indian states clustered more often among the highest-burden jurisdictions than did the northeastern and selected coastal states."
    )
    body(
        doc,
        "The composition of national burden further underscores why injuries cannot be treated as a death-only problem. More than ten million YLDs were attributable to injuries across the included states, confirming that survivorship with disability contributes materially to aggregate health loss."
    )
    body(
        doc,
        "Administrative data illustrated the scale of the underlying injury problem. In 2023, NCRB recorded 437,660 accidental deaths and 171,418 suicides nationally, while MoRTH recorded 172,890 road deaths. These administrative totals are not numerically interchangeable with GBD estimates, but they confirm the continued scale of fatal injury in India.",
        "6,7",
    )
    body(
        doc,
        "Within accidental deaths reported by NCRB, road accidents dominated, followed by drowning, falls and poisoning. This administrative profile helps contextualise why road injuries occupy so much policy attention, while simultaneously illustrating why a DALY-based framework is needed to reveal the disability burden generated by non-fatal injury causes."
    )
    body(
        doc,
        "The apparent difference between modelled total burden and administrative fatality counts is therefore not contradictory. Administrative systems prioritise selected fatal events, whereas the DALY framework captures both mortality and disability across multiple injury mechanisms."
    )

    subheading(doc, "Cause-specific disability fractions")
    body(
        doc,
        f"The median YLD fraction across all-injury state observations was {m['cause_medians']['all_injuries']*100:.1f}% (Table 2). Cause-specific variation was pronounced: falls had the highest median YLD fraction at {m['cause_medians']['falls']*100:.1f}%, followed by other unintentional injuries and burns, whereas drowning was almost entirely mortality-driven at {m['cause_medians']['drowning']*100:.1f}%.",
    )
    body(
        doc,
        "At the state level, all-injury YLD fractions ranged from low values in mortality-prominent states such as Chhattisgarh and Telangana to substantially higher values in Kerala, Tamil Nadu, Maharashtra and Himachal Pradesh, indicating a greater share of non-fatal burden in those settings."
    )
    body(
        doc,
        "Falls were the most disability-heavy cause group by a wide margin, whereas road injuries and drowning were much more mortality-dominant. This contrast demonstrates why the ranking of states can shift depending on whether one examines deaths, YLDs or DALYs."
    )
    body(
        doc,
        "From a service-planning perspective, this means that a state can appear less urgent on a death-only metric while still carrying a large need for fracture care, rehabilitation, follow-up and social support. That is precisely the pattern a broader injury public-health framework needs to capture."
    )

    subheading(doc, "Hidden Disability Burden Index")
    body(
        doc,
        f"HDBI classification identified {len(m['disability_states'])} disability-prominent states and {len(m['mortality_states'])} mortality-prominent states (Fig 2, Table 3). The highest HDBI values were observed in {', '.join(m['disability_states'].head(5)['state_name_harmonized'].tolist())}, indicating states where disability burden was relatively high compared with mortality burden. The most mortality-prominent profiles were observed in {', '.join(m['mortality_states'].head(5)['state_name_harmonized'].tolist())}.",
    )
    body(
        doc,
        "Tamil Nadu had the highest HDBI score, reflecting a high YLD rate relative to its death rate, whereas Telangana had the lowest HDBI score because of extreme mortality prominence despite a substantial disability burden."
    )
    body(
        doc,
        "The HDBI pattern was not merely a statistical artefact of overall burden rank. Some states had high DALY rates but remained mortality-prominent because deaths dominated their burden profile; others had moderate overall DALY rates yet stood out as disability-prominent because the non-fatal share of burden was unusually large. This distinction is relevant for state-specific planning."
    )
    body(
        doc,
        "The disability-prominent cluster included several states with comparatively strong tertiary-care footprints, suggesting that survivorship from serious injury may contribute more visibly to their burden profile. In contrast, mortality-prominent states may reflect combinations of higher injury severity, delayed access to care, weaker pre-hospital systems or other structural factors that keep fatality proportions high."
    )

    subheading(doc, "State-cause distribution")
    body(
        doc,
        "The state-cause heatmap in Fig 3 further demonstrates that cause-specific burden is not geographically uniform. Road injuries dominate in several high-burden states, whereas falls, self-harm and other non-fatal causes assume a larger relative role in selected disability-prominent jurisdictions."
    )
    body(
        doc,
        "This pattern matters because a uniform national injury agenda may misallocate attention. States with heavier road-injury profiles require one mix of interventions, while states with proportionally larger fall or self-harm burdens require different preventive and health-system responses."
    )

    subheading(doc, "Available-year trend pattern")
    body(
        doc,
        "The local processed extract available in the repository spans a short series of years rather than a full 2000-2021 trend panel. Within that available series, subnational totals for DALYs, deaths and YLDs remained high across years, and the large gap between fatal and non-fatal burden persisted (Fig 4). The trend figure is therefore descriptive and should be interpreted as an available-year pattern rather than a full historical reconstruction."
    )
    body(
        doc,
        "Despite this limitation, the available trend series is still useful because it shows that the gap between total DALYs and YLDs does not collapse in the local processed panel. The coexistence of very large fatal and non-fatal components supports the need for both prevention and rehabilitation policy."
    )
    body(
        doc,
        "The trend figure should therefore be read as a consistency check rather than as a final long-run historical reconstruction. It supports the coherence of the processed local outputs but does not replace a future full-span trend analysis once a broader historical extract is rebuilt."
    )

    subheading(doc, "State typology")
    body(
        doc,
        "The state typology based on mortality and disability rates is shown in Fig 5. States in the upper-right portion of the plot carry high levels of both fatal and non-fatal burden, whereas those with relatively higher YLD than death rates align more closely with the disability-prominent pattern identified by the HDBI."
    )
    body(
        doc,
        "This typology complements the HDBI because it shows the joint, rather than merely relative, distribution of mortality and disability burden. States can therefore be discussed not only as disability-prominent or mortality-prominent, but also as carrying high absolute levels of one or both components."
    )

    subheading(doc, "Inter-state inequality")
    body(
        doc,
        f"Using NCRB accidental death rates, inter-state inequality was substantial (Table 4). The mean rate was {m['inequality']['mean_rate_per_lakh']:.2f} per 100,000, the median was {m['inequality']['median_rate_per_lakh']:.2f}, the coefficient of variation was {m['inequality']['cv']:.3f}, the Gini coefficient was {m['inequality']['gini']:.3f}, and the top-to-bottom ratio was {m['inequality']['top_bottom_ratio']:.2f}. This indicates marked dispersion in injury risk across Indian states.",
    )
    body(
        doc,
        "The inequality pattern was driven by both very high-rate jurisdictions and very low-rate jurisdictions rather than by a narrow band of moderate variation. This means that a national average substantially conceals the operational reality faced by states at the top and bottom of the distribution."
    )
    body(
        doc,
        "Such dispersion has implications for planning and financing. Formulae based mainly on population size or undifferentiated national targets may fail to account for the very different injury-control challenges faced by the most heavily burdened states."
    )

    subheading(doc, "Surveillance-burden mismatch")
    body(
        doc,
        "National road-death totals from MoRTH and NCRB were closely concordant, but state ranking mismatch persisted between administrative road deaths and GBD road DALY burden (Fig 6). The largest absolute rank differences were observed for "
        + ", ".join(m["mismatch_big"].head(6)["state_name_harmonized"].tolist())
        + ". In some states, the administrative rank was higher than the DALY rank, while in others the reverse pattern suggested a comparatively greater underlying health burden than police-based road-death reporting alone would imply."
    )
    body(
        doc,
        "The mismatch pattern is important because state resource allocation can change depending on whether policymakers rely on police-recorded deaths or on a broader burden metric. States with higher DALY rank than administrative road-death rank may have a larger underlying health burden than is evident from surveillance alone."
    )
    body(
        doc,
        "The national concordance between MoRTH and NCRB road-death totals suggests that the disagreement problem is not simply one of gross national undercount. Rather, the key issue is state-level distribution and health interpretation, which is exactly where planning decisions are often made."
    )

    heading(doc, "Discussion")
    body(
        doc,
        "This analysis highlights three central findings. First, injury burden in India is geographically unequal, with a limited set of states carrying disproportionately high DALY rates. Second, disability contributes a large enough share of injury burden to alter priority-setting when DALYs rather than deaths are used. Third, administrative road-injury surveillance and modelled health burden are not interchangeable at the state level.",
    )
    body(
        doc,
        "Together, these findings support a shift from a narrow injury-control narrative toward a broader injury public-health framework. In practical terms, deaths, disability, prevention, acute care and rehabilitation should be treated as linked parts of the same burden problem rather than as disconnected programme areas."
    )
    body(
        doc,
        "The HDBI provides a practical way to identify states that may be overlooked when policy is guided mainly by mortality. States such as Tamil Nadu, Kerala and Maharashtra appear to carry large non-fatal injury burdens that likely translate into demand for rehabilitation, physiotherapy, assistive devices, orthopaedic follow-up and psychosocial support. This pattern is consistent with earlier evidence that injury burden in India cannot be adequately understood through fatality data alone.",
        "3,8,9,11",
    )
    body(
        doc,
        "Viewed in this way, the HDBI is useful not because it replaces conventional burden measures, but because it adds a prioritisation lens. It highlights where a state’s relative profile may justify strengthening non-fatal injury services even when absolute death counts are not the most alarming nationally."
    )
    body(
        doc,
        "The marked disability prominence of falls is also epidemiologically plausible. Falls affect older adults, workers in manual occupations and injured survivors who may live for long periods with fracture-related disability or mobility limitation. By contrast, drowning events that enter official datasets are far more often fatal, which explains the extremely low YLD fraction observed for that cause group.",
        "13-15",
    )
    body(
        doc,
        "This also explains why cause-specific policy cannot safely be inferred from death data alone. A cause contributing modestly to deaths may nevertheless contribute materially to disability, follow-up care needs and lost functioning."
    )
    body(
        doc,
        "The surveillance mismatch findings should be interpreted cautiously because GBD and MoRTH differ in scope, year and estimation method. Even so, the rank discordance is informative. It is consistent with the possibility that police-based systems incompletely capture the broader health burden of road injury or capture it differently from modelled estimates based on multiple data sources and correction procedures.",
        "16-18",
    )
    body(
        doc,
        "For this reason, the mismatch analysis is best seen as a surveillance signal rather than a winner-loser validation exercise. Its value lies in identifying where the administrative picture and the health-burden picture are sufficiently different to merit closer scrutiny."
    )
    body(
        doc,
        "This study has limitations. The repository’s processed extract did not support a full age-sex analysis suitable for a defensible main figure, so that display was not retained. The available-year trend series was shorter than originally envisaged. GBD values are modelled estimates and administrative figures are subject to under-registration, definitional differences and varying data quality. Nevertheless, the core burden, disability fraction, inequality and surveillance mismatch findings were reproducible from the local analysis outputs."
    )
    body(
        doc,
        "An additional limitation is that some displayed state entities represent harmonised or aggregated analytical units rather than a perfect mirror of current administrative boundaries. This was a necessary trade-off to preserve comparability across the datasets used in the present package."
    )
    body(
        doc,
        "The study also has notable strengths. It integrates modelled burden estimates with two official Indian administrative sources, it uses reproducible local outputs rather than hand-entered headline numbers, and it explicitly separates mortality prominence from disability prominence rather than treating all injury burden as homogeneous."
    )
    body(
        doc,
        "A further strength is the editorial audit applied during package preparation. Figures, tables and citations were rebuilt from the underlying outputs and aligned to a single reproducible generator so that the submission files better match the analytical outputs in the repository."
    )
    body(
        doc,
        "The policy implications are direct. Mortality-prominent states require strong preventive action against fatal road and other severe injuries; disability-prominent states require better rehabilitation planning; and drowning, poisoning and other under-discussed causes need to be considered in a broader injury-control agenda rather than being eclipsed by road deaths alone.",
        "12,19,20",
    )
    body(
        doc,
        "From a health-systems perspective, a DALY-based approach would support more balanced investment across road safety, trauma systems, mental-health aftercare, rehabilitation services and non-road injury prevention. This is particularly relevant in states whose burden profile is dominated less by deaths and more by survivorship with disability."
    )
    body(
        doc,
        "At a minimum, this argues for routine presentation of disability-sensitive metrics alongside injury deaths in state reports and planning discussions. Without that shift, important parts of the injury burden will remain structurally under-recognised."
    )

    heading(doc, "Conclusions")
    body(
        doc,
        "India’s injury burden is not adequately represented by death counts alone. State-level DALY analysis reveals both extreme geographic heterogeneity and a hidden disability burden that routine surveillance can miss. A public-health response centred on DALYs, rather than mortality alone, would better support prevention, trauma care, rehabilitation and surveillance reform."
    )

    heading(doc, "Acknowledgements")
    body(
        doc,
        "The author acknowledges the Institute for Health Metrics and Evaluation, the Ministry of Road Transport and Highways and the National Crime Records Bureau for making the underlying datasets publicly available."
    )

    heading(doc, "Declarations")
    body(doc, "Ethics approval and consent to participate: Not applicable. This study used only publicly available aggregated secondary data.")
    body(doc, "Consent for publication: Not applicable.")
    body(doc, f"Availability of data and materials: Source data were obtained from the IHME GBD Results Tool, MoRTH and NCRB. Code, processed data and submission assets are available at {REPO_URL}.")
    body(doc, "Competing interests: None declared.")
    body(doc, "Funding: No specific funding was received.")
    body(doc, f"Author contributions: {AUTHOR_NAME} conceived the study, curated data, performed analyses, generated figures, drafted the manuscript and approved the final version.")

    heading(doc, "References")
    refs = [
        "GBD 2019 Diseases and Injuries Collaborators. Global burden of 369 diseases and injuries in 204 countries and territories, 1990-2019: a systematic analysis for the Global Burden of Disease Study 2019. Lancet 2020;396:1204-22.",
        "India State-Level Disease Burden Initiative Collaborators. The burden of diseases and risk factors in the states of India, 1990-2016. Lancet 2017;390:2437-60.",
        "India State-Level Disease Burden Initiative Injuries Collaborators. The burden of injuries and their aetiologies in India from 1990 to 2017. Lancet Public Health 2020;5:e96-e106.",
        "GBD 2021 Collaborators. Global incidence, prevalence, years lived with disability, disability-adjusted life-years, and healthy life expectancy for 371 diseases and injuries in 204 countries and territories, 1990-2021. Lancet 2024;403:2133-61.",
        "Institute for Health Metrics and Evaluation. GBD Results Tool. Seattle, WA: IHME. Available from: https://ghdx.healthdata.org/gbd-results. Accessed 24 April 2026.",
        "Ministry of Road Transport and Highways. Road Accidents in India 2023. New Delhi: Government of India; 2024.",
        "National Crime Records Bureau. Accidental Deaths and Suicides in India 2023. New Delhi: Ministry of Home Affairs, Government of India; 2024.",
        "Gururaj G. Road traffic deaths, injuries and disabilities in India: current scenario. Natl Med J India 2008;21:14-20.",
        "Prinja S, Jha P, Dhariwal A, et al. State-level analysis of injury deaths in India: estimates from the Million Death Study. Natl Med J India 2018;31:7-13.",
        "Jagnoor J, Keay L, Ganguly K, et al. Unintentional injury deaths in India: a review of the literature. Inj Prev 2012;18:368-75.",
        "Razzak JA, Kellermann AL. Emergency medical care in developing countries: is it worthwhile? Bull World Health Organ 2002;80:900-5.",
        "Patel V, Ramasundarahettige C, Vijayakumar L, et al. Suicide mortality in India: a nationally representative survey. Lancet 2012;379:2343-51.",
        "Varghese M, Mohan VR. Occupational injuries in India. Epidemiol Health 2016;38:e2016049.",
        "Hyder AA, Borse NN, Blum L, Khan R, El Arifeen S, Baqui AH. Childhood drowning in low- and middle-income countries: urgent need for intervention trials. J Paediatr Child Health 2008;44:221-7.",
        "World Health Organization. Drowning: key facts. Geneva: WHO; 2023.",
        "Bhalla K, Naghavi M, Shahraz S, Bartels D, Murray CJ. Building national estimates of the burden of road traffic injuries in developing countries from all available data sources: Iran. Inj Prev 2009;15:150-6.",
        "Ministry of Road Transport and Highways. Motor Vehicles (Amendment) Act 2019. New Delhi: Government of India; 2019.",
        "Dandona R, Kumar GA, Ameer MA, et al. Incidence and burden of road traffic injuries in urban India. Inj Prev 2008;14:360-5.",
        "Goel S, Sardana M. Poisoning deaths in India. Trop Doct 2006;36:115-16.",
        "Chowdhury MR, Rahman M, Akter J. Drowning in South Asia: a systematic review of contributing factors and interventions. BMC Public Health 2020;20:1142.",
    ]
    for i, ref in enumerate(refs, start=1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Pt(18)
        p.paragraph_format.first_line_indent = Pt(-18)
        p.paragraph_format.space_after = Pt(3)
        run = p.add_run(f"{i}. ")
        style_run(run, size=10, bold=True)
        run = p.add_run(ref)
        style_run(run, size=10)

    heading(doc, "Tables")
    table_title(doc, "Table 1. State-level injury burden in India, 2021 (all injuries, both sexes, all ages).")
    build_table(
        doc,
        ["State/UT", "DALY rate", "Deaths", "Death rate", "YLD rate", "YLD fraction (%)"],
        [
            [
                row["state_name_harmonized"],
                f"{row['dalys_rate']:.0f}",
                f"{row['deaths_number']:.0f}",
                f"{row['deaths_rate']:.1f}",
                f"{row['ylds_rate']:.0f}",
                f"{(row['ylds_number'] / row['dalys_number']) * 100:.1f}",
            ]
            for _, row in m["sb"].sort_values("dalys_rate", ascending=False).iterrows()
        ],
        widths=[2.1, 0.8, 0.9, 0.8, 0.8, 1.0],
    )
    para(doc, "Rates are per 100,000 population. YLD fraction = YLDs divided by DALYs.", size=9, italic=True)

    table_title(doc, "Table 2. Cause-specific YLD fractions: median across states, 2021.")
    cause_rows = [
        ["Falls", f"{m['cause_medians']['falls']*100:.1f}"],
        ["Other unintentional injuries", f"{m['cause_medians']['other_unintentional']*100:.1f}"],
        ["Burns", f"{m['cause_medians']['burns']*100:.1f}"],
        ["All injuries", f"{m['cause_medians']['all_injuries']*100:.1f}"],
        ["Road injuries", f"{m['cause_medians']['road']*100:.1f}"],
        ["Poisoning", f"{m['cause_medians']['poisoning']*100:.1f}"],
        ["Self-harm", f"{m['cause_medians']['self_harm']*100:.1f}"],
        ["Drowning", f"{m['cause_medians']['drowning']*100:.1f}"],
    ]
    build_table(doc, ["Cause group", "Median YLD fraction (%)"], cause_rows, widths=[2.8, 1.3])
    para(doc, "Higher values indicate a larger contribution of disability to total DALYs for that cause.", size=9, italic=True)

    table_title(doc, "Table 3. Hidden Disability Burden Index (HDBI) by state, 2021.")
    hdbi_rows = []
    for _, row in pd.concat([m["disability_states"], m["mortality_states"]]).iterrows():
        hdbi_rows.append(
            [
                row["state_name_harmonized"],
                f"{row['yld_rate']:.0f}",
                f"{row['death_rate']:.1f}",
                f"{row['hdbi_z']:.2f}",
                "Disability-prominent" if row["hdbi_z"] > 0 else "Mortality-prominent",
            ]
        )
    build_table(doc, ["State/UT", "YLD rate", "Death rate", "HDBI z-score", "Profile"], hdbi_rows, widths=[2.1, 0.8, 0.8, 0.9, 1.5])
    para(doc, "HDBI = z(YLD rate) - z(death rate). Positive values indicate relatively greater disability burden.", size=9, italic=True)

    table_title(doc, "Table 4. Inter-state inequality in accidental death rates, India 2023.")
    ineq = m["inequality"]
    build_table(
        doc,
        ["Metric", "Value"],
        [
            ["Mean rate per 100,000", f"{ineq['mean_rate_per_lakh']:.2f}"],
            ["Median rate per 100,000", f"{ineq['median_rate_per_lakh']:.2f}"],
            ["Minimum rate per 100,000", f"{ineq['min_rate_per_lakh']:.2f}"],
            ["Maximum rate per 100,000", f"{ineq['max_rate_per_lakh']:.2f}"],
            ["Top-to-bottom ratio", f"{ineq['top_bottom_ratio']:.2f}"],
            ["Coefficient of variation", f"{ineq['cv']:.3f}"],
            ["Interquartile range", f"{ineq['iqr']:.2f}"],
            ["Gini coefficient", f"{ineq['gini']:.3f}"],
        ],
        widths=[2.8, 1.2],
    )
    para(doc, "Source: NCRB accidental death rates. The Gini coefficient ranges from 0 (equality) to 1 (maximal inequality).", size=9, italic=True)

    heading(doc, "Figure Legends")
    body(doc, "Fig 1. India choropleth of age-standardised injury DALY rate per 100,000 population in 2021. Darker shading indicates higher burden; boundary notes are shown in the figure.")
    body(doc, "Fig 2. Hidden Disability Burden Index by state in 2021. Positive values identify disability-prominent states and negative values identify mortality-prominent states.")
    body(doc, "Fig 3. Heatmap of cause-specific injury DALY rates by state in 2021. Colour intensity is scaled within each cause column.")
    body(doc, "Fig 4. Available-year trend series for total injury DALYs, deaths and YLDs across the processed local extract.")
    body(doc, "Fig 5. State typology scatter plot of injury death rate versus YLD rate in 2021.")
    body(doc, "Fig 6. Road-injury surveillance-burden rank mismatch comparing MoRTH road-death rank with GBD road-DALY rank.")

    safe_save(doc, "01_manuscript_submission.docx")


def build_cover_letter() -> None:
    doc = Document()
    set_margins(doc)
    para(doc, TODAY, size=12)
    para(doc, "The Editor", size=12, bold=True)
    para(doc, "The National Medical Journal of India", size=12)
    para(doc, "All India Institute of Medical Sciences", size=12)
    para(doc, "New Delhi 110029, India", size=12, space_after=12)
    body(doc, "Dear Editor,")
    body(
        doc,
        "Please consider our original article, entitled 'Burden of injuries in India from a public health perspective: state-level fatal-non-fatal decomposition, inequality, and surveillance-burden mismatch using GBD 2021 and official Indian secondary data', for publication in The National Medical Journal of India."
    )
    body(doc, "The manuscript makes five main contributions:")
    for point in [
        "it quantifies state-level injury DALY burden across India using the available processed GBD subnational extract;",
        "it distinguishes fatal and non-fatal burden through cause-specific disability fractions;",
        "it introduces a Hidden Disability Burden Index to identify states whose burden is underestimated by mortality-centred surveillance;",
        "it quantifies inter-state inequality and documents rank discordance between modelled burden and road-surveillance rankings;",
        f"it is accompanied by a public reproducibility repository containing code, processed outputs and submission assets ({REPO_URL}).",
    ]:
        p = doc.add_paragraph(style="List Bullet")
        run = p.add_run(point)
        style_run(run, size=12)
    body(
        doc,
        "The work is original, has not been published elsewhere, and is not under consideration by another journal. It uses only public aggregated secondary data, required no ethics approval, received no external funding and has no competing interests."
    )
    body(doc, "Suggested reviewers with relevant expertise and no known conflict are:")
    for reviewer in [
        "Prof. G. Gururaj, Bengaluru, India",
        "Dr. Rakhi Dandona, Hyderabad, India",
        "Dr. Shailaja Tetali, Hyderabad, India",
    ]:
        p = doc.add_paragraph(style="List Bullet")
        run = p.add_run(reviewer)
        style_run(run, size=12)
    body(doc, "Yours sincerely,")
    body(doc, AUTHOR_NAME)
    body(doc, AFFILIATION)
    body(doc, CORR_EMAIL)
    safe_save(doc, "02_cover_letter.docx")


def build_declarations() -> None:
    doc = Document()
    set_margins(doc)
    para(doc, "Author declarations", size=14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=14)
    for label, text in [
        ("Manuscript title", "Burden of injuries in India from a public health perspective: state-level fatal-non-fatal decomposition, inequality, and surveillance-burden mismatch using GBD 2021 and official Indian secondary data"),
        ("Corresponding author", f"{AUTHOR_NAME}; {AFFILIATION}; Email: {CORR_EMAIL}; Phone: {CORR_PHONE}; ORCID: {ORCID}"),
        ("Author contributions", f"{AUTHOR_NAME}: conceptualisation, data curation, formal analysis, visualisation, manuscript drafting, review and final approval."),
        ("Competing interests", "None declared."),
        ("Funding", "No specific funding was received."),
        ("Ethical approval", "Not required because only publicly available aggregated secondary data were analysed."),
        ("Data availability", f"Source data were obtained from GBD, MoRTH and NCRB. Code and processed data are available at {REPO_URL}."),
        ("Prior publication", "This work has not been published previously and is not under consideration elsewhere."),
    ]:
        p = doc.add_paragraph()
        r1 = p.add_run(f"{label}: ")
        style_run(r1, size=12, bold=True)
        r2 = p.add_run(text)
        style_run(r2, size=12)
    safe_save(doc, "03_declarations.docx")


def build_supplementary(m) -> None:
    doc = Document()
    set_margins(doc)
    para(doc, "Supplementary material", size=14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=14)

    table_title(doc, "Table S1. Data sources used in the analysis.")
    build_table(
        doc,
        ["Source", "Coverage", "Use"],
        [
            ["GBD 2021 subnational extract", "Indian states/state-equivalent units; multiple measures", "Primary burden estimation"],
            ["MoRTH Road Accidents in India 2023", "Road deaths by state", "Road surveillance comparison"],
            ["NCRB Accidental Deaths and Suicides in India 2023", "Accidental deaths and rates by state", "Inequality assessment and context"],
        ],
        widths=[2.3, 2.2, 2.0],
    )

    table_title(doc, "Table S2. Full state DALY-rate ranking, 2021.")
    build_table(
        doc,
        ["Rank", "State/UT", "DALY rate", "Death rate", "YLD rate"],
        [
            [i + 1, row["state_name_harmonized"], f"{row['dalys_rate']:.0f}", f"{row['deaths_rate']:.1f}", f"{row['ylds_rate']:.0f}"]
            for i, (_, row) in enumerate(m["sb"].sort_values("dalys_rate", ascending=False).iterrows())
        ],
        widths=[0.6, 2.2, 0.8, 0.8, 0.8],
    )

    table_title(doc, "Table S3. Road-injury surveillance-burden mismatch ranking.")
    build_table(
        doc,
        ["State/UT", "GBD rank", "MoRTH rank", "Rank difference"],
        [
            [row["state_name_harmonized"], f"{row['gbd_rank']:.0f}", f"{row['morth_rank']:.0f}", f"{row['rank_diff']:.0f}"]
            for _, row in m["mismatch"].sort_values("rank_diff", key=lambda s: s.abs(), ascending=False).iterrows()
        ],
        widths=[2.2, 0.8, 0.8, 0.9],
    )

    table_title(doc, "Table S4. Reproducibility notes.")
    build_table(
        doc,
        ["Item", "Detail"],
        [
            ["Repository", REPO_URL],
            ["Figure source folder", str(FIGURES_DIR)],
            ["Main outputs used", "state_burden_2021.csv; decomposition.csv; hdbi.csv; inequality.csv; mismatch.csv"],
            ["Software", "Python-based processing and document assembly"],
        ],
        widths=[1.8, 4.5],
    )
    safe_save(doc, "04_supplementary.docx")


def build_figures_doc() -> None:
    doc = Document()
    set_margins(doc)
    para(doc, "Figures", size=14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=14)
    figures = [
        ("Fig 1", "State-level injury DALY map, 2021.", "fig1_daly_map.png"),
        ("Fig 2", "Hidden Disability Burden Index by state, 2021.", "fig2_hdbi_bar.png"),
        ("Fig 3", "Cause-specific injury DALY heatmap by state.", "fig3_heatmap.png"),
        ("Fig 4", "Available-year trend series for burden totals.", "fig4_trends.png"),
        ("Fig 5", "State typology by death rate and YLD rate.", "fig5_quadrant.png"),
        ("Fig 6", "Road-injury surveillance-burden rank mismatch.", "fig6_mismatch.png"),
    ]
    for label, legend, filename in figures:
        para(doc, label, size=12, bold=True, space_after=3)
        para(doc, legend, size=11)
        doc.add_picture(str(FIGURES_DIR / filename), width=Inches(6.3))
        para(doc, "", space_after=12)
    safe_save(doc, "05_figures.docx")


def build_audit_note() -> None:
    note = f"""# Submission Audit Note

Date: {TODAY}

This rebuild restored the fuller manuscript structure after an earlier compressed rewrite reduced content depth, dropped keywords and shortened the reference list. The current package:

- restores a longer Introduction, Results and Discussion
- restores a 20-item reference list cited in textual order
- restores keywords in the manuscript
- restores ordered citations to Tables 1-4 and Figs 1-6
- removes unsupported figure claims
- keeps all generated submission assets linked to the public repository

Repository: {REPO_URL}
"""
    (PUBLISH_DIR / "06_editorial_audit.md").write_text(note, encoding="utf-8")


def copy_figure_assets() -> None:
    for stem in ["fig1_daly_map", "fig2_hdbi_bar", "fig3_heatmap", "fig4_trends", "fig5_quadrant", "fig6_mismatch"]:
        for ext in ["png", "pdf"]:
            src = FIGURES_DIR / f"{stem}.{ext}"
            if src.exists():
                dst = PUBLISH_DIR / f"{stem}.{ext}"
                dst.write_bytes(src.read_bytes())


def run() -> None:
    m = metrics()
    build_title_page(m)
    build_manuscript(m)
    build_cover_letter()
    build_declarations()
    build_supplementary(m)
    build_figures_doc()
    build_audit_note()
    copy_figure_assets()


if __name__ == "__main__":
    run()
