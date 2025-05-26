import numpy as np
import pandas as pd
import requests

from wapordl.toolbox.ogr_gdal import group_geoms_on_attribute
from wapordl.variable_descriptions import AGERA5_VARS, WAPOR3_VARS


def get_ts(region_shape, period, variable, l3_region=None, identifier=None):
    if "AGERA5" in variable:
        gsutiuri = AGERA5_VARS[variable]["gsutiuri"]
        scale_factor = AGERA5_VARS[variable]["scale"]
        long_name = AGERA5_VARS[variable]["long_name"]
        units = AGERA5_VARS[variable]["units"]
        overview = "NONE"
    else:
        gsutiuri = WAPOR3_VARS[variable]["gsutiuri"]
        scale_factor = WAPOR3_VARS[variable]["scale"]
        long_name = WAPOR3_VARS[variable]["long_name"]
        units = WAPOR3_VARS[variable]["units"]
        overview = "NONE"

    unions, _ = group_geoms_on_attribute(region_shape, identifier, format="json")

    if "L3" in variable:
        if isinstance(l3_region, type(None)):
            raise ValueError("Please specify a valid three letter `l3_region`.")
        gsutiuri += f".{l3_region}"

    data_parts = []
    for name, json_string in unions.items():
        data_ = request_ts(json_string, period, gsutiuri)
        data = parse_data(data_, scale_factor)
        if isinstance(identifier, type(None)):
            identifier = "None"
        data[identifier] = name
        data_parts.append(data)

    data: pd.DataFrame = (
        pd.concat(data_parts)
        .dropna(subset=["mean", "minimum", "maximum"])
        .sort_values([identifier, "start_date"])
        .reset_index(drop=True)
    )

    data["number_of_days"] = (data["end_date"] - data["start_date"]) + pd.Timedelta(
        days=1
    )

    data.attrs = {"long_name": long_name, "units": units, "overview": overview}

    return data


def request_ts(json_string, period, gsutiuri, extra_post_args={"all_touched": True}):
    to_post = {
        "GEE_imageCollection_id": gsutiuri,
        "area_of_interest": eval(json_string),
        "dateRange": {"startDate": period[0], "endDate": period[1]},
        **extra_post_args,
    }
    endpoint = "https://api.data.apps.fao.org/api/v2/map/zonalstats?streaming=false"
    resp = requests.post(endpoint, json=to_post)
    resp.raise_for_status()
    return resp.json()


def parse_data(data, scale_factor):
    df_data = {
        "start_date": [],
        "end_date": [],
        "minimum": [],
        "maximum": [],
        "mean": [],
    }
    for item in data:
        df_data["start_date"].append(np.datetime64(item["system_time_start"], "ms"))
        df_data["end_date"].append(np.datetime64(item["system_time_end"], "ms"))

        if item["min"] is not None:
            df_data["minimum"].append(item["min"] * scale_factor)
        else:
            df_data["minimum"].append(pd.NA)

        if item["max"] is not None:
            df_data["maximum"].append(item["max"] * scale_factor)
        else:
            df_data["maximum"].append(pd.NA)

        if item["mean"] is not None:
            df_data["mean"].append(item["mean"] * scale_factor)
        else:
            df_data["mean"].append(pd.NA)

    df = pd.DataFrame(df_data)
    return df


if __name__ == "__main__":
    ...
