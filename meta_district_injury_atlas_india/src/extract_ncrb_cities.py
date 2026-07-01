"""Extract NCRB ADSI 2023 mega-city anchor tables from the local report PDF.

Only three causes are tabulated at mega-city level and therefore usable as
district-level anchors:
  * all_injury  = total accidental deaths (Table 1.2) + suicides (Table 2.3)
  * road        = road-accident deaths      (Table 1A.2, "Road Accidents / Died")
  * suicide     = suicides in 2023          (Table 2.3, city-wise)

Table 1.2 also supplies each city's population (in lakh), used as the anchor
exposure (pop_a).

Parser is validated against the report's own narrative figures
(Delhi road 1457, Bengaluru road 915, Delhi suicide 3131, Bengaluru 2370).
"""
import re
import fitz
import pandas as pd
from meta_district_injury_atlas_india.config import NCRB_ADSI_2023_PDF, LOCAL, OUT, YEAR

# (page indices are 0-based within ADSI_2023.pdf, 298 pages)
P_TABLE_1_2 = [35]        # City-wise total accidental deaths + population
P_TABLE_1A_2 = [155, 156]  # City-wise traffic accidents: cases/injured/died
P_TABLE_2_3 = [238, 239]  # City-wise suicides 2022 & 2023


def _flat(doc, pages):
    return " ".join(re.sub(r"[ \t]*\n[ \t]*", " ", doc[p].get_text()) for p in pages)


def _parse_1_2(doc):
    t = _flat(doc, P_TABLE_1_2)
    rows = re.findall(
        r"(?:^|\s)(\d{1,2})\s+([A-Z][A-Z().\- ]+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+"
        r"([\d.]+)\s+([\d.]+)\s+([\d.]+)", t)
    return {r[1].strip(): {"total_acc": int(r[4]), "pop_lakh": float(r[6])} for r in rows}


def _parse_1a_2(doc):
    t = _flat(doc, P_TABLE_1A_2)
    rows = re.findall(r"(\d{1,2})\s+([A-Z][A-Z().\- ]+?)\s+" + r"(\d+)\s+" * 11 + r"(\d+)(?=\s)", t)
    # groups after city: RA_cases, RA_inj, RA_died, ... (13 ints); road died = 3rd int
    return {r[1].strip(): int(r[4]) for r in rows}


def _parse_2_3(doc, city_keys):
    t = _flat(doc, P_TABLE_2_3)
    rows = re.findall(r"(\d{1,2})\s+([A-Z][A-Z().\- ]+?)\s+(\d+)\s+(\d+)\s+(-?[\d.]+)(?=\s)", t)
    out = {}
    for r in rows:
        name = r[1].strip()
        if name in city_keys:                 # drop state rows that bleed in from prior page
            out[name] = int(r[3])             # 2023 column
    return out


def build():
    doc = fitz.open(NCRB_ADSI_2023_PDF)
    t12 = _parse_1_2(doc)
    road = _parse_1a_2(doc)
    suic = _parse_2_3(doc, set(t12))
    assert len(t12) == 53, f"expected 53 cities in Table 1.2, got {len(t12)}"

    long_rows, pop_rows, missing = [], [], []
    for city, d in t12.items():
        pop_rows.append({"city_name": city, "pop_lakh": d["pop_lakh"]})
        r = road.get(city)
        s = suic.get(city)
        if r is None:
            missing.append((city, "road"))
        if s is None:
            missing.append((city, "suicide"))
        all_inj = d["total_acc"] + s if s is not None else None
        for cause, val in [("all_injury", all_inj), ("road", r), ("suicide", s)]:
            long_rows.append({"city_name": city, "year": YEAR, "cause": cause,
                              "deaths_n": val, "source": "ncrb_adsi_2023"})

    LOCAL.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    long_df = pd.DataFrame(long_rows)
    long_df.to_csv(LOCAL / "ncrb_cities_2023.csv", index=False)
    pd.DataFrame(pop_rows).to_csv(LOCAL / "city_population_2023.csv", index=False)
    pd.DataFrame(missing, columns=["city_name", "cause"]).to_csv(
        OUT / "qc_city_missing_causes.csv", index=False)
    wide = long_df.pivot_table(index="city_name", columns="cause", values="deaths_n")
    wide.to_csv(OUT / "ncrb_cities_wide_2023.csv")
    return long_df, wide, missing


if __name__ == "__main__":
    long_df, wide, missing = build()
    print(f"cities={wide.shape[0]}  causes={list(wide.columns)}  missing={len(missing)}")
    print(wide.loc[["DELHI (CITY)", "BENGALURU", "CHENNAI", "MUMBAI"]])
