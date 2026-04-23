"""
State Name Harmonization
Applies the master state crosswalk to all datasets, ensuring consistent
state names across GBD, MoRTH, and NCRB sources.
Logs all name changes and flags unmatched entries.
"""

import pathlib
import pandas as pd
import logging
import csv
import re
import datetime

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
DOCS = PROJECT_ROOT / "docs"
DATA_INTERIM = PROJECT_ROOT / "data_interim"
LOGS = PROJECT_ROOT / "logs"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOGS / "05_harmonize_states.log"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)


def load_crosswalk() -> dict:
    """Load state crosswalk and build mapping dictionaries."""
    cw_path = DOCS / "state_crosswalk.csv"
    cw = pd.read_csv(cw_path)

    # Build: any source name → harmonized name
    # GBD names, MoRTH names, NCRB names all map to state_name_harmonized
    mapping = {}
    for _, row in cw.iterrows():
        harmonized = row["state_name_harmonized"]
        for col in ["state_name_harmonized", "gbd_name", "morth_name", "ncrb_name"]:
            val = str(row[col]).strip() if pd.notna(row[col]) and str(row[col]) != "nan" else None
            if val:
                mapping[val.lower()] = harmonized
                mapping[val] = harmonized  # exact match too

    # GBD 2023 combines J&K and Ladakh as a single subnational unit
    mapping["Jammu & Kashmir and Ladakh"] = "Jammu & Kashmir"
    mapping["jammu & kashmir and ladakh"] = "Jammu & Kashmir"
    mapping["Other Union Territories"] = "Other Union Territories"  # keep as-is
    mapping["India"] = "India"  # national aggregate — kept but excluded in analysis
    log.info(f"Crosswalk loaded: {len(cw)} states/UTs, {len(mapping)} name variants")
    return mapping, cw


def normalize_state_name(name: str) -> str:
    """Light normalization for fuzzy matching."""
    if not isinstance(name, str):
        return ""
    name = name.strip()
    name = re.sub(r"\s+", " ", name)
    return name


def apply_harmonization(df: pd.DataFrame, state_col: str, mapping: dict,
                         dataset_name: str) -> tuple[pd.DataFrame, list[dict]]:
    audit_rows = []
    harmonized_names = []

    for raw_name in df[state_col]:
        norm = normalize_state_name(str(raw_name))
        # Try exact match first
        harmonized = mapping.get(norm)
        # Try lowercase
        if harmonized is None:
            harmonized = mapping.get(norm.lower())
        # Try stripped version
        if harmonized is None:
            harmonized = mapping.get(norm.replace("&", "and").lower())

        if harmonized is None:
            log.warning(f"[{dataset_name}] UNMATCHED state name: '{raw_name}'")
            audit_rows.append({
                "dataset": dataset_name,
                "raw_name": raw_name,
                "harmonized_name": "UNMATCHED",
                "action": "FLAG",
                "timestamp": datetime.datetime.now().isoformat(),
            })
            harmonized_names.append(raw_name)  # keep original if unmatched
        else:
            if harmonized != norm:
                audit_rows.append({
                    "dataset": dataset_name,
                    "raw_name": raw_name,
                    "harmonized_name": harmonized,
                    "action": "RENAMED",
                    "timestamp": datetime.datetime.now().isoformat(),
                })
            harmonized_names.append(harmonized)

    df = df.copy()
    df["state_name_harmonized"] = harmonized_names
    return df, audit_rows


def write_audit_log(audit_rows: list[dict]):
    log_path = LOGS / "state_name_harmonization_log.csv"
    fieldnames = ["dataset", "raw_name", "harmonized_name", "action", "timestamp"]
    with open(log_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(audit_rows)
    log.info(f"Harmonization audit log: {log_path} ({len(audit_rows)} entries)")


def run():
    log.info("=== State Harmonization: Start ===")
    mapping, cw = load_crosswalk()
    all_audit = []

    datasets = {
        "gbd": ("gbd_raw_combined.csv", "location_name"),
        "morth": ("morth_raw.csv", "state_name_raw"),
        "ncrb_accidental": ("ncrb_accidental_raw.csv", "state_name_raw"),
        "ncrb_suicide": ("ncrb_suicide_raw.csv", "state_name_raw"),
    }

    for dataset_name, (filename, state_col) in datasets.items():
        fpath = DATA_INTERIM / filename
        if not fpath.exists():
            log.warning(f"File not found: {fpath} (skipping — will process when available)")
            continue

        df = pd.read_csv(fpath, low_memory=False)
        if state_col not in df.columns:
            log.warning(f"Column '{state_col}' not in {filename}; skipping")
            continue

        df, audit_rows = apply_harmonization(df, state_col, mapping, dataset_name)
        all_audit.extend(audit_rows)

        out_path = DATA_INTERIM / f"{dataset_name}_harmonized.csv"
        df.to_csv(out_path, index=False)
        log.info(f"Harmonized dataset: {out_path} ({len(df):,} rows)")

    write_audit_log(all_audit)
    unmatched = [r for r in all_audit if r["action"] == "FLAG"]
    if unmatched:
        log.warning(f"Total unmatched state names: {len(unmatched)} — review harmonization log")
    else:
        log.info("All state names successfully harmonized.")

    log.info("=== State Harmonization: Complete ===")


if __name__ == "__main__":
    run()
