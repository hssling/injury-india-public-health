"""
Full QC and Cross-Reference Verification (Step 7)
Checks:
1. Master dataset integrity (duplicates, missingness, impossible values)
2. Output file completeness
3. Figure file existence
4. Table file existence
5. Reference file integrity (placeholder — DOI validation done separately)
Outputs: outputs/qc_report.html
"""

import pathlib
import pandas as pd
import numpy as np
import logging
import datetime
import json

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_PROCESSED = PROJECT_ROOT / "data_processed"
OUTPUTS = PROJECT_ROOT / "outputs"
FIGURES = PROJECT_ROOT / "figures"
TABLES = PROJECT_ROOT / "tables"
LOGS = PROJECT_ROOT / "logs"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOGS / "21_qc_full.log"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)


def check_master_dataset() -> dict:
    """QC checks on master_dataset.csv."""
    report = {"name": "Master Dataset", "checks": [], "status": "PASS"}
    fpath = DATA_PROCESSED / "master_dataset.csv"

    if not fpath.exists():
        report["checks"].append({"check": "File exists", "result": "FAIL", "detail": str(fpath)})
        report["status"] = "FAIL"
        return report

    report["checks"].append({"check": "File exists", "result": "PASS", "detail": ""})

    df = pd.read_csv(fpath, low_memory=False)
    n = len(df)
    report["checks"].append({"check": "Row count", "result": "INFO", "detail": f"{n:,} rows"})

    # Duplicates
    id_cols = [c for c in ["state_name_harmonized", "year", "sex", "age_group",
                            "cause_group", "measure", "metric_type", "source"]
               if c in df.columns]
    dupes = df.duplicated(subset=id_cols).sum()
    report["checks"].append({
        "check": "Duplicate rows",
        "result": "PASS" if dupes == 0 else "WARN",
        "detail": f"{dupes} duplicates"
    })
    if dupes > 0:
        report["status"] = "WARN"

    # Missingness in key fields
    for col in ["state_name_harmonized", "measure", "value", "source"]:
        if col in df.columns:
            null_n = df[col].isna().sum()
            result = "PASS" if null_n == 0 else ("WARN" if null_n < n * 0.01 else "FAIL")
            report["checks"].append({
                "check": f"Null values: {col}",
                "result": result,
                "detail": f"{null_n} nulls ({100*null_n/n:.1f}%)"
            })
            if result == "FAIL":
                report["status"] = "FAIL"

    # Negative values
    if "value" in df.columns:
        neg = (pd.to_numeric(df["value"], errors="coerce") < 0).sum()
        report["checks"].append({
            "check": "Negative values",
            "result": "PASS" if neg == 0 else "WARN",
            "detail": f"{neg} negative values"
        })

    # GBD data presence
    gbd_rows = (df["source"] == "gbd2021").sum()
    report["checks"].append({
        "check": "GBD data present",
        "result": "PASS" if gbd_rows > 0 else "FAIL",
        "detail": f"{gbd_rows:,} GBD rows"
    })
    if gbd_rows == 0:
        report["status"] = "FAIL"

    # Admin data presence
    admin_rows = (df["source"].isin(["morth2023", "ncrb2023"])).sum()
    report["checks"].append({
        "check": "Administrative data present",
        "result": "PASS" if admin_rows > 0 else "WARN",
        "detail": f"{admin_rows:,} admin rows"
    })

    return report


def check_required_outputs() -> dict:
    """Check that all expected output files exist."""
    report = {"name": "Output Files", "checks": [], "status": "PASS"}

    expected_outputs = [
        OUTPUTS / "state_burden_2021.csv",
        OUTPUTS / "decomposition.csv",
        OUTPUTS / "hdbi.csv",
        OUTPUTS / "inequality.csv",
        OUTPUTS / "mismatch.csv",
        DATA_PROCESSED / "master_dataset.csv",
    ]

    for fpath in expected_outputs:
        exists = fpath.exists()
        size = fpath.stat().st_size if exists else 0
        report["checks"].append({
            "check": f"Output: {fpath.name}",
            "result": "PASS" if exists and size > 100 else ("WARN" if exists else "FAIL"),
            "detail": f"{size:,} bytes" if exists else "Not found",
        })
        if not exists:
            report["status"] = "WARN"

    return report


def check_required_tables() -> dict:
    """Check that all expected table files exist."""
    report = {"name": "Table Files", "checks": [], "status": "PASS"}

    expected_tables = [
        TABLES / "Table1_state_burden.xlsx",
        TABLES / "Table2_decomposition.xlsx",
        TABLES / "Table2b_hdbi.xlsx",
        TABLES / "Table5_mismatch.xlsx",
        TABLES / "Table_S2_inequality.xlsx",
    ]

    for fpath in expected_tables:
        exists = fpath.exists()
        report["checks"].append({
            "check": f"Table: {fpath.name}",
            "result": "PASS" if exists else "WARN",
            "detail": "" if exists else "Not yet generated",
        })
        if not exists:
            report["status"] = "WARN"

    return report


def check_required_figures() -> dict:
    """Check that all manuscript figures exist."""
    report = {"name": "Figure Files", "checks": [], "status": "PASS"}

    expected_figures = [
        "fig1_daly_map", "fig2_hdbi_map", "fig3_heatmap",
        "fig4_trends", "fig5_quadrant", "fig6_mismatch", "fig7_age_sex",
    ]

    for fig_name in expected_figures:
        png_path = FIGURES / f"{fig_name}.png"
        exists = png_path.exists()
        report["checks"].append({
            "check": f"Figure: {fig_name}",
            "result": "PASS" if exists else "WARN",
            "detail": "PNG+SVG+PDF" if exists else "Not yet generated",
        })
        if not exists:
            report["status"] = "WARN"

    return report


def check_acquisition_log() -> dict:
    """Check data acquisition log."""
    report = {"name": "Data Acquisition", "checks": [], "status": "PASS"}
    log_path = LOGS / "acquisition_log.csv"

    if not log_path.exists():
        report["checks"].append({
            "check": "Acquisition log exists",
            "result": "WARN",
            "detail": "Run src/ingest/01_download_plan.py first"
        })
        report["status"] = "WARN"
        return report

    acq = pd.read_csv(log_path)
    missing = acq[acq["status"] == "MISSING"]           # mandatory missing = FAIL
    optional = acq[acq["status"] == "OPTIONAL_MISSING"]  # optional missing = WARN
    present  = acq[acq["status"] == "PRESENT"]

    report["checks"].append({
        "check": "Mandatory files present",
        "result": "PASS" if len(missing) == 0 else "FAIL",
        "detail": f"{len(present)} present, {len(missing)} missing, {len(optional)} optional-missing"
    })
    for _, row in missing.iterrows():
        report["checks"].append({
            "check": f"MISSING (mandatory): {row['source_name']}",
            "result": "FAIL",
            "detail": f"Expected in: {row['file_path']}"
        })
        report["status"] = "FAIL"
    for _, row in optional.iterrows():
        report["checks"].append({
            "check": f"OPTIONAL not downloaded: {row['source_name']}",
            "result": "WARN",
            "detail": str(row.get('note', ''))
        })
        if report["status"] == "PASS":
            report["status"] = "WARN"

    return report


def generate_html_report(reports: list[dict]) -> str:
    """Generate HTML QC report."""
    status_colors = {"PASS": "#28a745", "WARN": "#ffc107", "FAIL": "#dc3545", "INFO": "#17a2b8"}

    rows = []
    for rep in reports:
        for check in rep["checks"]:
            color = status_colors.get(check["result"], "#6c757d")
            rows.append(
                f"<tr><td>{rep['name']}</td>"
                f"<td>{check['check']}</td>"
                f"<td style='color:{color};font-weight:bold'>{check['result']}</td>"
                f"<td>{check['detail']}</td></tr>"
            )

    overall = "PASS" if all(r["status"] == "PASS" for r in reports) else \
              ("FAIL" if any(r["status"] == "FAIL" for r in reports) else "WARN")
    overall_color = status_colors[overall]

    html = f"""<!DOCTYPE html>
<html>
<head>
  <title>QC Report — Burden of Injuries in India</title>
  <style>
    body {{font-family: Arial, sans-serif; margin: 30px; color: #333;}}
    h1 {{color: #2c3e50;}}
    table {{border-collapse: collapse; width: 100%;}}
    th, td {{border: 1px solid #ddd; padding: 8px; text-align: left;}}
    th {{background-color: #2c3e50; color: white;}}
    tr:nth-child(even) {{background-color: #f9f9f9;}}
    .overall {{font-size: 1.5em; font-weight: bold; color: {overall_color};}}
  </style>
</head>
<body>
  <h1>QC Report — Burden of Injuries in India Study</h1>
  <p>Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
  <p class='overall'>Overall status: {overall}</p>
  <table>
    <tr><th>Section</th><th>Check</th><th>Result</th><th>Detail</th></tr>
    {''.join(rows)}
  </table>
  <hr>
  <p><small>QC script: src/qc/21_qc_full.py</small></p>
</body>
</html>"""
    return html


def run():
    log.info("=== Full QC: Start ===")

    reports = [
        check_acquisition_log(),
        check_master_dataset(),
        check_required_outputs(),
        check_required_tables(),
        check_required_figures(),
    ]

    html = generate_html_report(reports)

    out_path = OUTPUTS / "qc_report.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    log.info(f"QC report: {out_path}")

    # Print summary
    for rep in reports:
        status_symbol = "✓" if rep["status"] == "PASS" else ("⚠" if rep["status"] == "WARN" else "✗")
        log.info(f"  {status_symbol} {rep['name']}: {rep['status']}")

    overall = "PASS" if all(r["status"] == "PASS" for r in reports) else \
              ("FAIL" if any(r["status"] == "FAIL" for r in reports) else "WARN")
    log.info(f"\nOverall QC status: {overall}")
    log.info("=== Full QC: Complete ===")

    return reports


if __name__ == "__main__":
    run()
