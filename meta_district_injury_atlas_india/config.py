from pathlib import Path

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent                     # injury_india_public_health/
DATA_RAW = PARENT / "data_raw"
DATA_INTERIM = PARENT / "data_interim"
DATA_PROCESSED = PARENT / "data_processed"
DOCS = PARENT / "docs"
LOCAL = HERE / "data_local"              # newly acquired/extracted data
OUT = HERE / "outputs"
FIG = HERE / "figures"
TAB = HERE / "tables"

YEAR = 2023
CAUSES = ["all_injury", "road", "falls", "drowning", "burns", "suicide"]
# NCRB mega-city tables only tabulate these three at city level -> anchorable/validatable.
# falls/drowning/burns are covariate-projected only (see spec limitations).
ANCHOR_CAUSES = ["all_injury", "road", "suicide"]

NCRB_ADSI_2023_PDF = DATA_RAW / "ncrb" / "ADSI_2023.pdf"
