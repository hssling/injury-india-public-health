"""
Master Dataset Assembly
Combines harmonized GBD, MoRTH, and NCRB data into a single long-format
master dataset with standardized schema.

Schema:
  state_name_harmonized | state_code | year | sex | age_group | cause_group |
  measure | metric_type | value | lower_ui | upper_ui | source | note
"""

import pathlib
import pandas as pd
import logging
import datetime

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_INTERIM = PROJECT_ROOT / "data_interim"
DATA_PROCESSED = PROJECT_ROOT / "data_processed"
LOGS = PROJECT_ROOT / "logs"
DATA_PROCESSED.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOGS / "08_assemble_master.log"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)

MASTER_SCHEMA = [
    "state_name_harmonized",
    "year",
    "sex",
    "age_group",
    "cause_group",
    "cause_gbd",
    "measure",
    "metric_type",
    "value",
    "lower_ui",
    "upper_ui",
    "source",
    "note",
]


def load_gbd() -> pd.DataFrame:
    fpath = DATA_INTERIM / "gbd_harmonized.csv"
    if not fpath.exists():
        fpath = DATA_INTERIM / "gbd_raw_combined.csv"
        log.warning(f"Harmonized GBD not found; using raw: {fpath}")
    if not fpath.exists():
        log.warning("No GBD data found. Run ingest steps first.")
        return pd.DataFrame()

    df = pd.read_csv(fpath, low_memory=False)
    log.info(f"GBD loaded: {len(df):,} rows")

    # Standardize to master schema
    col_map = {
        "measure": "measure",
        "location_name": "state_name_harmonized",
        "state_name_harmonized": "state_name_harmonized",
        "sex": "sex",
        "age_group": "age_group",
        "cause_group": "cause_group",
        "cause_gbd": "cause_gbd",
        "metric_type": "metric_type",
        "value": "value",
        "lower_ui": "lower_ui",
        "upper_ui": "upper_ui",
        "year": "year",
    }

    rename = {k: v for k, v in col_map.items() if k in df.columns and k != v}
    df = df.rename(columns=rename)
    df["source"] = "gbd2021"
    if "note" not in df.columns:
        df["note"] = ""

    # Keep only needed cols
    available = [c for c in MASTER_SCHEMA if c in df.columns]
    return df[available].copy()


def load_morth() -> pd.DataFrame:
    """Load MoRTH road accident and death data from extracted interim files."""
    rows = []

    # Road accidents (all 36 states, 2020-2023) from 05_extract_morth_tables.py
    acc_path = DATA_INTERIM / "morth_state_accidents.csv"
    if acc_path.exists():
        acc = pd.read_csv(acc_path)
        for _, row in acc.iterrows():
            rows.append({
                "state_name_harmonized": row["state_name_harmonized"],
                "year": row["year"],
                "sex": "both", "age_group": "all ages",
                "cause_group": "road", "cause_gbd": "",
                "measure": "Accidents", "metric_type": "Number",
                "value": row.get("road_accidents_n", float("nan")),
                "lower_ui": "", "upper_ui": "",
                "source": "morth2023",
                "note": "MoRTH Table 42 — road accidents by state",
            })
        log.info(f"MoRTH accidents loaded: {len(acc)} state-year rows")

    # Road deaths — partial (top states + national total)
    for deaths_file in ["morth_state_deaths_partial.csv", "morth_deaths_pdf_extract.csv"]:
        dpath = DATA_INTERIM / deaths_file
        if dpath.exists():
            deaths = pd.read_csv(dpath)
            for _, row in deaths.iterrows():
                rows.append({
                    "state_name_harmonized": row.get("state_name_harmonized", ""),
                    "year": row.get("year", 2023),
                    "sex": "both", "age_group": "all ages",
                    "cause_group": "road", "cause_gbd": "",
                    "measure": "Deaths", "metric_type": "Number",
                    "value": row.get("road_deaths_n", float("nan")),
                    "lower_ui": "", "upper_ui": "",
                    "source": "morth2023",
                    "note": f"MoRTH road deaths (source: {deaths_file})",
                })
            log.info(f"MoRTH deaths loaded from {deaths_file}: {len(deaths)} rows")
            break  # use first available file

    if not rows:
        log.warning("No MoRTH data found. Run src/ingest/05_extract_morth_tables.py first.")
        return pd.DataFrame(columns=MASTER_SCHEMA)

    out = pd.DataFrame(rows)
    out = out[out["value"].notna() & (out["value"] > 0)]
    log.info(f"MoRTH total long-format rows: {len(out):,}")
    return out


def load_ncrb() -> pd.DataFrame:
    """Load NCRB cause-specific deaths and suicides from extracted interim files."""
    rows = []

    # NCRB cause-specific accidental deaths (ncrb_accidental_deaths_2023.csv)
    # Schema: state_name_harmonized, year, cause_ncrb, deaths_n, source, note
    CAUSE_NCRB_MAP = {
        "drowning":         "drowning",
        "falls":            "falls",
        "fire_burns":       "burns",
        "road_accidents":   "road",
        "poisoning":        "poisoning",
        "suicide_total":    "self_harm",
        "total_accidental": "all_injuries",
    }

    acc_path = DATA_INTERIM / "ncrb_accidental_deaths_2023.csv"
    if acc_path.exists():
        acc = pd.read_csv(acc_path)
        for _, row in acc.iterrows():
            cause_ncrb = row.get("cause_ncrb", "")
            cause_group = CAUSE_NCRB_MAP.get(cause_ncrb, cause_ncrb)
            # suicide_total is in both files; skip here to avoid duplicates
            if cause_ncrb == "suicide_total":
                continue
            measure = "Suicides" if cause_ncrb == "suicide_total" else "Accidental Deaths"
            rows.append({
                "state_name_harmonized": row["state_name_harmonized"],
                "year": row["year"],
                "sex": "both", "age_group": "all ages",
                "cause_group": cause_group, "cause_gbd": "",
                "measure": measure, "metric_type": "Number",
                "value": row["deaths_n"],
                "lower_ui": "", "upper_ui": "",
                "source": "ncrb2023",
                "note": str(row.get("note", "")),
            })
        log.info(f"NCRB accidental deaths loaded: {len(acc)} rows")

    # NCRB suicides (dedicated file)
    sui_path = DATA_INTERIM / "ncrb_suicides_2023.csv"
    if sui_path.exists():
        sui = pd.read_csv(sui_path)
        for _, row in sui.iterrows():
            rows.append({
                "state_name_harmonized": row["state_name_harmonized"],
                "year": row["year"],
                "sex": "both", "age_group": "all ages",
                "cause_group": "self_harm", "cause_gbd": "",
                "measure": "Suicides", "metric_type": "Number",
                "value": row["suicide_deaths_n"],
                "lower_ui": "", "upper_ui": "",
                "source": "ncrb2023",
                "note": "all-method suicides (NCRB ADSI T34)",
            })
        log.info(f"NCRB suicides loaded: {len(sui)} rows")

    if not rows:
        log.warning("No NCRB data found. Run src/ingest/06_extract_ncrb_tables.py first.")
        return pd.DataFrame(columns=MASTER_SCHEMA)

    out = pd.DataFrame(rows)
    out = out[out["value"].notna()]
    log.info(f"NCRB total long-format rows: {len(out):,}")
    return out


def run_qc(df: pd.DataFrame) -> dict:
    """Run QC checks on master dataset."""
    issues = {}

    # Duplicates — use cause_gbd (specific) not cause_group (aggregated) as key
    id_cols = ["state_name_harmonized", "year", "sex", "age_group",
               "cause_gbd", "cause_group", "measure", "metric_type", "source"]
    id_cols_present = [c for c in id_cols if c in df.columns]
    dupes = df.duplicated(subset=id_cols_present).sum()
    if dupes:
        issues["duplicates"] = dupes
        log.warning(f"[QC] Duplicate rows: {dupes}")

    # Missingness
    for col in ["state_name_harmonized", "measure", "value", "source"]:
        if col in df.columns:
            n_null = df[col].isna().sum()
            if n_null > 0:
                issues[f"null_{col}"] = n_null
                log.warning(f"[QC] Null in '{col}': {n_null}")

    # Negative values
    neg = (pd.to_numeric(df["value"], errors="coerce") < 0).sum()
    if neg:
        issues["negative_values"] = neg
        log.warning(f"[QC] Negative values: {neg}")

    if not issues:
        log.info("[QC] Master dataset passed all checks.")
    return issues


def run():
    log.info("=== Master Assembly: Start ===")

    gbd = load_gbd()
    morth = load_morth()
    ncrb = load_ncrb()

    def _align(df: pd.DataFrame) -> pd.DataFrame:
        """Force each frame to exactly MASTER_SCHEMA columns, eliminating any dups."""
        # Build column-by-column to avoid pandas reindex issues with dup cols
        data = {}
        for col in MASTER_SCHEMA:
            if col in df.columns:
                # If somehow duplicated, take first occurrence
                col_data = df[col]
                if isinstance(col_data, pd.DataFrame):
                    col_data = col_data.iloc[:, 0]
                data[col] = col_data.values
            else:
                data[col] = [""] * len(df)
        return pd.DataFrame(data)

    frames = [_align(f) for f in [gbd, morth, ncrb] if not f.empty]

    if not frames:
        log.error("No data loaded. Run ingest and harmonization steps first.")
        return pd.DataFrame(columns=MASTER_SCHEMA)

    master = pd.concat(frames, ignore_index=True)
    master["value"] = pd.to_numeric(master["value"], errors="coerce")
    master["year"] = pd.to_numeric(master["year"], errors="coerce")

    log.info(f"Master dataset assembled: {len(master):,} rows")
    log.info(f"Sources: {master['source'].value_counts().to_dict()}")
    log.info(f"Measures: {master['measure'].unique()}")
    log.info(f"Years: {sorted(master['year'].dropna().unique())}")

    qc_issues = run_qc(master)

    # Save outputs
    out_csv = DATA_PROCESSED / "master_dataset.csv"
    master.to_csv(out_csv, index=False)
    log.info(f"Master CSV: {out_csv}")

    try:
        out_parquet = DATA_PROCESSED / "master_dataset.parquet"
        master.to_parquet(out_parquet, index=False)
        log.info(f"Master Parquet: {out_parquet}")
    except Exception as e:
        log.warning(f"Parquet write failed: {e}")

    # QC summary
    qc_path = LOGS / "master_qc_log.txt"
    with open(qc_path, "w") as f:
        f.write(f"Master QC Report — {datetime.datetime.now().isoformat()}\n")
        f.write(f"Total rows: {len(master):,}\n")
        f.write(f"Sources: {master['source'].value_counts().to_dict()}\n")
        if qc_issues:
            f.write("ISSUES:\n")
            for k, v in qc_issues.items():
                f.write(f"  {k}: {v}\n")
        else:
            f.write("All QC checks passed.\n")
    log.info(f"QC log: {qc_path}")

    log.info("=== Master Assembly: Complete ===")
    return master


if __name__ == "__main__":
    run()
