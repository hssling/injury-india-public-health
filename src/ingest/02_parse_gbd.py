"""
GBD 2021 CSV Parser
Parses all GBD CSV exports from data_raw/gbd/, validates, standardizes, and outputs
a combined interim dataset.

Expected GBD CSV columns (standard GBD Results Tool export):
  measure_id, measure_name, location_id, location_name, sex_id, sex_name,
  age_id, age_name, cause_id, cause_name, metric_id, metric_name,
  year, val, upper, lower
"""

import pathlib
import pandas as pd
import logging
import datetime

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_RAW = PROJECT_ROOT / "data_raw" / "gbd"
DATA_INTERIM = PROJECT_ROOT / "data_interim"
LOGS = PROJECT_ROOT / "logs"
DATA_INTERIM.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOGS / "02_parse_gbd.log"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GBD injury cause mapping: GBD cause_name → analysis cause_group
# ---------------------------------------------------------------------------

CAUSE_MAP = {
    # All causes (present in downloaded file; injury-specific re-download pending)
    "All causes": "all_causes",
    # Level 1
    "Injuries": "all_injuries",
    # Level 2
    "Transport injuries": "transport_all",
    "Unintentional injuries": "unintentional_all",
    "Self-harm and interpersonal violence": "intentional_all",
    # Level 3 – Transport
    "Road injuries": "road",
    "Other transport injuries": "other_transport",
    # Level 3 – Unintentional
    "Falls": "falls",
    "Drowning": "drowning",
    "Burns and heat": "burns",
    "Fire, heat, and hot substances": "burns",
    "Poisonings": "poisoning",
    "Unintentional poisoning": "poisoning",
    "Other unintentional injuries": "other_unintentional",
    # Level 3 – Intentional
    "Self-harm": "self_harm",
    "Self-harm by firearm": "self_harm",
    "Self-harm by other specified means": "self_harm",
    "Interpersonal violence": "violence",
    "Physical violence by firearm": "violence",
    "Collective violence and other injuries": "collective_violence",
    # Level 3 – Additional unintentional (in GBD 2023 subnational India file)
    "Electrocution": "other_unintentional",
    "Environmental heat and cold exposure": "other_unintentional",
    "Exposure to forces of nature": "other_unintentional",
    "Exposure to mechanical forces": "other_unintentional",
    "Other exposure to mechanical forces": "other_unintentional",
    "Animal contact": "other_unintentional",
    "Venomous animal contact": "other_unintentional",
    "Non-venomous animal contact": "other_unintentional",
    "Foreign body": "other_unintentional",
    "Foreign body in eyes": "other_unintentional",
    "Foreign body in other body part": "other_unintentional",
    "Pulmonary aspiration and foreign body in airway": "other_unintentional",
    "Adverse effects of medical treatment": "other_unintentional",
    "Unintentional firearm injuries": "other_unintentional",
    # Road injury sub-types → all map to 'road'
    "Motor vehicle road injuries": "road",
    "Motorcyclist road injuries": "road",
    "Pedestrian road injuries": "road",
    "Cyclist road injuries": "road",
    "Other road injuries": "road",
}

# Accepted measures
MEASURES = {"Deaths", "DALYs", "YLLs", "YLDs", "Incidence", "Prevalence"}

# Accepted metrics
METRICS = {"Number", "Rate", "Percent"}

# Core India location names (adjust if GBD uses different spelling)
INDIA_LOCATIONS = {
    "India",
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
    "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
    "West Bengal",
    # UTs
    "Andaman and Nicobar Islands", "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
    # GBD alternate spellings / combined UTs
    "Jammu & Kashmir", "Dadra & Nagar Haveli and Daman & Diu",
    "Jammu & Kashmir and Ladakh",   # GBD 2023 treats as combined
    "Other Union Territories",
}


def load_gbd_csvs(data_dir: pathlib.Path) -> pd.DataFrame:
    csv_files = list(data_dir.glob("*.csv"))
    if not csv_files:
        log.warning(f"No CSV files found in {data_dir}. Download GBD data first.")
        log.warning("Instructions: run src/ingest/01_download_plan.py --instructions")
        return pd.DataFrame()

    log.info(f"Found {len(csv_files)} CSV file(s) in {data_dir}")
    dfs = []
    for f in csv_files:
        log.info(f"Reading: {f.name}")
        try:
            df = pd.read_csv(f, low_memory=False)
            df["_source_file"] = f.name
            dfs.append(df)
            log.info(f"  → {len(df):,} rows, columns: {list(df.columns)}")
        except Exception as e:
            log.error(f"Failed to read {f.name}: {e}")
    if not dfs:
        return pd.DataFrame()
    combined = pd.concat(dfs, ignore_index=True)
    log.info(f"Combined GBD data: {len(combined):,} rows")
    return combined


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename GBD columns to project standard names."""
    rename_map = {
        "measure_name": "measure",
        "location_name": "location_name",
        "sex_name": "sex",
        "age_name": "age_group",
        "cause_name": "cause_gbd",
        "metric_name": "metric_type",
        "year": "year",
        "val": "value",
        "lower": "lower_ui",
        "upper": "upper_ui",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    return df


def filter_india_locations(df: pd.DataFrame) -> pd.DataFrame:
    if "location_name" not in df.columns:
        log.error("'location_name' column not found in GBD data.")
        return df
    before = len(df)
    # Flexible match: keep rows where location_name is in our India set OR contains 'India'
    mask = df["location_name"].isin(INDIA_LOCATIONS) | df["location_name"].str.contains("India", na=False)
    df = df[mask].copy()
    after = len(df)
    log.info(f"Filtered to India locations: {before:,} → {after:,} rows")
    unknown = set(df["location_name"].unique()) - INDIA_LOCATIONS
    if unknown:
        log.warning(f"Location names not in crosswalk (check for new UTs or spelling): {unknown}")
    return df


def filter_injuries(df: pd.DataFrame) -> pd.DataFrame:
    """Keep injury-related causes; also retain 'All causes' if injury-specific unavailable."""
    if "cause_gbd" not in df.columns:
        log.error("'cause_gbd' column not found.")
        return df
    injury_keywords = ["injur", "transport", "road", "fall", "drown", "burn",
                       "poison", "self-harm", "self_harm", "violence", "fire", "heat",
                       "electro", "drowning", "all causes", "animal", "foreign",
                       "mechanical", "aspiration", "adverse", "firearm"]
    pattern = "|".join(injury_keywords)
    before = len(df)
    mask = df["cause_gbd"].str.lower().str.contains(pattern, na=False)
    df = df[mask].copy()
    after = len(df)
    log.info(f"Filtered to injury/all-causes: {before:,} → {after:,} rows")

    unique_causes = set(df["cause_gbd"].unique())
    injury_specific = unique_causes - {"All causes"}
    if not injury_specific:
        log.warning(
            "DATA GAP: Only 'All causes' GBD data present. "
            "Re-download GBD with injury cause filters for full analysis."
        )
    else:
        log.info(f"Injury-specific causes present: {len(injury_specific)} cause types")
        # Drop 'All causes' rows now that injury-specific data is available
        # (keep them only if no injury-specific data exists)
        all_causes_rows = (df["cause_gbd"] == "All causes").sum()
        if all_causes_rows > 0:
            df = df[df["cause_gbd"] != "All causes"].copy()
            log.info(f"Dropped {all_causes_rows} 'All causes' rows (superseded by injury-specific data)")
    return df


def add_cause_group(df: pd.DataFrame) -> pd.DataFrame:
    df["cause_group"] = df["cause_gbd"].map(CAUSE_MAP)
    unmapped = df[df["cause_group"].isna()]["cause_gbd"].unique()
    if len(unmapped) > 0:
        log.warning(f"Unmapped GBD causes (will be labeled 'other_unclassified'): {unmapped}")
        df.loc[df["cause_group"].isna(), "cause_group"] = "other_unclassified"
    return df


def validate_data(df: pd.DataFrame) -> pd.DataFrame:
    issues = []

    # Check for nulls in key fields
    key_fields = ["measure", "location_name", "sex", "age_group", "cause_gbd",
                  "metric_type", "year", "value"]
    for field in key_fields:
        if field in df.columns:
            null_count = df[field].isna().sum()
            if null_count > 0:
                issues.append(f"Null values in '{field}': {null_count:,} rows")

    # Check value range
    if "value" in df.columns:
        neg = (df["value"] < 0).sum()
        if neg > 0:
            issues.append(f"Negative values in 'value': {neg} rows")

    # Check year range
    if "year" in df.columns:
        min_y, max_y = df["year"].min(), df["year"].max()
        if min_y < 1990 or max_y > 2025:
            issues.append(f"Year range unexpected: {min_y}–{max_y}")

    # Check UI ordering
    if all(c in df.columns for c in ["value", "lower_ui", "upper_ui"]):
        bad_ui = ((df["lower_ui"] > df["value"]) | (df["upper_ui"] < df["value"])).sum()
        if bad_ui > 0:
            issues.append(f"Uncertainty interval ordering issue: {bad_ui} rows")

    # Check duplicates
    id_cols = [c for c in ["measure", "location_name", "sex", "age_group",
                            "cause_gbd", "metric_type", "year"] if c in df.columns]
    dupes = df.duplicated(subset=id_cols).sum()
    if dupes > 0:
        issues.append(f"Duplicate rows: {dupes}")

    if issues:
        log.warning("Data validation issues found:")
        for issue in issues:
            log.warning(f"  - {issue}")
    else:
        log.info("Data validation passed.")

    return df


def add_metadata(df: pd.DataFrame) -> pd.DataFrame:
    df["source"] = "gbd2021"
    df["data_year_extracted"] = datetime.date.today().isoformat()
    return df


def run():
    log.info("=== GBD 2021 Parser: Start ===")

    df = load_gbd_csvs(DATA_RAW)

    if df.empty:
        log.warning("No GBD data to process. Please download GBD files first.")
        log.warning("See instructions in src/ingest/01_download_plan.py")
        # Create a placeholder output with the expected schema
        placeholder = pd.DataFrame(columns=[
            "measure", "location_name", "sex", "age_group", "cause_gbd",
            "cause_group", "metric_type", "year", "value", "lower_ui", "upper_ui",
            "source", "data_year_extracted", "_source_file"
        ])
        out_path = DATA_INTERIM / "gbd_raw_combined.csv"
        placeholder.to_csv(out_path, index=False)
        log.info(f"Placeholder schema written to: {out_path}")
        return placeholder

    df = standardize_columns(df)
    df = filter_india_locations(df)
    df = filter_injuries(df)
    df = add_cause_group(df)
    df = validate_data(df)
    df = add_metadata(df)

    # Output
    out_csv = DATA_INTERIM / "gbd_raw_combined.csv"
    df.to_csv(out_csv, index=False)
    log.info(f"Output written: {out_csv} ({len(df):,} rows)")

    try:
        out_parquet = DATA_INTERIM / "gbd_raw_combined.parquet"
        df.to_parquet(out_parquet, index=False)
        log.info(f"Parquet written: {out_parquet}")
    except Exception as e:
        log.warning(f"Parquet write failed (install pyarrow if needed): {e}")

    log.info("=== GBD 2021 Parser: Complete ===")
    return df


if __name__ == "__main__":
    run()
