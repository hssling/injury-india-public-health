"""Reproduce the district injury atlas end to end.

Prerequisites (one-time data acquisition, see README):
  data_local/districts_v2.geojson     LGD/Survey of India/Bhuvan/DataMeet district compilation
  data_local/census2011.csv           India district census 2011
  ../data_raw/ncrb/ADSI_2023.pdf       NCRB ADSI 2023 report (already local)
"""
from meta_district_injury_atlas_india.src import (
    extract_ncrb_cities, build_districts, run_pipeline, validate, sensitivity,
    model_comparison)


def main():
    extract_ncrb_cities.build()      # mega-city anchor tables
    build_districts.build()          # district frame + adjacency
    run_pipeline.main()              # fit 6 causes, tables, maps, blind-spots
    validate.main()                  # 5-fold city CV (anchored causes)
    sensitivity.main()               # structural sensitivity (road)
    model_comparison.main()          # formal LOO/WAIC spatial-vs-non-spatial comparison


if __name__ == "__main__":
    main()
