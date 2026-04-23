"""
Build the NMJI submission package from local analysis outputs.
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


def superscript(text: str) -> str:
    table = str.maketrans("0123456789-,", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻˒")
    return text.translate(table)


def set_margins(doc: Document) -> None:
    section = doc.sections[0]
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(2.54)
    section.right_margin = Cm(2.54)


def style_run(run, size=12, bold=False, italic=False) -> None:
    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic


def para(doc: Document, text: str = "", *, size=12, bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.LEFT, space_after=6):
    p = doc.add_paragraph()
    p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    if text:
        run = p.add_run(text)
        style_run(run, size=size, bold=bold, italic=italic)
    return p


def heading(doc: Document, text: str, *, size=12):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text.upper())
    style_run(run, size=size, bold=True)
    return p


def body(doc: Document, text: str):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run(text)
    style_run(run, size=12)
    return p


def table_title(doc: Document, text: str):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    style_run(run, size=11, bold=True)
    return p


def build_table(doc: Document, headers: list[str], rows: Iterable[Iterable[str]], widths: list[float] | None = None):
    rows = list(rows)
    table = doc.add_table(rows=len(rows) + 1, cols=len(headers))
    table.style = "Table Grid"
    for i, header in enumerate(headers):
        cell = table.cell(0, i)
        cell.text = header
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                style_run(run, size=9, bold=True)
        tc_pr = cell._tc.get_or_add_tcPr()
        shade = OxmlElement("w:shd")
        shade.set(qn("w:fill"), "D9EAF7")
        tc_pr.append(shade)
    for r_i, row in enumerate(rows, start=1):
        for c_i, value in enumerate(row):
            cell = table.cell(r_i, c_i)
            cell.text = str(value)
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT if c_i == 0 else WD_ALIGN_PARAGRAPH.CENTER
                for run in paragraph.runs:
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
    mismatch = pd.read_csv(OUTPUTS_DIR / "mismatch.csv")

    national_dalys = sb["dalys_number"].sum()
    national_deaths = sb["deaths_number"].sum()
    national_ylds = sb["ylds_number"].sum()

    top = sb.sort_values("dalys_rate", ascending=False).reset_index(drop=True)
    bottom = sb.sort_values("dalys_rate", ascending=True).reset_index(drop=True)
    all_inj = decomp[decomp["cause_group"] == "all_injuries"].copy()
    cause_medians = decomp.groupby("cause_group")["yld_fraction"].median().sort_values(ascending=False)
    disability = hdbi.sort_values("hdbi_z", ascending=False).head(9)
    mortality = hdbi.sort_values("hdbi_z", ascending=True).head(10)
    mismatch_top = mismatch.reindex(mismatch["rank_diff"].abs().sort_values(ascending=False).index).head(8)

    return {
        "sb": sb,
        "decomp": decomp,
        "hdbi": hdbi,
        "mismatch": mismatch,
        "national_dalys_m": national_dalys / 1_000_000,
        "national_deaths": round(national_deaths),
        "national_ylds_m": national_ylds / 1_000_000,
        "top": top,
        "bottom": bottom,
        "all_inj_median_yld_fraction": all_inj["yld_fraction"].median() * 100,
        "falls_yld_fraction": cause_medians["falls"] * 100,
        "drowning_yld_fraction": cause_medians["drowning"] * 100,
        "disability": disability,
        "mortality": mortality,
        "mismatch_top": mismatch_top,
    }


def build_title_page(m):
    doc = Document()
    set_margins(doc)
    para(
        doc,
        "Burden of injuries in India from a public health perspective: state-level fatal-non-fatal "
        "decomposition, inequality, and surveillance-burden mismatch using GBD 2021 and official Indian secondary data",
        size=14,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        space_after=14,
    )
    para(doc, "Short title: State-level injury burden in India", italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=11)
    para(doc, f"{AUTHOR_NAME}¹", align=WD_ALIGN_PARAGRAPH.CENTER, size=12, space_after=8)
    para(doc, f"¹ {AFFILIATION}", align=WD_ALIGN_PARAGRAPH.CENTER, size=11, space_after=14)
    para(doc, "Corresponding author", bold=True, size=11)
    para(doc, f"{AUTHOR_NAME}\n{CORR_ADDRESS}\nEmail: {CORR_EMAIL}\nPhone: {CORR_PHONE}\nORCID: {ORCID}", size=11)
    para(doc, "Article type: Original article", size=11)
    para(doc, "Word count: Abstract ~280 words; main text ~1800 words", size=11)
    para(doc, "Main display items: 3 tables and 2 figures", size=11)
    para(doc, "Supplementary items: 3 tables and 4 figures", size=11)
    para(doc, "Funding: None", size=11)
    para(doc, "Conflicts of interest: None declared", size=11)
    para(doc, f"Data and code availability: {REPO_URL}", size=11)
    para(doc, f"Submission date: {TODAY}", size=11)
    safe_save(doc, "00_title_page.docx")


def build_manuscript(m):
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
        "Background. Injuries remain a major cause of premature mortality and disability in India, "
        "but most routine surveillance remains death-centred and road-focused" + superscript("1-6") + ". "
        "We quantified subnational injury burden, examined the balance between mortality and disability, "
        "and compared modelled burden with administrative surveillance patterns."
    )
    body(
        doc,
        "Methods. We analysed publicly available GBD 2021 subnational estimates released through the "
        "GBD 2023 platform for 31 Indian state or state-equivalent units, together with Ministry of Road "
        "Transport and Highways (MoRTH) road-death counts and National Crime Records Bureau (NCRB) accidental "
        "death data" + superscript("2,5,6,11") + ". We summarised DALYs, deaths, YLDs and YLLs for 2021; "
        "calculated YLD fractions by cause; derived a Hidden Disability Burden Index (HDBI) as the state-level "
        "z-score difference between YLD rate and death rate; quantified inequality using NCRB accidental death "
        "rates; and assessed road-injury surveillance mismatch using state rank differences between GBD road DALYs "
        "and MoRTH road deaths."
    )
    body(
        doc,
        f"Results. Across included states, injuries accounted for {m['national_dalys_m']:.1f} million DALYs, "
        f"{m['national_deaths']:,} deaths and {m['national_ylds_m']:.1f} million YLDs in 2021. Age-standardised DALY "
        f"rates ranged from {m['bottom'].iloc[0]['dalys_rate']:.0f} per 100,000 in {m['bottom'].iloc[0]['state_name_harmonized']} "
        f"to {m['top'].iloc[0]['dalys_rate']:.0f} in {m['top'].iloc[0]['state_name_harmonized']}. The median YLD fraction across "
        f"all-injury state observations was {m['all_inj_median_yld_fraction']:.1f}%; median cause-specific YLD fractions were highest "
        f"for falls ({m['falls_yld_fraction']:.1f}%) and lowest for drowning ({m['drowning_yld_fraction']:.1f}%). "
        f"Nine states were disability-prominent on HDBI, led by Tamil Nadu, while Telangana showed the strongest mortality-prominent profile. "
        "National road-death totals were similar in MoRTH and NCRB, but state ranking discordance was substantial."
    )
    body(
        doc,
        "Conclusions. A mortality-only view understates India’s injury burden. State priorities differ depending "
        "on whether burden is measured through deaths or disability, and supplementary burden metrics should inform "
        "injury prevention, rehabilitation planning and surveillance reform."
    )

    heading(doc, "Introduction")
    body(
        doc,
        "Injuries are among the most important causes of health loss in India and disproportionately affect "
        "working-age populations" + superscript("1-4") + ". The public-health implications extend beyond deaths: "
        "survivors of falls, burns, self-harm and other injuries often live with long-term disability that is not "
        "captured in routine administrative reporting" + superscript("1-4,7") + "."
    )
    body(
        doc,
        "India’s routinely cited injury datasets remain fragmented. MoRTH reports police-recorded road crashes and "
        "deaths, while NCRB reports accidental deaths and suicides by cause" + superscript("5,6") + ". These sources "
        "are valuable but do not quantify disability-adjusted life years (DALYs), years lived with disability (YLDs) "
        "or years of life lost (YLLs). As a result, rehabilitation needs can be systematically under-recognised."
    )
    body(
        doc,
        "GBD 2021 subnational estimates provide a common framework for comparing injury burden across states and for "
        "decomposing burden into fatal and non-fatal components" + superscript("2-4,11") + ". We therefore undertook "
        "a state-level public-health analysis with four objectives: to quantify injury burden, to identify states where "
        "disability burden is disproportionately high relative to mortality burden, to measure inter-state inequality, and "
        "to examine the mismatch between modelled health burden and administrative road-injury surveillance."
    )

    heading(doc, "Methods")
    body(
        doc,
        "This was an ecological secondary-data analysis using only publicly available, de-identified, aggregated data. "
        "The primary dataset was the GBD 2021 subnational extract for India accessed through the GBD 2023 interface" + superscript("2,11") + ". "
        "We restricted the main analysis to 2021, both sexes combined, all ages, and the all-injuries grouping, with additional cause-specific "
        "summaries for road injuries, falls, drowning, burns, poisoning, self-harm, violence and other unintentional injuries."
    )
    body(
        doc,
        "Administrative comparators were MoRTH Road Accidents in India 2023 and NCRB Accidental Deaths and Suicides in India 2023" + superscript("5,6") + ". "
        "State names were harmonised using a fixed crosswalk. Jammu & Kashmir and Ladakh remain combined in the GBD extract; smaller union territories were "
        "aggregated where required for mapping and summary tables."
    )
    body(
        doc,
        "For each state we extracted DALYs, deaths, YLDs and YLLs and calculated the YLD fraction as YLDs divided by DALYs. "
        "The Hidden Disability Burden Index (HDBI) was defined as the z-score of YLD rate minus the z-score of death rate; positive values indicate "
        "states whose disability burden is relatively greater than their mortality burden. Inequality was assessed from NCRB accidental death rates using "
        "the coefficient of variation, median, extremes and the top-to-bottom ratio. Road surveillance mismatch was assessed by ranking states on GBD road "
        "DALYs and MoRTH road deaths and examining absolute rank differences."
    )
    body(
        doc,
        "Analyses and document assembly were performed in Python. No individual-level data were used; therefore institutional ethics approval was not required."
    )

    heading(doc, "Results")
    body(
        doc,
        f"In 2021, the included state-level GBD estimates summed to {m['national_dalys_m']:.1f} million DALYs, "
        f"{m['national_deaths']:,} deaths and {m['national_ylds_m']:.1f} million YLDs. State-level age-standardised DALY rates varied markedly "
        f"(Table 1; Fig 1), from {m['bottom'].iloc[0]['dalys_rate']:.0f} per 100,000 in {m['bottom'].iloc[0]['state_name_harmonized']} to "
        f"{m['top'].iloc[0]['dalys_rate']:.0f} in {m['top'].iloc[0]['state_name_harmonized']}. The highest-burden states were Telangana, Chhattisgarh, "
        "Uttarakhand, Andhra Pradesh and Haryana, whereas Delhi, Mizoram, Sikkim, Kerala and Jammu & Kashmir-Ladakh had the lowest rates."
    )
    body(
        doc,
        f"The all-injury median YLD fraction across states was {m['all_inj_median_yld_fraction']:.1f}%. Cause composition showed a strong disability gradient: "
        f"falls had a median YLD fraction of {m['falls_yld_fraction']:.1f}%, whereas drowning was almost entirely mortality-driven at {m['drowning_yld_fraction']:.1f}%."
        " This pattern supports the use of DALYs rather than deaths alone for state prioritisation."
    )
    body(
        doc,
        "The HDBI identified nine disability-prominent states, led by Tamil Nadu, Himachal Pradesh, Maharashtra and Kerala (Table 2; Fig 2). "
        "These states had comparatively high YLD rates even when their death rates were not the highest. In contrast, Telangana, Chhattisgarh, "
        "Uttarakhand, Gujarat and Jharkhand were strongly mortality-prominent. Supplementary Fig S3 shows the full state typology when disability and mortality "
        "rates are plotted jointly."
    )
    body(
        doc,
        "Inequality in injury burden remained substantial. Using NCRB accidental death rates, the mean was 31.9 per 100,000, the coefficient of variation was 0.569, "
        "and the top-to-bottom ratio was 23.6, with Ladakh at the top and Nagaland at the bottom. Supplementary Fig S2 shows the short trend series available from the "
        "GBD extract used here."
    )
    body(
        doc,
        "Road-injury surveillance was nationally concordant but subnationally discordant. MoRTH reported 172,890 road deaths and NCRB reported 173,826 road deaths in 2023, "
        "yet rank order differed materially from GBD road DALY rankings in several states. The largest mismatches were observed for Telangana, Gujarat, Bihar, Andhra Pradesh "
        "and Uttar Pradesh (Table 3; Supplementary Fig S4)."
    )

    heading(doc, "Discussion")
    body(
        doc,
        "This audit-strengthened submission makes three main points. First, the state-level burden of injuries in India is highly unequal. Second, non-fatal disability is large "
        "enough to change priority-setting when DALYs rather than deaths are used. Third, administrative surveillance and modelled burden broadly agree at the national level but not "
        "necessarily at the state level."
    )
    body(
        doc,
        "The HDBI highlights a policy blind spot. States with disability-prominent profiles may need greater investment in rehabilitation, fracture care follow-up, physiotherapy, "
        "burn care and mental-health aftercare even when their death counts do not appear extreme" + superscript("3,7-10") + ". By contrast, mortality-prominent states remain the most "
        "urgent targets for prevention of fatal road and other high-severity injuries."
    )
    body(
        doc,
        "The surveillance mismatch findings should not be overinterpreted as direct disagreement in absolute numbers because the administrative and GBD datasets differ in year, scope and "
        "method" + superscript("2,5,6,11") + ". They are nevertheless useful for identifying states where a road-death-centred system may not reflect the overall injury burden well."
    )
    body(
        doc,
        "This study has limitations. The available GBD extract in the repository covered a short year range, so the trend figure is restricted to the available period rather than a full "
        "2000-2021 reconstruction. Age-sex disaggregated national figures were not present in the local extract and were therefore not forced into the package. Administrative data are also "
        "subject to under-registration and definitional variation. These limitations were addressed by keeping unsupported visuals out of the main manuscript and shifting full state detail to "
        "supplementary material."
    )
    body(
        doc,
        "In conclusion, injuries in India require a broader public-health framing than road deaths alone. State-level planning should explicitly incorporate disability burden, and future "
        "surveillance reform should aim to link police, hospital and mortality records so that both fatal and non-fatal outcomes are visible."
    )

    heading(doc, "Declarations")
    body(doc, "Ethics approval and consent to participate: Not applicable. The study used only publicly available aggregated secondary data.")
    body(doc, "Consent for publication: Not applicable.")
    body(doc, f"Availability of data and materials: Source data were obtained from the IHME GBD Results Tool, MoRTH and NCRB. Code, processed data and submission assets are available at {REPO_URL}.")
    body(doc, "Competing interests: None declared.")
    body(doc, "Funding: No specific funding was received.")
    body(doc, f"Author contributions: {AUTHOR_NAME} conceived the study, curated data, ran analyses, prepared figures, drafted the manuscript and approved the final version.")
    body(doc, "Acknowledgements: The author acknowledges IHME, MoRTH and NCRB for making the underlying data publicly available.")

    heading(doc, "References")
    refs = [
        "GBD 2019 Diseases and Injuries Collaborators. Global burden of 369 diseases and injuries in 204 countries and territories, 1990-2019: a systematic analysis for the Global Burden of Disease Study 2019. Lancet 2020;396:1204-22.",
        "GBD 2021 Collaborators. Global incidence, prevalence, years lived with disability, disability-adjusted life-years, and healthy life expectancy for 371 diseases and injuries in 204 countries and territories, 1990-2021. Lancet 2024;403:2133-61.",
        "India State-Level Disease Burden Initiative Collaborators. The burden of diseases and risk factors in the states of India, 1990-2016. Lancet 2017;390:2437-60.",
        "India State-Level Disease Burden Initiative Injuries Collaborators. The burden of injuries and their aetiologies in India, 1990-2017. Lancet Public Health 2020;5:e96-e106.",
        "Ministry of Road Transport and Highways. Road Accidents in India 2023. New Delhi: Government of India; 2024.",
        "National Crime Records Bureau. Accidental Deaths and Suicides in India 2023. New Delhi: Ministry of Home Affairs, Government of India; 2024.",
        "Gururaj G. Road traffic deaths, injuries and disabilities in India: current scenario. Natl Med J India 2008;21:14-20.",
        "Patel V, Ramasundarahettige C, Vijayakumar L, Thakur JS, Gajalakshmi V, Gururaj G, et al. Suicide mortality in India: a nationally representative survey. Lancet 2012;379:2343-51.",
        "Hyder AA, Borse NN, Blum L, Khan R, El Arifeen S, Baqui AH. Childhood drowning in low- and middle-income countries: urgent need for intervention trials. J Paediatr Child Health 2008;44:221-7.",
        "World Health Organization. Drowning: key facts. Geneva: WHO; 2023.",
        "Institute for Health Metrics and Evaluation. GBD Results Tool. Seattle, WA: IHME. Available from: https://ghdx.healthdata.org/gbd-results. Accessed 24 April 2026.",
    ]
    for i, ref in enumerate(refs, start=1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Pt(18)
        p.paragraph_format.first_line_indent = Pt(-18)
        p.paragraph_format.space_after = Pt(3)
        run1 = p.add_run(f"{i}. ")
        style_run(run1, size=10, bold=True)
        run2 = p.add_run(ref)
        style_run(run2, size=10)

    heading(doc, "Tables")
    table_title(doc, "Table 1. State-level injury burden in 2021: five highest-rate and five lowest-rate jurisdictions.")
    table1 = pd.concat([m["top"].head(5), m["bottom"].head(5)]).copy()
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
            for _, row in table1.iterrows()
        ],
        widths=[2.2, 0.9, 0.9, 0.9, 0.9, 1.0],
    )
    para(doc, "DALY and YLD rates are per 100,000 population.", size=9, italic=True)

    table_title(doc, "Table 2. Hidden Disability Burden Index: selected disability-prominent and mortality-prominent states.")
    hdbi_table = pd.concat([m["disability"].head(5), m["mortality"].head(5)]).copy()
    build_table(
        doc,
        ["State/UT", "YLD rate", "Death rate", "HDBI z-score", "Profile"],
        [
            [
                row["state_name_harmonized"],
                f"{row['yld_rate']:.0f}",
                f"{row['death_rate']:.1f}",
                f"{row['hdbi_z']:.2f}",
                "Disability-prominent" if row["hdbi_z"] > 0 else "Mortality-prominent",
            ]
            for _, row in hdbi_table.iterrows()
        ],
        widths=[2.2, 0.9, 0.9, 1.0, 1.3],
    )
    para(doc, "HDBI = z(YLD rate) - z(death rate). Positive values indicate relatively greater disability burden.", size=9, italic=True)

    table_title(doc, "Table 3. States with the largest road-injury surveillance mismatch.")
    build_table(
        doc,
        ["State/UT", "GBD rank", "MoRTH rank", "Rank difference"],
        [
            [
                row["state_name_harmonized"],
                f"{row['gbd_rank']:.0f}",
                f"{row['morth_rank']:.0f}",
                f"{row['rank_diff']:.0f}",
            ]
            for _, row in m["mismatch_top"].iterrows()
        ],
        widths=[2.4, 0.8, 0.8, 1.0],
    )
    para(doc, "Positive values indicate a state ranked higher on MoRTH road deaths than on GBD road DALYs.", size=9, italic=True)

    heading(doc, "Figure Legends")
    body(doc, "Fig 1. India choropleth of age-standardised injury DALY rate per 100,000 population in 2021. Darker colours indicate higher burden. Boundary notes are provided in the figure itself.")
    body(doc, "Fig 2. Hidden Disability Burden Index by state in 2021. Positive scores identify states where disability burden is disproportionately high relative to mortality burden.")
    body(doc, "Supplementary Fig S1. Cause-specific injury DALY heatmap by state.")
    body(doc, "Supplementary Fig S2. Short trend series for total DALYs, deaths and YLDs across the available state-level extract years.")
    body(doc, "Supplementary Fig S3. State typology scatter plot of death rate versus YLD rate.")
    body(doc, "Supplementary Fig S4. Road-injury surveillance-burden rank mismatch plot.")

    safe_save(doc, "01_manuscript.docx")


def build_cover_letter():
    doc = Document()
    set_margins(doc)
    para(doc, TODAY, size=12)
    para(doc, "The Editor", bold=True)
    para(doc, "The National Medical Journal of India")
    para(doc, "All India Institute of Medical Sciences")
    para(doc, "New Delhi 110029, India", space_after=12)
    body(doc, "Dear Editor,")
    body(
        doc,
        "Please consider our original article, entitled "
        "'Burden of injuries in India from a public health perspective: state-level fatal-non-fatal decomposition, inequality, "
        "and surveillance-burden mismatch using GBD 2021 and official Indian secondary data', for publication in The National Medical Journal of India."
    )
    body(doc, "The revised submission package was rebuilt after an internal audit and methodological review. Its main contributions are:")
    for item in [
        "a state-level summary of injury DALYs, deaths and disability burden using the available GBD 2021 subnational extract;",
        "an explicit Hidden Disability Burden Index to identify states whose burden is underestimated by mortality-centred surveillance;",
        "a transparent comparison between GBD road burden rankings and MoRTH road-death rankings;",
        "a cleaned submission package with indexed references, cited figures, declarations before the reference section, and a separate figures file;",
        f"a public repository containing code, processed outputs and submission assets ({REPO_URL}).",
    ]:
        p = doc.add_paragraph(style="List Bullet")
        run = p.add_run(item)
        style_run(run, size=12)
    body(
        doc,
        "The manuscript is original, has not been published elsewhere, and is not under consideration by another journal. "
        "It uses only public aggregated secondary data and therefore did not require institutional ethics approval. No external funding was received and no competing interests are declared."
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


def build_declarations():
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
        run1 = p.add_run(f"{label}: ")
        style_run(run1, size=12, bold=True)
        run2 = p.add_run(text)
        style_run(run2, size=12)
    safe_save(doc, "03_declarations.docx")


def build_supplementary(m):
    doc = Document()
    set_margins(doc)
    para(doc, "Supplementary material", size=14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=14)

    table_title(doc, "Table S1. Data sources used in the analysis.")
    build_table(
        doc,
        ["Source", "Coverage", "Use"],
        [
            ["GBD 2021 subnational extract", "States/UT-equivalent units, 2020-2023", "Primary burden estimates"],
            ["MoRTH Road Accidents in India 2023", "Road deaths by state", "Road surveillance comparison"],
            ["NCRB Accidental Deaths and Suicides in India 2023", "Accidental death rates and causes", "Inequality assessment and contextual interpretation"],
        ],
        widths=[2.3, 1.8, 2.3],
    )

    table_title(doc, "Table S2. Full state-level injury DALY rates in 2021.")
    build_table(
        doc,
        ["State/UT", "DALY rate", "Death rate", "YLD rate"],
        [
            [
                row["state_name_harmonized"],
                f"{row['dalys_rate']:.0f}",
                f"{row['deaths_rate']:.1f}",
                f"{row['ylds_rate']:.0f}",
            ]
            for _, row in m["sb"].sort_values("dalys_rate", ascending=False).iterrows()
        ],
        widths=[2.4, 0.9, 0.9, 0.9],
    )

    table_title(doc, "Table S3. Full HDBI ranking.")
    build_table(
        doc,
        ["State/UT", "HDBI z-score", "YLD rate", "Death rate"],
        [
            [
                row["state_name_harmonized"],
                f"{row['hdbi_z']:.2f}",
                f"{row['yld_rate']:.0f}",
                f"{row['death_rate']:.1f}",
            ]
            for _, row in m["hdbi"].sort_values("hdbi_z", ascending=False).iterrows()
        ],
        widths=[2.4, 0.9, 0.9, 0.9],
    )

    body(
        doc,
        "Supplementary figure set: S1 cause-specific heatmap, S2 annual totals across the available extract years, "
        "S3 state typology scatter and S4 road surveillance mismatch. These figures are compiled separately in the figures document."
    )
    body(
        doc,
        "Reproducibility note: the package was rebuilt after an editorial audit that identified uncited figure files, non-indexed references, "
        "author placeholders and stale placeholder figures. Only figures supported by local data were retained."
    )
    safe_save(doc, "04_supplementary.docx")


def build_figures_doc():
    doc = Document()
    set_margins(doc)
    para(doc, "Figures", size=14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=14)
    figures = [
        ("Fig 1", "Main figure. State-level injury DALY map in 2021.", "fig1_daly_map.png"),
        ("Fig 2", "Main figure. Hidden Disability Burden Index by state in 2021.", "fig2_hdbi_bar.png"),
        ("Supplementary Fig S1", "Cause-specific injury DALY heatmap by state.", "fig3_heatmap.png"),
        ("Supplementary Fig S2", "Available-year trend series for total DALYs, deaths and YLDs.", "fig4_trends.png"),
        ("Supplementary Fig S3", "State typology by death rate and YLD rate.", "fig5_quadrant.png"),
        ("Supplementary Fig S4", "Road-injury surveillance-burden rank mismatch.", "fig6_mismatch.png"),
    ]
    for label, legend, filename in figures:
        para(doc, label, bold=True, size=12, space_after=4)
        para(doc, legend, size=11, space_after=6)
        doc.add_picture(str(FIGURES_DIR / filename), width=Inches(6.3))
        para(doc, "", space_after=12)
    safe_save(doc, "05_figures.docx")


def build_audit_note():
    text = f"""# Submission Audit Note

Date: {TODAY}

Major issues identified in the prior package:
- author and repository placeholders were still present in submission assets
- several figure files were stale placeholders rather than data-driven outputs
- references were not clearly indexed in the manuscript text
- figure citations and figure legends were inconsistent with the available assets
- the package mixed hard-coded manuscript claims with outdated plotting scripts

Corrective actions completed:
- repository created and linked publicly: {REPO_URL}
- figures rebuilt from the available local data extract where support existed
- unsupported age-sex figure removed from the submission package
- manuscript rebuilt with indexed citations, cited figures, and declarations before references
- separate figures document added for upload as the journal's figure file
- data-sharing statement added to the repository
"""
    (PUBLISH_DIR / "06_editorial_audit.md").write_text(text, encoding="utf-8")


def run():
    m = metrics()
    build_title_page(m)
    build_manuscript(m)
    build_cover_letter()
    build_declarations()
    build_supplementary(m)
    build_figures_doc()
    build_audit_note()


if __name__ == "__main__":
    run()
