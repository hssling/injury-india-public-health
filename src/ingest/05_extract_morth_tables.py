"""
MoRTH 2023 Comprehensive Table Extractor
Extracts all key state-wise tables from Road Accidents in India 2023 PDF.
Produces clean CSVs for analysis pipeline.
"""

import pathlib
import pandas as pd
import numpy as np
import logging
import re

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_RAW = PROJECT_ROOT / "data_raw" / "morth"
DATA_INTERIM = PROJECT_ROOT / "data_interim"
LOGS = PROJECT_ROOT / "logs"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOGS / "05_extract_morth_tables.log"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)

STATES_UTS = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
    "Tamil Nadu", "Telangana", "Tripura", "Uttarakhand", "Uttar Pradesh",
    "West Bengal", "Andaman & Nicobar Islands", "Chandigarh",
    "Dadra & Nagar Haveli and Daman & Diu", "Delhi", "Jammu & Kashmir",
    "Ladakh", "Lakshadweep", "Puducherry"
]

STATE_UPPER = {s.upper(): s for s in STATES_UTS}
STATE_UPPER.update({
    "ANDAMAN & NICOBAR ISLANDS": "Andaman & Nicobar Islands",
    "J & K#": "Jammu & Kashmir",
    "JAMMU & KASHMIR": "Jammu & Kashmir",
    "DADRA & NAGAR HAVELI AND DAMAN & DIU": "Dadra & Nagar Haveli and Daman & Diu",
    "DADRA & NAGAR HAVELI*": "Dadra & Nagar Haveli and Daman & Diu",
    "UTTARAKHAND": "Uttarakhand",
})


def clean_number(val):
    """Convert string number with commas/spaces to float."""
    if pd.isna(val):
        return np.nan
    s = str(val).replace(",", "").replace(" ", "").strip()
    try:
        return float(s)
    except (ValueError, TypeError):
        return np.nan


def extract_state_accidents_table(pdf_path):
    """
    Extract Table 42 (pages 120-180): State-wise Total Road Accidents 2020-2023.
    Returns df with state, year, accidents_total.
    """
    import tabula
    log.info("Extracting MoRTH state-wise accidents table...")
    try:
        tables = tabula.read_pdf(
            str(pdf_path), pages='120-180', multiple_tables=True,
            stream=True, encoding='latin-1', pandas_options={'header': None}
        )
    except Exception as e:
        log.error(f"tabula extraction failed: {e}")
        return pd.DataFrame()

    for t in tables:
        t_str = t.to_string().lower()
        if ('total number of road accidents' in t_str or
                ('karnataka' in t_str and 'tamil nadu' in t_str and t.shape[1] >= 4)):
            if t.shape[0] > 25:
                log.info(f"Found accidents table: shape {t.shape}")
                return parse_state_accidents(t)
    log.warning("Accidents table not found in pages 120-180")
    return pd.DataFrame()


def parse_state_accidents(raw: pd.DataFrame) -> pd.DataFrame:
    """Parse the raw state-wise accidents table into clean long format."""
    rows = []
    for _, row in raw.iterrows():
        state_raw = str(row.iloc[1]).strip() if len(row) > 1 else ""
        # Match state name
        state = STATE_UPPER.get(state_raw.upper())
        if not state:
            continue
        # Extract year values: columns vary; look for 2020, 2021, 2022, 2023
        # From Table 42, columns ~2-5 have 2020, 2021, 2022, 2023 values
        vals = [clean_number(v) for v in row.iloc[2:7]]
        years = [2020, 2021, 2022, 2023]
        # Use last 4 non-NaN values
        non_nan = [(i, v) for i, v in enumerate(vals) if not np.isnan(v)]
        if len(non_nan) >= 4:
            used = non_nan[-4:]
        else:
            used = non_nan
        for year_idx, (col_idx, val) in enumerate(used):
            if year_idx < len(years):
                rows.append({
                    "state_name_harmonized": state,
                    "year": years[year_idx + (4 - len(used))],
                    "accidents_total": val,
                    "source": "morth2023",
                })
    df = pd.DataFrame(rows)
    log.info(f"Parsed {len(df)} state-year accident rows")
    return df


def extract_state_deaths_injured(pdf_path):
    """
    Extract state-wise persons killed and injured from MoRTH.
    Tables 26/27 (pages 15-60) have top states with fatalities.
    Table 31 (pages 60-120) has top 10 with 2019-2023 data.
    We need the full state-wise deaths table.
    """
    import tabula
    log.info("Extracting MoRTH state-wise deaths and injured tables...")

    results = {}

    for pages in ['15-60', '60-120', '120-180', '180-250']:
        try:
            tables = tabula.read_pdf(
                str(pdf_path), pages=pages, multiple_tables=True,
                stream=True, encoding='latin-1', pandas_options={'header': None}
            )
            for t in tables:
                t_str = t.to_string().lower()
                # Total fatalities table (all states)
                if ('persons killed' in t_str or 'fatalities' in t_str or 'death' in t_str):
                    if any(s in t_str for s in ['karnataka', 'tamil nadu', 'maharashtra']):
                        if t.shape[0] > 25 and t.shape[1] >= 4:
                            if 'deaths' not in results:
                                results['deaths_raw'] = t
                                log.info(f"Found deaths table in pages {pages}, shape {t.shape}")
                if ('persons injured' in t_str or 'injured' in t_str):
                    if any(s in t_str for s in ['karnataka', 'tamil nadu', 'maharashtra']):
                        if t.shape[0] > 25 and t.shape[1] >= 4:
                            if 'injured' not in results:
                                results['injured_raw'] = t
                                log.info(f"Found injured table in pages {pages}, shape {t.shape}")
        except Exception as e:
            log.warning(f"Extraction failed for pages {pages}: {e}")

    return results


def extract_top_states_deaths(pdf_path) -> pd.DataFrame:
    """
    Extract Table 27 (pages 15-60): Top states by road fatalities 2019-2023.
    Also extract Table 31: All-India total road deaths by state from another table.
    """
    import tabula
    log.info("Extracting top states fatalities table...")
    try:
        tables = tabula.read_pdf(
            str(pdf_path), pages='15-60', multiple_tables=True,
            stream=True, encoding='latin-1', pandas_options={'header': None}
        )
    except Exception as e:
        log.error(f"Extraction failed: {e}")
        return pd.DataFrame()

    rows = []
    for t in tables:
        t_str = t.to_string()
        # Table 27: Top states by road deaths - has Uttar Pradesh with 8,830 in 2019
        if '8,830' in t_str or '8830' in t_str or '172890' in t_str or '1,72,890' in t_str:
            log.info(f"Found fatalities table shape {t.shape}")
            # Parse: rows 1-20, col 1=state, cols 2-6 = 2019-2023
            for _, row in t.iterrows():
                state_raw = str(row.iloc[1]).strip() if len(row) > 1 else ""
                state = STATE_UPPER.get(state_raw.upper())
                if not state:
                    continue
                vals = [clean_number(v) for v in row.iloc[2:7]]
                for yr_i, yr in enumerate([2019, 2020, 2021, 2022, 2023]):
                    if yr_i < len(vals) and not np.isnan(vals[yr_i]):
                        rows.append({
                            "state_name_harmonized": state,
                            "year": yr,
                            "road_deaths_n": vals[yr_i],
                            "source": "morth2023",
                        })

    # Also parse Table 31 which has all-India total and top states
    for t in tables:
        t_str = t.to_string()
        if '1,72,890' in t_str or '172890' in t_str:
            log.info(f"Found all-India deaths table (Table 31-style)")
            for _, row in t.iterrows():
                state_raw = str(row.iloc[0]).strip() if len(row) > 0 else ""
                state = STATE_UPPER.get(state_raw.upper())
                if not state:
                    continue
                vals = [clean_number(v) for v in row.iloc[1:6]]
                for yr_i, yr in enumerate([2019, 2020, 2021, 2022, 2023]):
                    if yr_i < len(vals) and not np.isnan(vals[yr_i]):
                        rows.append({
                            "state_name_harmonized": state,
                            "year": yr,
                            "road_deaths_n": vals[yr_i],
                            "source": "morth2023",
                        })

    df = pd.DataFrame(rows).drop_duplicates()
    log.info(f"Extracted {len(df)} state-year death rows")
    return df


def extract_all_state_accidents_from_found_table() -> pd.DataFrame:
    """
    Directly parse the Table 42 data we already found via exploration.
    Contains: all 36 states/UTs × 2020-2023.
    """
    raw_data = {
        "state_name_harmonized": [
            "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
            "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
            "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
            "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
            "Tamil Nadu", "Telangana", "Tripura", "Uttarakhand", "Uttar Pradesh",
            "West Bengal", "Andaman & Nicobar Islands", "Chandigarh",
            "Dadra & Nagar Haveli and Daman & Diu", "Delhi", "Jammu & Kashmir",
            "Ladakh", "Lakshadweep", "Puducherry"
        ],
        2020: [
            19509, 134, 6595, 8639, 11656, 2375, 13398, 9431, 2239, 4405, 34178,
            27877, 45266, 24971, 432, 214, 53, 500, 9817, 5203, 19114, 138,
            49844, 19172, 466, 1041, 34243, 10863, 141, 159, 100, 4178, 4860, np.nan, 1, 969
        ],
        2021: [
            21556, 283, 7411, 9553, 12375, 2849, 15186, 9933, 2404, 4728, 34647,
            33296, 48877, 29477, 366, 245, 69, 746, 10983, 5871, 20951, 155,
            55682, 21315, 479, 1405, 37729, 11937, 115, 208, 140, 4720, 5452, 236, 1, 1049
        ],
        2022: [
            21249, 227, 7023, 10801, 13279, 3011, 15751, 10429, 2597, 5175, 39762,
            43910, 54432, 33383, 508, 246, 133, 489, 11663, 6138, 23614, 211,
            64105, 21619, 575, 1674, 41746, 13686, 141, 237, 196, 5652, 6092, 374, 4, 1181
        ],
        2023: [
            19949, 287, 7421, 11014, 13468, 2846, 16349, 10463, 2253, 5315, 43440,
            48091, 55327, 35243, 398, 223, 106, 303, 11992, 6269, 24694, 182,
            67213, 22903, 577, 1691, 44534, 13795, 143, 182, 182, 5834, 6298, 289, 1, 1308
        ],
        "rank_2023": [
            9, 29, 16, 14, 12, 21, 10, 15, 22, 20, 5, 3, 2, 6, 26, 30, 35,
            27, 13, 18, 7, 31, 1, 8, 25, 23, 4, 11, 34, 31, 31, 19, 17, 28, 36, 24
        ]
    }

    rows = []
    for i, state in enumerate(raw_data["state_name_harmonized"]):
        for yr in [2020, 2021, 2022, 2023]:
            val = raw_data[yr][i]
            if not np.isnan(val):
                rows.append({
                    "state_name_harmonized": state,
                    "year": yr,
                    "road_accidents_n": val,
                    "source": "morth2023",
                    "rank_2023": raw_data["rank_2023"][i] if yr == 2023 else np.nan,
                })
    return pd.DataFrame(rows)


def extract_road_deaths_all_states_2023() -> pd.DataFrame:
    """
    From Table 31 in MoRTH 2023 exploration, we have full state-wise deaths.
    This encodes the data manually extracted from Table 27 and related tables.
    National total: 1,72,890 road deaths in 2023 (confirmed from text in Table 22).
    Top 10 states by fatalities 2023 from Table 27:
      UP=23,652; TN=18,347; MH=15,366; MP=13,798; KA=12,321;
      RJ=11,762; BR=8,873; AP=8,137; GJ=7,854; TG=7,660
    """
    # Partial data from extracted tables — top 10 confirmed, others need full table
    data = {
        "state_name_harmonized": [
            "Uttar Pradesh", "Tamil Nadu", "Maharashtra", "Madhya Pradesh", "Karnataka",
            "Rajasthan", "Bihar", "Andhra Pradesh", "Gujarat", "Telangana",
        ],
        "road_deaths_n_2023": [23652, 18347, 15366, 13798, 12321, 11762, 8873, 8137, 7854, 7660],
    }

    # All India total confirmed: 1,72,890
    rows = []
    for i, state in enumerate(data["state_name_harmonized"]):
        rows.append({
            "state_name_harmonized": state,
            "year": 2023,
            "road_deaths_n": data["road_deaths_n_2023"][i],
            "source": "morth2023",
            "note": "top10_extracted",
        })
    rows.append({
        "state_name_harmonized": "All India",
        "year": 2023,
        "road_deaths_n": 172890,
        "source": "morth2023",
        "note": "national_total_confirmed",
    })
    return pd.DataFrame(rows)


def run():
    log.info("=== MoRTH Extraction: Start ===")
    pdf_path = next(DATA_RAW.glob("*.pdf"), None)
    if not pdf_path:
        log.error("No MoRTH PDF found in data_raw/morth/")
        return

    log.info(f"Processing: {pdf_path}")

    # Extract state-wise accidents (comprehensive, all states, 2020-2023)
    accidents_df = extract_all_state_accidents_from_found_table()
    accidents_path = DATA_INTERIM / "morth_state_accidents.csv"
    accidents_df.to_csv(accidents_path, index=False)
    log.info(f"State accidents saved: {accidents_path} ({len(accidents_df)} rows)")

    # Extract deaths (top 10 confirmed + national total)
    deaths_df = extract_road_deaths_all_states_2023()
    deaths_path = DATA_INTERIM / "morth_state_deaths_partial.csv"
    deaths_df.to_csv(deaths_path, index=False)
    log.info(f"State deaths saved: {deaths_path} ({len(deaths_df)} rows, TOP 10 ONLY)")
    log.warning("Road deaths data is TOP 10 STATES ONLY. Full state-wise deaths table requires manual extraction.")
    log.warning("See data_raw/morth/manual_extraction_morth.xlsx for full table template.")

    # Try to extract full deaths from PDF
    top_deaths = extract_top_states_deaths(pdf_path)
    if not top_deaths.empty:
        top_deaths.to_csv(DATA_INTERIM / "morth_deaths_pdf_extract.csv", index=False)
        log.info(f"PDF-extracted deaths: {DATA_INTERIM / 'morth_deaths_pdf_extract.csv'}")

    log.info("=== MoRTH Extraction: Complete ===")
    return accidents_df, deaths_df


if __name__ == "__main__":
    run()
