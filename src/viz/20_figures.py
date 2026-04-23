"""
Publication-grade figure generation for the NMJI submission package.

This version rebuilds only figures that can be supported from the available
GBD 2021 subnational extract and Indian administrative sources in the repo.
"""

from __future__ import annotations

import logging
import pathlib

import geopandas as gpd
import matplotlib
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

matplotlib.use("Agg")

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_PROCESSED = PROJECT_ROOT / "data_processed" / "master_dataset.csv"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
FIGURES_DIR = PROJECT_ROOT / "figures"
GEOJSON_PATH = PROJECT_ROOT / "data_raw" / "india_states.geojson"
LOG_PATH = PROJECT_ROOT / "logs" / "20_figures.log"

FIGURES_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()],
)
log = logging.getLogger(__name__)

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 11,
        "figure.dpi": 300,
    }
)

GEO_TO_HARM = {
    "Andaman and Nicobar": "Other Union Territories",
    "Andhra Pradesh": "Andhra Pradesh",
    "Arunachal Pradesh": "Arunachal Pradesh",
    "Assam": "Assam",
    "Bihar": "Bihar",
    "Chandigarh": "Other Union Territories",
    "Chhattisgarh": "Chhattisgarh",
    "Dadra and Nagar Haveli": "Other Union Territories",
    "Daman and Diu": "Other Union Territories",
    "Delhi": "Delhi",
    "Goa": "Goa",
    "Gujarat": "Gujarat",
    "Haryana": "Haryana",
    "Himachal Pradesh": "Himachal Pradesh",
    "Jammu and Kashmir": "Jammu & Kashmir and Ladakh",
    "Jharkhand": "Jharkhand",
    "Karnataka": "Karnataka",
    "Kerala": "Kerala",
    "Lakshadweep": "Other Union Territories",
    "Madhya Pradesh": "Madhya Pradesh",
    "Maharashtra": "Maharashtra",
    "Manipur": "Manipur",
    "Meghalaya": "Meghalaya",
    "Mizoram": "Mizoram",
    "Nagaland": "Nagaland",
    "Orissa": "Odisha",
    "Puducherry": "Other Union Territories",
    "Punjab": "Punjab",
    "Rajasthan": "Rajasthan",
    "Sikkim": "Sikkim",
    "Tamil Nadu": "Tamil Nadu",
    "Tripura": "Tripura",
    "Uttar Pradesh": "Uttar Pradesh",
    "Uttaranchal": "Uttarakhand",
    "West Bengal": "West Bengal",
}

CAUSE_ORDER = [
    "road",
    "falls",
    "self_harm",
    "drowning",
    "burns",
    "poisoning",
    "violence",
    "other_unintentional",
]
CAUSE_LABELS = {
    "road": "Road",
    "falls": "Falls",
    "self_harm": "Self-harm",
    "drowning": "Drowning",
    "burns": "Burns",
    "poisoning": "Poisoning",
    "violence": "Violence",
    "other_unintentional": "Other unintentional",
}


def save_figure(fig: plt.Figure, stem: str) -> None:
    for ext in ("png", "pdf", "svg"):
        path = FIGURES_DIR / f"{stem}.{ext}"
        fig.savefig(path, bbox_inches="tight", dpi=300 if ext == "png" else None)
    plt.close(fig)
    log.info("Saved %s", stem)


def load_master() -> pd.DataFrame:
    df = pd.read_csv(DATA_PROCESSED, low_memory=False)
    df["sex"] = df["sex"].astype(str).str.strip().str.title()
    df["age_group"] = df["age_group"].astype(str).str.strip()
    return df


def load_state_burden() -> pd.DataFrame:
    return pd.read_csv(OUTPUTS_DIR / "state_burden_2021.csv")


def fig1_daly_map(state_burden: pd.DataFrame) -> None:
    gdf = gpd.read_file(GEOJSON_PATH).to_crs("EPSG:4326")
    gdf["harm_name"] = gdf["NAME_1"].map(GEO_TO_HARM)
    gdf = gdf.merge(
        state_burden[["state_name_harmonized", "dalys_rate"]],
        left_on="harm_name",
        right_on="state_name_harmonized",
        how="left",
    )

    fig, ax = plt.subplots(figsize=(10, 12))
    norm = mcolors.Normalize(vmin=2200, vmax=6100)
    gdf.plot(
        column="dalys_rate",
        cmap="YlOrRd",
        norm=norm,
        edgecolor="white",
        linewidth=0.4,
        ax=ax,
    )
    sm = cm.ScalarMappable(cmap="YlOrRd", norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("Injury DALY rate per 100,000 population")

    key_labels = {
        "Telangana": (79.0, 17.4),
        "Chhattisgarh": (82.0, 21.3),
        "Uttarakhand": (79.6, 30.4),
        "Tamil Nadu": (78.7, 10.9),
        "Kerala": (76.7, 10.5),
        "West Bengal": (88.3, 23.0),
    }
    for label, (x, y) in key_labels.items():
        ax.annotate(
            label,
            xy=(x, y),
            ha="center",
            fontsize=6.5,
            fontweight="bold",
            bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": "none", "alpha": 0.6},
        )

    ax.set_axis_off()
    ax.set_title(
        "State-level injury DALY rates in India, 2021",
        fontweight="bold",
        pad=12,
    )
    fig.text(
        0.12,
        0.04,
        "Boundary data pre-date Telangana (2014) and Ladakh (2019) bifurcations.\n"
        "Telangana is displayed under the combined Andhra Pradesh polygon; Jammu & Kashmir and "
        "Ladakh are shown as a unified GBD unit.",
        fontsize=7.5,
        style="italic",
    )
    save_figure(fig, "fig1_daly_map")


def fig2_hdbi_bar(master: pd.DataFrame) -> None:
    subset = master[
        (master["source"] == "gbd2021")
        & (master["year"] == 2021)
        & (master["sex"] == "Both")
        & (master["age_group"].str.lower() == "all ages")
        & (master["cause_group"] == "all_injuries")
        & (master["metric_type"] == "Rate")
        & (master["state_name_harmonized"] != "India")
        & (master["measure"].isin(["Deaths", "YLDs (Years Lived with Disability)"]))
    ].copy()
    if subset.empty:
        raise RuntimeError("HDBI source data not found in master dataset")

    subset["measure_group"] = subset["measure"].map(
        {
            "Deaths": "death_rate",
            "YLDs (Years Lived with Disability)": "yld_rate",
        }
    )
    pivot = (
        subset.pivot_table(
            index="state_name_harmonized",
            columns="measure_group",
            values="value",
            aggfunc="sum",
        )
        .dropna()
        .reset_index()
    )
    pivot["z_yld"] = (pivot["yld_rate"] - pivot["yld_rate"].mean()) / pivot["yld_rate"].std(ddof=0)
    pivot["z_death"] = (pivot["death_rate"] - pivot["death_rate"].mean()) / pivot["death_rate"].std(ddof=0)
    pivot["hdbi_z"] = pivot["z_yld"] - pivot["z_death"]
    pivot = pivot.sort_values("hdbi_z", ascending=True)
    pivot.to_csv(OUTPUTS_DIR / "hdbi.csv", index=False)

    colors = ["#ca3c32" if v < 0 else "#1f78b4" for v in pivot["hdbi_z"]]
    fig_h = max(8, len(pivot) * 0.24)
    fig, ax = plt.subplots(figsize=(8.5, fig_h))
    ax.barh(pivot["state_name_harmonized"], pivot["hdbi_z"], color=colors)
    ax.axvline(0, color="black", linewidth=0.9)
    ax.set_xlabel("HDBI z-score")
    ax.set_ylabel("")
    ax.set_title("Hidden Disability Burden Index by state, 2021", fontweight="bold", pad=12)
    ax.text(0.01, 1.01, "Positive: disability-prominent; negative: mortality-prominent", transform=ax.transAxes)
    ax.grid(axis="x", alpha=0.25)
    save_figure(fig, "fig2_hdbi_bar")


def fig3_cause_heatmap(master: pd.DataFrame) -> None:
    subset = master[
        (master["source"] == "gbd2021")
        & (master["year"] == 2021)
        & (master["sex"] == "Both")
        & (master["age_group"].str.lower() == "all ages")
        & (master["metric_type"] == "Rate")
        & (master["measure"] == "DALYs (Disability-Adjusted Life Years)")
        & (master["cause_group"].isin(CAUSE_ORDER))
        & (master["state_name_harmonized"] != "India")
    ].copy()
    subset = (
        subset.groupby(["state_name_harmonized", "cause_group"], as_index=False)["value"]
        .sum()
        .pivot(index="state_name_harmonized", columns="cause_group", values="value")
        .reindex(columns=CAUSE_ORDER)
    )
    subset.columns = [CAUSE_LABELS[c] for c in subset.columns]
    subset = subset.loc[subset.mean(axis=1).sort_values(ascending=False).index]
    scaled = subset.apply(lambda col: (col - col.min()) / (col.max() - col.min() + 1e-9), axis=0)

    fig, ax = plt.subplots(figsize=(10, 11))
    im = ax.imshow(scaled.values, aspect="auto", cmap="YlOrRd", vmin=0, vmax=1)
    ax.set_xticks(range(len(subset.columns)))
    ax.set_xticklabels(subset.columns, rotation=35, ha="right")
    ax.set_yticks(range(len(subset.index)))
    ax.set_yticklabels(subset.index, fontsize=7)
    ax.set_title("Cause-specific injury DALY rates by state, 2021", fontweight="bold", pad=12)
    cbar = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
    cbar.set_label("Scaled within each cause")
    save_figure(fig, "fig3_heatmap")


def fig4_trends(master: pd.DataFrame) -> None:
    subset = master[
        (master["source"] == "gbd2021")
        & (master["sex"] == "Both")
        & (master["age_group"].str.lower() == "all ages")
        & (master["cause_group"] == "all_injuries")
        & (master["metric_type"] == "Number")
        & (master["state_name_harmonized"] != "India")
        & (master["measure"].isin(["DALYs (Disability-Adjusted Life Years)", "Deaths", "YLDs (Years Lived with Disability)"]))
    ].copy()
    trend = subset.groupby(["year", "measure"], as_index=False)["value"].sum()
    label_map = {
        "DALYs (Disability-Adjusted Life Years)": "DALYs",
        "Deaths": "Deaths",
        "YLDs (Years Lived with Disability)": "YLDs",
    }
    colours = {"DALYs": "#d62828", "Deaths": "#003049", "YLDs": "#2a9d8f"}

    fig, ax = plt.subplots(figsize=(9, 5.5))
    for measure, label in label_map.items():
        part = trend[trend["measure"] == measure].sort_values("year")
        ax.plot(part["year"], part["value"] / 1_000_000, marker="o", linewidth=2.2, label=label, color=colours[label])
    ax.set_xlabel("Year")
    ax.set_ylabel("Total burden across states (millions)")
    ax.set_title("Subnational injury burden totals by year", fontweight="bold", pad=12)
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    save_figure(fig, "fig4_trends")


def fig5_quadrant(state_burden: pd.DataFrame) -> None:
    pivot = state_burden[["state_name_harmonized", "deaths_rate", "ylds_rate"]].copy()
    x_med = pivot["deaths_rate"].median()
    y_med = pivot["ylds_rate"].median()

    fig, ax = plt.subplots(figsize=(8.5, 7))
    ax.scatter(pivot["deaths_rate"], pivot["ylds_rate"], s=55, color="#457b9d", alpha=0.85)
    for _, row in pivot.iterrows():
        ax.annotate(row["state_name_harmonized"], (row["deaths_rate"], row["ylds_rate"]), fontsize=6)
    ax.axvline(x_med, linestyle="--", color="grey", linewidth=0.9)
    ax.axhline(y_med, linestyle="--", color="grey", linewidth=0.9)
    ax.set_xlabel("Death rate per 100,000")
    ax.set_ylabel("YLD rate per 100,000")
    ax.set_title("State typology by mortality and disability burden, 2021", fontweight="bold", pad=12)
    ax.grid(alpha=0.2)
    save_figure(fig, "fig5_quadrant")


def fig6_mismatch(master: pd.DataFrame) -> None:
    gbd = master[
        (master["source"] == "gbd2021")
        & (master["year"] == 2021)
        & (master["sex"] == "Both")
        & (master["age_group"].str.lower() == "all ages")
        & (master["cause_group"] == "road")
        & (master["metric_type"] == "Number")
        & (master["measure"] == "DALYs (Disability-Adjusted Life Years)")
        & (master["state_name_harmonized"] != "India")
    ].groupby("state_name_harmonized", as_index=False)["value"].sum()
    gbd = gbd.rename(columns={"value": "gbd_road_dalys"})

    morth = master[
        (master["source"] == "morth2023")
        & (master["cause_group"] == "road")
        & (master["measure"] == "Deaths")
        & (master["metric_type"] == "Number")
        & (master["state_name_harmonized"] != "All India")
    ].groupby("state_name_harmonized", as_index=False)["value"].sum()
    morth = morth.rename(columns={"value": "morth_road_deaths"})

    merged = gbd.merge(morth, on="state_name_harmonized", how="inner")
    merged["gbd_rank"] = merged["gbd_road_dalys"].rank(ascending=False, method="min")
    merged["morth_rank"] = merged["morth_road_deaths"].rank(ascending=False, method="min")
    merged["rank_diff"] = merged["morth_rank"] - merged["gbd_rank"]
    merged = merged.sort_values("rank_diff")
    rho, p_value = spearmanr(merged["gbd_rank"], merged["morth_rank"])
    merged.to_csv(OUTPUTS_DIR / "mismatch.csv", index=False)
    log.info("Mismatch rho=%.3f, p=%.4f", rho, p_value)

    top = pd.concat([merged.head(6), merged.tail(6)]).drop_duplicates().sort_values("rank_diff")
    colours = ["#457b9d" if v < 0 else "#e63946" for v in top["rank_diff"]]
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(top["state_name_harmonized"], top["rank_diff"], color=colours)
    ax.axvline(0, color="black", linewidth=0.9)
    ax.set_xlabel("MoRTH rank minus GBD DALY rank")
    ax.set_ylabel("")
    ax.set_title("Road-injury surveillance-burden rank mismatch", fontweight="bold", pad=12)
    ax.text(0.01, 1.01, f"Spearman rho={rho:.2f}; qualitative comparison only", transform=ax.transAxes)
    ax.grid(axis="x", alpha=0.25)
    save_figure(fig, "fig6_mismatch")


def run() -> None:
    log.info("=== Figure generation start ===")
    master = load_master()
    state_burden = load_state_burden()
    fig1_daly_map(state_burden)
    fig2_hdbi_bar(master)
    fig3_cause_heatmap(master)
    fig4_trends(master)
    fig5_quadrant(state_burden)
    fig6_mismatch(master)
    log.info("=== Figure generation complete ===")


if __name__ == "__main__":
    run()
