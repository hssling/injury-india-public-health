"""
NCRB Accidental Deaths and Suicides in India 2023 — PDF Table Extractor

Extracts:
1. Accidental deaths by cause (state-wise)
2. Suicides by method (state-wise)
3. Suicides by age and sex (state-wise)

Uses tabula-py or camelot-py; generates manual extraction template if automated
extraction fails.
"""

import pathlib
import pandas as pd
import logging

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_RAW_NCRB = PROJECT_ROOT / "data_raw" / "ncrb"
DATA_INTERIM = PROJECT_ROOT / "data_interim"
LOGS = PROJECT_ROOT / "logs"
DATA_INTERIM.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOGS / "04_parse_ncrb.log"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)

INDIA_STATES_UTS = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
    "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
    "West Bengal",
    "A & N Islands", "Chandigarh", "D & N Haveli", "Delhi",
    "Jammu & Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
]

ACCIDENTAL_DEATH_COLUMNS = [
    "state_name_raw",
    "acc_deaths_total",
    "acc_deaths_road",
    "acc_deaths_railway",
    "acc_deaths_falls",
    "acc_deaths_drowning",
    "acc_deaths_fire_burns",
    "acc_deaths_poisoning",
    "acc_deaths_electrocution",
    "acc_deaths_other",
    "year",
    "source",
    "note",
]

SUICIDE_COLUMNS = [
    "state_name_raw",
    "suicides_total",
    "suicides_hanging",
    "suicides_poisoning_agri",
    "suicides_poisoning_other",
    "suicides_drowning",
    "suicides_self_immolation",
    "suicides_firearms",
    "suicides_other",
    "year",
    "source",
    "note",
]


def try_tabula_extraction(pdf_path: pathlib.Path) -> list[pd.DataFrame] | None:
    try:
        import tabula
        tables = tabula.read_pdf(
            str(pdf_path), pages="all", multiple_tables=True,
            lattice=True, pandas_options={"header": None}
        )
        log.info(f"tabula: {len(tables)} table(s) extracted")
        return tables
    except ImportError:
        log.warning("tabula-py not installed: pip install tabula-py")
        return None
    except Exception as e:
        log.warning(f"tabula extraction failed: {e}")
        return None


def try_camelot_extraction(pdf_path: pathlib.Path) -> list[pd.DataFrame] | None:
    try:
        import camelot
        tables = camelot.read_pdf(str(pdf_path), pages="all", flavor="lattice")
        log.info(f"camelot: {len(tables)} table(s) extracted")
        return [t.df for t in tables]
    except ImportError:
        log.warning("camelot-py not installed: pip install camelot-py[cv]")
        return None
    except Exception as e:
        log.warning(f"camelot extraction failed: {e}")
        return None


def generate_manual_template():
    """Generate manual extraction templates for NCRB accidental deaths and suicides."""
    n = len(INDIA_STATES_UTS) + 1  # +1 for All India row

    # Template 1: Accidental deaths
    acc_template = pd.DataFrame({
        col: (INDIA_STATES_UTS + ["All India"]) if col == "state_name_raw"
             else ([2023] if col == "year" else (["ncrb2023"] if col == "source" else [""] * n))
        for col in ACCIDENTAL_DEATH_COLUMNS
    })

    # Template 2: Suicides
    sui_template = pd.DataFrame({
        col: (INDIA_STATES_UTS + ["All India"]) if col == "state_name_raw"
             else ([2023] if col == "year" else (["ncrb2023"] if col == "source" else [""] * n))
        for col in SUICIDE_COLUMNS
    })

    instructions = pd.DataFrame({
        "INSTRUCTIONS": [
            "Fill values from NCRB ADSI 2023 PDF",
            "Accidental Deaths sheet: use Table AD-XX (State-wise Accidental Deaths by Cause)",
            "Suicides sheet: use Table SU-XX (State-wise Suicides by Method)",
            "Leave blank if data not available for a state/cause",
            "Note the table number and page number in the 'note' column",
            "QA: verify sum of states ≈ All India row",
        ]
    })

    template_path = DATA_RAW_NCRB / "manual_extraction_ncrb.xlsx"
    try:
        with pd.ExcelWriter(str(template_path), engine="openpyxl") as writer:
            instructions.to_excel(writer, sheet_name="Instructions", index=False)
            acc_template.to_excel(writer, sheet_name="AccidentalDeaths", index=False)
            sui_template.to_excel(writer, sheet_name="Suicides", index=False)
        log.info(f"Manual extraction template: {template_path}")
        print(f"\n[ACTION REQUIRED] Please fill in NCRB data in: {template_path}")
        print("Then run: python src/ingest/04_parse_ncrb.py --from-template")
    except ImportError:
        acc_template.to_csv(DATA_RAW_NCRB / "manual_extraction_ncrb_accidental.csv", index=False)
        sui_template.to_csv(DATA_RAW_NCRB / "manual_extraction_ncrb_suicides.csv", index=False)
        log.info("CSV templates written (openpyxl not available)")


def validate_ncrb(df: pd.DataFrame, label: str) -> None:
    numeric_cols = [c for c in df.columns if c not in ("state_name_raw", "year", "source", "note")]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")

    total_col = f"{label}_total" if f"{label}_total" in df.columns else None
    if total_col:
        india_row = df[df["state_name_raw"].str.lower().str.contains("all india|total", na=False)]
        if not india_row.empty:
            national = india_row[total_col].values[0]
            state_sum = df[~df["state_name_raw"].str.lower().str.contains("all india|total", na=False)][total_col].sum()
            pct_diff = abs(national - state_sum) / max(national, 1) * 100
            if pct_diff > 5:
                log.warning(f"[QA {label}] Sum discrepancy: national={national:,.0f}, sum={state_sum:,.0f}, diff={pct_diff:.1f}%")
            else:
                log.info(f"[QA {label}] Totals consistent (diff={pct_diff:.1f}%)")


def run(from_template: bool = False):
    log.info("=== NCRB Parser: Start ===")

    DATA_RAW_NCRB.mkdir(parents=True, exist_ok=True)
    pdf_files = list(DATA_RAW_NCRB.glob("*.pdf"))
    template_path = DATA_RAW_NCRB / "manual_extraction_ncrb.xlsx"

    if from_template or not pdf_files:
        if template_path.exists():
            log.info(f"Loading from manual template: {template_path}")
            try:
                acc_df = pd.read_excel(template_path, sheet_name="AccidentalDeaths")
                sui_df = pd.read_excel(template_path, sheet_name="Suicides")
                validate_ncrb(acc_df, "acc_deaths")
                validate_ncrb(sui_df, "suicides")
                acc_df.to_csv(DATA_INTERIM / "ncrb_accidental_raw.csv", index=False)
                sui_df.to_csv(DATA_INTERIM / "ncrb_suicide_raw.csv", index=False)
                log.info("NCRB outputs written to data_interim/")
            except Exception as e:
                log.error(f"Template load failed: {e}")
        else:
            log.warning("No NCRB PDF and no manual template found.")
            generate_manual_template()
        return

    pdf_path = pdf_files[0]
    log.info(f"Processing: {pdf_path}")

    tables = try_tabula_extraction(pdf_path)
    if tables is None:
        tables = try_camelot_extraction(pdf_path)

    if tables:
        # Save all tables for inspection; require manual review to identify correct ones
        for i, t in enumerate(tables):
            raw_out = DATA_INTERIM / f"ncrb_candidate_table_{i}.csv"
            t.to_csv(raw_out, index=False)
        log.warning(f"Extracted {len(tables)} tables; saved to data_interim/ncrb_candidate_table_*.csv")
        log.warning("Manual review required to identify correct state-wise tables.")
        log.warning("Populate manual template and re-run with --from-template.")
        generate_manual_template()
    else:
        log.warning("Automated extraction failed. Generating manual template.")
        generate_manual_template()

    log.info("=== NCRB Parser: Complete ===")


if __name__ == "__main__":
    import sys
    from_template = "--from-template" in sys.argv
    run(from_template=from_template)
