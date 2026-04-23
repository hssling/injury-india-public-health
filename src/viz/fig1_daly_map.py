"""
Figure 1 – India Choropleth Map of Injury DALY Rate (per 100,000)
Uses GIS data from india_states.geojson (GBD 2023 subnational, all injuries).
"""

import pathlib
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import numpy as np
import logging

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_RAW   = PROJECT_ROOT / "data_raw"
OUTPUTS    = PROJECT_ROOT / "outputs"
FIGURES    = PROJECT_ROOT / "figures"
FIGURES.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── State name bridge: GeoJSON NAME_1 → harmonized name in burden table ────
GEO_TO_HARM = {
    "Andaman and Nicobar":      "Other Union Territories",   # aggregated
    "Andhra Pradesh":           "Andhra Pradesh",            # pre-2014 includes Telangana
    "Arunachal Pradesh":        "Arunachal Pradesh",
    "Assam":                    "Assam",
    "Bihar":                    "Bihar",
    "Chandigarh":               "Other Union Territories",
    "Chhattisgarh":             "Chhattisgarh",
    "Dadra and Nagar Haveli":   "Other Union Territories",
    "Daman and Diu":            "Other Union Territories",
    "Delhi":                    "Delhi",
    "Goa":                      "Goa",
    "Gujarat":                  "Gujarat",
    "Haryana":                  "Haryana",
    "Himachal Pradesh":         "Himachal Pradesh",
    "Jammu and Kashmir":        "Jammu & Kashmir and Ladakh",
    "Jharkhand":                "Jharkhand",
    "Karnataka":                "Karnataka",
    "Kerala":                   "Kerala",
    "Lakshadweep":              "Other Union Territories",
    "Madhya Pradesh":           "Madhya Pradesh",
    "Maharashtra":              "Maharashtra",
    "Manipur":                  "Manipur",
    "Meghalaya":                "Meghalaya",
    "Mizoram":                  "Mizoram",
    "Nagaland":                 "Nagaland",
    "Orissa":                   "Odisha",
    "Puducherry":               "Other Union Territories",
    "Punjab":                   "Punjab",
    "Rajasthan":                "Rajasthan",
    "Sikkim":                   "Sikkim",
    "Tamil Nadu":               "Tamil Nadu",
    "Tripura":                  "Tripura",
    "Uttar Pradesh":            "Uttar Pradesh",
    "Uttaranchal":              "Uttarakhand",
    "West Bengal":              "West Bengal",
}

# Telangana uses Andhra Pradesh GBD row weighted by population (~41% of combined AP+TS)
# GBD 2023 subnational treats combined AP row as historical AP+TS; we display as-is.

def run():
    log.info("=== Fig 1 DALY Map: Start ===")

    # Load burden data
    sb = pd.read_csv(OUTPUTS / "state_burden_2021.csv")
    burden = sb[["state_name_harmonized", "dalys_rate", "deaths_rate", "ylds_rate"]].copy()

    # Load shapefile
    gdf = gpd.read_file(DATA_RAW / "india_states.geojson")
    gdf = gdf.to_crs("EPSG:4326")

    # Map to harmonized names
    gdf["harm_name"] = gdf["NAME_1"].map(GEO_TO_HARM)
    unmapped = gdf[gdf["harm_name"].isna()]["NAME_1"].tolist()
    if unmapped:
        log.warning(f"Unmapped geo states: {unmapped}")

    # For states mapped to aggregates (multiple geo polygons → one burden value),
    # merge burden by harm_name first, then left-join
    gdf = gdf.merge(burden, left_on="harm_name", right_on="state_name_harmonized", how="left")
    log.info(f"States with DALY data: {gdf['dalys_rate'].notna().sum()} / {len(gdf)}")

    # ── Plot ──────────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(1, 1, figsize=(10, 12))

    cmap = cm.YlOrRd
    vmin, vmax = 2200, 6100
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

    gdf.plot(
        column="dalys_rate",
        ax=ax,
        cmap=cmap,
        norm=norm,
        missing_kwds={"color": "#d3d3d3", "label": "No data"},
        edgecolor="white",
        linewidth=0.4,
    )

    # Colorbar
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm._A = []
    cbar = fig.colorbar(sm, ax=ax, orientation="vertical", fraction=0.03, pad=0.02)
    cbar.set_label("Injury DALY rate (per 100,000 population)", fontsize=11)

    # Annotate top/bottom 5 states
    HIGH = ["Telangana", "Chhattisgarh", "Uttarakhand"]
    LOW  = ["Mizoram", "Delhi", "Sikkim"]

    # State labels for key states only
    LABEL_STATES = {
        "Tamil Nadu":   (80.2, 10.9),
        "Telangana":    (79.0, 17.4),  # shown on AP polygon
        "Chhattisgarh": (82.0, 21.3),
        "Uttarakhand":  (79.5, 30.3),
        "Kerala":       (76.5, 10.5),
        "West Bengal":  (88.3, 23.0),
    }
    for name, (lon, lat) in LABEL_STATES.items():
        ax.annotate(name, xy=(lon, lat), fontsize=6.5, ha="center",
                    color="#333333", fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", alpha=0.6, ec="none"))

    ax.set_axis_off()
    ax.set_title(
        "State-level injury burden in India\n"
        "Disability-Adjusted Life Years (DALYs) per 100,000 population — GBD 2023",
        fontsize=13, fontweight="bold", pad=14
    )

    # Note about boundary limitations
    note = ("Note: Boundary data pre-dates Telangana (2014) and Ladakh (2019) bifurcations.\n"
            "Telangana burden displayed under combined Andhra Pradesh polygon.\n"
            "Jammu & Kashmir and Ladakh shown as unified GBD unit.")
    fig.text(0.12, 0.04, note, fontsize=7.5, color="#555555", style="italic",
             wrap=True, ha="left")

    plt.tight_layout(rect=[0, 0.06, 1, 1])

    for ext in ["png", "svg", "pdf"]:
        out = FIGURES / f"fig1_daly_map.{ext}"
        fig.savefig(out, dpi=300 if ext == "png" else None, bbox_inches="tight")
        log.info(f"Saved: {out}")

    plt.close(fig)
    log.info("=== Fig 1 DALY Map: Complete ===")


if __name__ == "__main__":
    run()
