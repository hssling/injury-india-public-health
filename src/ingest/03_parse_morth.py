"""
MoRTH Road Accidents in India 2023 — PDF Table Extractor

Attempts automated table extraction using tabula-py (Java-based) or camelot-py.
If extraction fails or produces unreliable output, generates a manual extraction
template (Excel) with expected column structure and state list.

All parsing failures are logged transparently; no data is imputed.
"""

import pathlib
import pandas as pd
import logging
import json

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_RAW_MORTH = PROJECT_ROOT / "data_raw" / "morth"
DATA_INTERIM = PROJECT_ROOT / "data_interim"
LOGS = PROJECT_ROOT / "logs"
DATA_INTERIM.mkdir(exist_ok=True)
LOGS.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOGS / "03_parse_morth.log"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)

# Expected states (for QA validation)
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

# Expected MoRTH table schema
MORTH_COLUMNS = [
    "state_name_raw",       # State/UT name as in MoRTH
    "accidents_total",      # Total road accidents
    "accidents_fatal",      # Fatal accidents
    "accidents_nonfatal",   # Non-fatal accidents
    "deaths_total",         # Persons killed
    "injured_total",        # Persons injured
    "accidents_nh",         # Accidents on National Highways (if available)
    "deaths_nh",            # Deaths on National Highways (if available)
    "accidents_sh",         # State Highways (if available)
    "deaths_sh",            # State Highways deaths (if available)
    "year",                 # Always 2023
    "source",               # Always "morth2023"
    "note",                 # Extraction notes
]


def try_tabula_extraction(pdf_path: pathlib.Path) -> list[pd.DataFrame] | None:
    try:
        import tabula
        log.info("Attempting tabula-py extraction...")
        tables = tabula.read_pdf(
            str(pdf_path),
            pages="all",
            multiple_tables=True,
            lattice=True,
            pandas_options={"header": None},
        )
        log.info(f"tabula-py extracted {len(tables)} table(s)")
        return tables
    except ImportError:
        log.warning("tabula-py not installed. Try: pip install tabula-py")
        return None
    except Exception as e:
        log.warning(f"tabula-py extraction failed: {e}")
        return None


def try_camelot_extraction(pdf_path: pathlib.Path) -> list | None:
    try:
        import camelot
        log.info("Attempting camelot-py extraction...")
        tables = camelot.read_pdf(str(pdf_path), pages="all", flavor="lattice")
        log.info(f"camelot extracted {len(tables)} table(s)")
        return [t.df for t in tables]
    except ImportError:
        log.warning("camelot-py not installed. Try: pip install camelot-py[cv]")
        return None
    except Exception as e:
        log.warning(f"camelot-py extraction failed: {e}")
        return None


def identify_state_tables(tables: list[pd.DataFrame]) -> list[pd.DataFrame]:
    """Find tables that look like state-wise accident data."""
    candidate_tables = []
    for i, t in enumerate(tables):
        t_str = t.to_string().lower()
        # Tables with state names and numeric data
        has_states = any(s.lower() in t_str for s in ["maharashtra", "uttar pradesh", "tamil", "rajasthan"])
        has_numbers = t.apply(lambda col: col.str.replace(",", "").str.isnumeric().sum() > 5
                               if col.dtype == object else col.gt(0).sum() > 5).any()
        if has_states and has_numbers:
            log.info(f"Table {i}: looks like a state-wise table ({t.shape[0]} rows × {t.shape[1]} cols)")
            candidate_tables.append((i, t))
    return candidate_tables


def generate_manual_extraction_template(out_path: pathlib.Path):
    """
    Generate an Excel template for manual entry of MoRTH state-wise tables.
    Used when automated PDF extraction fails or is unreliable.
    """
    template_df = pd.DataFrame({
        "state_name_raw": INDIA_STATES_UTS + ["Total / All India"],
        "accidents_total": [""] * (len(INDIA_STATES_UTS) + 1),
        "accidents_fatal": [""] * (len(INDIA_STATES_UTS) + 1),
        "accidents_nonfatal": [""] * (len(INDIA_STATES_UTS) + 1),
        "deaths_total": [""] * (len(INDIA_STATES_UTS) + 1),
        "injured_total": [""] * (len(INDIA_STATES_UTS) + 1),
        "accidents_nh": [""] * (len(INDIA_STATES_UTS) + 1),
        "deaths_nh": [""] * (len(INDIA_STATES_UTS) + 1),
        "accidents_sh": [""] * (len(INDIA_STATES_UTS) + 1),
        "deaths_sh": [""] * (len(INDIA_STATES_UTS) + 1),
        "year": [2023] * (len(INDIA_STATES_UTS) + 1),
        "source": ["morth2023"] * (len(INDIA_STATES_UTS) + 1),
        "note": [""] * (len(INDIA_STATES_UTS) + 1),
    })

    instructions = pd.DataFrame({
        "INSTRUCTIONS": [
            "Fill in values from MoRTH 2023 Table: State-wise Accidents, Deaths, Injuries",
            "Source document: Road Accidents in India 2023 (MoRTH/GoI)",
            "Use values as printed; do NOT recalculate",
            "Leave blank if a value is not available for that state",
            "After filling, save and run: python src/ingest/03_parse_morth.py --from-template",
            "",
            "QA: Verify that sum of state values ≈ All India total",
            "QA: Note page numbers used in the 'note' column",
        ]
    })

    try:
        with pd.ExcelWriter(str(out_path), engine="openpyxl") as writer:
            instructions.to_excel(writer, sheet_name="Instructions", index=False)
            template_df.to_excel(writer, sheet_name="MoRTH_State_Data", index=False)
        log.info(f"Manual extraction template written to: {out_path}")
        print(f"\n[ACTION REQUIRED] Automated PDF extraction was not successful.")
        print(f"Please manually extract MoRTH state-wise tables into:")
        print(f"  {out_path}")
        print("Refer to the Instructions sheet inside the file.")
    except ImportError:
        log.warning("openpyxl not installed. Writing CSV template instead.")
        template_df.to_csv(out_path.with_suffix(".csv"), index=False)
        log.info(f"CSV template written to: {out_path.with_suffix('.csv')}")


def validate_morth(df: pd.DataFrame) -> bool:
    """Basic QA: check if All India row exists and state totals are plausible."""
    issues = []

    numeric_cols = ["accidents_total", "deaths_total", "injured_total"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")

    if "deaths_total" in df.columns:
        india_row = df[df["state_name_raw"].str.lower().str.contains("total|india|all", na=False)]
        if not india_row.empty:
            national_total = india_row["deaths_total"].values[0]
            state_sum = df[~df["state_name_raw"].str.lower().str.contains("total|india|all", na=False)]["deaths_total"].sum()
            if abs(national_total - state_sum) / max(national_total, 1) > 0.05:
                issues.append(f"State sum ({state_sum:,.0f}) differs from national total ({national_total:,.0f}) by >5%")

    if issues:
        for issue in issues:
            log.warning(f"[QA] {issue}")
        return False
    log.info("[QA] MoRTH data passed basic validation.")
    return True


def run(from_template: bool = False):
    log.info("=== MoRTH Parser: Start ===")

    # Find PDF
    pdf_files = list(DATA_RAW_MORTH.glob("*.pdf"))
    template_path = DATA_RAW_MORTH / "manual_extraction_morth.xlsx"

    if from_template or not pdf_files:
        if template_path.exists():
            log.info(f"Loading from manual template: {template_path}")
            try:
                df = pd.read_excel(template_path, sheet_name="MoRTH_State_Data")
                log.info(f"Loaded {len(df)} rows from template.")
                validate_morth(df)
                out_path = DATA_INTERIM / "morth_raw.csv"
                df.to_csv(out_path, index=False)
                log.info(f"Output: {out_path}")
            except Exception as e:
                log.error(f"Failed to load template: {e}")
            return
        else:
            log.warning("No MoRTH PDF and no manual template found.")
            generate_manual_extraction_template(template_path)
            return

    pdf_path = pdf_files[0]
    if len(pdf_files) > 1:
        log.warning(f"Multiple PDFs found; using: {pdf_path.name}")

    log.info(f"Processing: {pdf_path}")

    # Try automated extraction
    tables = try_tabula_extraction(pdf_path)
    if tables is None:
        tables = try_camelot_extraction(pdf_path)

    extraction_success = False
    if tables:
        candidates = identify_state_tables(tables)
        if candidates:
            # Save all candidate tables for manual review
            for idx, (table_num, t) in enumerate(candidates):
                raw_out = DATA_INTERIM / f"morth_candidate_table_{idx}.csv"
                t.to_csv(raw_out, index=False)
                log.info(f"Candidate table {idx} saved to: {raw_out}")
            log.warning("Automated extraction completed but requires manual review.")
            log.warning("Please inspect data_interim/morth_candidate_table_*.csv")
            log.warning("Then consolidate into: data_raw/morth/manual_extraction_morth.xlsx")
            extraction_success = True

    if not extraction_success:
        log.warning("Automated extraction did not produce usable state-wise tables.")
        generate_manual_extraction_template(template_path)

    log.info("=== MoRTH Parser: Complete ===")


if __name__ == "__main__":
    import sys
    from_template = "--from-template" in sys.argv
    run(from_template=from_template)
