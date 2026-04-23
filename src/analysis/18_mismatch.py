"""
Surveillance–Burden Mismatch Analysis (Step 4J)
Compares state rankings by administrative surveillance (MoRTH 2023 road deaths)
vs. GBD 2021 road injury DALYs.

NOTE: Year mismatch (2023 vs 2021) means only rank-based qualitative comparisons
are valid. No direct numerical comparisons are made.
"""

import pathlib
import pandas as pd
import numpy as np
import logging
from scipy import stats

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_PROCESSED = PROJECT_ROOT / "data_processed"
OUTPUTS = PROJECT_ROOT / "outputs"
TABLES = PROJECT_ROOT / "tables"
LOGS = PROJECT_ROOT / "logs"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOGS / "18_mismatch.log"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)

MISMATCH_THRESHOLD = 5  # rank positions considered notable mismatch


def run():
    log.info("=== Mismatch Analysis: Start ===")

    fpath = DATA_PROCESSED / "master_dataset.csv"
    if not fpath.exists():
        log.error("Master dataset not found.")
        return

    df = pd.read_csv(fpath, low_memory=False)

    # --- GBD road injury DALYs (2021, all ages, both sexes, Number) ---
    gbd_road = df[
        (df["source"] == "gbd2021") &
        (df["year"] == 2021) &
        (df["cause_group"] == "road") &
        (df["measure"] == "DALYs") &
        (df["metric_type"] == "Number") &
        (df["sex"] == "Both") &
        (df["age_group"] == "All ages") &
        (df["state_name_harmonized"] != "India")
    ][["state_name_harmonized", "value"]].rename(columns={"value": "gbd_road_dalys_n"})

    # Also get GBD road deaths for comparison
    gbd_road_deaths = df[
        (df["source"] == "gbd2021") &
        (df["year"] == 2021) &
        (df["cause_group"] == "road") &
        (df["measure"] == "Deaths") &
        (df["metric_type"] == "Number") &
        (df["sex"] == "Both") &
        (df["age_group"] == "All ages") &
        (df["state_name_harmonized"] != "India")
    ][["state_name_harmonized", "value"]].rename(columns={"value": "gbd_road_deaths_n"})

    # --- MoRTH road deaths (2023) ---
    morth_road = df[
        (df["source"] == "morth2023") &
        (df["cause_group"] == "road") &
        (df["measure"] == "Deaths") &
        (df["metric_type"] == "Number")
    ][["state_name_harmonized", "value"]].rename(columns={"value": "morth_road_deaths_n"})

    # --- Merge ---
    merged = gbd_road.merge(gbd_road_deaths, on="state_name_harmonized", how="outer")
    merged = merged.merge(morth_road, on="state_name_harmonized", how="outer")

    if merged.empty or len(merged) < 3:
        log.warning("Insufficient data for mismatch analysis. Need both GBD and MoRTH data.")
        log.warning("Generating placeholder mismatch output.")
        pd.DataFrame(columns=[
            "state_name_harmonized", "rank_gbd_road_dalys", "rank_gbd_road_deaths",
            "rank_morth_road_deaths", "rank_mismatch_daly_vs_morth",
            "rank_mismatch_gbd_death_vs_morth", "notable_mismatch"
        ]).to_csv(OUTPUTS / "mismatch.csv", index=False)
        return

    # Compute ranks (rank 1 = highest burden)
    if "gbd_road_dalys_n" in merged.columns:
        merged["rank_gbd_road_dalys"] = merged["gbd_road_dalys_n"].rank(ascending=False, na_option="bottom")
    if "gbd_road_deaths_n" in merged.columns:
        merged["rank_gbd_road_deaths"] = merged["gbd_road_deaths_n"].rank(ascending=False, na_option="bottom")
    if "morth_road_deaths_n" in merged.columns:
        merged["rank_morth_road_deaths"] = merged["morth_road_deaths_n"].rank(ascending=False, na_option="bottom")

    # Rank mismatch: DALY rank vs MoRTH death rank
    if all(c in merged.columns for c in ["rank_gbd_road_dalys", "rank_morth_road_deaths"]):
        merged["rank_mismatch_daly_vs_morth"] = (
            merged["rank_gbd_road_dalys"] - merged["rank_morth_road_deaths"]
        )
        merged["notable_mismatch"] = abs(merged["rank_mismatch_daly_vs_morth"]) >= MISMATCH_THRESHOLD

        # Spearman correlation
        valid = merged.dropna(subset=["rank_gbd_road_dalys", "rank_morth_road_deaths"])
        if len(valid) >= 5:
            rho, pval = stats.spearmanr(valid["rank_gbd_road_dalys"], valid["rank_morth_road_deaths"])
            log.info(f"Spearman correlation (GBD DALY rank vs MoRTH death rank): ρ={rho:.3f}, p={pval:.4f}")
            log.info("NOTE: Year mismatch (GBD 2021 vs MoRTH 2023) — interpret qualitatively only")

        notable = merged[merged["notable_mismatch"] == True].sort_values("rank_mismatch_daly_vs_morth")
        if len(notable) > 0:
            log.info(f"States with notable rank mismatch (≥{MISMATCH_THRESHOLD} positions):")
            log.info(notable[["state_name_harmonized", "rank_gbd_road_dalys",
                              "rank_morth_road_deaths", "rank_mismatch_daly_vs_morth"]].to_string())

    # GBD deaths vs MoRTH comparison
    if all(c in merged.columns for c in ["rank_gbd_road_deaths", "rank_morth_road_deaths"]):
        merged["rank_mismatch_gbd_death_vs_morth"] = (
            merged["rank_gbd_road_deaths"] - merged["rank_morth_road_deaths"]
        )

    merged.to_csv(OUTPUTS / "mismatch.csv", index=False)
    log.info(f"Mismatch output: {OUTPUTS / 'mismatch.csv'}")

    try:
        with pd.ExcelWriter(str(TABLES / "Table5_mismatch.xlsx"), engine="openpyxl") as w:
            merged.to_excel(w, sheet_name="Mismatch_Road", index=False)
    except Exception as e:
        log.warning(f"Excel write failed: {e}")

    log.info("=== Mismatch Analysis: Complete ===")
    log.info("IMPORTANT: MoRTH 2023 vs GBD 2021 — all comparisons are qualitative (rank-based) only.")
    return merged


if __name__ == "__main__":
    run()
