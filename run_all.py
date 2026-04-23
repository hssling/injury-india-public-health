"""
Master Pipeline Orchestrator
Burden of Injuries in India Study

Run this script to execute the complete analysis pipeline.
Some steps require manual data downloads first — see instructions below.

Usage:
  python run_all.py              # Full pipeline
  python run_all.py --phase 1   # Only Phase 1 (instructions + scaffold)
  python run_all.py --phase 2   # Only Phase 2 (parsing + cleaning)
  python run_all.py --phase 3   # Only Phase 3 (analysis)
  python run_all.py --phase 4   # Only Phase 4 (figures + tables)
  python run_all.py --phase 5   # Only Phase 5 (QC)
  python run_all.py --check     # Check status without running analysis

MANUAL STEPS REQUIRED BEFORE PIPELINE CAN COMPLETE:
  1. Download GBD 2021 data from https://ghdx.healthdata.org/gbd-results
     Save CSV files to: data_raw/gbd/
  2. Download MoRTH 2023 PDF from https://road.transport.gov.in
     Save to: data_raw/morth/road_accidents_india_2023.pdf
  3. Download NCRB ADSI 2023 PDF from https://ncrb.gov.in
     Save to: data_raw/ncrb/adsi_2023.pdf
  4. Download India shapefile from https://gadm.org
     Save to: data_raw/shapefiles/

After PDF downloads, if automated extraction fails:
  - Fill data_raw/morth/manual_extraction_morth.xlsx
  - Fill data_raw/ncrb/manual_extraction_ncrb.xlsx
  Then re-run: python run_all.py --phase 2
"""

import sys
import pathlib
import subprocess
import logging
import datetime
import importlib

PROJECT_ROOT = pathlib.Path(__file__).parent
LOGS = PROJECT_ROOT / "logs"
LOGS.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOGS / f"run_all_{datetime.date.today().isoformat()}.log"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)


def run_script(script_path: pathlib.Path, label: str) -> bool:
    """Run a Python script and return True if successful."""
    log.info(f"\n{'='*60}")
    log.info(f"RUNNING: {label}")
    log.info(f"Script: {script_path}")
    log.info(f"{'='*60}")

    if not script_path.exists():
        log.error(f"Script not found: {script_path}")
        return False

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(PROJECT_ROOT),
            capture_output=False,
            timeout=600,
        )
        if result.returncode == 0:
            log.info(f"[OK] {label} completed successfully.")
            return True
        else:
            log.error(f"[FAIL] {label} exited with code {result.returncode}")
            return False
    except subprocess.TimeoutExpired:
        log.error(f"[TIMEOUT] {label} exceeded 10 minutes.")
        return False
    except Exception as e:
        log.error(f"[ERROR] {label}: {e}")
        return False


PIPELINE = {
    1: [
        (PROJECT_ROOT / "src/ingest/01_download_plan.py", "Phase 1A: Download instructions and file validation"),
    ],
    2: [
        (PROJECT_ROOT / "src/ingest/02_parse_gbd.py", "Phase 2A: Parse GBD CSV files"),
        (PROJECT_ROOT / "src/ingest/03_parse_morth.py", "Phase 2B: Parse MoRTH PDF"),
        (PROJECT_ROOT / "src/ingest/04_parse_ncrb.py", "Phase 2C: Parse NCRB PDF"),
        (PROJECT_ROOT / "src/clean/05_harmonize_states.py", "Phase 2D: Harmonize state names"),
        (PROJECT_ROOT / "src/clean/08_assemble_master.py", "Phase 2E: Assemble master dataset"),
    ],
    3: [
        (PROJECT_ROOT / "src/analysis/10_state_burden.py", "Phase 3A: State burden analysis"),
        (PROJECT_ROOT / "src/analysis/11_decomposition.py", "Phase 3B: Fatal/non-fatal decomposition"),
        (PROJECT_ROOT / "src/analysis/12_hdbi.py", "Phase 3C: Hidden disability burden index"),
        (PROJECT_ROOT / "src/analysis/17_inequality.py", "Phase 3D: Inequality metrics"),
        (PROJECT_ROOT / "src/analysis/18_mismatch.py", "Phase 3E: Surveillance-burden mismatch"),
    ],
    4: [
        (PROJECT_ROOT / "src/viz/20_figures.py", "Phase 4A: Generate all figures"),
    ],
    5: [
        (PROJECT_ROOT / "src/qc/21_qc_full.py", "Phase 5: Full QC report"),
    ],
}


def check_status():
    """Quick status check of required files."""
    checks = {
        "GBD CSV files": list((PROJECT_ROOT / "data_raw/gbd").glob("*.csv")),
        "MoRTH PDF": list((PROJECT_ROOT / "data_raw/morth").glob("*.pdf")),
        "NCRB PDF": list((PROJECT_ROOT / "data_raw/ncrb").glob("*.pdf")),
        "Shapefile": list((PROJECT_ROOT / "data_raw/shapefiles").glob("*.shp")),
        "Master dataset": [PROJECT_ROOT / "data_processed/master_dataset.csv"]
            if (PROJECT_ROOT / "data_processed/master_dataset.csv").exists() else [],
        "QC report": [PROJECT_ROOT / "outputs/qc_report.html"]
            if (PROJECT_ROOT / "outputs/qc_report.html").exists() else [],
    }

    log.info("\n=== PROJECT STATUS ===")
    all_ok = True
    for name, files in checks.items():
        if files and all(f.exists() if isinstance(f, pathlib.Path) else True for f in files):
            log.info(f"  [✓] {name}: {len(files)} file(s) found")
        else:
            log.info(f"  [✗] {name}: NOT FOUND")
            all_ok = False
    log.info("======================")
    return all_ok


def run_phase(phase: int) -> bool:
    steps = PIPELINE.get(phase, [])
    if not steps:
        log.error(f"Phase {phase} not found.")
        return False

    all_ok = True
    for script_path, label in steps:
        ok = run_script(script_path, label)
        if not ok:
            log.warning(f"Step failed: {label} — continuing to next step")
            all_ok = False

    return all_ok


def run_all() -> bool:
    log.info("=== FULL PIPELINE: START ===")
    log.info(f"Project root: {PROJECT_ROOT}")
    log.info(f"Timestamp: {datetime.datetime.now().isoformat()}")

    all_ok = True
    for phase in sorted(PIPELINE.keys()):
        ok = run_phase(phase)
        if not ok:
            all_ok = False
            log.warning(f"Phase {phase} completed with warnings/errors.")

    log.info(f"\n{'='*60}")
    log.info(f"PIPELINE {'COMPLETE' if all_ok else 'COMPLETED WITH ISSUES'}")
    log.info(f"Check logs in: {LOGS}")
    log.info(f"Check QC report: {PROJECT_ROOT / 'outputs/qc_report.html'}")
    log.info(f"{'='*60}")

    return all_ok


def main():
    args = sys.argv[1:]

    if "--check" in args:
        check_status()
        return

    if "--phase" in args:
        idx = args.index("--phase")
        if idx + 1 < len(args):
            try:
                phase = int(args[idx + 1])
                run_phase(phase)
                return
            except ValueError:
                log.error("--phase requires an integer argument (1-5)")
                sys.exit(1)

    # Default: full pipeline
    check_status()
    log.info("\nStarting full pipeline...\n")
    run_all()


if __name__ == "__main__":
    main()
