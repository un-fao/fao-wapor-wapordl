import os
import pathlib

import numpy as np
import pytest

import wapordl
import wapordl.products
import wapordl.products.wapor3
import wapordl.toolbox
import wapordl.toolbox.ogr_gdal
import wapordl.variable_descriptions

module_path = wapordl.__path__[0]
assert "conda" not in module_path

test_data_folder = pathlib.Path(module_path).parent / "test_data"

vectors_ids = [
    (os.path.join(test_data_folder, "polygon_EPSG32636.gpkg"), "name"),
    (os.path.join(test_data_folder, "polygon_EPSG32636.gpkg"), "bla"),
    (os.path.join(test_data_folder, "multipolygon_EPSG4326.gpkg"), "name"),
    (os.path.join(test_data_folder, "multipolygon_EPSG4326.gpkg"), "bla"),
]


def test_main1():
    variable = "L3-T-D"
    period = ["2021-01-01", "2021-01-31"]
    overview = "NONE"
    region = os.path.join(test_data_folder, "polygon_EPSG32636.gpkg")
    identifier = "name"
    df1 = wapordl.wapor_ts(
        region, variable, period, identifier=identifier, overview=overview
    )
    assert df1.columns.size == 7
    assert identifier in list(df1.columns)
    assert np.isfinite(df1["mean"].dropna().mean())
    assert overview in df1.attrs["overview"]
    df2 = wapordl.wapor_ts(
        region, variable, period, identifier=identifier, overview=overview, n_threads=5
    )
    assert df1.equals(df2)


def test_main2():
    variable = "L3-T-D"
    period = ["2021-01-01", "2021-01-31"]
    overview = "NONE"
    region = os.path.join(test_data_folder, "polygon_EPSG32636.gpkg")
    identifier = "name"
    overview = "AUTO"
    df2 = wapordl.wapor_ts(
        region, variable, period, identifier=identifier, overview=overview
    )
    assert df2.columns.size == 7
    assert identifier in list(df2.columns)
    assert np.isfinite(df2["mean"].dropna().mean())
    assert overview in df2.attrs["overview"]
    assert not any(df2["start_date"].isnull())
    df3 = wapordl.wapor_ts(
        region, variable, period, identifier=identifier, overview=overview, n_threads=5
    )
    assert df2.equals(df3)


def test_main3():
    variable = "L3-T-D"
    period = ["2021-01-01", "2021-01-31"]
    overview = "NONE"
    region = os.path.join(test_data_folder, "polygon_EPSG32636.gpkg")
    identifier = None
    overview = "NONE"
    df3 = wapordl.wapor_ts(
        region, variable, period, identifier=identifier, overview=overview
    )
    assert df3.columns.size == 6
    assert overview in df3.attrs["overview"]
    df4 = wapordl.wapor_ts(
        region, variable, period, identifier=identifier, overview=overview, n_threads=5
    )
    assert df4.equals(df3)


def test_main4():
    variable = "L3-T-D"
    period = ["2021-01-01", "2021-01-31"]
    overview = "NONE"
    region = os.path.join(test_data_folder, "polygon_EPSG32636.gpkg")
    identifier = "name"
    region = "GEZ"
    overview = "AUTO"
    df4 = wapordl.wapor_ts(
        region, variable, period, identifier=identifier, overview=overview
    )
    assert df4.columns.size == 6


@pytest.mark.parametrize("vector,identifier", vectors_ids)
def test_base(vector, identifier):
    raster = os.path.join(test_data_folder, "GEZ_L3-AETI-D_1_none.tif")
    out = wapordl.toolbox.ogr_gdal.zonal_stats(raster, vector, identifier)
    assert out.size > 0
    assert out["mean"].dropna().size > 0
    assert np.isfinite(out["mean"].dropna().mean())


def test_invalid_id():
    raster = os.path.join(test_data_folder, "GEZ_L3-AETI-D_1_none.tif")
    vector = os.path.join(test_data_folder, "polygon_EPSG32636.gpkg")
    identifier = "XX"
    with pytest.raises(ValueError) as e:
        _ = wapordl.toolbox.ogr_gdal.zonal_stats(raster, vector, identifier)
    assert "not found in field names" in str(e.value)


def test_invalid_geomtype():
    raster = os.path.join(test_data_folder, "GEZ_L3-AETI-D_1_none.tif")
    vector = os.path.join(test_data_folder, "point_EPSG4326.gpkg")
    identifier = "name"
    with pytest.raises(NotImplementedError) as e:
        _ = wapordl.toolbox.ogr_gdal.zonal_stats(raster, vector, identifier)
    assert "`zonal_stats` for geometry type" in str(e.value)


if __name__ == "__main__":
    vector = vectors_ids[0][0]
    identifier = vectors_ids[0][1]
