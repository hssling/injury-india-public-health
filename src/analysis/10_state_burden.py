"""
State-Level Burden Analysis (Step 4B)
Computes state-wise deaths, DALYs, YLLs, YLDs for all injuries (2021).
Outputs ranked tables for Table 1 and supplementary tables.
"""

import pathlib
import pandas as pd
import numpy as np
import logging

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_PROCESSED = PROJECT_ROOT / "data_processed"
OUTPUTS = PROJECT_ROOT / "outputs"
TABLES = PROJECT_ROOT / "tables"
LOGS = PROJECT_ROOT / "logs"
OUTPUTS.mkdir(exist_ok=True)
TABLES.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOGS / "10_state_burden.log"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)


def load_master() -> pd.DataFrame:
    fpath = DATA_PROCESSED / "master_dataset.csv"
    if not fpath.exists():
        log.error(f"Master dataset not found: {fpath}")
        log.error("Run: python src/clean/08_assemble_master.py")
        return pd.DataFrame()
    df = pd.read_csv(fpath, low_memory=False)
    log.info(f"Master dataset loaded: {len(df):,} rows")
    return df


def get_gbd_state_burden(df: pd.DataFrame, year: int = 2021) -> pd.DataFrame:
    """Extract state-level injury burden metrics from GBD for a given year."""
    gbd = df[
        (df["source"] == "gbd2021") &
        (df["year"] == year) &
        (df["cause_group"] == "all_injuries") &
        (df["sex"] == "Both") &
        (df["age_group"] == "All ages") &
        (df["state_name_harmonized"] != "India")  # exclude national aggregate
    ].copy()

    if gbd.empty:
        log.warning(f"No GBD state data found for year={year}, cause=all_injuries, sex=Both, age=All ages")
        log.warning("Check that GBD data has been downloaded and parsed correctly.")
        return pd.DataFrame()

    # Pivot: measure × metric_type
    pivot = gbd.pivot_table(
        index="state_name_harmonized",
        columns=["measure", "metric_type"],
        values="value",
        aggfunc="first"
    )
    pivot.columns = ["_".join(str(c) for c in col).lower().replace(" ", "_") for col in pivot.columns]
    pivot = pivot.reset_index()
    return pivot


def get_ncrb_state_burden(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fallback: build state burden table from NCRB 2023 accidental deaths
    when GBD injury-specific data is not available.
    Uses: total_accidental deaths (n) + accidental death rate per lakh.
    """
    DATA_INTERIM = PROJECT_ROOT / "data_interim"

    # Load cause-specific NCRB deaths
    ncrb_path = DATA_INTERIM / "ncrb_accidental_deaths_2023.csv"
    rates_path = DATA_INTERIM / "ncrb_accidental_death_rates_2023.csv"

    if not ncrb_path.exists():
        return pd.DataFrame()

    ncrb = pd.read_csv(ncrb_path)
    # Filter to total accidental only
    total = ncrb[ncrb["cause_ncrb"] == "total_accidental"][
        ["state_name_harmonized", "deaths_n"]
    ].rename(columns={"deaths_n": "accidental_deaths_n_2023"})

    # Cause breakdown: pivot to wide for decomposition columns
    causes = ncrb[ncrb["cause_ncrb"] != "total_accidental"].pivot_table(
        index="state_name_harmonized", columns="cause_ncrb", values="deaths_n", aggfunc="first"
    ).reset_index()

    result = total.merge(causes, on="state_name_harmonized", how="left")

    # Add rates if available
    if rates_path.exists():
        rates = pd.read_csv(rates_path)[["state_name_harmonized", "accidental_death_rate_per_lakh"]]
        result = result.merge(rates, on="state_name_harmonized", how="left")

    result = result.sort_values("accidental_deaths_n_2023", ascending=False).reset_index(drop=True)
    result.insert(0, "rank_ncrb_deaths", range(1, len(result) + 1))
    result["data_source"] = "ncrb_adsi_2023"
    result["year"] = 2023
    result["note"] = "GBD injury-specific data pending re-download; NCRB deaths used for ranking"
    log.info(f"NCRB fallback burden table: {len(result)} states")
    return result


def create_state_summary_table(df: pd.DataFrame, year: int = 2021) -> pd.DataFrame:
    """Build a clean ranked summary table for Table 1."""
    pivot = get_gbd_state_burden(df, year)
    if pivot.empty:
        log.warning("GBD injury-specific data not available — using NCRB 2023 deaths as fallback.")
        return get_ncrb_state_burden(df)

    # Identify and rename columns robustly
    col_map = {}
    for col in pivot.columns:
        if "deaths" in col and "number" in col:
            col_map[col] = "deaths_number"
        elif "deaths" in col and "rate" in col and "age" in col:
            col_map[col] = "deaths_asr"
        elif "deaths" in col and "rate" in col:
            col_map[col] = "deaths_rate"
        elif "dalys" in col and "number" in col:
            col_map[col] = "dalys_number"
        elif "dalys" in col and "rate" in col and "age" in col:
            col_map[col] = "dalys_asr"
        elif "dalys" in col and "rate" in col:
            col_map[col] = "dalys_rate"
        elif "ylls" in col and "number" in col:
            col_map[col] = "ylls_number"
        elif "ylls" in col and "rate" in col:
            col_map[col] = "ylls_rate"
        elif "ylds" in col and "number" in col:
            col_map[col] = "ylds_number"
        elif "ylds" in col and "rate" in col:
            col_map[col] = "ylds_rate"

    pivot = pivot.rename(columns=col_map)

    if "dalys_asr" in pivot.columns:
        pivot = pivot.sort_values("dalys_asr", ascending=False).reset_index(drop=True)
        pivot.insert(0, "rank_daly", range(1, len(pivot) + 1))

    return pivot


def identify_top_bottom(df: pd.DataFrame, col: str, n: int = 5) -> dict:
    """Return top and bottom N states by a given column."""
    if col not in df.columns:
        return {}
    sorted_df = df.sort_values(col, ascending=False).dropna(subset=[col])
    return {
        "top": sorted_df.head(n)[["state_name_harmonized", col]].to_dict("records"),
        "bottom": sorted_df.tail(n)[["state_name_harmonized", col]].to_dict("records"),
    }


def run():
    log.info("=== State Burden Analysis: Start ===")

    df = load_master()
    if df.empty:
        log.warning("No data available. Outputs will be empty placeholders.")
        return

    summary = create_state_summary_table(df, year=2021)

    # Save
    out_csv = OUTPUTS / "state_burden_2021.csv"
    summary.to_csv(out_csv, index=False)
    log.info(f"State burden summary: {out_csv}")

    # Excel table for manuscript
    try:
        out_xlsx = TABLES / "Table1_state_burden.xlsx"
        with pd.ExcelWriter(str(out_xlsx), engine="openpyxl") as writer:
            summary.to_excel(writer, sheet_name="State_Burden_2021", index=False)
        log.info(f"Table 1: {out_xlsx}")
    except Exception as e:
        log.warning(f"Excel write failed: {e}")

    # Top/bottom highlights
    for metric_col in ["dalys_asr", "deaths_asr", "ylds_rate"]:
        tb = identify_top_bottom(summary, metric_col)
        if tb:
            log.info(f"\nTop 5 states by {metric_col}: "
                     f"{[r['state_name_harmonized'] for r in tb.get('top', [])]}")

    log.info("=== State Burden Analysis: Complete ===")
    return summary


if __name__ == "__main__":
    run()
