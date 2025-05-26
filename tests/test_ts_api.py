import os
import pathlib

import pandas as pd
import pytest

import wapordl
import wapordl.toolbox.ts_queries
from wapordl.variable_descriptions import AGERA5_VARS, WAPOR3_VARS

module_path = wapordl.__path__[0]
assert "conda" not in module_path

test_data_folder = pathlib.Path(module_path).parent / "test_data"

wapor_gsutiuris = [x["gsutiuri"] for var, x in WAPOR3_VARS.items() if "L3" not in var]


@pytest.mark.parametrize("gsutiuri", wapor_gsutiuris)
def test_base_wapor(gsutiuri):
    json_string = '{ "type": "Polygon", "coordinates": [ [ [ 39.1751869, 8.9148245 ], [ 39.1749088, 8.3098793 ], [ 40.0254231, 8.3085969 ], [ 40.0270531, 8.9134473 ], [ 39.1751869, 8.9148245 ] ] ] }'
    period = ["2021-01-12", "2021-01-12"]
    data = wapordl.toolbox.ts_queries.request_ts(json_string, period, gsutiuri)
    assert len(data) > 0
    assert not isinstance(data[-1]["max"], type(None))


agera5_gsutiuris = [x["gsutiuri"] for x in AGERA5_VARS.values()]


@pytest.mark.parametrize("gsutiuri", agera5_gsutiuris)
def test_base_agera5(gsutiuri):
    json_string = '{ "type": "Polygon", "coordinates": [ [ [ 39.1751869, 8.9148245 ], [ 39.1749088, 8.3098793 ], [ 40.0254231, 8.3085969 ], [ 40.0270531, 8.9134473 ], [ 39.1751869, 8.9148245 ] ] ] }'
    period = ["2021-01-12", "2021-01-12"]
    data = wapordl.toolbox.ts_queries.request_ts(json_string, period, gsutiuri)
    assert len(data) > 0
    assert not isinstance(data[-1]["max"], type(None))


def test_all_touched():
    json_string = '{ "type": "Polygon", "coordinates": [ [ [ 39.1751869, 8.9148245 ], [ 39.1749088, 8.3098793 ], [ 40.0254231, 8.3085969 ], [ 40.0270531, 8.9134473 ], [ 39.1751869, 8.9148245 ] ] ] }'
    period = ["2021-01-12", "2021-03-25"]
    gsutiuri = "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MAPSET/L2-AETI-D"
    extra_post_args = {"all_touched": True}
    data_all_touched = wapordl.toolbox.ts_queries.request_ts(
        json_string, period, gsutiuri, extra_post_args=extra_post_args
    )
    extra_post_args = {"all_touched": False}
    data_not_all_touched = wapordl.toolbox.ts_queries.request_ts(
        json_string, period, gsutiuri, extra_post_args=extra_post_args
    )
    assert data_all_touched[-1]["maskedCount"] > data_not_all_touched[-1]["maskedCount"]


def test_level3():
    variable = "L3-AETI-D"
    region = "/Users/hmcoerver/Library/Mobile Documents/com~apple~CloudDocs/GitHub/wapordl/wapordl/test_data/test_GEZ.geojson"
    json_string = '{ "type": "MultiPolygon", "coordinates": [ [ [ [ 33.321400177824032, 14.260368111392115 ], [ 33.371790739277863, 14.250535806718197 ], [ 33.423410338815934, 14.133777188715419 ], [ 33.334919596750666, 14.068638170250711 ], [ 33.204641559821255, 14.165732178905653 ], [ 33.321400177824032, 14.260368111392115 ] ] ] ] }'
    scale_factor = 0.1
    period = ["2021-01-12", "2021-03-25"]
    gsutiuri = "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-AETI-D.GEZ"
    data = wapordl.toolbox.ts_queries.request_ts(json_string, period, gsutiuri)
    df1 = wapordl.toolbox.ts_queries.parse_data(data, scale_factor)
    assert df1.iloc[-1]["mean"] == 1.944007436363251

    df2 = wapordl.wapor_ts(region, variable, period, method="original")
    assert df1["mean"].corr(df2["mean"]) > 0.999

    gsutiuri = "gs://fao-gismgr-wapor-3-data/DATA/WAPOR-3/MOSAICSET/L3-AETI-D.AWA"
    data = wapordl.toolbox.ts_queries.request_ts(json_string, period, gsutiuri)
    df3 = wapordl.toolbox.ts_queries.parse_data(data, scale_factor)
    assert df3["mean"].isna().all()


cases = [
    ([33.2, 14.0, 33.4, 14.2], "L3-AETI-D", "none", None),
    ([33.2, 14.0, 33.4, 14.2], "L2-AETI-D", "none", None),
    ([33.2, 14.0, 33.4, 14.2], "L1-AETI-D", "none", None),
    (
        os.path.join(test_data_folder, "polygon_EPSG32636.gpkg"),
        "L1-AETI-D",
        "none",
        "name",
    ),
    (
        os.path.join(test_data_folder, "polygon_EPSG32636.gpkg"),
        "L3-AETI-D",
        "dekad",
        "bla",
    ),
    (
        os.path.join(test_data_folder, "polygon_EPSG32636.gpkg"),
        "L2-AETI-M",
        "day",
        "bla",
    ),
    (
        os.path.join(test_data_folder, "polygon_EPSG32636.gpkg"),
        "L1-AETI-D",
        "none",
        None,
    ),
    (
        os.path.join(test_data_folder, "polygon_EPSG32636.gpkg"),
        "AGERA5-ET0-E",
        "none",
        None,
    ),
]


@pytest.mark.parametrize("region,variable,unit_conversion,identifier", cases)
def test_wapor_ts(region, variable, unit_conversion, identifier):
    if variable[-2:] == "-E":
        period = ["2021-01-22", "2021-02-03"]
    else:
        period = ["2021-01-12", "2021-02-25"]

    df1 = wapordl.wapor_ts(
        region,
        variable,
        period,
        method="original",
        unit_conversion=unit_conversion,
        identifier=identifier,
    )
    df2 = wapordl.wapor_ts(
        region,
        variable,
        period,
        method="new",
        unit_conversion=unit_conversion,
        identifier=identifier,
    )

    if identifier in df1.columns:
        for name in df1[identifier].unique():
            if isinstance(name, type(pd.NA)):
                x1 = df1.loc[df1[identifier].isnull()]["mean"]
                x2 = df2.loc[df2[identifier].isnull()]["mean"]
            else:
                x1 = df1.loc[df1[identifier] == name]["mean"]
                x2 = df2.loc[df2[identifier] == name]["mean"]
            r = x1.corr(x2)
            print(name, r)
            assert r > 0.999
            assert df1.attrs == df2.attrs
    else:
        x1 = df1["mean"]
        x2 = df2["mean"]
        r = x1.corr(x2)
        # print(name, r)
        assert r > 0.999
        assert df1.attrs == df2.attrs


if __name__ == "__main__":
    region, variable, unit_conversion, identifier = cases[-1]

    # import matplotlib.pyplot as plt

    # fig = plt.figure(1)
    # ax = fig.gca()
    # df2.loc[df2["name"] == "corn"]["mean"].plot(ax=ax, label="new")
    # df1.loc[df1["name"] == "corn"]["mean"].plot(ax=ax, label="original")
    # plt.legend()
