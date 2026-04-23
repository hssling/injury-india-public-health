"""
Publication-Grade Figure Generation (Step 6)
Generates all manuscript figures at 600 dpi PNG, SVG, and PDF.

Figures:
  Fig 1: India choropleth — DALY rate by state
  Fig 2: India choropleth — YLD:YLL ratio (hidden disability index)
  Fig 3: Heatmap — cause × state DALY rates
  Fig 4: Trend lines — national injury DALYs 2000–2021
  Fig 5: Quadrant plot — YLL rate vs YLD rate by state
  Fig 6: Rank mismatch plot (GBD DALY rank vs MoRTH death rank)
  Fig 7: Age-sex pyramid for injuries
"""

import pathlib
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Patch
import logging
import warnings
warnings.filterwarnings("ignore")

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_PROCESSED = PROJECT_ROOT / "data_processed"
OUTPUTS = PROJECT_ROOT / "outputs"
FIGURES = PROJECT_ROOT / "figures"
LOGS = PROJECT_ROOT / "logs"
FIGURES.mkdir(exist_ok=True)
(FIGURES / "supplementary").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOGS / "20_figures.log"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)

# Figure settings
DPI = 600
FIGSIZE_SINGLE = (10, 8)
FIGSIZE_WIDE = (14, 8)
IJMR_FONT = "DejaVu Sans"
plt.rcParams.update({
    "font.family": IJMR_FONT,
    "font.size": 11,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "figure.dpi": DPI,
})

CAUSE_LABELS = {
    "road": "Road injuries",
    "falls": "Falls",
    "self_harm": "Self-harm",
    "drowning": "Drowning",
    "burns": "Burns",
    "poisoning": "Poisoning",
    "violence": "Interpersonal violence",
    "other_transport": "Other transport",
    "other_unintentional": "Other unintentional",
    "all_injuries": "All injuries",
}


def save_fig(fig, name: str):
    for ext, dpi in [("png", DPI), ("svg", None), ("pdf", None)]:
        fpath = FIGURES / f"{name}.{ext}"
        fig.savefig(str(fpath), dpi=dpi if ext == "png" else None,
                    bbox_inches="tight", facecolor="white")
    log.info(f"Saved figure: {name} (PNG/SVG/PDF)")
    plt.close(fig)


def placeholder_figure(name: str, message: str):
    """Generate a placeholder figure when data is unavailable."""
    fig, ax = plt.subplots(figsize=FIGSIZE_SINGLE)
    ax.text(0.5, 0.5, f"[PLACEHOLDER]\n{message}\n\nWill be generated after\ndata download and processing.",
            ha="center", va="center", transform=ax.transAxes,
            fontsize=12, color="gray",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#f5f5f5", edgecolor="gray"))
    ax.set_axis_off()
    ax.set_title(name.replace("_", " ").title(), fontsize=13, pad=15)
    save_fig(fig, name)


def fig1_daly_choropleth(df: pd.DataFrame):
    """India choropleth of age-standardized DALY rate (all injuries, 2021)."""
    try:
        import geopandas as gpd
        shapefile = PROJECT_ROOT / "data_raw" / "shapefiles"
        shp_files = list(shapefile.glob("*.shp"))
        if not shp_files:
            placeholder_figure("fig1_daly_map", "Shapefile not downloaded yet.\nDownload from: https://gadm.org")
            return

        gdf = gpd.read_file(str(shp_files[0]))

        gbd_daly = df[
            (df["source"] == "gbd2021") & (df["year"] == 2021) &
            (df["cause_group"] == "all_injuries") & (df["measure"] == "DALYs") &
            (df["metric_type"] == "Rate") & (df["sex"] == "Both") &
            (df["age_group"] == "All ages") & (df["state_name_harmonized"] != "India")
        ][["state_name_harmonized", "value"]].rename(columns={"value": "daly_rate"})

        if gbd_daly.empty:
            placeholder_figure("fig1_daly_map", "GBD DALY data not yet available")
            return

        # Merge shapefile with data
        name_col = "NAME_1" if "NAME_1" in gdf.columns else gdf.columns[2]
        gdf = gdf.merge(gbd_daly, left_on=name_col, right_on="state_name_harmonized", how="left")

        fig, ax = plt.subplots(1, 1, figsize=(12, 12))
        gdf.plot(column="daly_rate", ax=ax, legend=True, cmap="YlOrRd",
                 missing_kwds={"color": "lightgray", "label": "No data"},
                 legend_kwds={"label": "Age-standardized DALY rate\n(per 100,000)", "shrink": 0.7})
        ax.set_axis_off()
        ax.set_title("Age-standardized injury DALY rate by state, India 2021\n(GBD 2021)",
                     fontsize=13, pad=15)
        plt.tight_layout()
        save_fig(fig, "fig1_daly_map")

    except ImportError:
        placeholder_figure("fig1_daly_map", "geopandas not installed.\nRun: pip install geopandas")
    except Exception as e:
        log.error(f"Fig 1 failed: {e}")
        placeholder_figure("fig1_daly_map", f"Map generation failed: {e}")


def fig2_hdbi_choropleth():
    """India choropleth of HDBI (hidden disability burden index)."""
    hdbi_path = OUTPUTS / "hdbi.csv"
    if not hdbi_path.exists():
        placeholder_figure("fig2_hdbi_map", "HDBI output not yet computed.\nRun: python src/analysis/12_hdbi.py")
        return

    try:
        import geopandas as gpd
        shapefile = PROJECT_ROOT / "data_raw" / "shapefiles"
        shp_files = list(shapefile.glob("*.shp"))
        if not shp_files:
            placeholder_figure("fig2_hdbi_map", "Shapefile not downloaded")
            return

        hdbi = pd.read_csv(hdbi_path)
        gdf = gpd.read_file(str(shp_files[0]))
        name_col = "NAME_1" if "NAME_1" in gdf.columns else gdf.columns[2]
        gdf = gdf.merge(hdbi[["state_name_harmonized", "hdbi_z"]],
                        left_on=name_col, right_on="state_name_harmonized", how="left")

        fig, ax = plt.subplots(1, 1, figsize=(12, 12))
        vmax = hdbi["hdbi_z"].abs().quantile(0.95) if len(hdbi) > 3 else 2
        gdf.plot(column="hdbi_z", ax=ax, legend=True, cmap="RdBu_r",
                 vmin=-vmax, vmax=vmax,
                 missing_kwds={"color": "lightgray"},
                 legend_kwds={"label": "HDBI (z-score)\n+ = disability prominent\n− = mortality prominent",
                               "shrink": 0.7})
        ax.set_axis_off()
        ax.set_title("Hidden Disability Burden Index by state, India 2021\n(GBD 2021)",
                     fontsize=13, pad=15)
        save_fig(fig, "fig2_hdbi_map")

    except ImportError:
        placeholder_figure("fig2_hdbi_map", "geopandas not installed")
    except Exception as e:
        log.error(f"Fig 2 failed: {e}")
        placeholder_figure("fig2_hdbi_map", f"Failed: {e}")


def fig3_cause_state_heatmap(df: pd.DataFrame):
    """Heatmap of cause-specific injury DALY rates by state."""
    if df.empty or "source" not in df.columns:
        placeholder_figure("fig3_heatmap", "GBD cause-specific data not yet available")
        return
    causes = ["road", "falls", "self_harm", "drowning", "burns", "poisoning", "violence"]
    gbd = df[
        (df["source"] == "gbd2021") & (df["year"] == 2021) &
        (df["cause_group"].isin(causes)) & (df["measure"] == "DALYs") &
        (df["metric_type"] == "Rate") & (df["sex"] == "Both") &
        (df["age_group"] == "All ages") & (df["state_name_harmonized"] != "India")
    ].copy()

    if gbd.empty:
        placeholder_figure("fig3_heatmap", "GBD cause-specific data not yet available")
        return

    pivot = gbd.pivot_table(index="state_name_harmonized", columns="cause_group",
                             values="value", aggfunc="first")
    pivot.columns = [CAUSE_LABELS.get(c, c) for c in pivot.columns]

    # Normalize each cause column for better visual contrast
    pivot_norm = (pivot - pivot.min()) / (pivot.max() - pivot.min() + 1e-9)
    pivot_norm = pivot_norm.sort_values(list(pivot_norm.columns)[0], ascending=False)

    fig, ax = plt.subplots(figsize=(14, max(10, len(pivot_norm) * 0.35)))
    im = ax.imshow(pivot_norm.values, cmap="YlOrRd", aspect="auto", vmin=0, vmax=1)

    ax.set_xticks(range(len(pivot_norm.columns)))
    ax.set_xticklabels(pivot_norm.columns, rotation=30, ha="right", fontsize=9)
    ax.set_yticks(range(len(pivot_norm.index)))
    ax.set_yticklabels(pivot_norm.index, fontsize=8)
    plt.colorbar(im, ax=ax, label="Relative DALY rate (within-cause scaled)", shrink=0.6)
    ax.set_title("Cause-specific injury DALY rates by state, India 2021\n"
                 "(GBD 2021; column-scaled: yellow=low, red=high)", fontsize=12, pad=15)
    plt.tight_layout()
    save_fig(fig, "fig3_heatmap")


def fig4_national_trends(df: pd.DataFrame):
    """Trend lines: national injury burden 2000–2021."""
    if df.empty or "source" not in df.columns:
        placeholder_figure("fig4_trends", "National GBD trend data not available")
        return
    gbd_nat = df[
        (df["source"] == "gbd2021") & (df["cause_group"] == "all_injuries") &
        (df["sex"] == "Both") & (df["age_group"] == "All ages") &
        (df["metric_type"] == "Rate") & (df["state_name_harmonized"] == "India")
    ].copy()

    if gbd_nat.empty:
        placeholder_figure("fig4_trends", "National GBD trend data not available")
        return

    measures = {"DALYs": "DALY rate", "Deaths": "Death rate", "YLDs": "YLD rate", "YLLs": "YLL rate"}
    colors = {"DALYs": "#e63946", "Deaths": "#457b9d", "YLDs": "#2a9d8f", "YLLs": "#f4a261"}

    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    for measure, label in measures.items():
        subset = gbd_nat[gbd_nat["measure"] == measure].sort_values("year")
        if not subset.empty:
            ax.plot(subset["year"], subset["value"], label=label,
                    color=colors.get(measure, "black"), linewidth=2.5, marker="o", markersize=5)
            if "lower_ui" in subset.columns and "upper_ui" in subset.columns:
                ax.fill_between(subset["year"], subset["lower_ui"], subset["upper_ui"],
                                alpha=0.15, color=colors.get(measure, "gray"))

    ax.set_xlabel("Year", fontsize=12)
    ax.set_ylabel("Rate per 100,000 population", fontsize=12)
    ax.set_title("National injury burden trends, India 2000–2021\n(GBD 2021)", fontsize=13)
    ax.legend(loc="best", fontsize=10)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    save_fig(fig, "fig4_trends")


def fig5_quadrant_plot(df: pd.DataFrame):
    """YLL rate vs YLD rate quadrant plot by state."""
    if df.empty or "source" not in df.columns:
        placeholder_figure("fig5_quadrant", "GBD YLL/YLD data not available")
        return
    gbd = df[
        (df["source"] == "gbd2021") & (df["year"] == 2021) &
        (df["cause_group"] == "all_injuries") &
        (df["measure"].isin(["YLLs", "YLDs"])) &
        (df["metric_type"] == "Rate") & (df["sex"] == "Both") &
        (df["age_group"] == "All ages") & (df["state_name_harmonized"] != "India")
    ].copy()

    if gbd.empty:
        placeholder_figure("fig5_quadrant", "GBD YLL/YLD data not available")
        return

    pivot = gbd.pivot_table(index="state_name_harmonized", columns="measure",
                             values="value", aggfunc="first").reset_index()
    if "YLLs" not in pivot.columns or "YLDs" not in pivot.columns:
        placeholder_figure("fig5_quadrant", "YLL or YLD columns missing")
        return
    pivot = pivot.rename(columns={"YLLs": "yll_rate", "YLDs": "yld_rate"})

    med_yll = pivot["yll_rate"].median()
    med_yld = pivot["yld_rate"].median()

    fig, ax = plt.subplots(figsize=FIGSIZE_SINGLE)
    ax.scatter(pivot["yll_rate"], pivot["yld_rate"], s=80, alpha=0.75,
               c="#e63946", edgecolors="white", linewidths=0.5, zorder=3)

    for _, row in pivot.iterrows():
        ax.annotate(row["state_name_harmonized"], (row["yll_rate"], row["yld_rate"]),
                    fontsize=6, ha="left", va="bottom", alpha=0.8)

    ax.axvline(med_yll, color="gray", linestyle="--", alpha=0.7, linewidth=1)
    ax.axhline(med_yld, color="gray", linestyle="--", alpha=0.7, linewidth=1)

    # Quadrant labels
    xl, xh = ax.get_xlim()
    yl, yh = ax.get_ylim()
    pad = 0.03
    ax.text(xh - pad*(xh-xl), yh - pad*(yh-yl), "High YLL\nHigh YLD\n(Q1)", ha="right", va="top",
            fontsize=8, color="#457b9d", alpha=0.8)
    ax.text(xl + pad*(xh-xl), yh - pad*(yh-yl), "Low YLL\nHigh YLD\n(Q3: Hidden disability)", ha="left", va="top",
            fontsize=8, color="#2a9d8f", alpha=0.8)
    ax.text(xh - pad*(xh-xl), yl + pad*(yh-yl), "High YLL\nLow YLD\n(Q2: Mortality dominant)", ha="right", va="bottom",
            fontsize=8, color="#f4a261", alpha=0.8)
    ax.text(xl + pad*(xh-xl), yl + pad*(yh-yl), "Low YLL\nLow YLD\n(Q4)", ha="left", va="bottom",
            fontsize=8, color="gray", alpha=0.8)

    ax.set_xlabel("YLL rate per 100,000", fontsize=12)
    ax.set_ylabel("YLD rate per 100,000", fontsize=12)
    ax.set_title("State-level injury burden typology: YLL vs YLD rates, India 2021\n(GBD 2021)",
                 fontsize=12, pad=15)
    ax.grid(alpha=0.25)
    plt.tight_layout()
    save_fig(fig, "fig5_quadrant")


def fig6_mismatch_plot():
    """Rank mismatch plot: GBD road DALY rank vs MoRTH road death rank."""
    mismatch_path = OUTPUTS / "mismatch.csv"
    if not mismatch_path.exists():
        placeholder_figure("fig6_mismatch", "Mismatch analysis not yet run.\nRun: python src/analysis/18_mismatch.py")
        return

    mm = pd.read_csv(mismatch_path)
    required = ["state_name_harmonized", "rank_gbd_road_dalys", "rank_morth_road_deaths"]
    if not all(c in mm.columns for c in required):
        placeholder_figure("fig6_mismatch", "Required columns missing from mismatch output")
        return

    mm = mm.dropna(subset=required).sort_values("rank_gbd_road_dalys")

    fig, ax = plt.subplots(figsize=(10, max(8, len(mm) * 0.32)))
    y = range(len(mm))
    ax.barh(y, mm["rank_morth_road_deaths"] - mm["rank_gbd_road_dalys"],
            color=["#e63946" if v > 0 else "#457b9d"
                   for v in (mm["rank_morth_road_deaths"] - mm["rank_gbd_road_dalys"])],
            alpha=0.8)
    ax.set_yticks(list(y))
    ax.set_yticklabels(mm["state_name_harmonized"], fontsize=8)
    ax.axvline(0, color="black", linewidth=1)
    ax.set_xlabel("Rank difference (MoRTH 2023 rank − GBD 2021 DALY rank)\n"
                  "Positive (red): ranked higher on road deaths than DALYs\n"
                  "Negative (blue): ranked higher on DALYs than deaths", fontsize=9)
    ax.set_title("Surveillance–burden rank mismatch: road injuries, India\n"
                 "(MoRTH 2023 vs GBD 2021; qualitative comparison only)", fontsize=11, pad=15)
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    save_fig(fig, "fig6_mismatch")


def fig7_age_sex_pyramid(df: pd.DataFrame):
    """Age-sex pyramid for all-injuries burden, India 2021."""
    if df.empty or "source" not in df.columns:
        placeholder_figure("fig7_age_sex", "Age-sex disaggregated GBD data not available")
        return
    gbd = df[
        (df["source"] == "gbd2021") & (df["year"] == 2021) &
        (df["cause_group"] == "all_injuries") & (df["measure"] == "DALYs") &
        (df["metric_type"] == "Rate") &
        (df["sex"].isin(["Male", "Female"])) &
        (df["state_name_harmonized"] == "India") &
        (~df["age_group"].isin(["All ages", "Age-standardized"]))
    ].copy()

    if gbd.empty:
        placeholder_figure("fig7_age_sex", "Age-sex disaggregated GBD data not available")
        return

    AGE_ORDER = ["0–4 years", "5–14 years", "15–29 years", "30–49 years",
                 "50–69 years", "70+ years"]
    gbd_pivot = gbd.pivot_table(index="age_group", columns="sex", values="value", aggfunc="first")

    # Try to align age groups
    available_ages = [a for a in AGE_ORDER if a in gbd_pivot.index]
    if not available_ages:
        available_ages = sorted(gbd_pivot.index)
    gbd_pivot = gbd_pivot.reindex(available_ages)

    fig, ax = plt.subplots(figsize=(10, 7))
    if "Male" in gbd_pivot.columns:
        ax.barh(range(len(gbd_pivot)), -gbd_pivot["Male"], color="#457b9d", alpha=0.85, label="Male")
    if "Female" in gbd_pivot.columns:
        ax.barh(range(len(gbd_pivot)), gbd_pivot["Female"], color="#e63946", alpha=0.85, label="Female")

    ax.set_yticks(range(len(gbd_pivot)))
    ax.set_yticklabels(list(gbd_pivot.index), fontsize=10)
    ax.set_xlabel("DALY rate per 100,000 (← Male | Female →)", fontsize=11)
    ax.set_title("Age-sex distribution of injury DALY rate, India 2021\n(GBD 2021)",
                 fontsize=12, pad=15)
    ax.legend(loc="lower right", fontsize=10)
    ax.grid(axis="x", alpha=0.3)
    xt = ax.get_xticks()
    ax.set_xticklabels([str(abs(int(x))) for x in xt], fontsize=9)
    ax.axvline(0, color="black", linewidth=0.8)
    plt.tight_layout()
    save_fig(fig, "fig7_age_sex")


def run():
    log.info("=== Figure Generation: Start ===")

    fpath = DATA_PROCESSED / "master_dataset.csv"
    if not fpath.exists():
        log.warning("Master dataset not found — generating all placeholder figures.")
        df = pd.DataFrame()
    else:
        df = pd.read_csv(fpath, low_memory=False)
        log.info(f"Master dataset loaded: {len(df):,} rows")

    # Generate all figures
    fig1_daly_choropleth(df)
    fig2_hdbi_choropleth()
    fig3_cause_state_heatmap(df)
    fig4_national_trends(df)
    fig5_quadrant_plot(df)
    fig6_mismatch_plot()
    fig7_age_sex_pyramid(df)

    log.info(f"All figures saved to: {FIGURES}")
    log.info("=== Figure Generation: Complete ===")


if __name__ == "__main__":
    run()
