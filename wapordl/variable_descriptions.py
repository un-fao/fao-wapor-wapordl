import os

import pandas as pd

from wapordl.toolbox.query import collect_responses


def collect_metadata(variable: str) -> dict:
    """Queries `long_name`, `units` and `source` for a given WaPOR variable code.

    Parameters
    ----------
    variable : str
        Name of variable, e.g. `L3-AETI-D`.

    Returns
    -------
    dict
        Metadata for the variable.

    Raises
    ------
    ValueError
        No valid variable name given.
    """

    if variable in AGERA5_VARS.keys():
        return {
            k: v
            for k, v in AGERA5_VARS[variable].items()
            if k in ["long_name", "units"]
        }

    if variable in WAPOR3_VARS.keys():
        return {
            k: v
            for k, v in WAPOR3_VARS[variable].items()
            if k in ["long_name", "units"]
        }

    if "L1" in variable:
        base_url = (
            "https://data.apps.fao.org/gismgr/api/v2/catalog/workspaces/WAPOR-3/mapsets"
        )
    elif "L2" in variable:
        base_url = (
            "https://data.apps.fao.org/gismgr/api/v2/catalog/workspaces/WAPOR-3/mapsets"
        )
    elif "L3" in variable:
        base_url = "https://data.apps.fao.org/gismgr/api/v2/catalog/workspaces/WAPOR-3/mosaicsets"
    elif "AGERA5" in variable:
        base_url = (
            "https://data.apps.fao.org/gismgr/api/v2/catalog/workspaces/C3S/mapsets"
        )
    else:
        raise ValueError(f"Invalid variable name {variable}.")  # NOTE: TESTED
    info = ["code", "measureCaption", "measureUnit"]
    var_codes = {
        x[0]: {"long_name": x[1], "units": x[2]}
        for x in collect_responses(base_url, info=info)
    }

    return var_codes[variable]


def date_func(url: str, tres: str) -> dict:
    """Determines start and end dates from a string a given temporal resolution, as well
    as the number of days between the two dates.

    Parameters
    ----------
    url : str
        URL linking to a resource.
    tres : str
        One of `"E"` (daily), `"D"` (dekadal), `"M"` (monthly), `"A"` (annual).

    Returns
    -------
    dict
        Dates and related information for a resource URL.

    Raises
    ------
    ValueError
        No valid `tres` given.
    """
    if tres == "D":
        year, month, dekad = os.path.split(url)[-1].split(".")[-2].split("-")
        start_day = {
            "D1": "01",
            "D2": "11",
            "D3": "21",
            "1": "01",
            "2": "11",
            "3": "21",
        }[dekad]
        start_date = f"{year}-{month}-{start_day}"
        end_day = {
            "D1": "10",
            "D2": "20",
            "D3": pd.Timestamp(start_date).daysinmonth,
            "1": "10",
            "2": "20",
            "3": pd.Timestamp(start_date).daysinmonth,
        }[dekad]
        end_date = f"{year}-{month}-{end_day}"
    elif tres == "M":
        year, month = os.path.split(url)[-1].split(".")[-2].split("-")
        start_date = f"{year}-{month}-01"
        end_date = f"{year}-{month}-{pd.Timestamp(start_date).days_in_month}"
    elif tres == "A":
        year = os.path.split(url)[-1].split(".")[-2]
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
    elif tres == "E":
        year, month, start_day = os.path.split(url)[-1].split(".")[-2].split("-")
        start_date = end_date = f"{year}-{month}-{start_day}"
    else:
        raise ValueError("Invalid temporal resolution.")  # NOTE: TESTED

    number_of_days = (
        pd.Timestamp(end_date) - pd.Timestamp(start_date) + pd.Timedelta(1, "D")
    ).days

    date_md = {
        "start_date": start_date,
        "end_date": end_date,
        "number_of_days": number_of_days,
        "temporal_resolution": {"E": "Day", "D": "Dekad", "M": "Month", "A": "Year"}[
            tres
        ],
    }

    if tres == "E":
        dekad = min(3, ((int(start_day) - 1) // 10) + 1)
        days_in_dekad = {1: 10, 2: 10, 3: pd.Timestamp(start_date).daysinmonth - 20}[
            dekad
        ]
        date_md["days_in_dekad"] = days_in_dekad

    return date_md


AGERA5_VARS = {
    "AGERA5-ET0-E": {
        "long_name": "Reference Evapotranspiration",
        "units": "mm/day",
        "source": "FAO56 with agERA5",
        "scale": 1.0,
        "gsutiuri": "gs://fao-gismgr-c3s-data/DATA/C3S/MAPSET/AGERA5-ET0",
    },
    "AGERA5-ET0-D": {
        "long_name": "Reference Evapotranspiration",
        "units": "mm/dekad",
        "source": "FAO56 with agERA5",
        "scale": 1.0,
        "gsutiuri": "gs://fao-gismgr-c3s-data/DATA/C3S/MAPSET/AGERA5-ET0-D",
    },
    "AGERA5-ET0-M": {
        "long_name": "Reference Evapotranspiration",
        "units": "mm/month",
        "source": "FAO56 with agERA5",
        "scale": 1.0,
        "gsutiuri": "gs://fao-gismgr-c3s-data/DATA/C3S/MAPSET/AGERA5-ET0-M",
    },
    "AGERA5-ET0-A": {
        "long_name": "Reference Evapotranspiration",
        "units": "mm/year",
        "source": "FAO56 with agERA5",
        "scale": 1.0,
        "gsutiuri": "gs://fao-gismgr-c3s-data/DATA/C3S/MAPSET/AGERA5-ET0-A",
    },
    "AGERA5-TMIN-E": {
        "long_name": "Minimum Air Temperature (2m)",
        "units": "K",
        "source": "agERA5",
        "scale": 1.0,
        "gsutiuri": "gs://fao-gismgr-c3s-data/DATA/C3S/MAPSET/AGERA5-TMIN",
    },
    "AGERA5-TMAX-E": {
        "long_name": "Maximum Air Temperature (2m)",
        "units": "K",
        "source": "agERA5",
        "scale": 1.0,
        "gsutiuri": "gs://fao-gismgr-c3s-data/DATA/C3S/MAPSET/AGERA5-TMAX",
    },
    "AGERA5-SRF-E": {
        "long_name": "Solar Radiation",
        "units": "J/m2/day",
        "source": "agERA5",
        "scale": 1.0,
        "gsutiuri": "gs://fao-gismgr-c3s-data/DATA/C3S/MAPSET/AGERA5-SRF",
    },
    "AGERA5-WS-E": {
        "long_name": "Wind Speed",
        "units": "m/s",
        "source": "agERA5",
        "scale": 1.0,
        "gsutiuri": "gs://fao-gismgr-c3s-data/DATA/C3S/MAPSET/AGERA5-WS",
    },
    "AGERA5-RH06-E": {
        "long_name": "Relative humidity at 06h (local time, 2m)",
        "units": "%",
        "source": "agERA5",
        "scale": 1.0,
        "gsutiuri": "gs://fao-gismgr-c3s-data/DATA/C3S/MAPSET/AGERA5-RH06",
    },
    "AGERA5-RH09-E": {
        "long_name": "Relative humidity at 09h (local time, 2m)",
        "units": "%",
        "source": "agERA5",
        "scale": 1.0,
        "gsutiuri": "gs://fao-gismgr-c3s-data/DATA/C3S/MAPSET/AGERA5-RH09",
    },
    "AGERA5-RH12-E": {
        "long_name": "Relative humidity at 12h (local time, 2m)",
        "units": "%",
        "source": "agERA5",
        "scale": 1.0,
        "gsutiuri": "gs://fao-gismgr-c3s-data/DATA/C3S/MAPSET/AGERA5-RH12",
    },
    "AGERA5-RH15-E": {
        "long_name": "Relative humidity at 15h (local time, 2m)",
        "units": "%",
        "source": "agERA5",
        "scale": 1.0,
        "gsutiuri": "gs://fao-gismgr-c3s-data/DATA/C3S/MAPSET/AGERA5-RH15",
    },
    "AGERA5-RH18-E": {
        "long_name": "Relative humidity at 18h (local time, 2m)",
        "units": "%",
        "source": "agERA5",
        "scale": 1.0,
        "gsutiuri": "gs://fao-gismgr-c3s-data/DATA/C3S/MAPSET/AGERA5-RH18",
    },
    "AGERA5-PF-E": {
        "long_name": "Precipitation",
        "units": "mm/day",
        "source": "agERA5",
        "scale": 1.0,
        "gsutiuri": "gs://fao-gismgr-c3s-data/DATA/C3S/MAPSET/AGERA5-PF",
    },
    "AGERA5-PF-D": {
        "long_name": "Precipitation",
        "units": "mm/dekad",
        "source": "agERA5",
        "scale": 1.0,
        "gsutiuri": "gs://fao-gismgr-c3s-data/DATA/C3S/MAPSET/AGERA5-PF-D",
    },
    "AGERA5-PF-M": {
        "long_name": "Precipitation",
        "units": "mm/month",
        "source": "agERA5",
        "scale": 1.0,
        "gsutiuri": "gs://fao-gismgr-c3s-data/DATA/C3S/MAPSET/AGERA5-PF-M",
    },
    "AGERA5-PF-A": {
        "long_name": "Precipitation",
        "units": "mm/year",
        "source": "agERA5",
        "scale": 1.0,
        "gsutiuri": "gs://fao-gismgr-c3s-data/DATA/C3S/MAPSET/AGERA5-PF-A",
    },
}

# new = dict()
# from wapordl.products.wapor3 import generate_urls
# period = ["2021-01-01", "2021-02-01"]

# for variable, meta in AGERA5_VARS.items():
#     if variable[-2:] == "-E":
#         variable_ = variable[:-2]
#     if variable in new.keys():
#         continue
#     print(variable)
#     x = generate_urls(variable_, None, period, info="scale")
#     y = generate_urls(variable_, None, period, info="gsutilUri")
#     new[variable] = {**meta, **{"scale": x[0]}, **{"gsutiuri": y[0]}}

WAPOR3_VARS = {
    "L1-AETI-A": {
        "long_name": "Actual EvapoTranspiration and Interception",
        "units": "mm/year",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-AETI-A",
        "scale": 0.1,
    },
    "L1-AETI-D": {
        "long_name": "Actual EvapoTranspiration and Interception",
        "units": "mm/day",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-AETI-D",
        "scale": 0.1,
    },
    "L1-AETI-M": {
        "long_name": "Actual EvapoTranspiration and Interception",
        "units": "mm/month",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-AETI-M",
        "scale": 0.1,
    },
    "L1-E-A": {
        "long_name": "Evaporation",
        "units": "mm/year",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-E-A",
        "scale": 0.1,
    },
    "L1-E-D": {
        "long_name": "Evaporation",
        "units": "mm/day",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-E-D",
        "scale": 0.1,
    },
    "L1-GBWP-A": {
        "long_name": "Gross Biomass Water Productivity",
        "units": "kg/m³",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-GBWP-A",
        "scale": 0.001,
    },
    "L1-I-A": {
        "long_name": "Interception",
        "units": "mm/year",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-I-A",
        "scale": 0.1,
    },
    "L1-I-D": {
        "long_name": "Interception",
        "units": "mm/day",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-I-D",
        "scale": 0.1,
    },
    "L1-NBWP-A": {
        "long_name": "Net Biomass Water Productivity",
        "units": "kg/m³",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-NBWP-A",
        "scale": 0.001,
    },
    "L1-NPP-D": {
        "long_name": "Net Primary Production",
        "units": "gC/m²/day",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-NPP-D",
        "scale": 0.001,
    },
    "L1-NPP-M": {
        "long_name": "Net Primary Production",
        "units": "gC/m²/month",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-NPP-M",
        "scale": 0.001,
    },
    "L1-PCP-A": {
        "long_name": "Precipitation",
        "units": "mm/year",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-PCP-A",
        "scale": 0.1,
    },
    "L1-PCP-D": {
        "long_name": "Precipitation",
        "units": "mm/day",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-PCP-D",
        "scale": 0.1,
    },
    "L1-PCP-E": {
        "long_name": "Precipitation",
        "units": "mm/day",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-PCP-E",
        "scale": 0.1,
    },
    "L1-PCP-M": {
        "long_name": "Precipitation",
        "units": "mm/month",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-PCP-M",
        "scale": 0.1,
    },
    "L1-QUAL-LST-D": {
        "long_name": "Quality Land Surface Temperature",
        "units": "d",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-QUAL-LST-D",
        "scale": 1.0,
    },
    "L1-QUAL-NDVI-D": {
        "long_name": "Quality of Normalized Difference Vegetation Index",
        "units": "d",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-QUAL-NDVI-D",
        "scale": 1.0,
    },
    "L1-RET-A": {
        "long_name": "Reference Evapotranspiration",
        "units": "mm/year",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-RET-A",
        "scale": 0.1,
    },
    "L1-RET-D": {
        "long_name": "Reference Evapotranspiration",
        "units": "mm/day",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-RET-D",
        "scale": 0.1,
    },
    "L1-RET-E": {
        "long_name": "Reference Evapotranspiration",
        "units": "mm/day",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-RET-E",
        "scale": 0.1,
    },
    "L1-RET-M": {
        "long_name": "Reference Evapotranspiration",
        "units": "mm/month",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-RET-M",
        "scale": 0.1,
    },
    "L1-RSM-D": {
        "long_name": "Relative Soil Moisture",
        "units": "%",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-RSM-D",
        "scale": 0.001,
    },
    "L1-T-A": {
        "long_name": "Transpiration",
        "units": "mm/year",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-T-A",
        "scale": 0.1,
    },
    "L1-T-D": {
        "long_name": "Transpiration",
        "units": "mm/day",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-T-D",
        "scale": 0.1,
    },
    "L1-TBP-A": {
        "long_name": "Total Biomass Production",
        "units": "kg/ha",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L1-TBP-A",
        "scale": 1.0,
    },
    "L2-AETI-A": {
        "long_name": "Actual EvapoTranspiration and Interception",
        "units": "mm/year",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L2-AETI-A",
        "scale": 0.1,
    },
    "L2-AETI-D": {
        "long_name": "Actual EvapoTranspiration and Interception",
        "units": "mm/day",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L2-AETI-D",
        "scale": 0.1,
    },
    "L2-AETI-M": {
        "long_name": "Actual EvapoTranspiration and Interception",
        "units": "mm/month",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L2-AETI-M",
        "scale": 0.1,
    },
    "L2-E-A": {
        "long_name": "Evaporation",
        "units": "mm/year",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L2-E-A",
        "scale": 0.1,
    },
    "L2-E-D": {
        "long_name": "Evaporation",
        "units": "mm/day",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L2-E-D",
        "scale": 0.1,
    },
    "L2-GBWP-A": {
        "long_name": "Gross Biomass Water Productivity",
        "units": "kg/m³",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L2-GBWP-A",
        "scale": 0.001,
    },
    "L2-I-A": {
        "long_name": "Interception",
        "units": "mm/year",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L2-I-A",
        "scale": 0.1,
    },
    "L2-I-D": {
        "long_name": "Interception",
        "units": "mm/day",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L2-I-D",
        "scale": 0.1,
    },
    "L2-NBWP-A": {
        "long_name": "Net Biomass Water Productivity",
        "units": "kg/m³",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L2-NBWP-A",
        "scale": 0.001,
    },
    "L2-NPP-D": {
        "long_name": "Net Primary Production",
        "units": "gC/m²/day",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L2-NPP-D",
        "scale": 0.001,
    },
    "L2-NPP-M": {
        "long_name": "Net Primary Production",
        "units": "gC/m²/month",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L2-NPP-M",
        "scale": 0.001,
    },
    "L2-QUAL-NDVI-D": {
        "long_name": "Quality of Normalized Difference Vegetation Index",
        "units": "d",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L2-QUAL-NDVI-D",
        "scale": 1.0,
    },
    "L2-RSM-D": {
        "long_name": "Relative Soil Moisture",
        "units": "%",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L2-RSM-D",
        "scale": 0.001,
    },
    "L2-T-A": {
        "long_name": "Transpiration",
        "units": "mm/year",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L2-T-A",
        "scale": 0.1,
    },
    "L2-T-D": {
        "long_name": "Transpiration",
        "units": "mm/day",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L2-T-D",
        "scale": 0.1,
    },
    "L2-TBP-A": {
        "long_name": "Total Biomass Production",
        "units": "kg/ha",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L2-TBP-A",
        "scale": 1.0,
    },
    "L3-AETI-A": {
        "long_name": "Actual EvapoTranspiration and Interception",
        "units": "mm/year",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-AETI-A",
        "scale": 0.1,
    },
    "L3-AETI-D": {
        "long_name": "Actual EvapoTranspiration and Interception",
        "units": "mm/day",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-AETI-D",
        "scale": 0.1,
    },
    "L3-AETI-M": {
        "long_name": "Actual EvapoTranspiration and Interception",
        "units": "mm/month",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-AETI-M",
        "scale": 0.1,
    },
    "L3-E-A": {
        "long_name": "Evaporation",
        "units": "mm/year",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-E-A",
        "scale": 0.1,
    },
    "L3-E-D": {
        "long_name": "Evaporation",
        "units": "mm/day",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-E-D",
        "scale": 0.1,
    },
    "L3-GBWP-A": {
        "long_name": "Gross Biomass Water Productivity",
        "units": "kg/m³",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-GBWP-A",
        "scale": 0.001,
    },
    "L3-I-A": {
        "long_name": "Interception",
        "units": "mm/year",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-I-A",
        "scale": 0.1,
    },
    "L3-I-D": {
        "long_name": "Interception",
        "units": "mm/day",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-I-D",
        "scale": 0.1,
    },
    "L3-NBWP-A": {
        "long_name": "Net Biomass Water Productivity",
        "units": " kg/m³",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-NBWP-A",
        "scale": 0.001,
    },
    "L3-NPP-D": {
        "long_name": "Net Primary Production",
        "units": "gC/m²/day",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-NPP-D",
        "scale": 0.001,
    },
    "L3-NPP-M": {
        "long_name": "Net Primary Production",
        "units": "gC/m²/month",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-NPP-M",
        "scale": 0.001,
    },
    "L3-QUAL-NDVI-D": {
        "long_name": "Quality of Normalized Difference Vegetation Index",
        "units": "d",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-QUAL-NDVI-D",
        "scale": 1.0,
    },
    "L3-RSM-D": {
        "long_name": "Relative Soil Moisture",
        "units": "%",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-RSM-D",
        "scale": 0.001,
    },
    "L3-T-A": {
        "long_name": "Transpiration",
        "units": "mm/year",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-T-A",
        "scale": 0.1,
    },
    "L3-T-D": {
        "long_name": "Transpiration",
        "units": "mm/day",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-T-D",
        "scale": 0.1,
    },
    "L3-TBP-A": {
        "long_name": "Total Biomass Production",
        "units": "kg/ha",
        "gsutiuri": "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-TBP-A",
        "scale": 1.0,
    },
}
