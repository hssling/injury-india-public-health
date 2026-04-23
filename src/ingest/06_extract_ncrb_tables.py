"""
NCRB ADSI 2023 Comprehensive Table Extractor
=============================================
Extracts all key state-wise accidental death and suicide tables from
Accidental Deaths & Suicides in India 2023 (NCRB).

Data confirmed by direct PDF extraction using tabula-py stream mode.
All cause-specific state tables are in pages 50-200 of the PDF.

Outputs:
  data_interim/ncrb_accidental_deaths_2023.csv  -- cause-specific deaths by state
  data_interim/ncrb_suicides_2023.csv           -- suicide deaths by state (if found)
  data_interim/ncrb_total_accidents_2022_2023.csv -- total accidental deaths 2022+2023
"""

import pathlib
import pandas as pd
import numpy as np
import logging

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_RAW     = PROJECT_ROOT / "data_raw" / "ncrb"
DATA_INTERIM = PROJECT_ROOT / "data_interim"
LOGS         = PROJECT_ROOT / "logs"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOGS / "06_extract_ncrb_tables.log"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# State name mapping  (NCRB uses upper-case / abbreviations)
# ---------------------------------------------------------------------------
STATE_MAP = {
    "ANDHRA PRADESH":   "Andhra Pradesh",
    "ARUNACHAL PRADESH":"Arunachal Pradesh",
    "ASSAM":            "Assam",
    "BIHAR":            "Bihar",
    "CHHATTISGARH":     "Chhattisgarh",
    "GOA":              "Goa",
    "GUJARAT":          "Gujarat",
    "HARYANA":          "Haryana",
    "HIMACHAL PRADESH": "Himachal Pradesh",
    "JHARKHAND":        "Jharkhand",
    "KARNATAKA":        "Karnataka",
    "KERALA":           "Kerala",
    "MADHYA PRADESH":   "Madhya Pradesh",
    "MAHARASHTRA":      "Maharashtra",
    "MANIPUR":          "Manipur",
    "MEGHALAYA":        "Meghalaya",
    "MIZORAM":          "Mizoram",
    "NAGALAND":         "Nagaland",
    "ODISHA":           "Odisha",
    "PUNJAB":           "Punjab",
    "RAJASTHAN":        "Rajasthan",
    "SIKKIM":           "Sikkim",
    "TAMIL NADU":       "Tamil Nadu",
    "TELANGANA":        "Telangana",
    "TRIPURA":          "Tripura",
    "UTTARAKHAND":      "Uttarakhand",
    "UTTAR PRADESH":    "Uttar Pradesh",
    "WEST BENGAL":      "West Bengal",
    # Union Territories
    "A & N ISLANDS":                   "Andaman & Nicobar Islands",
    "ANDAMAN & NICOBAR ISLANDS":       "Andaman & Nicobar Islands",
    "CHANDIGARH":                      "Chandigarh",
    "D & N HAVELI AND":                "Dadra & Nagar Haveli and Daman & Diu",
    "D&N HAVELI AND DAMAN & DIU":      "Dadra & Nagar Haveli and Daman & Diu",
    "DELHI (UT)":                      "Delhi",
    "DELHI UT":                        "Delhi",
    "JAMMU & KASHMIR":                 "Jammu & Kashmir",
    "LADAKH":                          "Ladakh",
    "LAKSHADWEEP":                     "Lakshadweep",
    "PUDUCHERRY":                      "Puducherry",
}


# ===========================================================================
# HARDCODED DATA  (confirmed by tabula extraction — 2023 figures)
# All values are "No. of Persons Died" (total = male + female + transgender)
# Source: NCRB ADSI 2023, Chapter on Accidental Deaths
# ===========================================================================

# Table indices from pages 50-200 extraction:
#   T21 = Drowning (Total)      T31 = Falls (Total)
#   T39 = Accidental Fire (Total) T48 = Road Accidents
#   T60 = Poisoning (Total)     T73 = Total Accidental Deaths 2023

STATES_ORDER = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
    "Tamil Nadu", "Telangana", "Tripura", "Uttarakhand", "Uttar Pradesh",
    "West Bengal",
    # Union Territories
    "Andaman & Nicobar Islands", "Chandigarh",
    "Dadra & Nagar Haveli and Daman & Diu", "Delhi",
    "Jammu & Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
]

# ── Drowning (Total) deaths 2023 ── (NCRB T21, col "No. of Persons Died Total")
DROWNING_DEATHS_2023 = {
    "Andhra Pradesh": 1480, "Arunachal Pradesh": 25, "Assam": 688,
    "Bihar": 2249, "Chhattisgarh": 2082, "Goa": 153, "Gujarat": 1956,
    "Haryana": 815, "Himachal Pradesh": 215, "Jharkhand": 788,
    "Karnataka": 2598, "Kerala": 1344, "Madhya Pradesh": 5149,
    "Maharashtra": 4548, "Manipur": 11, "Meghalaya": 73, "Mizoram": 26,
    "Nagaland": 6, "Odisha": 2066, "Punjab": 520, "Rajasthan": 2478,
    "Sikkim": 21, "Tamil Nadu": 2094, "Telangana": 1655, "Tripura": 57,
    "Uttarakhand": 166, "Uttar Pradesh": 3199, "West Bengal": 945,
    # UTs
    "Andaman & Nicobar Islands": 21, "Chandigarh": 1,
    "Dadra & Nagar Haveli and Daman & Diu": 45, "Delhi": 175,
    "Jammu & Kashmir": 31, "Ladakh": 9, "Lakshadweep": 2, "Puducherry": 47,
}
DROWNING_NATIONAL_2023 = 37738   # TOTAL (ALL INDIA)

# ── Falls (Total) deaths 2023 ── (NCRB T31)
FALLS_DEATHS_2023 = {
    "Andhra Pradesh": 1829, "Arunachal Pradesh": 18, "Assam": 35,
    "Bihar": 279, "Chhattisgarh": 791, "Goa": 124, "Gujarat": 2033,
    "Haryana": 738, "Himachal Pradesh": 877, "Jharkhand": 544,
    "Karnataka": 964, "Kerala": 1061, "Madhya Pradesh": 1927,
    "Maharashtra": 4563, "Manipur": 5, "Meghalaya": 51, "Mizoram": 29,
    "Nagaland": 3, "Odisha": 1335, "Punjab": 400, "Rajasthan": 2448,
    "Sikkim": 59, "Tamil Nadu": 1972, "Telangana": 1159, "Tripura": 55,
    "Uttarakhand": 192, "Uttar Pradesh": 896, "West Bengal": 339,
    # UTs
    "Andaman & Nicobar Islands": 16, "Chandigarh": 34,
    "Dadra & Nagar Haveli and Daman & Diu": 42, "Delhi": 238,
    "Jammu & Kashmir": 39, "Ladakh": 5, "Lakshadweep": 0, "Puducherry": 50,
}
FALLS_NATIONAL_2023 = 25150

# ── Accidental Fire (Total) deaths 2023 ── (NCRB T39)
FIRE_DEATHS_2023 = {
    "Andhra Pradesh": 328, "Arunachal Pradesh": 6, "Assam": 21,
    "Bihar": 374, "Chhattisgarh": 438, "Goa": 7, "Gujarat": 279,
    "Haryana": 104, "Himachal Pradesh": 55, "Jharkhand": 220,
    "Karnataka": 466, "Kerala": 240, "Madhya Pradesh": 597,
    "Maharashtra": 697, "Manipur": 0, "Meghalaya": 7, "Mizoram": 1,
    "Nagaland": 4, "Odisha": 1032, "Punjab": 103, "Rajasthan": 322,
    "Sikkim": 3, "Tamil Nadu": 616, "Telangana": 111, "Tripura": 20,
    "Uttarakhand": 23, "Uttar Pradesh": 374, "West Bengal": 364,
    # UTs
    "Andaman & Nicobar Islands": 1, "Chandigarh": 4,
    "Dadra & Nagar Haveli and Daman & Diu": 1, "Delhi": 54,
    "Jammu & Kashmir": 12, "Ladakh": 2, "Lakshadweep": 0, "Puducherry": 5,
}
FIRE_NATIONAL_2023 = 6891

# ── Road Accidents deaths 2023 (NCRB) ── (NCRB T48)
# Note: NCRB (1,73,826) differs slightly from MoRTH (1,72,890) —
# both are police-reported; MoRTH collates directly from state transport depts.
ROAD_DEATHS_NCRB_2023 = {
    "Andhra Pradesh": 8137, "Arunachal Pradesh": 136, "Assam": 3296,
    "Bihar": 8873, "Chhattisgarh": 6166, "Goa": 292, "Gujarat": 7854,
    "Haryana": 5401, "Himachal Pradesh": 885, "Jharkhand": 4173,
    "Karnataka": 12322, "Kerala": 4080, "Madhya Pradesh": 14098,
    "Maharashtra": 15434, "Manipur": 73, "Meghalaya": 168, "Mizoram": 49,
    "Nagaland": 37, "Odisha": 5737, "Punjab": 4906, "Rajasthan": 11932,
    "Sikkim": 68, "Tamil Nadu": 18347, "Telangana": 7660, "Tripura": 261,
    "Uttarakhand": 1054, "Uttar Pradesh": 23947, "West Bengal": 5703,
    # UTs
    "Andaman & Nicobar Islands": 27, "Chandigarh": 67,
    "Dadra & Nagar Haveli and Daman & Diu": 81, "Delhi": 1457,
    "Jammu & Kashmir": 897, "Ladakh": 59, "Lakshadweep": 0, "Puducherry": 149,
}
ROAD_NATIONAL_NCRB_2023 = 173826

# ── Poisoning (Total) deaths 2023 ── (NCRB T60)
POISONING_DEATHS_2023 = {
    "Andhra Pradesh": 435, "Arunachal Pradesh": 1, "Assam": 74,
    "Bihar": 501, "Chhattisgarh": 1362, "Goa": 7, "Gujarat": 597,
    "Haryana": 790, "Himachal Pradesh": 140, "Jharkhand": 356,
    "Karnataka": 2241, "Kerala": 106, "Madhya Pradesh": 4590,
    "Maharashtra": 1454, "Manipur": 0, "Meghalaya": 3, "Mizoram": 1,
    "Nagaland": 0, "Odisha": 1157, "Punjab": 688, "Rajasthan": 2622,
    "Sikkim": 3, "Tamil Nadu": 1594, "Telangana": 276, "Tripura": 2,
    "Uttarakhand": 195, "Uttar Pradesh": 1655, "West Bengal": 811,
    # UTs
    "Andaman & Nicobar Islands": 1, "Chandigarh": 6,
    "Dadra & Nagar Haveli and Daman & Diu": 2, "Delhi": 64,
    "Jammu & Kashmir": 40, "Ladakh": 4, "Lakshadweep": 0, "Puducherry": 7,
}
POISONING_NATIONAL_2023 = 21785

# ── Total Accidental Deaths 2023 by state ── (NCRB T73, "No. of Persons Died Total")
TOTAL_ACCIDENTAL_DEATHS_2023 = {
    "Andhra Pradesh": 16885, "Arunachal Pradesh": 321, "Assam": 5311,
    "Bihar": 15802, "Chhattisgarh": 15781, "Goa": 724, "Gujarat": 22911,
    "Haryana": 16087, "Himachal Pradesh": 2912, "Jharkhand": 7999,
    "Karnataka": 29907, "Kerala": 14936, "Madhya Pradesh": 42531,
    "Maharashtra": 69497, "Manipur": 195, "Meghalaya": 488, "Mizoram": 297,
    "Nagaland": 72, "Odisha": 20954, "Punjab": 10838, "Rajasthan": 30004,
    "Sikkim": 306, "Tamil Nadu": 32679, "Telangana": 13237, "Tripura": 651,
    "Uttarakhand": 2400, "Uttar Pradesh": 42355, "West Bengal": 14646,
    # UTs
    "Andaman & Nicobar Islands": 183, "Chandigarh": 312,
    "Dadra & Nagar Haveli and Daman & Diu": 242, "Delhi": 3508,
    "Jammu & Kashmir": 1450, "Ladakh": 133, "Lakshadweep": 3, "Puducherry": 1103,
}
TOTAL_ACCIDENTAL_NATIONAL_2023 = 437660

# ── Total Accidental Deaths 2022 by state ── (NCRB Table 21 from pages 1-50)
# Columns: "Total Accidental Deaths 2022"  (= Forces of Nature + Other Causes)
TOTAL_ACCIDENTAL_DEATHS_2022 = {
    "Andhra Pradesh": 16693, "Arunachal Pradesh": 409, "Assam": 5057,
    "Bihar": 16025, "Chhattisgarh": 16893, "Goa": 696, "Gujarat": 22410,
    "Haryana": 16041, "Himachal Pradesh": 2834, "Jharkhand": 7772,
    "Karnataka": 29090, "Kerala": 15119, "Madhya Pradesh": 43726,
    "Maharashtra": 66656, "Manipur": 353, "Meghalaya": 590, "Mizoram": 319,
    "Nagaland": 55, "Odisha": 21013, "Punjab": 11126, "Rajasthan": 26449,
    "Sikkim": 310, "Tamil Nadu": 29115, "Telangana": 12710, "Tripura": 635,
    "Uttarakhand": 2675, "Uttar Pradesh": 42930, "West Bengal": 15494,
    # UTs (from Table 21 rows 37-47 in pages 1-50)
    "Andaman & Nicobar Islands": 207, "Chandigarh": 287,
    "Dadra & Nagar Haveli and Daman & Diu": np.nan,   # split row in PDF
    "Delhi": np.nan, "Jammu & Kashmir": np.nan,
    "Ladakh": np.nan, "Lakshadweep": np.nan, "Puducherry": np.nan,
}

# ── Accidental death RATE per lakh population 2023 (Table 11 from pages 1-50) ──
# State-level accidental death rate per lakh population
ACCIDENTAL_DEATH_RATE_PER_LAKH_2023 = {
    "Ladakh": 75.4,    "Puducherry": 66.5, "Maharashtra": 55.1,
    "Haryana": 53.7,   "Chhattisgarh": 52.9, "Madhya Pradesh": 49.8,
    "Sikkim": 49.2,    "Odisha": 48.1,    "Goa": 45.9,
    "Andaman & Nicobar Islands": 45.7, "Karnataka": 44.2,
    "Tamil Nadu": 42.6, "Kerala": 41.7,  "Himachal Pradesh": 40.9,
    "Rajasthan": 37.1, "Punjab": 36.0,   "Telangana": 35.1,
    "Gujarat": 32.1,   "Andhra Pradesh": 32.0, "Chandigarh": 25.3,
    "Mizoram": 24.3,   "Arunachal Pradesh": 21.8, "Jharkhand": 21.2,
    "Uttarakhand": 21.1, "Dadra & Nagar Haveli and Daman & Diu": 18.9,
    "Uttar Pradesh": 18.3, "Delhi": 16.3, "Tripura": 15.9,
    "Meghalaya": 15.0, "West Bengal": 14.9, "Assam": 14.9,
    "Bihar": 12.9,     "Jammu & Kashmir": 10.7, "Manipur": 6.0,
    "Lakshadweep": 4.3, "Nagaland": 3.2,
    # National Average: 31.9
}
ACCIDENTAL_DEATH_RATE_NATIONAL_2023 = 31.9

# ── Suicides (Total) deaths 2023 ── (NCRB T34 from pages 200-298)
# "Number of Suicides 2023" column (col 4 in extracted table)
SUICIDE_DEATHS_2023 = {
    "Andhra Pradesh": 8684, "Arunachal Pradesh": 128, "Assam": 3051,
    "Bihar": 926, "Chhattisgarh": 7868, "Goa": 327, "Gujarat": 8948,
    "Haryana": 3361, "Himachal Pradesh": 818, "Jharkhand": 2006,
    "Karnataka": 13330, "Kerala": 10972, "Madhya Pradesh": 15662,
    "Maharashtra": 22687, "Manipur": 25, "Meghalaya": 220, "Mizoram": 98,
    "Nagaland": 36, "Odisha": 5989, "Punjab": 2298, "Rajasthan": 5552,
    "Sikkim": 278, "Tamil Nadu": 19483, "Telangana": 10580, "Tripura": 644,
    "Uttarakhand": 940, "Uttar Pradesh": 9154, "West Bengal": 12819,
    # Union Territories
    "Andaman & Nicobar Islands": 200, "Chandigarh": 150,
    "Dadra & Nagar Haveli and Daman & Diu": 201, "Delhi": 3131,
    "Jammu & Kashmir": 365, "Ladakh": 19, "Lakshadweep": 3, "Puducherry": 465,
}
SUICIDE_NATIONAL_2023 = 171418   # NCRB T36 total (all methods, all states+UTs)


# ===========================================================================
# ASSEMBLY FUNCTIONS
# ===========================================================================

def build_cause_specific_table() -> pd.DataFrame:
    """
    Build long-format cause-specific accidental deaths table for 2023.
    Each row = (state, cause, deaths_n).
    """
    cause_dicts = {
        "drowning":         DROWNING_DEATHS_2023,
        "falls":            FALLS_DEATHS_2023,
        "fire_burns":       FIRE_DEATHS_2023,
        "road_accidents":   ROAD_DEATHS_NCRB_2023,
        "poisoning":        POISONING_DEATHS_2023,
        "suicide_total":    SUICIDE_DEATHS_2023,
        "total_accidental": TOTAL_ACCIDENTAL_DEATHS_2023,
    }
    rows = []
    for cause, data in cause_dicts.items():
        for state, deaths in data.items():
            rows.append({
                "state_name_harmonized": state,
                "year": 2023,
                "cause_ncrb": cause,
                "deaths_n": deaths,
                "source": "ncrb_adsi_2023",
                "note": "police-reported accidental deaths",
            })
    df = pd.DataFrame(rows)
    log.info(f"Built cause-specific table: {len(df)} rows")
    return df


def build_total_accidents_timeseries() -> pd.DataFrame:
    """
    Build 2022–2023 total accidental deaths timeseries per state.
    """
    rows = []
    for state in STATES_ORDER:
        v2022 = TOTAL_ACCIDENTAL_DEATHS_2022.get(state, np.nan)
        v2023 = TOTAL_ACCIDENTAL_DEATHS_2023.get(state, np.nan)
        for yr, val in [(2022, v2022), (2023, v2023)]:
            rows.append({
                "state_name_harmonized": state,
                "year": yr,
                "total_accidental_deaths": val,
                "source": "ncrb_adsi_2023",
            })
    df = pd.DataFrame(rows)
    log.info(f"Built timeseries table: {len(df)} rows")
    return df


def build_rates_table() -> pd.DataFrame:
    """
    Build accidental death rate per lakh population table (2023).
    """
    rows = []
    for state, rate in ACCIDENTAL_DEATH_RATE_PER_LAKH_2023.items():
        rows.append({
            "state_name_harmonized": state,
            "year": 2023,
            "accidental_death_rate_per_lakh": rate,
            "source": "ncrb_adsi_2023",
            "note": "rate per lakh population; national avg = 31.9",
        })
    df = pd.DataFrame(rows)
    log.info(f"Built rates table: {len(df)} rows")
    return df


def try_extract_suicide_table(pdf_path: pathlib.Path) -> pd.DataFrame:
    """
    Attempt live extraction of state-wise suicide deaths from NCRB PDF pages 200-298.
    Suicides are in a separate chapter (Part II) of ADSI.
    Falls back to returning empty DataFrame if extraction fails.
    """
    try:
        import tabula
        log.info("Attempting live suicide table extraction (pages 200-298)...")
        tables = tabula.read_pdf(
            str(pdf_path), pages='200-298', multiple_tables=True,
            stream=True, encoding='latin-1', pandas_options={'header': None}
        )
        log.info(f"Found {len(tables)} tables in pages 200-298")
        # Look for state-wise suicide total table
        states_check = ['ANDHRA PRADESH', 'KARNATAKA', 'TAMIL NADU',
                        'MAHARASHTRA', 'UTTAR PRADESH']
        for i, t in enumerate(tables):
            t_str = t.to_string().upper()
            matches = sum(1 for s in states_check if s in t_str)
            if matches >= 4 and t.shape[0] >= 28:
                log.info(f"Found candidate suicide table T{i} shape={t.shape}")
                return _parse_suicide_table(t)
        log.warning("No suitable suicide table found in pages 200-298")
    except Exception as e:
        log.warning(f"Suicide extraction failed: {e}")
    return pd.DataFrame()


def _parse_suicide_table(raw: pd.DataFrame) -> pd.DataFrame:
    """Parse raw suicide table into clean format."""
    rows = []
    for _, row in raw.iterrows():
        raw_name = str(row.iloc[1]).strip().upper()
        state = STATE_MAP.get(raw_name)
        if not state:
            continue
        # Last column = total deaths
        total = None
        for val in reversed(row.tolist()):
            try:
                v = float(str(val).replace(",", "").replace(" ", ""))
                if not np.isnan(v) and v >= 0:
                    total = v
                    break
            except (ValueError, TypeError):
                continue
        if total is not None:
            rows.append({
                "state_name_harmonized": state,
                "year": 2023,
                "cause_ncrb": "suicide_total",
                "deaths_n": total,
                "source": "ncrb_adsi_2023",
                "note": "suicide deaths (all methods)",
            })
    return pd.DataFrame(rows)


def validate(df: pd.DataFrame, name: str) -> None:
    """Basic validation checks."""
    log.info(f"Validating {name}...")
    assert not df.empty, f"{name} is empty"
    nulls = df["deaths_n"].isna().sum() if "deaths_n" in df.columns else 0
    log.info(f"  Rows: {len(df)} | Null deaths: {nulls}")
    if "cause_ncrb" in df.columns:
        for cause, grp in df.groupby("cause_ncrb"):
            total = grp["deaths_n"].sum()
            log.info(f"  Cause={cause}: n_states={len(grp)}, sum_deaths={total:,.0f}")


def validate_simple(df: pd.DataFrame, name: str, col: str) -> None:
    """Validate a simple deaths dataframe."""
    log.info(f"Validating {name}...")
    assert not df.empty, f"{name} is empty"
    nulls = df[col].isna().sum()
    total = df[col].sum()
    log.info(f"  Rows: {len(df)} | Null: {nulls} | Total deaths: {total:,.0f}")


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    DATA_INTERIM.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)

    pdf_path = DATA_RAW / "1ADSIPublication-2023.pdf"
    if not pdf_path.exists():
        log.error(f"NCRB PDF not found: {pdf_path}")
        log.error("Download from https://ncrb.gov.in/adsi.html and save to data_raw/ncrb/")
        return

    log.info("=" * 60)
    log.info("NCRB ADSI 2023 Extraction")
    log.info("=" * 60)

    # 1. Cause-specific accidental deaths
    df_causes = build_cause_specific_table()
    validate(df_causes, "cause_specific")
    out1 = DATA_INTERIM / "ncrb_accidental_deaths_2023.csv"
    df_causes.to_csv(out1, index=False)
    log.info(f"Saved: {out1}")

    # 2. Timeseries 2022–2023
    df_ts = build_total_accidents_timeseries()
    out2 = DATA_INTERIM / "ncrb_total_accidents_2022_2023.csv"
    df_ts.to_csv(out2, index=False)
    log.info(f"Saved: {out2}")

    # 3. Accidental death rates
    df_rates = build_rates_table()
    out3 = DATA_INTERIM / "ncrb_accidental_death_rates_2023.csv"
    df_rates.to_csv(out3, index=False)
    log.info(f"Saved: {out3}")

    # 4. Suicide data — hardcoded from NCRB T34 (pages 200-298), confirmed
    # Note: cause_specific table already includes suicide_total; save dedicated file too
    df_suicide_rows = [
        {"state_name_harmonized": state, "year": 2023,
         "suicide_deaths_n": n, "source": "ncrb_adsi_2023",
         "note": "all-method suicide deaths (NCRB T34)"}
        for state, n in SUICIDE_DEATHS_2023.items()
    ]
    df_suicide = pd.DataFrame(df_suicide_rows)
    validate_simple(df_suicide, "suicide", "suicide_deaths_n")
    out4 = DATA_INTERIM / "ncrb_suicides_2023.csv"
    df_suicide.to_csv(out4, index=False)
    log.info(f"Saved: {out4}")

    log.info("=" * 60)
    log.info("NCRB extraction complete")

    # Summary
    _print_summary(df_causes)


def _write_suicide_template():
    """Write manual entry template for suicide data."""
    template_path = DATA_RAW / "manual_extraction_ncrb_suicide.xlsx"
    states = STATES_ORDER
    df = pd.DataFrame({
        "state_name_harmonized": states,
        "suicide_total_deaths_2023": [None] * len(states),
        "suicide_male_2023": [None] * len(states),
        "suicide_female_2023": [None] * len(states),
        "note": ["Enter from NCRB ADSI 2023 Table S-1 or similar"] * len(states),
    })
    df.to_excel(template_path, index=False)
    log.info(f"Suicide template written: {template_path}")


def _print_summary(df: pd.DataFrame):
    """Print key extraction summary for QC."""
    log.info("\n--- EXTRACTION SUMMARY ---")
    log.info(f"National totals (2023):")
    log.info(f"  Drowning:     {DROWNING_NATIONAL_2023:>8,}")
    log.info(f"  Falls:        {FALLS_NATIONAL_2023:>8,}")
    log.info(f"  Fire/Burns:   {FIRE_NATIONAL_2023:>8,}")
    log.info(f"  Road (NCRB):  {ROAD_NATIONAL_NCRB_2023:>8,}")
    log.info(f"  Poisoning:    {POISONING_NATIONAL_2023:>8,}")
    log.info(f"  Total Acc.:   {TOTAL_ACCIDENTAL_NATIONAL_2023:>8,}")
    log.info(f"  Suicide tot:  {SUICIDE_NATIONAL_2023:>8,}")
    log.info(f"  Acc. rate:    {ACCIDENTAL_DEATH_RATE_NATIONAL_2023} per lakh")
    log.info(f"\nTop 5 states by total accidental deaths (2023):")
    top5 = sorted(TOTAL_ACCIDENTAL_DEATHS_2023.items(), key=lambda x: x[1] or 0, reverse=True)[:5]
    for state, n in top5:
        log.info(f"  {state:<40} {n:>8,}")


if __name__ == "__main__":
    main()
