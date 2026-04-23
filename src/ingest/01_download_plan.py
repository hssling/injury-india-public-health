"""
Download plan and acquisition logger for the Burden of Injuries in India study.

This script:
1. Documents exact download parameters for each data source.
2. Validates presence of required files after manual download.
3. Computes SHA256 checksums for downloaded files.
4. Writes a provenance log.

NOTE: GBD 2021, MoRTH, and NCRB data require manual browser-based downloads
(free registration or government portal). This script provides exact instructions
and validates after download.
"""

import hashlib
import os
import datetime
import csv
import pathlib

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_RAW = PROJECT_ROOT / "data_raw"
LOGS = PROJECT_ROOT / "logs"
LOGS.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Data source definitions
# ---------------------------------------------------------------------------

SOURCES = [
    {
        "source_id": "GBD2021_deaths_dalys",
        "source_name": "GBD 2021 — Deaths & DALYs, India subnational",
        "url": "https://ghdx.healthdata.org/gbd-results",
        "access_method": "Manual browser download after free registration",
        "format": "CSV",
        "target_dir": DATA_RAW / "gbd",
        "expected_filename_pattern": "*.csv",
        "download_instructions": """
GBD 2021 Deaths and DALYs Download Instructions:
-------------------------------------------------
1. Navigate to: https://ghdx.healthdata.org/gbd-results
2. Create a free IHME account if not already registered.
3. Set the following parameters:

   BASE:
   - GBD Cycle: GBD 2021
   - Location: India [AND] All subnational (select India then expand to all states/UTs)
     TIP: Search for 'India' then check the box for subnational locations.
   - Year: Select ALL years 2000–2021 (or download by decade if size limit applies)
   - Age: All Ages + Age-standardized + individual groups (0-4, 5-14, 15-29, 30-49, 50-69, 70+)
   - Sex: Both + Male + Female
   - Cause: Injuries (search 'injuries' — select Level 1 ALL INJURIES, then expand L2/L3)
     Required causes:
       * All causes > Injuries (L1)
       * Transport injuries (L2)
         - Road injuries (L3)
         - Other transport injuries (L3)
       * Unintentional injuries (L2)
         - Falls (L3)
         - Drowning (L3)
         - Burns and heat (L3)
         - Poisonings (L3)
         - Other unintentional injuries (L3)
       * Self-harm and interpersonal violence (L2)
         - Self-harm (L3)
         - Interpersonal violence (L3)
   - Measure: Deaths, DALYs, YLLs, YLDs
   - Metric: Number, Rate

   INCIDENCE (separate download if needed):
   - Same parameters but Measure: Incidence
   - Metric: Number, Rate

4. Click 'Download'. If file is too large, split by:
   - Download deaths+YLLs first, then YLDs+DALYs
   - Or download by cause group (transport, unintentional, intentional)

5. Save downloaded CSV file(s) to:
   {target_dir}/

6. Name the file descriptively, e.g.:
   gbd2021_india_injuries_deaths_dalys_all.csv
   gbd2021_india_injuries_ylls_ylds_all.csv

7. Run this script to validate: python src/ingest/01_download_plan.py
""".format(target_dir=DATA_RAW / "gbd"),
    },
    {
        "source_id": "MoRTH2023",
        "source_name": "Road Accidents in India 2023 (MoRTH)",
        "url": "https://road.transport.gov.in/publications/road-accidents-in-india",
        "access_method": "Direct PDF download",
        "format": "PDF",
        "target_dir": DATA_RAW / "morth",
        "expected_filename_pattern": "*.pdf",
        "download_instructions": """
MoRTH Road Accidents in India 2023 Download Instructions:
----------------------------------------------------------
1. Navigate to: https://road.transport.gov.in/publications/road-accidents-in-india
   Alternative: https://morth.nic.in (search 'road accidents 2023')
2. Find 'Road Accidents in India — 2023' (most recent annual report).
3. Click to download the full PDF report.
4. Save to: {target_dir}/road_accidents_india_2023.pdf
5. Run this script to validate.

Key tables required from the PDF:
- Table 1.X: State-wise Road Accidents (total)
- Table 1.X: State-wise Deaths (road injuries)
- Table 1.X: State-wise Injured Persons
- Tables on road type, vehicle type, road user if available
""".format(target_dir=DATA_RAW / "morth"),
    },
    {
        "source_id": "NCRB_ADSI_2023",
        "source_name": "Accidental Deaths & Suicides in India 2023 (NCRB)",
        "url": "https://ncrb.gov.in/adsi.html",
        "access_method": "Direct PDF download",
        "format": "PDF",
        "target_dir": DATA_RAW / "ncrb",
        "expected_filename_pattern": "*.pdf",
        "download_instructions": """
NCRB ADSI 2023 Download Instructions:
--------------------------------------
1. Navigate to: https://ncrb.gov.in/adsi.html
   Alternative: https://ncrb.gov.in → Publications → Accidental Deaths & Suicides
2. Find 'Accidental Deaths & Suicides in India 2023'.
3. Download the full report PDF (or chapter-wise PDFs if available).
4. Save to: {target_dir}/adsi_2023.pdf
5. Run this script to validate.

Key tables required from the PDF:
- Table AD-X: State-wise accidental deaths by cause (drowning, falls, poisoning, fire, electrocution, road)
- Table SU-X: State-wise suicides by method
- Table SU-X: State-wise suicides by age and sex
""".format(target_dir=DATA_RAW / "ncrb"),
    },
    {
        "source_id": "India_shapefile",
        "source_name": "India State Boundaries — GADM Level 1",
        "url": "https://gadm.org/download_country.html",
        "access_method": "Direct download",
        "format": "Shapefile / GeoJSON",
        "target_dir": DATA_RAW / "shapefiles",
        "expected_filename_pattern": "*.shp",
        "download_instructions": """
India State Shapefile Download Instructions:
--------------------------------------------
1. Navigate to: https://gadm.org/download_country.html
2. Select country: India
3. Click 'Level 1' (states) — download as Shapefile.
   Alternative GeoJSON also acceptable.
4. Save to: {target_dir}/
   Expected files: gadm41_IND_1.shp (+ .dbf, .prj, .shx)
5. Run this script to validate.

Note: Verify that Jammu & Kashmir and Ladakh are correctly represented per 2019 bifurcation.
If not, note the discrepancy in logs.
""".format(target_dir=DATA_RAW / "shapefiles"),
    },
]


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def sha256_file(filepath: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def get_file_size(filepath: pathlib.Path) -> int:
    return filepath.stat().st_size


def print_download_instructions():
    print("\n" + "="*80)
    print("DATA ACQUISITION INSTRUCTIONS")
    print("Burden of Injuries in India Study")
    print("="*80)
    for source in SOURCES:
        print(f"\n{'─'*60}")
        print(f"SOURCE: {source['source_name']}")
        print(f"URL: {source['url']}")
        print(source["download_instructions"])
    print("="*80)
    print("\nAfter downloading all files, run this script again to validate.")
    print("="*80 + "\n")


def validate_downloads() -> list[dict]:
    """Check which required files are present and compute checksums."""
    import glob
    log_rows = []
    all_ok = True

    for source in SOURCES:
        target_dir = source["target_dir"]
        target_dir.mkdir(parents=True, exist_ok=True)
        pattern = str(target_dir / source["expected_filename_pattern"])
        found_files = glob.glob(pattern)

        if not found_files:
            print(f"[MISSING] {source['source_name']}: No files found in {target_dir}")
            all_ok = False
            log_rows.append({
                "source_id": source["source_id"],
                "source_name": source["source_name"],
                "url": source["url"],
                "file_path": str(target_dir),
                "filename": "NOT FOUND",
                "sha256": "",
                "size_bytes": 0,
                "access_date": datetime.date.today().isoformat(),
                "status": "MISSING",
                "note": "File not downloaded yet",
            })
        else:
            for fp in found_files:
                fp_path = pathlib.Path(fp)
                checksum = sha256_file(fp_path)
                size = get_file_size(fp_path)
                print(f"[OK] {source['source_name']}: {fp_path.name} ({size:,} bytes, SHA256: {checksum[:16]}...)")
                log_rows.append({
                    "source_id": source["source_id"],
                    "source_name": source["source_name"],
                    "url": source["url"],
                    "file_path": str(fp_path),
                    "filename": fp_path.name,
                    "sha256": checksum,
                    "size_bytes": size,
                    "access_date": datetime.date.today().isoformat(),
                    "status": "PRESENT",
                    "note": "",
                })

    return log_rows, all_ok


def write_acquisition_log(log_rows: list[dict]):
    log_file = LOGS / "acquisition_log.csv"
    fieldnames = ["source_id", "source_name", "url", "file_path", "filename",
                  "sha256", "size_bytes", "access_date", "status", "note"]
    with open(log_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(log_rows)
    print(f"\nAcquisition log written to: {log_file}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    if "--instructions" in sys.argv or len(sys.argv) == 1:
        print_download_instructions()

    print("\nValidating downloaded files...\n")
    log_rows, all_ok = validate_downloads()
    write_acquisition_log(log_rows)

    if all_ok:
        print("\n[SUCCESS] All required data files are present.")
        print("Next step: Run src/ingest/02_parse_gbd.py")
    else:
        print("\n[ACTION REQUIRED] Some files are missing.")
        print("Please download the missing files following the instructions above,")
        print("then re-run this script to validate.")
